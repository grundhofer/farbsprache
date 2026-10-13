"""Palette prüfen: Scanner, Rollen, Befund-Engine, Reparatur, Ansicht und Exporte.

Spiegel von web/check.js (FS.check). Rein und deterministisch, ohne Datei-IO außer im Kommandozeilenteil.
Der Build rendert damit das Beispiel der Prüfseite statisch, der Browser rendert jede eigene Eingabe mit
web/check.js. tests/check.test.cjs vergleicht beide Ausgaben Byte für Byte.

  scan(text, cfg)                     Farben im Freitext und in CSS-Variablen, Kontexte hell und dunkel
  analyze(scan, cfg, refs, state)     Rollen, Hintergrund, Befunde, Erfüllt, kleinste Abstände
  render(model, R)                    HTML der Ergebnisblöcke 2 bis 9
  report / hexlist / css              Exporte (Prüfbericht, Hex-Liste, CSS mit Rollen)

Konfiguration: data/check.json (Rollen-Regex, Paare, Befundarten). Texte: web/copy/check.py.
Jede Zahl kommt aus den Formatierern und Platzhaltern von tools/color.py.
Check palette engine (Python mirror of web/check.js)."""
import json, re, sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import color as C, export as X  # noqa: E402

SEVS = ("fail", "check", "note")
SYM = {"fail": "■", "check": "▲", "note": "●", "pass": "✓"}
KINDS_SIM = ("normal", "gray", "deutan", "protan", "tritan")
KINDS_DIST = ("normal", "deutan", "protan", "tritan", "gray")
CTXS = ("light", "dark")

_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
_DECL = re.compile(r"(^|[ \t\r\n\f{;])(--[A-Za-z0-9_-]+)[ \t\r\n\f]*:[ \t\r\n\f]*([^;{}]*)")
_HEX = re.compile(r"#[0-9A-Fa-f]{3,8}(?![0-9A-Za-z_-])")
_FUNC = re.compile(r"(rgba?|hsla?|oklch|oklab|color)\([^()]*\)", re.I)
_WORD = re.compile(r"[A-Za-z]+")
_IMPORTANT = re.compile(r"[ \t\r\n\f]*!important[ \t\r\n\f]*$", re.I)
_TRIM = re.compile(r"^[ \t\r\n\f]+|[ \t\r\n\f]+$")
_HSLCH = re.compile(r"-?[0-9]*\.?[0-9]+(deg)?[ \t]+[0-9]*\.?[0-9]+%[ \t]+[0-9]*\.?[0-9]+%")
_VAR = re.compile(r"var\([ \t]*--([A-Za-z0-9_-]+)[ \t]*(,[^)]*)?\)")
_IDENT = re.compile(r"[A-Za-z0-9_-]")


def _ident_before(text, i):
    return i > 0 and bool(_IDENT.fullmatch(text[i - 1]))


def _ident_after(text, i):
    return i < len(text) and bool(_IDENT.fullmatch(text[i]))


# ---- Scanner

def _blocks(text):
    """Blöcke {…} mit ihrem Selektor: [(öffnet, schließt, prelude)]. Unvollständige schließen am Textende."""
    out, stack, last = [], [], 0
    for i, ch in enumerate(text):
        if ch == "{":
            stack.append((i, _TRIM.sub("", text[last:i])))
            last = i + 1
        elif ch == "}":
            if stack:
                o, pre = stack.pop()
                out.append((o, i, pre))
            last = i + 1
        elif ch == ";":
            last = i + 1
    for o, pre in stack:
        out.append((o, len(text), pre))
    return out


def _ctx_at(pos, blocks, dark):
    for o, c, pre in blocks:
        if o < pos < c and any(rx.search(pre) for rx in dark):
            return "dark"
    return "light"


def _parse_value(v):
    """Farbe aus einem Variablenwert: CSS-Farbe oder Kanäle im shadcn-Stil „222 47% 11%“."""
    p = C.parse(v, False)
    if p is None and _HSLCH.fullmatch(v):
        p = C.parse("hsl(" + v + ")", False)
    return p


def scan(text, cfg):
    """Freitext oder CSS → {colors, notes}. colors in der Reihenfolge hell, dann dunkel; je Kontext höchstens
    cfg.max_colors nach dem Zusammenfassen gleicher Farben. Ein Eintrag: {hex, alpha, oog, md, raw, names,
    spans, ctx}. names sind Variablennamen ohne „--“, spans die Textstellen der Werte."""
    text = text if isinstance(text, str) else ""
    clean = _COMMENT.sub(lambda m: " " * len(m.group(0)), text)
    dark = [re.compile(p, re.I) for p in cfg["dark_contexts"]]
    blocks = _blocks(clean)
    found, taken, notes = [], [], []
    decls = []
    for m in _DECL.finditer(clean):
        name = m.group(2)[2:]
        vs = m.start(3)
        val = _TRIM.sub("", _IMPORTANT.sub("", _TRIM.sub("", m.group(3))))
        start = m.start(2)
        decls.append({"name": name, "val": val, "vs": vs, "ve": vs + len(val), "ctx": _ctx_at(start, blocks, dark), "start": start})
        taken.append((start, m.end(3)))
    by_ctx = {}
    for d in decls:
        by_ctx[(d["ctx"], d["name"])] = d  # die letzte Deklaration gilt (Kaskade)
    for d in decls:
        if not d["val"]:
            continue
        p = _parse_value(d["val"])
        if p is None:
            mv = _VAR.fullmatch(d["val"])
            if mv is None:
                continue
            ref = by_ctx.get((d["ctx"], mv.group(1)))
            p = _parse_value(ref["val"]) if ref and not _VAR.fullmatch(ref["val"] or "") else None
            if p is None:
                notes.append({"key": "var", "name": d["name"], "ref": mv.group(1)})
                continue
        found.append({"pos": d["start"], "p": p, "raw": d["val"], "name": d["name"], "span": [d["vs"], d["ve"]], "ctx": d["ctx"]})

    def free(s, e):
        for a, b in taken:
            if s < b and e > a:
                return False
        return True
    toks = []
    for m in _HEX.finditer(clean):
        if not _ident_before(clean, m.start()) and clean[m.start() - 1:m.start()] != "&":
            toks.append((m.start(), m.end()))
    for m in _FUNC.finditer(clean):
        if not _ident_before(clean, m.start()):
            toks.append((m.start(), m.end()))
    for m in _WORD.finditer(clean):
        w = m.group(0).lower()
        if w in C.NAMES and not _ident_before(clean, m.start()) and not _ident_after(clean, m.end()):
            toks.append((m.start(), m.end()))
    toks.sort()
    last_end = -1
    for s, e in toks:
        if s < last_end or not free(s, e):
            continue
        p = C.parse(clean[s:e], False)
        if p is None:
            continue
        last_end = e
        found.append({"pos": s, "p": p, "raw": text[s:e], "name": None, "span": [s, e], "ctx": _ctx_at(s, blocks, dark)})
    found.sort(key=lambda f: f["pos"])
    colors, dropped = {"light": [], "dark": []}, {"light": 0, "dark": 0}
    for f in found:
        lst, p = colors[f["ctx"]], f["p"]
        hit = None
        for c in lst:
            if c["hex"] == p["hex"] and c["alpha"] == p["alpha"]:
                hit = c
                break
        if hit is None:
            if len(lst) >= cfg["max_colors"]:
                dropped[f["ctx"]] += 1
                continue
            hit = {"hex": p["hex"], "alpha": p["alpha"], "oog": bool(p["out_of_gamut"]), "md": p["mapped_distance"],
                   "raw": f["raw"], "names": [], "spans": [], "ctx": f["ctx"]}
            lst.append(hit)
        if f["name"] and f["name"] not in hit["names"]:
            hit["names"].append(f["name"])
        hit["spans"].append(f["span"])
    for ctx in CTXS:
        if dropped[ctx]:
            notes.append({"key": "dropped", "ctx": ctx, "n": dropped[ctx]})
    return {"colors": colors["light"] + colors["dark"], "notes": notes}


