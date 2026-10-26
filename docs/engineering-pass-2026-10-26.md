# Engineering Pass — Version 2.1.0 — 26. Oktober 2026

## Nachgewiesene P0-Ursachen

### Settings

`_build_actions` verbindet den Settings-Knopf mit `_act_toggle("settings")`.
Dieser ruft `_act_fill` und `_fill_settings` auf. Die beiden Preview-Aufrufer
übergaben einen bloßen Theme-/Accent-Namen; `_settings_choice` erwartete dagegen
`theme:<id>` beziehungsweise `accent:<id>`. Das Entpacken von `split(":", 1)`
scheiterte mit `ValueError`, bevor der Revealer geöffnet wurde.

Die Aufrufer verwenden jetzt das richtige Format. Fehler beim Aufbau werden mit
vollständigem Traceback protokolliert und als übersetzte Fehlermeldung angezeigt.
Der Bereich kann danach erneut geöffnet werden. Ein Zurück-Eintrag schließt ihn.
Settings bleibt in der vorhandenen Main-Action-Struktur; es wurde kein neuer
Stack und keine Ersatznavigation eingeführt.

`--direct` wird bis zur Anwendung durchgereicht und startet tatsächlich eine
Terminalinstanz. Zuvor konnte dieser Aufruf stattdessen einen vorhandenen Daemon
signalisieren, sodass dessen Exceptions nicht im aufrufenden Terminal erschienen.
Die Debuginstanz verändert die PID-/Runtime-Dateien des Daemons nicht.

### Bluetooth

Die Klasse definierte `_bt_worker` zweimal. Die spätere Geräteverbindungsmethode
überschrieb den Power-Worker. `on_bt` erreichte deshalb nicht
`bluetooth_set_power`, sondern übergab Generation/Zielzustand an einen Worker,
der eine MAC-Adresse und einen Verbindungszustand erwartete. Die Methoden sind
jetzt eindeutig benannt (`_bt_worker` und `_bt_device_worker`).

Zusätzlicher nachgewiesener Ablaufdefekt: Ein Soft-Block kann den Controller
vollständig aus `bluetoothctl list` verschwinden lassen. Die bisherige frühe
Rückgabe bei fehlendem Adapter verhinderte das Unblocken. Jetzt darf der
Einschaltpfad diesen Zustand prüfen und einen Soft-Block ohne Privilegien lösen;
danach erfolgt erneut eine begrenzte Adapterabfrage. Auch ein initial unbekannter
Powered-Wert verhindert den Klick nicht mehr.

Eine verfügbare Read-only-Laufzeitprobe zeigte BlueZ aktiv, System-Bus-Owner
vorhanden, keinen Controller und einen Soft-Block. Es wurde **kein** Power- oder
Unblock-Befehl auf realer Hardware ausgeführt.

Der normale Kontrollpfad bleibt `bluetoothctl list/show`, `rfkill list bluetooth`,
gegebenenfalls `rfkill unblock bluetooth`, anschließend `bluetoothctl power on/off`
und erneutes `show`. `gdbus ... --system ... NameHasOwner org.bluez` unterscheidet
bei leerer Adapterliste einen fehlenden Dienst. Es gibt keine automatische
Service-Aktivierung und kein sudo/pkexec. Allgemeine `org.bluez.Error.Failed`
werden nicht mehr als fehlender Dienst eingeordnet. Exit 0 allein gilt nicht als
Erfolg; semantische CLI-Fehler und tatsächlicher Powered-Readback werden geprüft.

Die genaue vom Nutzer erinnerte Meldung „BlueZ aktivieren fehlgeschlagen“ ist im
aktuellen Quelltext nicht vorhanden. Der Diagnosebericht nennt deshalb auch den
tatsächlich ausgeführten Scriptpfad. Weitere Hardware-/Berechtigungsursachen
können erst durch die Desktop-Prüfung ausgeschlossen werden.

## Audio und Async-Lifecycle

- Funktionierendes pactl bleibt maßgeblich, auch bei leerer Sink-Liste. wpctl ist
  Fallback, keine zweite gleichzeitig ausgewertete Gerätewahrheit.
- Defekte JSON-Einträge und unbekannte wpctl-Ausgabe werden als Fehler behandelt.
- Ein bereits bereites Audio-UI fällt bei Hintergrundabfragen nicht erneut in
  Loading. Fehler/Timeout/leeres Ergebnis bleiben explizite Endzustände.
