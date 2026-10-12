"""Generator der Aufgabe KI-Bild (Spiegel von web/gen/ai-image.js, Spezifikation 3.7, 4.8, 5.5).

Ein englischer Farbblock für Bildprompts: Farben aus dem Feld „Eigene Farben“ (f), sonst drei Vorschläge aus der
eigenen Farbe (c, Chips s), sonst das Startset (p). Farbnamen nur aus dem festen Vokabular data/colornames.json,
Modellsyntax aus data/models.json (beide über ctx["data"]). Vertrag nach 7.4: build(task, inp, ctx) -> Palettenobjekt;
der Rahmen setzt task, preset, input, name_de und name_en. Rein und deterministisch, keine Datei-IO.
"""
import re

from tools import color as C
from tools import export as X

ROLES = ("dominant", "secondary", "accent", "background")
PARTS = ("[BACKGROUND AND LARGE SHAPES]", "[SECONDARY ELEMENTS]", "[THE FOCAL ELEMENT]")
PART_NO_BG = "[LARGE SHAPES]"  # Bildteil der Hauptfarbe, wenn eine eigene Hintergrundfarbe gesetzt ist
INK, PAPER = "#16191D", "#FFFFFF"  # fester Grund der Anteils-Tafel
TOKEN = re.compile(r"\{(c|w|p|a|b)\}")
WS = " \t\n\r"


# ---- Farbnamen (4.8.1)

def _sector(h, sectors):
    for lim, name in sectors:
        if h < lim:
            return name
    return sectors[-1][1]


def color_name(hx, cn):
    """Englischer Name aus dem festen Vokabular: Helligkeit, Buntheit, Grundwort (4.8.1, Schritte 1 bis 7)."""
    L, c, h = C.hex_to_oklch(hx)
    if c < cn["neutral_c_max"] or h is None:
        name = "black"
        for lim, n in cn["neutral_steps"]:
            if L >= lim:
                name = n
                break
        t = cn["tint"]
        if h is not None and c >= t["c_min"] and name != "black":
            if t["warm"][0] <= h <= t["warm"][1]:
                name += " with a warm tint"
            elif t["cool"][0] <= h <= t["cool"][1]:
                name += " with a cool tint"
        return name
    base = _sector(h, cn["sectors"])
    if base == "teal|cyan":
        base = "teal" if L < cn["teal_cyan_l"] else "cyan"
    drop = False
    for s in cn["substitutions"]:
        if base in s["bases"] and (("l_below" in s and L < s["l_below"]) or ("l_from" in s and L >= s["l_from"])):
            base, drop = s["to"], s["drop_lightness"]
            break
    lw, light = cn["lightness"], None
    if not drop:
        if L >= lw["light"]["l_from"]:
            if L >= lw["pale"]["l_from"] and c < lw["pale"]["c_below"]:
                light = "pale"
            elif c < lw["light"]["c_below"]:
                light = "light"
        elif lw["deep"][0] <= L < lw["deep"][1]:
            light = "deep"
        elif L < lw["dark"][1]:
            light = "dark"
    ch = cn["chroma"]
    chroma = "muted" if c < ch["muted_below"] else "vivid" if c > ch["vivid_above"] else None
    return " ".join(x for x in (light, chroma, base) if x)


def block_names(hexes, cn):
    """Namen eines Blocks; gleiche Namen ohne Helligkeitszusatz bekommen „lighter “ und „darker “ (Schritt 8), aber nur,
    wenn die hellste wirklich heller ist als die dunkelste. Gleiche Hex-Werte heißen immer gleich, dann greift same-names."""
    names = [color_name(h, cn) for h in hexes]
    out = list(names)
    words = set(cn["lightness_words"])
    for n in dict.fromkeys(names):
        idx = [i for i, x in enumerate(names) if x == n]
        if len(idx) < 2 or any(w in words for w in n.split(" ")):
            continue
        L = {i: C.hex_to_oklch(hexes[i])[0] for i in idx}
        lo = hi = idx[0]
        for i in idx:  # dunkelste: erste mit kleinstem L, hellste: letzte mit größtem L
            if L[i] < L[lo]:
                lo = i
            if L[i] >= L[hi]:
                hi = i
        if not L[hi] > L[lo]:
            continue
        for i in idx:
            if hexes[i] == hexes[hi]:
                out[i] = "lighter " + n
            elif hexes[i] == hexes[lo]:
                out[i] = "darker " + n
    return out


# ---- Vorschläge aus einer Farbe (4.8.2)