def _uniq(nm, used):
    """Name in einem Block eindeutig machen: der zweite heißt „surface-b“, der dritte „surface-c“. Ein Buchstabe trifft
    kein Rollenmuster aus data/check.json (anders als „text-2“, das als gedämpfter Text gälte). used wird ergänzt."""
    s, k = nm, 0
    while s in used:
        s = nm + "-" + "bcdefghijklmnopqrstuvwxyz"[k]
        k += 1
    used.add(s)
    return s


def state_text(f, r):
    """Eingabetext aus dem URL-Zustand (f, r): mit r als CSS-Block (Rolle als Variablenname, „-“ als Farbe ohne
    Namen im Block ihres Kontexts), sonst als Hex-Liste. Teilen sich Farben eine Rolle, bekommen sie eindeutige Namen."""
    if not r:
        return " ".join(f)
    out = {"light": [], "dark": []}
    used = {"light": set(), "dark": set()}
    for i, hx in enumerate(f):
        tok = r[i] if i < len(r) else "-"
        ctx = "dark" if tok.endswith(".d") else "light"
        role = tok[:-2] if tok.endswith(".d") else tok
        out[ctx].append("  " + ("--" + _uniq(role, used[ctx]) + ": " if role != "-" else "") + hx + ";")
    parts = []
    if out["light"]:
        parts.append(":root {\n" + "\n".join(out["light"]) + "\n}")
    if out["dark"]:
        parts.append(".dark {\n" + "\n".join(out["dark"]) + "\n}")
    return "\n".join(parts)


def state_roles(r):
    """Rollen aus r (parallel zu f) und ob sie bestätigt sind. Nur „-“ heißt: r trägt allein den Kontext (dunkel),
    die Rollen sind nicht bestätigt (query schreibt dann keine Rollen)."""
    if not r:
        return None, False
    roles = [None if (t[:-2] if t.endswith(".d") else t) == "-" else (t[:-2] if t.endswith(".d") else t) for t in r]
    if not any(roles):
        return None, False
    return roles, True


# ---- Rollen

def guess_roles(colors, cfg):
    """Rolle je Farbe aus den Variablennamen: beste Priorität gewinnt, jede Rolle je Kontext höchstens einmal."""
    rx = [[re.compile(p) for p in role["patterns"]] for role in cfg["roles"]]
    pre = cfg["name_prefix"]
    best = []
    for c in colors:
        b = None
        for name in c["names"]:
            n = name.lower()
            if n.startswith(pre):
                n = n[len(pre):]
            for ri, pats in enumerate(rx):
                for pi, p in enumerate(pats):
                    if p.fullmatch(n) and (b is None or (pi, ri) < (b[0], b[1])):
                        b = (pi, ri)
        best.append(b)
    out = [None] * len(colors)
    for ctx in CTXS:
        for ri, role in enumerate(cfg["roles"]):
            win = None
            for g, c in enumerate(colors):
                if c["ctx"] == ctx and best[g] is not None and best[g][1] == ri:
                    if win is None or best[g][0] < best[win][0]:
                        win = g
            if win is not None:
                out[win] = role["id"]
    return out


# ---- Bewertung

def _role_def(cfg, rid):
    for r in cfg["roles"]:
        if r["id"] == rid:
            return r
    return None


def _finding_def(cfg, fid):
    for f in cfg["findings"]:
        if f["id"] == fid:
            return f
    return None


def _contrast_items(m, cfg, cx):
    """Alle Kontrastprüfungen eines Kontexts: [{id, i, on, min, firm, cond, role}] (ohne Ergebnis)."""
    cols = m["colors"]
    idx, bg = cx["idx"], cx["bg"]
    roles = {g: cols[g]["role"] for g in idx}
    items = []

    def of_role(rid):
        if rid == "bg":
            return [bg]
        return [g for g in idx if roles[g] == rid]
    if cx["roles_mode"]:
        for pr in cfg["pairs"]:
            for g in of_role(pr["fg"]):
                if g == bg:
                    continue
                ons = []
                for rid in pr["on"]:
                    for o in of_role(rid):
                        if o != g and o not in ons:
                            ons.append(o)
                if ons:
                    items.append({"id": pr["finding"], "i": g, "on": ons, "min": pr["min"], "firm": pr["firm"],
                                  "cond": pr.get("cond"), "role": pr["fg"]})
    for g in idx:
        if g == bg or (cx["roles_mode"] and roles[g] is not None):
            continue
        items.append({"id": "check-text", "i": g, "on": [bg], "min": cfg["free_text_min"], "firm": False, "cond": "free", "role": None})
        items.append({"id": "check-nontext", "i": g, "on": [bg], "min": cfg["free_nontext_min"], "firm": False, "cond": "free", "role": None})
    return items


def _measure(item, hexes):
    worst, wi = None, None
    for o in item["on"]:
        r = C.contrast(hexes[item["i"]], hexes[o])
        if worst is None or r < worst - 1e-12:
            worst, wi = r, o
    return worst, wi


def _values(items, hexes):
    return [_measure(it, hexes)[0] for it in items]


def _worse(it, before, after):
    """Eine Kontrastprüfung wird schlechter, wenn sie vorher erfüllt war und danach verfehlt, oder wenn sie schon
    verfehlt war und ihr Wert weiter sinkt."""
    return (before >= it["min"] > after) or (before < it["min"] and after < before - 1e-12)


def _metric(fid, a, b, refs):
    if fid == "check-duplicates":
        return C.distance(a, b, "normal")
    if fid == "check-gray":
        return C.gray_distance(a, b)
    return C.worst_distance(a, b, C.WORST_KINDS)


def _target(fid, cfg, refs):
    """Vergleichswert eines Abstands-Befunds, um 1e-9 abgesenkt: Okabe-Ito selbst liegt nicht „unter“ seinem eigenen
    Vergleichswert, auch wenn Python und JS das letzte Bit verschieden rechnen."""
    if fid == "check-cvd":
        return refs[cfg["compare"]]["value"] - 1e-9
    return C.JND_DISTANCE - 1e-9


def _repair_contrast(it, hexes):
    """Reparatur: solve_l mit gleichem Farbton und gleicher Buntheit, weg vom Hintergrund."""
    a = hexes[it["i"]]
    L, Cc, h = C.hex_to_oklch(a)
    ya = C.rel_lum(a)
    against = [hexes[o] for o in it["on"]]
    lighter = [C.rel_lum(b) >= ya for b in against]
    direction = -1 if all(lighter) else 1 if not any(lighter) else 0
    if direction == 0:
        return {"i": it["i"], "from": a, "to": None}
    try:
        r = C.solve_l(Cc, h, against, it["min"], direction, L)
    except C.SolveError:
        return {"i": it["i"], "from": a, "to": None}
    return {"i": it["i"], "from": a, "to": r["hex"]}


