"""Generator der Aufgabe Text auf Bild. Spiegel von web/gen/image-text.js.

build(task, inp, ctx) -> Palettenobjekt mit einem Modus „default“. Die eigene Farbe (URL-Name sc) ist die
Schleierfarbe, tc die Schriftfarbe, tg das Ziel (3 oder 4,5). Gerechnet wird mit scrim_alpha gegen den
schlimmsten Pixel nach F83: reines Weiß hinter heller Schrift, reines Schwarz hinter dunkler. Ohne Lösung
(selbst volle Deckkraft reicht nicht) wirft der Generator SolveError("scrim-unreachable").
Aufgabenspezifische Exporte: Schleier-CSS, Werte und ein Prompt für Coding-Agenten, alles nur mit Hex-Werten.
"""
from tools import color as C, export as X

# Feste Referenzflächen des Musters (Pixel eines Fotos, keine Palettenrollen): reines Weiß und reines Schwarz
# sind Pflicht, dazu Grau- und Farbtöne, die wie Himmel, Laub, Haut oder Asphalt wirken.
REF = {"ref-white": "#FFFFFF", "ref-black": "#000000", "ref-sky": "#DCEAF4", "ref-sand": "#EFE3C8",
       "ref-leaf": "#5E7F3A", "ref-stone": "#8A8F96", "ref-night": "#141B2D", "ref-dusk": "#3A3F55",
       "ref-light": "#FFD98A", "ref-red": "#C2413B", "ref-blue": "#2F6FB0"}


def target_of(options):
    return float(options["tg"])


def scrim(palette):
    """Ergebnis von scrim_alpha zur Palette (Schrift, Schleier, Ziel)."""
    r = palette["roles"]["default"]
    return C.scrim_alpha(r["text"], r["scrim"], target_of(palette["input"]["options"]))


def build(task, inp, ctx):
    o = inp["options"]
    text, sc, target = o["tc"], inp["seed"], target_of(o)
    res = C.scrim_alpha(text, sc, target)
    if res is None:
        raise C.SolveError("scrim-unreachable", {"target": target, "best": C.contrast(text, sc)})
    roles = {"default": {"text": text, "scrim": sc, "worst-pixel": res["worst"], "composite": res["mix_hex"]}}
    t2 = dict(task, pairs=[dict(p, min=target) for p in task["pairs"]])
    ev = C.evaluate(t2, roles, "skip")
    worst = "white" if res["worst"] == "#FFFFFF" else "black"
    tkey = "3" if target == 3.0 else "4.5"
    # Es zählt der kleinere Kontrast. Die Seite zeigt den 8-Bit-Wert und sagt, ob er der kleinere ist. Gleichstand
    # innerhalb der Rechengenauigkeit (1e-9, wie im Paritätstest) gilt als 8 Bit, in Python und JS gleich.
    low = "8bit" if res["ratio_at_percent_8bit"] <= res["ratio_at_percent"] + 1e-9 else "float"
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": [], "changes": [], "findings": [], "usage": {},
            "extra": {"summary": ["summary.alpha." + tkey, "summary.low." + low, "summary.worst." + worst],
                      "scrim": {"alpha": res["alpha"], "percent": res["percent"], "ratio": res["ratio_at_percent"],
                                "ratio_8bit": res["ratio_at_percent_8bit"], "target": target}}}


def view_vars(palette, mode, toggles):
    """Deckkraft des Schleiers als Zahl (--d-alpha) und die festen Farben der Referenzflächen."""
    out = dict(REF)
    out["alpha"] = X.dec(palette["extra"]["scrim"]["percent"], 2)
    return out


# ---- Exporte

def _alpha(pct):
    return X.dec(pct, 2)


def _rgb(hx, a):
    return f"rgb({int(hx[1:3], 16)} {int(hx[3:5], 16)} {int(hx[5:7], 16)} / {a})"


def _rgba(hx, a):
    return f"rgba({int(hx[1:3], 16)}, {int(hx[3:5], 16)}, {int(hx[5:7], 16)}, {a})"


