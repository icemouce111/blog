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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


LIVE_RSS_URL = "https://blog.icemouce.cc/ai-daily.xml"


class PublishError(RuntimeError):
    """Raised when generation or publication cannot be verified."""


@dataclass(frozen=True)
class PublishResult:
    status: str
    commit_sha: str


def allowed_artifact_paths(date: str) -> set[str]:
    return {
        f"src/content/ai-daily/{date}.md",
        "public/ai-daily.xml",
        "src/data/ai-trends.json",
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
        raise PublishError(f"{' '.join(args)} failed: {detail}")
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
    ):
        self.repo_root = Path(repo_root).resolve()
        self.remote = remote
        self.branch = branch
        self.live_check = live_check or self._default_live_check
        self.verify_timeout = verify_timeout
        self.poll_interval = poll_interval

    def publish(
        self,
        date: str,
        *,
        force: bool = False,
        generate: Callable[[Path, str], None] | None = None,
    ) -> PublishResult:
        with AtomicRunLock(self.repo_root):
            for attempt in range(2):
                try:
                    return self._publish_attempt(date, generate, force)
                except PublishError as error:
                    if attempt == 0 and self._is_non_fast_forward(error):
                        continue
                    raise
        raise PublishError("AI Daily publication retry exhausted")

    @staticmethod
    def _is_non_fast_forward(error: PublishError) -> bool:
        message = str(error).lower()
        return "git push" in message and any(
            marker in message
            for marker in ("non-fast-forward", "fetch first", "[rejected]")
        )

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
                base_ref,
            )
            worktree_added = True
            if generate is None:
                self._run_generator(workspace, date, force=force)
            else:
                generate(workspace, date)

            changed = self._changed_paths(workspace)
            unexpected = changed - allowed_artifact_paths(date)
            if unexpected:
                raise PublishError(
                    "generator changed unexpected files: "
                    + ", ".join(sorted(unexpected))
                )

            if not changed:
                remote_sha = self._remote_sha()
                self._require_remote_report(date)
                self._verify_live(date)
                return PublishResult("already-published", remote_sha)

            artifact_paths = sorted(allowed_artifact_paths(date))
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
            if staged - allowed_artifact_paths(date):
                raise PublishError(
                    "staged unexpected files: "
                    + ", ".join(sorted(staged - allowed_artifact_paths(date)))
                )

            _run(
                workspace,
                "git",
                "commit",
                "-m",
                f"chore: add AI daily report for {date}",
            )
            commit_sha = _run(workspace, "git", "rev-parse", "HEAD").stdout.strip()
            _run(
                workspace,
                "git",
                "push",
                self.remote,
                f"HEAD:{self.branch}",
                timeout=180,
            )
            remote_sha = self._remote_sha()
            if remote_sha != commit_sha:
                raise PublishError(
                    f"remote {self.branch} is {remote_sha}, expected {commit_sha}"
                )
            self._verify_live(date)
            return PublishResult("published", commit_sha)
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

    def _require_remote_report(self, date: str) -> None:
        result = _run(
            self.repo_root,
            "git",
            "show",
            f"{self.remote}/{self.branch}:src/content/ai-daily/{date}.md",
            check=False,
        )
        if result.returncode != 0:
            raise PublishError(
                f"report {date} is not present on remote {self.branch}"
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
    def _default_live_check(date: str) -> bool:
        try:
            request = urllib.request.Request(
                LIVE_RSS_URL,
                headers={"User-Agent": "ai-daily-sop/1.0"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                return date in response.read().decode("utf-8", errors="replace")
        except Exception:
            return False


def publish(repo_root: Path, date: str, *, force: bool = False) -> PublishResult:
    return Publisher(repo_root).publish(date, force=force)
