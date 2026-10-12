#!/usr/bin/env python3
"""Baut die Website Farbsprache nach docs/.

    python3 build.py                     vollständiger Build; fehlt eine Aufgabe, bricht er ab
    python3 build.py --allow-missing     lokal während der Paketarbeit: Platzhalter statt Abbruch
    python3 build.py --fixtures          zusätzlich die Testaufgabe nach tests/out/fixtures/docs/
    python3 build.py --date 2026-10-11   festes Datum (sonst SOURCE_DATE_EPOCH, sonst heute)
    python3 build.py --update-golden     tests/golden/<aufgabe>.json neu schreiben (nur bewusst)

README.md und README.de.md schreibt nur der strenge Build (ohne --allow-missing und ohne --update-golden).

Quellen:
  data/tasks/_order.json, data/tasks/<id>.json   Aufgaben (Reihenfolge, Definition, Startpaletten)
  tools/gen/<modul>.py, web/gen/<id>.js           Generatoren je Aufgabe (Python für den Build, JS im Browser)
  patterns/<id>.html, patterns/<id>-mini.svg      Referenzmuster und Mini-Vorschau
  web/copy/<modul>.py                             Texte, COPY[lang][seite][schlüssel]
  data/rules|explain|sources/*.json               Regeln, Kurz erklärt, Quellen
  data/datasets/*.json, data/comparisons.json     Datensätze und Vergleichswerte
  pages/home.py, pages/task.py, pages/<seite>.py  Seiten (Start, Aufgabenrahmen, Prüfen, Erklärt, Methode, Quellen)

Der Build prüft vorher alle Daten (tools/checks.py) und den Farbkern gegen data/testvectors.json, rechnet
alle Startpaletten mit den Python-Generatoren und baut nach docs.tmp/, bevor er docs/ tauscht.
Seiten entstehen datengetrieben aus data/tasks/_order.json; eine neue Aufgabe braucht hier nur eine SEG-Zeile und
N_PAGES_PER_LANG + 1.

Build the bilingual Farbsprache site. See README.md.
"""
import argparse, datetime, hashlib, html, importlib, io, json, os, pathlib, re, shutil, sys, traceback, unittest

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if __name__ == "__main__":
    sys.modules.setdefault("build", sys.modules["__main__"])

from tools import checks  # noqa: E402  (lädt den Farbkern erst bei Bedarf)
from web import theme  # noqa: E402

DOCS = ROOT / "docs"
FIXTURES = ROOT / "tests" / "fixtures"
FIXTURE_OUT = ROOT / "tests" / "out" / "fixtures" / "docs"
SITE_URL = "https://grundhofer.github.io/farbsprache"
REPO_URL = "https://github.com/grundhofer/farbsprache"
SIBLINGS = [("Bildsprache", "https://grundhofer.github.io/bildsprache/"),
            ("Designsprache", "https://grundhofer.github.io/designsprache/")]
LANGS = ("de", "en")
SEG = {
    "website": {"de": "website", "en": "website"},
    "status": {"de": "status", "en": "status"},
    "charts": {"de": "diagramm", "en": "charts"},
    "slides": {"de": "folien", "en": "slides"},
    "brand": {"de": "marke", "en": "brand"},
    "image-text": {"de": "text-auf-bild", "en": "text-on-image"},
    "ai-image": {"de": "ki-bild", "en": "ai-image"},
    "check": {"de": "pruefen", "en": "check"},
    "explained": {"de": "erklaert", "en": "explained"},
    "method": {"de": "methode", "en": "method"},
    "sources": {"de": "quellen", "en": "sources"},
}
# Nur für die Testaufgabe (wird nie ausgeliefert); verschiedene Segmente prüfen PAGE_TWIN.
FIXTURE_SEG = {"fixture": {"de": "testaufgabe", "en": "test-task"}}
PAGES = ("check", "explained", "method", "sources")   # Seiten von P5 (pages/<name>.py)
N_PAGES_PER_LANG = 12
# Schriften liefert die Seite selbst aus (web/fonts/ nach assets/fonts/, SIL OFL 1.1), keine Anfrage an fremde Server
# (nach Z geändert, 7.2). site.css bindet sie per @font-face ein; vorgeladen werden die drei Schnitte von Inter, die jede
# Seite im ersten Bildschirm braucht. Die Lizenztexte liegen in data/licenses/ und gehen mit nach assets/fonts/.
PRELOAD_FONTS = ("inter-400.woff2", "inter-500.woff2", "inter-700.woff2")
FONT_LICENSES = ("OFL-1.1-Inter.txt", "OFL-1.1-IBM-Plex.txt")
# Pflichtvermerke für das Material aus CSS Color 4 (W3C Software and Document License) und WCAG 2.2 (W3C Document
# License, Leuchtdichte und Kontrast); beide stehen in der ersten Zeile der ausgelieferten color.js und wörtlich auf der
# Quellenseite (web/copy/sources.py lic.w3c.text und lic.wcag.sw).
W3C_NOTICE = ("This software includes material copied from or derived from CSS Color Module Level 4 "
              "(https://www.w3.org/TR/2026/CRD-css-color-4-20261009/). Copyright © 2026 World Wide Web Consortium. "
              "https://www.w3.org/copyright/software-license-2023/")
WCAG_NOTICE = ("Copyright © 2023 W3C®. This software or document includes material copied from or derived from "
               "Web Content Accessibility Guidelines (WCAG) 2.2 (https://www.w3.org/TR/2024/REC-WCAG22-20241212/).")
# Eigene Marke: rotes Quadrat mit drei gestaffelten weißen Quadraten (eine Stufenleiter)
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' fill='%23C8050F'/%3E%3Crect x='4' y='20' width='8' height='8' fill='%23FFFFFF'/%3E"
           "%3Crect x='12' y='12' width='8' height='8' fill='%23FFFFFF'/%3E%3Crect x='20' y='4' width='8' height='8' fill='%23FFFFFF'/%3E%3C/svg%3E")
