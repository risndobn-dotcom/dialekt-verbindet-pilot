#!/usr/bin/env python3
"""Zeige die Struktur einer unbekannten SQLite-.db-Datei an.

Die vom Betreiber gesammelten Vokabel-Dateien haben oft keine dokumentierte
Struktur. Dieses Skript listet Tabellen, Spalten und ein paar Beispielzeilen,
damit man das richtige Mapping fuer import_vocab.py findet
(--table, --hoch-col, --dialekt-col, --category-col).

Beispiel
--------
    python inspect_db.py woerter.db
    python inspect_db.py woerter.db --rows 10
"""

import argparse
import sqlite3
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db", help="Pfad zur SQLite-Datei (.db/.sqlite)")
    parser.add_argument("--rows", type=int, default=5, help="Beispielzeilen pro Tabelle (Default: 5)")
    args = parser.parse_args(argv)

    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as exc:
        raise SystemExit(f"Kann '{args.db}' nicht oeffnen: {exc}")
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            raise SystemExit("Keine Tabellen gefunden - ist das wirklich eine SQLite-Datei?")

        print(f"Datei: {args.db}")
        print(f"Tabellen ({len(tables)}): {', '.join(tables)}\n")

        for table in tables:
            cur.execute(f'PRAGMA table_info("{table}")')
            cols = cur.fetchall()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            total = cur.fetchone()[0]
            print(f"== Tabelle '{table}' ({total} Zeilen) ==")
            print("  Spalten:")
            for c in cols:
                print(f"    - {c['name']} ({c['type'] or 'ohne Typ'})")
            if args.rows > 0 and total:
                cur.execute(f'SELECT * FROM "{table}" LIMIT {args.rows}')
                sample = cur.fetchall()
                names = [d[0] for d in cur.description]
                print(f"  Beispielzeilen (max {args.rows}):")
                for r in sample:
                    values = {n: r[n] for n in names}
                    print(f"    {values}")
            print()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
