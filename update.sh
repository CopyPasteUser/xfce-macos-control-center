#!/usr/bin/env bash
# Update source release -> persistent install -> restart the resident app -> show new code.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# GUI archive managers can strip executable bits. The update entrypoint can be
# run through bash, and the installer itself is intentionally invoked through bash.
if [[ ! -f "$HERE/install.sh" || ! -r "$HERE/install.sh" || ! -f "$HERE/VERSION" || ! -r "$HERE/VERSION" ]]; then
    echo "Update-Archiv unvollständig: install.sh oder VERSION fehlt/ist nicht lesbar." >&2
    exit 1
fi
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/macos-control-center"
SOURCE_VERSION=$(cat "$HERE/VERSION")
INSTALLED_VERSION=$(cat "$APP_ROOT/app/VERSION" 2>/dev/null || echo "keine Installation")
printf 'Release im Archiv: %s\n' "$SOURCE_VERSION"
printf 'Bisher installiert: %s\n' "$INSTALLED_VERSION"
printf 'Alte Instanz beenden, neue Datei atomar installieren und aktuellen Daemon neu starten …\n'
exec bash "$HERE/install.sh" "$@"
