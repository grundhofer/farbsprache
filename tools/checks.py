"""Datenprüfungen vor dem Build. Jede check_*-Funktion liefert deutsche Meldungen
nach dem Muster „Kontext id: Problem (was tun)“. check_all(root) sammelt sie.

Leitsatz wie in Bildsprache: Was die Website behauptet, wird nachgerechnet. Hier heißt das zuerst:
Daten enthalten Eingaben, Schwellen, Texte und Quellen, nie Messergebnisse, und keine Zahl steht von Hand
im Text. load_all() lädt alles selbst in try/except; kaputtes JSON wird eine Meldung, kein Traceback.

Aufgaben hängen eigene Prüfungen an: tools/checks_<owner>.py mit check(D, warn) -> [Meldungen].
D ist das Datenbündel aus load_all(); warn(text) meldet eine WARNUNG.
Data checks run before the build."""
import datetime, importlib.util, json, pathlib, re

SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
HEX6 = re.compile(r"#[0-9A-Fa-f]{6}")
LEVELS = ("norm", "research", "convention", "unproven")
STRENGTHS = ("strong", "partial")
SRC_KINDS = ("norm", "spec", "paper", "review", "book", "docs", "code", "press", "secondary")
ACCESS = ("fulltext", "abstract", "snippet")
ROLE_KINDS = ("surface", "text", "ui", "decor", "data")
CTL_TYPES = ("chips", "toggle", "stepper", "color", "colors", "text")
RELIABILITY = ("defined", "computed", "measured", "consensus")
DS_KINDS = ("categorical", "sequential", "diverging", "mixed")  # mixed: Paletten verschiedener Art, maßgeblich ist schemes[].kind
CVD_KINDS = ("normal", "deutan", "protan", "tritan", "gray")
FORBIDDEN = {"contrast", "ratio", "kontrast", "delta", "distance", "abstand", "result", "ergebnis", "pass", "cr"}
README_KEYS = ("__N_TASKS__", "__N_PRESETS__", "__N_PAIRS__", "__N_RULES__", "__N_SOURCES__")
COLORBREWER_NOTICE = ("This product includes color specifications and designs developed by Cynthia Brewer "
                      "(http://colorbrewer.org/).")
GENERIC_FORMATS = ("css", "tailwind", "dtcg", "hex", "agent", "rationale")
SIBLING_SITES = ("bildsprache", "designsprache")
RESERVED = ("c", "p", "lang")
PRESET_COUNT = {"charts": 4}
ALLOWED_RATIOS = ("3:1", "4,5:1", "4.5:1", "7:1", "21:1")
RATIO_RE = re.compile(r"\d+([.,]\d+)?\s*:\s*1(?![0-9])")
NUMWORD_RE = re.compile(r"(ΔE|Delta ?E|Abstand|Deckkraft|distance|opacity)\D{0,12}\d")
PH_ANY = re.compile(r"\{([A-Za-z]+):[^{}]*\}")
PH_KNOWN = re.compile(r"\{(cr|dist|gray|gs|L|proj|scrim|ref|hex|count|date)(?::([^{}]*))?\}")
ARITY = {"cr": 2, "dist": 3, "gray": 1, "gs": 2, "L": 1, "proj": 3, "scrim": 3, "ref": 1, "hex": 1, "count": 1, "date": 0}
HEX_ANY = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
TAG = re.compile(r"<[^>]*>")
SHORT_IMP = ("Wähl ", "Kopier ", "Prüf ", "Füg ", "Setz ", "Speicher ", "Frag ")
# Nur in Imperativstellung: am Satzanfang (groß), nach „und“, „oder“, „dann“ oder nach einem Komma (klein, etwa
# „Fehlt eine Rolle, frag nach“). So löst ein Substantiv wie „im Speicher“ nichts aus.
_IMP = "|".join(w.strip() for w in SHORT_IMP)
SHORT_IMP_RE = re.compile(rf"(?:^\s*|[.!?:;]\s+|[„“\"'(\[]\s*)({_IMP})\s|(?:\b(?:und|oder|dann)|,)\s+({_IMP.lower()})\s")
# Sprachmarken in Quellentexten: [en]…[/en] und [de]…[/de] (pages/sources.py zeichnet sie mit lang aus)
LANG_MARK = re.compile(r"\[(/?)(de|en)\]")
TITLE_LANGS = (None, "de", "en", "en/de", "de/en")
BRITISH = ("colour", "grey", "centre", "catalogue", "licence", "favour")
HYPE = ("einfach", "mühelos", "perfekt", "seamless", "powerful", "perfect", "colorblind safe")
SIE = re.compile(r"[^.!?:\s]\s+(Sie|Ihr|Ihre|Ihnen|Ihrer|Ihren|Ihrem|Ihres)\b")
COLOR_PROPS = re.compile(r"^(color|background|background-color|border|border-[a-z-]*|outline|outline-color|fill|stroke|"
                         r"box-shadow|text-shadow|text-decoration|text-decoration-color|caret-color|accent-color|"
                         r"column-rule|column-rule-color|stop-color|flood-color|lighting-color)$")
NO_TEXT_FILES = ("color-constants.json", "cvd.json", "css-names.json", "testvectors.json")


# ---- Laden

def _rel(root, p):
    try:
        return str(pathlib.Path(p).relative_to(root))
    except ValueError:
        return str(p)


def read_json(path, errs, label):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        errs.append(f"{label}: Datei fehlt")
    except UnicodeDecodeError as e:
        errs.append(f"{label}: kein UTF-8 ({e})")
    except json.JSONDecodeError as e:
        errs.append(f"{label}: kein gültiges JSON, Zeile {e.lineno} Spalte {e.colno}: {e.msg} (Datei reparieren)")
    return None


