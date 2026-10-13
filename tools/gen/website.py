"""Generator der Aufgabe Website oder App (Spiegel von web/gen/website.js).

Neutraltöne aus Farbton und Tönung der eigenen Farbe, Akzent als Fläche mit
Schriftfarbe, Akzent als Text, Diagrammfarben für die Export-Option. Dazu Statusfarben, in festen
Bändern optimiert auf den größten kleinsten Abstand bei normalem Sehen, Deuteranopie und Protanopie, mit
dem Vergleichswert ohne Optimierung. Die Aufgabe status nutzt neutrals, status_colors und status_findings.
Vertrag: build(task, inp, ctx) -> Palettenobjekt; task, preset, input und Namen setzt der Rahmen.
"""
import json

from tools import color as C, export as X

KINDS3 = ["normal", "deutan", "protan"]
# Statusfarben: Farbton, Chroma je Modus, Fläche je Modus (L, C), Band je Modus (Start, Anzahl), Schritt 0,02
STATUS = [("danger", 27.0), ("warning", 70.0), ("success", 150.0), ("info", 250.0)]
STATUS_C = {"light": 0.15, "dark": 0.13}
STATUS_SURF = {"light": (0.965, 0.025), "dark": (0.27, 0.04)}
BAND = {"light": (0.42, 9), "dark": (0.62, 13)}
STATUS_DIR = {"light": -1, "dark": 1}
CHARTS = 5
# Start der Suche für die Linkfarbe, wenn die eigene Farbe jenseits der Flächen liegt (dunkler als die dunklen
# Flächen, heller als der helle Hintergrund): unterhalb der Grenze 4,5:1 und auf der richtigen Seite der Flächen
TEXT_L0 = {-1: 0.80, 1: 0.40}
# Reserve über der Schwelle (Festlegung): gedämpfter Text 4,95 statt 4,5, kräftiger Rahmen 3,3 statt 3,
# als Literal wie LIGHT_T in tools/gen/slides.py. pages/method.py liest die Reserve und DARK_C von hier.
TEXT_T, LINE_T = 4.95, 3.3
# Buntheit des Akzents im dunklen Modus
DARK_C = 0.85


def tint(cs, tone):
    """Tönung t der Neutraltöne: neutral 0, leicht getönt 0,1·C, kräftig 0,25·C, jeweils begrenzt."""
    if tone == "neutral":
        return 0.0
    if tone == "strong":
        return min(max(0.25 * cs, 0.010), 0.030)
    return min(max(0.1 * cs, 0.004), 0.012)


def seed_lch(seed, tone):
    """Seed → (L, C, h, t, h_roh). Unbunte Farbe (Farbton powerless, h_roh None): h = 0, Tönung 0."""
    L, cs, h = C.hex_to_oklch(seed)
    if h is None:
        return L, cs, 0.0, 0.0, None
    return L, cs, h, tint(cs, tone), h


def neutrals(h, t):
    """Neutraltöne hell und dunkel, Reserve ×1,1 über TEXT_T und LINE_T."""
    lt = {"bg": C.oklch_to_hex(0.985, 0.4 * t, h), "surface": "#FFFFFF", "surface-2": C.oklch_to_hex(0.955, 0.6 * t, h),
          "text": C.oklch_to_hex(0.24, 1.6 * t, h), "border": C.oklch_to_hex(0.88, t, h)}
    lt["text-muted"] = C.solve_l(1.4 * t, h, [lt["bg"], lt["surface"], lt["surface-2"]], TEXT_T, -1, 0.60)["hex"]
    lt["border-strong"] = C.solve_l(1.4 * t, h, [lt["bg"], lt["surface"]], LINE_T, -1, 0.72)["hex"]
    dk = {"bg": C.oklch_to_hex(0.19, t, h), "surface": C.oklch_to_hex(0.23, t, h), "surface-2": C.oklch_to_hex(0.27, t, h),
          "text": C.oklch_to_hex(0.94, 0.6 * t, h), "border": C.oklch_to_hex(0.34, t, h)}
    dk["text-muted"] = C.solve_l(t, h, [dk["bg"], dk["surface"], dk["surface-2"]], TEXT_T, 1, 0.60)["hex"]
    dk["border-strong"] = C.solve_l(t, h, [dk["bg"], dk["surface"]], LINE_T, 1, 0.45)["hex"]
    return {"light": lt, "dark": dk}


