#!/bin/sh
# Phonnect installer for macOS and Linux.
#
#   curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/install.sh | sh
#
# Options (after `sh -s --` when piped, e.g. `... | sh -s -- --yes`):
#   --version X.Y.Z   install that release instead of the latest
#   --source PATH|URL install from a local checkout, wheel or git URL (developers)
#   --update          only replace the app; keep start-at-login and settings as they are
#   --no-deps         don't offer to install scrcpy / adb
#   --yes, -y         answer yes to every question (unattended installs)
#
# Everything goes into your user account; nothing here needs admin rights, except
# installing scrcpy / adb with your package manager, which it asks about first.
# Remove it again with:
#   curl -fsSL https://github.com/3sztof/phonnect/releases/latest/download/uninstall.sh | sh
set -eu

REPO="3sztof/phonnect"
# Set by the release workflow, so each release's script installs that release.
DEFAULT_VERSION=""
RELEASES="https://github.com/$REPO/releases"
UNINSTALL_CMD="curl -fsSL $RELEASES/latest/download/uninstall.sh | sh"

VERSION="${PHONNECT_VERSION:-$DEFAULT_VERSION}"
SOURCE=""
UPDATE=0
DEPS=1
YES="${PHONNECT_YES:-0}"

usage() {
    cat <<EOF
Phonnect installer for macOS and Linux.

  curl -fsSL $RELEASES/latest/download/install.sh | sh -s -- [options]

  --version X.Y.Z    install that release instead of the latest
  --source PATH|URL  install from a local checkout, wheel or git URL (developers)
  --update           only replace the app; keep start-at-login and settings as they are
  --no-deps          don't offer to install scrcpy / adb
  --yes, -y          answer yes to every question (unattended installs)
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --version) VERSION="${2:?--version needs a value}"; shift 2 ;;
        --version=*) VERSION="${1#*=}"; shift ;;
        --source) SOURCE="${2:?--source needs a value}"; shift 2 ;;
        --source=*) SOURCE="${1#*=}"; shift ;;
        --update) UPDATE=1; shift ;;
        --no-deps) DEPS=0; shift ;;
        --yes|-y) YES=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1 (see --help)"; exit 1 ;;
    esac
done
VERSION="${VERSION#v}"

# ── output helpers ───────────────────────────────────────────────────────────

if [ -t 1 ]; then
    B="$(printf '\033[1m')" DIM="$(printf '\033[2m')" G="$(printf '\033[32m')" Y="$(printf '\033[33m')" R="$(printf '\033[31m')" N="$(printf '\033[0m')"
else
    B="" DIM="" G="" Y="" R="" N=""
fi
step() { printf '\n%s==> %s%s\n' "$B" "$1" "$N"; }
ok() { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$1"; }
fail() { printf '\n%sError:%s %s\n' "$R" "$N" "$1" >&2; exit 1; }
row() { printf '  %-16s %s\n' "$1" "$2"; }

# ask "Question" default(y|n): reads the answer from the terminal, also when this
# script itself arrives through a pipe (curl ... | sh).
ask() {
    if [ "$YES" = 1 ]; then return 0; fi
    if [ "$2" = y ]; then hint="[Y/n]"; else hint="[y/N]"; fi
    if ! { true </dev/tty; } 2>/dev/null; then
        fail "No terminal to ask \"$1\". Re-run with --yes to accept everything."
    fi
    printf '%s %s ' "$1" "$hint"
    read -r answer </dev/tty || answer=""
    case "${answer:-$2}" in [yY]*) return 0 ;; *) return 1 ;; esac
}

tilde() { case "$1" in "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;; *) printf '%s' "$1" ;; esac; }

# ── what's here already ──────────────────────────────────────────────────────

OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM=macOS ;;
    Linux) PLATFORM=Linux ;;
    *) fail "This installer is for macOS and Linux. On Windows, run in PowerShell:
  irm $RELEASES/latest/download/install.ps1 | iex" ;;
esac

find_cmd() {
    # PATH first, then where installers usually put things (PATH may be minimal).
    command -v "$1" 2>/dev/null && return 0
    for d in "$HOME/.local/bin" "$HOME/.cargo/bin" /opt/homebrew/bin /usr/local/bin /usr/bin /snap/bin \
        "$HOME/Library/Android/sdk/platform-tools" "$HOME/Android/Sdk/platform-tools"; do
        [ -x "$d/$1" ] && { echo "$d/$1"; return 0; }
    done
    return 1
}

UV="$(find_cmd uv || true)"
SCRCPY="$(find_cmd scrcpy || true)"
ADB="$(find_cmd adb || true)"

