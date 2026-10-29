"""Private process configuration and redacted output shared by both generators."""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Mapping

SENSITIVE_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", re.I)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink():
        raise RuntimeError("Private configuration must not be a symbolic link")
    if os.name == "posix":
        path.chmod(0o600)
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) and value:
            os.environ.setdefault(key, value)


def load_private_config(root: Path) -> None:
    # Existing process variables always win; .env precedes the legacy file.
    for name in (".env", "dc-config.env"):
        load_env_file(root / "scripts" / name)


def secret_values(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    return tuple(sorted({value for key, value in (os.environ if env is None else env).items()
                         if SENSITIVE_NAME.search(key) and len(value) >= 8}, key=len, reverse=True))


def redact(value: object) -> str:
    text = str(value)
    for secret in secret_values():
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(Bearer\s+)[^\s\"'<>]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)([?&](?:[a-z_]*token|api[_-]?key|secret|password|key)=)[^\s&#\"'<>]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?)[^\r\n\"']+", r"\1[REDACTED]", text)
    text = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[REDACTED]@", text)
    return text


def safe_print(*values, **kwargs) -> None:
    print(*(redact(value) for value in values), **kwargs)


def print_error(error: BaseException) -> None:
    safe_print(f"[fail] {type(error).__name__}: {error}", file=sys.stderr)


class RedactingStream:
    def __init__(self, stream):
        self.stream = stream

    def write(self, value):
        self.stream.write(redact(value))
        return len(value)

    def flush(self):
        self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


def protect_output() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        if not isinstance(stream, RedactingStream):
            setattr(sys, name, RedactingStream(stream))
    # Ensure logging handlers created before protection also redact messages.
    class SecretFilter(logging.Filter):
        def filter(self, record):
            record.msg = redact(record.getMessage())
            record.args = ()
            return True
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretFilter())
