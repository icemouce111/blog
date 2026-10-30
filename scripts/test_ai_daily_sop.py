import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock
from pathlib import Path

from scripts.ai_daily_sop import (
    AtomicRunLock,
    PublishError,
    Publisher,
    allowed_artifact_paths,
)
from scripts.github_pr import PullRequestError
from scripts.security_check import SecurityError


def run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class LocalPullRequests:
    """Exercise real Git branches and squash merges against a local bare remote."""
    def __init__(self, seed: Path, remote: Path):
        self.seed, self.remote = seed, remote
        self.pending = None
        self.created = 0
        self.fail_merge = False

    def find(self, _head):
        return self.pending

    def validate(self, _pr, _allowed):
        pass

    def create(self, head, _title):
        self.created += 1
        self.pending = {"number": self.created, "url": "https://github.com/example/blog/pull/1",
                        "headRefName": head, "headRefOid": run_git(self.remote, "rev-parse", f"refs/heads/{head}")}
        return self.pending

    def wait_for_merge(self, pr, allowed, **_kwargs):
        if self.fail_merge:
            raise PullRequestError(f"PR still pending: {pr['url']}")
        run_git(self.seed, "fetch", "origin", "main")
        run_git(self.seed, "checkout", "main")
        run_git(self.seed, "merge", "--ff-only", "origin/main")
        run_git(self.seed, "fetch", "origin", pr["headRefName"])
        run_git(self.seed, "merge", "--squash", "FETCH_HEAD")
        run_git(self.seed, "commit", "-m", "Merge daily PR")
        run_git(self.seed, "push", "origin", "main")
        merged = run_git(self.seed, "rev-parse", "HEAD")
        self.pending = None
        return merged


class AtomicRunLockTest(unittest.TestCase):
    def test_prevents_two_publishers_for_the_same_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            first = AtomicRunLock(repo)
            second = AtomicRunLock(repo)

            with first:
                with self.assertRaises(PublishError):
                    with second:
                        pass

    def test_recovers_a_stale_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = AtomicRunLock(Path(directory), stale_after=1)
            lock.path.write_text("999999 0\n", encoding="utf-8")
            old = time.time() - 10
            lock.path.touch()
            import os

            os.utime(lock.path, (old, old))

            with lock:
                self.assertTrue(lock.path.exists())

            self.assertFalse(lock.path.exists())

    def test_linked_worktrees_share_one_repository_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            linked = root / "linked"
            repo.mkdir()
            run_git(repo, "init")
            run_git(repo, "config", "user.name", "AI Daily Test")
            run_git(repo, "config", "user.email", "ai-daily@example.com")
            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            run_git(repo, "add", "README.md")
            run_git(repo, "commit", "-m", "seed")
            run_git(repo, "worktree", "add", "-b", "linked", str(linked))

            first = AtomicRunLock(repo)
            second = AtomicRunLock(linked)

            self.assertEqual(first.path, second.path)
            with first:
                with self.assertRaises(PublishError):
                    with second:
                        pass

            run_git(repo, "worktree", "remove", "--force", str(linked))