def suggest(seed, kind):
    """Drei Farben dominant, secondary, accent aus der eigenen Farbe, gamut-gemappt und quantisiert."""
    L, Cs, h = C.hex_to_oklch(seed)
    h = 0.0 if h is None else h
    seed = C.norm_hex(seed)
    if kind == "contrast":
        acc = C.oklch_to_hex(0.70 if L < 0.55 else 0.45, min(max(Cs, 0.10), 0.16), (h + 180) % 360)
        return [seed, C.oklch_to_hex(0.96, 0.01, h), acc]
    if kind == "signal":
        return [C.oklch_to_hex(0.95, 0.008, h), C.oklch_to_hex(0.30, 0.01, h), seed]
    sec = C.oklch_to_hex(0.95, min(0.02, Cs), h) if L < 0.7 else C.oklch_to_hex(0.30, min(0.04, Cs), h)
    acc = C.oklch_to_hex(L - 0.25, Cs, h) if L >= 0.5 else C.oklch_to_hex(L + 0.30, Cs, h)
    return [seed, sec, acc]


def suggest_values(seed, kind):
    """Kleinster Abstand normal, Rot-Grün (Deuteranopie und Protanopie) und in Graustufen für einen Vorschlag."""
    cols = suggest(seed, kind)
    return {"normal": C.min_distance(cols, ["normal"])["value"],
            "redgreen": C.min_distance(cols, ["deutan", "protan"])["value"],
            "gray": C.min_distance(cols, ["gray"])["value"]}


# ---- Palette

def _colors(inp):
    """Vorrang f vor c vor p (2.3). → ([(rolle, hex)], quelle)."""
    o = inp["options"]
    f = o.get("f")
    if f:
        if len(f) < 2:
            raise C.SolveError("few-colors", {"n": len(f)})
        return [(ROLES[i], C.norm_hex(x)) for i, x in enumerate(f[:4])], "f"
    if inp.get("seed"):
        return list(zip(ROLES, suggest(inp["seed"], o.get("s") or "calm"))), "seed"
    return [(c["role"], C.norm_hex(c["value"])) for c in inp["colors"]], "preset"


def _weights(o, present):
    main = [r for r in present if r != "background"]
    if len(main) == 2:
        return {main[0]: 80, main[1]: 20}
    w = [int(x) for x in (o.get("w") or "60-30-10").split("-")]
    return {r: w[i] for i, r in enumerate(main)}


def build(task, inp, ctx):
    cn = ctx["data"]["colornames"]
    o = inp["options"]
    cols, src = _colors(inp)
    present = [r for r, _ in cols]
    hexes = [hx for _, hx in cols]
    roles = {"default": dict(cols)}
    names = dict(zip(present, block_names(hexes, cn)))
    # Textpaar: dunkelste auf hellster Farbe (4.8.4)
    ys = [C.rel_lum(hx) for hx in hexes]
    dk, lt = 0, 0
    for i, y in enumerate(ys):
        if y < ys[dk]:
            dk = i
        if y > ys[lt]:
            lt = i
    lines = [{"fg": present[dk], "on": [present[lt]], "min": 4.5, "criterion": "1.4.3", "rule": "text-contrast"}] if dk != lt else []
    ev = C.evaluate(dict(task, pairs=lines), roles, "skip")
    tp = {present[dk], present[lt]}
    decorative = [d for d in ev["decorative"] if not (lines and {d["fg"], d["bg"]} == tp)]
    text_ok = bool(ev["pairs"]) and ev["pairs"][0]["pass"]
    findings = []
    if not text_ok:
        findings.append({"id": "no-text-line", "mode": None, "severity": "note",
                         "values": {"ratio": ev["pairs"][0]["ratio"] if ev["pairs"] else 1.0}})
    if len(set(names.values())) < len(names):
        findings.append({"id": "same-names", "mode": None, "severity": "note", "values": {}})
    distinct = []
    for kind in ("normal", "deutan", "protan", "gray"):
        md = C.min_distance(hexes, [kind])
        distinct.append({"id": "colors", "mode": "default", "value": md["value"], "a": present[md["i"]],
                         "b": present[md["j"]], "kind": kind})
    ref = "background" if "background" in roles["default"] else "dominant"
    use = {}
    for r, hx in cols:
        if r != ref:
            cr = C.contrast(hx, roles["default"][ref])
            use[r] = "text" if cr >= 4.5 else "lines" if cr >= 3.0 else "area"
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": decorative,
            "distinct": distinct, "changes": [], "findings": findings, "usage": {"default": use},
            "extra": {"names": names, "weights": _weights(o, present), "text_pair": [present[dk], present[lt]] if text_ok else None,
                      "source": src}}


def view_vars(palette, mode, toggles):
    """Anteils-Tafel: Flächen im Verhältnis der Anteile, Beschriftung mit Name und Hex (CSS-Zeichenkette)."""
    r, ex = palette["roles"]["default"], palette["extra"]
    out = {"paper": PAPER, "ink": INK, "board": r.get("background", PAPER)}
    for role in ROLES:
        if role in r:
            out["label-" + role] = "'" + ex["names"][role] + " · " + r[role] + "'"
            out["w-" + role] = str(ex["weights"].get(role, 0))
            out["show-" + role] = "flex"
        else:
            out["show-" + role] = "none"
    return out


# ---- Export Bildprompt (5.5)