if [ -n "$UV" ]; then
    TOOLS_DIR="$("$UV" tool dir 2>/dev/null || true)"
    BIN="$("$UV" tool dir --bin 2>/dev/null || true)"
fi
TOOLS_DIR="${TOOLS_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/uv/tools}"
BIN="${BIN:-$HOME/.local/bin}"
APP="$BIN/phonnect"

if [ "$PLATFORM" = macOS ]; then
    SETTINGS="$HOME/Library/Application Support/phonnect"
    LOGS="$SETTINGS"
    LOGIN_ENTRY="$HOME/Library/LaunchAgents/io.github.3sztof.phonnect.plist"
    MENU_ENTRY="$HOME/Applications/Phonnect.app"
else
    SETTINGS="${XDG_CONFIG_HOME:-$HOME/.config}/phonnect"
    LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/phonnect"
    LOGIN_ENTRY="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/phonnect.desktop"
    MENU_ENTRY="${XDG_DATA_HOME:-$HOME/.local/share}/applications/phonnect.desktop"
fi

if [ -z "$SOURCE" ]; then
    if [ -z "$VERSION" ]; then
        # /releases/latest redirects to /releases/tag/vX.Y.Z (no API rate limit).
        latest="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "$RELEASES/latest")" ||
            fail "Could not reach GitHub to find the latest release."
        VERSION="${latest##*/v}"
    fi
    # Only digits and dots: the version goes into URLs and commands.
    case "$VERSION" in
        ""|*[!0-9.]*|.*|*.|*..*) fail "Not a release version: '$VERSION' (see $RELEASES)" ;;
    esac
    SOURCE="$RELEASES/download/v$VERSION/phonnect-$VERSION-py3-none-any.whl"
    WHAT="Phonnect $VERSION"
else
    WHAT="Phonnect from $SOURCE"
fi

INSTALLED=""
[ -x "$APP" ] && INSTALLED="$("$APP" --version 2>/dev/null | awk '{print $2}' || true)"

# Package-manager commands for scrcpy / adb, per platform.
DEPS_CMD=""
DEPS_NOTE=""
if [ -z "$SCRCPY" ] || [ -z "$ADB" ]; then
    if [ "$PLATFORM" = macOS ]; then
        BREW="$(find_cmd brew || true)"
        if [ -n "$BREW" ]; then
            [ -z "$SCRCPY" ] && DEPS_CMD="$BREW install scrcpy"
            [ -z "$ADB" ] && DEPS_CMD="${DEPS_CMD:+$DEPS_CMD && }$BREW install --cask android-platform-tools"
        else
            DEPS_NOTE="Install Homebrew (https://brew.sh), then: brew install scrcpy && brew install --cask android-platform-tools"
        fi
    elif command -v apt-get >/dev/null 2>&1; then
        DEPS_CMD="sudo apt-get install -y scrcpy adb"
    elif command -v pacman >/dev/null 2>&1; then
        DEPS_CMD="sudo pacman -S --needed scrcpy android-tools"
    elif command -v zypper >/dev/null 2>&1; then
        DEPS_CMD="sudo zypper install scrcpy android-tools"
    elif command -v dnf >/dev/null 2>&1; then
        [ -z "$ADB" ] && DEPS_CMD="sudo dnf install android-tools"
        [ -z "$SCRCPY" ] && DEPS_NOTE="scrcpy isn't in Fedora's own repositories: https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md"
    else
        DEPS_NOTE="Install scrcpy and adb with your package manager: https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md"
    fi
fi

# ── the plan ─────────────────────────────────────────────────────────────────

printf '\n%sPhonnect installer%s  %syour Android phone on your desktop, via scrcpy + adb%s\n' "$B" "$N" "$DIM" "$N"

if [ "$UPDATE" = 1 ]; then
    step "Update"
    row "Installed" "${INSTALLED:-not found}"
    row "New" "$WHAT"
    row "Steps" "stop the app (phone settings it changed are put back), replace it, start it again"
    row "Kept" "settings, remembered phones, start at login"
    [ -n "$UV" ] || fail "uv was not found. Run the full installer instead (without --update)."
    echo
    ask "Update now?" y || { echo "Nothing changed."; exit 0; }
