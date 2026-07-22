"""Schreibe einen VocabStore in die JS-Arrays von index.html.

Ersetzt die drei Bloecke `const unterland = [...]`, `const oberland = [...]`
und `const walser = [...]` und laesst den Rest der Datei unveraendert. Robust
gegen die fehlenden schliessenden Tags der aktuellen index.html (das Muster
matcht direkt die Array-Literale).
"""

import json
import os
import re

from .model import CATEGORIES


def default_index_path():
    """index.html im Projekt-Root, relativ zu diesem Modul geraten.

    core/ -> app/ -> Projekt-Root
    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "index.html")
    )


def render_array(name, entries):
    if not entries:
        return f"const {name} = []"
    body = ",\n".join(
        "{{hoch:{h},dialekt:{d}}}".format(
            h=json.dumps(e["hoch"], ensure_ascii=False),
            d=json.dumps(e["dialekt"], ensure_ascii=False),
        )
        for e in entries
    )
    return f"const {name} = [\n{body}\n]"


def check(html):
    """Liefere die Liste der Regionen, deren Array in html NICHT gefunden wird."""
    missing = []
    for cat in CATEGORIES:
        pattern = re.compile(r"const\s+" + re.escape(cat) + r"\s*=\s*\[.*?\]", re.DOTALL)
        if not pattern.search(html):
            missing.append(cat)
    return missing


def update_index_html(store, html_path=None, backup=True):
    """Schreibe die Vokabeln in index.html.

    Rueckgabe: dict mit {changed, counts, backup_path, missing}.
    Wirft FileNotFoundError, wenn die Datei fehlt, und ValueError, wenn ein
    Array-Block nicht gefunden wird.
    """
    html_path = os.path.abspath(html_path or default_index_path())
    if not os.path.exists(html_path):
        raise FileNotFoundError(html_path)

    with open(html_path, encoding="utf-8") as fh:
        html = fh.read()

    missing = check(html)
    if missing:
        raise ValueError(
            "Arrays nicht gefunden: " + ", ".join(missing)
            + " (erwartet je ein 'const <name> = [ ... ]')."
        )

    store.sort()
    new_html = html
    counts = {}
    for cat in CATEGORIES:
        pattern = re.compile(r"const\s+" + re.escape(cat) + r"\s*=\s*\[.*?\]", re.DOTALL)
        replacement = render_array(cat, store.data[cat])
        new_html = pattern.sub(lambda m: replacement, new_html, count=1)
        counts[cat] = len(store.data[cat])

    changed = new_html != html
    backup_path = None
    if changed:
        if backup:
            backup_path = html_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as fh:
                fh.write(html)
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(new_html)

    return {"changed": changed, "counts": counts, "backup_path": backup_path,
            "missing": [], "html_path": html_path}
