"""Branch-safe publication orchestration for AI Daily."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from scripts.github_pr import GitHubPullRequests
    from scripts.security_check import scan_files
    from scripts.security_config import load_private_config, redact
except ModuleNotFoundError:
    from github_pr import GitHubPullRequests
    from security_check import scan_files
    from security_config import load_private_config, redact


LIVE_RSS_URL = "https://blog.icemouce.cc/ai-daily.xml"


class PublishError(RuntimeError):
    """Raised when generation or publication cannot be verified."""


@dataclass(frozen=True)
class PublishResult:
    status: str
    commit_sha: str
    pr_url: str | None = None


def allowed_artifact_paths(date: str) -> set[str]:
    return {
        f"src/content/ai-daily/{date}.md",
        "public/ai-daily.xml",
        "src/data/ai-trends.json",
        "src/data/ai-opportunities.json",
    }


def _run(
    cwd: Path,
    *args: str,
    check: bool = True,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(redact(f"{' '.join(args)} failed: {detail}"))
    return result


class AtomicRunLock:
    """Cross-platform process lock stored outside the repository."""

    def __init__(self, repo_root: Path, stale_after: int = 6 * 60 * 60):
        self.repo_root = Path(repo_root).resolve()
        self.stale_after = stale_after
        identity = self._repository_identity()
        digest = hashlib.sha256(str(identity).encode()).hexdigest()[:16]
        self.path = Path(tempfile.gettempdir()) / f"ai-daily-{digest}.lock"
        self._owned = False

    def _repository_identity(self) -> Path:
        result = _run(
            self.repo_root,
            "git",
            "rev-parse",
            "--git-common-dir",
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return self.repo_root
        common = Path(result.stdout.strip())
        if not common.is_absolute():
            common = self.repo_root / common
        return common.resolve()

    def __enter__(self) -> "AtomicRunLock":
        self._acquire()
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self._owned:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._owned = False

    def _acquire(self) -> None:
        for attempt in range(2):
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                if attempt == 0 and self._is_stale():
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                raise PublishError(
                    f"another AI Daily run is active ({self.path})"
                )
            with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
                lock_file.write(f"{os.getpid()} {int(time.time())}\n")
            self._owned = True
            return
        raise PublishError(f"unable to acquire AI Daily lock ({self.path})")

    def _is_stale(self) -> bool:
        try:
            return time.time() - self.path.stat().st_mtime > self.stale_after
        except FileNotFoundError:
            return False


class Publisher:
    def __init__(
        self,
        repo_root: Path,
        *,
        remote: str = "origin",
        branch: str = "main",
        live_check: Callable[[str], bool] | None = None,
        verify_timeout: int = 600,
        poll_interval: int = 10,
        artifacts: Callable[[str], set[str]] | None = None,
        commit_message: Callable[[str], str] | None = None,
        remote_artifact: Callable[[str], str] | None = None,
        live_url: str | None = LIVE_RSS_URL,
        publication_key: str = "ai-daily",
        pull_requests=None,
        security_check: Callable = scan_files,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.remote = remote
        self.branch = branch
        self.live_url = live_url
        self.live_check = live_check or self._build_live_check(live_url)
        self.verify_timeout = verify_timeout
        self.poll_interval = poll_interval
        self.artifacts = artifacts or allowed_artifact_paths
        self.commit_message = commit_message or (
            lambda date: f"chore: add AI daily report for {date}"
        )
        self.remote_artifact = remote_artifact or (
            lambda date: f"src/content/ai-daily/{date}.md"
        )
        self.publication_key = publication_key
        self.pull_requests = pull_requests
        self.security_check = security_check

    def publish(
        self,
        date: str,
        *,
        force: bool = False,
        generate: Callable[[Path, str], None] | None = None,
    ) -> PublishResult:
        from datetime import date as calendar_date
        if calendar_date.fromisoformat(date).isoformat() != date:
            raise PublishError("Date must be YYYY-MM-DD")
        load_private_config(self.repo_root)
        with AtomicRunLock(self.repo_root):
            return self._publish_attempt(date, generate, force)

    def _publish_attempt(
        self,
        date: str,
        generate: Callable[[Path, str], None] | None,
        force: bool,
    ) -> PublishResult:
        _run(
            self.repo_root,
            "git",
            "fetch",
            self.remote,
            self.branch,
            "--prune",
        )
        base_ref = f"{self.remote}/{self.branch}"
        client = self.pull_requests or GitHubPullRequests(self.repo_root, self.branch)
        head = f"codex/{self.publication_key}-{date}"
        allowed = self.artifacts(date)
        existing = client.find(head)
        recover_branch = False
        if existing:
            head = existing["headRefName"]
            client.validate(existing, allowed)
            # Scan the actual remote head before resuming, never overwrite a
            # pending branch or regenerate a potentially costly daily report.
            _run(self.repo_root, "git", "fetch", self.remote, head)
            fetched_head = _run(self.repo_root, "git", "rev-parse", "FETCH_HEAD").stdout.strip()
            if fetched_head != existing["headRefOid"]:
                raise PublishError("Remote PR head changed during verification")
            if force:
                raise PublishError(f"Close the pending PR before forcing regeneration: {existing['url']}")
        else:
            remote_head = _run(self.repo_root, "git", "ls-remote", "--heads", self.remote,
                               f"refs/heads/{head}").stdout.strip()
            if remote_head and force:
                # A previously closed/merged PR may leave its branch behind.
                # A fresh branch avoids force-pushing or deleting reviewed work.
                head = f"{head}-{uuid.uuid4().hex[:8]}"
            elif remote_head:
                _run(self.repo_root, "git", "fetch", self.remote, head)
                fetched_head = _run(self.repo_root, "git", "rev-parse", "FETCH_HEAD").stdout.strip()
                same_report = _run(self.repo_root, "git", "diff", "--quiet", base_ref,
                                   fetched_head, "--", self.remote_artifact(date), check=False)
                if same_report.returncode == 0:
                    # Squash merges need not remove their old source branch.
                    # Work from main and use a fresh name only if new changes
                    # are actually generated; do not publish the old PR again.
                    head = f"{head}-{uuid.uuid4().hex[:8]}"
                elif same_report.returncode == 1:
                    changed = set(_run(self.repo_root, "git", "diff", "--name-only",
                                       f"{base_ref}...{fetched_head}").stdout.splitlines())
                    if not changed or changed - allowed:
                        raise PublishError("Existing daily branch is not a recoverable artifact-only change")
                    recover_branch = True
                else:
                    raise PublishError("Unable to inspect existing daily branch")
        workspace = Path(tempfile.mkdtemp(prefix="ai-daily-worktree-"))
        worktree_added = False
        try:
            _run(
                self.repo_root,
                "git",
                "worktree",
                "add",
                "--detach",
                str(workspace),
                fetched_head if existing or recover_branch else base_ref,
            )
            worktree_added = True
            if existing or recover_branch:
                self.security_check(workspace, allowed)
                if not existing:
                    existing = client.create(head, self.commit_message(date))
                if not existing or existing["headRefOid"] != fetched_head:
                    raise PublishError("Recovered PR does not match the scanned branch")
                client.validate(existing, allowed)
                merged = client.wait_for_merge(existing, allowed, timeout=self.verify_timeout, interval=self.poll_interval)
                self._verify_merged(merged, date)
                return PublishResult("published", merged, existing["url"])
            if generate is None:
                self._run_generator(workspace, date, force=force)
            else:
                generate(workspace, date)

            changed = self._changed_paths(workspace)
            unexpected = changed - allowed
            if unexpected:
                raise PublishError(
                    "generator changed unexpected files: "
                    + ", ".join(sorted(unexpected))
                )

            if not changed:
                remote_sha = self._remote_sha()
                self.security_check(workspace, allowed)
                self._require_remote_artifact(date)
                self._verify_live(date)
                return PublishResult("already-published", remote_sha)

            artifact_paths = sorted(allowed)
            self.security_check(workspace, artifact_paths)
            _run(workspace, "git", "add", "--", *artifact_paths)
            staged = set(
                filter(
                    None,
                    _run(
                        workspace,
                        "git",
                        "diff",
                        "--cached",
                        "--name-only",
                    ).stdout.splitlines(),
                )
            )
            if not staged:
                raise PublishError("generator produced no stageable artifacts")
            if staged - allowed:
                raise PublishError(
                    "staged unexpected files: "
                    + ", ".join(sorted(staged - allowed))
                )

            _run(
                workspace,
                "git",
                "commit",
                "-m",
                self.commit_message(date),
            )
            commit_sha = _run(workspace, "git", "rev-parse", "HEAD").stdout.strip()
            _run(
                workspace,
                "git",
                "push",
                self.remote,
                f"HEAD:refs/heads/{head}",
                timeout=180,
            )
            pr = client.create(head, self.commit_message(date))
            if not pr or pr["headRefOid"] != commit_sha:
                raise PublishError("PR head does not match the scanned commit")
            client.validate(pr, allowed)
            merged = client.wait_for_merge(pr, allowed, timeout=self.verify_timeout, interval=self.poll_interval)
            self._verify_merged(merged, date)
            return PublishResult("published", merged, pr["url"])
        finally:
            if worktree_added:
                _run(
                    self.repo_root,
                    "git",
                    "worktree",
                    "remove",
                    "--force",
                    str(workspace),
                    check=False,
                )
            shutil.rmtree(workspace, ignore_errors=True)

    def _verify_merged(self, commit_sha: str, date: str) -> None:
        _run(self.repo_root, "git", "fetch", self.remote, self.branch)
        result = _run(self.repo_root, "git", "merge-base", "--is-ancestor", commit_sha,
                      f"{self.remote}/{self.branch}", check=False)
        if result.returncode:
            raise PublishError("Merged commit was not found on the remote production branch")
        self._require_remote_artifact(date)
        self._verify_live(date)

    def _run_generator(
        self,
        worktree: Path,
        date: str,
        *,
        force: bool = False,
    ) -> None:
        command = [
            sys.executable,
            str(worktree / "scripts" / "generate-ai-daily.py"),
            "--generate-only",
            "--date",
            date,
        ]
        if force:
            command.append("--force")
        result = _run(
            worktree,
            *command,
            timeout=15 * 60,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise PublishError(f"AI Daily generation failed: {detail}")

    @staticmethod
    def _changed_paths(worktree: Path) -> set[str]:
        output = _run(
            worktree,
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout
        changed: set[str] = set()
        for line in output.splitlines():
            if len(line) < 4:
                continue
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.add(path)
        return changed

    def _remote_sha(self) -> str:
        result = _run(
            self.repo_root,
            "git",
            "ls-remote",
            self.remote,
            f"refs/heads/{self.branch}",
        )
        line = result.stdout.strip()
        if not line:
            raise PublishError(f"remote branch {self.branch} does not exist")
        return line.split()[0]

    def _require_remote_artifact(self, date: str) -> None:
        artifact = self.remote_artifact(date)
        result = _run(
            self.repo_root,
            "git",
            "show",
            f"{self.remote}/{self.branch}:{artifact}",
            check=False,
        )
        if result.returncode != 0:
            raise PublishError(
                f"artifact {artifact} is not present on remote {self.branch}"
            )

    def _verify_live(self, date: str) -> None:
        deadline = time.monotonic() + self.verify_timeout
        while True:
            if self.live_check(date):
                return
            if time.monotonic() >= deadline:
                raise PublishError(
                    f"remote push succeeded but live RSS does not contain {date}"
                )
            time.sleep(self.poll_interval)

    @staticmethod
    def _build_live_check(live_url: str | None) -> Callable[[str], bool]:
        if live_url is None:
            return lambda _date: True

        def check(date: str) -> bool:
            try:
                request = urllib.request.Request(
                    live_url,
                    headers={"User-Agent": "ai-daily-sop/1.0"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    return date in response.read().decode("utf-8", errors="replace")
            except Exception:
                return False

        return check


def publish(repo_root: Path, date: str, *, force: bool = False) -> PublishResult:
    return Publisher(repo_root).publish(date, force=force)
