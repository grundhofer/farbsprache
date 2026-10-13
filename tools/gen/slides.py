"""Generator der Aufgabe Präsentation. Spiegel von web/gen/slides.js.

build(task, inp, ctx) -> Palettenobjekt mit einem Modus „default“. Der Folienhintergrund (bg) wählt die
Werte für hell oder dunkel, das Raumlicht (room) wirkt nur auf den projizierten Kontrast und
die Ansicht „Beamer“ (view_vars). Textrollen bekommen 10 % Reserve (7,7 statt 7, 3,3 statt 3), Diagrammfarben
kommen aus Okabe-Ito mit mindestens 3:1 auf der Folie und starten mit dem Akzent (pick_distinct).
Aufgabenspezifische Exporte: Hex-Liste in der Reihenfolge des Office-Farbschemas und Begründung mit dem
projizierten Kontrast beim gewählten Raumlicht.
"""
from tools import color as C, export as X

LIGHT_T = 7.7    # 7:1 plus 10 % Reserve, als Literal wegen 7.0 * 1.1
LINE_T = 3.3
DARK_C = 0.85    # Buntheit des Akzents im dunklen Modus, wie DARK_C in tools/gen/website.py
OFFICE = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink",
          "folHlink")
CHARTS = ("chart-1", "chart-2", "chart-3", "chart-4")


def _tint(cs):
    """Tönung t wie „tinted“ in der Aufgabe Website oder App."""
    return min(max(0.1 * cs, 0.004), 0.012)


def _solve(c, h, against, target, direction, l0):
    """solve_l mit Startwert L0; liegt die Startfarbe auf der falschen Seite der Flächen (mixed-sides), startet
    die Suche bei L 0,5. Das Ergebnis ist dieselbe Grenze, nur der Startpunkt wandert (so bleiben sehr helle
    bzw. sehr dunkle eigene Farben lösbar)."""
    try:
        return C.solve_l(c, h, against, target, direction, l0)
    except C.SolveError as e:
        if e.key != "mixed-sides":
            raise
        return C.solve_l(c, h, against, target, direction, 0.5)


def okabe_colors(ctx):
    ds = ctx["datasets"]["okabe-ito"]
    scheme = next(s for s in ds["schemes"] if s["id"] == "okabe-ito")
    return [c["hex"] for c in scheme["colors"] if c["name"] != "black"]


def _office(roles):
    """Office-Plätze dk1 … folHlink → Rollen. Akzent 2 bis 4 sind die Diagrammfarben ohne den Akzent;
    fehlt eine, steht dort text-2."""
    extra = [rid for rid in CHARTS if rid in roles and roles[rid] != roles["accent"]][:3]
    while len(extra) < 3:
        extra.append("text-2")
    rids = ["text", "slide", "text-2", "slide-2", "accent"] + extra + ["text-2", "line", "accent-text", "text-2"]
    return [{"slot": s, "role": r} for s, r in zip(OFFICE, rids)]


