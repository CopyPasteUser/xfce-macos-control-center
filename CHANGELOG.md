# Version 2.0.0 · 2026-10-25

- Aktionssuche mit Strg+F/Enter, Kategorien und gespeicherter kompakter Ansicht.
- Geräteverwaltung mit validierten Weblinks, Bearbeiten/Löschen und Wake-on-LAN.
- Fokus-Timer mit 25/45/60 Minuten und optionaler Desktopbenachrichtigung.
- Systemübersicht; keine eingebauten privaten Serveradressen oder VPN-Namen.
- Ressourcenprofile für App-Abfragen, kompatible Migration bestehender Intervalle.
- Teilweise Statuslieferung, Fehlerisolation und parallele optionale Geräteerkennung.
- Helligkeit aus GTK ausgelagert, Zwischenwerte gebündelt, D-Bus-Timeout begrenzt.
- Begrenzter SVG-Cache; Suche löst keine neuen Geräteabfragen aus.
- Neue Tests für Validierung, Magic Packet, Suche, Profile, Polling und Helligkeit.
- README, Übergabe, Umsetzungsplan und nachvollziehbarer Prüfstatus ergänzt.
- Bestehende Installer-/Starterlogik und LocalSend-Sandbox unverändert.
- Grenzen: kein echter GTK-Sichttest hier; Prozessintegration in dieser Umgebung blockiert.

# Changelog

## 1.3.1 — Zuverlässiger Toggle, Utility-Regressionstests und vollständige Dokumentation (2026-10-25)

- Release-Version, Programmkonstante, Installer-Fallback, User-Agent und manuelle Smoke-Test-Dokumentation auf 1.3.1 synchronisiert.
- Toggle-Test-Double schreibt Runtime-Zustand atomar und veröffentlicht sein Testsignal erst nach abgeschlossener Zustandsänderung; reduziert einen Dateileserennen-Testfehler, ohne Produktionslogik zu schwächen.
- Runtime-Tests decken mehrere Notizen, private Dateirechte, Migration der alten Einzelnotiz, größte Dateien, Dateiarten, Ordnergrößen, Symlink-/Dateisystemgrenzen und das Auslesen von Fan-/Temperatursensoren ab.
- `run-tests.sh` führt die Utility-Regressionstests direkt aus.
- README von Grund auf neu geschrieben: Features, Schnellaktionen, Netzwerk, Medien, Keyboard-Light, Notizen, Speicheranalyse, Lüftermonitor, Settings, Installations-/Updatepfad, Konfigurations-/Runtime-Pfade, Fehlerdiagnose und Sicherheitsgrenzen dokumentiert.
- `handover.md` wird nicht mehr im Projekt- oder Release-Paket geführt.
- LocalSend-Sandbox und alle bisherigen Systemschutzregeln bleiben unverändert.


## 1.2.0 — Feinschliff, Medienwidget und neue Dienstprogramme (2026-10-25)

- Professionelle README mit Funktionsübersicht, Setup, Datenpfaden, Tests, Sicherheit und bekannten Grenzen.
- Einstellungen besitzen direkte Auswahlmenüs für Theme, Akzentfarbe, Sprache und Animationen statt blindem Durchschalten.
- Medienwidget erweitert: 16:9-Vorschaubild, Wiedergabestatus, Fortschrittsbalken und Zeitposition aus MPRIS/`playerctl`.
- Netzwerkdetails um DNS erweitert; WLAN-Scanresultat wird für Verbindungszusammenfassung wiederverwendet, um doppelte `nmcli`-Scans zu vermeiden.
- Tastaturbeleuchtung zeigt drei feste Zustände: Aus, An und Heller.
- Kurznotizen, Speicheranalyse und Lüfter-/Temperaturmonitor als optionale Schnellaktionen; Notizspeicherung mit privaten Dateirechten, Storage-Scan dateisystembegrenzt, Lüfterwerte read-only.
- Screenshot bleibt eine Quick Action; der redundante Screenshot-Button in der unteren Leiste bleibt entfernt.
- `reduce_motion` berücksichtigt jetzt auch die Animationsgeschwindigkeit.
- Regressionstests für Medien, DNS, Settings-Picker, Tastaturstufen, Notizen, Speicheranalyse, Lüftersicherheit und Versionskonsistenz ergänzt.
- LocalSend-Sandbox und deckendes Fenster bleiben unverändert.

## 1.1.0 — Symbolleiste und Schnellaktionen

- Untere Leiste auf Power, Schnellaktionen und Einstellungen reduziert; Sperren und Mission Center entfernt.
- 18 zusätzliche optionale Schnellaktionen mit Verfügbarkeitsprüfung.
- Dunkles Blaugrau, monochrome SVG-Symbole und blaue Akzentfarbe für aktive Schalter.

## 1.0.0 — Toggle-Lifecycle und Wiederherstellung

- Resident-Toggle, Runtime-Versionierung, sichere Update-/Rollback-Abläufe, Diagnose und rotierende Logs.
- Dynamische Popup-Höhe, Scrollen bei Übergröße und weiche Größenanimation.
- Schnellaktionseditor, fünfsprachige UI, private Konfiguration und Regressionstests.
