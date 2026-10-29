import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.security_check import SecurityError, check_staged, scan_files, scanner, _scan
from scripts.security_config import load_private_config, redact, safe_print
from scripts.github_pr import GitHubPullRequests, PullRequestError


class PrivateConfigurationTest(unittest.TestCase):
    def test_process_env_wins_and_legacy_is_supported(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DEEPSEEK_API_KEY": "process-value"}, clear=True):
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts/.env").write_text('DEEPSEEK_API_KEY=file-value\nOPENAI_API_KEY=primary-value\n')
            (root / "scripts/dc-config.env").write_text('OPENAI_API_KEY=legacy-value\nDESIRECORE_MODEL=test-model\n')
            load_private_config(root)
            self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "process-value")
            self.assertEqual(os.environ["OPENAI_API_KEY"], "primary-value")
            self.assertEqual(os.environ["DESIRECORE_MODEL"], "test-model")
            if os.name == "posix":
                self.assertEqual((root / "scripts/.env").stat().st_mode & 0o777, 0o600)

    def test_redacts_credentials_in_errors_and_authenticated_urls(self):
        synthetic = "synthetic-" + "credential-123456789"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": synthetic}):
            output = io.StringIO()
            safe_print(RuntimeError(f'{synthetic} Bearer other-value https://user:pass@example.org/?token=other-token'), file=output)
            text = output.getvalue()
            for sensitive in [synthetic, "other-value", "user:pass", "other-token"]:
                self.assertNotIn(sensitive, text)


class SecretGateTest(unittest.TestCase):
    def test_opaque_known_secret_is_detected_after_file_deleted_from_history(self):
        synthetic = "temporary-" + "opaque-historical-private-1234"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DEEPSEEK_API_KEY": synthetic}):
            root = Path(directory)
            for args in [["init", "-q"], ["config", "user.name", "test"], ["config", "user.email", "test@example.org"]]:
                subprocess.run(["git", *args], cwd=root, check=True)
            (root / "post.md").write_text(synthetic)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "historical fixture"], cwd=root, check=True)
            (root / "post.md").unlink()
            subprocess.run(["git", "commit", "-qam", "delete fixture"], cwd=root, check=True)
            with self.assertRaises(SecurityError) as caught:
                _scan(root, history=True)
            self.assertNotIn(synthetic, str(caught.exception))

    def test_article_cannot_exempt_its_own_secret_with_allow_comment(self):
        import secrets
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credential = "ghp_" + secrets.token_hex(18)
            (root / "post.md").write_text(f'token="{credential}" # gitleaks:allow\n')
            with self.assertRaises(SecurityError) as caught:
                scan_files(root, ["post.md"])
            self.assertNotIn(credential, str(caught.exception))

    def test_known_secret_rejected_in_every_public_artifact(self):
        synthetic = "temporary-" + "private-test-value-1234"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DEEPSEEK_API_KEY": synthetic}):
            root = Path(directory)
            for filename in ["report.md", "rss.xml", "record.json", "dist.js"]:
                (root / filename).write_text(synthetic)
                with self.subTest(filename=filename), self.assertRaises(SecurityError) as caught:
                    scan_files(root, [filename])
                self.assertNotIn(synthetic, str(caught.exception))

    def test_generic_private_key_rejected_without_runtime_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "article.md").write_text('-----BEGIN ' + 'RSA PRIVATE KEY-----\n' + 'A' * 128 + '\n-----END ' + 'RSA PRIVATE KEY-----\n')
            with self.assertRaises(SecurityError) as caught:
                scan_files(root, ["article.md"])
            self.assertNotIn('A' * 128, str(caught.exception))

    def test_missing_scanner_fails_closed(self):
        with patch("scripts.security_check.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(SecurityError):
                scanner()

    def test_scans_staged_bytes_even_when_worktree_is_cleaned(self):
        synthetic = "temporary-" + "staged-private-123456"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DEEPSEEK_API_KEY": synthetic}):
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "post.md").write_text(synthetic)
            subprocess.run(["git", "add", "post.md"], cwd=root, check=True)
            (root / "post.md").write_text("clean worktree content")
            with self.assertRaises(SecurityError):
                check_staged(root)

    def test_private_env_ignored_and_example_can_be_committed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            source = Path(__file__).resolve().parent.parent / ".gitignore"
            (root / ".gitignore").write_text(source.read_text())
            for name in ["scripts/.env", "scripts/.env.production", "scripts/dc-config.env"]:
                result = subprocess.run(["git", "check-ignore", name], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 0)
            for name in ["scripts/.env.example", "scripts/dc-config.env.example"]:
                result = subprocess.run(["git", "check-ignore", name], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 1)