def _grid(orig, cfg, cache):
    """Kandidaten der Abstands-Reparatur für eine Farbe (gleiches C und h, L im Raster), je Analyse einmal gerechnet."""
    if orig not in cache:
        L0, Cc, h = C.hex_to_oklch(orig)
        g = cfg["repair_grid"]
        cache[orig] = [C.oklch_to_hex(k / g["div"], Cc, h) for k in range(g["from"], g["to"] + 1)]
    return cache[orig]


def _repair_distance(fid, g1, g2, m, cfg, refs, items, hexes, members, cache):
    """Abstands-Befund: die hellere Farbe in L verschieben (Raster cfg.repair_grid), kleinster Abstand zum
    Original, Vergleichswert erreicht, keine Kontrastprüfung verschlechtert (_worse), keine weitere Nähe erzeugt."""
    ya, yb = C.rel_lum(hexes[g1]), C.rel_lum(hexes[g2])
    mv, other = (g1, g2) if ya > yb else (g2, g1)
    orig = hexes[mv]
    target = _target(fid, cfg, refs)
    # nur Prüfungen, an denen die verschobene Farbe beteiligt ist, können sich ändern
    items = [it for it in items if it["i"] == mv or mv in it["on"]]
    before = _values(items, hexes)
    near_before = {o: _metric(fid, orig, hexes[o], refs) >= target for o in members if o not in (mv, other)}
    best, best_d = None, None
    for cand in _grid(orig, cfg, cache):
        if any(cand == hx for o, hx in hexes.items() if o != mv) or cand == orig:
            continue
        if _metric(fid, cand, hexes[other], refs) < target:
            continue
        trial = dict(hexes)
        trial[mv] = cand
        after = _values(items, trial)
        if any(_worse(it, b, a) for it, b, a in zip(items, before, after)):
            continue
        if any(ok and _metric(fid, cand, hexes[o], refs) < target for o, ok in near_before.items()):
            continue
        d = C.distance(orig, cand, "normal")
        if best is None or d < best_d - 1e-12:
            best, best_d = cand, d
    return {"i": mv, "from": orig, "to": best, "other": other}


def analyze(sc, cfg, refs, state=None):
    """Befund-Engine. state: {confirmed: bool, roles: [rolle|None je Farbe] | None, bgi: int | None}.
    → Modell {colors, ctxs, confirmed, has_names, notes}. Indizes sind global (Reihenfolge von scan)."""
    state = state or {}
    raw = sc["colors"]
    n = len(raw)
    roles = state.get("roles")
    guessed = guess_roles(raw, cfg)
    confirmed = bool(state.get("confirmed")) and roles is not None
    cols = []
    for g, c in enumerate(raw):
        c2 = dict(c)
        if roles is not None:
            c2["role"] = roles[g] if g < len(roles) else None
            c2["role_src"] = "confirmed" if confirmed else "user"
        else:
            c2["role"] = guessed[g]
            c2["role_src"] = "guess"
        cols.append(c2)
    m = {"colors": cols, "ctxs": [], "confirmed": confirmed, "notes": list(sc.get("notes") or []),
         "has_names": any(c["names"] for c in raw) or roles is not None}
    bgi = state.get("bgi")
    for ctx in CTXS:
        idx = [g for g in range(n) if cols[g]["ctx"] == ctx]
        if not idx:
            continue
        cx = {"ctx": ctx, "idx": idx, "roles_mode": any(cols[g]["role"] for g in idx)}
        # Hintergrund: Chip (bgi) vor Rolle bg vor hellster (hell) bzw. dunkelster (dunkel) Farbe
        bg = None
        if isinstance(bgi, int) and bgi in idx:
            bg = bgi
        if bg is None:
            for g in idx:
                if cols[g]["role"] == "bg":
                    bg = g
                    break
        if bg is None:
            def over_white(g):
                c = cols[g]
                return c["hex"] if c["alpha"] >= 1 else C.composite(c["hex"], c["alpha"], "#FFFFFF")
            for g in idx:
                y = C.rel_lum(over_white(g))
                if bg is None or (ctx == "dark" and y < C.rel_lum(over_white(bg)) - 1e-12) or \
                        (ctx != "dark" and y > C.rel_lum(over_white(bg)) + 1e-12):
                    bg = g
        cx["bg"] = bg
        bc = cols[bg]
        bg_eff = bc["hex"] if bc["alpha"] >= 1 else C.composite(bc["hex"], bc["alpha"], "#FFFFFF")
        for g in idx:
            c = cols[g]
            c["eff"] = bg_eff if g == bg else (c["hex"] if c["alpha"] >= 1 else C.composite(c["hex"], c["alpha"], bg_eff))
            L, Cc, h = C.hex_to_oklch(c["eff"])
            c["chroma"] = Cc
            c["oklch"] = C.shortest_oklch(c["eff"])
            wr, kr = C.contrast(c["eff"], "#FFFFFF"), C.contrast(c["eff"], "#000000")
            c["best"] = "#FFFFFF" if wr >= kr else "#000000"
        hexes = {g: cols[g]["eff"] for g in idx}
        items = _contrast_items(m, cfg, cx)
        findings, passes = [], []
        for it in items:
            if it["id"] == "check-nontext" and it["cond"] == "free":
                # Linie und Grafik nur, wenn die Farbe als Text schon verfehlt (sonst trivial erfüllt)
                twin = next(x for x in items if x["id"] == "check-text" and x["i"] == it["i"] and x["cond"] == "free")
                if _measure(twin, hexes)[0] >= twin["min"]:
                    continue
            r, wi = _measure(it, hexes)
            rec = {"id": it["id"], "i": it["i"], "j": wi, "on": it["on"], "min": it["min"], "role": it["role"],
                   "cond": it["cond"], "firm": it["firm"], "value": r, "ctx": ctx}
            if r >= it["min"]:
                passes.append(rec)
                continue
            rec["sev"] = "fail" if it["firm"] and confirmed else "check"
            rec["open"] = "unconfirmed" if it["firm"] and not confirmed else it["cond"]
            rec["repair"] = _repair_contrast(it, hexes)
            findings.append(rec)
        # Abstände: mit Rollen nur Signalfarben und Farben ohne Rolle, ohne Rollen alle außer dem Hintergrund
        signal = set(cfg["signal_roles"])
        members = [g for g in idx if g != bg and (not cx["roles_mode"] or cols[g]["role"] is None or cols[g]["role"] in signal)]
        cx["set"] = members
        dup, grid_cache = set(), {}
        for fid in ("check-duplicates", "check-cvd", "check-gray"):
            target = _target(fid, cfg, refs)
            for a_i in range(len(members)):
                for b_i in range(a_i + 1, len(members)):
                    g1, g2 = members[a_i], members[b_i]
                    if (g1, g2) in dup:
                        continue
                    a, b = hexes[g1], hexes[g2]
                    if fid == "check-cvd":
                        md = C.min_distance([a, b], C.WORST_KINDS)
                        v, kind = md["value"], md["kind"]
                    else:
                        v, kind = _metric(fid, a, b, refs), ("normal" if fid == "check-duplicates" else "gray")
                    if v >= target:
                        continue
                    if fid == "check-duplicates":
                        dup.add((g1, g2))
                    rec = {"id": fid, "i": g1, "j": g2, "kind": kind, "value": v, "sev": "note", "ctx": ctx}
                    rec["repair"] = _repair_distance(fid, g1, g2, m, cfg, refs, items, hexes, members, grid_cache)
                    findings.append(rec)
        if len(idx) >= 2 and not any(cols[g]["chroma"] < cfg["neutral_c_max"] for g in idx):
            findings.append({"id": "check-neutral-missing", "i": None, "j": None, "sev": "note", "ctx": ctx, "repair": None})
        for g in idx:
            if cols[g]["oog"]:
                findings.append({"id": "check-gamut", "i": g, "j": None, "sev": "note", "ctx": ctx, "repair": None})
            if cols[g]["alpha"] < 1:
                findings.append({"id": "check-alpha", "i": g, "j": None, "sev": "note", "ctx": ctx, "repair": None})
        order = [f["id"] for f in cfg["findings"]]
        for k, f in enumerate(findings):
            f["n"] = k
            f["key"] = "|".join([ctx, f["id"], "-" if f["i"] is None else str(f["i"]), "-" if f["j"] is None else str(f["j"])])
        findings.sort(key=lambda f: (SEVS.index(f["sev"]), order.index(f["id"]), f["n"]))
        cx["findings"] = findings
        cx["passes"] = passes
        # Kleinste Abstände je Sichtweise (Block 7)
        dist = {}
        for kind in KINDS_DIST:
            ps = []
            for a_i in range(len(members)):
                for b_i in range(a_i + 1, len(members)):
                    g1, g2 = members[a_i], members[b_i]
                    ps.append((C.distance(hexes[g1], hexes[g2], kind), a_i, b_i, g1, g2))
            ps.sort(key=lambda t: (t[0], t[1], t[2]))
            dist[kind] = [{"a": t[3], "b": t[4], "value": t[0]} for t in ps[:5]]
        cx["dist"] = dist
        m["ctxs"].append(cx)
    return m