else
    step "This will install"
    row "Phonnect" "$WHAT${INSTALLED:+ (replacing $INSTALLED)}"
    row "App files" "$(tilde "$TOOLS_DIR")/phonnect  ${DIM}(its own Python environment, managed by uv)$N"
    row "Commands" "$(tilde "$BIN")/phonnect, phonnect-tray"
    row "Settings" "$(tilde "$SETTINGS")"
    [ "$LOGS" != "$SETTINGS" ] && row "Log" "$(tilde "$LOGS")"
    row "Start at login" "$(tilde "$LOGIN_ENTRY")"
    [ -n "$MENU_ENTRY" ] && row "App menu" "$(tilde "$MENU_ENTRY")"
    echo
    echo "  It needs:"
    if [ -n "$UV" ]; then row "uv" "found: $(tilde "$UV")"
    else row "uv" "${Y}missing${N}: installs Python apps; you'll be asked before it's installed to ~/.local/bin"; fi
    if [ -n "$SCRCPY" ]; then row "scrcpy" "found: $(tilde "$SCRCPY")"
    else row "scrcpy" "${Y}missing${N}: mirrors the phone's screen"; fi
    if [ -n "$ADB" ]; then row "adb" "found: $(tilde "$ADB")"
    else row "adb" "${Y}missing${N}: talks to the phone (Android platform tools)"; fi
    echo
    echo "  Nothing is changed on your phone. No admin rights needed, except for installing"
    echo "  scrcpy / adb with your package manager (asked separately)."
    echo "  To remove it later: $UNINSTALL_CMD"
    echo
    ask "Continue?" y || { echo "Nothing changed."; exit 0; }
fi

# ── uv ───────────────────────────────────────────────────────────────────────

if [ -z "$UV" ]; then
    step "Installing uv"
    echo "  uv (https://docs.astral.sh/uv/) installs Phonnect and the Python it needs, separate from"
    echo "  your system's Python. The official installer would run:"
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  It puts uv in ~/.local/bin and may add that folder to your shell profile."
    echo "  Remove it later: https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
    ask "Install uv?" y || fail "uv is required. Install it yourself, then run this again."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    UV="$(find_cmd uv || true)"
    [ -n "$UV" ] || fail "uv was installed, but it can't be found. Open a new terminal and run this again."
    BIN="$("$UV" tool dir --bin)"
    APP="$BIN/phonnect"
    ok "uv installed: $(tilde "$UV")"
fi

# ── scrcpy and adb ───────────────────────────────────────────────────────────

if [ "$UPDATE" = 0 ] && [ "$DEPS" = 1 ] && { [ -z "$SCRCPY" ] || [ -z "$ADB" ]; }; then
    step "scrcpy and adb"
    if [ -n "$DEPS_CMD" ]; then
        echo "  They come from your package manager, which also keeps them up to date. This would run:"
        echo "    $DEPS_CMD"
        if ask "Install them now?" y; then
            sh -c "$DEPS_CMD" || warn "That didn't work. Install them yourself; Phonnect waits for them (red icon)."
        else
            warn "Skipped. Phonnect shows a red icon until scrcpy and adb are installed."
        fi
    fi
    [ -n "$DEPS_NOTE" ] && warn "$DEPS_NOTE"
fi

# ── Phonnect ─────────────────────────────────────────────────────────────────

step "Installing $WHAT"
if [ -x "$APP" ]; then
    "$APP" stop || true
fi
# The app used to be called scrcpy-autolaunch: remove that one (its settings move over).
if [ -x "$BIN/scrcpy-autolaunch" ]; then
    echo "  Replacing the old scrcpy-autolaunch ..."
    "$BIN/scrcpy-autolaunch" stop || true
    "$UV" tool uninstall scrcpy-autolaunch || true
fi
"$UV" tool install --force --reinstall --python ">=3.11" "$SOURCE" ||
    fail "uv could not install $SOURCE (see above). A previous version, if any, is still there: phonnect start"
[ -x "$APP" ] || fail "uv did not install the phonnect command into $BIN"
ok "Installed $("$APP" --version)"

if [ "$UPDATE" = 1 ]; then
    "$APP" start
else
    step "Checking scrcpy, adb and your phone"
    "$APP" doctor || true
    step "Start at login, app menu entry, starting the app"
    "$APP" install
fi

# ── done ─────────────────────────────────────────────────────────────────────

step "Done"
echo "  Look for the phone icon in the menu bar / tray. Plug in your phone with USB debugging on,"
echo "  and its screen opens on your desktop. Phone setup: https://github.com/$REPO/blob/main/docs/phone-setup.md"
echo
row "Commands" "phonnect status | doctor | start | stop | update"
row "Uninstall" "$UNINSTALL_CMD"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo; warn "$(tilde "$BIN") is not on your PATH, so 'phonnect' isn't found yet. Fix: $UV tool update-shell" ;;
esac
