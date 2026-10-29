"""GitHub PR transport. No privileged workflows, admin merge, or bypass path."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

try:
    from scripts.security_config import redact
except ModuleNotFoundError:
    from security_config import redact


class PullRequestError(RuntimeError):
    pass


class GitHubPullRequests:
    def __init__(self, root: Path, base: str = "main"):
        self.root = root
        self.base = base
        self.repo = self._run("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()
        self.login = self._run("api", "user", "--jq", ".login").strip()

    def _run(self, *args: str) -> str:
        try:
            result = subprocess.run(["gh", *args], cwd=self.root, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            raise PullRequestError("GitHub CLI unavailable or timed out") from None
        if result.returncode:
            raise PullRequestError(redact(result.stderr.strip()) or "GitHub request failed")
        return result.stdout

    def find(self, head: str):
        pages = json.loads(self._run("api", "--paginate", "--slurp",
                           f"repos/{self.repo}/pulls?state=open&base={self.base}&per_page=100"))
        entries = [pr for page in pages for pr in page
                   if pr["head"]["ref"] == head or pr["head"]["ref"].startswith(head + "-")]
        if len(entries) > 1:
            raise PullRequestError("Multiple pending PRs for this report; resolve them before publishing")
        return self.get(entries[0]["number"]) if entries else None

    def get(self, number: int):
        return json.loads(self._run("pr", "view", str(number), "--repo", self.repo, "--json",
            "number,url,state,headRefName,headRefOid,baseRefName,isCrossRepository,author,files,mergeable,statusCheckRollup,mergeCommit"))

    def validate(self, pr, allowed: set[str]) -> None:
        if pr["isCrossRepository"] or pr["author"]["login"].lower() != self.login.lower() or pr["baseRefName"] != self.base:
            raise PullRequestError("Refusing a PR not owned by this trusted publisher")
        # gh's files field is limited. A separate paginated request is needed to
        # ensure a truncated response cannot hide changes beyond the allowlist.
        files = json.loads(self._run("api", "--paginate", "--slurp",
                          f"repos/{self.repo}/pulls/{pr['number']}/files?per_page=100"))
        changed = {item["filename"] for page in files for item in page}
        changed.update(item["previous_filename"] for page in files for item in page if "previous_filename" in item)
        if not changed or changed - allowed:
            raise PullRequestError("PR contains files outside the daily artifact allowlist")

    def create(self, head: str, title: str):
        self._run("pr", "create", "--repo", self.repo, "--base", self.base, "--head", head,
                  "--title", title, "--body", "Automated daily artifacts. Secret scanning, tests and build must pass before merge.")
        return self.find(head)

    def wait_for_merge(self, pr, allowed: set[str], *, timeout: int = 600, interval: int = 10):
        deadline = time.monotonic() + timeout
        expected = pr["headRefOid"]
        requested = False
        while True:
            current = self.get(pr["number"])
            self.validate(current, allowed)
            if current["headRefOid"] != expected:
                raise PullRequestError(f"PR head changed unexpectedly; review required: {pr['url']}")
            if current["state"] == "MERGED":
                return current["mergeCommit"]["oid"]
            if current["state"] != "OPEN":
                raise PullRequestError(f"PR closed without merging: {pr['url']}")
            if current["mergeable"] == "CONFLICTING":
                raise PullRequestError(f"PR has conflicts; no automatic overwrite: {pr['url']}")
            checks = {item.get("name") or item.get("context"): item
                      for item in current.get("statusCheckRollup") or []}
            failed = [name for name, item in checks.items() if item.get("conclusion") in
                      {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
                      or item.get("state") in {"FAILURE", "ERROR"}]
            if failed:
                raise PullRequestError(f"PR checks failed ({', '.join(failed)}): {pr['url']}")
            ready = all(checks.get(name, {}).get("conclusion") == "SUCCESS"
                        for name in ("security", "tests", "build"))
            if ready and not requested:
                # Merge only this head now. Leaving server-side auto-merge
                # armed could authorize a later, unscanned head after we exit.
                self._run("pr", "merge", str(pr["number"]), "--repo", self.repo, "--squash",
                          "--match-head-commit", expected)
                requested = True
            if time.monotonic() >= deadline:
                raise PullRequestError(f"PR still pending after {timeout}s; rerun to resume: {pr['url']}")
            time.sleep(interval)
