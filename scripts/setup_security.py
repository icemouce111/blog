"""Install local commit protection; scanner installation is explicit and verified."""
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=ROOT, check=True)
    if os.name == "posix":
        (ROOT / ".githooks/pre-commit").chmod(0o755)
        for name in ["scripts/.env", "scripts/dc-config.env"]:
            path = ROOT / name
            if path.exists() and not path.is_symlink():
                path.chmod(0o600)
    print("Local commit scanning configured. Install scanner: npm run security:install")


if __name__ == "__main__":
    main()
