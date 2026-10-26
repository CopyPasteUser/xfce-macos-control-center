# Übergabe · macOS Control Center 2.1.0 · 2026-10-26

## Quelle und Ziel

Aus 2.0.0 (stabile visuelle Basis; historische Herkunft siehe docs/2.0-PLAN.md).
Eigenständiges Python/GTK3-Popup für
XFCE/X11. Benutzerpräferenz: dunkle kompakte Oberfläche, schnelle Bedienung,
allgemeine XFCE-Geräteunterstützung, optionale Homelab-Funktionen.

## Unveränderliche Regeln

- `LOCALSEND_CMD` bleibt `["flatpak", "run", "--nofilesystem=/mnt/medien", "org.localsend.localsend_app"]`.
- Keine Änderungen an Desktop-Themes, Icons, Plank, Panel, Wallpaper oder Whisker.
- Deckendes Fenster mit `set_app_paintable(False)`, kein RGBA-Visual.
- Sensoransicht bleibt lesend; keine Lüfter-/PWM-Manipulation.
- Keine gespeicherten WLAN-/VPN-Geheimnisse; URLs mit Zugangsdaten abweisen.

## Implementiert

2.1 behebt den Settings-Konstruktionsfehler und den überschriebenen Bluetooth-
Power-Worker. Bluetooth unterscheidet Dienst, Bus, Adapter, Powered und rfkill;
Audio liefert immer einen endlichen Discovery-Zustand. Die Diagnosemodi sind
read-only und verändern weder Hardware noch Daemon-/Config-Zustand.

`./run.sh --direct` startet eine eigene Debug-Instanz und zeigt GTK-/Worker-
Exceptions im Terminal. `--diagnose`, `--diagnose-bluetooth` und
`--diagnose-audio` funktionieren ohne DISPLAY.

Neue Funktionen: `_filter_actions`, `_validate_devices`, `_magic_packet`,
`_resource_policy`, `_system_snapshot`. GTK-Methoden: `_render_actions`,
`_open_workspace`, Geräteverwaltung, Fokus-Timer und `_configure_polling`.

Status-Pipeline: `_poll_collect` liefert Teilwerte mit `_partial=True` über
`GLib.idle_add`; erst die Abschlussnachricht hebt `_polling` auf. Ein Fehler
betrifft nur seinen Leser. Poolwechsel werden bis zum Abschluss aufgeschoben.
Widgets werden ausschließlich im GTK-Thread verändert.

Helligkeit: ein Worker mit Lock und zuletzt angefordertem Wert; 1500-ms-D-Bus-
Methoden-Timeout. SVG_CACHE maximal 128 Pixbufs. Keine Disk-Caches für SSIDs/Titel.

Konfiguration ergänzt um `resource_profile`, `compact_actions`, `devices`.
Alte Configs ohne Profil behalten ihr Intervall als `custom`. Kein persönlicher
VPN-Default mehr; vorhandene Einstellung bleibt erhalten. Benutzerdefinierte
Aktionslisten bleiben unverändert: neue Aktionen gegebenenfalls dort aktivieren.

## Tests und nächste Prüfung

Siehe docs/VALIDATION.md. Portabler Testlauf bestanden. Der vollständige Testlauf
hat hier zwei bereits im Original vorhandene PID-Namespace-Fehler. Kein GTK-Sichttest
möglich, PyGObject/Xvfb fehlen. Keine Aussage über echte Startzeiten machen.
Vor weiterer Veröffentlichung auf XFCE testen: Popup-Geometrie bei 768 px Höhe,
Suche/Kategorien, Dialogfokus, Profile, Helligkeit, Resident-Toggle, Geräte und WOL.

Installer-/Toggle-Skripte wurden funktional nicht geändert. README beschreibt
Benutzerinstallation, Update und vorhandene Recovery-Backups. Neue Konfiguration
und Notizen dürfen beim Update nicht überschrieben werden.