# ---- Akzent

def accent_fill(cand, L, c, h, labels, mode, changes):
    """Akzent als Fläche: labels = [(Schrift, Richtung)], Richtung −1 für helle Schrift (Akzent dunkler),
    +1 für dunkle Schrift (heller). → (Akzent, Schrift, behalten)."""
    best = None
    for lab, _ in labels:
        r = C.contrast(lab, cand)
        if r >= 4.5 and (best is None or r > best[1]):
            best = (lab, r)
    if best is not None:
        return cand, best[0], True
    pick, err = None, None
    for lab, d in labels:
        try:
            res = C.solve_l(c, h, [lab], 4.5, d, L)
        except C.SolveError as e:
            err = err or e
            continue
        step = abs(res["L"] - L)
        if pick is None or step < pick[1] or (step == pick[1] and res["ratio"] > pick[2]["ratio"]):
            pick = (lab, step, res, d)
    if pick is None:
        raise err
    lab, _, res, d = pick
    changes.append({"role": "accent", "mode": mode, "from": cand, "to": res["hex"],
                    "key": "accent-darker" if d < 0 else "accent-lighter",
                    "values": {"before": C.contrast(lab, cand), "after": res["ratio"]}})
    return res["hex"], lab, False


def text_accent(c, h, against, d, L):
    """Akzent als Text: solve_l ab der eigenen Helligkeit L. Liegt die eigene Farbe jenseits der Flächen
    (Vorbedingung von solve_l verletzt, etwa bei Schwarz oder #111827 im dunklen Modus), sucht er ab TEXT_L0."""
    try:
        return C.solve_l(c, h, against, 4.5, d, L)
    except C.SolveError as e:
        if e.key != "mixed-sides":
            raise
        return C.solve_l(c, h, against, 4.5, d, TEXT_L0[d])


def accents(seed, L, cs, h, roles, changes):
    """Akzent, Schrift darauf und Akzent als Text in beiden Modi. → {mode: behalten?} für das Kurzergebnis."""
    lt, dk = roles["light"], roles["dark"]
    kept = {}
    lt["accent"], lt["on-accent"], kept["light"] = accent_fill(seed, L, cs, h, [("#FFFFFF", -1), (lt["text"], 1)], "light", changes)
    at = text_accent(cs, h, [lt["bg"], lt["surface"]], -1, L)
    lt["accent-text"] = at["hex"]
    if at["hex"] != seed:
        changes.append({"role": "accent-text", "mode": "light", "from": seed, "to": at["hex"], "key": "accent-text-darker",
                        "values": {"before": min(C.contrast(seed, lt["bg"]), C.contrast(seed, lt["surface"])), "after": at["ratio"]}})
    cand = C.oklch_to_hex(L, DARK_C * cs, h)
    dk["accent"], dk["on-accent"], kept["dark"] = accent_fill(cand, L, DARK_C * cs, h, [(dk["text"], -1), (dk["bg"], 1)], "dark", changes)
    # Dunkel geht die Linkfarbe vom dunklen Kandidaten aus; weicht sie ab, sagt das ein Hinweis wie hell (Block C)
    at = text_accent(DARK_C * cs, h, [dk["bg"], dk["surface"]], 1, L)
    dk["accent-text"] = at["hex"]
    if at["hex"] != cand:
        changes.append({"role": "accent-text", "mode": "dark", "from": cand, "to": at["hex"], "key": "accent-text-lighter",
                        "values": {"before": min(C.contrast(cand, dk["bg"]), C.contrast(cand, dk["surface"])), "after": at["ratio"]}})
    return kept


def okabe(ctx):
    return [c["hex"] for c in ctx["datasets"]["okabe-ito"]["schemes"][0]["colors"] if c["name"] != "black"]


