---
name: dialekt-vokabular
description: >-
  Verwaltet die Dialekt-Vokabeln der Plattform "Dialekt verbindet"
  (Liechtenstein, index.html). Nutze diese Skill immer, wenn Woerter/Vokabeln
  aus .db- (SQLite), CSV- oder JSON-Dateien eingelesen, bereinigt, dedupliziert
  und den drei Regionen Unterland, Oberland oder Triesenbergerisch (Walser)
  zugeordnet und in die Website eingebunden werden sollen. Trigger auch bei:
  "Vokabeln/Woerter hinzufuegen", "meine .db einbinden", "Dialektdaten
  aktualisieren", "Hochdeutsch/Dialekt-Paare importieren", "neue Woerter auf der
  Seite anzeigen", sowie beim Import/Update von dialect vocabulary oder beim
  Verdrahten einer Wort-Datenbank mit index.html - auch wenn "Skill" nicht
  ausdruecklich erwaehnt wird.
---

# Dialekt-Vokabular verwalten

Diese Skill bringt gesammelte Dialekt-Vokabeln (oft als `.db`-SQLite-Dateien)
strukturiert auf die Website `index.html` der Plattform **"Dialekt verbindet"**.
Sie deckt den ganzen Weg ab: Rohdaten lesen -> normalisieren, deduplizieren, den
drei Regionen zuordnen -> als kanonisches JSON ablegen -> in die Inline-Arrays
von `index.html` schreiben, ohne das bestehende Layout anzutasten.

## Wann diese Skill greift

Sobald es darum geht, **Dialekt-Woerter zu importieren, zu bereinigen oder auf
der Seite anzuzeigen**. Typische Ausloeser: "Ich habe eine .db mit Vokabeln,
bau sie ein", "Fuege diese Woerter zum Unterland hinzu", "Aktualisiere die
Dialektlisten", "Warum erscheint mein Wort nicht auf der Seite".

## Kernidee: ein kanonisches Zwischenformat

Alles laeuft ueber **eine** JSON-Datei als Quelle der Wahrheit. Rohdaten sind
uneinheitlich (verschiedene Spaltennamen, Duplikate, Tippfehler); die Website
braucht dagegen genau drei saubere Arrays. Das Zwischenformat entkoppelt beides:

```
Rohquellen (.db/.csv/.json)  --import_vocab.py-->  vokabeln.json  --update_site.py-->  index.html
```

Das kanonische Format und die drei Regionen (`unterland`, `oberland`, `walser`)
sind in **`references/data-model.md`** beschrieben. Lies diese Datei zuerst,
wenn dir der Aufbau oder die Regionszuordnung unklar ist.

## Workflow

### 1. Quelle verstehen

Bei einer unbekannten `.db` immer zuerst die Struktur ansehen - Tabellen- und
Spaltennamen sind nicht vorhersehbar:

```bash
python scripts/inspect_db.py PFAD/zu/woerter.db
```

Merke dir Tabelle sowie die Spalten fuer Hochdeutsch, Dialekt und (falls
vorhanden) Region. Details und das Spalten-Mapping stehen in
**`references/quellen-mapping.md`**.

### 2. In das kanonische Format importieren

`import_vocab.py` liest `.db`, `.csv` und `.json`, erkennt gaengige
Spaltennamen automatisch und normalisiert/dedupliziert. Jedes Wort **muss**
einer Region zugeordnet werden - entweder fest fuer die ganze Quelle
(`--category`) oder aus einer Spalte (`--category-col`):

```bash
# Ganze Datei einer Region zuordnen:
python scripts/import_vocab.py woerter.db --category unterland -o vokabeln.json

# Region steckt in einer Spalte:
python scripts/import_vocab.py alles.db --category-col region -o vokabeln.json

# Spalten explizit mappen, wenn die Auto-Erkennung nicht passt:
python scripts/import_vocab.py woerter.db \
    --table lexikon --hoch-col german --dialekt-col mundart --category oberland -o vokabeln.json
```

