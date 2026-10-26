# macOS Control Center

**Version 2.1.0 · GTK 3 / Python · Linux Mint XFCE und kompatible X11-Desktops**

Ein kompaktes, macOS-inspiriertes Control Center für Linux. Es bündelt häufig benötigte Systemschalter, Regler, Mediensteuerung und individuell sortierbare Schnellaktionen in einem schwebenden Popup. Das Programm ist ein eigenständiges GTK-Fenster – kein XFCE-Panel-Plugin – und verändert keine globalen Desktop-Themes oder Panel-Einstellungen.

> Zielplattform ist ein klassischer X11-Desktop, besonders XFCE. Unter Wayland kann die Fensterpositionierung je nach Compositor eingeschränkt sein.

## Neu in 2.1

2.1 härtet die bestehende Control-Center-Oberfläche und ihre Hardwarepfade,
ohne Main-UI oder Navigation neu zu bauen. Settings, Audio, Bluetooth,
Konfiguration und Hintergrund-Worker liefern jetzt nachvollziehbare Endzustände.
Read-only-Diagnosemodi helfen bei der Prüfung auf realer XFCE-Hardware.

Die Version 2.0 bleibt die stabile visuelle Basis; Konfiguration und Notizen
werden weiterverwendet. Die App bleibt eigenständig und verändert keine globalen
Desktop-Designs.

### Aktionen schneller finden

Oben steht eine Suchzeile. **Strg+F** fokussiert die Suche; **Enter** führt den
ersten Treffer aus. Die Suche berücksichtigt Namen, Beschreibung und interne
Aktionsnamen, ohne dabei Systembefehle auszuführen. Kategorien grenzen die
Ansicht auf Verbindungen, Werkzeuge oder Gerätefunktionen ein.

Die Standardansicht zeigt höchstens acht verfügbare Aktionen. **Alle Aktionen**
klappt die vollständige Auswahl auf; **Kompakte Ansicht** reduziert sie wieder.
Diese Entscheidung wird gespeichert. Unter **Schnellaktionen anpassen** bleiben
Reihenfolge und Auswahl frei einstellbar; die ersten acht ausgewählten Aktionen
bilden dann die kompakte Ansicht. Such- und Kategorieansichten zeigen alle
passenden aktivierten Aktionen. Deaktivierte Aktionen werden im Anpassungsmenü
wieder aktiviert.

Ohne eigene Reihenfolge werden LocalSend, Notizen, Meine Geräte, Fokus-Timer,
Speicheranalyse, Sensoren, Tastaturlicht und Wachhalten bevorzugt. Je nach
Verfügbarkeit können andere Aktionen nachrücken.

### Meine Geräte: persönlich, aber nicht fest verdrahtet

**Meine Geräte** öffnet eine eigene Verwaltung mit Hinzufügen, Bearbeiten und
Entfernen. Jeder Eintrag enthält einen Namen und mindestens eine der Angaben:

- HTTP(S)-Adresse für die Weboberfläche, geöffnet im Standardbrowser;
- MAC-Adresse für Wake-on-LAN, optional mit eigener Broadcast-IPv4-Adresse.

Damit lassen sich beispielsweise ein NAS, Satella, Regulus oder ein Router
verwalten. Das sind mögliche Namen, keine eingebauten Zieladressen. Es gibt
keinen automatischen Netzwerkscan und keine Abfrage entfernter Dienste beim
Öffnen des Control Centers. Webadressen dürfen keine eingebetteten Benutzernamen
oder Passwörter enthalten. Die Liste wird in der privaten App-Konfiguration gespeichert.

**Aufwecken** sendet ein Magic Packet per UDP an Port 9. Die Erfolgsmeldung
bestätigt nur das Senden, nicht den Start des Rechners. Das Ziel muss Wake-on-LAN
in Firmware und Netzwerkadapter unterstützen; Broadcast-Pakete werden nicht
beliebig über Router oder VPN weitergeleitet. Standard ist `255.255.255.255`;
bei Bedarf die Broadcast-Adresse des eigenen LANs eintragen. Es werden keine
Firewall-, Router- oder BIOS-Einstellungen verändert.

### Fokus-Timer

