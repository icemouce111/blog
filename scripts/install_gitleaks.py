"""Install the pinned scanner, verifying the upstream archive checksum."""
from __future__ import annotations

import hashlib
import io
import os
import platform
import tarfile
import subprocess
from pathlib import Path
from urllib.request import urlopen

VERSION = "8.30.1"


def install(destination: Path | None = None) -> Path:
    destination = destination or Path.home() / ".local" / "bin" / "gitleaks"
    if destination.is_file():
        current = subprocess.run([str(destination), "version"], capture_output=True, text=True, timeout=10)
        if current.returncode == 0 and current.stdout.strip().removeprefix("v") == VERSION:
            return destination
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}[platform.system()]
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}[platform.machine()]
    if system == "windows":
        raise RuntimeError("Install the official Windows Gitleaks v8.30.1 binary manually")
    archive = f"gitleaks_{VERSION}_{system}_{arch}.tar.gz"
    base = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}"
    with urlopen(f"{base}/gitleaks_{VERSION}_checksums.txt", timeout=60) as response:
        checksums = {name.lstrip('*'): checksum for checksum, name in (
            line.split() for line in response.read().decode().splitlines() if line.strip()
        )}
    with urlopen(f"{base}/{archive}", timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != checksums[archive]:
        raise RuntimeError("Gitleaks archive checksum mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as bundle:
        binary = bundle.extractfile("gitleaks")
        if binary is None:
            raise RuntimeError("Gitleaks binary missing from archive")
        temporary = destination.with_suffix(".download")
        temporary.write_bytes(binary.read())
    temporary.chmod(0o755)
    os.replace(temporary, destination)
    return destination


if __name__ == "__main__":
    print(f"Installed Gitleaks {VERSION}: {install()}")
