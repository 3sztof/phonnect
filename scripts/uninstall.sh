#!/bin/sh
# Phonnect uninstaller for macOS and Linux.
#
#   curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/uninstall.sh | sh
#
# Options (after `sh -s --` when piped):
#   --purge     also delete settings, logs and remembered phones (otherwise it asks)
#   --keep      keep settings, logs and remembered phones (otherwise it asks)
#   --yes, -y   answer yes to every question
#
# Removes only what the installer added. uv, scrcpy and adb stay; see the end of the output for how to remove them.
set -eu

PURGE=""
YES="${PHONNECT_YES:-0}"
while [ $# -gt 0 ]; do
    case "$1" in
        --purge) PURGE=1; shift ;;
        --keep) PURGE=0; shift ;;
        --yes|-y) YES=1; shift ;;
        -h|--help) echo "Usage: uninstall.sh [--purge | --keep] [--yes]"; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -t 1 ]; then
    B="$(printf '\033[1m')" G="$(printf '\033[32m')" Y="$(printf '\033[33m')" R="$(printf '\033[31m')" N="$(printf '\033[0m')"
else
    B="" G="" Y="" R="" N=""
fi
step() { printf '\n%s==> %s%s\n' "$B" "$1" "$N"; }
ok() { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
fail() { printf '\n%sError:%s %s\n' "$R" "$N" "$1" >&2; exit 1; }
row() { printf '  %-16s %s\n' "$1" "$2"; }
tilde() { case "$1" in "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;; *) printf '%s' "$1" ;; esac; }
ask() {
    if [ "$YES" = 1 ]; then [ "$2" = y ]; return; fi
    if [ "$2" = y ]; then hint="[Y/n]"; else hint="[y/N]"; fi
    { true </dev/tty; } 2>/dev/null || fail "No terminal to ask \"$1\". Re-run with --yes (and --purge or --keep)."
    printf '%s %s ' "$1" "$hint"
    read -r answer </dev/tty || answer=""
    case "${answer:-$2}" in [yY]*) return 0 ;; *) return 1 ;; esac
}

find_cmd() {
    command -v "$1" 2>/dev/null && return 0
    for d in "$HOME/.local/bin" "$HOME/.cargo/bin" /opt/homebrew/bin /usr/local/bin; do
        [ -x "$d/$1" ] && { echo "$d/$1"; return 0; }
    done
    return 1
}

UV="$(find_cmd uv || true)"
BIN="$HOME/.local/bin"
TOOLS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/uv/tools"
if [ -n "$UV" ]; then
    BIN="$("$UV" tool dir --bin 2>/dev/null || echo "$BIN")"
    TOOLS_DIR="$("$UV" tool dir 2>/dev/null || echo "$TOOLS_DIR")"
fi
APP="$BIN/phonnect"

if [ "$(uname -s)" = Darwin ]; then
    SETTINGS="$HOME/Library/Application Support/phonnect"
    LOGS="$SETTINGS"
    ENTRIES="$HOME/Library/LaunchAgents/io.github.3sztof.phonnect.plist $HOME/Applications/Phonnect.app"
else
    SETTINGS="${XDG_CONFIG_HOME:-$HOME/.config}/phonnect"
    LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/phonnect"
    ENTRIES="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/phonnect.desktop ${XDG_DATA_HOME:-$HOME/.local/share}/applications/phonnect.desktop"
fi

printf '\n%sPhonnect uninstaller%s\n' "$B" "$N"
step "This will remove"
found=0
if [ -x "$APP" ]; then row "App" "$(tilde "$TOOLS_DIR")/phonnect  (stopped first; phone settings it changed are put back)"; found=1; fi
if [ -x "$APP" ]; then row "Commands" "$(tilde "$BIN")/phonnect, phonnect-tray"; fi
for e in $ENTRIES; do
    if [ -e "$e" ]; then row "Entry" "$(tilde "$e")"; found=1; fi
done
has_data=0
for d in "$SETTINGS" "$LOGS"; do [ -d "$d" ] && has_data=1; done
if [ "$has_data" = 1 ]; then
    row "Settings" "$(tilde "$SETTINGS")  (only if you choose to below)"
    [ "$LOGS" != "$SETTINGS" ] && row "Log" "$(tilde "$LOGS")  (same)"
    found=1
fi
if [ "$found" = 0 ]; then
    echo "  Phonnect isn't installed for this user. Nothing to do."
    exit 0
fi
echo
echo "  Not touched: uv, scrcpy, adb, and anything on your phone."
echo

ask "Uninstall Phonnect?" y || { echo "Nothing changed."; exit 0; }
if [ -z "$PURGE" ] && [ "$has_data" = 1 ]; then
    if ask "Also delete settings, logs and remembered Wi-Fi phones? (keep them to reinstall later)" n; then PURGE=1; else PURGE=0; fi
fi

step "Removing"
if [ -x "$APP" ]; then
    if [ "$PURGE" = 1 ]; then "$APP" uninstall --purge; else "$APP" uninstall; fi
    "$UV" tool uninstall phonnect && ok "Removed the app"
else
    # The app is gone already; clean up what it left.
    for e in $ENTRIES; do [ -e "$e" ] && rm -rf "$e" && ok "Removed $(tilde "$e")"; done
    if [ "$PURGE" = 1 ]; then
        for d in "$SETTINGS" "$LOGS"; do [ -d "$d" ] && rm -rf "$d" && ok "Deleted $(tilde "$d")"; done
    fi
fi
[ "$PURGE" = 1 ] || { [ "$has_data" = 1 ] && ok "Kept your settings in $(tilde "$SETTINGS")"; }

step "Done"
echo "  Phonnect is removed. If you don't need these anymore, remove them too:"
row "uv" "https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
if [ "$(uname -s)" = Darwin ]; then
    row "scrcpy, adb" "brew uninstall scrcpy && brew uninstall --cask android-platform-tools"
else
    row "scrcpy, adb" "with your package manager, e.g. sudo apt remove scrcpy adb"
fi