Wähle 25, 45 oder 60 Minuten. Die Restzeit erscheint unter den Aktionen. Der
Timer läuft bei verstecktem Popup weiter, solange der Prozess lebt. Beim Ablauf
erscheint ein Hinweis und, falls `notify-send` vorhanden ist, eine
Desktopbenachrichtigung. **Timer beenden** bricht ihn ab. Ein neuer Timer ersetzt
den bisherigen. Neustart/Beenden der App löscht den Timer. Die Zeitmessung nutzt
eine monotone Uhr; Standbyzeit zählt unter Linux nicht zur Fokuszeit.

Der Timer verändert weder „Nicht stören“ noch Energie- oder Wachhalteeinstellungen.

### Ressourcenprofile der App

Unter **Einstellungen → Ressourcenprofil der App**:

| Profil | Statusintervall bei sichtbarem Popup | Gleichzeitige Statusabfragen |
|---|---:|---:|
| Leicht | 30 Sekunden | bis 2 |
| Ausgewogen | 10 Sekunden | bis 4 |
| Reaktiv | 3 Sekunden | bis 8 |
| Individuell | bisheriger/manuell gewählter Wert | bis 4 |

Die Obergrenze wird zusätzlich an die logische CPU-Anzahl angepasst (mindestens
zwei für diese überwiegend wartenden I/O-Aufgaben). Das sind **App-Profile**, keine
CPU-Takt-, Lüfter- oder Systemenergieprofile. Ein versteckter Resident pausiert
nach der ersten Initialisierung seine regelmäßigen Statusabfragen. Der optionale
Fokus-Timer läuft weiter. Bedienaktionen bleiben in jedem Profil sofort möglich.

Bestehende Konfigurationen ohne Profilfeld erhalten „Individuell“ und behalten
ihr bisheriges Intervall. Ein Profilwechsel wartet auf das Ende laufender
Abfragen, bevor er den Threadpool ersetzt. Bereits laufende Abfragen werden beim
Verstecken nicht gewaltsam abgebrochen.

### Systemübersicht und Leistungsänderungen

Die Systemübersicht zeigt RAM, 1-Minuten-Systemlast, logische CPUs, Laufzeit und
Anhaltspunkte zur vorhandenen Werkzeug-/Hardwareunterstützung. Die Systemlast ist
kein CPU-Prozentwert. Die Daten werden beim Öffnen gelesen. **Geräte neu erkennen**
prüft optionale Kacheln erneut; der Diagnosebericht enthält das effektive
Abfrageintervall, das Profil, die letzte Poll-Dauer und fehlgeschlagene Leser.

Die Übersicht weist Werkzeug-/Sysfs-Verfügbarkeit nach, nicht die Erlaubnis für
jede Hardwareaktion. Neu angeschlossene Backlight-/Akkugeräte benötigen weiterhin
einen App-Neustart, weil deren Sysfs-Pfade beim Start bestimmt werden.

Technisch geändert wurden:

- Grundaktionen werden vor der langsamen optionalen Geräteerkennung aufgebaut.
- Unabhängige Statuswerte erscheinen sofort nach ihrer jeweiligen Abfrage;
  ein langsamer oder fehlerhafter Leser hält andere Werte nicht zurück.
- Helligkeitsänderungen laufen mit begrenztem D-Bus-Timeout in einem separaten
  Worker; Zwischenwerte werden zusammengefasst und der letzte Wert übernommen.
- SVG-Pixbufs werden begrenzt zwischengespeichert, statt sie bei jeder Suche neu
  zu parsen. Suche und Kategorien starten keine neuen Statusabfragen.
- Geräteerkennung fragt unabhängige optionale Dienste parallel und fehlerisoliert ab.
- Neue Installationen enthalten keinen voreingestellten persönlichen VPN-Namen.

Ein garantierter Startzeitwert wurde nicht gemessen. Schnelles Wiederöffnen
setzt weiterhin den laufenden Resident voraus; ein Kaltstart muss Python/GTK laden.

## Prüfstatus dieses Pakets

