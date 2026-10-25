#!/usr/bin/env bash
# Read-only diagnostic report for installation, GTK availability and resident toggle.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/macos-control-center"
APP_DIR="$APP_ROOT/app"
APP="$APP_DIR/macos-control-center"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
PIDFILE="${CC_PIDFILE:-$RUNTIME_DIR/macos-control-center.pid}"
STATEFILE="${CC_STATEFILE:-$PIDFILE.state.json}"
PASS=0; WARN=0; FAIL=0

pass() { printf '  [OK]   %s\n' "$*"; PASS=$((PASS+1)); }
warn() { printf '  [HINW] %s\n' "$*"; WARN=$((WARN+1)); }
fail() { printf '  [FEHLER] %s\n' "$*"; FAIL=$((FAIL+1)); }

printf 'DubSync/Mac-like Control Center – Systemdiagnose\n'
printf 'Datum: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
printf 'Benutzer: %s (UID %s)\n' "${USER:-unknown}" "$(id -u)"
printf 'Desktop: %s / Sitzung: %s\n\n' "${XDG_CURRENT_DESKTOP:-unknown}" "${XDG_SESSION_TYPE:-unknown}"

release_version=$(cat "$HERE/VERSION" 2>/dev/null || cat "$APP_DIR/VERSION" 2>/dev/null || echo unbekannt)
installed_version=$(cat "$APP_DIR/VERSION" 2>/dev/null || echo nicht-installiert)
printf 'Release-Ordner: %s (%s)\n' "$HERE" "$release_version"
printf 'Installiert:    %s (%s)\n\n' "$APP" "$installed_version"

printf '%s\n' '=== Voraussetzungen ==='
if command -v python3 >/dev/null 2>&1; then pass "Python: $(python3 --version 2>&1)"; else fail "python3 fehlt"; fi
if command -v python3 >/dev/null 2>&1 && python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
  pass 'PyGObject und GTK 3 importierbar'
else
  fail 'PyGObject/GTK 3 kann mit dem auf PATH gefundenen Python nicht importiert werden'
fi
if [[ -n "${DISPLAY:-}" ]]; then pass "X11 DISPLAY=$DISPLAY"; elif [[ -n "${WAYLAND_DISPLAY:-}" ]]; then warn "Wayland erkannt ($WAYLAND_DISPLAY); Popup-Verhalten kann compositorabhängig sein"; else warn 'Keine grafische DISPLAY-/WAYLAND-Sitzung in der Umgebung erkannt'; fi
for cmd in nmcli pactl rfkill playerctl flatpak xrandr notify-send; do
  if command -v "$cmd" >/dev/null 2>&1; then pass "$cmd verfügbar"; else warn "$cmd fehlt oder ist nicht im PATH (zugehörige Funktionen werden ggf. ausgeblendet)"; fi
done

printf '\n%s\n' '=== Dateien und Desktopintegration ==='
if [[ -r "$APP" ]]; then pass "Installierte Programmdatei lesbar: $APP"; else fail "Programmdatei fehlt: $APP"; fi
if [[ -x "$BIN_DIR/macos-control-center-toggle" ]]; then pass 'Toggle-Starter ausführbar'; else fail "Toggle-Starter fehlt/ist nicht ausführbar: $BIN_DIR/macos-control-center-toggle"; fi
if [[ -r "$APPS_DIR/macos-control-center.desktop" ]]; then
  pass 'Desktop-Menüeintrag vorhanden'
  if command -v desktop-file-validate >/dev/null 2>&1; then
    if desktop-file-validate "$APPS_DIR/macos-control-center.desktop"; then pass 'Desktop-Datei validiert'; else fail 'Desktop-Datei ist ungültig'; fi
  else warn 'desktop-file-validate nicht installiert; Validierung übersprungen'; fi
else warn 'Kein installierter Desktop-Menüeintrag gefunden'; fi
if [[ -d "${XDG_CONFIG_HOME:-$HOME/.config}/macos-control-center" ]]; then
  config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/macos-control-center"
  if python3 - "$config_dir" <<'PY'
import os, stat, sys
try: raise SystemExit(0 if stat.S_IMODE(os.stat(sys.argv[1]).st_mode) & 0o077 == 0 else 1)
except OSError: raise SystemExit(1)
PY
  then pass 'Konfigurationsordner hat private Berechtigungen'; else warn 'Konfigurationsordner ist für Gruppe/Andere zugänglich'; fi
else pass 'Konfigurationsordner noch nicht angelegt (wird bei Bedarf erstellt)'; fi

printf '\n%s\n' '=== Resident / Toggle ==='
if [[ -r "$PIDFILE" ]]; then
  pid=$(cat "$PIDFILE" 2>/dev/null || true)
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    pass "PID-Datei zeigt auf laufenden Prozess $pid"
  else warn 'PID-Datei ist vorhanden, aber ihr Prozess läuft nicht'; fi
else warn 'PID-Datei fehlt; beim nächsten Starter-Aufruf wird der Daemon selbstheilend gestartet'; fi
if [[ -r "$STATEFILE" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 - "$STATEFILE" "$PIDFILE" "$APP" "$installed_version" <<'PY'
import json, os, sys
state_path, pid_path, app_path, version = sys.argv[1:]
try:
    with open(state_path, encoding='utf-8') as f: state = json.load(f)
    with open(pid_path, encoding='ascii') as f: pid = int(f.read().strip())
    good = (state.get('pid') == pid and state.get('resident') is True
            and os.path.realpath(state.get('script', '')) == os.path.realpath(app_path)
            and (version == 'nicht-installiert' or state.get('version') == version))
    if not good: raise SystemExit(1)
    print('  Laufzeit-Version:', state.get('version', 'unbekannt'))
    print('  Laufzeit-PID:    ', state.get('pid'))
    print('  Popup sichtbar:  ', state.get('visible', 'unbekannt'))
    print('  Script-Pfad:     ', state.get('script', 'unbekannt'))
except (OSError, ValueError, TypeError): raise SystemExit(1)
PY
  then pass 'Runtime-Metadaten passen zur installierten Version und PID'; else warn 'Runtime-Metadaten fehlen, veraltet oder gehören zu einer anderen Version'; fi
else warn 'Runtime-Statusdatei fehlt; Daemon ist nicht bereit oder nutzt einen anderen Statuspfad'; fi
printf '\nErgebnis: %d OK · %d Hinweise · %d Fehler\n' "$PASS" "$WARN" "$FAIL"
printf 'Log: %s\n' "$APP_ROOT/logs/daemon.log"
printf 'Status: bash %s/status.sh\n' "$HERE"
[[ "$FAIL" -eq 0 ]]
