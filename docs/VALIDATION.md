# Prüfprotokoll · 2.1.0 · 2026-10-26

## 2.1 Ergebnis

`bash run-tests.sh` endet mit `ALLE PROJEKTTESTS BESTANDEN`. Enthalten sind
Settings-Konstruktion und Wiederöffnung, realitätsnahe Bluetooth-CLI-Semantik,
Audio-Discovery/Selection, stale Callback Guards, Config-Wiederherstellung,
Diagnose-Nebenwirkungsprüfung, Theme-CSS-Matrix und Strict Audit.

Die Tests prüfen keine reale Bluetooth-/Audio-Hardware. Der vorhandene Headless-
GTK-Test überspringt den echten Widget-/Stack-Teil ausdrücklich, wenn kein
Display erreichbar ist.

Die verfügbaren read-only Diagnosebefehle sind:

```text
./run.sh --diagnose
./run.sh --diagnose-bluetooth
./run.sh --diagnose-audio
```

## Ausgangsarchiv

1.3.1 erfolgreich geladen, SHA256 stimmt mit dem angehängten Prüfwert überein.
Originaltests vor Änderungen ausgeführt. Reine Python-/Konfigurations-/Utility-
Tests und Shellsyntax bestanden. Zwei Prozessintegrationstests bereits im
Original fehlgeschlagen.

## Erfolgreich in 2.1

`bash run-tests.sh --portable`: Codeverträge, fünfsprachige Texte, private
Konfiguration, Alt-Migration, Schnellaktionen, Layoutlogik, Fokus-/Togglelogik,
Notizen, Speicheranalyse, Sensorparser, Runtime-Metadaten und Shellsyntax.

Neue echte Verhaltenstests in `tests/test_v2.py`:
- Ungültige URLs, Zugangsdaten, MACs, IPs und zu große Gerätelisten abweisen.
- WOL-Paket: exakt 102 Bytes, Header und sechzehn MAC-Wiederholungen.
- Profile begrenzen Parallelität je CPU-Anzahl; eigenes Intervall bleibt möglich.
- Unicode-Suche, Kategorien und Acht-Aktionen-Grenze.
- Reale Threadpool-Aufgaben mit absichtlich blockiertem Bluetooth-Leser: schneller
  Lautstärkewert wird vorher ausgeliefert; fehlerhafte Kachelabfrage isoliert.
- Teilupdates geben den Polling-Guard nicht vorzeitig frei.
- Timer endet genau einmal und nutzt eine monotone Deadline.
- Langsamer Helligkeitsdienst blockiert den Aufrufer nicht; 10→40→90 schreibt
  bei blockierter erster Abfrage nur 10 und anschließend den letzten Wert 90.

Die GTK-Empfänger und D-Bus-Schnittstellen werden dabei durch Testobjekte ersetzt.
Das prüft Verhalten und Nebenläufigkeit, ersetzt aber keine echte GUI-Sitzung.

## Nicht erfolgreich bzw. hier nicht durchführbar

`test_install_lifecycle.py` und `test_toggle_launcher.py`: /proc zeigt äußere
Prozess-IDs, während gestartete Programme innere PIDs verwenden (NSpid enthält
zwei Werte). Beispielbefund: äußerer PID 2207, innerer PID 101. Die normalen
Linux-/proc-Prüfungen treffen deshalb nicht die laufende Testinstanz. Diese
Tests werden im portablen Modus explizit ausgelassen; der normale Testlauf
behält sie unverändert bei. Der vorgelagerte ZIP-Modus-/No-start-Installertest
hat bestanden, die vollständige Start-/Stop-Integration nicht.

Python-GTK/PyGObject und Xvfb sind hier nicht verfügbar. Ein echter Start,
Screenshot, Fokus-/Fenstermanager-Test oder Hardwaretest wurde nicht durchgeführt.
Keine gemessene Latenz- oder CPU-Verbrauchsverbesserung wird behauptet.

## Auf einem XFCE-Zielgerät

1. `bash run-tests.sh` vollständig ausführen.
2. Quellbaum über `bash run.sh` starten; Popup öffnen/schließen und mit
   `bash status.sh` Version/PID prüfen. Der Quellbaumstarter kann einen älteren
   Resident ersetzen — nicht parallel mit einem alten Stand testen.
3. Bei kleinem Monitor Suche, Kategorien und alle Aktionen auf Überlauf prüfen.
4. Unter Geräte einen Test-Weblink anlegen, bearbeiten, öffnen, löschen.
5. Nur bei bekanntem Ziel-MAC WOL testen; „gesendet“ ist kein Online-Nachweis.
6. Helligkeitsregler schnell bewegen, letzte Stufe und reaktive UI prüfen.
7. Jedes Ressourcenprofil wählen; Popup verstecken und wieder öffnen.
8. Fokus-Timer starten, verstecken, wieder öffnen, stoppen; Abschluss prüfen.
9. Auf Desktop ohne Akku/Tastaturlicht prüfen; bestehende Notizen und Config erhalten.
10. Erst nach Zielgerät-Prüfung `bash update.sh` verwenden.
