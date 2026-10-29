"""Fail-closed secret checks. Findings never include matched source or values."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from scripts.security_config import load_private_config, print_error, redact, secret_values
except ModuleNotFoundError:
    from security_config import load_private_config, print_error, redact, secret_values

VERSION = "8.30.1"


class SecurityError(RuntimeError):
    pass


def scanner() -> str:
    binary = shutil.which("gitleaks") or str(Path.home() / ".local/bin/gitleaks")
    try:
        result = subprocess.run([binary, "version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise SecurityError("Gitleaks unavailable; run python3 scripts/install_gitleaks.py") from None
    if result.returncode or result.stdout.strip().removeprefix("v") != VERSION:
        raise SecurityError(f"Gitleaks {VERSION} is required")
    return binary


def _check_bytes(data: bytes, path: str) -> None:
    for secret in secret_values():
        # Include JSON-escaped values, as generated artifacts may be serialized.
        variants = (secret.encode(), json.dumps(secret, ensure_ascii=True)[1:-1].encode())
        if any(value in data for value in variants):
            raise SecurityError(f"Known private credential in {redact(path)} (value withheld)")


def _scan(target: Path, *, history: bool = False) -> None:
    binary = scanner()
    if history:
        _check_history_credentials(target)
    with tempfile.TemporaryDirectory(prefix="blog-security-") as directory:
        report = Path(directory) / "findings.json"
        report.touch(mode=0o600)
        config = Path(directory) / "scanner.toml"
        config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
        command = [binary, "git" if history else "dir", str(target), "--redact=100",
                   "--no-banner", "--ignore-gitleaks-allow", f"--config={config}",
                   "--report-format=json", f"--report-path={report}"]
        if history:
            command.append("--log-opts=--all")
        env = {key: value for key, value in os.environ.items() if not key.startswith("GITLEAKS_")}
        # An empty trusted working directory prevents the target repository
        # from supplying .gitleaks.toml / .gitleaksignore to weaken the scan.
        result = subprocess.run(command, cwd=directory, env=env, capture_output=True, text=True, timeout=180)
        if result.returncode:
            try:
                findings = json.loads(report.read_text())
            except (OSError, ValueError):
                findings = []
            locations = [f"{redact(item.get('File', '?'))}:{item.get('StartLine', '?')} [{item.get('RuleID', '?')}]"
                         for item in findings[:20]]
            raise SecurityError("Secret scan rejected: " + ("; ".join(locations) or "scanner failed; details withheld"))


def _check_history_credentials(root: Path) -> None:
    if not secret_values():
        return
    objects = subprocess.run(["git", "rev-list", "--objects", "--all"], cwd=root,
                             capture_output=True, check=True).stdout.splitlines()
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        for entry in objects:
            oid, _, name = entry.partition(b" ")
            process.stdin.write(oid + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3:
                raise SecurityError("Unable to inspect Git history object")
            size = int(header[2])
            data = process.stdout.read(size)
            process.stdout.read(1)
            if len(data) != size:
                raise SecurityError("Incomplete Git history object")
            _check_bytes(data, f"history object {oid.decode()} {os.fsdecode(name)}")
    finally:
        process.stdin.close()
        process.stdout.close()
        process.terminate()
        process.wait()


def scan_files(root: Path, paths) -> None:
    root = root.resolve()
    scanner()  # Missing tooling must fail even for an empty file set.
    with tempfile.TemporaryDirectory(prefix="blog-public-artifacts-") as directory:
        destination = Path(directory)
        for name in paths:
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise SecurityError("Refusing a path outside the repository")
            basename = relative.name
            example = basename == ".env.example" or basename.endswith(".env.example")
            if not example and (basename == ".env" or basename.startswith(".env.") or basename.endswith(".env")):
                raise SecurityError(f"Private configuration cannot be published: {redact(relative)}")
            path = root / relative
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise SecurityError(f"Refusing symbolic link or external artifact: {redact(relative)}")
            if not path.exists():
                continue  # Deletions have no bytes to publish.
            if not path.is_file():
                raise SecurityError("Scan inputs must be files")
            data = path.read_bytes()
            _check_bytes(data, str(relative))
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        _scan(destination)


def _git_paths(root: Path, *args: str) -> list[str]:
    result = subprocess.run(["git", *args, "-z"], cwd=root, check=True, capture_output=True)
    return [os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def check_staged(root: Path) -> None:
    names = _git_paths(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    with tempfile.TemporaryDirectory(prefix="blog-staged-") as directory:
        temporary = Path(directory)
        for name in names:
            mode = subprocess.run(["git", "ls-files", "-s", "--", name], cwd=root,
                                  check=True, capture_output=True, text=True).stdout.split()[0]
            if mode not in {"100644", "100755"}:
                raise SecurityError("Refusing staged symlink or gitlink")
            data = subprocess.run(["git", "show", f":{name}"], cwd=root,
                                  check=True, capture_output=True).stdout
            path = temporary / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        scan_files(temporary, names)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("staged", "history", "worktree", "dist", "files"))
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    load_private_config(root)
    if args.mode == "staged":
        check_staged(root)
    elif args.mode == "history":
        _scan(root, history=True)
    elif args.mode == "dist":
        if not (root / "dist").is_dir():
            raise SecurityError("Build output dist is missing")
        scan_files(root, [str(path.relative_to(root)) for path in (root / "dist").rglob("*") if path.is_file()])
    elif args.mode == "worktree":
        scan_files(root, _git_paths(root, "ls-files", "--cached", "--others", "--exclude-standard"))
    else:
        scan_files(root, args.paths)
    print("Security check passed:", args.mode)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print_error(error)
        raise SystemExit(1)
