# Mitmachen / Contributing

*Deutsch oben, English below.*

---

## Deutsch

Willkommen sind **Korrekturen** an Texten, Regeln und Quellen sowie **Fehlerberichte** zu Zahlen. Jede Zahl
auf der Website ist nachgerechnet. Wenn dir eine Zahl falsch vorkommt, nenne Seite, Farben und deine Rechnung.

### Ton

- Du-Form, nie „Sie“. Lange Imperative: „Wähle“, „Kopiere“, „Prüfe“, „Setze“, nicht „Wähl“, „Kopier“.
- Kurze Sätze, Richtwert 10 bis 15 Wörter. Ein Gedanke pro Satz, Doppelpunkt statt Nebensatzkette.
- Keine Ausrufezeichen, kein Hype („einfach“, „perfekt“, „mühelos“), nie „sicher für Farbenblinde“.
- Keine Geviertstriche (—) im Fließtext. Der Halbgeviertstrich (–) steht nur als Titeltrenner und für Bereiche.
- Englisch amerikanisch: color, gray, center, catalog, license. Überschriften in Sentence case.
- Deutsch mit Dezimalkomma, Englisch mit Punkt. In Code (CSS, JSON, JS) immer Punkt. Vor % steht im Deutschen ein
  schmales geschütztes Leerzeichen (U+202F, „8 %“), im Englischen keins („8%“).
- Anführungszeichen folgen der Sprache des Satzes: im Deutschen „…“, im Englischen “…”.
- `tools/checks.py` prüft das; der Build bricht bei Verstößen ab oder warnt.

### Zahlen

- **Keine Kontrast-, Abstands- oder Deckkraftzahl von Hand**, weder in `web/copy/` noch in `data/`.
  Schreibe Platzhalter: `{cr:#777777/#FFFFFF}`, `{cr:text/bg@light}`, `{dist:#009E73/#CC79A7/deutan}`,
  `{scrim:#FFFFFF/#000000/4.5}`, `{ref:okabe-ito-7}`, `{hex:accent@light}`, `{count:pairs}`, `{date}`.
  Der Build rechnet sie aus und schreibt sie als `<data>`-Element in die Seite; `tests/test_honesty.py`
  rechnet jedes davon nach.
- Erlaubt sind nur Schwellen: 3:1, 4,5:1 (4.5:1), 7:1, 21:1.
- Kontrastverhältnisse aus Quellen (x:1) stehen nur in `sources[].claim_de/en`; die Quellenseite zeigt sie als
  Quellzahl. Andere Zahlen aus Quellen, etwa Anteile in Prozent, dürfen auch im Text von Regeln und Erklärt-Einträgen
  stehen, wenn der Satz die Quelle nennt und sie unter `sources` des Eintrags steht.
- Gerundet wird immer zur ungünstigen Seite: Kontrast und Abstand abgeschnitten, nötige Deckkraft aufgerundet.
  Nie `round(`, `toFixed(` oder `Math.round(` (Grep-Test).
- Daten enthalten Eingaben, Schwellen, Texte und Quellen, nie Messergebnisse. Schlüssel wie `ratio`,
  `contrast`, `distance` oder `pass` sind in `data/` verboten.

### Belege

- Jede Regel und jeder Erklärt-Eintrag hat eine Belegstufe: `norm` (braucht `normative`), `research`
  (braucht `strength`: `strong` oder `partial`), `convention` oder `unproven` (mit `myth: true`, wenn widerlegt).
  Eigene Festlegungen von Farbsprache tragen `own: true` und die Stufe `convention`. Mischt eine Aussage einen Beleg
  mit einer eigenen Festlegung, teile sie in zwei Regeln.
- W3C-Techniken, Failures und Understanding-Texte sind informativ (`informative`, Quelle mit `normative: false`).
  Sie begründen allein nie eine Norm.
- Jede Quelle braucht `https`-URL, Abrufdatum (`retrieved`, JJJJ-MM-TT), `kind`, `access` (`fulltext`,
  `abstract`, `snippet`) und die belegte Aussage in beiden Sprachen. Was du nicht geprüft hast, steht in
  `unverified_de/en`.
- Zitate in einer anderen Sprache als der Satz stehen in `[en]…[/en]` bzw. `[de]…[/de]`, etwa
  `„[en]natural color balance[/en]“`. Die Seite zeichnet sie mit `lang` aus. `title_lang` nennt die Sprache des
  Quellentitels: `en`, `de` oder `en/de` für zweisprachige Titel der Form „English / Deutsch“. Bleibt die Kurzangabe
  unübersetzt (`short_de` gleich `short_en`, etwa „Understanding 1.4.3“), nennt `short_lang` ihre Sprache.
