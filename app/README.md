# Dialekt-Vokabel-Manager (Desktop-App)

Eine kleine Desktop-App, um die Dialekt-Vokabeln der Plattform **„Dialekt
verbindet"** zu verwalten und in die Website `index.html` zu schreiben – ohne
Kommandozeile. Sie ist das Gegenstück zur Skill `dialekt-vokabular`: dieselbe
Logik, aber mit grafischer Oberfläche und als Windows-`.exe` paketierbar.

## Was die App kann

- **Importieren** aus `.db` (SQLite), `.csv`/`.tsv` und `.json` – mit
  automatischer Spaltenerkennung und manuellem Mapping, falls die Spaltennamen
  ungewöhnlich sind.
- **Struktur prüfen**: unbekannte `.db`-Dateien anzeigen (Tabellen, Spalten,
  Beispielzeilen), um das richtige Mapping zu finden.
- **Bearbeiten**: Wörter je Region (Unterland / Oberland / Triesenbergerisch)
  hinzufügen, ändern, löschen – Duplikate werden automatisch verhindert.
- **Speichern/Öffnen** der kanonischen `vokabeln.json`.
- **Website aktualisieren**: schreibt die drei Vokabel-Arrays in `index.html`
  und lässt Layout und Rest der Seite unangetastet (mit Backup `index.html.bak`).

## Lokal starten (Python)

Voraussetzung: Python 3.9+ mit `tkinter` (unter Windows/macOS Teil der
offiziellen Installation; unter Linux ggf. `sudo apt install python3-tk`).

```bash
cd app
python dialekt_app.py
```

Es werden **keine** zusätzlichen Pakete zur Laufzeit benötigt – alles läuft mit
der Standardbibliothek.

## Als Windows-.exe

Die `.exe` wird automatisch per GitHub Actions gebaut
(`.github/workflows/build-windows-exe.yml`):

1. Im GitHub-Repo auf **Actions** → **„Windows-.exe bauen"** gehen.
2. Entweder wartet man auf den automatischen Lauf (nach Änderungen unter
   `app/`) oder startet ihn per **„Run workflow"** manuell.
3. Nach dem Lauf die `.exe` unter **Artifacts →
   `dialekt-vokabel-manager-windows`** herunterladen.

Selbst bauen (auf einem Windows-Rechner):

```bash
cd app
pip install -r requirements.txt
pyinstaller --clean --noconfirm dialekt-app.spec
# Ergebnis: app/dist/dialekt-vokabel-manager.exe
```

## Aufbau

```
app/
├── dialekt_app.py        # Tkinter-Oberfläche (Einstiegspunkt)
├── core/                 # GUI-freie Kernlogik (getestet, wiederverwendbar)
│   ├── model.py          # Datenmodell + kanonische vokabeln.json
│   ├── importer.py       # Import aus .db/.csv/.json + .db-Struktur prüfen
│   └── site.py           # index.html aktualisieren
├── dialekt-app.spec      # PyInstaller-Konfiguration
└── requirements.txt      # nur Build-Abhängigkeit (pyinstaller)
```

Das kanonische Datenformat und die drei Dialektregionen sind in
`.claude/skills/dialekt-vokabular/references/data-model.md` dokumentiert.

## Hinweis zum Test

Die **Kernlogik** (`core/`) ist plattformunabhängig getestet. Die
**GUI-Schicht** wird beim `.exe`-Build importiert und geprüft, das eigentliche
Fensterverhalten testest du am besten einmal lokal, da es eine grafische
Oberfläche voraussetzt.
