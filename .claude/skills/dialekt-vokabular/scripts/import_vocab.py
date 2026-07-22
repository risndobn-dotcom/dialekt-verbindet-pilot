#!/usr/bin/env python3
"""Importiere Dialekt-Vokabeln aus .db (SQLite), CSV oder JSON in das
kanonische Format der Plattform "Dialekt verbindet".

Kanonisches Format (siehe references/data-model.md):

    {
      "unterland": [{"hoch": "Hallo", "dialekt": "Hoi"}, ...],
      "oberland":  [...],
      "walser":    [...]
    }

- "hoch"    = Hochdeutsch / Schriftsprache
- "dialekt" = Dialektform (Unterland, Oberland oder Triesenbergerisch/Walser)

Nur Python-Standardbibliothek - keine Installation noetig.

Beispiele
---------
Eine ganze .db-Datei einer Region zuordnen (alle Zeilen -> Unterland):

    python import_vocab.py woerter.db --category unterland -o vokabeln.json

Spalten explizit mappen (wenn die Auto-Erkennung nicht passt):

    python import_vocab.py woerter.db --table lexikon \
        --hoch-col german --dialekt-col mundart --category oberland

Kategorie steckt in einer Spalte der Quelle:

    python import_vocab.py alles.csv --category-col region

Mehrere Quellen in eine bestehende Datei mergen:

    python import_vocab.py neu.db --category walser --merge vokabeln.json -o vokabeln.json
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys

# Kanonische Kategorie-Schluessel, die index.html erwartet.
CATEGORIES = ("unterland", "oberland", "walser")

# Schreibweisen aus den Quelldaten -> kanonischer Schluessel.
CATEGORY_ALIASES = {
    "unterland": "unterland",
    "ul": "unterland",
    "oberland": "oberland",
    "ol": "oberland",
    "walser": "walser",
    "triesenberg": "walser",
    "triesenbergerisch": "walser",
    "triesenberger": "walser",
    "trisabaergerisch": "walser",
    "trisabärgerisch": "walser",
    "walserdeutsch": "walser",
}

# Kandidaten fuer die Auto-Erkennung der Spalten (klein geschrieben).
HOCH_CANDIDATES = (
    "hoch", "hochdeutsch", "standard", "schriftsprache", "deutsch",
    "german", "de", "begriff", "wort", "word", "lemma",
)
DIALEKT_CANDIDATES = (
    "dialekt", "dialect", "mundart", "dialektwort", "dialektform",
    "uebersetzung", "übersetzung", "translation", "di",
)
CATEGORY_CANDIDATES = (
    "kategorie", "category", "region", "dialektregion", "dialekt_region",
    "gemeinde", "ort",
)


def normalize_text(value):
    """Trimme Rand-Whitespace und staure interne Whitespace-Folgen zu einem
    Leerzeichen zusammen. Gibt None zurueck, wenn nichts uebrig bleibt."""
    if value is None:
        return None
    text = str(value).replace(" ", " ")  # geschuetztes Leerzeichen -> normal
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def canonical_category(name):
    """Mappe eine beliebige Regionsbezeichnung auf einen kanonischen Schluessel."""
    if name is None:
        return None
    key = re.sub(r"\s+", "", str(name).strip().lower())
    return CATEGORY_ALIASES.get(key)


def pick_column(available, candidates, explicit=None):
    """Waehle eine Spalte: explizit hat Vorrang, sonst erster Treffer aus den
    Kandidaten (Gross-/Kleinschreibung egal)."""
    if explicit:
        for col in available:
            if col.lower() == explicit.lower():
                return col
        raise SystemExit(
            f"Spalte '{explicit}' nicht gefunden. Vorhanden: {', '.join(available)}"
        )
    lower_map = {col.lower(): col for col in available}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def read_sqlite(path, table=None):
    """Lies eine SQLite-Datei und liefere (spalten, zeilen-als-dicts)."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if table is None:
            cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [r[0] for r in cur.fetchall()]
            if not tables:
                raise SystemExit(f"Keine Tabellen in '{path}' gefunden.")
            table = tables[0]
            if len(tables) > 1:
                print(
                    f"Hinweis: mehrere Tabellen {tables} - verwende '{table}'. "
                    f"Mit --table waehlst du eine andere.",
                    file=sys.stderr,
                )
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, [dict(r) for r in rows]
    finally:
        conn.close()


def read_csv(path):
    """Lies eine CSV/TSV-Datei mit Kopfzeile und liefere (spalten, zeilen)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.DictReader(fh, delimiter=delimiter)
        columns = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return columns, rows


def read_json(path):
    """Lies eine JSON-Datei. Akzeptiert entweder das kanonische Format
    (Objekt mit Kategorie-Schluesseln) oder eine flache Liste von Objekten."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and any(k in data for k in CATEGORIES):
        rows = []
        for cat in CATEGORIES:
            for entry in data.get(cat, []):
                item = dict(entry)
                item.setdefault("_category", cat)
                rows.append(item)
        columns = ["hoch", "dialekt", "_category"]
        return columns, rows
    if isinstance(data, list):
        columns = list(data[0].keys()) if data else []
        return columns, [dict(r) for r in data]
    raise SystemExit("JSON weder kanonisches Objekt noch Liste von Objekten.")


