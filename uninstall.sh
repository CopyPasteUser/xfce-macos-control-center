#!/usr/bin/env bash
# Entfernt installierte Programmteile und stoppt alle eigenen, laufenden Instanzen.
# Benutzerkonfiguration und Recovery-Backups bleiben erhalten.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/macos-control-center"
APP_DIR="$APP_ROOT/app"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

if [[ -f "$HERE/scripts/daemon-lifecycle.sh" ]]; then
  # shellcheck source=scripts/daemon-lifecycle.sh
  source "$HERE/scripts/daemon-lifecycle.sh"
elif [[ -f "$APP_ROOT/scripts/daemon-lifecycle.sh" ]]; then
  # Works even after the original downloaded/project folder has been deleted.
  source "$APP_ROOT/scripts/daemon-lifecycle.sh"
else
  echo "Sicherheitshelfer fehlt; kann laufende Instanzen nicht zuverlässig stoppen." >&2
  exit 2
fi

if ! cc_stop_control_center_instances; then
  echo "Deinstallation abgebrochen, da eine laufende Instanz nicht sicher beendet wurde." >&2
  exit 3
fi

rm -f -- "$APPS_DIR/macos-control-center.desktop" \
          "$AUTOSTART_DIR/macos-control-center-resident.desktop"
for f in "$BIN_DIR/macos-control-center" "$BIN_DIR/macos-control-center-toggle"; do
  if [[ -f "$f" ]] && grep -Eq 'macos-control-center/(app/macos-control-center|scripts/macos-control-center-toggle)' "$f" 2>/dev/null; then
    rm -f -- "$f"
  fi
done
rm -rf -- "$APP_DIR"
rm -f -- "$APP_ROOT/assets/macos-control-center.svg"
rmdir "$APP_ROOT/assets" 2>/dev/null || true
rm -f -- "$APP_ROOT/uninstall.sh" "$APP_ROOT/status.sh" "$APP_ROOT/doctor.sh"
rm -rf -- "$APP_ROOT/scripts"
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
printf '%s\n' "Programmbestandteile entfernt." \
  "Konfiguration bleibt erhalten: ${XDG_CONFIG_HOME:-$HOME/.config}/macos-control-center" \
  "Backups und Logs bleiben erhalten: $APP_ROOT"