def query(m, bgi=None):
    """URL-Zustand: f (Hex ohne #, Alpha als achtstelliges Hex), r mit bestätigten Rollen, bgi. Ohne Bestätigung
    trägt r nur den Kontext („-“ hell, „-.d“ dunkel) und nur, wenn es dunkle Farben gibt; Rollen stehen nie darin."""
    cols = m["colors"]
    if not cols:
        return ""
    f = []
    for c in cols:
        h = c["hex"][1:]
        if c["alpha"] < 1:
            h += "%02X" % C.quantize(c["alpha"])
        f.append(h)
    out = ["f=" + ",".join(f)]
    if m["confirmed"]:
        out.append("r=" + ",".join((c["role"] or "-") + (".d" if c["ctx"] == "dark" else "") for c in cols))
    elif any(c["ctx"] == "dark" for c in cols):
        out.append("r=" + ",".join("-.d" if c["ctx"] == "dark" else "-" for c in cols))
    if isinstance(bgi, int) and 0 <= bgi < len(cols):
        out.append("bgi=" + str(bgi))
    return "&".join(out)


def read_query(search, cfg):
    """Query-String → {f: [Hex], r: [Token] | None, bgi: int | None, dirty: bool}. Ungültiges fällt weg."""
    f, r, bgi, dirty, seen = None, None, None, False, set()
    for part in (search or "").lstrip("?").split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        if k in seen:
            dirty = True
            continue
        seen.add(k)
        if k == "f":
            vals = []
            for x in v.split(","):
                p = C.parse("#" + x, False) if re.fullmatch(r"[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", x) else None
                if p is None:
                    vals = None
                    break
                vals.append("#" + x.upper())
            if vals and len(vals) <= 2 * cfg["max_colors"]:
                f = vals
            else:
                dirty = True
        elif k == "r":
            ids = {x["id"] for x in cfg["roles"]}
            toks = v.split(",")
            if all((t[:-2] if t.endswith(".d") else t) in ids | {"-"} for t in toks):
                r = toks
            else:
                dirty = True
        elif k == "bgi":
            if re.fullmatch(r"[0-9]{1,2}", v):
                bgi = int(v)
            else:
                dirty = True
        else:
            dirty = True
    if f is None and (r is not None or bgi is not None):
        r, bgi, dirty = None, None, True
    if f is not None and r is not None and len(r) != len(f):
        r, dirty = None, True
    if f is not None and bgi is not None and bgi >= len(f):
        bgi, dirty = None, True
    if f is not None and r is not None:
        # Reihenfolge wie scan: erst hell, dann dunkel (state_text schreibt die Blöcke so); bgi wandert mit
        order = [i for i in range(len(r)) if not r[i].endswith(".d")] + [i for i in range(len(r)) if r[i].endswith(".d")]
        if order != list(range(len(r))):
            f, r = [f[i] for i in order], [r[i] for i in order]
            bgi = order.index(bgi) if bgi is not None else None
            dirty = True
    return {"f": f, "r": r, "bgi": bgi, "dirty": dirty}


# ---- Ansicht (HTML, Spiegel in web/check.js)

def _fill(tmpl, values):
    return re.sub(r"\{([a-z_]+)\}", lambda mt: values[mt.group(1)] if mt.group(1) in values else mt.group(0), tmpl)


def _num(R, tmpl):
    return C.render_text(tmpl, {"refs": R["refs"]}, R["lang"], False)[0]


def _cr(R, a, b):
    return _num(R, "{cr:" + a + "/" + b + "}")


def _dist(R, a, b, kind):
    return _num(R, "{dist:" + a + "/" + b + "/" + kind + "}")


def _code(hx):
    return "<code>" + hx + "</code>"


def _thr(x, lang):
    return X.fmt_threshold(x, lang)


def _role_name(R, rid):
    r = _role_def(R["cfg"], rid)
    return r["name_" + R["lang"]] if r else rid


def _plain(html):
    return X.unesc(re.sub(r"<[^>]*>", "", html))


def _ctx_label(R, m, cx):
    return C.esc(R["T"]["ctx." + cx["ctx"]]) if len(m["ctxs"]) > 1 else ""


def finding_message(R, m, f):
    """Messsatz eines Befunds als HTML (vertrauenswürdige Vorlage, Zahlen als <data>)."""
    T, cols = R["T"], m["colors"]
    hx = {g: cols[g]["eff"] for g in range(len(cols)) if "eff" in cols[g]}
    fid = f["id"]
    if fid in ("check-text", "check-nontext"):
        a, b = hx[f["i"]], hx[f["j"]]
        kind = "text" if fid == "check-text" else "nontext"
        key = "msg." + kind + "." + ("free" if f["cond"] == "free" else "role")
        out = _fill(T[key], {"a": _code(a), "b": _code(b), "ratio": _cr(R, a, b), "min": _thr(f["min"], R["lang"]),
                             "role": C.esc(_role_name(R, f["role"])) if f["role"] else ""})
        if f.get("open") and f["open"] != "free":
            out += " " + T["open." + f["open"]]
        return out
    if fid in ("check-duplicates", "check-cvd", "check-gray"):
        a, b = hx[f["i"]], hx[f["j"]]
        v = {"a": _code(a), "b": _code(b), "d": _dist(R, a, b, f["kind"]), "at": C.esc(R["T"]["at." + f["kind"]]),
             "okabe": _num(R, "{ref:" + R["cfg"]["compare"] + "}")}
        return _fill(T["msg." + fid[6:]], v)
    if fid == "check-neutral-missing":
        return T["msg.neutral-missing"]
    c = cols[f["i"]]
    if fid == "check-gamut":
        return _fill(T["msg.gamut"], {"raw": _code(C.esc(c["raw"])), "a": _code(c["hex"]), "d": C.fmt_dist(c["md"] or 0.0, R["lang"])})
    return _fill(T["msg.alpha"], {"raw": _code(C.esc(c["raw"])), "a": _code(c["eff"])})