- wpctl-Volume/Mute-Abfragen verwenden bei ausgewähltem wpctl nicht zuerst pactl.
- Das Verschieben laufender Pulse-Streams hat ein gemeinsames Zeitbudget; die
  Verifikation des neuen Default-Sinks erfolgt unabhängig davon.
- Bluetooth-Pollantworten tragen eine Generation. Antworten vor oder während
  eines Power-Vorgangs überschreiben dessen verifizierten Zustand nicht.
- Detailabfragen werden pro Bereich zusammengefasst und generationengeprüft.
  Antworten nach Page Leave oder Reentry verändern keine fremde/neue Ansicht.
- Wi-Fi-Rescans haben einen Timeout und werden reaped.
- Verspätete Rückmeldungen für VPN, Wi-Fi, Bluetooth, DND, Input, Rotation,
  Keyboard-Light, Power-Profil, Media und Tiles prüfen den Fensterlebenszyklus.
- Passwortanfragen werden beim Navigieren invalidiert. Auch erneutes Öffnen
  derselben SSID akzeptiert keine Antwort einer älteren Passwortanfrage.

## Settings, Themes und Persistenz

Die vorhandenen vier Themes (Midnight, Graphite, Frosted Dark, Light), neun
Accents, Dichte-/Quick-Action-Einstellungen, Sprache, Artwork, Motion, Fokus und
Refresh-Profile bleiben bestehen. Preview-Konstruktion ist jetzt getestet.
Alle Themes besitzen zusätzlich eigene Warning-/Destructive-Farben; Light nutzt
dunklere Fehlermeldungsfarben. Layoutdimensionen und Main-Komposition bleiben gleich.

Neu sind drei persistierte Optionen: Wiedergabefortschritt, Media bei fehlendem
Player ausblenden, Erfolgsmeldungen. Fehler bleiben unabhängig davon sichtbar.
Defaults bewahren die bisherige Darstellung. Es werden keine unzuverlässigen
Auto-Themes, unvollständigen Sprachen oder frei konfigurierbaren Pollingraten angeboten.

Config verwendet Schema-Version 1, validierte Defaults und atomischen Ersatz mit
fsync sowie privaten Dateirechten. Beschädigte Dateien werden vor dem Speichern
privat gesichert. Größere unbekannte Dateien und zukünftige Schema-Versionen
werden nicht überschrieben. Unbekannte Schlüssel bleiben beim Speichern erhalten.
Config-Symlinks werden nicht beschrieben. Fehlerhafte Reads laden sichere Defaults.

## Performance und geprüfte Integrationen

| Bereich | Beurteilung / Änderung |
|---|---|
| GTK-Startup | Konstruktion liest lokale sysfs-/procfs-Werte; Hardware-Discovery und Polling laufen in Workern. Kein Display-Workaround. |
| DND | Entferntes synchrones `dict.get(..., notification_dnd_state())`: der Default-Ausdruck wurde zuvor auch bei vorhandenem Cache ausgeführt. |
| Awake / Night Shift | pgrep/pkill und Zustandsprüfung aus GTK-Callbacks in Worker verschoben; alle subprocess.run-Aufrufe haben Timeouts. |
| NetworkManager | Vorhandene nmcli-Worker beibehalten; Scan und verspätete UI-Antworten gehärtet. |
| BlueZ | System-Bus-Owner-Diagnose; Adapter-Power über bluetoothctl; keine Dienststeuerung. |
| PipeWire / PulseAudio | pactl bevorzugt; wpctl-Fallback, überprüfter Default-Sink und endliche Discovery. |
| MPRIS | Bestehendes playerctl und Artwork-Generation beibehalten; neue Media-Optionen und Destroy-Guards. |
| UPower / Akku | Vorhandene sysfs-Grunddaten und zeitbegrenzte Hintergrundabfrage beibehalten. |
| XRandR / Input | Vorhandene Worker und Timeouts beibehalten; Completion-Guards ergänzt. |
| Storage / Sensors | Vorhandene begrenzte/cancelbare Storage-Scans und Dialog-Monitoring beibehalten. Keine neue Polling-Schicht. |