def load_module(path, name):
    """Python-Modul aus einer Datei laden, ohne sys.path zu verändern."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find(roots, rel):
    """Letzte Wurzel, die die Datei hat (Überlagerung: die Testaufgabe ersetzt _order.json)."""
    hit = None
    for r in roots:
        if (r / rel).exists():
            hit = r / rel
    return hit


def _own(roots, r, f):
    """Darf Datei f aus Wurzel r geladen werden? Mit Überlagerung (Testaufgabe) liefert das Projekt nur seinen
    Kern: data/*/core.json, web/copy/core.py, Datensätze, Konstanten. Aufgaben, Regeln, Erklärt, Quellen,
    Texte und eigene Prüfungen (tools/checks_*.py) bleiben draußen, damit die Testaufgabe nie von ihnen abhängt."""
    return len(roots) == 1 or r != roots[0] or pathlib.Path(f).stem == "core"


def load_all(roots):
    """Lädt alle Daten aus den Wurzeln (Projekt, optional tests/fixtures) → (D, Fehler).
    Mit mehreren Wurzeln ist die erste nur Kern (siehe _own), Dateien späterer Wurzeln überlagern."""
    roots = [pathlib.Path(r) for r in roots]
    root = roots[0]
    errs = []
    D = {"root": root, "roots": roots, "tasks": {}, "task_root": {}, "rules": {}, "explain": {}, "sources": {},
         "datasets": {}, "owner": {"rules": {}, "explain": {}, "sources": {}}, "copy": {"de": {}, "en": {}},
         "copy_src": {}, "js_text": {"de": {}, "en": {}}, "patterns": {}, "pkg_checks": [], "readme": {},
         "files": {}, "order": [], "explain_order": [], "comparisons": None, "models": None, "colornames": None,
         "check": None, "blocklist": []}
    # Aufgaben
    p = _find(roots, "data/tasks/_order.json")
    order = read_json(p, errs, "data/tasks/_order.json") if p else errs.append("data/tasks/_order.json: Datei fehlt")
    if order is not None:
        if isinstance(order, dict):
            order = order.get("order")
        if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
            errs.append("data/tasks/_order.json: erwartet {\"order\": [Aufgaben-IDs]}")
        else:
            D["order"] = order
    for r in roots:
        for f in sorted((r / "data" / "tasks").glob("*.json")):
            if f.name.startswith("_") or not _own(roots, r, "-"):
                continue
            t = read_json(f, errs, _rel(root, f))
            if t is None:
                continue
            D["files"][("task", f.stem)] = _rel(root, f)
            if not isinstance(t, dict):
                errs.append(f"{_rel(root, f)}: erwartet ein Objekt")
                continue
            if t.get("id") != f.stem:
                errs.append(f"Aufgabe {f.stem}: Feld id ({t.get('id')!r}) passt nicht zum Dateinamen")
            D["tasks"][f.stem] = t
            D["task_root"][f.stem] = r
    # Regeln, Erklärt, Quellen
    for kind, key in (("rules", "rules"), ("explain", "entries"), ("sources", "sources")):
        for r in roots:
            for f in sorted((r / "data" / kind).glob("*.json")):
                if f.name.startswith("_") or not _own(roots, r, f):
                    continue
                d = read_json(f, errs, _rel(root, f))
                if d is None:
                    continue
                items = d.get(key) if isinstance(d, dict) else None
                if not isinstance(items, list):
                    errs.append(f"{_rel(root, f)}: erwartet {{\"{key}\": [...]}}")
                    continue
                for it in items:
                    if not isinstance(it, dict) or not isinstance(it.get("id"), str):
                        errs.append(f"{_rel(root, f)}: Eintrag ohne id")
                        continue
                    if it["id"] in D[kind]:
                        errs.append(f"{kind} {it['id']}: doppelt ({D['owner'][kind][it['id']]} und {f.stem})")
                    D[kind][it["id"]] = it
                    D["owner"][kind][it["id"]] = f.stem
    p = _find(roots, "data/explain/_order.json")
    if p:
        eo = read_json(p, errs, "data/explain/_order.json")
        if eo is not None:
            eo = eo.get("order") if isinstance(eo, dict) else eo
            if isinstance(eo, list):
                D["explain_order"] = eo
            else:
                errs.append("data/explain/_order.json: erwartet {\"order\": [IDs]}")
    else:
        errs.append("data/explain/_order.json: Datei fehlt")
    # Datensätze und Einzeldateien
    for r in roots:
        for f in sorted((r / "data" / "datasets").glob("*.json")):
            d = read_json(f, errs, _rel(root, f))
            if d is not None:
                D["datasets"][f.stem] = d
    for name in ("comparisons", "models", "colornames", "check"):
        p = _find(roots, f"data/{name}.json")
        if p:
            D[name] = read_json(p, errs, f"data/{name}.json")
        elif name == "comparisons":
            errs.append("data/comparisons.json: Datei fehlt")
    for name in ("color-constants", "cvd", "css-names", "testvectors"):
        p = root / "data" / f"{name}.json"
        D["files"][name] = read_json(p, errs, f"data/{name}.json")
    # Texte (web/copy/*.py)
    for r in roots:
        for f in sorted((r / "web" / "copy").glob("*.py")):
            if not _own(roots, r, f):
                continue
            label = _rel(root, f)
            try:
                mod = load_module(f, f"fs_copy_{abs(hash(str(f)))}")
            except Exception as e:  # noqa: BLE001  (jeder Fehler im Modul ist ein Datenfehler)
                errs.append(f"{label}: lässt sich nicht laden ({type(e).__name__}: {e})")
                continue
            copy = getattr(mod, "COPY", None)
            if not isinstance(copy, dict) or set(copy) != {"de", "en"}:
                errs.append(f"{label}: COPY fehlt oder hat nicht genau die Sprachen de und en")
                continue
            for lang in ("de", "en"):
                for page, keys in copy[lang].items():
                    if not isinstance(keys, dict):
                        errs.append(f"{label}: COPY[{lang}][{page}] ist kein Objekt")
                        continue
                    if page in D["copy"][lang] and D["copy_src"].get(page) != label:
                        errs.append(f"{label}: Seite {page} ist schon in {D['copy_src'][page]} definiert")
                    D["copy"][lang][page] = keys
                    D["copy_src"][page] = label
            js = getattr(mod, "JS_TEXT", None)
            if js is not None:
                for lang in ("de", "en"):
                    D["js_text"][lang].update(js.get(lang, {}))
    # Muster
    for tid, r in D["task_root"].items():
        t = D["tasks"][tid]
        pid = t.get("pattern") if isinstance(t.get("pattern"), str) else tid
        entry = {}
        for k, rel in (("html", f"patterns/{pid}.html"), ("mini", f"patterns/{tid}-mini.svg")):
            p = _find(roots, rel)
            entry[k + "_path"] = rel
            entry[k] = p.read_text(encoding="utf-8") if p else None
        D["patterns"][tid] = entry
    # Weitere Muster ohne Aufgabe (etwa die Demo für Kurz erklärt): gleiche Regeln, Präfix .demo-<name ohne demo->
    D["extra_patterns"] = {}
    used = {e["html_path"] for e in D["patterns"].values()}
    for r in roots:
        if not _own(roots, r, "-"):
            continue
        for f in sorted((r / "patterns").glob("*.html")):
            if f"patterns/{f.name}" not in used:
                D["extra_patterns"][f"patterns/{f.name}"] = f.read_text(encoding="utf-8")
    # README-Vorlagen, Sperrliste, eigene Prüfungen (tools/checks_*.py)
    for lang in ("de", "en"):
        p = root / "web" / f"readme.{lang}.md"
        D["readme"][lang] = p.read_text(encoding="utf-8") if p.exists() else None
    p = root / "tools" / "blocklist.txt"
    if p.exists():
        D["blocklist"] = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    else:
        errs.append("tools/blocklist.txt: Datei fehlt")
    for r in roots:
        for f in sorted((r / "tools").glob("checks_*.py")):
            if not _own(roots, r, "-"):
                continue
            try:
                D["pkg_checks"].append((_rel(root, f), load_module(f, f"fs_checks_{abs(hash(str(f)))}")))
            except Exception as e:  # noqa: BLE001
                errs.append(f"{_rel(root, f)}: lässt sich nicht laden ({type(e).__name__}: {e})")
    return D, errs


# ---- Hilfen

def _walk(o, path=""):
    """Alle (pfad, schlüssel, wert) eines JSON-Baums."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield path, k, v
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{path}[{i}]")


def _need(errs, ctx, obj, fields):
    for f in fields:
        if f not in obj or obj[f] in (None, ""):
            errs.append(f"{ctx}: Feld {f} fehlt")


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def texts(D):
    """Alle Nutzertexte → (kontext, sprache, text, art). art: copy | data | claim | quote."""
    out = []
    for lang in ("de", "en"):
        for page, keys in D["copy"][lang].items():
            for k, v in keys.items():
                for i, s in enumerate(v if isinstance(v, list) else [v]):
                    if isinstance(s, dict):
                        s = s.get("text")
                    if isinstance(s, str):
                        out.append((f"{D['copy_src'].get(page, 'web/copy')} {lang}.{page}.{k}", lang, s, "copy"))
        for k, s in D["js_text"][lang].items():
            out.append((f"JS_TEXT {lang}.{k}", lang, s, "copy"))

    def data(label, obj, exempt=()):
        for path, k, v in _walk(obj):
            lang = "de" if k.endswith("_de") else "en" if k.endswith("_en") else None
            if lang is None:
                continue
            art = "claim" if k.startswith("claim_") else "data"
            for s in v if isinstance(v, list) else [v]:
                if isinstance(s, dict):
                    s = s.get("text")
                if isinstance(s, str):
                    out.append((f"{label} {path}.{k}".replace(" .", " "), lang, s, art))
    for tid, t in D["tasks"].items():
        data(f"Aufgabe {tid}", t)
    for kind in ("rules", "explain", "sources"):
        for i, it in D[kind].items():
            data(f"{kind} {i}", it)
    for i, ds in D["datasets"].items():
        data(f"Datensatz {i}", ds)
    for name in ("comparisons", "models", "colornames", "check"):
        if D.get(name) is not None:
            data(f"data/{name}.json", D[name])
    if D.get("models"):
        for m in D["models"].get("models", []):
            if isinstance(m, dict) and isinstance(m.get("quote"), str):
                out.append((f"models {m.get('id')}.quote", "en", m["quote"], "quote"))
    return out


def _strip(s):
    return HEX_ANY.sub("§", PH_KNOWN.sub("§", TAG.sub(" ", s)))


# ---- 1 · Schema der Aufgaben, Regeln, Erklärt, Quellen, Datensätze

def check_tasks(D, allow_missing, warn):
    errs = []
    order = D["order"]
    for tid in order:
        if not SLUG.fullmatch(tid):
            errs.append(f"data/tasks/_order.json: ungültige ID {tid!r}")
        if tid not in D["tasks"]:
            msg = f"Aufgabe {tid}: data/tasks/{tid}.json fehlt (Aufgabe anlegen oder mit --allow-missing bauen)"
            (warn if allow_missing else errs.append)(msg)
    if len(set(order)) != len(order):
        errs.append("data/tasks/_order.json: doppelte Aufgaben")
    for tid in D["tasks"]:
        if tid not in order:
            errs.append(f"Aufgabe {tid}: steht nicht in data/tasks/_order.json")
    for tid, t in D["tasks"].items():
        errs += check_task(D, tid, t, allow_missing, warn)
    return errs


def check_task(D, tid, t, allow_missing=False, warn=None):
    """Schema einer Aufgabe. Verweise auf Regeln und Erklärt-Einträge, die es (noch) nicht gibt, sind mit
    --allow-missing nur eine WARNUNG: Eine Aufgabe darf Einträge nennen, die erst später dazukommen."""
    errs = []
    c = f"Aufgabe {tid}"
    missing = warn if allow_missing and warn is not None else errs.append
    _need(errs, c, t, ("id", "generator", "name_de", "name_en", "summary_de", "summary_en", "modes", "controls",
                       "presets", "roles", "pairs", "rules", "explain", "pattern", "exports", "related",
                       "not_checked_de", "not_checked_en"))
    if errs:
        return errs
    if not isinstance(t["generator"], str) or not SLUG.fullmatch(t["generator"]):
        errs.append(f"{c}: generator muss ein Slug sein")
    modes = t["modes"]
    if modes not in (["light", "dark"], ["default"], ["light"], ["dark"]):
        errs.append(f"{c}: modes muss [\"light\", \"dark\"] oder [\"default\"] sein")
    roles = {}
    for r in t["roles"]:
        rc = f"{c} Rolle {r.get('id')}"
        _need(errs, rc, r, ("id", "name_de", "name_en", "use_de", "use_en", "kind"))
        if "core" not in r or not isinstance(r.get("core"), bool):
            errs.append(f"{rc}: Feld core fehlt oder ist kein Wahrheitswert")
        if r.get("kind") not in ROLE_KINDS:
            errs.append(f"{rc}: kind muss eines von {', '.join(ROLE_KINDS)} sein")
        if isinstance(r.get("id"), str):
            if not SLUG.fullmatch(r["id"]):
                errs.append(f"{rc}: ungültige Rollen-ID")
            if r["id"] in roles:
                errs.append(f"{rc}: doppelt")
            roles[r["id"]] = r
        if r.get("css_name") is not None and not SLUG.fullmatch(str(r["css_name"])):
            errs.append(f"{rc}: css_name muss ein Slug sein")
    for i, line in enumerate(t["pairs"]):
        lc = f"{c} pairs[{i}]"
        _need(errs, lc, line, ("fg", "on", "min", "criterion", "rule"))
        if line.get("fg") not in roles:
            errs.append(f"{lc}: fg {line.get('fg')} ist keine Rolle der Aufgabe")
        for b in line.get("on") or []:
            if b not in roles:
                errs.append(f"{lc}: on {b} ist keine Rolle der Aufgabe")
        if not _is_num(line.get("min")) or not 1 < line["min"] <= 21:
            errs.append(f"{lc}: min muss eine Zahl über 1 sein")
        if line.get("rule") and line["rule"] not in D["rules"]:
            missing(f"{lc}: Regel {line['rule']} gibt es nicht")
    for key in ("decorative", "advisory"):
        for i, line in enumerate(t.get(key) or []):
            lc = f"{c} {key}[{i}]"
            if line.get("fg") not in roles:
                errs.append(f"{lc}: fg {line.get('fg')} ist keine Rolle der Aufgabe")
            ons = line.get("on") if isinstance(line.get("on"), list) else [line.get("on")]
            for b in ons:
                if b not in roles:
                    errs.append(f"{lc}: on {b} ist keine Rolle der Aufgabe")
            if key == "advisory":
                _need(errs, lc, line, ("min", "finding"))
    for i, d in enumerate(t.get("distinct") or []):
        lc = f"{c} distinct[{i}]"
        _need(errs, lc, d, ("id", "set", "kinds"))
        for r in d.get("set") or []:
            if r not in roles:
                errs.append(f"{lc}: {r} ist keine Rolle der Aufgabe")
        for k in d.get("kinds") or []:
            if k not in CVD_KINDS:
                errs.append(f"{lc}: unbekannte Sichtweise {k}")
    # Steuerelemente (16)
    ids = set()
    for ctl in t["controls"]:
        cc = f"{c} Steuerelement {ctl.get('id')}"
        _need(errs, cc, ctl, ("id", "type", "label_key"))
        if "default" not in ctl:
            errs.append(f"{cc}: Feld default fehlt")
        if "visible" not in ctl or not isinstance(ctl.get("visible"), bool):
            errs.append(f"{cc}: Feld visible fehlt oder ist kein Wahrheitswert")
        cid = ctl.get("id")
        if cid in RESERVED or cid == t.get("seed_param"):
            errs.append(f"{cc}: Die ID ist als URL-Parameter reserviert")
        if cid in ids:
            errs.append(f"{cc}: doppelt")
        ids.add(cid)
        typ = ctl.get("type")
        if typ not in CTL_TYPES:
            errs.append(f"{cc}: type muss eines von {', '.join(CTL_TYPES)} sein")
        if "lang" in ctl and (typ != "text" or ctl["lang"] not in ("de", "en")):
            errs.append(f"{cc}: lang gibt es nur bei type text, als de oder en")
        errs += _ctl_value(cc, ctl, ctl.get("default"), D)
    if sum(1 for ctl in t["controls"] if ctl.get("visible")) > 3:
        errs.append(f"{c}: mehr als drei sichtbare Steuerelemente (Rest unter „Mehr Optionen“, visible: false)")
    for ctl in t["controls"]:
        if ctl.get("by") and ctl["by"] not in ids:
            errs.append(f"{c} Steuerelement {ctl['id']}: by verweist auf unbekanntes Steuerelement {ctl['by']}")
    if t.get("preset_control") and t["preset_control"] not in ids:
        errs.append(f"{c}: preset_control {t['preset_control']} ist kein Steuerelement")
    if t.get("seed_control"):
        sc = next((x for x in t["controls"] if x.get("id") == t["seed_control"]), None)
        if sc is None or sc.get("type") != "chips":
            errs.append(f"{c}: seed_control {t['seed_control']} muss ein Chip-Steuerelement der Aufgabe sein")
        elif sc.get("visible"):
            errs.append(f"{c}: seed_control {t['seed_control']} braucht visible: false (der Rahmen zeigt es statt der Startpaletten)")
        if t.get("preset_control"):
            errs.append(f"{c}: seed_control und preset_control schließen sich aus")
    for tg in t.get("pattern_toggles") or []:
        _need(errs, f"{c} pattern_toggles {tg.get('id')}", tg, ("id", "values", "default"))
        if tg.get("default") not in (tg.get("values") or []):
            errs.append(f"{c} pattern_toggles {tg.get('id')}: default steht nicht in values")
    # Presets
    want = PRESET_COUNT.get(tid, 3)
    if len(t["presets"]) != want:
        errs.append(f"{c}: genau {want} Startpaletten nötig, gefunden {len(t['presets'])}")
    pids = set()
    for p in t["presets"]:
        pc = f"{c} Startpalette {p.get('id')}"
        _need(errs, pc, p, ("id", "name_de", "name_en"))
        if "options" not in p or not isinstance(p.get("options"), dict):
            errs.append(f"{pc}: Feld options fehlt (auch leer: {{}})")
        if "expect" not in p or not isinstance(p.get("expect"), list):
            errs.append(f"{pc}: Feld expect fehlt (auch leer: [])")
        if isinstance(p.get("id"), str):
            if not SLUG.fullmatch(p["id"]):
                errs.append(f"{pc}: ungültige ID")
            if p["id"] in pids:
                errs.append(f"{pc}: doppelt")
            pids.add(p["id"])
        if "seed" not in p and "colors" not in p and not p.get("dataset") and not t.get("preset_control"):
            # Ohne eigene Farbe geht es nur, wenn die Startpalette auf einem Datensatz beruht oder ein
            # Steuerelement sie wählt (preset_control); der Generator bekommt dann seed und colors als None.
            errs.append(f"{pc}: seed oder colors fehlt (oder dataset bzw. preset_control der Aufgabe)")
        errs += _colors_parse(pc, p)
        for k, v in (p.get("options") or {}).items():
            ctl = next((x for x in t["controls"] if x.get("id") == k), None)
            if ctl is None:
                errs.append(f"{pc}: Option {k} ist kein Steuerelement")
            else:
                errs += _ctl_value(f"{pc} Option {k}", ctl, v, D)
        for e in p.get("expect") or []:
            if not isinstance(e, str) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*(@(light|dark|default))?", e):
                errs.append(f"{pc}: expect-Eintrag {e!r} hat nicht die Form befund@modus")
        if p.get("dataset") and p["dataset"] not in D["datasets"]:
            errs.append(f"{pc}: Datensatz {p['dataset']} gibt es nicht")
    if t.get("preset_control"):
        pcid = t["preset_control"]
        for p in t["presets"]:
            if pcid not in (p.get("options") or {}):
                errs.append(f"{c} Startpalette {p.get('id')}: options.{pcid} fehlt (preset_control)")
    # Fremdschlüssel (5)
    for r in t["rules"]:
        if r not in D["rules"]:
            missing(f"{c}: Regel {r} gibt es nicht (data/rules/*.json)")
    if not 3 <= len(t["explain"]) <= 6:
        errs.append(f"{c}: 3 bis 6 Erklärt-Einträge nötig, gefunden {len(t['explain'])}")
    for e in t["explain"]:
        if e not in D["explain"]:
            missing(f"{c}: Erklärt-Eintrag {e} gibt es nicht (data/explain/*.json)")
    pat = D["patterns"].get(tid) or {}
    if pat.get("html") is None:
        errs.append(f"{c}: Muster {pat.get('html_path')} fehlt")
    if pat.get("mini") is None:
        errs.append(f"{c}: Mini-Vorschau {pat.get('mini_path')} fehlt")
    ex = t["exports"]
    _need(errs, f"{c} exports", ex, ("primary", "visible"))
    vis = ex.get("visible") or []
    if len(vis) > 3:
        errs.append(f"{c} exports: höchstens drei sichtbare Formate")
    if vis and vis[0] != ex.get("primary"):
        errs.append(f"{c} exports: das Standardformat {ex.get('primary')} muss zuerst unter visible stehen")
    fmts = list(vis) + list(ex.get("more") or [])
    if len(set(fmts)) != len(fmts):
        errs.append(f"{c} exports: Format doppelt")
    for o in ex.get("options") or []:
        if not isinstance(o, dict) or not SLUG.fullmatch(str(o.get("id"))):
            errs.append(f"{c} exports.options: ungültiger Eintrag {o!r}")
    for rid in t["related"]:
        if rid == tid or rid not in D["order"]:
            errs.append(f"{c}: verwandte Aufgabe {rid} gibt es nicht")
    for s in t.get("siblings") or []:
        if s.get("site") not in SIBLING_SITES:
            errs.append(f"{c} siblings: site muss bildsprache oder designsprache sein")
        _need(errs, f"{c} siblings", s, ("path_de", "path_en", "label_key"))
    for d in t.get("datasets") or []:
        if d not in D["datasets"]:
            errs.append(f"{c}: Datensatz {d} gibt es nicht")
    for n in t.get("data_files") or []:
        if n not in ("models", "colornames", "check"):
            errs.append(f"{c}: data_files kennt nur models, colornames und check, nicht {n!r}")
        elif D.get(n) is None:
            errs.append(f"{c}: data_files nennt {n}, aber data/{n}.json fehlt")
    for d in t.get("gen_deps") or []:
        if not SLUG.fullmatch(str(d)):
            errs.append(f"{c}: gen_deps-Eintrag {d!r} ist kein Slug")
    if t.get("menu_paths") is not None and tid != "slides":
        errs.append(f"{c}: menu_paths gibt es nur bei slides")
    for m in t.get("menu_paths") or []:
        _need(errs, f"{c} menu_paths", m, ("app", "text_de", "text_en", "source", "checked"))
    # Texte der Aufgabe
    errs += _task_copy(D, tid, t)
    return errs


def _colors_parse(pc, p):
    from tools import color as C
    errs = []
    if "seed" in p and (not isinstance(p["seed"], str) or C.parse(p["seed"], False) is None):
        errs.append(f"{pc}: seed {p.get('seed')!r} lässt sich nicht lesen (#RRGGBB oder oklch(L C h))")
    for i, col in enumerate(p.get("colors") or []):
        if not isinstance(col, dict) or not isinstance(col.get("value"), str) or C.parse(col["value"], False) is None:
            errs.append(f"{pc}: colors[{i}] lässt sich nicht lesen")
    return errs


def _ctl_value(cc, ctl, v, D):
    from tools import color as C
    typ = ctl.get("type")
    vals = ctl.get("values")
    cases = ctl.get("cases") or {}
    allv = list(vals or [])
    for cs in cases.values():
        allv += list(cs.get("values") or [])
    if typ == "chips":
        if not allv:
            return [f"{cc}: values fehlt"]
        if v not in allv:
            return [f"{cc}: Wert {v!r} steht nicht in values"]
    elif typ == "toggle":
        if not isinstance(v, bool):
            return [f"{cc}: Wert muss true oder false sein"]
    elif typ == "stepper":
        lo, hi = ctl.get("min"), ctl.get("max")
        for cs in cases.values():
            lo = min(lo, cs.get("min", lo)) if lo is not None else cs.get("min")
            hi = max(hi, cs.get("max", hi)) if hi is not None else cs.get("max")
        if not isinstance(v, int) or isinstance(v, bool) or lo is None or hi is None or not lo <= v <= hi:
            return [f"{cc}: Wert {v!r} liegt nicht zwischen min und max"]
    elif typ == "color":
        if v is not None and (not isinstance(v, str) or C.parse(v, False) is None):
            return [f"{cc}: Farbe {v!r} lässt sich nicht lesen"]
    elif typ == "colors":
        if v is not None and (not isinstance(v, list) or any(C.parse(x, False) is None for x in v)):
            return [f"{cc}: Farbliste {v!r} lässt sich nicht lesen"]
    elif typ == "text":
        if v is not None and not isinstance(v, str):
            return [f"{cc}: Text erwartet"]
    return []


def _copy_has(D, page, key, lang):
    return key in D["copy"][lang].get(page, {}) or key in D["copy"][lang].get("frame", {})


def _task_copy(D, tid, t):
    errs = []
    c = f"Aufgabe {tid}"
    for lang in ("de", "en"):
        tc = D["copy"][lang].get(tid)
        if tc is None:
            errs.append(f"{c}: Texte fehlen (web/copy/{tid.replace('-', '_')}.py mit COPY[{lang}][{tid!r}])")
            continue
        for k in ("h1", "lede", "outcome"):
            if k not in tc:
                errs.append(f"{c}: Text {k} fehlt in COPY[{lang}][{tid!r}]")
        need = []
        for ctl in t.get("controls") or []:
            need.append(ctl.get("label_key"))
            if ctl.get("type") == "chips":
                vals = list(ctl.get("values") or [])
                for cs in (ctl.get("cases") or {}).values():
                    vals += cs.get("values") or []
                need += [f"{ctl.get('label_key')}.{v}" for v in vals]
        for tg in t.get("pattern_toggles") or []:
            need.append(f"toggle.{tg.get('id')}")
            need += [f"toggle.{tg.get('id')}.{v}" for v in tg.get("values") or []]
        ex = t.get("exports") or {}
        for f in list(ex.get("visible") or []) + list(ex.get("more") or []):
            need.append(f"fmt.{f}")
        need += [f"opt.{o.get('id')}" for o in ex.get("options") or [] if isinstance(o, dict)]
        need += [f"distinct.{d.get('id')}" for d in t.get("distinct") or []]
        need += [s.get("label_key") for s in t.get("siblings") or []]
        for k in need:
            if k and not _copy_has(D, tid, k, lang):
                errs.append(f"{c}: Text {k} fehlt in COPY[{lang}][{tid!r}] (oder im Rahmen)")
        fmts = list(ex.get("visible") or []) + list(ex.get("more") or [])
        if "agent" in fmts:
            for k in ("agent.title", "agent.idea", "agent.avoid", "agent.checks", "agent.tip"):
                if k not in tc:
                    errs.append(f"{c}: Text {k} fehlt in COPY[{lang}][{tid!r}] (Export agent)")
        if "rationale" in fmts and not isinstance(tc.get("rationale"), list):
            errs.append(f"{c}: Text rationale (Liste von Sätzen) fehlt in COPY[{lang}][{tid!r}] (Export rationale)")
    return errs


def check_rules_explain(D):
    errs = []
    for kind in ("rules", "explain"):
        for i, it in D[kind].items():
            c = f"{'Regel' if kind == 'rules' else 'Kurz erklärt'} {i}"
            if kind == "rules":
                _need(errs, c, it, ("level", "text_de", "text_en", "sources"))
                if "show_if" not in it:
                    errs.append(f"{c}: Feld show_if fehlt (null, wenn immer sichtbar)")
                elif it["show_if"] is not None:
                    errs += _show_if(c, it["show_if"])
            else:
                _need(errs, c, it, ("level", "title_de", "title_en", "body_de", "body_en", "sources"))
                if "demo" not in it:
                    errs.append(f"{c}: Feld demo fehlt (null, wenn ohne Demo)")
                elif it["demo"] is not None and f"patterns/demo-{it['demo']}.html" not in (D.get("extra_patterns") or {}):
                    errs.append(f"{c}: Demo patterns/demo-{it['demo']}.html fehlt (Muster mit Selektoren .demo-{it['demo']})")
                for lang in ("de", "en"):
                    body = it.get("body_" + lang) or ""
                    n = len(re.findall(r"\S+", PH_KNOWN.sub("x", body)))
                    if body and not 60 <= n <= 120:
                        errs.append(f"{c}: body_{lang} hat {n} Wörter, erlaubt sind 60 bis 120")
                    if "<" in body:
                        errs.append(f"{c}: body_{lang} enthält HTML (nur Text, Absätze durch Leerzeile)")
            if "own" not in it or not isinstance(it.get("own"), bool):
                errs.append(f"{c}: Feld own fehlt oder ist kein Wahrheitswert")
            lvl = it.get("level")
            if lvl not in LEVELS:
                errs.append(f"{c}: level muss eines von {', '.join(LEVELS)} sein")
            # 7 · Belegstufen
            if lvl == "norm" and not it.get("normative"):
                errs.append(f"{c}: Norm braucht normative (Quellen-IDs der normativen Grundlage)")
            if lvl == "research" and it.get("strength") not in STRENGTHS:
                errs.append(f"{c}: Forschung braucht strength strong oder partial")
            if lvl != "research" and it.get("strength") not in (None,):
                errs.append(f"{c}: strength gibt es nur bei research")
            if it.get("myth") and lvl != "unproven":
                errs.append(f"{c}: myth gibt es nur bei unproven")
            if kind == "rules" and it.get("own") and lvl != "convention":
                errs.append(f"{c}: own: true (Festlegung von Farbsprache) trägt die Stufe convention; mischt die Regel Beleg "
                            f"und Festlegung, teile sie")
            if kind == "rules" and not it.get("own") and "Festlegung" in str(it.get("text_de", "")):
                errs.append(f"{c}: Der Text nennt eine Festlegung, die Regel hat aber own: false (teile Beleg und Festlegung)")
            if not it.get("sources"):
                errs.append(f"{c}: mindestens eine Quelle nötig")
            # 5 · Fremdschlüssel zu Quellen mit passendem normative-Flag
            for s in it.get("sources") or []:
                if s not in D["sources"]:
                    errs.append(f"{c}: Quelle {s} gibt es nicht (data/sources/*.json)")
            for s in it.get("normative") or []:
                if s not in D["sources"]:
                    errs.append(f"{c}: normative Quelle {s} gibt es nicht")
                elif D["sources"][s].get("normative") is not True:
                    errs.append(f"{c}: {s} steht unter normative, die Quelle ist aber nicht normativ")
                if s not in (it.get("sources") or []):
                    errs.append(f"{c}: {s} steht unter normative, aber nicht unter sources")
            for s in it.get("informative") or []:
                if s not in D["sources"]:
                    errs.append(f"{c}: informative Quelle {s} gibt es nicht")
                elif D["sources"][s].get("normative") is not False:
                    errs.append(f"{c}: {s} steht unter informative, die Quelle ist aber normativ")
                if s not in (it.get("sources") or []):
                    errs.append(f"{c}: {s} steht unter informative, aber nicht unter sources")
    return errs


def _show_if(c, s):
    errs = []
    if not isinstance(s, dict):
        return [f"{c}: show_if muss ein Objekt oder null sein"]
    m = s.get("metric")
    if m not in ("cr", "dist", "gs", "count", "finding"):
        errs.append(f"{c}: show_if.metric muss cr, dist, gs, count oder finding sein")
    if m in ("cr", "dist", "gs", "count"):
        if s.get("op") not in ("<", ">="):
            errs.append(f"{c}: show_if.op muss < oder >= sein")
        if not _is_num(s.get("value")):
            errs.append(f"{c}: show_if.value muss eine Zahl sein")
    if m in ("cr", "dist", "gs") and not (s.get("a") and s.get("b")):
        errs.append(f"{c}: show_if braucht a und b")
    if m == "finding" and not s.get("a"):
        errs.append(f"{c}: show_if mit finding braucht a (Befund-ID)")
    if s.get("mode") not in (None, "light", "dark", "default"):
        errs.append(f"{c}: show_if.mode muss light, dark, default oder null sein")
    return errs


def check_explain_order(D, allow_missing, warn):
    errs = []
    eo = D["explain_order"]
    if len(set(eo)) != len(eo):
        errs.append("data/explain/_order.json: doppelte IDs")
    for i in eo:
        if i not in D["explain"]:
            msg = f"Kurz erklärt {i}: steht in data/explain/_order.json, der Eintrag fehlt"
            (warn if allow_missing else errs.append)(msg)
    for i in D["explain"]:
        if i not in eo:
            errs.append(f"Kurz erklärt {i}: fehlt in data/explain/_order.json (Reihenfolge ergänzen)")
    return errs


def check_orphans(D, allow_missing, warn):
    """6 · Jede Regel und jeder Erklärt-Eintrag braucht eine Aufgabe oder data/check.json."""
    errs = []
    used_r = {r for t in D["tasks"].values() for r in t.get("rules") or []}
    used_r |= {p.get("rule") for t in D["tasks"].values() for p in t.get("pairs") or []}
    used_e = {e for t in D["tasks"].values() for e in t.get("explain") or []}
    check_strings = {v for _, _, v in _walk(D.get("check") or {}) if isinstance(v, str)}
    for i in D["rules"]:
        if i not in used_r and i not in check_strings:
            msg = f"Regel {i}: von keiner Aufgabe verwendet (Aufgabe ergänzen oder Regel streichen)"
            (warn if allow_missing else errs.append)(msg)
    for i in D["explain"]:
        if i not in used_e and i not in check_strings:
            msg = f"Kurz erklärt {i}: von keiner Aufgabe verwendet (Aufgabe ergänzen oder Eintrag streichen)"
            (warn if allow_missing else errs.append)(msg)
    return errs


def check_sources(D):
    """8 · Quellen: https, ISO-Datum, kind, access."""
    errs = []
    for i, s in D["sources"].items():
        c = f"Quelle {i}"
        _need(errs, c, s, ("title", "url", "retrieved", "kind", "access", "claim_de", "claim_en"))
        if "normative" not in s or not isinstance(s.get("normative"), bool):
            errs.append(f"{c}: Feld normative fehlt oder ist kein Wahrheitswert")
        if not str(s.get("url", "")).startswith("https://"):
            errs.append(f"{c}: url muss mit https:// beginnen")
        if not ISO.fullmatch(str(s.get("retrieved", ""))):
            errs.append(f"{c}: retrieved muss ein ISO-Datum JJJJ-MM-TT sein")
        if s.get("kind") not in SRC_KINDS:
            errs.append(f"{c}: kind muss eines von {', '.join(SRC_KINDS)} sein")
        if s.get("access") not in ACCESS:
            errs.append(f"{c}: access muss fulltext, abstract oder snippet sein")
        for k in ("authors", "publisher", "date", "unverified_de", "unverified_en"):
            if k not in s:
                errs.append(f"{c}: Feld {k} fehlt (null, wenn unbekannt)")
        # Sprache des Titels (lang auf der Quellenseite): en, de, en/de für „English / Deutsch“, null für Dateinamen
        if "title_lang" not in s or s.get("title_lang") not in TITLE_LANGS:
            errs.append(f"{c}: Feld title_lang fehlt oder ist nicht en, de, en/de, de/en oder null")
        elif ("/" in (s.get("title_lang") or "")) != (str(s.get("title", "")).count(" / ") == 1):
            errs.append(f"{c}: zweisprachiger Titel „A / B“ braucht title_lang en/de oder de/en, einsprachiger keins mit /")
        for k in ("claim_de", "claim_en", "unverified_de", "unverified_en"):
            v = s.get(k) or ""
            marks = [(m.group(1), m.group(2)) for m in LANG_MARK.finditer(v)]
            ok = len(marks) % 2 == 0 and all(marks[i] == ("", marks[i + 1][1]) and marks[i + 1][0] == "/"
                                              for i in range(0, len(marks), 2))
            if not ok:
                errs.append(f"{c}: {k} hat unvollständige Sprachmarken (je [en]…[/en] bzw. [de]…[/de])")
            if any(m[1] == k[-2:] for m in marks):
                errs.append(f"{c}: {k} markiert die eigene Sprache (Marken nur für fremde Zitate)")
        # Sprache einer unübersetzten Kurzangabe (etwa „Understanding 1.4.3“ auch auf der deutschen Seite)
        if "short_lang" in s and (s["short_lang"] not in ("de", "en") or s.get("short_de") != s.get("short_en")):
            errs.append(f"{c}: short_lang (de oder en) gibt es nur, wenn short_de und short_en gleich sind")
    return errs


def check_datasets(D):
    """13 · Datensätze: Lizenz, Herkunft, Prüfsumme, Belastbarkeit; Hex gleich origin.rgb."""
    errs = []
    for i, ds in D["datasets"].items():
        c = f"Datensatz {i}"
        if not isinstance(ds, dict):
            errs.append(f"{c}: erwartet ein Objekt")
            continue
        if ds.get("id") != i:
            errs.append(f"{c}: Feld id passt nicht zum Dateinamen")
        _need(errs, c, ds, ("license", "attribution", "source_url", "machine_source", "machine_sha256", "retrieved",
                            "reliability", "kind", "schemes"))
        for k in ("source_url", "machine_source"):
            if ds.get(k) and not str(ds[k]).startswith("https://"):
                errs.append(f"{c}: {k} muss mit https:// beginnen")
        if ds.get("machine_sha256") and not re.fullmatch(r"[0-9a-f]{64}", str(ds["machine_sha256"])):
            errs.append(f"{c}: machine_sha256 ist keine SHA-256-Prüfsumme")
        if ds.get("retrieved") and not ISO.fullmatch(str(ds["retrieved"])):
            errs.append(f"{c}: retrieved muss ein ISO-Datum sein")
        if ds.get("reliability") not in RELIABILITY:
            errs.append(f"{c}: reliability muss eines von {', '.join(RELIABILITY)} sein")
        if ds.get("kind") not in DS_KINDS:
            errs.append(f"{c}: kind muss eines von {', '.join(DS_KINDS)} sein")
        if "required_notice" not in ds:
            errs.append(f"{c}: Feld required_notice fehlt (null, wenn keine Pflicht)")
        if i == "colorbrewer" and ds.get("required_notice") != COLORBREWER_NOTICE:
            errs.append(f"{c}: required_notice muss wörtlich der ColorBrewer-Pflichtsatz sein")
        for path, k, v in _walk(ds.get("schemes") or []):
            if k == "hex" and isinstance(v, str) and not re.fullmatch(r"#[0-9A-F]{6}", v):
                errs.append(f"{c} {path}: hex {v!r} ist nicht #RRGGBB in Großbuchstaben")
        for sch in ds.get("schemes") or []:
            for col in sch.get("colors") or []:
                o = (col.get("origin") or {}).get("rgb")
                if isinstance(o, list) and len(o) == 3 and isinstance(col.get("hex"), str):
                    if col["hex"].upper() != "#%02X%02X%02X" % tuple(o):
                        errs.append(f"{c} {sch.get('id')}: {col.get('name')} hex {col['hex']} passt nicht zu origin.rgb {o}")
    return errs


def check_comparisons(D):
    errs = []
    comp = D.get("comparisons") or {}
    ids = set()
    for cmp in comp.get("comparisons") or []:
        c = f"Vergleichswert {cmp.get('id')}"
        _need(errs, c, cmp, ("id", "name_de", "name_en", "colors", "kinds"))
        if cmp.get("id") in ids:
            errs.append(f"{c}: doppelt")
        ids.add(cmp.get("id"))
        col = cmp.get("colors") or {}
        if "dataset" in col and col["dataset"] not in D["datasets"]:
            errs.append(f"{c}: Datensatz {col['dataset']} gibt es nicht")
        for k in cmp.get("kinds") or []:
            if k not in CVD_KINDS:
                errs.append(f"{c}: unbekannte Sichtweise {k}")
    return errs


# ---- 2, 3 · Sprachpaare und IDs

def check_pairs_and_ids(D):
    errs = []

    def pairs(label, obj):
        for path, k, v in _walk(obj):
            if k.endswith("_de"):
                en = k[:-3] + "_en"
                parent = _get(obj, path)
                if isinstance(parent, dict) and en not in parent:
                    errs.append(f"{label} {path}: {k} ohne {en}")
                elif isinstance(parent, dict) and isinstance(v, list) and isinstance(parent.get(en), list) and len(v) != len(parent[en]):
                    errs.append(f"{label} {path}: {k} und {en} sind unterschiedlich lang")
            if k.endswith("_en"):
                de = k[:-3] + "_de"
                parent = _get(obj, path)
                if isinstance(parent, dict) and de not in parent:
                    errs.append(f"{label} {path}: {k} ohne {de}")
    for tid, t in D["tasks"].items():
        pairs(f"Aufgabe {tid}", t)
    for kind in ("rules", "explain", "sources"):
        for i, it in D[kind].items():
            pairs(f"{kind} {i}", it)
    for i, ds in D["datasets"].items():
        pairs(f"Datensatz {i}", ds)
    for name in ("comparisons", "models", "colornames", "check"):
        if D.get(name) is not None:
            pairs(f"data/{name}.json", D[name])
    # COPY: gleiche Seiten und Schlüssel in de und en, Listen gleich lang
    for page in set(D["copy"]["de"]) | set(D["copy"]["en"]):
        de, en = D["copy"]["de"].get(page), D["copy"]["en"].get(page)
        src = D["copy_src"].get(page, "web/copy")
        if de is None or en is None:
            errs.append(f"{src}: Seite {page} fehlt in {'de' if de is None else 'en'}")
            continue
        for k in set(de) ^ set(en):
            errs.append(f"{src}: Schlüssel {page}.{k} nur in {'de' if k in de else 'en'}")
        for k in set(de) & set(en):
            if isinstance(de[k], list) and isinstance(en[k], list) and len(de[k]) != len(en[k]):
                errs.append(f"{src}: {page}.{k} hat in de und en unterschiedlich viele Einträge")
    for k in set(D["js_text"]["de"]) ^ set(D["js_text"]["en"]):
        errs.append(f"JS_TEXT: Schlüssel {k} nur in einer Sprache")
    # Slugs und Eindeutigkeit je Art
    for kind in ("rules", "explain", "sources"):
        for i in D[kind]:
            if not SLUG.fullmatch(i):
                errs.append(f"{kind} {i}: ungültige ID (Slug a-z, 0-9, Bindestrich)")
    for i in D["tasks"]:
        if not SLUG.fullmatch(i):
            errs.append(f"Aufgabe {i}: ungültige ID")
    for i in D["datasets"]:
        if not SLUG.fullmatch(i):
            errs.append(f"Datensatz {i}: ungültige ID")
    return errs


def _get(obj, path):
    if not path:
        return obj
    cur = obj
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            cur = cur[int(part[1:-1])]
        else:
            cur = cur[part]
    return cur


# ---- 4 · SEG und PAGE_TWIN

def check_seg(seg, twin, langs=("de", "en")):
    errs = []
    owner = {}
    for key, v in seg.items():
        for lang in langs:
            val = v[lang]
            if val in owner and owner[val] != key:
                errs.append(f"SEG: Wert {val} kommt bei {owner[val]} und {key} vor (eindeutig machen)")
            owner.setdefault(val, key)
    for key, v in seg.items():
        for lang in langs:
            o = "en" if lang == "de" else "de"
            page = f"{lang}/{v[lang]}/"
            back = twin(o, twin(lang, page))
            if back != page:
                errs.append(f"PAGE_TWIN: {page} führt über {twin(lang, page)} zu {back}")
    for lang in langs:
        o = "en" if lang == "de" else "de"
        if twin(o, twin(lang, f"{lang}/")) != f"{lang}/":
            errs.append(f"PAGE_TWIN: Startseite {lang} kein Rundlauf")
    return errs


# ---- 9 · verbotene Ergebnisfelder

def check_forbidden(D):
    errs = []

    def scan(label, obj):
        for path, k, v in _walk(obj):
            if k.lower() in FORBIDDEN:
                errs.append(f"{label} {path}: Schlüssel {k} ist in data/ verboten (Daten enthalten keine Messergebnisse)")
    for tid, t in D["tasks"].items():
        scan(f"Aufgabe {tid}", t)
    for kind in ("rules", "explain", "sources"):
        for i, it in D[kind].items():
            scan(f"{kind} {i}", it)
    for i, ds in D["datasets"].items():
        scan(f"Datensatz {i}", ds)
    for name in ("comparisons", "models", "colornames", "check"):
        if D.get(name) is not None:
            scan(f"data/{name}.json", D[name])
    for name in NO_TEXT_FILES:
        f = name.removesuffix(".json")
        if D["files"].get(f) is not None:
            scan(f"data/{name}", D["files"][f])
    return errs


# ---- 10, 11 · Handzahlen und Ton

def check_text(D, warn):
    errs = []
    for ctx, lang, s, art in texts(D):
        bare = _strip(s)
        if art not in ("claim", "quote"):
            for m in RATIO_RE.finditer(bare):
                if re.sub(r"\s", "", m.group(0)) not in ALLOWED_RATIOS:
                    errs.append(f"{ctx}: Kontrastzahl „{m.group(0)}“ von Hand (Platzhalter {{cr:A/B}} nutzen, erlaubt sind nur Schwellen)")
            m = NUMWORD_RE.search(bare)
            if m:
                errs.append(f"{ctx}: Zahl hinter „{m.group(1)}“ von Hand: „{m.group(0)}“ (Platzhalter nutzen)")
        if art == "quote":
            continue
        if "!" in bare:
            errs.append(f"{ctx}: Ausrufezeichen im Nutzertext")
        if "—" in s:
            errs.append(f"{ctx}: Geviertstrich (U+2014) im Text (Doppelpunkt oder neuer Satz)")
        if lang == "de" and re.search(r"\d %", s):
            errs.append(f"{ctx}: Prozent mit normalem Leerzeichen (im Deutschen schmales geschütztes Leerzeichen U+202F: „8\u202f%“)")
        if lang == "en" and "„" in s:
            errs.append(f"{ctx}: deutsche Anführungszeichen im englischen Text (“…”, deutsche Wörter in [de]…[/de] bzw. <span lang=\"de\">)")
        if lang == "de" and "”" in s:
            errs.append(f"{ctx}: englisches Schlusszeichen ” im deutschen Text (deutsche Anführungszeichen „…“)")
        if LANG_MARK.search(s) and not (ctx.startswith("sources ") and re.search(r" (claim|unverified)_(de|en)$", ctx)):
            errs.append(f"{ctx}: Sprachmarke [en]/[de] gibt es nur in claim_* und unverified_* von Quellen")
        if lang == "de":
            m = SIE.search(" " + bare)
            if m:
                errs.append(f"{ctx}: Anrede „{m.group(1)}“ (du-Form nutzen)")
            if art != "claim":
                for w in dict.fromkeys(m.group(1) or m.group(2) for m in SHORT_IMP_RE.finditer(bare)):
                    warn(f"{ctx}: Kurzimperativ „{w}“ (lange Form: Wähle, Kopiere, Prüfe, Füge, Setze, Speichere, Frage)")
        else:
            low = bare.lower()
            for w in BRITISH:
                if w in low and art != "claim":
                    errs.append(f"{ctx}: britische Schreibweise „{w}“ (amerikanisch: color, gray, center, catalog, license, favor)")
        low = bare.lower()
        if "sicher für farbenblinde" in low:
            errs.append(f"{ctx}: „sicher für Farbenblinde“ ist ein unhaltbares Versprechen")
        for w in HYPE:
            if re.search(r"(?<![a-zäöüß])" + re.escape(w) + r"(?![a-zäöüß])", low) and art != "claim":
                warn(f"{ctx}: Hype-Wort „{w}“")
        for m in PH_ANY.finditer(s):
            if m.group(1) == "href":
                continue  # {href:<seite>} setzt der Rahmen in crossref ein
            if m.group(1) not in ARITY:
                warn(f"{ctx}: unbekannter Platzhalter {m.group(0)} (bleibt wörtlich stehen)")
        for m in PH_KNOWN.finditer(s):
            name, arg = m.group(1), m.group(2)
            if name == "date":
                continue
            if arg is None:
                errs.append(f"{ctx}: Platzhalter {m.group(0)} ohne Argumente")
                continue
            a = arg.rsplit("@", 1)[0] if "@" in arg else arg
            if len(a.split("/")) != ARITY[name]:
                errs.append(f"{ctx}: Platzhalter {m.group(0)} braucht {ARITY[name]} Argumente")
            if name == "ref":
                ids = {c.get("id") for c in (D.get("comparisons") or {}).get("comparisons") or []}
                if a not in ids:
                    errs.append(f"{ctx}: Vergleichswert {a} gibt es nicht (data/comparisons.json)")
            for part in a.split("/")[:2]:
                if part.startswith("#") and not HEX6.fullmatch(part):
                    errs.append(f"{ctx}: {part} in {m.group(0)} ist kein #RRGGBB")
    return errs


# ---- 12 · Rechte

def check_rights(D):
    errs = []
    terms = [(t, re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I)) for t in D["blocklist"]]

    def hit(s):
        for t, rx in terms:
            if rx.search(s):
                return t
        return None
    names = []
    for tid, t in D["tasks"].items():
        names.append((f"Aufgabe {tid}: ID", tid))
        for p in t.get("presets") or []:
            names.append((f"Aufgabe {tid} Startpalette {p.get('id')}: ID", str(p.get("id"))))
            for lang in ("de", "en"):
                names.append((f"Aufgabe {tid} Startpalette {p.get('id')}: name_{lang}", str(p.get("name_" + lang, ""))))
    for kind in ("rules", "explain", "sources"):
        for i in D[kind]:
            names.append((f"{kind} {i}: ID", i))
    for i, ds in D["datasets"].items():
        names.append((f"Datensatz {i}: name", str(ds.get("name", ""))))
        for sch in ds.get("schemes") or []:
            names.append((f"Datensatz {i}: Schema-ID", str(sch.get("id", ""))))
            for col in sch.get("colors") or []:
                names.append((f"Datensatz {i} {sch.get('id')}: Farbname", str(col.get("name", ""))))
    cn = D.get("colornames") or {}
    for w in cn.get("allowed_words") or []:
        names.append(("data/colornames.json allowed_words", str(w)))
    for ctx, s in names:
        t = hit(s)
        if t:
            errs.append(f"{ctx} „{s}“ enthält das Sperrwort „{t}“ (tools/blocklist.txt)")
    for ctx, lang, s, art in texts(D):
        if art == "quote":
            continue
        for sent in re.split(r"(?<=[.!?])\s+", TAG.sub(" ", s)):
            t = hit(sent)
            if t and (HEX_ANY.search(sent) or "{hex:" in sent):
                errs.append(f"{ctx}: Sperrwort „{t}“ und ein Hex-Wert im selben Satz (keine Umrechnung von Normfarbsystemen)")
    return errs


# ---- 14 · Bildmodelle

def check_models(D, date, warn):
    errs = []
    m = D.get("models")
    if not m:
        return errs
    try:
        today = datetime.date.fromisoformat(date) if date else datetime.date.today()
    except ValueError:
        today = datetime.date.today()
    for mod in m.get("models") or []:
        c = f"Bildmodell {mod.get('id')}"
        ch = mod.get("checked")
        if not isinstance(ch, str) or not ISO.fullmatch(ch):
            errs.append(f"{c}: checked muss ein ISO-Datum sein")
            continue
        age = (today - datetime.date.fromisoformat(ch)).days
        if age > 183:
            warn(f"{c}: Stand {ch} ist {age} Tage alt (Doku prüfen, checked aktualisieren)")
    return errs


# ---- 15 · Muster

def _css_blocks(css):
    """(prelude, body) aller Regeln, @media/@supports aufgelöst."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if prelude.startswith(("@media", "@supports", "@container")):
            out += _css_blocks(body)
        else:
            out.append((prelude, body))
        i = k
    return out


def _decls(body):
    for d in body.split(";"):
        if ":" in d:
            p, v = d.split(":", 1)
            yield p.strip().lower(), v.strip()


def check_patterns(D):
    errs = []
    css_names = D["files"].get("css-names") or {}
    names = {k for k in css_names if not k.startswith("_")}
    named_rx = re.compile(r"(?<![a-z0-9-])(" + "|".join(sorted(names, key=len, reverse=True)) + r")(?![a-z0-9-])", re.I) if names else None
    lit_rx = re.compile(r"(#[0-9A-Fa-f]{3,8}\b|\b(rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|hwb|color)\()", re.I)

    def color_value(where, prop, val):
        """Farben nur über var(--d-<rolle>): kein Literal in irgendeiner Deklaration (auch nicht in eigenen
        Variablen), kein Farbname in Farbeigenschaften und Variablen, keine fremde Variable in Farbeigenschaften."""
        e = []
        colorish = bool(COLOR_PROPS.match(prop)) or prop.startswith("--")
        v = re.sub(r"var\(\s*--d-[a-z0-9-]+\s*(,[^)]*)?\)", "", val)
        if lit_rx.search(v):
            e.append(f"{where}: Farbliteral in {prop}: {val} (nur var(--d-<rolle>))")
        elif colorish and named_rx and named_rx.search(re.sub(r"\b(transparent|currentcolor|none|inherit|initial|unset)\b", "", v, flags=re.I)):
            e.append(f"{where}: Farbname in {prop}: {val} (nur var(--d-<rolle>))")
        if colorish and re.search(r"var\(\s*--(?!d-)", v):
            e.append(f"{where}: {prop} nutzt eine Variable außerhalb von --d-*: {val}")
        return e
    items = []
    for tid, pat in D["patterns"].items():
        for kind in ("html", "mini"):
            if pat.get(kind) is not None:
                items.append((tid, kind, pat[kind], pat[kind + "_path"], tid))
    for rel, src in (D.get("extra_patterns") or {}).items():
        stem = pathlib.Path(rel).stem
        items.append((stem[5:] if stem.startswith("demo-") else stem, "html", src, rel, None))
    for tid, kind, src, where, page in items:
        low = src.lower()
        if "<script" in low:
            errs.append(f"{where}: <script> ist in Mustern verboten")
        for tag in ("<link", "<iframe", "<img", "<object", "<embed", "<video", "<audio", "<form", "<base", "<meta"):
            if tag in low:
                errs.append(f"{where}: {tag}> ist in Mustern verboten")
        if re.search(r"\son[a-z]+\s*=", low):
            errs.append(f"{where}: on*-Attribute sind verboten")
        if "url(" in low:
            errs.append(f"{where}: url( ist verboten")
        if "@import" in low or "@font-face" in low:
            errs.append(f"{where}: @import und @font-face sind verboten")
        for m in re.finditer(r"\s(src|href|xlink:href|action|srcset)\s*=\s*[\"']([^\"']*)", src, re.I):
            if not (m.group(1).lower() in ("href", "xlink:href") and m.group(2).startswith("#")):
                errs.append(f"{where}: {m.group(1)}=\"{m.group(2)}\" verweist nach außen (nur href=\"#…\")")
        if re.search(r"\sid\s*=", src, re.I):
            errs.append(f"{where}: id-Attribute sind verboten (das Muster steht mehrfach auf der Seite)")
        for m in re.finditer(r"\s(fill|stroke|color|bgcolor|stop-color)\s*=\s*[\"']([^\"']*)", src, re.I):
            v = m.group(2).strip().lower()
            if v not in ("none", "currentcolor", "transparent", "inherit") and not re.fullmatch(r"var\(--d-[a-z0-9-]+\)", v):
                errs.append(f"{where}: Attribut {m.group(1)}=\"{m.group(2)}\" ist eine feste Farbe (style=\"fill:var(--d-…)\" nutzen)")
        for m in re.finditer(r"\sstyle\s*=\s*\"([^\"]*)\"", src, re.I):
            for p, v in _decls(m.group(1)):
                errs += color_value(where, p, v)
        styles = re.findall(r"<style[^>]*>(.*?)</style>", src, re.S | re.I)
        if kind == "mini" and styles:
            errs.append(f"{where}: <style> ist in der Mini-Vorschau verboten (style-Attribute nutzen)")
        for css in styles:
            for prelude, body in _css_blocks(css):
                if prelude.startswith("@keyframes"):
                    if not prelude.split(None, 1)[-1].startswith(f"demo-{tid}"):
                        errs.append(f"{where}: @keyframes ohne Präfix demo-{tid}")
                    continue
                if prelude.startswith("@"):
                    errs.append(f"{where}: {prelude.split()[0]} ist in Mustern nicht erlaubt")
                    continue
                for sel in prelude.split(","):
                    if not re.match(rf"\.demo-{re.escape(tid)}(?![A-Za-z0-9_-])", sel.strip()):
                        errs.append(f"{where}: Selektor „{sel.strip()}“ beginnt nicht mit .demo-{tid}")
                for p, v in _decls(body):
                    errs += color_value(where, p, v)
        for m in re.finditer(r"\{\{([a-z0-9_.-]+)\}\}", src if page else ""):
            for lang in ("de", "en"):
                if "pattern." + m.group(1) not in D["copy"][lang].get(page, {}):
                    errs.append(f"{where}: Text {{{{{m.group(1)}}}}} fehlt als pattern.{m.group(1)} in COPY[{lang}][{tid!r}]")
    return errs


# ---- 17 · README-Vorlagen

def check_readme(D):
    errs = []
    for lang, text in D["readme"].items():
        if text is None:
            errs.append(f"web/readme.{lang}.md: Datei fehlt")
            continue
        for m in re.finditer(r"__N_[A-Z_]+__", text):
            if m.group(0) not in README_KEYS:
                errs.append(f"web/readme.{lang}.md: unbekannter Platzhalter {m.group(0)}")
    return errs


# ---- Sammeln

def run(D, seg=None, twin=None, allow_missing=False, date=None, warnings=None):
    """Alle generischen Prüfungen und die eigenen Prüfungen (tools/checks_*.py) auf einem geladenen Datenbündel."""
    warns = warnings if warnings is not None else []
    warn = warns.append
    errs = []
    steps = [
        ("check_tasks", lambda: check_tasks(D, allow_missing, warn)),
        ("check_rules_explain", lambda: check_rules_explain(D)),
        ("check_explain_order", lambda: check_explain_order(D, allow_missing, warn)),
        ("check_orphans", lambda: check_orphans(D, allow_missing, warn)),
        ("check_sources", lambda: check_sources(D)),
        ("check_datasets", lambda: check_datasets(D)),
        ("check_comparisons", lambda: check_comparisons(D)),
        ("check_pairs_and_ids", lambda: check_pairs_and_ids(D)),
        ("check_forbidden", lambda: check_forbidden(D)),
        ("check_text", lambda: check_text(D, warn)),
        ("check_rights", lambda: check_rights(D)),
        ("check_models", lambda: check_models(D, date, warn)),
        ("check_patterns", lambda: check_patterns(D)),
        ("check_readme", lambda: check_readme(D)),
    ]
    if seg is not None and twin is not None:
        steps.append(("check_seg", lambda: check_seg(seg, twin)))
    for name, step in steps:
        try:
            errs += step()
        except Exception as e:  # noqa: BLE001  (eine Prüfung, die abstürzt, ist selbst ein Befund)
            errs.append(f"Prüfung {name} abgebrochen: {type(e).__name__}: {e}")
    for label, mod in D["pkg_checks"]:
        try:
            errs += list(mod.check(D, warn))
        except Exception as e:  # noqa: BLE001
            errs.append(f"{label}: check() abgebrochen ({type(e).__name__}: {e})")
    return errs


def check_all(root, extra_roots=(), allow_missing=False, date=None, warnings=None, seg=None, twin=None):
    """Lädt alle Daten unter root (plus Überlagerungen) und prüft sie → Liste der Fehlermeldungen."""
    roots = [pathlib.Path(root)] + [pathlib.Path(r) for r in extra_roots]
    D, errs = load_all(roots)
    if seg is None or twin is None:
        import build  # noqa: PLC0415  (SEG und PAGE_TWIN gehören build.py)
        seg, twin = build.SEG, build.PAGE_TWIN
    return errs + run(D, seg, twin, allow_missing, date, warnings)