LOGO = ('<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" fill="var(--accent)"/>'
        '<rect x="4" y="20" width="8" height="8" fill="var(--surface)"/><rect x="12" y="12" width="8" height="8" fill="var(--surface)"/>'
        '<rect x="20" y="4" width="8" height="8" fill="var(--surface)"/></svg>')
REMEMBER = ("<script>document.addEventListener('click',function(e){var a=e.target.closest('.tb-lang a');"
            "if(a){try{localStorage.setItem('farbsprache.language',a.hreflang)}catch(x){}}});</script>")


def asset_version(data):
    """Kurzer Inhalts-Hash der ausgelieferten Datei, damit Browser und Pages-Cache neu laden."""
    return hashlib.sha1(data).hexdigest()[:10]


def _word(c):
    return c.isalnum() or c in "_$" or ord(c) > 127


RE_BEFORE = set("(,=:[!&|?{};+-*%<>~^")
RE_WORDS = {"return", "typeof", "case", "do", "else", "in", "instanceof", "new", "void", "delete", "throw"}


def squeeze_js(line):
    """Leerraum innerhalb einer Codezeile entfernen, wo er nichts trennt (nach Z geändert, 7.2): Zeichenketten, Regex
    und Kommentare bleiben wörtlich. Ein Leerzeichen bleibt zwischen zwei Wortzeichen, zwischen ++ und --, neben /
    und dort, wo sonst <! oder -> entstünde. Bleibt etwas offen (Zeichenkette, Regex, Blockkommentar), bleibt die
    Zeile unverändert. Nur Leerraum fällt weg; tests/test_site.py prüft das für jede ausgelieferte Datei."""
    out, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch in "'\"":
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            if j >= n:
                return line
            out.append(line[i:j + 1])
            i = j + 1
        elif line.startswith("//", i):
            out.append(line[i:])
            break
        elif line.startswith("/*", i):
            j = line.find("*/", i + 2)
            if j < 0:
                return line
            out.append(line[i:j + 2])
            i = j + 2
        elif ch == "/":
            prev = "".join(out).rstrip()
            word = re.search(r"[A-Za-z_$]+$", prev)
            if not prev or prev[-1] in RE_BEFORE or (word and word.group(0) in RE_WORDS):
                j, cls = i + 1, False
                while j < n and (cls or line[j] != "/"):
                    if line[j] == "\\":
                        j += 1
                    elif line[j] in "[]":
                        cls = line[j] == "["
                    j += 1
                if j >= n:
                    return line
                j += 1
                while j < n and _word(line[j]):
                    j += 1
                out.append(line[i:j])
                i = j
            else:
                out.append(ch)
                i += 1
        elif ch in " \t":
            j = i
            while j < n and line[j] in " \t":
                j += 1
            a, b = (out[-1][-1] if out else ""), (line[j] if j < n else "")
            if a and b and ((_word(a) and _word(b)) or (a == b and a in "+-") or "/" in (a, b) or a + b in ("<!", "->")):
                out.append(" ")
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def compact_js(src):
    """Jedes ausgelieferte Skript (color.js, export.js, site.js, check.js, gen/*.js, ui/*.js) wegen des Budgets
    7.11: Einzug, reine Kommentarzeilen und Blockkommentare am Zeilenanfang entfallen, Leerraum innerhalb der Zeile
    nach squeeze_js (nach Z geändert). Jeder Zeilenumbruch im Code bleibt (ASI und Bedeutung unverändert). Eine Zeile
    nach einem Backslash am Zeilenende bleibt samt Einzug stehen. tests/export.test.cjs und state.test.cjs laden genau
    diese Dateien."""
    out, in_block, keep = [], False, False
    for line in src.splitlines():
        s, raw = (line if keep else line.strip()), keep or line.endswith("\\")
        keep = line.endswith("\\")
        if in_block:
            end = s.find("*/")
            if end < 0:
                continue
            in_block, s = False, s[end + 2:].strip()
            if not s:
                continue
        if not s or s.startswith("//"):
            continue
        if s.startswith("/*"):
            end = s.find("*/", 2)
            if end < 0:
                in_block = True
                continue
            s = s[end + 2:].strip()
            if not s:
                continue
        out.append(s if raw else squeeze_js(s))
    return "\n".join(out) + "\n"


def compact_css(src):
    """site.css wegen des Budgets 7.11 (nach Z geändert): Kommentare, Einzug und Leerzeilen entfallen, die Regeln stehen
    wörtlich. Die Quellen (web/site.css, web/css/*.css) behalten ihre Kommentare; Zeichenketten mit /* gibt es dort nicht."""
    return "\n".join(s for s in (line.strip() for line in re.sub(r"/\*.*?\*/", "", src, flags=re.S).splitlines()) if s) + "\n"


