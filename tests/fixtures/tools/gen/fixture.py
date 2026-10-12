"""Generator der Testaufgabe (Spiegel von tests/fixtures/web/gen/fixture.js).

Trivial, aber mit echtem Farbkern: Neutraltöne aus dem Farbton der eigenen Farbe, ein Akzent mit
Schriftfarbe (Änderungshinweis, wenn keine Schrift 4,5:1 erreicht), Stufen per solve_l auf 3,3:1,
Abstände mit Vergleich, Hinweise aus evaluate. Vertrag nach Spezifikation 7.4:
build(task, inp, ctx) -> Palettenobjekt (6.14); der Rahmen setzt task, preset, input, name_de, name_en.
"""
from tools import color as C


def _neutrals(h, t):
    light = {"bg": C.oklch_to_hex(0.985, 0.4 * t, h), "surface": "#FFFFFF",
             "text": C.oklch_to_hex(0.24, 1.6 * t, h), "border": C.oklch_to_hex(0.88, t, h)}
    light["text-muted"] = C.solve_l(1.4 * t, h, [light["bg"], light["surface"]], 4.95, -1, 0.60)["hex"]
    dark = {"bg": C.oklch_to_hex(0.19, t, h), "surface": C.oklch_to_hex(0.23, t, h),
            "text": C.oklch_to_hex(0.94, 0.6 * t, h), "border": C.oklch_to_hex(0.34, t, h)}
    dark["text-muted"] = C.solve_l(t, h, [dark["bg"], dark["surface"]], 4.95, 1, 0.60)["hex"]
    return light, dark


def _accent(cand, L, Cc, h, labels, mode, changes):
    """Akzent als Fläche: bleibt, wenn eine Beschriftung 4,5:1 erreicht, sonst dunkler für helle Schrift."""
    best, label = -1.0, None
    for lab in labels:
        r = C.contrast(lab, cand)
        if r > best:
            best, label = r, lab
    if best >= 4.5:
        return cand, label
    light_label = labels[0] if C.rel_lum(labels[0]) >= C.rel_lum(labels[1]) else labels[1]
    res = C.solve_l(Cc, h, [light_label], 4.5, -1, L)
    changes.append({"role": "accent", "mode": mode, "from": cand, "to": res["hex"], "key": "accent-darker",
                    "values": {"before": C.contrast(light_label, cand), "after": res["ratio"]}})
    return res["hex"], light_label


def build(task, inp, ctx):
    o = inp["options"]
    L, Cs, h = C.hex_to_oklch(inp["seed"])
    if h is None:
        h = 0.0
    t = 0.0 if o["tone"] == "neutral" else min(max(0.1 * Cs, 0.004), 0.012)
    light, dark = _neutrals(h, t)
    changes, findings = [], []
    light["accent"], light["on-accent"] = _accent(inp["seed"], L, Cs, h, [o["tc"], light["text"]], "light", changes)
    light["accent-text"] = C.solve_l(Cs, h, [light["bg"], light["surface"]], 4.5, -1, L)["hex"]
    cand = C.oklch_to_hex(L, 0.85 * Cs, h)
    dark["accent"], dark["on-accent"] = _accent(cand, L, 0.85 * Cs, h, [dark["text"], dark["bg"]], "dark", changes)
    dark["accent-text"] = C.solve_l(0.85 * Cs, h, [dark["bg"], dark["surface"]], 4.5, 1, L)["hex"]
    raw = {"light": [], "dark": []}
    for i in range(o["k"]):
        hue = (h + i * 120) % 360
        light[f"step-{i + 1}"] = C.solve_l(Cs, hue, [light["bg"]], 3.3, -1, 0.62)["hex"]
        dark[f"step-{i + 1}"] = C.solve_l(0.85 * Cs, hue, [dark["bg"]], 3.3, 1, 0.62)["hex"]
        raw["light"].append(C.oklch_to_hex(0.62, Cs, hue))
        raw["dark"].append(C.oklch_to_hex(0.62, 0.85 * Cs, hue))
    okabe = [c["hex"] for c in ctx["datasets"]["okabe-ito"]["schemes"][0]["colors"] if c["name"] != "black"]
    for mode, roles in (("light", light), ("dark", dark)):
        pool = [x for x in okabe if C.contrast(x, roles["bg"]) >= 3.0]
        roles["chart-1"] = C.pick_distinct(pool, 1, C.WORST_KINDS, None, roles["bg"])[0]
    roles = {"light": light, "dark": dark}
    ev = C.evaluate(task, roles, "skip")
    for a in ev["advisory"]:
        if not a["pass"]:
            findings.append({"id": a["finding"], "mode": a["mode"], "severity": "note", "values": {"ratio": a["ratio"]}})
    for mode in ("light", "dark"):
        r = C.contrast(roles[mode]["accent-text"], roles[mode]["text"])
        if r < 3.0:
            findings.append({"id": "link-low", "mode": mode, "severity": "note", "values": {"ratio": r}})
    distinct = []
    if o["k"] >= 2:
        kinds = ["normal", "deutan", "protan"] + (["gray"] if o["pr"] else [])
        for mode in ("light", "dark"):
            steps = [roles[mode][f"step-{i + 1}"] for i in range(o["k"])]
            md = C.min_distance(steps, kinds)
            rw = C.min_distance(raw[mode], kinds)
            distinct.append({"id": "steps", "mode": mode, "value": md["value"], "a": f"step-{md['i'] + 1}",
                             "b": f"step-{md['j'] + 1}", "kind": md["kind"],
                             "compare": {"id": "steps-raw", "value": rw["value"], "a": rw["a"], "b": rw["b"], "kind": rw["kind"]}})
    for mode in ("light", "dark"):  # Vergleich nur per ID aus data/comparisons.json (Name kommt von dort)
        md2 = C.min_distance([roles[mode]["chart-1"], roles[mode]["accent-text"]], ["normal", "deutan", "protan"])
        distinct.append({"id": "chart", "mode": mode, "value": md2["value"], "a": "chart-1", "b": "accent-text",
                         "kind": md2["kind"], "compare": {"id": "okabe-ito-7"}})
    usage = {}
    for mode in ("light", "dark"):
        usage[mode] = {}
        for i in range(o["k"]):
            rid = f"step-{i + 1}"
            r = C.contrast(roles[mode][rid], roles[mode]["bg"])
            usage[mode][rid] = "text" if r >= 4.5 else "lines" if r >= 3.0 else "area"
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": distinct, "changes": changes, "findings": findings, "usage": usage,
            "extra": {"datasets": {"okabe-ito": ["chart-1"]}, "summary": ["summary.text"], "pair_note": "pair.note"}}


def view_vars(palette, mode, toggles):
    """Muster-Schalter „Vertauscht“: Hintergrund und Text tauschen (prüft den Haken des Rahmens)."""
    r = palette["roles"][mode]
    if toggles.get("view") == "inverted":
        return {"bg": r["text"], "text": r["bg"]}
    return {}


def _list(palette, task, ctx, lang, opts=None):
    """Aufgabenspezifisches Format „Liste“: Rolle und Hex je Modus."""
    out = []
    for mode in palette["modes"]:
        out.append(ctx["core"]["label." + mode])
        out += [f"{rid}: {hx}" for rid, hx in palette["roles"][mode].items()]
        out.append("")
    out.append(ctx["core"]["link"].replace("{url}", ctx["url"]))
    return [{"label": None, "text": "\n".join(out), "suffix": "", "lang": None, "note": ctx["text"]["list.bnote"]}]


exports = {"list": _list}
