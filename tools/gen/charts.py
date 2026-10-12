"""Generator der Aufgabe Diagramm oder Dashboard (Spezifikation 3.3, 4.4). Spiegel von web/gen/charts.js.

Vertrag nach 7.4: build(task, inp, ctx) -> Palettenobjekt (6.14); der Rahmen setzt task, preset, input, name_de,
name_en. Ein Modus („default“), der Hintergrund kommt aus der Option bg. Datentypen t: cat (Gruppen), seq
(Verlauf), div (Abweichung), hl (eine Linie hervorheben). Familien nur innerhalb einer Familie, nie gemischt.
Die eigene Farbe wird Serie 1 (cat) bzw. die Hervorhebung (hl), bei Linien vorher per solve_l auf 3:1 gebracht;
fiele die Hervorhebung dabei praktisch mit dem Kontextgrau zusammen, bleibt Okabe-Blau (Änderungshinweis);
bei seq und div bestimmt sie den Farbton der Familie „seed“. Festlegungen dieser Datei (Konvention, eigen):
Verläufe stehen so, dass „mehr“ sich stärker vom Hintergrund abhebt (auf Weiß dunkler, auf Dunkel heller);
bei Abweichungen steht die kühle Seite zuerst (Stufe 1 = weit darunter).
Zusätzlich view_vars (Anzeige des Musters), exports["js"] (JS-Array, 5.8) und die generischen Exporte mit dem
Zweck „nur Flächen mit Kontur“ für Serien unter 3:1.
"""
import math

from tools import color as C, export as X

BG = {"light": "#FFFFFF", "dark": "#16191D"}
TEXT = {"light": "#222222", "dark": "#E8E8E8"}
GRID_L = {"light": 0.90, "dark": 0.30}
AXIS_L0 = {"light": 0.45, "dark": 0.75}
CONTEXT_L0 = {"light": 0.70, "dark": 0.45}
DIRECTION = {"light": -1, "dark": 1}
OKABE_BLUE = "#0072B2"
MODE = "default"
DEFAULT_FAM = {"cat": "okabe-ito", "seq": "viridis", "div": "blue-orange", "hl": "gray"}
CAT_FAM = {"okabe-ito": ("okabe-ito", "okabe-ito", ("black",)), "tol-bright": ("tol", "bright", ()),
           "tol-muted": ("tol", "muted", ())}
CB_FAM = {"cb-blues": "blues", "cb-rdbu": "rdbu", "cb-puor": "puor"}
DIV_HUES = (255.0, 50.0)      # blue-orange: kühle und warme Seite (4.4)
# Feste Daten der Kachelkarte 7 × 5 (Muster), Werte 0 bis 99, für jede Palette gleich
TILE = [44, 62, 64, 57, 62, 83, 99, 44, 52, 45, 45, 62, 82, 86, 37, 33, 29, 41, 63, 73, 67,
        22, 15, 21, 42, 58, 56, 50, 2, 3, 21, 41, 44, 37, 40]


# ---- Hilfen

def _usage(hx, bg):
    r = C.contrast(hx, bg)
    return "text" if r >= 4.5 else "lines" if r >= 3.0 else "area"


def _red(h):
    return h is not None and (0 <= h <= 45 or h >= 345)


def _green(h):
    return h is not None and 120 <= h <= 160


def red_green(h_a, h_b):
    """Rot-Grün-Ablehnung für div mit eigener Farbe (4.4): Liegt ein Ende im Rotbereich (0–45° oder ab 345°)
    und das andere im Grünbereich (120–160°), wird die Gegenseite h_b durch 255° ersetzt → (h_b, ersetzt)."""
    if (_red(h_a) and _green(h_b)) or (_green(h_a) and _red(h_b)):
        return 255.0, True
    return h_b, False