class ArtifactContractTest(unittest.TestCase):
    def test_allowed_artifacts_include_only_report_and_derived_data(self):
        self.assertEqual(
            allowed_artifact_paths("2026-07-01"),
            {
                "src/content/ai-daily/2026-07-01.md",
                "public/ai-daily.xml",
                "src/data/ai-trends.json",
                "src/data/ai-opportunities.json",
            },
        )


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.remote = root / "remote.git"
        self.seed = root / "seed"
        self.checkout = root / "checkout"

        run_git(root, "init", "--bare", str(self.remote))
        run_git(root, "clone", str(self.remote), str(self.seed))
        run_git(self.seed, "config", "user.name", "AI Daily Test")
        run_git(self.seed, "config", "user.email", "ai-daily@example.com")
        (self.seed / "scripts").mkdir()
        (self.seed / "src" / "content" / "ai-daily").mkdir(parents=True)
        (self.seed / "src" / "data").mkdir(parents=True)
        (self.seed / "public").mkdir()
        (self.seed / "scripts" / "generate-ai-daily.py").write_text(
            "# test fixture\n",
            encoding="utf-8",
        )
        (self.seed / "README.md").write_text("main\n", encoding="utf-8")
        (self.seed / "src" / "data" / "ai-trends.json").write_text(
            '{"windows":[]}\n',
            encoding="utf-8",
        )
        (self.seed / "src" / "data" / "ai-opportunities.json").write_text(
            '{"schemaVersion":2,"opportunities":[]}\n', encoding="utf-8",
        )
        run_git(self.seed, "add", ".")
        run_git(self.seed, "commit", "-m", "seed")
        run_git(self.seed, "branch", "-M", "main")
        run_git(self.seed, "push", "-u", "origin", "main")
        run_git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")

        run_git(root, "clone", str(self.remote), str(self.checkout))
        run_git(self.checkout, "config", "user.name", "AI Daily Test")
        run_git(self.checkout, "config", "user.email", "ai-daily@example.com")
        run_git(self.checkout, "switch", "-c", "feature")
        (self.checkout / "feature-only.txt").write_text(
            "must never reach main\n",
            encoding="utf-8",
        )
        run_git(self.checkout, "add", "feature-only.txt")
        run_git(self.checkout, "commit", "-m", "feature work")

        self.live_checks = []
        self.pull_requests = LocalPullRequests(self.seed, self.remote)
        self.publisher = Publisher(
            self.checkout,
            live_check=lambda date: self.live_checks.append(date) or True,
            verify_timeout=0,
            pull_requests=self.pull_requests,
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def generate_valid(worktree: Path, date: str) -> None:
        report = worktree / "src" / "content" / "ai-daily" / f"{date}.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(f"# AI Daily {date}\n", encoding="utf-8")
        (worktree / "public").mkdir(parents=True, exist_ok=True)
        (worktree / "public" / "ai-daily.xml").write_text(
            f"<rss>{date}</rss>\n",
            encoding="utf-8",
        )
        (worktree / "src" / "data" / "ai-trends.json").write_text(
            '{"windows":[{"window":"week"}]}\n',
            encoding="utf-8",
        )
        (worktree / "src" / "data" / "ai-opportunities.json").write_text(
            '{"schemaVersion":2,"opportunities":[{"id":"checked-opportunity"}]}\n', encoding="utf-8",
        )

    def test_publishes_from_origin_main_without_feature_commits(self):
        result = self.publisher.publish("2026-07-01", generate=self.generate_valid)

        run_git(self.seed, "fetch", "origin", "main")
        remote_files = run_git(
            self.seed,
            "ls-tree",
            "-r",
            "--name-only",
            "origin/main",
        ).splitlines()

        self.assertEqual(result.status, "published")
        self.assertIn("src/content/ai-daily/2026-07-01.md", remote_files)
        self.assertIn("public/ai-daily.xml", remote_files)
        self.assertNotIn("feature-only.txt", remote_files)
        self.assertEqual(
            run_git(self.remote, "rev-parse", "refs/heads/main"),
            result.commit_sha,
        )
        self.assertEqual(self.live_checks, ["2026-07-01"])

    def test_rejects_unexpected_generated_files_before_push(self):
        before = run_git(self.remote, "rev-parse", "refs/heads/main")

        def generate_unexpected(worktree: Path, date: str) -> None:
            self.generate_valid(worktree, date)
            (worktree / "unexpected.txt").write_text("no\n", encoding="utf-8")

        with self.assertRaisesRegex(PublishError, "unexpected.txt"):
            self.publisher.publish("2026-07-01", generate=generate_unexpected)

        self.assertEqual(
            run_git(self.remote, "rev-parse", "refs/heads/main"),
            before,
        )

    def test_rerun_verifies_remote_and_live_state(self):
        first = self.publisher.publish("2026-07-01", generate=self.generate_valid)
        second = self.publisher.publish("2026-07-01", generate=self.generate_valid)

        self.assertEqual(first.status, "published")
        self.assertEqual(second.status, "already-published")
        self.assertEqual(second.commit_sha, first.commit_sha)
        self.assertEqual(self.live_checks, ["2026-07-01", "2026-07-01"])

    def test_retries_once_when_remote_main_advances_during_generation(self):
        advanced = False

        def generate_with_concurrent_push(worktree: Path, date: str) -> None:
            nonlocal advanced
            self.generate_valid(worktree, date)
            if advanced:
                return
            advanced = True
            (self.seed / "concurrent.txt").write_text("keep me\n", encoding="utf-8")
            run_git(self.seed, "add", "concurrent.txt")
            run_git(self.seed, "commit", "-m", "concurrent update")
            run_git(self.seed, "push", "origin", "main")

        result = self.publisher.publish(
            "2026-07-01",
            generate=generate_with_concurrent_push,
        )

        run_git(self.seed, "fetch", "origin", "main")
        remote_files = run_git(
            self.seed,
            "ls-tree",
            "-r",
            "--name-only",
            "origin/main",
        ).splitlines()
        self.assertEqual(result.status, "published")
        self.assertIn("concurrent.txt", remote_files)
        self.assertIn("src/content/ai-daily/2026-07-01.md", remote_files)

    def test_pending_pr_is_resumed_without_regeneration(self):
        before = run_git(self.remote, "rev-parse", "refs/heads/main")
        self.pull_requests.fail_merge = True
        with self.assertRaises(PullRequestError):
            self.publisher.publish("2026-07-01", generate=self.generate_valid)
        self.assertEqual(before, run_git(self.remote, "rev-parse", "refs/heads/main"))
        self.pull_requests.fail_merge = False
        generator = Mock(side_effect=AssertionError("must reuse the pending PR"))
        result = self.publisher.publish("2026-07-01", generate=generator)
        self.assertEqual(result.status, "published")
        self.assertEqual(self.pull_requests.created, 1)
        generator.assert_not_called()

    def test_secret_failure_never_pushes_a_branch(self):
        self.publisher.security_check = Mock(side_effect=SecurityError("synthetic credential detected"))
        before = run_git(self.remote, "show-ref")
        with self.assertRaises(SecurityError):
            self.publisher.publish("2026-07-01", generate=self.generate_valid)
        self.assertEqual(before, run_git(self.remote, "show-ref"))
        self.assertEqual(self.pull_requests.created, 0)

    def test_failed_checks_do_not_report_publication_or_verify_live(self):
        self.pull_requests.fail_merge = True
        with self.assertRaises(PullRequestError):
            self.publisher.publish("2026-07-01", generate=self.generate_valid)
        self.assertEqual(self.live_checks, [])

    def test_branch_is_recovered_if_pr_creation_failed_after_push(self):
        original = self.pull_requests.create
        self.pull_requests.create = Mock(side_effect=PullRequestError("temporary GitHub failure"))
        with self.assertRaises(PullRequestError):
            self.publisher.publish("2026-07-01", generate=self.generate_valid)
        self.pull_requests.create = original
        generator = Mock(side_effect=AssertionError("must not regenerate"))
        result = self.publisher.publish("2026-07-01", generate=generator)
        self.assertEqual(result.status, "published")
        generator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