- Keine Werte aus Pantone, RAL, HKS oder NCS, keine Markenfarben als Themes, keine lebenden Künstlerinnen,
  Künstler oder Studios als Stilangabe (`tools/blocklist.txt`).

### Lokal bauen und testen

Benötigt Python 3.12+ und Node 22. Nichts zu installieren.

```sh
python3 build.py --fixtures                      # Website nach docs/, Testaufgabe nach tests/out/
python3 -m http.server 8000 --directory docs     # http://localhost:8000/de/
python3 tools/parity.py                          # Python-Seite des Paritätstests
FARBSPRACHE_REQUIRE_BUILD=1 python3 -m unittest discover -s tests -v
FARBSPRACHE_REQUIRE_BUILD=1 node --test tests/*.test.cjs
FARBSPRACHE_REQUIRE_BUILD=1 FARBSPRACHE_JS_DIR=docs/assets node --test tests/*.test.cjs   # dieselben Tests gegen die ausgelieferten Skripte
```

`README.md` und `README.de.md` erzeugt der Build aus `web/readme.en.md` und `web/readme.de.md`; ändere nur die Vorlagen.
Ändern sich Aufgaben, Startpaletten oder Quellen, rendere `og.png` mit `python3 tools/og.py` neu (braucht Google Chrome;
den Pfad setzt `CHROME` in `tools/og.py`).

Der Build bricht ab, solange eine Aufgabe aus `data/tasks/_order.json` fehlt; so läuft die CI. Arbeitest du an einer
neuen Aufgabe, die noch nicht vollständig ist, baue mit `--allow-missing`: Fehlende Aufgaben werden dann Platzhalter.
Mit `--date JJJJ-MM-TT` (oder `SOURCE_DATE_EPOCH`) ist das Datum in Exporten fest.

Die Schriften unter `web/fonts/` liefert die Seite selbst aus (SIL OFL 1.1, Texte in `data/licenses/`); keine Seite lädt
etwas von fremden Servern, `tests/test_site.py` prüft das. Inter stammt aus dem Release 4.1 (github.com/rsms/inter) und ist
mit fonttools beschnitten: `pyftsubset Inter-Regular.woff2 --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+0394,U+03B1,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+2248,U+2260,U+2264-2265,U+25A0,U+25B2,U+25CF,U+2713,U+FEFF,U+FFFD" --layout-features+=tnum --name-IDs='*' --name-legacy
--name-languages='*' --flavor=woff2`, ebenso Medium und Bold. IBM Plex Mono kommt unverändert aus dem Release
@ibm/plex-mono 2.5.0 (Teilmengen Latin1 und Pi von IBM), weil die OFL geänderte Fassungen mit dem reservierten Namen
„Plex“ ausschließt. Kommen neue Zeichen in den Text, bilde die Teilmenge neu und prüfe `unicode-range` in `web/site.css`.

### Kurzanleitung für eine neue Aufgabe

Eine Aufgabe besteht aus diesen Dateien. Dazu kommen ihre ID in `data/tasks/_order.json`, die IDs ihrer Erklärt-Einträge
in `data/explain/_order.json` und zwei Stellen in `build.py`: eine Zeile in `SEG` (URL-Segment je Sprache, etwa
`"fixture": {"de": "testaufgabe", "en": "test-task"}`) und `N_PAGES_PER_LANG` um eins höher. `web/site.js`,
`web/site.css` und `tools/checks.py` bleiben unverändert; braucht eine Aufgabe dort etwas Neues, öffne dafür ein Issue.
Die Testaufgabe in `tests/fixtures/` ist ein vollständiges Beispiel für jede Datei.

