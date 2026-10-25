#!/usr/bin/env bash
# Benutzerlokale Installation/Aktualisierung. Aktualisiert den Code auch im bereits
# installierten Pfad und startet danach genau diese Version neu.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/macos-control-center"
APP_DIR="$APP_ROOT/app"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
PIDFILE="$RUNTIME_DIR/macos-control-center.pid"
STAMP=$(date +%Y%m%d-%H%M%S)
START_AFTER_INSTALL=1
SHOW_AFTER_INSTALL=1

for arg in "$@"; do
  case "$arg" in
    --no-start) START_AFTER_INSTALL=0 ;;
    --start-hidden) START_AFTER_INSTALL=1; SHOW_AFTER_INSTALL=0 ;;
    --help|-h)
      cat <<'HELP'
macOS Control Center 1.3.1 – benutzerlokaler Installer

Usage: ./install.sh [option]
  (keine Option)  Installieren/aktualisieren, neuen Daemon starten und Popup öffnen
  --start-hidden  Installieren/aktualisieren und Daemon starten, Popup versteckt lassen
  --no-start      Dateien aktualisieren, Daemon nicht neu starten (für Tests/Headless)
  --help          Diese Hilfe anzeigen

Bei Updates werden laufende Control-Center-Prozesse gestoppt, damit nie absichtlich
weiter die alte, im Speicher geladene Version angezeigt wird. Einstellungen bleiben erhalten.
HELP
      exit 0 ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 2 ;;
  esac
done

# ZIP tools (especially GUI archive managers) do not always preserve Unix mode
# bits consistently. The source only needs to be a readable regular file because
# `install -m 0755` below sets the correct mode on the installed copy.
if [[ ! -f "$HERE/macos-control-center" || ! -r "$HERE/macos-control-center" ]]; then
  echo "Die Quelldatei macos-control-center fehlt oder ist nicht lesbar." >&2
  echo "Erwarteter Pfad: $HERE/macos-control-center" >&2
  exit 1
fi
if [[ ! -f "$HERE/scripts/daemon-lifecycle.sh" ]]; then
  echo "Installer-Hilfsdatei scripts/daemon-lifecycle.sh fehlt." >&2
  exit 1
fi
if [[ ! -f "$HERE/macos-control-center-toggle" || ! -r "$HERE/macos-control-center-toggle" ]]; then
  echo "Selbstheilender Toggle-Starter macos-control-center-toggle fehlt." >&2
  exit 1
fi
# shellcheck source=scripts/daemon-lifecycle.sh
source "$HERE/scripts/daemon-lifecycle.sh"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 fehlt." >&2
  exit 1
fi
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
  echo "GTK 3 / PyGObject fehlt. Installiere die Pakete deiner Distribution, z. B. python3-gi und gir1.2-gtk-3.0." >&2
  echo "Der Installer verändert das Basissystem nicht und verwendet kein sudo." >&2
  exit 2
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$APPS_DIR" "$AUTOSTART_DIR" \
         "$APP_ROOT/backups" "$APP_ROOT/logs" "$APP_ROOT/scripts" "$APP_ROOT/assets" "$RUNTIME_DIR"
chmod 700 "$APP_ROOT/backups" "$APP_ROOT/logs"

# Stage the new code before stopping a running instance. Rename is atomic within APP_DIR.
STAGED_APP="$APP_DIR/.macos-control-center.new.$STAMP"
STAGED_VERSION="$APP_DIR/.VERSION.new.$STAMP"
install -m 0755 "$HERE/macos-control-center" "$STAGED_APP"
if [[ -f "$HERE/VERSION" ]]; then
  SOURCE_VERSION=$(cat "$HERE/VERSION")
  APP_SOURCE_VERSION=$(python3 - "$HERE/macos-control-center" <<'PYVER'
import ast, sys
from pathlib import Path
module = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node in module.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in node.targets):
        print(ast.literal_eval(node.value))
        break
else:
    raise SystemExit("APP_VERSION fehlt im Programm")
PYVER
)
  if [[ "$SOURCE_VERSION" != "$APP_SOURCE_VERSION" ]]; then
    echo "Versionsabweichung: VERSION=$SOURCE_VERSION, Programm=$APP_SOURCE_VERSION" >&2
    rm -f -- "$STAGED_APP"
    exit 1
  fi
  install -m 0644 "$HERE/VERSION" "$STAGED_VERSION"