Mehrere Quellen in **eine** Datei zusammenfuehren, ohne Bestehendes zu
verlieren, mit `--merge`:

```bash
python scripts/import_vocab.py neu.db --category walser --merge vokabeln.json -o vokabeln.json
```

**Prüfe immer die Zusammenfassung** (gelesen / neu / Duplikate / unvollstaendig
/ ohne Region), die das Skript nach `stderr` ausgibt. Tauchen viele Eintraege
"ohne erkennbare Region" auf, stimmt das Mapping oder eine Alias-Schreibweise
nicht - siehe `references/quellen-mapping.md`.

### 3. In die Website schreiben

`update_site.py` ersetzt **nur** die drei `const ... = [ ... ]`-Bloecke in
`index.html` und laesst Styles, Layout und Funktionen unveraendert. Erst mit
`--check` trocken pruefen, dann schreiben:

```bash
python scripts/update_site.py vokabeln.json --check      # nur pruefen
python scripts/update_site.py vokabeln.json              # schreiben (+ index.html.bak)
```

Ohne `--html` sucht das Skript `index.html` im Projekt-Root. Es legt
standardmaessig ein Backup `index.html.bak` an und ist idempotent (zweiter Lauf
meldet "Keine Aenderung noetig").

### 4. Kontrollieren

Nach dem Schreiben kurz verifizieren, dass die neuen Woerter drin sind und die
Seite intakt ist:

```bash
# Vorschau der Arrays:
grep -n -A3 "const unterland" index.html
# Optionaler Syntax-Check des Skriptblocks (falls node vorhanden):
node --check <(python3 -c "import re;h=open('index.html').read();i=h.index('<script>')+8;print(h[i:])")
```

## Neue Vokabeln von Hand hinzufuegen

Fuer wenige Woerter ohne Datenbank: entweder direkt in die kanonische
`vokabeln.json` eintragen und Schritt 3 ausfuehren, oder eine kleine CSV nach
Vorlage `assets/vokabeln-vorlage.csv` anlegen und importieren:

```bash
python scripts/import_vocab.py meine_woerter.csv --category-col region --merge vokabeln.json -o vokabeln.json
```

## Wichtige Prinzipien

- **Layout nie anfassen.** Der Betreiber mag den bestehenden Aufbau. Es aendern
  sich ausschliesslich die Wortlisten - `update_site.py` ist genau dafuer gebaut.
- **Kanonisches JSON versionieren.** `vokabeln.json` ist die Quelle der
  Wahrheit; committe sie zusammen mit `index.html`, damit der Datenstand
  nachvollziehbar bleibt.
- **Beide Felder pflichtig.** Ein Eintrag ohne `hoch` oder `dialekt` ist fuer
  das Hin- und Rueckuebersetzen der Plattform nutzlos und wird verworfen.
- **Nur Standardbibliothek.** Alle Skripte laufen mit reinem `python3`, ohne
  Installation - passend zu diesem schlanken GitHub-Pages-Projekt.

## Dateien in dieser Skill

| Datei                                | Zweck                                              |
| ------------------------------------ | -------------------------------------------------- |
| `scripts/inspect_db.py`              | Struktur einer unbekannten `.db` anzeigen          |
| `scripts/import_vocab.py`            | Rohquellen -> kanonisches `vokabeln.json`          |
| `scripts/update_site.py`             | `vokabeln.json` -> Arrays in `index.html`          |
| `references/data-model.md`           | Schema, Regionen, wie `index.html` die Daten nutzt |
| `references/quellen-mapping.md`      | Spalten mappen, unbekannte Quellen zuordnen        |
| `assets/vokabeln.schema.json`        | JSON-Schema der kanonischen Datei                  |
| `assets/vokabeln-vorlage.csv`        | CSV-Vorlage zum Sammeln neuer Woerter              |