| Datei | Inhalt |
| --- | --- |
| `data/tasks/<id>.json` | Aufgabe: Rollen, Paare, Steuerelemente, drei Startpaletten (Diagramm: vier), Exporte |
| `tools/gen/<modul>.py` | `build(task, inp, ctx) -> Palettenobjekt` (`modes`, `roles`, `pairs`, `decorative`, `distinct`, `changes`, `findings`, `usage`, `extra`), optional `view_vars`, `exports`, `display_name` |
| `web/gen/<id>.js` | derselbe Generator in ES5, registriert als `FS.gen[<id>]` |
| `web/ui/<id>.js` | optional: eigene Bedienteile, `FS.ui[<id>] = {init(api), render(palette, state, api)}` |
| `patterns/<id>.html` | Referenzmuster: `<style>` mit Selektoren `.demo-<id> …` und Markup, Farben nur `var(--d-<rolle>)`, keine Links, Knöpfe, Formularfelder oder `tabindex` (die Testaufgabe enthält Link und Knopf absichtlich; der Link dient einem Prüftest) |
| `patterns/<id>-mini.svg` | Vorschau der Startseite, Farben nur `style="fill:var(--d-<rolle>)"` |
| `web/copy/<modul>.py` | `COPY = {"de": {"<id>": {...}}, "en": {"<id>": {...}}}` mit h1, lede, outcome und allen Texten |
| `web/css/<id>.css` | optional, nur Selektoren mit `.t-<id>` |
| `data/rules/<owner>.json`, `data/explain/<owner>.json`, `data/sources/<owner>.json` | Regeln, Kurz erklärt, Quellen |
| `tools/checks_<owner>.py` | optional: `check(D, warn) -> [Meldungen]` |
| `tests/golden/<id>.json` | Hex-Werte aller Startpaletten, geschrieben von `python3 build.py --update-golden` |

Optionale Felder, die der Rahmen ohne eigene Änderung versteht:

- In `data/tasks/<id>.json`: `seed_param` (URL-Name der eigenen Farbe, etwa `sc`), `preset_control` (ein
  Steuerelement wählt die Startpalette, ohne Preset-Chips), `seed_control` (Chips mit Vorschlägen aus der eigenen
  Farbe, stehen statt der Startpaletten, solange eine Farbe gesetzt ist), `gen_deps` (weitere `web/gen/*.js`),
  `datasets` (Datensätze für den Browser), `data_files` (`models`, `colornames`, `check` als `ctx.data`),
  Steuerelemente mit `by`/`cases` und `view: true`, Rollen mit `css_name` und `export_option`, Paare mit `group`.
- Im Palettenobjekt unter `extra`: `datasets` (Pflichtnennungen), `summary` (Textschlüssel für ein Kurzergebnis
  unter dem Farbstreifen), `pair_note` (Textschlüssel für eine Zusatzzeile je geprüftem Paar, Pseudo-Rollen
  `pair-fg` und `pair-bg`). Neben `pairs` und `decorative` optional `advisory` (Hinweispaare aus `evaluate`, mit Wert
  in Block C, F und im Prompt).
- Generator-Haken `display_name(palette, text, lang)` (JS `displayName`): Name eigener Zustände ohne eigene Farbe aus
  dem, was die Palette zeigt; die Texte `name.*` beider Sprachen kommen über `#task-data` (`name_text`).
- Eigene Exportformate liefern einen String oder Blöcke `{label, text, suffix, lang, note, ext}`; `note` ist eine
  Vorlage aus COPY und steht außerhalb des Kopiertexts, `ext` eine eigene Dateiendung des Blocks (etwa `json`). `header()` und `notices()` aus `tools/export.py`
  (`FS.export.header`, `FS.export.notices`) liefern Kopfzeile und Pflichtnennungen.

Ablauf: Daten und Texte anlegen, Generator in Python schreiben, mit `python3 build.py --allow-missing` bauen,
JS-Generator nachziehen, `python3 tools/parity.py` und `node --test tests/parity.test.cjs` laufen lassen.
Golden-Dateien schreibst du bewusst mit `python3 build.py --allow-missing --update-golden` und begründest jede
Änderung im Pull Request. Jeder berechnete Hinweis einer Startpalette muss in `expect` stehen, und keine
Startpalette darf ein normatives Paar verfehlen; sonst bricht der Build ab.

Commit-Nachrichten wie in Bildsprache: deutsch, „Bereich: Ergebnis“, ohne Präfix und ohne Schlusspunkt.

---

## English

**Corrections** to texts, rules and sources and **bug reports** about numbers are welcome. Every number on the
website is calculated. If a number looks wrong to you, name the page, the colors and your calculation.

### Tone

- German pages use the informal “du”. English uses plain second person.
- Short sentences, about 10 to 15 words. One idea per sentence, a colon instead of chained clauses.
- No exclamation marks, no hype (“easy”, “perfect”, “seamless”, “powerful”), never “colorblind safe”.
- No em dashes in running text. The en dash only separates titles and ranges.
- American English: color, gray, center, catalog, license. Headings in sentence case.
- German uses a decimal comma, English a point. Code (CSS, JSON, JS) always uses a point. German puts a narrow
  no-break space (U+202F, “8 %”) before %, English none (“8%”).