def charts(roles, ctx):
    """Export-Option „Diagrammfarben einschließen“: Linkfarbe zuerst, dann Okabe-Ito mit ≥ 3:1 auf bg."""
    ok = okabe(ctx)
    for mode in ("light", "dark"):
        r = roles[mode]
        pool = [r["accent-text"]] + [x for x in ok if C.contrast(x, r["bg"]) >= 3.0]
        for i, hx in enumerate(C.pick_distinct(pool, CHARTS, KINDS3, r["accent-text"], None)):
            r[f"chart-{i + 1}"] = hx


# ---- Statusfarben

def status_surface(mode, hue):
    Ls, cs = STATUS_SURF[mode]
    return C.oklch_to_hex(Ls, cs, hue)


def _best(cands, dist):
    """Kombination mit dem größten kleinsten Abstand; lexikographisch, Ersatz nur bei mehr als 1e-12 besser."""
    best, pick = -1.0, None
    n = [len(c) for c in cands]
    d01, d02, d03, d12, d13, d23 = dist
    for a in range(n[0]):
        for b in range(n[1]):
            m1 = d01[a][b]
            if m1 <= best + 1e-12:
                continue
            for c in range(n[2]):
                m2 = min(m1, d02[a][c], d12[b][c])
                if m2 <= best + 1e-12:
                    continue
                for d in range(n[3]):
                    m3 = min(m2, d03[a][d], d13[b][d], d23[c][d])
                    if m3 > best + 1e-12:
                        best, pick = m3, (a, b, c, d)
    return pick


def status_colors(roles, findings):
    """Statusfarben und Flächen je Modus → distinct-Einträge mit Vergleich „unoptimiert“."""
    distinct = []
    for mode in ("light", "dark"):
        r = roles[mode]
        cc, (lo, steps), sd = STATUS_C[mode], BAND[mode], STATUS_DIR[mode]
        cands, raw = [], []
        for sid, hue in STATUS:
            surf = status_surface(mode, hue)
            r[sid + "-subtle"] = surf
            against = [r["bg"], r["surface"], surf]
            raw.append(C.solve_l(cc, hue, against, 4.5, sd, 0.60)["hex"])
            ok = []
            for i in range(steps):
                hx = C.oklch_to_hex(lo + i * 0.02, cc, hue)
                if hx not in ok and all(C.contrast(hx, b) >= 4.5 for b in against):
                    ok.append(hx)
            cands.append(ok)
        # Fehlt einem Status jeder Kandidat, gilt der Wert ohne Optimierung (ein Hinweis je Modus)
        missing = [sid for k, (sid, _) in enumerate(STATUS) if not cands[k]]
        for k in range(4):
            if not cands[k]:
                cands[k] = [raw[k]]
        if missing:
            findings.append({"id": "status-fallback", "mode": mode, "severity": "note", "values": {"status": missing}})
        idx = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        dist = [[[min(C.distance(x, y, k) for k in KINDS3) for y in cands[j]] for x in cands[i]] for i, j in idx]
        pick = _best(cands, dist)
        cols = [cands[k][pick[k]] for k in range(4)]
        for k, (sid, _) in enumerate(STATUS):
            r[sid] = cols[k]
        md, mr = C.min_distance(cols, KINDS3), C.min_distance(raw, KINDS3)
        distinct.append({"id": "status", "mode": mode, "value": md["value"], "a": STATUS[md["i"]][0], "b": STATUS[md["j"]][0],
                         "kind": md["kind"], "compare": {"id": "status-unoptimized", "value": mr["value"], "a": mr["a"],
                                                         "b": mr["b"], "kind": mr["kind"]}})
    return distinct


def status_findings(distinct, ctx, findings):
    """Hinweis je Modus, wenn die Statusfarben näher liegen als der Vergleichswert Okabe-Ito."""
    ref = C.reference_values(ctx["comparisons"], ctx["datasets"])["okabe-ito-7"]["value"]
    for d in distinct:
        if d["id"] == "status" and d["value"] < ref:
            findings.append({"id": "status-close", "mode": d["mode"], "severity": "note",
                             "values": {"value": d["value"]}})