def to_contrast(seed, bg, bgk, target=3.0):
    """Eigene Farbe auf target gegen bg bringen (solve_l, Farbton und Chroma bleiben, nur L wandert).
    Auf Dunkel startet die Suche oberhalb der Hintergrundhelligkeit, damit keine Seite gemischt ist."""
    if C.contrast(seed, bg) >= target and (bgk == "light" or C.rel_lum(seed) > C.rel_lum(bg)):
        return seed
    L, Cs, h = C.hex_to_oklch(seed)
    hue = h if h is not None else 0.0
    L0 = L
    if bgk == "dark":
        yb = C.rel_lum(bg)
        L0 = max(L, C.hex_to_oklch(bg)[0])
        steps = 0
        while C.rel_lum(C.oklch_to_hex(L0, Cs, hue)) <= yb and steps < 20:
            L0 = min(1.0, L0 + 0.05)
            steps += 1
    return C.solve_l(Cs, hue, [bg], target, DIRECTION[bgk], L0)["hex"]


def _adjacent(colors, kinds):
    """Kleinster Abstand benachbarter Farben → {value, i, kind} (Gleichstand: frühere, wie min_distance)."""
    best = None
    for i in range(len(colors) - 1):
        for k in kinds:
            d = C.distance(colors[i], colors[i + 1], k)
            if best is None or d < best["value"] - 1e-12:
                best = {"value": d, "i": i, "kind": k}
    return best


def _monotone(steps, kind):
    """OKLab-L der quantisierten Stufen: seq streng monoton, div von der Mitte zu beiden Enden streng fallend."""
    ls = [C.hex_to_oklch(s)[0] for s in steps]
    if kind == "seq":
        up = all(ls[i] < ls[i + 1] for i in range(len(ls) - 1))
        down = all(ls[i] > ls[i + 1] for i in range(len(ls) - 1))
        return up or down
    m = len(ls) // 2
    return all(ls[i] < ls[i + 1] for i in range(m)) and all(ls[i] > ls[i + 1] for i in range(m, len(ls) - 1))


def _scheme(ds, sid):
    return next(s for s in ds["schemes"] if s["id"] == sid)


# ---- Datentypen

def _cat(o, seed, bg, bgk, kinds, ctx, changes, summary):
    ds_id, sid, drop = CAT_FAM[o["fam"]]
    fam = [c["hex"] for c in _scheme(ctx["datasets"][ds_id], sid)["colors"] if c.get("name") not in drop]
    lines = o["mark"] == "lines"
    pool = [c for c in fam if C.contrast(c, bg) >= 3.0] if lines else list(fam)
    start = None
    if seed:
        start = seed
        if lines:
            start = to_contrast(seed, bg, bgk)
            if start != seed:
                changes.append({"role": "series-1", "mode": MODE, "from": seed, "to": start, "key": "series-1",
                                "values": {"before": C.contrast(seed, bg), "after": C.contrast(start, bg)}})
    chosen = C.pick_distinct(pool, o["n"], kinds, start, bg)
    if len(chosen) < o["n"]:
        summary.append("summary.pool" if lines else "summary.pool-areas")
    used = [ds_id] if len(chosen) > (1 if start else 0) else []
    return {f"series-{i + 1}": hx for i, hx in enumerate(chosen)}, used