else
  printf '%s\n' "1.3.1" > "$STAGED_VERSION"
  chmod 0644 "$STAGED_VERSION"
fi

# Keep dated recovery copies of the previous application and integration files.
backup_one() {
  local target="$1"
  if [[ -e "$target" ]]; then
    cp -p -- "$target" "$APP_ROOT/backups/$(basename "$target").$STAMP"
  fi
}
PREVIOUS_APP_BACKUP=""
PREVIOUS_VERSION_BACKUP=""
if [[ -f "$APP_DIR/macos-control-center" ]]; then
  PREVIOUS_APP_BACKUP="$APP_ROOT/backups/macos-control-center.$STAMP"
  cp -p -- "$APP_DIR/macos-control-center" "$PREVIOUS_APP_BACKUP"
fi
if [[ -f "$APP_DIR/VERSION" ]]; then
  PREVIOUS_VERSION_BACKUP="$APP_ROOT/backups/VERSION.$STAMP"
  cp -p -- "$APP_DIR/VERSION" "$PREVIOUS_VERSION_BACKUP"
fi
backup_one "$BIN_DIR/macos-control-center"
backup_one "$BIN_DIR/macos-control-center-toggle"
backup_one "$APPS_DIR/macos-control-center.desktop"
backup_one "$AUTOSTART_DIR/macos-control-center-resident.desktop"
backup_one "$APP_ROOT/uninstall.sh"
backup_one "$APP_ROOT/status.sh"
backup_one "$APP_ROOT/doctor.sh"
backup_one "$APP_ROOT/scripts/macos-control-center-toggle"

# Critical: stop resident and non-resident copies before replacing files. This
# catches old daemons launched directly from ~/projekte as well as installed copies.
if ! cc_stop_control_center_instances; then
  rm -f -- "$STAGED_APP" "$STAGED_VERSION"
  echo "Update abgebrochen: Die alte Instanz wurde nicht sicher beendet." >&2
  exit 3
fi

mv -f -- "$STAGED_APP" "$APP_DIR/macos-control-center"
mv -f -- "$STAGED_VERSION" "$APP_DIR/VERSION"

# Stable wrappers always point at APP_DIR, not at the temporary ZIP/extract directory.
cat > "$BIN_DIR/macos-control-center" <<EOF_WRAPPER
#!/usr/bin/env bash
if [[ "\${1:-}" == "--daemon" ]]; then
  exec "$APP_DIR/macos-control-center" "\$@"
fi
exec "$APP_ROOT/scripts/macos-control-center-toggle" "\$@"
EOF_WRAPPER
cat > "$BIN_DIR/macos-control-center-toggle" <<EOF_TOGGLE
#!/usr/bin/env bash
exec "$APP_ROOT/scripts/macos-control-center-toggle" "\$@"
EOF_TOGGLE
chmod 0755 "$BIN_DIR/macos-control-center" "$BIN_DIR/macos-control-center-toggle"

# Desktop Exec fields are double-quoted absolute program paths; arguments remain separate.
cat > "$APPS_DIR/macos-control-center.desktop" <<EOF_DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=Control Center
Comment=macOS-artiges Control Center für XFCE
Exec="$BIN_DIR/macos-control-center-toggle"
Icon=$APP_ROOT/assets/macos-control-center.svg
Terminal=false
Categories=Settings;
StartupNotify=false
EOF_DESKTOP
cat > "$AUTOSTART_DIR/macos-control-center-resident.desktop" <<EOF_AUTOSTART
[Desktop Entry]
Type=Application
Version=1.0
Name=Control Center Resident
Comment=Aktuelle Control-Center-Version vorladen und schnell umschalten
Exec="$BIN_DIR/macos-control-center" --daemon
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
EOF_AUTOSTART
chmod 0644 "$APPS_DIR/macos-control-center.desktop" "$AUTOSTART_DIR/macos-control-center-resident.desktop"