Die portablen Code-, Daten- und Verhaltenstests sind bestanden. Ein echter
GTK-/XFCE-Sichttest war in der Erstellungsumgebung nicht möglich. Zwei
Prozessintegrationstests scheitern dort schon mit Version 1.3.1 an abweichenden
PID-Namensräumen. Die produktive Installer-/Starterlogik wurde nicht dafür
umgeschrieben. Details und Prüfschritte stehen in `docs/VALIDATION.md` und
`docs/SMOKE-TEST.md`. Das Paket sollte vor dem produktiven Update auf dem
Ziel-Desktop geprüft werden.

## Inhaltsverzeichnis

- [Funktionen auf einen Blick](#funktionen-auf-einen-blick)
- [Hauptfenster](#hauptfenster)
- [Verbindungen und Netzwerkdetails](#verbindungen-und-netzwerkdetails)
- [Regler und Mediensteuerung](#regler-und-mediensteuerung)
- [Schnellaktionen](#schnellaktionen)
- [Kurznotizen](#kurznotizen)
- [Speicheranalyse](#speicheranalyse)
- [Lüfter- und Temperaturmonitor](#lüfter--und-temperaturmonitor)
- [Einstellungen und Bedienung](#einstellungen-und-bedienung)
- [Installation, Start und Update](#installation-start-und-update)
- [Konfiguration und Dateipfade](#konfiguration-und-dateipfade)
- [Abhängigkeiten und optionale Werkzeuge](#abhängigkeiten-und-optionale-werkzeuge)
- [Fehlerdiagnose](#fehlerdiagnose)
- [Sicherheit und bekannte Grenzen](#sicherheit-und-bekannte-grenzen)
- [Tests](#tests)

## Funktionen auf einen Blick

- WLAN, Bluetooth und VPN direkt aus einem Popup bedienen.
- WLAN-Details einschließlich Verbindung, Netzwerkgerät, Signal/Sicherheit, IPv4, Gateway und DNS anzeigen – soweit NetworkManager die Werte liefert.
- Bildschirmhelligkeit, Lautstärke, Stummschaltung, Audioausgabe und Energieprofil verwalten.
- Medienplayer über MPRIS/`playerctl` steuern, inklusive verfügbarer Artwork-Vorschau und Fortschritt.
- Schnellaktionen nach Bedarf ein- und ausblenden, sortieren und auf die Standardreihenfolge zurücksetzen.
- Mehrere private Kurznotizen speichern.
- Ordnergrößen, größte Dateien und Dateitypen analysieren.
- Lüfterdrehzahlen und Temperatursensoren samt Verlauf beobachten.
- Theme, Akzentfarbe, Sprache, Animationen und Verhalten des Control Centers konfigurieren.
- Resident-Daemon verwenden, damit der Panel-Starter dieselbe Instanz öffnet oder schließt.

## Hauptfenster

Das Control Center erscheint als deckendes, abgerundetes Popup oben rechts. Die Breite bleibt kompakt; die Höhe richtet sich nach Inhalt und verfügbarem Monitorbereich. Bei umfangreichen Menüs wird der Inhalt scrollbar, und Größenänderungen werden animiert. Die Option „Bewegung reduzieren“ beziehungsweise Animationen „Aus“ deaktiviert die meisten Übergänge.

Die Oberfläche enthält:

- **Aktionssuche:** Suche per Tastatur und Kategorien mit kompakter oder vollständiger Kachelansicht.

- **Verbindungstasten:** WLAN, Bluetooth, VPN und optional Night Shift.
- **Regler:** Bildschirmhelligkeit, Lautstärke und – sofern die Hardware es unterstützt – die Tastaturbeleuchtung als Schnellaktion.
- **Medienwidget:** nur sichtbar, wenn ein unterstützter Player Metadaten bereitstellt.
- **Schnellaktionsraster:** verfügbare Werkzeuge öffnen oder direkt steuerbare Zustände umschalten.
- **Aktionsleiste:** Energieoptionen, Schnellaktionen anpassen und Control-Center-Einstellungen. Screenshots sind über Schnellaktionen erreichbar.
- **Akkuanzeige:** erscheint, wenn passende Akkuinformationen verfügbar sind.

Ein Klick auf den Panel-Starter öffnet das existierende Popup; der nächste Klick sendet ein explizites Verstecksignal an dieselbe Resident-Instanz. Der Starter soll nicht bei jedem Klick einen zweiten Prozess erstellen.

## Verbindungen und Netzwerkdetails

### WLAN

Die WLAN-Taste zeigt den Verbindungszustand und – sofern verfügbar – die aktuelle SSID. Die Detailansicht kann verfügbare Netzwerke, Netzwerkgerät, Signalstärke, Sicherheitsart und Verbindungsinformationen anzeigen. Bei einer aktiven Verbindung werden außerdem IPv4-Adresse, Gateway und DNS-Server aufgeführt, wenn NetworkManager diese Angaben bereitstellt.

Verbindungsprofile werden über NetworkManager verwaltet. Bei geschützten Netzwerken erscheint der Passwortdialog; das Passwort wird weder in Prozessargumente geschrieben noch als Klartext in der App-Konfiguration gespeichert.

### Bluetooth

Die Detailansicht listet erkannte beziehungsweise gepaarte Geräte, soweit BlueZ/Blueman die Informationen liefert. Die Aktion zum Öffnen der erweiterten Geräteverwaltung wird nur angeboten, wenn ein geeignetes Werkzeug installiert ist.

### VPN

Die VPN-Ansicht arbeitet mit den auf dem System erkennbaren Verbindungen und vorhandenen WireGuard-/NetworkManager-Profilen. Ein bevorzugtes Profil kann über die Konfiguration bestimmt werden. Verfügbarkeit und Status hängen von den lokalen Diensten und Profilen ab.

### Night Shift / Blaulichtfilter

Wenn `gammastep` verfügbar ist, wird optional eine entsprechende Steuerung eingeblendet. Fehlt das Programm, wird keine tote Schaltfläche angezeigt.

## Regler und Mediensteuerung

### Bildschirmhelligkeit

Der Helligkeitsregler wird nur angezeigt, wenn ein geeigneter steuerbarer Bildschirmhelligkeitswert erkannt wird. Unterstützung hängt von Gerät, Kernel und Treiber ab.

### Lautstärke und Audioausgabe

Der Lautstärkeregler verwendet `pactl`/PulseAudio-kompatible Schnittstellen. Ein Klick auf das Lautsprechersymbol schaltet die Standardausgabe stumm beziehungsweise wieder hörbar. Wenn mehrere Ausgabegeräte erkannt werden, kann die Audioausgabe über eine Schnellaktion gewechselt werden.

### Tastaturbeleuchtung

Es gibt keine verwirrende Dauer-Skala: Die Schnellaktion durchläuft **Aus → An → Heller**. Auf Hardware mit nur zwei echten Zuständen werden nur die tatsächlich möglichen Stufen durchlaufen. Das Element wird nur angeboten, wenn der Kernel eine passende Tastaturbeleuchtung meldet und die System-Sitzung das Ändern erlaubt.

### Medienwidget

Aktive MPRIS-Player werden über `playerctl` erkannt. Das Widget zeigt, sofern der Player die Metadaten liefert:

- Titel und Interpret/Kanal;
- ein Vorschaubild im 16:9-Format;
- Wiedergabe-/Pause-Zustand;
- Fortschrittsbalken und Zeitposition;
- Vorheriger Titel, Wiedergabe/Pause und Nächster Titel.

YouTube im Browser funktioniert nur, wenn der Browser beziehungsweise ein Medienintegrations-Plugin MPRIS-Metadaten und gegebenenfalls eine Artwork-URL veröffentlicht. Ohne Cover wird ein neutrales Symbol angezeigt. Das Laden von Artwork läuft im Hintergrund, besitzt Zeitlimits und kann in den Einstellungen deaktiviert werden.

## Schnellaktionen

Über **Schnellaktionen anpassen** lassen sich Kacheln aktivieren/deaktivieren, mit Pfeilen neu sortieren und über „Automatische Anordnung wiederherstellen“ zurücksetzen. Die Auswahl wird gespeichert. Aktionen, die ein optionales Programm erfordern, erscheinen nur bei erkannter Verfügbarkeit; hardwareabhängige Kacheln können auf bestimmten Geräten fehlen.

Die verfügbaren Aktionen können unter anderem umfassen:

| Aktion | Funktion / Voraussetzung |
|---|---|
| LocalSend | Startet LocalSend mit einer fest eingebauten Flatpak-Dateisystem-Sandbox. |
| Wach halten | Schaltet die entsprechende Standby-Verhinderung um, wenn das dafür verwendete Werkzeug verfügbar ist. |
| Mikrofon | Schaltet das Standardmikrofon stumm/aktiv, sofern `pactl` vorhanden ist. |
| Flugmodus | Steuert Funkgeräte über `rfkill`, falls verfügbar. |
| Energieprofil | Wechselt verfügbare Power-Profile, wenn ein kompatibler Dienst sie meldet. |
| Touchscreen / Touchpad | Aktiviert/deaktiviert erkannte Eingabegeräte. |
| Bildschirm drehen | Wechselt verfügbare Rotationen, sofern die Anzeigeverwaltung dies unterstützt. |
| Audioausgabe | Wählt ein erkanntes Audioausgabegerät aus. |
| Bildschirmtastatur | Startet `onboard`, wenn installiert. |
| Tastaturbeleuchtung | Wechselt die verfügbaren Beleuchtungsstufen. |
| Screenshot-Menü / Screenshot-Ordner | Erstellt Screenshots über `xfce4-screenshooter` beziehungsweise öffnet den passenden Ordner. |
| Persönlicher Ordner / Downloads | Öffnet bekannte Benutzerordner im Standard-Dateimanager. |
| Dateimanager / Terminal | Startet ein verfügbares Programm, beispielsweise Thunar oder XFCE Terminal. |
| Zwischenablage | Öffnet die Zwischenablagehistorie, falls Clipman oder CopyQ installiert ist. |
| Netzwerk / Bluetooth / Audio / Energieeinstellungen | Öffnet passende Einstellungen, falls verfügbar. |
| Tastatur / Maus & Touchpad / Display | Öffnet die jeweiligen XFCE-Einstellungen. |
| App-Finder / Systemeinstellungen | Öffnet `xfce4-appfinder` beziehungsweise den XFCE-Einstellungsmanager. |
| Nicht stören | Steuert den XFCE-Notification-Daemon, wenn `xfconf-query` und die passende Einstellung verfügbar sind. |
| Kurznotizen | Öffnet den integrierten Notizeditor. |
| Speicheranalyse | Öffnet die integrierte Speicheranalyse. |
| Lüfter und Temperaturen | Öffnet den Sensor-Monitor. |
| Desktop anzeigen | Wird angeboten, wenn `wmctrl` verfügbar ist. |

**LocalSend-Sandbox – unveränderliche Sicherheitsregel:** Der Befehl lautet exakt `flatpak run --nofilesystem=/mnt/medien org.localsend.localsend_app`. LocalSend erhält dadurch keinen Zugriff auf den NAS-Mount `/mnt/medien`; Installer und Tests dürfen diese Beschränkung niemals aufweiten.

## Kurznotizen

Die integrierte Notizansicht unterstützt mehrere Notizen statt nur einer einzigen Textdatei:

- neue Notizen erstellen, Titel vergeben und aus einer Liste auswählen;
- Inhalt bearbeiten und mit `Strg+S` speichern;
- Notizen einzeln löschen – mit Rückfrage;
- automatische Speicherung der aktuellen Änderungen beim Wechsel beziehungsweise Schließen, sofern die Eingabe erfolgreich gespeichert werden kann;
- Migration einer älteren Einzelnotizdatei, wenn noch keine neueren Notizen vorhanden sind.

Die Dateien werden unter `~/.local/share/macos-control-center/notes/` gespeichert. Das Verzeichnis erhält Berechtigungen `0700`, einzelne Notizdateien `0600`. Pro Notiz wird JSON verwendet; die Speicherung erfolgt atomar, damit ein Programmabbruch nicht mitten in die eigentliche Datei schreibt.

## Speicheranalyse

Der Speicheranalysierer bietet drei Modi:

1. **Ordnergrößen:** Größe der Unterordner bis zu einer einstellbaren Tiefe. Hierbei wird `du -x` verwendet, damit keine anderen Dateisysteme – beispielsweise ein unterhalb des Ordners eingehängtes NAS – in den Scan hineingezogen werden.
2. **Größte Dateien:** begrenzte Liste der größten Dateien innerhalb der gewählten Tiefe.
3. **Dateitypen:** summierte Dateigröße und Anzahl pro Erweiterung.

Der Scan läuft im Hintergrund, zeigt Fortschritt und Ergebniszusammenfassung und bietet Abbruch, Öffnen/Kopieren eines ausgewählten Pfads sowie CSV-Export. Symlinks werden nicht verfolgt; Scans haben Zeit- und Eintragsgrenzen. Unlesbare Dateien werden übersprungen und soweit möglich in der Warnung kenntlich gemacht.

Die Angaben zu frei/belegt stammen vom Dateisystem, auf dem sich der gewählte Ordner befindet. Sie sind keine alleinige Berechnung des von diesem Ordner verursachten Speicherverbrauchs.

## Lüfter- und Temperaturmonitor

Die Lüfteransicht liest verfügbare Sensoren aus `/sys/class/hwmon`:

- aktuelle Lüfterdrehzahlen in RPM;
- Temperaturwerte in °C;
- verfügbare Mindest-, Höchst- und kritische Temperaturwerte;
- Verlauf der letzten Messungen sowie Min-/Durchschnitts-/Maximalwerte;
- manuelle Aktualisierung und CSV-Export;
- Schaltfläche zum Öffnen von CoolerControl, falls es installiert ist.

**Wichtig:** Der eingebaute Monitor ist absichtlich lesend. Er schreibt keine PWM- oder Kernelwerte und behauptet keine Lüftersteuerung, wenn sie von der Hardware nicht unterstützt wird. Für tatsächliche Regelkurven kann ein geeignetes separates Werkzeug wie CoolerControl verwendet werden.

## Einstellungen und Bedienung

Die Einstellungen des Control Centers sind vom globalen XFCE-Theming getrennt. Verfügbar sind:

- **Theme:** Mitternacht, Graphit oder Hell;
- **Akzentfarbe:** Blau, Violett, Türkis oder Pink;
- **Sprache:** automatisch oder Deutsch, Englisch, Italienisch, Französisch und Spanisch;
- **Animation:** flüssig, schnell oder aus, zusätzlich „Bewegung reduzieren“;
- **Aktualisierungsintervall:** 3 bis 60 Sekunden;
- **Verhalten:** Popup beim Fokusverlust schließen oder über „Geöffnet halten“ offenlassen;
- **Medienvorschaubilder:** Artwork-Laden aktivieren/deaktivieren;
- **Diagnose:** Version, Runtime, Kernel, Python, CPU/RAM und Verfügbarkeit unterstützender Werkzeuge anzeigen und Diagnosebericht kopieren.

Eine Änderung der Sprache benötigt einen Neustart des Control Centers, damit sämtliche Texte konsistent neu geladen werden. Andere Darstellungsoptionen werden möglichst sofort angewendet.

### Tastaturkürzel

| Kürzel | Aktion |
|---|---|
| `Esc` | Popup bzw. das aktuelle Menü schließen; im Passwortdialog nur die Eingabe abbrechen. |
| `Strg+F` | Aktionssuche fokussieren; Enter startet den ersten Treffer. |
| `Strg+R` | Status manuell aktualisieren. |
| `Strg+Q` | Popup schließen/verbergen. |
| `Strg+,` | Control-Center-Einstellungen öffnen. |
| `Bild ↑` / `Bild ↓` | Im scrollbaren Popup nach oben/unten springen. |
| `Pos1` / `Ende` | Zum Anfang/Ende des Popup-Inhalts springen. |
| `Strg+S` | Aktuelle Kurznotiz speichern. |

## Installation, Start und Update

### Voraussetzungen

Benötigt werden Python 3.10 oder neuer, GTK 3 und PyGObject (`gi`). Die App ist primär für Linux Mint XFCE und ähnliche X11-Desktops vorgesehen. Optionale Funktionen hängen von den verfügbaren Systemwerkzeugen ab.

### Erst testen

Im entpackten Projektverzeichnis:

```bash
bash ./run.sh
```

Dies startet den Quellbaum direkt, ohne die Installation in deinem Home-Verzeichnis zu ändern.

### Benutzerlokal installieren

```bash
bash ./install.sh
```

Der Installer installiert die Anwendung nach `~/.local/share/macos-control-center/app`, erstellt einen stabilen Starter unter `~/.local/bin/`, den Desktop-Menüeintrag, den Resident-Autostart und Diagnose-/Update-Werkzeuge. Er benötigt für die normale Installation kein `sudo` und installiert keine Systempakete ungefragt.

### Aktualisieren

Entpacke ein neues Release in einen neuen Ordner und führe dort aus:

```bash
bash ./update.sh
bash ./status.sh
```

Der Update-Prozess sichert die bisherige Programmdatei, beendet alte Instanzen – auch aus anderen Checkout-Pfaden – und verifiziert Runtime-Version/PID/Pfad, bevor er den neuen Daemon als bereit meldet. Scheitert der Start nach einem Update, versucht der Installer die vorherige Programmversion wiederherzustellen.

### Diagnose

```bash
bash ./doctor.sh
bash ./status.sh
bash ./run-tests.sh
```

`status.sh` zeigt Release, installierte Datei, aktive Prozesse und Runtime-Version. `doctor.sh` prüft häufige Abhängigkeits-, Pfad- und Startprobleme. Logs sind unter `~/.local/share/macos-control-center/logs/` zu finden.

### Deinstallation

```bash
bash ./uninstall.sh
```

Der Uninstaller entfernt Anwendung, Starter, Menüeintrag und Autostart, erhält aber die Benutzerkonfiguration, Notizen, Logs und Recovery-Backups standardmäßig. Prüfe die angezeigte Zusammenfassung vor der Bestätigung.

## Konfiguration und Dateipfade

| Daten | Ort |
|---|---|
| Konfiguration | `~/.config/macos-control-center/config.json` |
| Mehrere Kurznotizen | `~/.local/share/macos-control-center/notes/*.json` |
| Alte Einzelnotiz für einmalige Migration | `~/.local/share/macos-control-center/quick-note.txt` |
| Installation | `~/.local/share/macos-control-center/app/` |
| Recovery-Backups | `~/.local/share/macos-control-center/backups/` |
| Logs | `~/.local/share/macos-control-center/logs/` |
| Runtime-PID/Status | normalerweise unter `$XDG_RUNTIME_DIR` oder ersatzweise `/tmp` |
| Benutzerstarter | `~/.local/bin/macos-control-center-toggle` |
| Desktop-Menüeintrag | `~/.local/share/applications/macos-control-center.desktop` |
| Resident-Autostart | `~/.config/autostart/macos-control-center-resident.desktop` |

Die private Konfiguration wird atomar gespeichert. Vertrauliche Passwörter, WLAN-Geheimnisse und VPN-Schlüssel gehören nicht in die Konfigurationsdatei. Konfigurationsordner und -datei erhalten nach Möglichkeit Berechtigungen `0700` und `0600`.

## Abhängigkeiten und optionale Werkzeuge

Das Programm prüft die Verfügbarkeit benötigter Befehle zur Laufzeit; optionale Kacheln werden ausgeblendet, wenn ihr Werkzeug nicht verfügbar ist. Typische optionale Programme sind:

- `nmcli`/NetworkManager für WLAN- und Verbindungsinformationen;
- `rfkill` für Funkzustände;
- `pactl` für Lautstärke, Mikrofon und Ausgabegeräte;
- `playerctl` für MPRIS-Mediensteuerung;
- `gammastep` für Night Shift;
- `xfce4-screenshooter`, `xfce4-display-settings`, `xfce4-power-manager-settings`, `xfce4-mouse-settings` und `xfce4-settings-manager` für die entsprechenden Schnellaktionen;
- `blueman-manager` für Bluetooth-Geräte;
- Thunar, Nemo, Dolphin oder ein anderer unterstützter Dateimanager;
- XFCE Terminal, Konsole oder ein anderes erkanntes Terminal;
- Clipman oder CopyQ für die Zwischenablagehistorie;
- `wmctrl` für „Desktop anzeigen“;
- `du` für den effizienten Ordnergrößenscan;
- CoolerControl für externe Lüfterregelung.

Typische Pakete für GTK/PyGObject:

- Debian, Ubuntu, Linux Mint: `python3-gi`, `gir1.2-gtk-3.0`;
- Fedora: `python3-gobject`, `gtk3`;
- Arch/Manjaro: `python-gobject`, `gtk3`.

Paketnamen und Systemwerkzeuge unterscheiden sich je Distribution. Der Installer verändert das Basissystem nicht automatisch.

## Fehlerdiagnose

1. **Das Popup öffnet nicht oder schließt sofort:** `bash ./status.sh` ausführen und prüfen, ob Version, Codepfad und Runtime-Metadaten zusammenpassen. Danach `bash ./doctor.sh` und `~/.local/share/macos-control-center/logs/daemon.log` prüfen.
2. **Zweiter Klick startet eine neue Instanz:** sicherstellen, dass der Panel-Eintrag `~/.local/bin/macos-control-center-toggle` startet – nicht eine alte Quelldatei direkt. Der Starter liest Runtime-PID, Version, Pfad und `visible`-Zustand und sendet explizit Show oder Hide.
3. **Eine Kachel fehlt:** sie wird möglicherweise nur bei vorhandener Hardware oder installiertem Werkzeug angeboten. `doctor.sh` zeigt erkannte Abhängigkeiten.
4. **Mediacover fehlt:** der Player stellt möglicherweise kein MPRIS-Artwork bereit; Wiedergabe-Steuerung und Titel können trotzdem funktionieren.
5. **Tastaturbeleuchtung nicht verfügbar:** benötigt ein erkanntes `kbd_backlight` und die vom System erlaubte Login1-Schnittstelle. Nicht alle Treiber unterstützen drei Helligkeitsstufen.
6. **Lüfterwerte fehlen:** viele Geräte veröffentlichen keine Lüfter-RPMs unter `hwmon`; der Monitor kann nur veröffentlichte Werte anzeigen.
7. **Position unter Wayland nicht korrekt:** Fenstermanager beschränken dort teils das freie Positionieren. X11/XFCE ist die Referenzumgebung.

## Sicherheit und bekannte Grenzen

- LocalSend wird immer mit `flatpak run --nofilesystem=/mnt/medien org.localsend.localsend_app` gestartet. `/mnt/medien` wird LocalSend nicht freigegeben.
- Das Fenster bleibt deckend (`set_app_paintable(False)`) und verwendet kein RGBA-Visual.
- Installation, Tests und Updates ändern keine XFCE-Panel-, Theme-, Icon-Theme-, Plank-, Wallpaper- oder Whisker-Konfiguration.
- WLAN-Passwörter werden nicht als Prozessargumente verwendet oder in Logs geschrieben.
- Die Lüfteransicht liest Sensoren nur aus; sie schreibt keine PWM-/Kernelwerte.
- Die Anwendung kann nur Systemfunktionen steuern, die Hardware, Treiber und lokale Dienste bereitstellen.
- Die Positionierung ist auf X11 ausgelegt; Wayland-Compositoren können sie einschränken.
- `run-tests.sh` prüft Codeverträge und Pure-Python-Hilfslogik ohne echte Hardware-Schalter umzulegen. Der endgültige optische Smoke-Test sollte nach Updates auf dem Ziel-Desktop erfolgen.

## Tests

```bash
bash ./run-tests.sh
```

`bash ./run-tests.sh --portable` lässt ausdrücklich nur die beiden Prozessintegrationstests aus und meldet diese Auslassung. Für ein XFCE-Zielgerät ist der vollständige Lauf ohne Option vorgesehen.

Die Tests prüfen unter anderem Python-Syntax, fünfsprachige Texte, Konfigurationsvalidierung und -rechte, Multi-Notizspeicherung, Speicheranalysemodi, Parsing simulierter hwmon-Sensoren, Einstellungen und Schnellaktionen, Runtime-Metadaten, Daemon-Show/Hide, Update-Lifecycle, Installer-Verhalten und die LocalSend-Sandbox. Die Tests verwenden temporäre Verzeichnisse und betätigen keine echten WLAN-, Bluetooth-, VPN- oder Lüfterschalter.