def conflict(cs, h, findings):
    """Konfliktregel: Akzent weniger als 30° von 27° entfernt und C > 0,1."""
    if h is None or cs <= 0.1:
        return
    dh = abs(h - 27.0) % 360
    if min(dh, 360 - dh) < 30:
        findings.append({"id": "accent-error-conflict", "mode": None, "severity": "note", "values": {"hue": h, "chroma": cs}})


# ---- Aufgabe

def build(task, inp, ctx):
    o = inp["options"]
    seed = inp["seed"]
    L, cs, h, t, h0 = seed_lch(seed, o["tone"])
    roles = neutrals(h, t)
    changes, findings = [], []
    kept = accents(seed, L, cs, h, roles, changes)
    distinct = status_colors(roles, findings)
    charts(roles, ctx)
    ev = C.evaluate(task, roles, "skip")
    # Schwachstellen: textartige Rollen auf nicht freigegebenen Flächen, Akzentfläche, Links, Status
    for mode in ("light", "dark"):
        r = roles[mode]
        for rid in ["accent-text"] + [s for s, _ in STATUS]:
            v = C.contrast(r[rid], r["surface-2"])
            if v < 4.5:
                findings.append({"id": "unsafe-surface" if rid == "accent-text" else "unsafe-surface-" + rid, "mode": mode,
                                 "severity": "note", "values": {"ratio": v}})
    for a in ev["advisory"]:
        if not a["pass"]:
            findings.append({"id": a["finding"], "mode": a["mode"], "severity": "note", "values": {"ratio": a["ratio"]}})
    for mode in ("light", "dark"):
        r = roles[mode]
        v = C.contrast(r["accent-text"], r["text"])
        if v < 3.0:
            win = C.link_window(r["text"], [r["bg"], r["surface"]])
            findings.append({"id": "link-window-empty" if win["empty"] else "link-underline", "mode": mode, "severity": "note",
                             "values": {"ratio": v}})
    status_findings(distinct, ctx, findings)
    conflict(cs, h0, findings)
    summary = []
    for mode in ("light", "dark"):
        if kept[mode]:
            light_label = roles[mode]["on-accent"] == ("#FFFFFF" if mode == "light" else roles[mode]["text"])
            summary.append(f"sum.{mode}.{'keep-light' if light_label else 'keep-dark'}")
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": distinct, "changes": changes, "findings": findings, "usage": {},
            "extra": {"datasets": {"okabe-ito": [f"chart-{i + 1}" for i in range(CHARTS)]}, "summary": summary}}


# ---- Exporte

def status_template(palette, text, mode, key):
    """Vorlage weak.status oder why.status mit dem engsten Statuspaar des Modus (aus palette.distinct);
    {kind_l} ist die Sichtweise mit kleinem Anfangsbuchstaben für die Satzmitte."""
    d = next(x for x in palette["distinct"] if x["id"] == "status" and x["mode"] == mode)
    hx = palette["roles"][mode]
    kind = text["cvd." + d["kind"]]
    return (text[key].replace("{kind_l}", kind[:1].lower() + kind[1:]).replace("{kind}", kind).replace("{a}", text["st." + d["a"]])
            .replace("{b}", text["st." + d["b"]]).replace("{pair_dist}", "{dist:" + hx[d["a"]] + "/" + hx[d["b"]] + "/" + d["kind"] + "}"))


def status_ctx(palette, ctx):
    """Palette und Texte für die generischen Renderer: Der Hinweis status-close bekommt je Modus den Text mit
    dem engsten Paar (Prompt), das Token {status_why} der Begründung den Satz für hell, ohne
    Hinweis hell den Satz why.status_plain."""
    text = dict(ctx["text"])
    # Idee je Tönung: ohne Tönung (neutral oder unbunte Farbe) und kräftig mit eigenem Text, sonst agent.idea
    tone = (palette.get("input") or {}).get("options", {}).get("tone")
    if tone and palette["input"].get("seed"):
        key = "neutral" if seed_lch(palette["input"]["seed"], tone)[3] == 0.0 else tone
        text["agent.idea"] = text.get("agent.idea." + key, text["agent.idea"])
    fs = []
    for f in palette["findings"]:
        if f["id"] == "status-close":
            key = "status-close-" + f["mode"]
            text["finding." + key] = status_template(palette, text, f["mode"], "weak.status")
            f = dict(f, id=key)
        fs.append(f)
    light = any(f["id"] == "status-close" and f["mode"] == "light" for f in palette["findings"])
    why = []
    for e in text["rationale"]:
        if e == "{status_why}":
            if light:
                why.append(status_template(palette, text, "light", "why.status"))
            elif "why.status_plain" in text:
                why.append(text["why.status_plain"])
        else:
            why.append(e)
    text["rationale"] = why
    return dict(palette, findings=fs), dict(ctx, text=text)