# The installer and lifecycle helper remain available after deleting the extracted ZIP.
install -m 0755 "$HERE/uninstall.sh" "$APP_ROOT/uninstall.sh"
install -m 0755 "$HERE/status.sh" "$APP_ROOT/status.sh"
if [[ -r "$HERE/doctor.sh" ]]; then install -m 0755 "$HERE/doctor.sh" "$APP_ROOT/doctor.sh"; fi
install -m 0755 "$HERE/scripts/daemon-lifecycle.sh" "$APP_ROOT/scripts/daemon-lifecycle.sh"
install -m 0755 "$HERE/macos-control-center-toggle" "$APP_ROOT/scripts/macos-control-center-toggle"
if [[ -r "$HERE/assets/macos-control-center.svg" ]]; then
  install -m 0644 "$HERE/assets/macos-control-center.svg" "$APP_ROOT/assets/macos-control-center.svg"
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "$APPS_DIR/macos-control-center.desktop"
  desktop-file-validate "$AUTOSTART_DIR/macos-control-center-resident.desktop"
else
  echo "Hinweis: desktop-file-validate fehlt; Desktop-Dateien strukturell erzeugt."
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

printf '\nDateien installiert; prüfe jetzt den Daemon-Start.\n'
printf 'Version:   %s\n' "$(cat "$APP_DIR/VERSION")"
printf 'Programm:  %s\n' "$APP_DIR/macos-control-center"
printf 'Starter:   %s\n' "$BIN_DIR/macos-control-center-toggle"
printf 'Menü:      %s\n' "$APPS_DIR/macos-control-center.desktop"
printf 'Autostart: %s\n' "$AUTOSTART_DIR/macos-control-center-resident.desktop"
printf 'Backups:   %s\n' "$APP_ROOT/backups"
printf 'Logs:      %s\n' "$APP_ROOT/logs"
printf 'Diagnose:  %s\n' "$APP_ROOT/doctor.sh"
printf 'Config:    %s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/macos-control-center (unverändert)"

if [[ "$START_AFTER_INSTALL" -eq 1 ]]; then
  if [[ "$SHOW_AFTER_INSTALL" -eq 1 ]]; then
    START_MODE="show"
  else
    START_MODE="hidden"
  fi
  if cc_start_and_show_control_center "$APP_DIR/macos-control-center" "$APP_ROOT" "$START_MODE"; then
    if [[ "$SHOW_AFTER_INSTALL" -eq 1 ]]; then
      echo "Die neue Version wurde gestartet und das Popup geöffnet."
    else
      echo "Die neue Version wurde als Resident-Daemon gestartet; das Popup bleibt verborgen."
    fi
    echo "Installation/Aktualisierung erfolgreich."
  else
    echo "FEHLER: Dateien wurden installiert, aber der Resident-Daemon konnte nicht gestartet werden." >&2
    echo "Die Installation ist nicht betriebsbereit; siehe Diagnose und Log unten." >&2
    echo "Prüfe das Log: $APP_ROOT/logs/daemon.log" >&2
    if [[ -n "$PREVIOUS_APP_BACKUP" && -f "$PREVIOUS_APP_BACKUP" ]]; then
      echo "Stelle die vorherige, gesicherte Programmversion wieder her …" >&2
      # Stop a partly started new process before restoring the old executable.
      cc_stop_control_center_instances || true
      RESTORE_APP="$APP_DIR/.macos-control-center.restore.$STAMP"
      install -m 0755 "$PREVIOUS_APP_BACKUP" "$RESTORE_APP"
      mv -f -- "$RESTORE_APP" "$APP_DIR/macos-control-center"
      if [[ -n "$PREVIOUS_VERSION_BACKUP" && -f "$PREVIOUS_VERSION_BACKUP" ]]; then
        cp -p -- "$PREVIOUS_VERSION_BACKUP" "$APP_DIR/VERSION"
      fi
      if cc_start_and_show_control_center "$APP_DIR/macos-control-center" "$APP_ROOT" show; then
        echo "Rollback erfolgreich: Vorherige Version wurde wieder geöffnet." >&2
      else
        echo "Rollback-Code ist wiederhergestellt, aber auch der vorherige Daemon startet nicht." >&2
        echo "Bitte Log prüfen: $APP_ROOT/logs/daemon.log" >&2
      fi
    else
      echo "Erstinstallation: Es gibt keine vorherige Version zum Zurückrollen." >&2
    fi
    exit 4
  fi
else
  echo "Installation/Aktualisierung erfolgreich (Daemon-Start mit --no-start ausdrücklich übersprungen)."
  echo "Ein späterer normaler Starter-Aufruf nutzt die installierte Datei."
fi

echo "Keine XFCE-Panel-, Theme-, Wallpaper-, Plank- oder Whisker-Einstellungen wurden verändert."
