"""Cut a release: bump __version__, commit, tag vX.Y.Z and push. CI builds the GitHub Release.

Usage: uv run python scripts/release.py 0.2.0   (or: just release 0.2.0)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT = ROOT / "src" / "phonnect" / "__init__.py"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        print("Usage: release.py X.Y.Z")
        return 2
    version = sys.argv[1]
    tag = f"v{version}"

    if git("status", "--porcelain"):
        print("The working tree has uncommitted changes; commit or stash them first.")
        return 1
    if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        print("Releases are cut from main.")
        return 1
    if tag in git("tag", "--list", tag).splitlines():
        print(f"Tag {tag} already exists.")
        return 1

    text = INIT.read_text(encoding="utf-8")
    current = re.search(r'__version__ = "([^"]+)"', text).group(1)
    if current != version:
        INIT.write_text(text.replace(f'__version__ = "{current}"', f'__version__ = "{version}"'), encoding="utf-8")

    subprocess.run(["uv", "run", "pytest", "-q"], cwd=ROOT, check=True)

    if current != version:
        git("add", str(INIT))
        git("commit", "-m", f"Release {tag}")
    git("tag", "-a", tag, "-m", f"phonnect {version}")
    git("push", "origin", "main")
    git("push", "origin", tag)
    print(f"Pushed {tag}. The Release workflow builds and publishes it:")
    print("  https://github.com/3sztof/phonnect/actions/workflows/release.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
