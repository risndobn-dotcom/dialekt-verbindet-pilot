"""Datenmodell fuer die Dialekt-Vokabeln.

Reine Python-Standardbibliothek, keine GUI - damit dieser Kern getestet und in
mehreren Kontexten (App, Skript) genutzt werden kann. Das kanonische Format
entspricht dem der Skill `dialekt-vokabular`:

    { "unterland": [{"hoch": "...", "dialekt": "..."}], "oberland": [...], "walser": [...] }
"""

import json
import re

CATEGORIES = ("unterland", "oberland", "walser")

# Anzeige-Labels wie auf der Website.
REGION_LABELS = {
    "unterland": "Unterland",
    "oberland": "Oberland",
    "walser": "Triesenbergerisch",
}

# Schreibweisen aus Quelldaten -> kanonischer Schluessel.
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


def normalize_text(value):
    """Rand-Whitespace trimmen, interne Whitespace-Folgen zusammenziehen.
    Gibt None zurueck, wenn nichts uebrig bleibt."""
    if value is None:
        return None
    text = str(value).replace(" ", " ")  # geschuetztes Leerzeichen
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def canonical_category(name):
    """Beliebige Regionsbezeichnung -> kanonischer Schluessel oder None."""
    if name is None:
        return None
    key = re.sub(r"\s+", "", str(name).strip().lower())
    return CATEGORY_ALIASES.get(key)


class VocabStore:
    """Haelt die drei Vokabellisten und bietet Lade-/Speicher-/Editier-Methoden."""

    def __init__(self, data=None):
        self.data = {cat: [] for cat in CATEGORIES}
        if data:
            for cat in CATEGORIES:
                for entry in data.get(cat, []):
                    h = normalize_text(entry.get("hoch"))
                    d = normalize_text(entry.get("dialekt"))
                    if h and d:
                        self.data[cat].append({"hoch": h, "dialekt": d})

    # -- Laden / Speichern -------------------------------------------------
    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def to_json(self):
        self.sort()
        return json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    # -- Editieren ---------------------------------------------------------
    def _key_set(self, category):
        return {(e["hoch"].lower(), e["dialekt"].lower()) for e in self.data[category]}

    def add(self, category, hoch, dialekt):
        """Fuege ein Paar hinzu. Rueckgabe: True wenn neu, False wenn ungueltig
        oder Duplikat (case-insensitiv innerhalb der Region)."""
        if category not in CATEGORIES:
            raise ValueError(f"Unbekannte Region: {category}")
        h = normalize_text(hoch)
        d = normalize_text(dialekt)
        if not h or not d:
            return False
        if (h.lower(), d.lower()) in self._key_set(category):
            return False
        self.data[category].append({"hoch": h, "dialekt": d})
        return True

    def update(self, category, index, hoch, dialekt):
        h = normalize_text(hoch)
        d = normalize_text(dialekt)
        if not h or not d:
            return False
        self.data[category][index] = {"hoch": h, "dialekt": d}
        return True

    def remove(self, category, index):
        del self.data[category][index]

    def sort(self):
        for cat in CATEGORIES:
            self.data[cat].sort(key=lambda e: e["hoch"].lower())

    def counts(self):
        return {cat: len(self.data[cat]) for cat in CATEGORIES}

    def total(self):
        return sum(len(self.data[cat]) for cat in CATEGORIES)

    def merge(self, other):
        """Fuege alle Eintraege eines anderen Stores hinzu (dedupliziert).
        Rueckgabe: Anzahl neu hinzugefuegter Eintraege."""
        added = 0
        for cat in CATEGORIES:
            for e in other.data[cat]:
                if self.add(cat, e["hoch"], e["dialekt"]):
                    added += 1
        return added
