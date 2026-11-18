#!/bin/sh
# Installs scrcpy-autolaunch with uv (installing uv first if needed, after asking).
# Usage: sh scripts/install.sh [path or git URL]
set -eu

SOURCE="${1:-}"
if [ -z "$SOURCE" ]; then
    REPO="$(cd "$(dirname "$0")/.." && pwd)"
    if [ -f "$REPO/pyproject.toml" ]; then SOURCE="$REPO"
    else SOURCE="git+https://github.com/3sztof/scrcpy-autolaunch"; fi
fi

UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
    echo "uv (https://docs.astral.sh/uv/) is required but not installed."
    echo "It would be installed with the official installer:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "(installs to ~/.local/bin and may add it to your shell profile)"
    printf "Install uv now? [y/N] "
    read -r answer
    case "$answer" in [yY]*) ;; *) echo "Aborted: uv is required."; exit 1 ;; esac
    curl -LsSf https://astral.sh/uv/install.sh | sh
    UV="$HOME/.local/bin/uv"
    [ -x "$UV" ] || { echo "uv was installed, but not found at $UV. Open a new shell and run this again."; exit 1; }
fi

BIN="$("$UV" tool dir --bin)"
APP="$BIN/scrcpy-autolaunch"

[ -x "$APP" ] && "$APP" stop || true

echo "Installing scrcpy-autolaunch from $SOURCE ..."
"$UV" tool install --force --reinstall "$SOURCE"

echo
"$APP" doctor || true
echo
"$APP" install

case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo; echo "Note: $BIN is not on your PATH. Run 'uv tool update-shell' to use 'scrcpy-autolaunch' directly." ;;
esac