def repair_text(R, m, f):
    """Reparaturvorschlag als HTML ohne Knopf, oder "" ohne Reparatur."""
    T, rp = R["T"], f.get("repair")
    if rp is None:
        return ""
    if rp["to"] is None:
        key = "fix.none." + ("contrast" if f["id"] in ("check-text", "check-nontext") else "distance")
        return _fill(T[key], {"link": '<a href="' + R["paths"]["charts"] + '">' + C.esc(T["fix.charts"]) + "</a>"})
    cols = m["colors"]
    a, b = rp["from"], rp["to"]
    if f["id"] in ("check-text", "check-nontext"):
        worst = None
        for o in f["on"]:
            r = C.contrast(b, cols[o]["eff"])
            if worst is None or r < worst[0] - 1e-12:
                worst = (r, o)
        return _fill(T["fix.contrast"], {"to": _code(b), "from": _code(a), "ratio": _cr(R, b, cols[worst[1]]["eff"]),
                                         "d": _dist(R, a, b, "normal")})
    o = cols[rp["other"]]["eff"]
    kind = f["kind"] if f["id"] != "check-cvd" else C.min_distance([b, o], C.WORST_KINDS)["kind"]
    return _fill(T["fix.distance"], {"to": _code(b), "from": _code(a), "dd": _dist(R, b, o, kind),
                                     "at": C.esc(T["at." + kind]), "d": _dist(R, a, b, "normal")})


def repair_html(R, m, f):
    txt = repair_text(R, m, f)
    if not txt:
        return ""
    rp = f["repair"]
    btn = ""
    if rp["to"] is not None:
        btn = f' <button type="button" class="btn js-only" data-apply="{rp["i"]}" data-to="{rp["to"]}">{C.esc(R["T"]["fix.apply"])}</button>'
    return f'<p class="fix">{txt}{btn}</p>'


def _rule_of(R, fid):
    fd = _finding_def(R["cfg"], fid)
    return R["rules"].get(fd["rule"]) if fd else None


def level_tags(R, obj):
    F = R["F"]
    tags = ['<span class="tag-level">' + C.esc(F["level." + obj["level"]]) + "</span>"]
    if obj.get("strength"):
        tags.append('<span class="tag-sub">' + C.esc(F["strength." + obj["strength"]]) + "</span>")
    if obj.get("myth"):
        tags.append('<span class="tag-sub">' + C.esc(F["myth"]) + "</span>")
    if obj.get("own"):
        tags.append('<span class="tag-sub">' + C.esc(F["own"]) + "</span>")
    return " ".join(tags)


def _short_src(R, rule):
    ids = (rule.get("normative") or []) + [i for i in rule.get("sources") or [] if i not in (rule.get("normative") or [])]
    for i in ids:
        s = R["sources"].get(i)
        if s:
            return s.get("short_" + R["lang"]) or s["title"]
    return ""


def why_text(R, m, f):
    """„Begründung kopieren“: ein Satz mit Zahl, Schwelle, Quelle und Link mit Zustand (reiner Text)."""
    rule = _rule_of(R, f["id"]) or {}
    return _plain(_fill(R["T"]["why"], {"msg": finding_message(R, m, f), "src": C.esc(_short_src(R, rule)), "url": C.esc(R["url"])}))


def finding_html(R, m, f, new_keys):
    T = R["T"]
    rule = _rule_of(R, f["id"])
    fd = _finding_def(R["cfg"], f["id"])
    head = f'<span class="sev">{SYM[f["sev"]]} {C.esc(T["sev." + f["sev"]])}</span>'
    if rule:
        head += " " + level_tags(R, rule) + ' <small class="f-src">' + C.esc(_short_src(R, rule)) + "</small>"
    new = f["key"] in new_keys
    if new:
        head += ' <span class="tag-sub f-new">' + C.esc(T["new"]) + "</span>"
    more = ""
    if fd and fd.get("explain"):
        more = f' <a class="more-link" href="{R["paths"]["explained"]}#{fd["explain"]}">{C.esc(R["F"]["more_about"])}</a>'
    return (f'<li class="finding" data-sev="{f["sev"]}" data-key="{C.esc(f["key"])}"{" data-new" if new else ""}>'
            f'<div class="finding-h">{head}</div><p>{finding_message(R, m, f)}</p>{repair_html(R, m, f)}'
            f'<p class="f-links"><button type="button" class="btn" data-copy="{C.esc(why_text(R, m, f))}">{C.esc(T["why_btn"])}</button>{more}</p></li>')


def pass_html(R, m, p):
    cols = m["colors"]
    a, b = cols[p["i"]]["eff"], cols[p["j"]]["eff"]
    key = "pass." + ("text" if p["id"] == "check-text" else "nontext")
    role = (" (" + C.esc(_role_name(R, p["role"])) + ")") if p["role"] else ""
    return "<li>" + SYM["pass"] + " " + _fill(R["T"][key], {"a": _code(a), "b": _code(b), "role": role, "ratio": _cr(R, a, b),
                                                         "min": _thr(p["min"], R["lang"])}) + "</li>"


def _roles_block(R, m, cx):
    T, cols = R["T"], m["colors"]
    items = []
    for g in cx["idx"]:
        c = cols[g]
        name = ", ".join("--" + C.esc(x) for x in c["names"]) or _code(c["hex"])
        if c["names"]:
            name = "<code>" + name + "</code>"
        opts = '<option value="-"' + (" selected" if not c["role"] else "") + ">" + C.esc(T["roles.none"]) + "</option>"
        for r in R["cfg"]["roles"]:
            opts += f'<option value="{r["id"]}"' + (" selected" if c["role"] == r["id"] else "") + ">" + C.esc(r["name_" + R["lang"]]) + "</option>"
        lab = C.esc(_fill(T["roles.menu_l"], {"name": _plain(name)}))
        tag = ' <span class="tag-sub">' + C.esc(T["roles.suggest"]) + "</span>" if c["role"] and c["role_src"] != "confirmed" else ""
        items.append(f'<li><span class="swatch" style="background:{c["eff"]}"></span><span class="rl-n">{name}</span>'
                     f'<span class="rl-arrow" aria-hidden="true">→</span><select class="rl-sel" data-role="{g}" aria-label="{lab}">{opts}</select>{tag}</li>')
    btn = ("<p class=\"hint\">" + C.esc(T["roles.confirmed"]) + "</p>") if m["confirmed"] else \
        f'<button type="button" class="btn primary js-only" data-confirm>{C.esc(T["roles.confirm"])}</button>'
    return (f'<section class="chk-blk"><h3>{C.esc(T["roles.h"])}</h3><p class="hint">{C.esc(T["roles.intro"])}</p>'
            f'<ul class="chk-roles">{"".join(items)}</ul>{btn}</section>')


def _bg_block(R, m, cx):
    T, cols = R["T"], m["colors"]
    chips = "".join(f'<button type="button" class="chip chk-bg" data-bgi="{g}" aria-pressed="{"true" if g == cx["bg"] else "false"}">'
                    f'<span class="sw" style="background:{cols[g]["eff"]}"></span>{cols[g]["eff"]}</button>' for g in cx["idx"])
    lid = "chk-bg-" + cx["ctx"]
    return (f'<section class="chk-blk"><h3 id="{lid}">{C.esc(T["bg.h"])}</h3>'
            f'<div class="chips" role="group" aria-labelledby="{lid}">{chips}</div></section>')