def fill(t, vals):
    return TOKEN.sub(lambda m: vals[m.group(1)] if m.group(1) in vals else m.group(0), t)


def model(ctx, mid):
    for m in ctx["data"]["models"]["models"]:
        if m["id"] == mid:
            return m
    return ctx["data"]["models"]["models"][0]


def _part(o, key, default):
    v = (o.get(key) or "").strip(WS)
    return v or default


def prompt_text(palette, mdl, text):
    """Der englische Farbblock in der Syntax des Modells (ohne Vorbehalte, ohne Kopfzeile)."""
    o = palette["input"]["options"]
    r, ex = palette["roles"]["default"], palette["extra"]
    hexed = mdl["method"] == "hex-in-prompt"

    def nm(role):
        return ex["names"][role] + (" (" + r[role] + ")" if hexed else "")
    bg = "background" in r
    p1 = _part(o, "b1", PARTS[0])
    if bg and p1 == PARTS[0]:
        p1 = PART_NO_BG
    w = ex["weights"]
    clauses = [fill(text["pr.dominant"], {"c": nm("dominant"), "w": str(w["dominant"]), "p": p1})]
    if "secondary" in r:
        clauses.append(fill(text["pr.secondary"], {"c": nm("secondary"), "w": str(w["secondary"]), "p": _part(o, "b2", PARTS[1])}))
    if "accent" in r:
        clauses.append(fill(text["pr.accent"], {"c": nm("accent"), "w": str(w["accent"]), "p": _part(o, "b3", PARTS[2])}))
    if bg:
        clauses.append(fill(text["pr.background"], {"c": nm("background")}))
    out = text["pr.open"] + "; ".join(clauses) + ". " + text["pr.guard"]
    if ex["text_pair"]:
        out += " " + fill(text["pr.text"], {"a": nm(ex["text_pair"][0]), "b": nm(ex["text_pair"][1])})
    if mdl["id"] == "gpt-image":
        out += " " + text["pr.gpt"]
    return out


def _rgb(hx):
    return "[" + ", ".join(str(int(hx[i:i + 2], 16)) for i in (1, 3, 5)) + "]"


def recraft_json(palette):
    r, w = palette["roles"]["default"], palette["extra"]["weights"]
    cols = ", ".join('{"rgb": ' + _rgb(r[x]) + ', "weight": ' + X.dec(w[x], 2) + "}" for x in ROLES if x in r and x != "background")
    out = '{"controls": {"colors": [' + cols + "]"
    if "background" in r:
        out += ', "background_color": {"rgb": ' + _rgb(r["background"]) + "}"
    return out + "}}"


def _note(mdl, text, lang, extra=None):
    """Hinweis neben dem Block, außerhalb des Kopiertexts: Modell, Stand der Doku, Pflichtzeile."""
    esc = C.esc
    head = fill(text["note.model"], {"c": "<b>" + esc(mdl["name"]) + "</b>", "w": esc(mdl["vendor"]), "p": esc(mdl["checked"])})
    parts = [head + " " + esc(mdl["note_" + lang])]
    if mdl.get("doc_note_" + lang):
        parts.append(esc(mdl["doc_note_" + lang]))
    if mdl.get("quote"):
        parts.append(fill(text["note.quote"], {"c": esc(mdl["quote"])}))
    if extra:
        parts.append(esc(extra))
    parts.append(text["note.duty"])
    return " ".join(parts)


def prompt(palette, task, ctx, lang, opts=None):
    text = ctx["text"]
    mdl = model(ctx, palette["input"]["options"].get("mdl"))
    blocks = [{"label": None, "text": prompt_text(palette, mdl, text), "suffix": "", "lang": "en", "note": _note(mdl, text, lang)}]
    r = palette["roles"]["default"]
    if mdl["method"] == "palette-field":
        blocks[0]["label"] = text["blk.prompt"]
        blocks.append({"label": text["blk.palette"], "text": " ".join(r[x] for x in ROLES if x in r), "suffix": "-palette",
                       "lang": None, "note": _note(mdl, text, lang, mdl.get("field_note_" + lang))})
    elif mdl["method"] == "api-weights":
        blocks[0]["label"] = text["blk.prompt"]
        blocks.append({"label": text["blk.json"], "text": recraft_json(palette), "suffix": "-controls", "lang": None,
                       "note": _note(mdl, text, lang, mdl.get("field_note_" + lang)), "ext": "json"})
    return blocks


def hex_list(palette, task, ctx, lang, opts=None):
    """Hex-Liste des Rahmens. Mit eigenen Farben (f) nennt die Kopfzeile „Eigene Farben“ statt der Startpalette
    (f geht vor p, 2.3). Seit Z setzt der Rahmen diesen Namen selbst (custom_name_colors); das bleibt als Absicherung."""
    if palette["extra"].get("source") == "f":
        ctx = dict(ctx, name=ctx["text"]["name.f"])
    return X.hex_list(palette, task, ctx, lang, opts)


exports = {"prompt": prompt, "hex": hex_list}
