# Quellen richtig zuordnen (Spalten-Mapping)

Die vom Betreiber gesammelten `.db`-Dateien haben oft **keine dokumentierte
Struktur** - Tabellen- und Spaltennamen variieren. Diese Datei hilft, eine
unbekannte Quelle korrekt in das kanonische Format zu bringen.

## Schritt 1: Struktur ansehen

```bash
python scripts/inspect_db.py PFAD/zu/woerter.db
```

Zeigt Tabellen, Spalten und ein paar Beispielzeilen. Danach weisst du,

- welche **Tabelle** die Vokabeln enthaelt (falls mehrere),
- welche Spalte das **Hochdeutsch-Wort** ist,
- welche Spalte das **Dialekt-Wort** ist,
- ob es eine **Regions-/Kategorie-Spalte** gibt.

Bei CSV/JSON genuegt ein Blick in die ersten Zeilen der Datei.

## Schritt 2: Auto-Erkennung oder explizites Mapping

`import_vocab.py` erkennt gaengige Spaltennamen automatisch (Gross-/
Kleinschreibung egal). Aktuelle Kandidaten:

- **hoch**: hoch, hochdeutsch, standard, schriftsprache, deutsch, german, de,
  begriff, wort, word, lemma
- **dialekt**: dialekt, dialect, mundart, dialektwort, dialektform,
  uebersetzung, übersetzung, translation, di
- **kategorie**: kategorie, category, region, dialektregion, gemeinde, ort

Passen die Namen nicht, mappe explizit:

```bash
python scripts/import_vocab.py woerter.db \
    --table lexikon --hoch-col german --dialekt-col mundart --category oberland
```

## Schritt 3: Region festlegen

Jedes Wort muss genau einer Region zugeordnet werden. Zwei Wege:

1. **Feste Region** fuer die ganze Quelle - wenn eine `.db` nur Unterland-
   Woerter enthaelt:

   ```bash
   python scripts/import_vocab.py unterland.db --category unterland
   ```

2. **Region aus einer Spalte** - wenn die Quelle gemischt ist und eine
   Regions-Spalte hat:

   ```bash
   python scripts/import_vocab.py alles.db --category-col region
   ```

   Der Importer normalisiert Schreibweisen (z.B. `Triesenbergerisch` -> `walser`).
   Zeilen mit unbekannter Region werden **nicht** importiert, sondern in der
   Zusammenfassung als "ohne erkennbare Region" gezaehlt. Taucht dort etwas auf,
   ergaenze die Aliasliste `CATEGORY_ALIASES` in `scripts/import_vocab.py`.

## Was der Importer automatisch macht

- **Normalisieren**: Rand-Whitespace entfernen, mehrfaches Whitespace zu einem
  Leerzeichen zusammenziehen, geschuetzte Leerzeichen ersetzen.
- **Unvollstaendige Eintraege** (leeres `hoch` oder `dialekt`) verwerfen.
- **Duplikate** innerhalb einer Region entfernen (case-insensitiv auf dem Paar
  `hoch`+`dialekt`).
- **Sortieren** nach `hoch` fuer stabile Diffs.
- **Mergen**: mit `--merge bestehende.json` werden neue Woerter zu einer
  vorhandenen kanonischen Datei hinzugefuegt, ohne bestehende zu verlieren.

Die Zusammenfassung am Ende (gelesen / neu / Duplikate / unvollstaendig / ohne
Region) ist die Kontrolle: pruefe sie, bevor du auf die Website schreibst.