- Quotation marks follow the language of the sentence: „…“ in German, “…” in English.
- `tools/checks.py` enforces this; the build stops or warns.

### Numbers

- **No contrast, distance or opacity figure by hand**, neither in `web/copy/` nor in `data/`. Write
  placeholders: `{cr:#777777/#FFFFFF}`, `{cr:text/bg@light}`, `{dist:#009E73/#CC79A7/deutan}`,
  `{scrim:#FFFFFF/#000000/4.5}`, `{ref:okabe-ito-7}`, `{hex:accent@light}`, `{count:pairs}`, `{date}`.
  The build calculates them and writes them into the page as `<data>` elements; `tests/test_honesty.py`
  recalculates every one of them.
- Only thresholds are allowed as written figures: 3:1, 4.5:1, 7:1, 21:1.
- Contrast ratios from sources (x:1) go only into `sources[].claim_de/en`; the sources page shows them as source
  figures. Other figures from sources, such as percentages, may also appear in the text of rules and explained
  entries if the sentence names the source and it is listed under `sources` of the entry.
- Rounding always goes to the unfavorable side: contrast and distance are truncated, required opacity is
  rounded up. Never `round(`, `toFixed(` or `Math.round(` (grep test).
- Data holds inputs, thresholds, texts and sources, never measurements. Keys such as `ratio`, `contrast`,
  `distance` or `pass` are not allowed in `data/`.

### Evidence

- Every rule and explained entry has an evidence level: `norm` (needs `normative`), `research` (needs
  `strength`: `strong` or `partial`), `convention` or `unproven` (with `myth: true` if disproved). Farbsprache's
  own settings carry `own: true` and the level `convention`. If a statement mixes evidence with an own setting,
  split it into two rules.
- W3C techniques, failures and understanding documents are informative (`informative`, source with
  `normative: false`). They never support a standard on their own.
- Every source needs an `https` URL, a retrieval date (`retrieved`, YYYY-MM-DD), `kind`, `access` (`fulltext`,
  `abstract`, `snippet`) and the backed claim in both languages. What you did not check goes into
  `unverified_de/en`.
- Quotes in a language other than the sentence go into `[en]…[/en]` or `[de]…[/de]`, such as
  `“[de]Dunkel 1[/de]”`. The site marks them with `lang`. `title_lang` gives the language of the source title:
  `en`, `de` or `en/de` for bilingual titles of the form “English / Deutsch”. If the short label stays untranslated
  (`short_de` equals `short_en`, such as “Understanding 1.4.3”), `short_lang` gives its language.
- No values from Pantone, RAL, HKS or NCS, no brand colors as themes, no living artists or studios as style
  references (`tools/blocklist.txt`).

### Build and test locally

Requires Python 3.12+ and Node 22. Nothing to install.

```sh
python3 build.py --fixtures                      # site into docs/, test task into tests/out/
python3 -m http.server 8000 --directory docs     # http://localhost:8000/en/
python3 tools/parity.py                          # Python side of the parity test
FARBSPRACHE_REQUIRE_BUILD=1 python3 -m unittest discover -s tests -v
FARBSPRACHE_REQUIRE_BUILD=1 node --test tests/*.test.cjs
FARBSPRACHE_REQUIRE_BUILD=1 FARBSPRACHE_JS_DIR=docs/assets node --test tests/*.test.cjs   # the same tests against the shipped scripts
```

The build writes `README.md` and `README.de.md` from `web/readme.en.md` and `web/readme.de.md`; edit the templates
only. If tasks, starter palettes or sources change, render `og.png` again with `python3 tools/og.py` (needs Google
Chrome; `CHROME` in `tools/og.py` sets the path).

The build stops while a task from `data/tasks/_order.json` is missing; this is how CI runs. While you work on a
new task that is not complete yet, build with `--allow-missing`: missing tasks then become placeholders.
With `--date YYYY-MM-DD` (or `SOURCE_DATE_EPOCH`) the date in exports is fixed.

