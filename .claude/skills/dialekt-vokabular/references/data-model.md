# Datenmodell: Dialekt-Vokabeln

Diese Datei beschreibt, wie die Vokabeln in der Plattform "Dialekt verbindet"
strukturiert sind und wie `index.html` sie verwendet. Lies sie, bevor du Daten
importierst oder das Schema aenderst.

## Die drei Dialektregionen

Liechtenstein wird auf der Seite in drei Dialektgruppen aufgeteilt. Der
**kanonische Schluessel** (links) ist das, was Code und JSON verwenden; das
**Label** (rechts) ist die Anzeige fuer Nutzer:innen.

| Kanonischer Schluessel | Label auf der Seite      | Beschreibung                                  |
| ---------------------- | ------------------------ | --------------------------------------------- |
| `unterland`            | Unterland                | Ruggell, Schellenberg, Gamprin, Eschen, Mauren |
| `oberland`             | Oberland                 | Vaduz, Schaan, Triesen, Balzers, Planken       |
| `walser`               | Triesenbergerisch        | Walser-Dialekt von Triesenberg                 |

Wichtig: In den Quelldaten taucht die Walser-Region unter vielen Namen auf
(Triesenberg, Triesenbergerisch, Trisabaergerisch, Walserdeutsch ...). Der
Importer normalisiert diese alle auf `walser`. Die vollstaendige Aliasliste
steht in `scripts/import_vocab.py` (`CATEGORY_ALIASES`) - erweitere sie dort,
wenn eine neue Schreibweise auftaucht.

## Ein Vokabel-Eintrag

Jeder Eintrag ist ein Paar aus Schriftsprache und Dialekt:

```json
{ "hoch": "Kartoffel", "dialekt": "Härdöpfel" }
```

- `hoch`    - Hochdeutsch / Schriftsprache (das, was global eingegeben wird)
- `dialekt` - die lokale Dialektform

Der von den Nutzer:innen unsichtbare Zwischenschritt der Plattform ist genau
dieses Mapping `hoch <-> dialekt`: Eingabe in Schriftsprache -> Dialekt (aus
diesen Daten) -> zurueck in Schriftsprache. Deshalb muessen beide Felder immer
gefuellt sein; Eintraege mit leerem `hoch` oder `dialekt` werden verworfen.

## Kanonisches JSON (die Zwischendatei)

`import_vocab.py` erzeugt und `update_site.py` liest dieses Format. Es ist die
einzige "Quelle der Wahrheit" zwischen Rohdaten und Website:

```json
{
  "unterland": [ { "hoch": "...", "dialekt": "..." } ],
  "oberland":  [ { "hoch": "...", "dialekt": "..." } ],
  "walser":    [ { "hoch": "...", "dialekt": "..." } ]
}
```

Eintraege sind pro Region alphabetisch nach `hoch` sortiert, damit Git-Diffs
klein und lesbar bleiben. Das JSON-Schema liegt in
`assets/vokabeln.schema.json`.

## Wie index.html die Daten nutzt

Im `<script>`-Block ganz unten stehen drei Inline-Arrays:

```javascript
const unterland = [
{hoch:"Hallo",dialekt:"Hoi"},
...
]
const oberland = [ ... ]
const walser   = [ ... ]
```

`renderWords(list, elementId)` baut daraus die Karten mit einem "Audio"-Knopf,
der `speak(dialekt)` aufruft. `speak()` nutzt die Browser-Sprachausgabe
(`SpeechSynthesisUtterance`) mit `lang="de-CH"` - es ist keine externe
TTS-Bibliothek noetig, die drei Arrays sind die einzige Datenquelle.

`update_site.py` ersetzt **nur** diese drei `const ... = [ ... ]`-Bloecke und
laesst Layout, Styles und Funktionen unangetastet. Es sucht die Bloecke per
Muster `const <name> = [ ... ]` und ist damit unabhaengig davon, dass die Datei
aktuell keine schliessenden `</script>`/`</body>`/`</html>`-Tags hat (Browser
ergaenzen diese automatisch; das Skript braucht sie nicht).