def _bar_block(R, m, cx, changed):
    T, cols, lang = R["T"], m["colors"], R["lang"]
    rows = []
    for g in cx["idx"]:
        c = cols[g]
        best = c["best"]
        bt = _fill(T["bar.best." + ("white" if best == "#FFFFFF" else "black")], {"ratio": _cr(R, best, c["eff"])})
        notes = []
        if c["role"]:
            notes.append(C.esc(_role_name(R, c["role"])) + (" (" + C.esc(T["roles.suggest"]) + ")" if c["role_src"] != "confirmed" else ""))
        if g == cx["bg"] and c["role"] != "bg":
            notes.append(C.esc(T["bar.isbg"]))
        if c["oog"]:
            notes.append(_fill(T["bar.gamut"], {"d": C.fmt_dist(c["md"] or 0.0, lang)}))
        if c["alpha"] < 1:
            notes.append(_fill(T["bar.alpha"], {"color": _code(c["hex"])}))
        undo = ""
        if g in changed:
            undo = f' <button type="button" class="btn" data-undo>{C.esc(T["bar.undo"])}</button>'
        ok = f'<code class="ok">{c["oklch"]}</code>' if c["oklch"] else ""
        note = '<small class="bar-note">' + " · ".join(notes) + "</small>" if notes else ""
        rows.append(f'<li class="bar-row"><span class="swatch" style="background:{c["eff"]}"></span>'
                    f'<span class="bar-t"><code class="hex">{c["eff"]}</code> {ok}<small>{bt}</small>{note}</span>'
                    f'<span class="bar-act"><button type="button" class="btn icon" data-copy="{c["eff"]}" aria-label="{C.esc(_fill(T["bar.copy_l"], {"value": c["eff"]}))}">'
                    f'{COPY_ICON}</button>{undo}</span></li>')
    return f'<section class="chk-blk"><h3>{C.esc(T["bar.h"])}</h3><ul class="chk-bar">{"".join(rows)}</ul></section>'


COPY_ICON = ('<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
             '<path d="M5 1h9v11H5z M2 4h2v1H3v9h8v-1h1v2H2z" fill="currentColor"/></svg>')


def _cls(r):
    return "t" if r >= 4.5 else "g" if r >= 3 else "d"


def _matrix_block(R, m, cx):
    T, cols = R["T"], m["colors"]
    idx = cx["idx"]
    if len(idx) < 2:
        return ""
    ctx = cx["ctx"]
    head = "".join(f'<th scope="col"><span class="sw" style="background:{cols[g]["eff"]}"></span><code>{cols[g]["eff"]}</code></th>' for g in idx)
    rows = []
    for a in idx:
        cells = []
        for b in idx:
            if a == b:
                cells.append('<td class="mx-d">–</td>')
                continue
            r = C.contrast(cols[a]["eff"], cols[b]["eff"])
            k = _cls(r)
            cells.append(f'<td class="mx-{k}">{_cr(R, cols[a]["eff"], cols[b]["eff"])}<small>{C.esc(T["mx." + k])}</small></td>')
        rows.append(f'<tr><th scope="row"><span class="sw" style="background:{cols[a]["eff"]}"></span><code>{cols[a]["eff"]}</code></th>{"".join(cells)}</tr>')
    legend = " · ".join(f'<span class="mx-{k}">{C.esc(T["mx.legend." + k])}</span>' for k in ("t", "g", "d"))
    picks = "".join(f'<button type="button" class="chip" data-mxpick="{g}" aria-pressed="{"true" if i == 0 else "false"}">'
                    f'<span class="sw" style="background:{cols[g]["eff"]}"></span>{cols[g]["eff"]}</button>' for i, g in enumerate(idx))
    lists = []
    for i, a in enumerate(idx):
        li = []
        for b in idx:
            if a == b:
                continue
            r = C.contrast(cols[a]["eff"], cols[b]["eff"])
            li.append(f'<li><span class="sw" style="background:{cols[b]["eff"]}"></span><code>{cols[b]["eff"]}</code> '
                      f'{_cr(R, cols[a]["eff"], cols[b]["eff"])} <small class="mx-{_cls(r)}">{C.esc(T["mx." + _cls(r)])}</small></li>')
        lists.append(f'<ul class="mx-list plain{" on" if i == 0 else ""}" data-mxlist="{a}">{"".join(li)}</ul>')
    return (f'<section class="chk-blk chk-mx"><h3>{C.esc(T["mx.h"])}</h3><p class="hint">{legend}</p>'
            f'<div class="mx-wide" role="region" tabindex="0" aria-label="{C.esc(T["mx.h"])}"><table class="mx"><thead><tr><td></td>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<div class="mx-narrow"><span class="ctl-label" id="mx-pick-{ctx}">{C.esc(T["mx.pick"])}</span>'
            f'<div class="chips js-only" role="group" aria-labelledby="mx-pick-{ctx}">{picks}</div>{"".join(lists)}</div></section>')


def _sim_block(R, m, cx):
    T, F, cols = R["T"], R["F"], m["colors"]
    rows = []
    for k in KINDS_SIM:
        cells = "".join(f'<span style="background:{C.sim_hex(cols[g]["eff"], k)}"></span>' for g in cx["idx"])
        rows.append(f'<div class="sim-row"><span class="sim-k">{C.esc(F["sim." + k])}</span><div class="strip" aria-hidden="true">{cells}</div></div>')
    return (f'<section class="chk-blk"><h3>{C.esc(T["sim.h"])}</h3>{"".join(rows)}'
            f'<p class="sim-note">{C.esc(F["sim_note"])}</p></section>')


def _dist_block(R, m, cx):
    T, F, cols = R["T"], R["F"], m["colors"]
    if len(cx["set"]) < 2:
        return f'<section class="chk-blk"><h3>{C.esc(T["dist.h"])}</h3><p class="hint">{C.esc(T["dist.none"])}</p></section>'
    cols_html = []
    for k in KINDS_DIST:
        li = "".join(f'<li><span class="sw" style="background:{cols[d["a"]]["eff"]}"></span><span class="sw" style="background:{cols[d["b"]]["eff"]}"></span>'
                     f'<code>{cols[d["a"]]["eff"]}/{cols[d["b"]]["eff"]}</code> {_dist(R, cols[d["a"]]["eff"], cols[d["b"]]["eff"], k)}</li>'
                     for d in cx["dist"][k])
        cols_html.append(f'<div class="dist-k"><h4>{C.esc(F["sim." + k])}</h4><ol class="plain">{li}</ol></div>')
    refs = " · ".join(C.esc(c["name_" + R["lang"]]) + " " + _num(R, "{ref:" + c["id"] + "}") for c in R["comparisons"])
    return (f'<section class="chk-blk"><h3>{C.esc(T["dist.h"])}</h3><p class="hint">{C.esc(T["dist.intro"])}</p>'
            f'<div class="dist-grid">{"".join(cols_html)}</div><p class="muted">{_fill(F["distinct.refs"], {"list": refs})}</p></section>')