The site ships the fonts under `web/fonts/` itself (SIL OFL 1.1, texts in `data/licenses/`); no page loads anything from
other servers, and `tests/test_site.py` checks this. Inter comes from release 4.1 (github.com/rsms/inter) and is subset
with fonttools: `pyftsubset Inter-Regular.woff2 --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+0394,U+03B1,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+2248,U+2260,U+2264-2265,U+25A0,U+25B2,U+25CF,U+2713,U+FEFF,U+FFFD" --layout-features+=tnum --name-IDs='*' --name-legacy
--name-languages='*' --flavor=woff2`, and the same for Medium and Bold. IBM Plex Mono comes unchanged from release
@ibm/plex-mono 2.5.0 (IBM's Latin1 and Pi subsets), because the OFL rules out modified versions with the reserved name
“Plex”. If the text gains new characters, rebuild the subset and check `unicode-range` in `web/site.css`.

### Quick guide for a new task

A task consists of these files, plus its ID in `data/tasks/_order.json`, the IDs of its explained entries in
`data/explain/_order.json` and two places in `build.py`: one line in `SEG` (URL segment per language, such as
`"fixture": {"de": "testaufgabe", "en": "test-task"}`) and `N_PAGES_PER_LANG` one higher. `web/site.js`,
`web/site.css` and `tools/checks.py` stay unchanged; if a task needs something new there, open an issue. The test task
in `tests/fixtures/` is a complete example of every file.

| File | Content |
| --- | --- |
| `data/tasks/<id>.json` | Task: roles, pairs, controls, three starter palettes (charts: four), exports |
| `tools/gen/<module>.py` | `build(task, inp, ctx) -> palette object` (`modes`, `roles`, `pairs`, `decorative`, `distinct`, `changes`, `findings`, `usage`, `extra`), optional `view_vars`, `exports`, `display_name` |
| `web/gen/<id>.js` | the same generator in ES5, registered as `FS.gen[<id>]` |
| `web/ui/<id>.js` | optional: own controls, `FS.ui[<id>] = {init(api), render(palette, state, api)}` |
| `patterns/<id>.html` | reference pattern: `<style>` with `.demo-<id> …` selectors and markup, colors only `var(--d-<role>)`, no links, buttons, form fields or `tabindex` (the test task has a link and a button on purpose; the link serves a check test) |
| `patterns/<id>-mini.svg` | start page preview, colors only `style="fill:var(--d-<role>)"` |
| `web/copy/<module>.py` | `COPY = {"de": {"<id>": {...}}, "en": {"<id>": {...}}}` with h1, lede, outcome and all texts |
| `web/css/<id>.css` | optional, only selectors with `.t-<id>` |
| `data/rules/<owner>.json`, `data/explain/<owner>.json`, `data/sources/<owner>.json` | rules, explained entries, sources |
| `tools/checks_<owner>.py` | optional: `check(D, warn) -> [messages]` |
| `tests/golden/<id>.json` | hex values of all starter palettes, written by `python3 build.py --update-golden` |

Optional fields the frame understands without any change of its own:

- In `data/tasks/<id>.json`: `seed_param` (URL name of your own color, such as `sc`), `preset_control` (a control
  picks the starter palette, no preset chips), `seed_control` (chips with suggestions from your own color, shown
  instead of the starter palettes while a color is set), `gen_deps` (further `web/gen/*.js`), `datasets` (data sets
  for the browser), `data_files` (`models`, `colornames`, `check` as `ctx.data`), controls with `by`/`cases` and
  `view: true`, roles with `css_name` and `export_option`, pairs with `group`.
- In the palette object under `extra`: `datasets` (required credits), `summary` (text keys for a short result
  below the color strip), `pair_note` (text key for an extra line per checked pair, pseudo roles `pair-fg` and
  `pair-bg`). Next to `pairs` and `decorative`, optionally `advisory` (advisory pairs from `evaluate`, shown with
  their value in blocks C and F and in the prompt).
- Generator hook `display_name(palette, text, lang)` (JS `displayName`): the name of a custom state without your own
  color, built from what the palette shows; the `name.*` texts of both languages come through `#task-data` (`name_text`).
- Own export formats return a string or blocks `{label, text, suffix, lang, note, ext}`; `note` is a template from COPY
  and stays outside the copied text, `ext` is the block's own file extension (such as `json`). `header()` and `notices()` in `tools/export.py` (`FS.export.header`,
  `FS.export.notices`) give the header line and the required credits.

Workflow: add data and texts, write the generator in Python, build with `python3 build.py --allow-missing`,
port the generator to JS, run `python3 tools/parity.py` and `node --test tests/parity.test.cjs`. Write golden
files deliberately with `python3 build.py --allow-missing --update-golden` and explain every change in the pull
request. Every calculated note of a starter palette must be listed in `expect`, and no starter palette may fail
a normative pair; otherwise the build stops.

Commit messages as in Bildsprache: German, “Bereich: Ergebnis”, no prefix, no final period.