def agent(palette, task, ctx, lang, opts=None):
    p, c = status_ctx(palette, ctx)
    return _charts_css(X.agent(p, task, c, lang, opts), palette, ctx, lang, opts)


def rationale(palette, task, ctx, lang, opts=None):
    p, c = status_ctx(palette, ctx)
    return X.rationale(p, task, c, lang, opts)


# Hinweis, wenn in einem Modus weniger als fünf Diagrammfarben 3:1 erreichen. Er steht in jedem Export,
# der die Diagrammfarben enthält: CSS, Tailwind, Tokens im Prompt, Hex-Liste und Design-Tokens.

def charts_few(palette, ctx, lang, mode, opts):
    """Text css.charts_few (bei genau einer Farbe css.charts_few_1) für den Modus, sonst None."""
    if not (opts or {}).get("charts"):
        return None
    n = sum(1 for k in palette["roles"][mode] if k.startswith("chart-"))
    if n >= CHARTS:
        return None
    return ctx["text"]["css.charts_few_1" if n == 1 else "css.charts_few"].replace("{n}", C.fmt_count(n, lang))


def _charts_css(text, palette, ctx, lang, opts):
    """Kommentar nach der letzten Zeile mit --chart- je Block (:root, dann je @media ein Modus)."""
    lines = text.split("\n")
    block, last = 0, {}
    for i, line in enumerate(lines):
        if line.startswith("@media"):
            block += 1
        if line.lstrip().startswith("--chart-"):
            last[block] = i
    for b in sorted(last, reverse=True):
        note = charts_few(palette, ctx, lang, palette["modes"][b], opts)
        if note:
            ind = lines[last[b]][:len(lines[last[b]]) - len(lines[last[b]].lstrip())]
            lines.insert(last[b] + 1, ind + "/* " + X.comment_safe(note) + " */")
    return "\n".join(lines)


def css(palette, task, ctx, lang, opts=None):
    return _charts_css(X.css(palette, task, ctx, lang, opts), palette, ctx, lang, opts)


def tailwind(palette, task, ctx, lang, opts=None):
    return _charts_css(X.tailwind(palette, task, ctx, lang, opts), palette, ctx, lang, opts)


def hex_list(palette, task, ctx, lang, opts=None):
    """Hex-Liste mit dem Hinweis als eigener Zeile nach der letzten Diagrammfarbe des Modus."""
    parts = X.hex_list(palette, task, ctx, lang, opts).split("\n\n")
    for i, mode in enumerate(palette["modes"]):
        note = charts_few(palette, ctx, lang, mode, opts)
        rows = parts[i].split("\n")
        at = [k for k, row in enumerate(rows) if row.startswith("chart-")]
        if note and at:
            rows.insert(at[-1] + 1, note)
            parts[i] = "\n".join(rows)
    return "\n\n".join(parts)


def dtcg(palette, task, ctx, lang, opts=None):
    """Design-Tokens mit dem Hinweis als Feld note unter $extensions, je Modus eine Datei."""
    out = X.dtcg(palette, task, ctx, lang, opts)
    for mode, b in zip(palette["modes"], out):
        note = charts_few(palette, ctx, lang, mode, opts)
        if note:
            head = '      "standard": '
            i = b["text"].index(head)
            j = b["text"].index("\n", i) + 1
            b["text"] = b["text"][:j] + '      "note": ' + json.dumps(note, ensure_ascii=False) + ",\n" + b["text"][j:]
    return out


exports = {"css": css, "tailwind": tailwind, "hex": hex_list, "dtcg": dtcg, "agent": agent, "rationale": rationale}