def _findings_block(R, m, cx, new_keys):
    T = R["T"]
    fs = cx["findings"]
    lim = R["cfg"]["open_findings"]
    head = f'<h3>{C.esc(T["f.h"])}</h3>'
    if not fs:
        body = f'<p>{C.esc(T["f.none"])}</p>'
    else:
        body = '<ul class="findings">' + "".join(finding_html(R, m, f, new_keys) for f in fs[:lim]) + "</ul>"
        if len(fs) > lim:
            # Zählform wie in.count1: eigener Text für genau eins („1 weiterer Befund“)
            more = _fill(T["f.more_1" if len(fs) - lim == 1 else "f.more"], {"n": C.render_text("{count:n}", {"counts": {"n": len(fs) - lim}}, R["lang"], False)[0]})
            body += (f'<details class="f-more"><summary>{more}</summary><ul class="findings">'
                     + "".join(finding_html(R, m, f, new_keys) for f in fs[lim:]) + "</ul></details>")
    ps = cx["passes"]
    if ps:
        summ = _fill(T["f.passed"], {"n": C.render_text("{count:n}", {"counts": {"n": len(ps)}}, R["lang"], False)[0]})
        body += f'<details class="f-pass"><summary>{summ}</summary><ul class="plain">{"".join(pass_html(R, m, p) for p in ps)}</ul></details>'
    return f'<section class="chk-blk chk-f">{head}{body}</section>'


def _notes_html(R, m):
    T, out = R["T"], []
    for n in m["notes"]:
        if n["key"] == "var":
            out.append(_fill(T["note.var"], {"name": _code("--" + C.esc(n["name"])), "target": _code("--" + C.esc(n["ref"]))}))
        elif n["key"] == "dropped":
            out.append(_fill(T["note.dropped_1" if n["n"] == 1 else "note.dropped"], {"n": C.render_text("{count:n}", {"counts": {"n": n["n"]}}, R["lang"], False)[0],
                                                 "max": C.render_text("{count:n}", {"counts": {"n": R["cfg"]["max_colors"]}}, R["lang"], False)[0],
                                                 "ctx": C.esc(T["ctx." + n["ctx"]])}))
    return "".join(f'<p class="note" role="note">{x}</p>' for x in out)


def most_colorful(m):
    best = None
    for g, c in enumerate(m["colors"]):
        if "chroma" in c and (best is None or c["chroma"] > m["colors"][best]["chroma"] + 1e-12):
            best = g
    return m["colors"][best]["eff"] if best is not None else None


def render(m, R, opts=None):
    """HTML aller Ergebnisblöcke. opts: {new_keys: [..], changed: [g], example: bool}."""
    opts = opts or {}
    new_keys = set(opts.get("new_keys") or [])
    changed = set(opts.get("changed") or [])
    T = R["T"]
    out = []
    if opts.get("example"):
        out.append(f'<p class="note chk-example">{_fill(T["example"], {"colors": _code(C.esc(R["cfg"]["example"]))})}</p>')
    out.append(_notes_html(R, m))
    if not m["ctxs"]:
        out.append(f'<p class="hint">{C.esc(T["empty"])}</p>')
        return "".join(out)
    F = R["F"]
    out.append(f'<div class="pal-act"><button type="button" class="btn primary" data-copy-from="#exp-report-0">'
               f'{C.esc(_fill(F["copy_fmt"], {"fmt": F["fmt.report.inline"]}))}</button><a class="more-link" href="#kopieren">{C.esc(F["all_fmts"])}</a></div>')
    if len(m["ctxs"]) > 1:
        chips = "".join(f'<button type="button" class="chip" data-ctxpick="{cx["ctx"]}" aria-pressed="{"true" if i == 0 else "false"}">'
                        f'{C.esc(T["ctx." + cx["ctx"]])}</button>' for i, cx in enumerate(m["ctxs"]))
        out.append(f'<div class="chips js-only chk-ctxpick" role="group" aria-label="{C.esc(T["ctx_l"])}">{chips}</div>')
    for cx in m["ctxs"]:
        lab = _ctx_label(R, m, cx)
        out.append(f'<div class="chk-ctx" data-ctx="{cx["ctx"]}">' + (f'<h2 class="ctx-h">{lab}</h2>' if lab else ""))
        if m["has_names"]:
            out.append(_roles_block(R, m, cx))
        out.append(_bg_block(R, m, cx))
        out.append(_bar_block(R, m, cx, changed))
        out.append(_matrix_block(R, m, cx))
        out.append(_sim_block(R, m, cx))
        out.append(_dist_block(R, m, cx))
        out.append(_findings_block(R, m, cx, new_keys))
        out.append("</div>")
    return "".join(out)


# ---- Exporte

def _sec_lines(R, m, cx, sev):
    out = []
    for f in cx["findings"]:
        if f["sev"] != sev:
            continue
        line = "- " + SYM[sev] + " " + _plain(finding_message(R, m, f))
        fix = repair_text(R, m, f)
        if fix:
            line += "\n  " + _plain(fix)
        out.append(line)
    return out


def report(m, R):
    """Prüfbericht als Markdown: Kopf mit Datum und Link, Verfehlt, Prüfen, Hinweise, Erfüllt, Fußzeile."""
    T, lang = R["T"], R["lang"]
    out = ["# " + T["rep.title"], "", _fill(T["rep.head"], {"date": R["date"], "url": R["url"]})]
    roles = T["rep.roles." + ("confirmed" if m["confirmed"] else "guess" if any(c["role"] for c in m["colors"]) else "none")]
    out.append(roles)
    for cx in m["ctxs"]:
        cols = m["colors"]
        pre = (T["ctx." + cx["ctx"]] + ": ") if len(m["ctxs"]) > 1 else ""
        out += ["", "## " + pre + T["rep.colors"],
                ", ".join(cols[g]["eff"] + (" (" + _role_name(R, cols[g]["role"]) + ")" if cols[g]["role"] else "") for g in cx["idx"]),
                _fill(T["rep.bg"], {"color": cols[cx["bg"]]["eff"]})]
        for sev in SEVS:
            lines = _sec_lines(R, m, cx, sev)
            out += ["", "## " + pre + T["rep." + sev] + " (" + C.fmt_count(len(lines), lang) + ")"]
            out += lines or ["- " + T["rep.empty"]]
        ps = [("- " + _plain(pass_html(R, m, p))) for p in cx["passes"]]
        out += ["", "## " + pre + T["rep.pass"] + " (" + C.fmt_count(len(ps), lang) + ")"] + (ps or ["- " + T["rep.empty"]])
    refs = " · ".join(c["name_" + lang] + " " + _plain(_num(R, "{ref:" + c["id"] + "}")) for c in R["comparisons"])
    out += ["", "---", T["rep.sim"], _fill(R["F"]["distinct.refs"], {"list": refs}),
            T["rep.not_checked"] + " " + ", ".join(T["not_checked"]) + ".", T["rep.license"]]
    return "\n".join(out)


def hexlist(m, R):
    T, cols = R["T"], m["colors"]
    parts = []
    for cx in m["ctxs"]:
        head = _fill(T["hex.head"], {"date": R["date"]}) + ((" · " + T["ctx." + cx["ctx"]].lower()) if len(m["ctxs"]) > 1 else "")
        names = [(cols[g]["names"][0] if cols[g]["names"] else (cols[g]["role"] or "")) for g in cx["idx"]]
        w = max([len(x) for x in names] + [0]) + 2
        rows = []
        for g, nm in zip(cx["idx"], names):
            c = cols[g]
            rows.append((nm.ljust(w) if w > 2 else "") + c["eff"] + ("  " + _role_name(R, c["role"]) if c["role"] else ""))
        parts.append("\n".join([head] + rows))
    return "\n\n".join(parts) + "\n\n" + _fill(T["hex.link"], {"url": R["url"]})