class PullRequestPolicyTest(unittest.TestCase):
    def client(self):
        client = object.__new__(GitHubPullRequests)
        client.base, client.login, client.repo = "main", "owner", "owner/blog"
        return client

    def pr(self):
        return dict(number=1, url="https://github.com/owner/blog/pull/1", author={"login": "owner"},
                    isCrossRepository=False, baseRefName="main", headRefOid="expected", state="OPEN",
                    mergeable="MERGEABLE", statusCheckRollup=[])

    def test_untrusted_author_cannot_auto_merge(self):
        pr = self.pr()
        pr["author"] = {"login": "someone-else"}
        with self.assertRaises(PullRequestError):
            self.client().validate(pr, {"post.md"})

    def test_hidden_extra_files_are_rejected(self):
        client = self.client()
        client._run = lambda *args: '[[{"filename":"post.md"}], [{"filename":"scripts/evil.py"}]]'
        with self.assertRaises(PullRequestError):
            client.validate(self.pr(), {"post.md"})

    def test_pending_checks_never_call_merge(self):
        client = self.client()
        client.get = lambda number: self.pr()
        client.validate = lambda *args: None
        with patch.object(client, "_run") as run, self.assertRaisesRegex(PullRequestError, "pending"):
            client.wait_for_merge(self.pr(), {"post.md"}, timeout=0)
        run.assert_not_called()

    def test_failed_checks_and_conflicts_stop_publication(self):
        for field, value in [("mergeable", "CONFLICTING"), ("statusCheckRollup", [{"name":"tests", "conclusion":"FAILURE"}])]:
            client, pr = self.client(), self.pr()
            pr[field] = value
            client.get = lambda number: pr
            client.validate = lambda *args: None
            with self.subTest(field=field), self.assertRaises(PullRequestError):
                client.wait_for_merge(self.pr(), {"post.md"}, timeout=0)

    def test_changed_head_stops_auto_merge(self):
        client, pr = self.client(), self.pr()
        pr["headRefOid"] = "unreviewed"
        client.get = lambda number: pr
        client.validate = lambda *args: None
        with self.assertRaisesRegex(PullRequestError, "head changed"):
            client.wait_for_merge(self.pr(), {"post.md"}, timeout=0)

    def test_merge_is_bound_to_scanned_head_without_standing_auto_authorization(self):
        client, ready = self.client(), self.pr()
        ready["statusCheckRollup"] = [{"name": name, "conclusion": "SUCCESS"} for name in ["security", "tests", "build"]]
        merged = dict(ready, state="MERGED", mergeCommit={"oid": "merged-sha"})
        client.validate = lambda *args: None
        with patch.object(client, "get", side_effect=[ready, merged]), patch.object(client, "_run") as run:
            result = client.wait_for_merge(self.pr(), {"post.md"}, interval=0)
        self.assertEqual(result, "merged-sha")
        args = run.call_args.args
        self.assertNotIn("--auto", args)
        self.assertEqual(args[-2:], ("--match-head-commit", "expected"))


if __name__ == "__main__":
    unittest.main()
