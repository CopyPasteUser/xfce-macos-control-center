#!/usr/bin/env bash
# Read-only status: distinguishes archive source, installed binary and running process metadata.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/macos-control-center"
APP_DIR="$APP_ROOT/app"
PIDFILE="${XDG_RUNTIME_DIR:-/tmp}/macos-control-center.pid"
STATEFILE="${CC_STATEFILE:-$PIDFILE.state.json}"

if [[ -f "$HERE/scripts/daemon-lifecycle.sh" ]]; then
  # shellcheck source=scripts/daemon-lifecycle.sh
  source "$HERE/scripts/daemon-lifecycle.sh"
elif [[ -f "$APP_ROOT/scripts/daemon-lifecycle.sh" ]]; then
  # Installed helper means this status check still works after the ZIP folder is deleted.
  source "$APP_ROOT/scripts/daemon-lifecycle.sh"
else
  echo "Helper fehlt. Starte status.sh aus einem vollständigen Release-Ordner."
  exit 2
fi

printf '%s\n' "=== Control-Center-Versionen ==="
printf 'Release-Datei: %s\n' "$(cat "$HERE/VERSION" 2>/dev/null || echo unbekannt)"
if [[ -r "$APP_DIR/VERSION" ]]; then
  printf 'Installiert:   %s\n' "$(cat "$APP_DIR/VERSION")"
else
  echo "Installiert:   keine Installation gefunden"
fi
if [[ -f "$APP_DIR/macos-control-center" && -f "$HERE/macos-control-center" ]]; then
  if cmp -s "$HERE/macos-control-center" "$APP_DIR/macos-control-center"; then
    echo "Quelldatei:    Release und installierte Datei sind identisch"
  else
    echo "Quelldatei:    Release-Datei und installierte Datei unterscheiden sich"
  fi
fi

printf '\n%s\n' "=== Laufende Prozesse ==="
found=0
for proc in /proc/[0-9]*; do
  [[ -r "$proc/status" && -r "$proc/cmdline" ]] || continue
  pid="${proc##*/}"
  cc_is_control_center_process "$pid" || continue
  local_path=""
  local_mode="Fensterprozess"
  argv=()
  mapfile -d '' -t argv < "$proc/cmdline" 2>/dev/null || true
  ((${#argv[@]} >= 2)) || continue
  local_path="${argv[1]}"
  for arg in "${argv[@]}"; do
    if [[ "$arg" == "--daemon" ]]; then local_mode="Resident-Daemon"; fi
  done
  printf 'PID %s · %s\n  Codepfad: %s\n' "$pid" "$local_mode" "$local_path"
  if [[ "$local_path" == "$APP_DIR/macos-control-center" ]]; then
    echo "  Herkunft: installierter Programm-Pfad"
  else
    echo "  Herkunft: andere Checkout-/Programmdatei (wird von update.sh beim Update beendet)"
  fi
  found=1
done
[[ "$found" -eq 1 ]] || echo "Keine laufende Control-Center-Instanz gefunden."

printf '\n%s\n' "=== Tatsächlich gemeldeter Laufzeitstand ==="
if [[ -r "$STATEFILE" ]] && command -v python3 >/dev/null 2>&1; then
  python3 - "$STATEFILE" "$PIDFILE" <<'PY'
import json, os, sys
state_path, pid_path = sys.argv[1:]
try:
    state = json.load(open(state_path, encoding="utf-8"))
    try:
        pid = int(open(pid_path, encoding="ascii").read().strip())
    except (OSError, ValueError):
        pid = -1
    if not isinstance(state, dict):
        raise ValueError("Statusdatei ist kein Objekt")
    print("Laufzeit-Version:", state.get("version", "unbekannt"))
    print("Laufzeit-PID:    ", state.get("pid", "unbekannt"))
    print("Startzeit:       ", state.get("started_at", "unbekannt"))
    print("Resident:        ", state.get("resident", "unbekannt"))
    print("Popup sichtbar:  ", state.get("visible", "unbekannt"))
    print("Zuletzt geändert:", state.get("updated_at", state.get("started_at", "unbekannt")))
    print("Geladener Pfad:  ", state.get("script", "unbekannt"))
    if state.get("pid") != pid:
        print("WARNUNG: Laufzeit-Metadaten und PID-Datei passen nicht zusammen.")
except (OSError, ValueError, TypeError) as exc:
    print("Runtime-Status kann nicht gelesen werden:", exc)
PY
else
  echo "Keine Runtime-Metadaten vorhanden (alte Instanz oder Daemon läuft nicht)."
fi
printf '\nDiagnoselog: %s\n' "$APP_ROOT/logs/daemon.log"
printf 'Update-Befehl aus dem gewünschten neuen Release: ./update.sh\n'