Kein vollständiger Event-/D-Bus-Rewrite: vorhandene begrenzte Polling-Worker und
das Pausieren des residenten Fensters im verborgenen Zustand bleiben erhalten.
Keine neue generische Hardware-Abstraktion; vorhandene Ergebnis-Dictionaries
und Generation Guards wurden an konkret fehlerhaften Grenzen verbessert.

## Diagnostik und Sicherheit

`./run.sh --diagnose`, `--diagnose-bluetooth`, `--diagnose-audio` sind read-only,
benötigen kein Display und signalisieren keinen Daemon. Bluetooth-Berichte zeigen
Dienst-/Bus-/Adapter-/rfkill-Zustände getrennt. Audio zeigt ausgewähltes Backend,
Servertyp, Ausgänge, Default-Index und Volume-/Mute-Lesbarkeit. Die allgemeine
Matrix kennzeichnet CLI-Verfügbarkeit ausdrücklich als solche, nicht als
Nachweis funktionierender Hardware. MAC-Adressen werden entfernt; Netzwerk- und
Playernamen werden nicht benötigt. Keine Passwörter/Keys/Tokens werden ausgegeben.

libpulse kann bei Leseoperationen Cookies erzeugen. Diagnoseaufrufe verwenden
deshalb eine private, nachher gelöschte temporäre Client-Konfiguration, explizite
Socket-Verbindung und isolierten Config-Pfad. Keine persistenten Config-Dateien
werden erzeugt und kein Audio-Server wird automatisch gestartet.

Static Audit: keine doppelten Methoden/Dictionary-Keys, kein shell=True,
os.system, eval/exec, keine unbeschränkten subprocess.run-Aufrufe, keine
privilegierte Bluetooth-Service-Aktivierung. LocalSend bleibt exakt:
`flatpak run --nofilesystem=/mnt/medien org.localsend.localsend_app`.

## Tests und Grenzen

Neue Tests führen tatsächliche Settings-Konstruktoren, Signals, Back und
Wiederöffnung aus. Mit erreichbarem Display wird dasselbe Szenario zusätzlich
mit echten GTK-Widgets und dem Main-Stack ausgeführt; hier wird dieser Teil
explizit übersprungen. Headless-Widgets sind kein Ersatz für die Sichtprüfung.

Bluetooth-Tests modellieren CLI-Zustandsübergänge und führen zusätzlich die echte
Kette `on_bt -> Thread-Ziel -> Backend -> idle callback -> UI-State` aus. Die
Suite prüft Soft-/Hard-Block, verborgenen/fehlenden Adapter, fehlenden Dienst,
Permission, Timeout, semantischen Fehler trotz Exit 0 und unveränderten Readback.
Weitere Tests decken verspätete Polls, Page Leave/Reentry, zerstörte Widgets,
Passwort-Generationen, Media-Persistenz/Visibility, kaputte Configs und CLI-Diagnose ab.

Abschlussergebnis: `bash run-tests.sh` **Exit 0**, keine unerwarteten Exceptions;
alle Shell-Syntaxprüfungen bestanden. Der Lauf umfasst Python-/Shell-Syntax, 4 × 9 GTK-CSS-Parser-
Matrix, Navigation, Config, Hardware-Mocks, Media, Network-Verträge,
Installer-/Update-/Launcher-Integration und `tests/strict_audit.py`.
Strict Audit ist ein automatischer statischer Gate, kein Beweis realer Hardwarefunktion.

Nicht live verifiziert: echte Settings-Anzeige/Interaktion unter XFCE, Bluetooth
ON/OFF/Verbindung, Audio-Gerätewechsel/Volume/Mute, Wi-Fi/VPN-Verbindungswechsel,
XRandR-/Power-Aktionen. Erfolgreiche Audio-Lesediagnose in der verfügbaren Umgebung
zeigte PipeWire via PulseAudio und einen Default-Ausgang. Das ersetzt keine
Schreib-/Interaktionsprüfung auf dem Desktop.

## Anschließende Desktop-Prüfung

```bash
./run.sh --direct
./run.sh --diagnose-bluetooth
./run.sh --diagnose-audio
```

In der direkten Instanz Settings mehrfach öffnen/zurück, Theme/Accent wechseln,
Bluetooth an/aus, Sound-Ausgabe/Volume/Mute prüfen. Danach Instanz schließen und
erneut starten, um Persistenz zu kontrollieren. Keine weiteren experimentellen
Features sind Teil dieses Durchgangs.