def css(m, R):
    """CSS mit Rollen (nur wenn Rollen vergeben sind), dunkler Kontext über prefers-color-scheme wie der CSS-Export in tools/export.py."""
    T, cols = R["T"], m["colors"]
    lines = ["/* " + _fill(T["hex.head"], {"date": R["date"]}), "   " + T["css.checked"], "   " + _fill(T["hex.link"], {"url": R["url"]}) + " */"]
    for k, cx in enumerate(m["ctxs"]):
        rows, used = [], set()
        for g in cx["idx"]:
            c = cols[g]
            nm = c["names"][0] if c["names"] else c["role"]
            if not nm:
                continue
            nm = _uniq(nm, used)  # jede geprüfte Farbe bleibt adressierbar (keine doppelte Custom Property)
            note = " · ".join(x for x in (c["oklch"], _role_name(R, c["role"]) if c["role"] else None) if x)
            rows.append((nm, c["eff"], note))
        if not rows:
            continue
        w = max(len(x[0]) for x in rows) + 3
        ind = "  " if cx["ctx"] == "light" else "    "
        if cx["ctx"] == "light":
            lines.append(":root {")
        else:
            lines += ["@media (prefers-color-scheme: dark) {", "  :root {"]
        for nm, hx, note in rows:
            lines.append(ind + ("--" + nm + ":").ljust(w + 1) + hx + ";" + (" /* " + note.replace("*/", "* /") + " */" if note else ""))
        lines.append("}" if cx["ctx"] == "light" else "  }")
        if cx["ctx"] != "light":
            lines.append("}")
    return "\n".join(lines)


def has_css(m):
    """CSS gibt es nur mit Rollen."""
    return any(c["role"] for c in m["colors"])


def exports(m, R):
    """Exportblöcke {fmt: text} in der Reihenfolge der Reiter: Prüfbericht, Hex-Liste, CSS (nur mit Rollen)."""
    out = [("report", report(m, R)), ("hex", hexlist(m, R))]
    if has_css(m):
        out.append(("css", css(m, R)))
    return out


def export_html(m, R):
    """Block 9: Reiter, <pre>, Kopieren, Speichern, Umbrechen und „In Aufgabe öffnen“."""
    T, F = R["T"], R["F"]
    ex = exports(m, R)
    tabs = "".join(f'<button type="button" role="tab" class="tab" id="tab-{f}" data-tab="{f}" aria-controls="panel-{f}" '
                   f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=\"-1\""}>{C.esc(F["fmt." + f])}</button>'
                   for i, (f, _) in enumerate(ex))
    panels = []
    for i, (f, text) in enumerate(ex):
        pid = "exp-" + f + "-0"
        name, mime = X.filename("check", None, f), X.mime(f)  # Schema: farbsprache-check-eigen.<ext>
        panels.append(f'<div class="tabpanel{" on" if i == 0 else ""}" id="panel-{f}" role="tabpanel" aria-labelledby="tab-{f}">'
                      f'<h3 class="panel-h">{C.esc(F["fmt." + f])}</h3>'
                      f'<pre class="code" id="{pid}" tabindex="0"><code>{C.esc(text)}</code></pre>'
                      f'<div class="exp-act"><button type="button" class="btn primary" data-copy-from="#{pid}">{C.esc(F["copy"])}</button>'
                      f'<button type="button" class="btn js-only" data-download="#{pid}" data-filename="{name}" data-mime="{mime}">{C.esc(F["download"])}</button>'
                      f'<button type="button" class="btn js-only" data-wrap="#{pid}" aria-pressed="false">{C.esc(F["wrap"])}</button></div></div>')
    hx = most_colorful(m)
    links = ""
    if hx:
        links = (f'<h3>{C.esc(T["open.h"])}</h3><ul class="next">'
                 + "".join(f'<li><a href="{R["paths"][t]}?c={hx[1:]}">{_fill(C.esc(T["open." + t]), {"color": hx})}</a></li>'
                           for t in ("website", "charts")) + "</ul>")
    return (f'<div class="tabs" role="tablist" aria-label="{C.esc(F["fmts_l"])}">{tabs}</div>{"".join(panels)}{links}')


# ---- Kommandozeile (für tests/check.test.cjs: Python-Seite des Paritätsvergleichs)

def _root():
    return Path(__file__).resolve().parent.parent


def _load_cfg():
    return json.loads((_root() / "data" / "check.json").read_text(encoding="utf-8"))


def test_context(lang, cfg=None):
    """Kontext R wie auf der Seite, aus den Dateien des Projekts (nur für Tests und den Kommandozeilenteil)."""
    import importlib.util
    root = _root()

    def copy(name):
        spec = importlib.util.spec_from_file_location("fs_copy_" + name, root / "web" / "copy" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.COPY

    def items(kind, key):
        out = {}
        for f in sorted((root / "data" / kind).glob("*.json")):
            for it in json.loads(f.read_text(encoding="utf-8"))[key]:
                out[it["id"]] = it
        return out
    cfg = cfg or _load_cfg()
    core = copy("core")
    return {"lang": lang, "T": copy("check")[lang]["check"], "F": core[lang]["frame"], "refs": C.reference_values(), "cfg": cfg,
            "rules": items("rules", "rules"), "sources": items("sources", "sources"),
            "comparisons": json.loads((root / "data" / "comparisons.json").read_text(encoding="utf-8"))["comparisons"],
            "paths": {"explained": "../erklaert/", "website": "../website/", "charts": "../diagramm/"},
            "url": "https://grundhofer.github.io/farbsprache/" + lang + "/test/", "date": "2026-10-11"}


def dump(cases, cfg=None, html=False):
    """Modelle für Testeingaben → JSON-taugliche Liste (Farben, Rollen, Befunde, Reparaturen, Erfüllt).
    html=True rendert zusätzlich Ergebnis und Exporte in beiden Sprachen (Kontext test_context)."""
    cfg = cfg or _load_cfg()
    refs = C.reference_values()
    Rs = {lang: test_context(lang, cfg) for lang in ("de", "en")} if html else {}
    out = []
    for case in cases:
        sc = scan(case["text"], cfg)
        m = analyze(sc, cfg, refs, case.get("state"))
        o = {"scan": sc, "model": _strip_model(m), "query": query(m, (case.get("state") or {}).get("bgi"))}
        for lang, R in Rs.items():
            o["html_" + lang] = render(m, R, case.get("opts"))
            o["exp_" + lang] = export_html(m, R)
        out.append(o)
    return out


def _strip_model(m):
    def fin(f):
        return {k: f.get(k) for k in ("id", "sev", "i", "j", "key", "value", "kind", "open", "repair") if k in f}
    return {"colors": [{k: c.get(k) for k in ("hex", "eff", "alpha", "role", "role_src", "ctx", "oklch", "best", "chroma")} for c in m["colors"]],
            "ctxs": [{"ctx": cx["ctx"], "bg": cx["bg"], "set": cx["set"], "findings": [fin(f) for f in cx["findings"]],
                      "passes": [fin(p) for p in cx["passes"]], "dist": cx["dist"]} for cx in m["ctxs"]],
            "confirmed": m["confirmed"], "has_names": m["has_names"], "notes": m["notes"]}


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--dump":
        cases = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        if sys.argv[3:] == ["--html"]:
            res = {"R": {lang: test_context(lang) for lang in ("de", "en")}, "res": dump(cases, html=True)}
        else:
            res = dump(cases)
        sys.stdout.write(json.dumps(res, ensure_ascii=False, allow_nan=False))
    else:
        sys.exit("Aufruf: python3 tools/check.py --dump FAELLE.json [--html]")
