"""Generator der Aufgabe Logo und Marke (Spiegel von web/gen/brand.js, Spezifikation 3.5, 4.6, 5.8).

Steckbrief einer Markenfarbe: Schriftfarbe darauf (Weiß oder Schwarz, der höhere Kontrast), Textvarianten auf Weiß
und auf #16191D per solve_l bei gleichem Farbton und gleicher Chroma, Graustufe nach 4.1.6, optional eine zweite
Markenfarbe mit Kontrast und Abständen. Die Markenfarbe selbst bleibt immer unverändert; abgeleitete Textvarianten
melden sich als Änderungshinweis. Vertrag nach 7.4: build(task, inp, ctx) -> Palettenobjekt.
"""
from tools import color as C
from tools import export as X

WHITE, BLACK, DARK = "#FFFFFF", "#000000", "#16191D"  # #16191D: dunkler Hintergrund (4.1.17, Festlegung)
KINDS2 = ("normal", "deutan", "protan", "gray")


def _variant(c, h, L, against, direction):
    """Textvariante bei gleichem Farbton und gleicher Chroma. Liegt die Fläche auf der falschen Seite der
    Markenfarbe (sehr dunkle Farbe gegen #16191D), startet die Suche knapp jenseits der Fläche."""
    try:
        return C.solve_l(c, h, [against], 4.5, direction, L)
    except C.SolveError as e:
        if e.key != "mixed-sides":
            raise
        return C.solve_l(c, h, [against], 4.5, direction, C.hex_to_oklch(against)[0] + 0.05 * direction)


def build(task, inp, ctx):
    seed = C.norm_hex(inp["seed"])
    o = inp["options"]
    L, c, h = C.hex_to_oklch(seed)
    h = 0.0 if h is None else h
    on = WHITE if C.contrast(seed, WHITE) >= C.contrast(seed, BLACK) else BLACK
    light = _variant(c, h, L, WHITE, -1)
    dark = _variant(c, h, L, DARK, 1)
    r = {"brand": seed, "on-brand": on, "brand-text-light": light["hex"], "brand-text-dark": dark["hex"],
         "brand-gray": C.gray_hex(seed), "bg-light": WHITE, "bg-dark": DARK}
    c2 = o.get("c2")
    if c2:
        r["brand-2"] = C.norm_hex(c2)
    roles = {"default": r}
    changes = []
    for rid, res, bg, key in (("brand-text-light", light, WHITE, "text-light"), ("brand-text-dark", dark, DARK, "text-dark")):
        if res["hex"] != seed:
            changes.append({"role": rid, "mode": "default", "from": seed, "to": res["hex"], "key": key,
                            "values": {"before": C.contrast(seed, bg), "after": res["ratio"]}})
    ev = C.evaluate(task, roles, "skip")
    distinct, findings = [], []
    if c2:
        md = C.min_distance([seed, r["brand-2"]], list(C.WORST_KINDS))
        distinct.append({"id": "brand2", "mode": "default", "value": md["value"], "a": "brand", "b": "brand-2",
                         "kind": md["kind"], "compare": {"id": "okabe-ito-7"}})
        g = C.gray_distance(seed, r["brand-2"])
        distinct.append({"id": "brand2-gray", "mode": "default", "value": g, "a": "brand", "b": "brand-2", "kind": "gray"})
        if md["value"] < C.JND_DISTANCE:
            findings.append({"id": "brand2-close", "mode": None, "severity": "note", "values": {"distance": md["value"]}})
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": distinct, "changes": changes, "findings": findings, "usage": {},
            "extra": {"summary": ["summary.c2"] if c2 else []}}


def view_vars(palette, mode, toggles):
    """Einfarbige Fassungen in reinem Schwarz und Weiß und die Anzeige der zweiten Farbe im Muster."""
    return {"mono-ink": BLACK, "mono-paper": WHITE, "show-2": "flex" if "brand-2" in palette["roles"][mode] else "none"}


# ---- Steckbrief (5.8, Markdown)

def _rgb(hx):
    return "rgb(" + " ".join(str(int(hx[i:i + 2], 16)) for i in (1, 3, 5)) + ")"


def factsheet(palette, task, ctx, lang, opts=None):
    t = ctx["text"]
    r = palette["roles"]["default"]
    rc = X.rctx(palette, "default", None, ctx)

    def p(key):
        return X.plain(X.presub(t[key], ctx), rc, lang)
    ok = C.shortest_oklch(r["brand"])
    out = [p("fs.title"), X.header(ctx), "", "## " + t["fs.h_screen"],
           "- Hex: " + r["brand"], "- RGB: " + _rgb(r["brand"]),
           "- OKLCH: " + (ok if ok else t["fs.oklch_none"]), "",
           "## " + t["fs.h_on"], p("fs.on_white"), p("fs.on_black"),
           p("fs.on_pick_white" if r["on-brand"] == "#FFFFFF" else "fs.on_pick_black"),
           p("fs.aaa_ok" if C.contrast(r["on-brand"], r["brand"]) >= 7 else "fs.aaa_gap"), "",
           "## " + t["fs.h_text"],
           p("fs.text_light" if r["brand-text-light"] == r["brand"] else "fs.text_light_changed"),
           p("fs.text_dark" if r["brand-text-dark"] == r["brand"] else "fs.text_dark_changed"), "",
           "## " + t["fs.h_gray"], p("fs.gray"), "",
           "## " + t["fs.h_mono"], p("fs.mono_black"), p("fs.mono_white"), ""]
    if "brand-2" in r:
        out += ["## " + t["fs.h_c2"], p("fs.c2_hex"), p("fs.c2_cr"), p("fs.c2_dist"), ""]
    out += ["## " + t["fs.h_print"], p("fs.print"), "", "## " + t["fs.h_law"], p("fs.law"), "", "---",
            X.presub(ctx["core"]["link"], ctx)]
    return "\n".join(out)


exports = {"factsheet": factsheet}