def load_source(path, table=None):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".db", ".sqlite", ".sqlite3"):
        return read_sqlite(path, table)
    if ext in (".csv", ".tsv"):
        return read_csv(path)
    if ext == ".json":
        return read_json(path)
    # Unbekannte Endung: als SQLite versuchen (viele .db-Dateien tragen keine).
    try:
        return read_sqlite(path, table)
    except sqlite3.DatabaseError:
        raise SystemExit(f"Unbekanntes Format fuer '{path}' ({ext or 'ohne Endung'}).")


def empty_store():
    return {cat: [] for cat in CATEGORIES}


def load_existing(path):
    if not path:
        return empty_store()
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    store = empty_store()
    for cat in CATEGORIES:
        for entry in data.get(cat, []):
            h = normalize_text(entry.get("hoch"))
            d = normalize_text(entry.get("dialekt"))
            if h and d:
                store[cat].append({"hoch": h, "dialekt": d})
    return store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+", help="Eine oder mehrere Quelldateien (.db/.csv/.json)")
    parser.add_argument("--table", help="Tabellenname (nur SQLite, sonst erste Tabelle)")
    parser.add_argument("--hoch-col", help="Spalte mit dem Hochdeutsch-Wort")
    parser.add_argument("--dialekt-col", help="Spalte mit dem Dialekt-Wort")
    parser.add_argument("--category-col", help="Spalte mit der Regionsbezeichnung")
    parser.add_argument("--category", choices=CATEGORIES,
                        help="Feste Kategorie fuer alle Zeilen der Quelle")
    parser.add_argument("--merge", help="Bestehende kanonische JSON-Datei, in die gemergt wird")
    parser.add_argument("-o", "--output", help="Zieldatei (Default: stdout)")
    args = parser.parse_args(argv)

    if not args.category and not args.category_col:
        parser.error("Bitte --category ODER --category-col angeben, "
                     "damit jedes Wort einer Region zugeordnet werden kann.")

    store = load_existing(args.merge)
    # Set zur Duplikat-Erkennung (case-insensitiv) pro Kategorie.
    seen = {cat: {(e["hoch"].lower(), e["dialekt"].lower()) for e in store[cat]}
            for cat in CATEGORIES}

    stats = {"gelesen": 0, "hinzugefuegt": 0, "duplikate": 0, "unvollstaendig": 0, "ohne_region": 0}

    for path in args.sources:
        columns, rows = load_source(path, args.table)
        hoch_col = pick_column(columns, HOCH_CANDIDATES, args.hoch_col)
        dialekt_col = pick_column(columns, DIALEKT_CANDIDATES, args.dialekt_col)
        cat_col = pick_column(columns, CATEGORY_CANDIDATES, args.category_col) if args.category_col else \
            (pick_column(columns, CATEGORY_CANDIDATES) if not args.category else None)

        if hoch_col is None or dialekt_col is None:
            raise SystemExit(
                f"'{path}': Spalten nicht erkannt. Gefunden: {', '.join(columns)}. "
                f"Bitte mit --hoch-col/--dialekt-col mappen. "
                f"(Tipp: scripts/inspect_db.py zeigt die Struktur.)"
            )
        print(f"'{path}': hoch='{hoch_col}', dialekt='{dialekt_col}'"
              + (f", kategorie='{cat_col}'" if cat_col else ""), file=sys.stderr)

        for row in rows:
            stats["gelesen"] += 1
            h = normalize_text(row.get(hoch_col))
            d = normalize_text(row.get(dialekt_col))
            if not h or not d:
                stats["unvollstaendig"] += 1
                continue
            if args.category:
                cat = args.category
            else:
                cat = canonical_category(row.get(cat_col))
            if cat not in CATEGORIES:
                stats["ohne_region"] += 1
                continue
            key = (h.lower(), d.lower())
            if key in seen[cat]:
                stats["duplikate"] += 1
                continue
            seen[cat].add(key)
            store[cat].append({"hoch": h, "dialekt": d})
            stats["hinzugefuegt"] += 1

    # Stabil sortieren nach Hochdeutsch, damit Diffs klein bleiben.
    for cat in CATEGORIES:
        store[cat].sort(key=lambda e: e["hoch"].lower())

    payload = json.dumps(store, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"-> {args.output} geschrieben.", file=sys.stderr)
    else:
        sys.stdout.write(payload)

    print(
        "Zusammenfassung: "
        f"{stats['gelesen']} gelesen, {stats['hinzugefuegt']} neu, "
        f"{stats['duplikate']} Duplikate, {stats['unvollstaendig']} unvollstaendig, "
        f"{stats['ohne_region']} ohne erkennbare Region. "
        + " | ".join(f"{cat}: {len(store[cat])}" for cat in CATEGORIES),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