def build(task, inp, ctx):
    o = inp["options"]
    seed = inp["seed"]
    bg, room, pr = o["bg"], o["room"], bool(o["pr"])
    ls, cs, h = C.hex_to_oklch(seed)
    if h is None:
        h, t = 0.0, 0.0
    else:
        t = _tint(cs)
    r = {}
    changes, findings = [], []
    if bg == "dark":
        r["slide"] = C.oklch_to_hex(0.20, t, h)
        r["slide-2"] = C.oklch_to_hex(0.25, t, h)
        surf = [r["slide"], r["slide-2"]]
        r["text"] = _solve(0.6 * t, h, surf, LIGHT_T, 1, 0.94)["hex"]
        r["text-2"] = _solve(t, h, surf, 7.0, 1, 0.80)["hex"]
        r["line"] = _solve(t, h, [r["slide"]], LINE_T, 1, 0.45)["hex"]
        ca = DARK_C * cs
        cand = C.oklch_to_hex(ls, ca, h)
        if C.contrast(cand, r["slide"]) >= 3.0:
            r["accent"], key = cand, "accent-dark"
        else:
            r["accent"], key = _solve(ca, h, [r["slide"]], 3.0, 1, ls)["hex"], "accent-lighter"
        r["accent-text"] = _solve(ca, h, surf, 7.0, 1, ls)["hex"]
    else:
        r["slide"] = C.oklch_to_hex(0.985, 0.4 * t, h)
        r["slide-2"] = C.oklch_to_hex(0.95, 0.6 * t, h)
        surf = [r["slide"], r["slide-2"]]
        r["text"] = _solve(1.6 * t, h, surf, LIGHT_T, -1, 0.24)["hex"]
        r["text-2"] = _solve(1.4 * t, h, surf, 7.0, -1, 0.45)["hex"]
        r["line"] = _solve(1.4 * t, h, [r["slide"]], LINE_T, -1, 0.70)["hex"]
        if C.contrast(seed, r["slide"]) >= 3.0:
            r["accent"], key = seed, None
        else:
            r["accent"], key = _solve(cs, h, [r["slide"]], 3.0, -1, ls)["hex"], "accent-darker"
        r["accent-text"] = _solve(cs, h, surf, 7.0, -1, ls)["hex"]
    if r["accent"] != seed:
        changes.append({"role": "accent", "mode": "default", "from": seed, "to": r["accent"], "key": key or "accent-darker",
                        "values": {"before": C.contrast(seed, r["slide"]), "after": C.contrast(r["accent"], r["slide"])}})
    if r["accent-text"] != seed:
        # Auf dunklem Grund geht die Textvariante vom Akzent mit 0,85-facher Chroma aus; der Hinweis sagt das.
        changes.append({"role": "accent-text", "mode": "default", "from": seed, "to": r["accent-text"],
                        "key": "accent-text-dark" if bg == "dark" else "accent-text",
                        "values": {"before": C.contrast(seed, r["slide"]), "after": C.contrast(r["accent-text"], r["slide-2"])}})
    # Diagrammfarben: Akzent zuerst, dann Okabe-Ito mit mindestens 3:1 auf der Folie (bei Druck mit Graustufen)
    okabe = okabe_colors(ctx)
    pool = [r["accent"]] + [x for x in okabe if C.contrast(x, r["slide"]) >= 3.0]
    kinds = list(C.WORST_KINDS) + (["gray"] if pr else [])
    picked = C.pick_distinct(pool, 4, kinds, r["accent"], r["slide"])
    for i, hx in enumerate(picked):
        r[CHARTS[i]] = hx
    roles = {"default": r}
    ev = C.evaluate(task, roles, "skip")
    if bg == "dark":
        findings.append({"id": "dark-slide", "mode": None, "severity": "note", "values": {}})
    if room == "bright":
        findings.append({"id": "bright-room", "mode": None, "severity": "note",
                         "values": {"projected": C.projected_contrast(r["text"], r["slide"], room)}})
    if len(picked) < 4:
        findings.append({"id": "few-chart-colors", "mode": None, "severity": "note", "values": {"count": len(picked)}})
    distinct = []
    charts = [r[rid] for rid in CHARTS if rid in r]
    if len(charts) >= 2:
        md = C.min_distance(charts, ["normal", "deutan", "protan"])
        distinct.append({"id": "chart", "mode": "default", "value": md["value"], "a": CHARTS[md["i"]], "b": CHARTS[md["j"]],
                         "kind": md["kind"], "compare": {"id": "okabe-ito-7"}})
        if pr:
            mg = C.min_distance(charts, ["gray"])
            distinct.append({"id": "chart-gray", "mode": "default", "value": mg["value"], "a": CHARTS[mg["i"]],
                             "b": CHARTS[mg["j"]], "kind": "gray"})
    usage = {"default": {}}
    for rid in ("accent",) + CHARTS:
        if rid in r:
            k = C.contrast(r[rid], r["slide"])
            usage["default"][rid] = "text" if k >= 4.5 else "lines" if k >= 3.0 else "area"
    oset = set(okabe)
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": distinct, "changes": changes, "findings": findings, "usage": usage,
            "extra": {"datasets": {"okabe-ito": [rid for rid in CHARTS if rid in r and r[rid] in oset]},
                      "summary": ["summary." + room], "pair_note": "pair." + room, "office": _office(r)}}