def _hex8(hx, pct):
    """Hex mit Alpha, aufgerundet (nie weniger deckend als die Mindestdeckkraft)."""
    n = (pct * 255 + 99) // 100
    return hx + "0123456789ABCDEF"[n // 16] + "0123456789ABCDEF"[n % 16]


def _words(palette, ctx, lang):
    tx = ctx["text"]
    r = palette["roles"]["default"]
    s = palette["extra"]["scrim"]
    worst = "white" if r["worst-pixel"] == "#FFFFFF" else "black"
    return {"tx": tx, "r": r, "s": s, "pct": C.fmt_pct_up(s["percent"] / 100, lang),
            "target": X.fmt_threshold(s["target"], lang), "worst": worst,
            "tkey": "3" if s["target"] == 3.0 else "4.5"}


def _fill(t, values):
    for k, v in values.items():
        t = t.replace("{" + k + "}", v)
    return t


def _scrim_css(palette, task, ctx, lang, opts=None):
    """Schleier-CSS: unteres Feld 0 bis 40 % voll gedeckt, Auslauf auf 0 bei 70 % (Konvention)."""
    w = _words(palette, ctx, lang)
    r, tx = w["r"], w["tx"]
    a = _alpha(w["s"]["percent"])
    vals = {"text": r["text"], "sc": r["scrim"], "target": w["target"], "pct": w["pct"], "pixel": r["worst-pixel"]}
    head = [X.header(ctx), _fill(tx["css.line"], vals), _fill(tx["css.worst." + w["worst"]], vals), tx["css.text"],
            X.presub(ctx["core"]["link"], ctx)]
    lines = ["/* " + X.comment_safe(head[0])] + ["   " + X.comment_safe(x) for x in head[1:]]
    lines[-1] += " */"
    lines += [".hero {", "  background:",
              f"    linear-gradient(to top, {_rgb(r['scrim'], a)} 0%, {_rgb(r['scrim'], a)} 40%, {_rgb(r['scrim'], '0')} 70%),",
              "    url(\"" + tx["css.image"] + "\") center / cover;",
              "  color: " + r["text"] + ";", "}"]
    return "\n".join(lines)


def _values(palette, task, ctx, lang, opts=None):
    """Werte: Schrift, Schleier, Mindestdeckkraft, Kontrast beim schlimmsten Pixel, Ziel."""
    w = _words(palette, ctx, lang)
    r, s, tx = w["r"], w["s"], w["tx"]
    low = min(s["ratio"], s["ratio_8bit"])
    rows = [("val.text", r["text"]), ("val.scrim", r["scrim"]),
            ("val.target", w["target"] + " " + tx["val.target." + w["tkey"]]),
            ("val.alpha", w["pct"] + " (alpha " + _alpha(s["percent"]) + ")"),
            ("val.worst", r["worst-pixel"] + " " + tx["val.worst." + w["worst"]]),
            ("val.mix", r["composite"]),
            ("val.ratio", _fill(tx["val.ratio.v"], {"f": C.fmt_ratio(s["ratio"], lang, s["target"]),
                                                    "q": C.fmt_ratio(s["ratio_8bit"], lang, s["target"]),
                                                    "m": C.fmt_ratio(low, lang, s["target"])})),
            ("val.area", tx["val.area.v"])]
    labels = [tx[k] for k, _ in rows]
    width = max(len(x) for x in labels) + 2
    lines = [X.header(ctx)] + [lab.ljust(width) + v for lab, (_, v) in zip(labels, rows)]
    lines += ["", X.presub(ctx["core"]["link"], ctx)]
    return "\n".join(lines)


def _agent(palette, task, ctx, lang, opts=None):
    """Prompt für Coding-Agenten (Variante Text auf Bild): nur Hex-Werte, keine CSS-Variablen."""
    w = _words(palette, ctx, lang)
    r, s, tx, core = w["r"], w["s"], w["tx"], ctx["core"]
    a = _alpha(s["percent"])
    rc = X.rctx(palette, None, None, ctx)
    vals = {"text": r["text"], "sc": r["scrim"], "target": w["target"], "pct": w["pct"], "pixel": r["worst-pixel"],
            "alpha": a, "mix": r["composite"], "hex8": _hex8(r["scrim"], s["percent"]), "hex0": r["scrim"] + "00",
            "rgba": _rgba(r["scrim"], a), "rgba0": _rgba(r["scrim"], "0"),
            "ratio": C.fmt_ratio(min(s["ratio"], s["ratio_8bit"]), lang, s["target"])}
    out = [tx["agent.intro"], "", "# " + X.presub(tx["agent.title"], ctx), "", core["h_idea"],
           _fill(tx["agent.idea." + w["worst"]], vals), "", tx["agent.h_values"]]
    out += ["- " + _fill(x, vals) for x in tx["agent.values"]]
    out += ["", tx["agent.h_build"]]
    out += ["- " + _fill(x, vals) for x in tx["agent.build"]]
    out += ["", core["h_rules"]]
    for rule in ctx.get("rules") or []:
        out.append("- " + X.plain(X.presub(rule["text_" + lang], ctx), rc, lang) + " " + X.level_note(rule, ctx, lang))
    out += ["", core["h_avoid"]]
    out += ["- " + X.plain(X.presub(x, ctx), rc, lang) for x in tx["agent.avoid"]]
    out += ["", core["h_check"]]
    out += ["- " + X.plain(X.presub(x, ctx), rc, lang) for x in tx["agent.checks"]]
    out += ["", core["h_tip"], X.plain(X.presub(tx["agent.tip"], ctx), rc, lang), "", "---"]
    out.append(X.presub(core["agent_source_custom" if palette.get("preset") is None else "agent_source"], ctx))
    return "\n".join(out)


exports = {"scrim": _scrim_css, "values": _values, "agent": _agent}
