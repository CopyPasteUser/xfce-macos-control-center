# Manueller Smoke-Test – macOS Control Center 1.3.1

Diese Checkliste nach Updates an GTK, Medienwidget, Fensterlayout oder Toggle-Lifecycle auf dem Ziel-Desktop abarbeiten.

## Popup und Bedienung

1. Panel-Starter öffnet das Popup; ein zweiter Klick schließt es und ein dritter öffnet es wieder.
2. Popup bleibt deckend und oben rechts. Es gibt keine zusätzliche Kopfzeile mit Logo/Close-Button.
3. Auf einem kleinen Monitor bleibt der Inhalt erreichbar; lange Einstellungs-/Detailmenüs scrollen statt abgeschnitten zu werden.
4. Menüanimationen folgen der Einstellung (Flüssig/Schnell/Aus) und der Option für reduzierte Bewegung.
5. `Esc` schließt das Popup; `Ctrl+R` aktualisiert; `Ctrl+,` öffnet Einstellungen.

## Einstellungen und Schnellaktionen

6. Einstellungen öffnen und Theme Mitternacht/Graphit/Hell direkt auswählen.
7. Akzentfarbe, Sprache und Animationsgeschwindigkeit direkt in den Untermenüs auswählen.
8. Anwendung neu starten und prüfen, dass die ausgewählten Einstellungen erhalten bleiben; bei Sprachwechsel wird der Prozess neu geladen.
9. Schnellaktionen ein-/ausblenden und sortieren; die Auswahl bleibt nach einem Neustart erhalten.
10. Screenshot ist als Schnellaktion vorhanden, aber kein eigener Button in der unteren Aktionsleiste.
11. Power-Menü nutzt Symbole; Neustart/Herunterfahren benötigen die zusätzliche Bestätigung.
12. Kurznotizen öffnen, Text mit `Ctrl+S` speichern, Anwendung schließen und prüfen, dass der Text nach erneutem Öffnen noch vorhanden ist.
13. Speicheranalyse auf einem kleinen Ordner starten, Ergebnisliste und verwendeten/freien Speicher prüfen.
14. Lüfteransicht öffnen: falls Hardware-Sensoren verfügbar sind, werden RPM/Temperaturen angezeigt. Ohne Sensoren soll eine klare Meldung erscheinen. Falls CoolerControl installiert ist, muss dessen Starter funktionieren.

## Medien und Netzwerk

15. Einen `playerctl`-/MPRIS-fähigen Player starten, z. B. Browser/YouTube sofern der Player MPRIS exportiert. Titel, Kanal/Interpret, Vorschaubild, Fortschrittsbalken und Zeitposition prüfen.
16. Wenn keine Artwork-URL bereitgestellt wird, bleibt ein neutrales Videosymbol; das Popup darf nicht hängen bleiben.
17. WLAN-Details öffnen: aktuelle SSID, Gerät, Signal/Sicherheit sowie – falls verfügbar – IP, Gateway und DNS prüfen.
18. WLAN-Profile, Passwortdialog, Bluetooth und VPN einzeln testen. WLAN-Passwort darf nicht in Prozessargumenten, Logs oder Konfigurationsdateien erscheinen.
19. Tastaturbeleuchtung testen, sofern Hardware vorhanden: genau drei Zustände Aus/An/Heller. Auf nicht unterstützter Hardware soll das Element fehlen.

## Update und Sicherheitsgrenzen

20. `bash ./status.sh` prüft Release-/Installationsversion, Runtime-Version, PID und Codepfad.
21. Ein neues Release in einem neuen Ordner entpacken und dort `bash ./update.sh` starten; alte Instanzen müssen sicher beendet und der neue Daemon verifiziert werden.
22. `bash ./run-tests.sh` muss ohne Fehler enden.
23. LocalSend mit `flatpak info --show-permissions org.localsend.localsend_app` prüfen: `/mnt/medien` darf nicht freigegeben sein.
24. Installer/Tests dürfen keine XFCE-Panel-, Theme-, Icon-Theme-, Plank-, Wallpaper- oder Whisker-Einstellungen verändern.


## Version 2.0

Zusätzliche Prüfungen und Grenzen: siehe `VALIDATION.md`, Abschnitt „Auf einem XFCE-Zielgerät“.