def view_vars(palette, mode, toggles):
    """Muster-Schalter „Beamer“: jede Farbe nach dem Beamer-Modell beim gewählten Raumlicht. Die
    Modellbeschriftung bleibt in den Bildschirmfarben (cap-text auf cap-bg), damit sie auch im hellen Raum lesbar ist."""
    if toggles.get("view") != "projector":
        return {}
    room = palette["input"]["options"]["room"]
    roles = palette["roles"][mode]
    out = {rid: C.projector_hex(hx, room) for rid, hx in roles.items()}
    out["cap-text"], out["cap-bg"] = roles["text"], roles["slide"]
    return out


# ---- Exporte

def _menu_note(task, ctx, lang):
    """Drei Sätze „So trägst du die Farben ein“ aus task.menu_paths (außerhalb des Kopiertexts)."""
    tx = ctx["text"]
    out = ["<b>" + C.esc(tx["menu.h"]) + "</b>"]
    for m in task.get("menu_paths") or []:
        line = "<b>" + C.esc(m["app"]) + ":</b> " + C.esc(m["text_" + lang])
        if m.get("checked"):
            line += " <small>" + tx["menu.checked"].replace("{date}", C.esc(m["checked"])).replace("{url}", C.esc(m["url"])) + "</small>"
        out.append(line)
    return "<br>".join(out)


def _hex(palette, task, ctx, lang, opts=None):
    """Hex-Liste in der Reihenfolge des Office-Farbschemas."""
    tx = ctx["text"]
    roles = palette["roles"]["default"]
    by_id = {r["id"]: r for r in task["roles"]}
    rows = palette["extra"]["office"]
    labels = [tx["office." + x["slot"]] for x in rows]
    width = max(len(s) for s in labels) + 2
    lines = [X.header(ctx), tx["office.intro"]]
    if palette["input"]["options"]["bg"] == "dark":
        lines.append(tx["office.dark"])
    lines.append("")
    for x, lab in zip(rows, labels):
        lines.append(lab.ljust(width) + roles[x["role"]] + "  " + X.css_name(by_id[x["role"]]))
    lines.append("")
    lines += X.notices(palette, ctx, task, opts)
    lines.append(X.presub(ctx["core"]["link"], ctx))
    return [{"label": None, "text": "\n".join(lines), "suffix": "", "lang": None, "note": _menu_note(task, ctx, lang)}]


def _rationale(palette, task, ctx, lang, opts=None):
    """Begründung mit dem Folienhintergrund und dem projizierten Kontrast beim gewählten Raumlicht."""
    tx = ctx["text"]
    o = palette["input"]["options"]
    rc = X.rctx(palette, None, None, ctx)
    keys = ["rationale.bg." + o["bg"]]
    parts = [X.plain(X.presub(tx[keys[0]], ctx), rc, lang)]
    for e in tx["rationale"]:
        if isinstance(e, dict):
            if not X.show_if(e.get("show_if"), palette):
                continue
            e = e["text"]
        parts.append(X.plain(X.presub(e, ctx), rc, lang))
    if o["pr"]:
        parts.append(X.plain(X.presub(tx["rationale.pr"], ctx), rc, lang))
    parts.append(X.plain(X.presub(tx["rationale.proj." + o["room"]], ctx), rc, lang))
    parts.append(X.presub(ctx["core"]["rationale_end"], ctx))
    return " ".join(parts + X.notices(palette, ctx, task, opts))


exports = {"hex": _hex, "rationale": _rationale}