def _seq(o, seed, bgk, ctx, summary):
    fam, n = o["fam"], o["n"]
    if fam == "seed" and not seed:
        summary.append("summary.seed-missing")
        fam = DEFAULT_FAM["seq"]
    elif fam != "seed" and seed:
        summary.append("summary.seed-unused")
    used = []
    if fam == "viridis":
        table = [c["hex"] for c in _scheme(ctx["datasets"]["viridis"], "viridis")["colors"]]
        steps = [table[(2 * i * 255 + (n - 1)) // (2 * (n - 1))] for i in range(n)]
        if bgk == "light":
            steps.reverse()
        used = ["viridis"]
    elif fam == "cb-blues":
        steps = [c["hex"] for c in _scheme(ctx["datasets"]["colorbrewer"], "blues")["classes"][str(n)]]
        if bgk == "dark":
            steps.reverse()
        used = ["colorbrewer"]
    else:
        L, Cs, h = C.hex_to_oklch(seed)
        gray = h is None
        if gray:
            summary.append("summary.seed-gray")
        steps = []
        for i in range(n):
            t = i / (n - 1)
            c = 0.0 if gray else 0.02 + 0.10 * math.sin(math.pi * min(1.0, 1.1 * t))
            steps.append(C.oklch_to_hex(0.96 - 0.64 * t, c, 0.0 if gray else h))
        if bgk == "dark":
            steps.reverse()
    return steps, used


def _div(o, seed, ctx, changes, summary):
    fam, n = o["fam"], o["n"]
    if fam == "seed" and not seed:
        summary.append("summary.seed-missing")
        fam = DEFAULT_FAM["div"]
    elif fam != "seed" and seed:
        summary.append("summary.seed-unused")
    if fam in CB_FAM:
        steps = [c["hex"] for c in _scheme(ctx["datasets"]["colorbrewer"], CB_FAM[fam])["classes"][str(n)]]
        steps.reverse()   # kühle Seite zuerst: Stufe 1 = weit unter dem Mittelwert
        return steps, ["colorbrewer"]
    h_a, h_b = DIV_HUES
    if fam == "seed":
        h_s = C.hex_to_oklch(seed)[2]
        if h_s is None:
            summary.append("summary.seed-gray-div")
        else:
            h_a, h_b = h_s, (h_s + 180.0) % 360.0
            h_new, swapped = red_green(h_a, h_b)
            if swapped:
                before = C.oklch_to_hex(0.97 - 0.55, 0.13, h_b)
                h_b = h_new
                changes.append({"role": f"step-{n}", "mode": MODE, "from": before, "to": C.oklch_to_hex(0.97 - 0.55, 0.13, h_b),
                                "key": "red-green", "values": {"hue_from": (h_s + 180.0) % 360.0, "hue_to": h_b}})
    steps = []
    for i in range(n):
        u = (2 * i - (n - 1)) / (n - 1)
        a = abs(u)
        hue = h_a if u < 0 else h_b if u > 0 else 0.0
        steps.append(C.oklch_to_hex(0.97 - 0.55 * a, 0.13 * a, hue))
    return steps, []


# ---- Generator

def build(task, inp, ctx):
    o = inp["options"]
    t, bgk = o["t"], o["bg"]
    seed = inp.get("seed")
    bg = BG[bgk]
    roles = {}
    changes, findings, summary, distinct, used = [], [], [], [], []
    kinds = list(C.WORST_KINDS) + (["gray"] if o["pr"] else [])
    data = []
    if t == "cat":
        r, used = _cat(o, seed, bg, bgk, kinds, ctx, changes, summary)
        roles.update(r)
        data = list(r)
        summary.insert(0, "summary.cat-pr" if o["pr"] else "summary.cat")
    elif t in ("seq", "div"):
        steps, used = _seq(o, seed, bgk, ctx, summary) if t == "seq" else _div(o, seed, ctx, changes, summary)
        for i, hx in enumerate(steps):
            roles[f"step-{i + 1}"] = hx
        data = list(roles)
        summary.insert(0, f"summary.{t}" + ("-dark" if t == "seq" and bgk == "dark" else ""))
        if not _monotone(steps, t):
            findings.append({"id": "not-monotone", "mode": None, "severity": "note", "values": {}})
    else:
        context = C.solve_l(0.0, 0.0, [bg], 3.0, DIRECTION[bgk], CONTEXT_L0[bgk])["hex"]
        roles["highlight"] = OKABE_BLUE
        used = ["okabe-ito"]
        if seed:
            hi = to_contrast(seed, bg, bgk)
            # Fällt die eigene Farbe auf 3:1 praktisch mit dem Kontextgrau zusammen (unter der Schwelle 2 aus
            # CSS Color 4, schlechtester Fall normal, Deuteranopie, Protanopie), bleibt Okabe-Blau, mit Hinweis.
            if C.worst_distance(hi, context) < C.JND_DISTANCE:
                changes.append({"role": "highlight", "mode": MODE, "from": seed, "to": OKABE_BLUE, "key": "highlight-gray",
                                "values": {"distance": C.worst_distance(hi, context)}})
            else:
                used = []
                roles["highlight"] = hi
                if hi != seed:
                    changes.append({"role": "highlight", "mode": MODE, "from": seed, "to": hi, "key": "highlight",
                                    "values": {"before": C.contrast(seed, bg), "after": C.contrast(hi, bg)}})
        roles["context"] = context
        data = ["highlight", "context"]
        summary.insert(0, "summary.hl")
    roles["bg"] = bg
    roles["text"] = TEXT[bgk]
    roles["text-2"] = C.solve_l(0.0, 0.0, [bg], 4.5, DIRECTION[bgk], AXIS_L0[bgk])["hex"]
    roles["grid"] = C.oklch_to_hex(GRID_L[bgk], 0.0, 0.0)
    rbm = {MODE: roles}

    # Paare: Linien (cat lines, hl) normativ 3:1; Flächen (cat areas, seq, div) nur als Hinweis (4.4)
    t2 = dict(task)
    if t == "cat" and o["mark"] == "areas":
        t2["pairs"] = [p for p in task["pairs"] if not p["fg"].startswith("series-")]
        t2["advisory"] = list(task.get("advisory") or []) + [
            {"fg": p["fg"], "on": p["on"], "min": p["min"], "finding": "low-contrast"} for p in task["pairs"] if p["fg"].startswith("series-")]
    ev = C.evaluate(t2, rbm, "skip")
    low = [a for a in ev["advisory"] if not a["pass"]]
    if low:
        findings.insert(0, {"id": "low-contrast", "mode": None, "severity": "note", "values": {"ratio": min(a["ratio"] for a in low)}})

    # Abstände (4.1.8): schlechtester Fall normal, Deuteranopie, Protanopie; bei pr zusätzlich Graustufen getrennt
    cols = [roles[r] for r in data]
    if t in ("seq", "div"):
        groups = [("steps", list(C.WORST_KINDS))] + ([("steps-gray", ["gray"])] if o["pr"] else [])
        for did, ks in groups:
            a = _adjacent(cols, ks)
            if a:
                distinct.append({"id": did, "mode": MODE, "value": a["value"], "a": data[a["i"]], "b": data[a["i"] + 1], "kind": a["kind"]})
    else:
        base = "series" if t == "cat" else "highlight"
        groups = [(base, list(C.WORST_KINDS))] + ([(base + "-gray", ["gray"])] if o["pr"] else [])
        for did, ks in groups:
            md = C.min_distance(cols, ks)
            if md:
                distinct.append({"id": did, "mode": MODE, "value": md["value"], "a": data[md["i"]], "b": data[md["j"]], "kind": md["kind"]})
    if any(d["value"] < C.JND_DISTANCE for d in distinct):
        findings.append({"id": "near-jnd", "mode": None, "severity": "note", "values": {}})

    usage = {MODE: {r: _usage(roles[r], bg) for r in data}}
    # advisory: Datenfarben ohne Normpaar (Stufen, Flächen) mit Wert; der Rahmen zeigt sie in Block C und F (3.3)
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": rbm, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "advisory": ev["advisory"], "distinct": distinct, "changes": changes, "findings": findings, "usage": usage,
            "extra": {"datasets": used, "summary": summary}}


# ---- Name eines eigenen Zustands ohne eigene Farbe (nach Z geändert, 5.0)

def display_name(palette, text, lang):
    """Name aus dem, was die Palette tatsächlich zeigt: Familie, Anzahl, Darstellung und Hintergrund. Nennt nie eine
    Familie, aus der die Farben nicht stammen; fam „seed“ ohne eigene Farbe fällt wie im Generator auf die
    Standardfamilie. text sind die Texte der Aufgabe in der Sprache lang (Schlüssel name.*)."""
    o = palette["input"]["options"]
    t = o["t"]
    fam = DEFAULT_FAM[t] if o["fam"] == "seed" and not palette["input"].get("seed") else o["fam"]
    n = sum(1 for k in palette["roles"][MODE] if k.startswith("series-" if t == "cat" else "step-"))
    key = "name.hl" if t == "hl" else "name.cat" + ("_1" if n == 1 else "") if t == "cat" else "name.steps"
    return (text[key].replace("{fam}", text["name.fam." + fam]).replace("{n}", C.fmt_count(n, lang))
            .replace("{mark}", text["name.mark." + o["mark"]]).replace("{bg}", text["name.bg." + o["bg"]]))


# ---- Anzeige des Musters (view_vars): Teile ein- und ausblenden, Kacheln füllen, Konturen

def view_vars(palette, mode, toggles):
    o = palette["input"]["options"]
    t = o["t"]
    r = palette["roles"][mode]
    u = (palette.get("usage") or {}).get(mode, {})
    v = {"scheme": "dark" if o["bg"] == "dark" else "light",
         "v-lines": "block" if t == "hl" or (t == "cat" and o["mark"] == "lines") else "none",
         "v-bars": "block" if t == "cat" else "none",
         "v-tiles": "block" if t in ("seq", "div") else "none",
         "v-cat": "flex" if t == "cat" else "none",
         "v-hl": "flex" if t == "hl" else "none",
         "v-seq": "flex" if t == "seq" else "none",
         "v-div": "flex" if t == "div" else "none"}
    for k in range(1, 9):
        rid = f"series-{k}"
        v[f"s{k}"] = "flex" if rid in r else "none"
        v[f"e{k}"] = r["text"] if u.get(rid) == "area" else "transparent"
    n = sum(1 for k in r if k.startswith("step-"))
    for k in range(1, 10):
        v[f"t{k}"] = "flex" if k <= n else "none"
        v[f"f{k}"] = r["text"] if u.get(f"step-{k}") == "area" else "transparent"
    if n:
        for i, val in enumerate(TILE):
            s = val * n // 100 + 1
            v[f"c{i + 1}"] = r[f"step-{s}"]
            v[f"k{i + 1}"] = v[f"f{s}"]
    return v


# ---- JS-Array (5.8)

def _js(palette, task, ctx, lang, opts=None):
    o = palette["input"]["options"]
    t = o["t"]
    r = palette["roles"][MODE]
    text = ctx["text"]
    keys = {"cat": "series-", "seq": "step-", "div": "step-"}
    if t == "hl":
        rids = ["highlight", "context"]
    else:
        rids = [k for k in r if k.startswith(keys[t])]
        rids.sort(key=lambda k: int(k.rsplit("-", 1)[1]))
    head = text["js.head"].replace("{type}", text["ctl.t." + t])
    lines = ["// " + X.presub(head, ctx)]
    lines += ["// " + n for n in X.notices(palette, ctx, task, opts)]
    lines.append("// " + text["js.order." + t + ("-pr" if t == "cat" and o["pr"] else "")])
    low = [r[k] for k in rids if (palette.get("usage") or {}).get(MODE, {}).get(k) == "area"]
    if low:
        lines.append("// " + text["js.low"].replace("{text}", r["text"]).replace("{list}", ", ".join(low)))
    lines.append("const chartColors = [" + ", ".join('"' + r[k] + '"' for k in rids) + "];")
    lines.append("// " + X.presub(ctx["core"]["link"], ctx))
    return "\n".join(lines)


# ---- Zweck der Datenfarben unter 3:1 (4.4): „nur Flächen mit Kontur“ statt „Linien, Punkte, Balken“

def _area_task(palette, task, ctx, lang):
    """Aufgabe für die Exporte, in der Serien mit usage area den Zweck use.area tragen (Text mit der Konturfarbe)."""
    u = (palette.get("usage") or {}).get(MODE, {})
    use = ctx["text"]["use.area"].replace("{text}", palette["roles"][MODE]["text"])
    return dict(task, roles=[dict(r, **{"use_" + lang: use}) if u.get(r["id"]) == "area" and r["id"].startswith("series-") else r
                             for r in task["roles"]])


def _with_area(fn):
    def render(palette, task, ctx, lang, opts=None):
        return fn(palette, _area_task(palette, task, ctx, lang), ctx, lang, opts)
    return render


exports = {"js": _js, "hex": _with_area(X.hex_list), "css": _with_area(X.css), "dtcg": _with_area(X.dtcg),
           "agent": _with_area(X.agent)}