def jload(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def h(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def no_comments(o):
    """JSON ohne _comment-Schlüssel: Die Kommentare der Datendateien sind Arbeitsnotizen für das Repo und gehören nicht
    in die ausgelieferten Seiten (kein Skript liest sie)."""
    if isinstance(o, dict):
        return {k: no_comments(v) for k, v in o.items() if k != "_comment"}
    if isinstance(o, list):
        return [no_comments(v) for v in o]
    return o


def jscript(obj, id_):
    text = json.dumps(no_comments(obj), ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return f'<script type="application/json" id="{id_}">{text}</script>'


def num(n, lang):
    from tools import color
    return color.fmt_count(n, lang)


def other(lang):
    return "en" if lang == "de" else "de"


# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------
def path(lang, kind, seg=None):
    """Pfad relativ zu docs/, immer mit abschließendem und ohne führenden Schrägstrich."""
    if kind == "home":
        return f"{lang}/"
    return f"{lang}/{(seg or SEG)[kind][lang]}/"


def rel(src, dst):
    return "../" * src.count("/") + dst


def PAGE_TWIN(lang, page, seg=None):
    """Gegenstück einer Seite in der anderen Sprache; übersetzt nur Segment [1]."""
    o = other(lang)
    parts = page.split("/")
    parts[0] = o
    if len(parts) > 2 and parts[1]:
        for v in (seg or SEG).values():
            if parts[1] == v[lang]:
                parts[1] = v[o]
                break
    return "/".join(parts)


def write(out, page, text):
    f = out / page / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


class BuildError(Exception):
    def __init__(self, errors):
        super().__init__(f"{len(errors)} Fehler")
        self.errors = errors


def _where(e):
    tb = traceback.extract_tb(e.__traceback__)
    last = tb[-1] if tb else None
    return f"{type(e).__name__}: {e}" + (f" ({pathlib.Path(last.filename).name}:{last.lineno})" if last else "")


# ---------------------------------------------------------------------------
# Website
# ---------------------------------------------------------------------------
class Site:
    """Ein Build: Daten, Generatoren, Startpaletten, Seitenrahmen. Die Seitenmodule bekommen dieses Objekt."""
    SIBLINGS = SIBLINGS

    def __init__(self, roots, out, date, allow_missing=False, seg=None):
        self.roots = [pathlib.Path(r) for r in roots]
        self.out = pathlib.Path(out)
        self.date = date
        self.allow_missing = allow_missing
        self.seg = dict(SEG, **(seg or {}))
        self.warnings = []
        self.h, self.rel, self.jscript = h, rel, jscript
        self.ver = {}

    # ---- Pfade und Kleinkram
    def path(self, lang, kind):
        return path(lang, kind, self.seg)

    def twin(self, lang, page):
        return PAGE_TWIN(lang, page, self.seg)

    def abs_url(self, lang, kind):
        return f"{SITE_URL}/{self.path(lang, kind)}"

    def sibling_url(self, name):
        return dict((k.lower(), v) for k, v in SIBLINGS)[name]

    def warn(self, msg):
        self.warnings.append(msg)

    def task_datasets(self, task):
        ids = list(task.get("datasets") or [])
        for p in task["presets"]:
            if p.get("dataset") and p["dataset"] not in ids:
                ids.append(p["dataset"])
        return ids

    def has_ui(self, tid):
        return self.ui_root.get(tid) is not None

    def pattern(self, tid, lang):
        """Muster der Aufgabe: Stil (einmal in den Kopf), Markup und Mini-Vorschau mit Texten der Sprache."""
        raw = self.D["patterns"][tid]
        tc = self.copy[lang][tid]

        def text(s):
            return re.sub(r"\{\{([a-z0-9_.-]+)\}\}", lambda m: h(tc["pattern." + m.group(1)]), s or "")
        src = raw["html"] or ""
        styles = "".join(f"<style>{s}</style>" for s in re.findall(r"<style[^>]*>(.*?)</style>", src, re.S | re.I))
        markup = re.sub(r"<style[^>]*>.*?</style>", "", src, flags=re.S | re.I).strip()
        return {"style": styles, "html": text(markup), "mini": text((raw["mini"] or "").strip())}

    # ---- Vorbereitung: Daten, Prüfungen, Farbkern, Generatoren
    def prepare(self):
        D, errs = checks.load_all(self.roots)
        self.D = D
        errs += checks.run(D, self.seg, self.twin, self.allow_missing, self.date, self.warnings)
        if errs:
            raise BuildError(errs)
        errs = self.selftest()
        if errs:
            raise BuildError(errs)
        from tools import color, export  # noqa: F401  (erst nach der Prüfung der Konstanten)
        self.color = color
        self.copy = D["copy"]
        self.js_text = D["js_text"]
        self.order = D["order"]
        self.tasks = [D["tasks"][t] for t in self.order if t in D["tasks"]]
        self.task_by_id = {t["id"]: t for t in self.tasks}
        self.missing = [t for t in self.order if t not in D["tasks"]]
        self.rules, self.explain, self.sources = D["rules"], D["explain"], D["sources"]
        self.explain_order = D["explain_order"]
        self.datasets = D["datasets"]
        self.comparisons = (D["comparisons"] or {}).get("comparisons") or []
        self.refs = color.reference_values(D["comparisons"], self.datasets)
        self.rule_users = {r: [t["id"] for t in self.tasks if r in t["rules"]] for r in self.rules}
        self.explain_users = {e: [t["id"] for t in self.tasks if e in t["explain"]] for e in self.explain}
        errs = self.load_code()
        if errs:
            raise BuildError(errs)
        errs = self.run_presets()
        if errs:
            raise BuildError(errs)
        self.counts = {"tasks": len(self.tasks), "presets": sum(len(t["presets"]) for t in self.tasks),
                       "pairs": sum(len(p["pairs"]) for t in self.tasks for p in self.palettes[t["id"]].values()),
                       "rules": len(self.rules), "sources": len(self.sources)}

    def selftest(self):
        """Farbkern gegen data/testvectors.json (dieselben Fälle wie tests/test_color.py)."""
        try:
            mod = checks.load_module(ROOT / "tests" / "test_color.py", "fs_selftest_color")
        except Exception as e:  # noqa: BLE001
            return [f"Farbkern: tests/test_color.py lässt sich nicht laden ({_where(e)})"]
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(mod.TestVectors)
        res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        if res.wasSuccessful() and not res.skipped:
            return []
        return [f"Farbkern: Testvektor {t.id().rsplit('.', 1)[-1]} verfehlt ({str(err).strip().splitlines()[-1]})"
                for t, err in res.failures + res.errors] or ["Farbkern: Testvektoren übersprungen"]

    def _root_of(self, rel_path):
        hit = None
        for r in self.roots:
            if (r / rel_path).exists():
                hit = r
        return hit

    def load_code(self):
        errs = []
        self.gens, self.gen_js, self.ui_root, self.page_mods = {}, {}, {}, {}
        for t in self.tasks:
            mod = t["generator"].replace("-", "_")
            r = self._root_of(f"tools/gen/{mod}.py")
            if r is None:
                errs.append(f"Aufgabe {t['id']}: Generator tools/gen/{mod}.py fehlt")
                continue
            try:
                if r == ROOT:
                    gen = importlib.import_module(f"tools.gen.{mod}")
                else:
                    gen = checks.load_module(r / "tools" / "gen" / f"{mod}.py", f"fs_gen_{mod}_{abs(hash(str(r)))}")
            except Exception as e:  # noqa: BLE001
                errs.append(f"Aufgabe {t['id']}: tools/gen/{mod}.py lässt sich nicht laden ({_where(e)})")
                continue
            if not callable(getattr(gen, "build", None)):
                errs.append(f"Aufgabe {t['id']}: tools/gen/{mod}.py hat keine Funktion build(task, inp, ctx)")
            self.gens[t["id"]] = gen
            for g in list(t.get("gen_deps") or []) + [t["generator"]]:
                rj = self._root_of(f"web/gen/{g}.js")
                if rj is None:
                    errs.append(f"Aufgabe {t['id']}: web/gen/{g}.js fehlt")
                else:
                    self.gen_js[g] = rj / "web" / "gen" / f"{g}.js"
            self.ui_root[t["id"]] = self._root_of(f"web/ui/{t['id']}.js")
            ex = t["exports"]
            for f in list(ex["visible"]) + list(ex.get("more") or []):
                if f not in checks.GENERIC_FORMATS and f not in (getattr(gen, "exports", None) or {}):
                    errs.append(f"Aufgabe {t['id']}: Exportformat {f} hat keinen Renderer (generisch oder gen.exports)")
        for name in PAGES:
            f = ROOT / "pages" / f"{name}.py"
            if len(self.roots) > 1:
                continue  # Testaufgabe: nur Kern von P0 (checks._own), Seiten von P5 als Platzhalter
            if f.exists():
                try:
                    self.page_mods[name] = importlib.import_module(f"pages.{name}")
                except Exception as e:  # noqa: BLE001
                    errs.append(f"pages/{name}.py lässt sich nicht laden ({_where(e)})")
            elif self.allow_missing:
                self.warn(f"Seite {name}: pages/{name}.py fehlt, Platzhalterseite gebaut")
            else:
                errs.append(f"Seite {name}: pages/{name}.py fehlt (Seite anlegen oder mit --allow-missing bauen)")
        return errs

    def make_input(self, task, preset):
        """Eingabe für den Generator: {seed, colors, options}, Farben bereits als Hex."""
        C = self.color
        opts = {c["id"]: c["default"] for c in task["controls"]}
        opts.update(preset.get("options") or {})
        for c in task["controls"]:
            case = (c.get("cases") or {}).get(str(opts.get(c.get("by")))) if c.get("by") else None
            if case and "default" in case and c["id"] not in (preset.get("options") or {}):
                opts[c["id"]] = case["default"]
            if c["type"] == "color" and opts.get(c["id"]):
                opts[c["id"]] = C.parse(opts[c["id"]], False)["hex"]
            if c["type"] == "colors" and opts.get(c["id"]):
                opts[c["id"]] = [C.parse(x, False)["hex"] for x in opts[c["id"]]]
        seed = C.parse(preset["seed"], False)["hex"] if preset.get("seed") else None
        colors = [{"value": C.parse(x["value"], False)["hex"], "role": x.get("role")} for x in preset["colors"]] if preset.get("colors") else None
        return {"seed": seed, "colors": colors, "options": opts}

    def custom_names(self):
        return {lang: self.copy[lang]["export"]["custom_name"] for lang in LANGS}

    def gen_data(self, task):
        """Weitere Datendateien für den Generator (Aufgabenfeld data_files, etwa models, colornames)."""
        return {n: self.D[n] for n in task.get("data_files") or []}

    def gen_ctx(self, task):
        return {"datasets": self.datasets, "comparisons": self.D["comparisons"], "lang": None, "data": self.gen_data(task)}

    def run_presets(self):
        errs = []
        self.palettes = {}
        C = self.color
        for t in self.tasks:
            gen = self.gens.get(t["id"])
            if gen is None:
                continue
            pals = {}
            for p in t["presets"]:
                label = f"Startpalette {p['id']} ({t['id']})"
                try:
                    pal = gen.build(t, self.make_input(t, p), self.gen_ctx(t))
                except C.SolveError as e:
                    errs.append(f"{label}: Generator findet keine Lösung ({e.key}, {e.values})")
                    continue
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{label}: Generator bricht ab ({_where(e)})")
                    continue
                pal = frame_palette(t, p, self.make_input(t, p), pal, self.custom_names())
                errs += validate_palette(self, t, p, pal, label)
                pals[p["id"]] = pal
            self.palettes[t["id"]] = pals
        return errs

    # ---- Golden-Dateien (tests/golden/<id>.json)
    def golden(self, tid):
        pals = self.palettes[tid]
        return {"task": tid, "presets": {pid: pal["roles"] for pid, pal in pals.items()}}

    def golden_path(self, tid):
        return self.D["task_root"][tid] / "tests" / "golden" / f"{tid}.json"

    def check_golden(self, update=False):
        for t in self.tasks:
            f = self.golden_path(t["id"])
            g = self.golden(t["id"])
            if update:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                continue
            if not f.exists():
                self.warn(f"Aufgabe {t['id']}: {f.relative_to(ROOT)} fehlt (python3 build.py --update-golden, im PR begründen)")
            elif json.loads(f.read_text(encoding="utf-8")) != g:
                self.warn(f"Aufgabe {t['id']}: Startpaletten weichen von {f.relative_to(ROOT)} ab (tests/test_presets.py schlägt fehl)")

    # ---- Seitenrahmen
    def head(self, lang, page, title, desc, kind, extra_head="", main_class="", noindex=False):
        ui = self.copy[lang]["ui"]
        alt_page = self.twin(lang, page)
        robots = '<meta name="robots" content="noindex">\n' if noindex else ""
        cls = f' class="{h(main_class)}"' if main_class else ""
        fonts = "".join(f'<link rel="preload" href="{rel(page, "assets/fonts/" + f)}?v={self.ver.get("fonts/" + f, "")}" as="font" '
                        f'type="font/woff2" crossorigin>' for f in PRELOAD_FONTS)
        return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<meta name="description" content="{h(desc)}">
<meta name="author" content="Sebastian Grundhöfer">
{robots}<link rel="canonical" href="{SITE_URL}/{page}">
<link rel="alternate" hreflang="{lang}" href="{SITE_URL}/{page}">
<link rel="alternate" hreflang="{other(lang)}" href="{SITE_URL}/{alt_page}">
<meta property="og:type" content="website">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<meta property="og:url" content="{SITE_URL}/{page}">
<meta property="og:locale" content="{'de_DE' if lang == 'de' else 'en_US'}">
<meta property="og:image" content="{SITE_URL}/og.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
{fonts}
{theme.script()}<style>{theme.css()}</style>
<link rel="stylesheet" href="{rel(page, 'assets/site.css')}?v={self.ver.get('site.css', '')}">
{extra_head}</head>
<body data-page="{kind}">
<a class="skip" href="#main">{h(ui['skip'])}</a>
{self.topbar(lang, page, kind)}
<main id="main"{cls}>
"""

    def topbar(self, lang, page, kind):
        ui = self.copy[lang]["ui"]
        cur = {"home": "home", "task": "home", "check": "check", "method": "method"}.get(kind)
        items = []
        for k in ("home", "check", "method"):
            long_, short = ui[f"nav.{k}"], ui[f"nav.{k}.s"]
            text = h(long_) if long_ == short else f'<span class="nl">{h(long_)}</span><span class="ns">{h(short)}</span>'
            items.append(f'<a href="{rel(page, self.path(lang, k))}"{" aria-current=\"page\"" if k == cur else ""}>{text}</a>')
        twin = self.twin(lang, page)
        return (f'<header class="topbar"><div class="wrap topbar-in">'
                f'<a class="tb-brand" href="{rel(page, self.path(lang, "home"))}">{LOGO}Farbsprache</a>'
                f'<nav class="tb-nav" aria-label="{h(ui["nav_l"])}">{"".join(items)}</nav>'
                f'<div class="tb-end"><span class="tb-lang"><a href="{rel(page, twin)}" hreflang="{other(lang)}" lang="{other(lang)}" '
                f'aria-label="{h(ui["other_lang"])}"><span class="nl">{h(ui["other_lang"])}</span><span class="ns">{h(ui["other_lang.s"])}</span></a>'
                f'</span>{theme.controls(lang)}</div></div></header>')

    def foot(self, lang, page, scripts=("site.js",)):
        ui = self.copy[lang]["ui"]
        sib = " · ".join(f'<a href="{url}{lang}/" rel="noopener">{name}</a>' for name, url in SIBLINGS)
        tags = "\n".join(f'<script src="{rel(page, "assets/" + s)}?v={self.ver.get(s, "")}" defer></script>' for s in scripts)
        return f"""</main>
<footer class="foot"><div class="wrap foot-in">
<p>{h(ui['foot_license'])}</p>
<p><a href="{rel(page, self.path(lang, 'explained'))}">{h(ui['foot.explained'])}</a> · <a href="{rel(page, self.path(lang, 'sources'))}">{h(ui['foot.sources'])}</a> · <a href="{REPO_URL}" rel="noopener">{h(ui['foot.github'])}</a></p>
<p>{h(ui['foot_siblings'])} {sib}</p>
</div></footer>
<p class="sr-only" role="status" id="status"></p>
{jscript(self.js_text[lang], 'i18n')}
{tags}
</body>
</html>
"""

    def render(self, template, ctx, lang, escape=False):
        """Platzhalter (6.12) mit den Zählern, Vergleichswerten und dem Datum dieses Builds."""
        c = {"refs": self.refs, "counts": self.counts, "date": self.date}
        c.update(ctx or {})
        return self.color.render_text(template, c, lang, escape)[0]

    def stub(self, lang, key, name):
        page = self.path(lang, key)
        kind = key if key in ("check", "method") else "task" if key in self.seg and key not in PAGES else "stub"
        out = [self.head(lang, page, f"{name} – Farbsprache", self.copy[lang]["stub"]["lede"], kind, noindex=True, main_class="stub"),
               f'<section class="mast"><div class="wrap"><h1>{h(name)}</h1><p class="lede">{h(self.copy[lang]["stub"]["lede"])}</p></div></section>',
               self.foot(lang, page)]
        return "".join(out)

    # ---- Sprachweiche, Fehlerseite, Assets
    def landing(self, out):
        c = self.copy["de"]["landing"]
        text = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(c['title'])}</title>
<meta name="description" content="{h(c['desc'])}">
<link rel="canonical" href="{SITE_URL}/">
<link rel="alternate" hreflang="de" href="{SITE_URL}/de/">
<link rel="alternate" hreflang="en" href="{SITE_URL}/en/">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/">
<meta property="og:type" content="website">
<meta property="og:title" content="{h(c['title'])}">
<meta property="og:description" content="{h(c['desc'])}">
<meta property="og:url" content="{SITE_URL}/">
<meta property="og:image" content="{SITE_URL}/og.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
{theme.script()}<script id="lang-switch">
(function () {{
  var search = location.search.replace(/^\\?/, ''), keep = [], lang = null, i, part, name, m;
  var parts = search ? search.split('&') : [];
  for (i = 0; i < parts.length; i++) {{
    part = parts[i]; name = part.split('=')[0];
    try {{ name = decodeURIComponent(name.replace(/\\+/g, ' ')); }} catch (e) {{}}
    if (name === 'lang') {{ if (!lang) {{ m = part.slice(part.indexOf('=') + 1); if (m === 'de' || m === 'en') lang = m; }} }}
    else if (part) keep.push(part);
  }}
  if (!lang) {{ try {{ var s = localStorage.getItem('farbsprache.language'); if (s === 'de' || s === 'en') lang = s; }} catch (e) {{}} }}
  if (!lang) {{
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
    for (i = 0; i < prefs.length; i++) {{
      m = /^(de|en)(?:-|$)/i.exec(String(prefs[i] || ''));
      if (m) {{ lang = m[1].toLowerCase(); break; }}
    }}
  }}
  if (!lang) lang = 'en';
  location.replace(lang + '/' + (keep.length ? '?' + keep.join('&') : '') + location.hash);
}})();
</script>
<style>{theme.css()}body{{margin:0;font:17px/1.6 Inter,Helvetica,Arial,sans-serif;background:var(--ground);color:var(--ink);display:grid;place-items:center;min-height:100vh;padding:16px;box-sizing:border-box}}a{{color:var(--accent)}}</style>
</head>
<body><main><h1>Farbsprache</h1><p><a href="de/" hreflang="de" lang="de">Deutsch</a> · <a href="en/" hreflang="en" lang="en">English</a></p></main></body>
</html>
"""
        (out / "index.html").write_text(text, encoding="utf-8")

    def not_found(self, out):
        de, en = self.copy["de"]["notfound"], self.copy["en"]["notfound"]
        (out / "404.html").write_text(
            f'<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>404 – Farbsprache</title><meta name="robots" content="noindex"><link rel="icon" href="{FAVICON}">{theme.script()}'
            f'<style>{theme.css()}body{{margin:0;font:17px/1.6 Inter,Helvetica,Arial,sans-serif;background:var(--ground);color:var(--ink);'
            f'display:grid;place-items:center;min-height:100vh;padding:16px;box-sizing:border-box}}main{{max-width:36rem;border-top:3px solid var(--ink);padding-top:12px}}'
            f'h1{{font-size:clamp(48px,12vw,96px);line-height:1;letter-spacing:-.045em;margin:8px 0 16px}}p{{margin:0 0 10px}}'
            f'a{{color:var(--accent);text-underline-offset:3px;white-space:nowrap}}.brand{{font:700 12px Inter,sans-serif;letter-spacing:.06em;text-transform:uppercase}}</style></head>'
            f'<body><main><p class="brand">Farbsprache</p><h1>404</h1>'
            f'<p lang="de">{h(de["text"])} <a href="/farbsprache/de/" hreflang="de">{h(de["link"])}</a></p>'
            f'<p lang="en">{h(en["text"])} <a href="/farbsprache/en/" hreflang="en">{h(en["link"])}</a></p></main></body></html>',
            encoding="utf-8")

    def fs_const(self):
        k = {}
        for name in ("color-constants", "cvd"):
            k.update({a: b for a, b in self.D["files"][name].items() if not a.startswith("_")})
        k["css_names"] = {a: b for a, b in self.D["files"]["css-names"].items() if not a.startswith("_")}
        return k

    def copy_assets(self, out):
        a = out / "assets"
        a.mkdir(parents=True, exist_ok=True)

        def put(name, data):
            f = a / name
            f.parent.mkdir(parents=True, exist_ok=True)
            data = data.encode("utf-8") if isinstance(data, str) else data
            f.write_bytes(data)
            self.ver[name] = asset_version(data)
        # Schriften zuerst: site.css verweist mit deren Inhalts-Hash auf sie (url(fonts/<datei>?v=…))
        for f in sorted((ROOT / "web" / "fonts").glob("*.woff2")):
            put("fonts/" + f.name, f.read_bytes())
        for name in FONT_LICENSES:
            put("fonts/" + name, (ROOT / "data" / "licenses" / name).read_bytes())
        css = (ROOT / "web" / "site.css").read_text(encoding="utf-8")
        for r in self.roots:
            for f in sorted((r / "web" / "css").glob("*.css")):
                css += f"\n/* ---------- {f.name} ---------- */\n" + f.read_text(encoding="utf-8")

        def font_url(m):
            if "fonts/" + m.group(1) not in self.ver:
                raise BuildError([f"site.css: Schrift {m.group(1)} fehlt unter web/fonts/"])
            return f'url(fonts/{m.group(1)}?v={self.ver["fonts/" + m.group(1)]})'
        put("site.css", compact_css(re.sub(r"url\(fonts/([A-Za-z0-9-]+\.woff2)\)", font_url, css)))
        consts = json.dumps(self.fs_const(), ensure_ascii=False, separators=(",", ":"))
        put("color.js", "/* " + W3C_NOTICE + " " + WCAG_NOTICE + " */\nvar FS_CONST=" + consts + ";\n"
            + compact_js((ROOT / "web" / "color.js").read_text(encoding="utf-8")))
        put("site.js", compact_js((ROOT / "web" / "site.js").read_text(encoding="utf-8")))
        for name in ("export.js", "check.js"):
            f = ROOT / "web" / name
            if f.exists():
                put(name, compact_js(f.read_text(encoding="utf-8")))
        for g, f in self.gen_js.items():
            put(f"gen/{g}.js", compact_js(f.read_text(encoding="utf-8")))
        for r in self.roots:  # alle DOM-Haken, auch ui/check.js der Prüfseite (P5)
            for f in sorted((r / "web" / "ui").glob("*.js")):
                put(f"ui/{f.name}", compact_js(f.read_text(encoding="utf-8")))
        og = ROOT / "og.png"
        if og.exists():
            shutil.copyfile(og, out / "og.png")
        else:
            self.warn("og.png fehlt – Link-Vorschauen bleiben ohne Bild (python3 tools/og.py)")
        (out / ".nojekyll").write_text("", encoding="utf-8")

    # ---- Schreiben
    def pages(self, lang):
        """(Pfad, HTML) aller Seiten einer Sprache in fester Reihenfolge."""
        from pages import home, task as task_page
        out = [(self.path(lang, "home"), home.page(self, lang))]
        for tid in self.order:
            if tid in self.task_by_id:
                out.append((self.path(lang, tid), task_page.page(self, lang, self.task_by_id[tid])))
            else:
                out.append((self.path(lang, tid), self.stub(lang, tid, tid)))
        for name in PAGES:
            if name in self.page_mods:
                out.append((self.path(lang, name), self.page_mods[name].page(self, lang)))
            else:
                out.append((self.path(lang, name), self.stub(lang, name, self.copy[lang]["ui"]["page." + name])))
        return out

    def write_all(self):
        tmp = self.out.parent / (self.out.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        errs, files = [], []
        try:
            self.copy_assets(tmp)
            self.landing(tmp)
            self.not_found(tmp)
            for lang in LANGS:
                for page, text in self.pages(lang):
                    files.append(write(tmp, page, text.replace("</body>", REMEMBER + "\n</body>")))
        except BuildError:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        except Exception as e:  # noqa: BLE001  (ein Seitenfehler wird eine Meldung, docs/ bleibt unverändert)
            shutil.rmtree(tmp, ignore_errors=True)
            errs.append(f"Seiten: {_where(e)}")
            raise BuildError(errs) from e
        if self.out.exists():
            shutil.rmtree(self.out)
        tmp.rename(self.out)
        self.files = [self.out / f.relative_to(tmp) for f in files]
        return self.files

    def write_readmes(self):
        """README.md und README.de.md aus web/readme.*.md, mit denselben Zahlen wie die Website."""
        for src, dst, lang in (("readme.en.md", "README.md", "en"), ("readme.de.md", "README.de.md", "de")):
            text = (ROOT / "web" / src).read_text(encoding="utf-8")
            for key in ("tasks", "presets", "pairs", "rules", "sources"):
                text = text.replace(f"__N_{key.upper()}__", num(self.counts[key], lang))
            (ROOT / dst).write_text(text, encoding="utf-8")


def frame_palette(task, preset, inp, pal, names):
    """Der Rahmen setzt task, preset, input, name_de und name_en (Spiegel: FS.site.framePalette).
    preset ist das Preset-Objekt oder None für eigene Eingaben; names die Namen eigener Paletten je Sprache."""
    if not isinstance(pal, dict):
        return pal
    pal["task"] = task["id"]
    pal["preset"] = preset["id"] if preset else None
    pal["input"] = inp
    for lang in LANGS:
        pal["name_" + lang] = preset["name_" + lang] if preset else names[lang]
    return pal


def validate_palette(site, task, preset, pal, label):
    """Palettenobjekt (6.14) prüfen: Form, Rollen, nachgerechnete Paare, Normpaare, Hinweise in beide Richtungen."""
    C = site.color
    from tools import export as X
    errs = []
    for k in ("task", "preset", "input", "name_de", "name_en", "modes", "roles", "pairs", "decorative", "distinct",
              "changes", "findings", "usage", "extra"):
        if k not in pal:
            errs.append(f"{label}: Palettenobjekt ohne Feld {k}")
    if errs:
        return errs
    if pal["task"] != task["id"] or pal["preset"] != preset["id"]:
        errs.append(f"{label}: task/preset im Palettenobjekt passen nicht ({pal['task']}/{pal['preset']})")
    if pal["modes"] != task["modes"]:
        errs.append(f"{label}: modes {pal['modes']} passt nicht zur Aufgabe {task['modes']}")
    declared = {r["id"] for r in task["roles"]}
    for mode in pal["modes"]:
        roles = pal["roles"].get(mode)
        if not isinstance(roles, dict):
            errs.append(f"{label}: Rollen für Modus {mode} fehlen")
            continue
        for rid, hx in roles.items():
            if rid not in declared:
                errs.append(f"{label}: Rolle {rid} ({mode}) ist in der Aufgabe nicht deklariert")
            if not isinstance(hx, str) or not re.fullmatch(r"#[0-9A-F]{6}", hx):
                errs.append(f"{label}: Rolle {rid} ({mode}) hat kein Hex #RRGGBB: {hx!r}")
    if errs:
        return errs
    lang = "de"
    for p in pal["pairs"]:
        r = C.contrast(pal["roles"][p["mode"]][p["fg"]], pal["roles"][p["mode"]][p["bg"]])
        if abs(r - p["ratio"]) > 1e-9:
            errs.append(f"{label}: Paar {p['fg']}/{p['bg']} ({p['mode']}) ratio passt nicht zum Hex")
        if not p["pass"] or r < p["min"]:
            mode = site.copy["de"]["export"].get("mode." + p["mode"], p["mode"])
            errs.append(f"Startpalette {preset['id']} ({task['id']}, {mode}): {p['fg']}/{p['bg']} "
                        f"{C.fmt_ratio(r, lang, p['min'])[:-2]} < {X.fmt_threshold(p['min'], lang)[:-2]}")
    for p in pal["decorative"]:
        r = C.contrast(pal["roles"][p["mode"]][p["fg"]], pal["roles"][p["mode"]][p["bg"]])
        if abs(r - p["ratio"]) > 1e-9:
            errs.append(f"{label}: dekoratives Paar {p['fg']}/{p['bg']} ({p['mode']}) ratio passt nicht zum Hex")
    for d in pal["distinct"]:
        try:
            hx = pal["roles"][d["mode"]]
            v = C.distance(hx[d["a"]], hx[d["b"]], d["kind"])
            if abs(v - d["value"]) > 1e-9:
                errs.append(f"{label}: Abstand {d['id']} ({d['mode']}) passt nicht zu den Rollen {d['a']}/{d['b']}")
            c = d.get("compare")
            if c and c.get("a"):
                if abs(C.distance(c["a"], c["b"], c["kind"]) - c["value"]) > 1e-9:
                    errs.append(f"{label}: Vergleichswert {c.get('id')} passt nicht zu {c['a']}/{c['b']}")
            elif c and c.get("id") not in site.refs:
                errs.append(f"{label}: Vergleich {c.get('id')} braucht a, b und kind oder eine ID aus data/comparisons.json")
        except (KeyError, TypeError, ValueError) as e:
            errs.append(f"{label}: distinct-Eintrag unvollständig ({_where(e)})")
    for lang_ in LANGS:
        tc = site.copy[lang_].get(task["id"], {})
        for ch in pal["changes"]:
            if "change." + ch.get("key", "?") not in tc:
                errs.append(f"{label}: Text change.{ch.get('key')} fehlt in COPY[{lang_}][{task['id']!r}]")
            for k in ("role", "mode", "from", "to"):
                if k not in ch:
                    errs.append(f"{label}: Änderung ohne Feld {k}")
        for f in pal["findings"]:
            if "finding." + f.get("id", "?") not in tc:
                errs.append(f"{label}: Text finding.{f.get('id')} fehlt in COPY[{lang_}][{task['id']!r}]")
        for d in pal["distinct"]:
            c = d.get("compare")
            if c and c.get("a") and "compare." + c.get("id", "?") not in tc:
                errs.append(f"{label}: Text compare.{c.get('id')} fehlt in COPY[{lang_}][{task['id']!r}]")
        ex = pal.get("extra") or {}
        keys = ex.get("summary") or []
        keys = [keys] if isinstance(keys, str) else list(keys)
        for k in keys + ([ex["pair_note"]] if ex.get("pair_note") else []):
            if k not in tc:
                errs.append(f"{label}: Text {k} (palette.extra) fehlt in COPY[{lang_}][{task['id']!r}]")
    got = {f["id"] + ("@" + f["mode"] if f.get("mode") else "") for f in pal["findings"]}
    want = set(preset.get("expect") or [])
    for x in sorted(got - want):
        errs.append(f"{label}: Hinweis {x} berechnet, steht aber nicht in expect")
    for x in sorted(want - got):
        errs.append(f"{label}: expect nennt {x}, berechnet wurde es nicht")
    try:
        json.dumps(pal, allow_nan=False)
    except ValueError:
        errs.append(f"{label}: Palettenobjekt enthält NaN oder Unendlich (powerless als None führen)")
    return errs


def build_date(arg):
    if arg:
        return datetime.date.fromisoformat(arg).isoformat()
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde:
        return datetime.datetime.fromtimestamp(int(sde), datetime.timezone.utc).date().isoformat()
    return datetime.date.today().isoformat()


def build_site(roots, out, date, allow_missing=False, seg=None, update_golden=False, readmes=False):
    """Ein vollständiger Build in out/ (über out.tmp/). Wirft BuildError mit den Meldungen."""
    site = Site(roots, out, date, allow_missing, seg)
    site.prepare()
    site.check_golden(update_golden)
    site.write_all()
    if readmes:
        site.write_readmes()
    return site


def build_fixtures(date, update_golden=False):
    """Testaufgabe „fixture“ (tests/fixtures/) von Ende zu Ende, nach tests/out/fixtures/docs/."""
    return build_site([ROOT, FIXTURES], FIXTURE_OUT, date, allow_missing=True, seg=FIXTURE_SEG, update_golden=update_golden)


def report(site, label):
    for w in site.warnings:
        print("  WARNUNG", w, file=sys.stderr)
    n = len(site.files)
    print(f"  {label}: {n} Seiten, {site.counts['tasks']} Aufgaben, {site.counts['presets']} Startpaletten, "
          f"{site.counts['pairs']} geprüfte Paare, {site.counts['rules']} Regeln, {site.counts['sources']} Quellen -> "
          f"{site.out.relative_to(ROOT)}/")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Baut Farbsprache nach docs/.")
    ap.add_argument("--date", help="Build-Datum JJJJ-MM-TT (sonst SOURCE_DATE_EPOCH oder heute)")
    ap.add_argument("--allow-missing", action="store_true", help="fehlende Aufgaben und Seiten als Platzhalter (nur lokal)")
    ap.add_argument("--fixtures", action="store_true", help="zusätzlich die Testaufgabe nach tests/out/fixtures/docs/")
    ap.add_argument("--update-golden", action="store_true", help="tests/golden/*.json neu schreiben")
    args = ap.parse_args(argv)
    try:
        date = build_date(args.date)
    except ValueError:
        sys.exit(f"--date {args.date}: kein Datum JJJJ-MM-TT")
    try:
        # README.md und README.de.md nur im strengen Build: Paketbauten (--allow-missing) und --update-golden
        # überschrieben sonst Dateien von P0 mit Teilzahlen.
        site = build_site([ROOT], DOCS, date, args.allow_missing, None, args.update_golden,
                          readmes=not (args.allow_missing or args.update_golden))
    except BuildError as e:
        for p in e.errors:
            print("  FEHLER", p, file=sys.stderr)
        sys.exit(f"{len(e.errors)} Datenfehler – Build abgebrochen")
    report(site, "Website")
    if args.fixtures:
        try:
            fx = build_fixtures(date, args.update_golden)
        except BuildError as e:
            for p in e.errors:
                print("  FEHLER", p, file=sys.stderr)
            sys.exit(f"{len(e.errors)} Fehler in der Testaufgabe – Build abgebrochen")
        report(fx, "Testaufgabe")


if __name__ == "__main__":
    main()
