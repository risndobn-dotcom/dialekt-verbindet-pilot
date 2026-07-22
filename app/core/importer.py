"""Import von Vokabeln aus .db (SQLite), CSV/TSV und JSON in einen VocabStore.

Erkennt gaengige Spaltennamen automatisch und normalisiert/dedupliziert ueber
den VocabStore. Reine Standardbibliothek.
"""

import csv
import os
import sqlite3

from .model import CATEGORIES, VocabStore, canonical_category, normalize_text

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

DB_EXTS = (".db", ".sqlite", ".sqlite3")
CSV_EXTS = (".csv", ".tsv")


class ImportError_(Exception):
    """Fuer erwartbare, dem Nutzer erklaerbare Importfehler."""


def pick_column(available, candidates, explicit=None):
    if explicit:
        for col in available:
            if col.lower() == explicit.lower():
                return col
        raise ImportError_(
            f"Spalte '{explicit}' nicht gefunden. Vorhanden: {', '.join(available)}"
        )
    lower_map = {col.lower(): col for col in available}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def list_tables(path):
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def inspect_db(path, sample_rows=5):
    """Liefere eine menschenlesbare Beschreibung der Struktur einer .db."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    lines = [f"Datei: {os.path.basename(path)}"]
    try:
        cur = conn.cursor()
        tables = list_tables(path)
        if not tables:
            return "Keine Tabellen gefunden - ist das eine SQLite-Datei?"
        lines.append(f"Tabellen ({len(tables)}): {', '.join(tables)}")
        for table in tables:
            cur.execute(f'PRAGMA table_info("{table}")')
            cols = cur.fetchall()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            total = cur.fetchone()[0]
            lines.append("")
            lines.append(f"== {table} ({total} Zeilen) ==")
            lines.append("  Spalten: " + ", ".join(f"{c['name']}" for c in cols))
            if sample_rows and total:
                cur.execute(f'SELECT * FROM "{table}" LIMIT {sample_rows}')
                names = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    lines.append("    " + str({n: r[n] for n in names}))
    finally:
        conn.close()
    return "\n".join(lines)


def read_sqlite(path, table=None):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if table is None:
            tables = list_tables(path)
            if not tables:
                raise ImportError_(f"Keine Tabellen in '{os.path.basename(path)}'.")
            table = tables[0]
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, [dict(r) for r in rows]
    finally:
        conn.close()


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.DictReader(fh, delimiter=delimiter)
        columns = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return columns, rows


def read_json(path):
    import json
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and any(k in data for k in CATEGORIES):
        rows = []
        for cat in CATEGORIES:
            for entry in data.get(cat, []):
                item = dict(entry)
                item.setdefault("_category", cat)
                rows.append(item)
        return ["hoch", "dialekt", "_category"], rows
    if isinstance(data, list):
        columns = list(data[0].keys()) if data else []
        return columns, [dict(r) for r in data]
    raise ImportError_("JSON weder kanonisches Objekt noch Liste von Objekten.")


def load_source(path, table=None):
    ext = os.path.splitext(path)[1].lower()
    if ext in DB_EXTS:
        return read_sqlite(path, table)
    if ext in CSV_EXTS:
        return read_csv(path)
    if ext == ".json":
        return read_json(path)
    try:
        return read_sqlite(path, table)
    except sqlite3.DatabaseError:
        raise ImportError_(f"Unbekanntes Format: {os.path.basename(path)} ({ext or 'ohne Endung'}).")


def import_into(store, path, category=None, category_col=None,
                hoch_col=None, dialekt_col=None, table=None):
    """Importiere eine Quelle in einen bestehenden VocabStore.

    Genau eines von `category` (feste Region) oder `category_col`
    (Regions-Spalte) muss die Zuordnung liefern; wird keins angegeben, versucht
    die Funktion, eine Kategorie-Spalte automatisch zu erkennen.

    Rueckgabe: dict mit Statistik.
    """
    columns, rows = load_source(path, table)
    hcol = pick_column(columns, HOCH_CANDIDATES, hoch_col)
    dcol = pick_column(columns, DIALEKT_CANDIDATES, dialekt_col)
    if category:
        ccol = None
    elif category_col:
        ccol = pick_column(columns, CATEGORY_CANDIDATES, category_col)
    else:
        ccol = pick_column(columns, CATEGORY_CANDIDATES)

    if hcol is None or dcol is None:
        raise ImportError_(
            "Spalten nicht erkannt. Gefunden: " + ", ".join(columns)
            + ". Bitte Hochdeutsch- und Dialekt-Spalte manuell zuordnen."
        )
    if not category and ccol is None:
        raise ImportError_(
            "Keine Region bestimmbar: entweder eine feste Region waehlen oder "
            "eine Regions-Spalte angeben."
        )

    stats = {"gelesen": 0, "neu": 0, "duplikate": 0, "unvollstaendig": 0,
             "ohne_region": 0, "hoch_col": hcol, "dialekt_col": dcol, "kategorie_col": ccol}
    for row in rows:
        stats["gelesen"] += 1
        h = normalize_text(row.get(hcol))
        d = normalize_text(row.get(dcol))
        if not h or not d:
            stats["unvollstaendig"] += 1
            continue
        cat = category if category else canonical_category(row.get(ccol))
        if cat not in CATEGORIES:
            stats["ohne_region"] += 1
            continue
        if store.add(cat, h, d):
            stats["neu"] += 1
        else:
            stats["duplikate"] += 1
    return stats
