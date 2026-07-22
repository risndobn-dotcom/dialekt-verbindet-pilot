#!/usr/bin/env python3
"""Schreibe kanonische Vokabel-Daten in die JavaScript-Arrays von index.html.

Die Seite haelt die Vokabeln als drei Inline-Arrays im <script>-Block:

    const unterland = [
    {hoch:"Hallo",dialekt:"Hoi"},
    ...
    ]

Dieses Skript ersetzt genau diese drei Bloecke (unterland/oberland/walser)
durch den Inhalt einer kanonischen JSON-Datei (siehe import_vocab.py) und
laesst den Rest der Datei unveraendert. So bleibt das Layout, das dem Betreiber
gefaellt, exakt erhalten - es aendern sich nur die Wortlisten.

Standardmaessig wird ein Backup index.html.bak angelegt.

Beispiele
---------
    python update_site.py vokabeln.json
    python update_site.py vokabeln.json --html ../../index.html
    python update_site.py vokabeln.json --check   # nur pruefen, nichts schreiben
"""

import argparse
import json
import os
import re
import sys

CATEGORIES = ("unterland", "oberland", "walser")


def render_array(name, entries):
    """Erzeuge ein JS-Array-Literal im Stil der bestehenden Seite.

    json.dumps liefert korrekt escapte, doppelt gequotete Strings - damit sind
    Anfuehrungszeichen, Backslashes und Umlaute in den Woertern sicher."""
    lines = [f"const {name} = ["]
    body = []
    for e in entries:
        hoch = json.dumps(e["hoch"], ensure_ascii=False)
        dialekt = json.dumps(e["dialekt"], ensure_ascii=False)
        body.append(f"{{hoch:{hoch},dialekt:{dialekt}}}")
    lines.append(",\n".join(body))
    lines.append("]")
    # Bei leerem Array keine leere Zeile in der Mitte.
    if not body:
        return f"const {name} = []"
    return "\n".join(lines)


def load_data(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    store = {}
    for cat in CATEGORIES:
        entries = []
        for e in data.get(cat, []):
            if e.get("hoch") and e.get("dialekt"):
                entries.append({"hoch": e["hoch"], "dialekt": e["dialekt"]})
        store[cat] = entries
    return store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", help="Kanonische JSON-Datei mit den Vokabeln")
    parser.add_argument("--html", default=None,
                        help="Pfad zu index.html (Default: Projekt-Root relativ zum Skript)")
    parser.add_argument("--no-backup", action="store_true", help="Kein index.html.bak anlegen")
    parser.add_argument("--check", action="store_true",
                        help="Nur pruefen, ob alle Bloecke gefunden werden - nichts schreiben")
    args = parser.parse_args(argv)

    html_path = args.html
    if html_path is None:
        # scripts/ -> dialekt-vokabular/ -> skills/ -> .claude/ -> Projekt-Root
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        html_path = os.path.join(root, "index.html")
    html_path = os.path.abspath(html_path)

    if not os.path.exists(html_path):
        raise SystemExit(f"index.html nicht gefunden: {html_path} (mit --html Pfad angeben).")

    store = load_data(args.data)
    with open(html_path, encoding="utf-8") as fh:
        html = fh.read()

    missing = []
    counts = {}
    new_html = html
    for cat in CATEGORIES:
        # Nicht-gierig bis zur ersten schliessenden Klammer; die Arrays enthalten
        # selbst keine ']' , daher ist das eindeutig.
        pattern = re.compile(r"const\s+" + re.escape(cat) + r"\s*=\s*\[.*?\]", re.DOTALL)
        if not pattern.search(new_html):
            missing.append(cat)
            continue
        replacement = render_array(cat, store[cat])
        new_html = pattern.sub(lambda m: replacement, new_html, count=1)
        counts[cat] = len(store[cat])

    if missing:
        raise SystemExit(
            "Folgende Arrays wurden in index.html nicht gefunden: "
            + ", ".join(missing)
            + ". Erwartet wird je ein 'const <name> = [ ... ]' im <script>-Block."
        )

    summary = ", ".join(f"{cat}: {counts[cat]}" for cat in CATEGORIES)
    if args.check:
        print(f"OK - alle Bloecke gefunden. Wuerde schreiben: {summary}")
        return 0

    if new_html == html:
        print(f"Keine Aenderung noetig (Inhalt identisch). {summary}")
        return 0

    if not args.no_backup:
        with open(html_path + ".bak", "w", encoding="utf-8") as fh:
            fh.write(html)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(new_html)
    print(f"index.html aktualisiert ({summary}). Backup: "
          + ("- (deaktiviert)" if args.no_backup else html_path + ".bak"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
