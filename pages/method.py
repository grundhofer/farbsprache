"""Seite Methode (Spezifikation 3.10): 16 Abschnitte, Texte in web/copy/method.py.

Jede Zahl kommt über einen Platzhalter (6.12) oder aus den Daten: Konstanten aus data/color-constants.json,
Raster aus data/check.json, Theme aus web/theme.py. Die Vergleichstabelle (Abschnitt 6) und die Abweichung
des Anzeige-Graus (Abschnitt 4) rechnet diese Datei beim Bau. [[quellen-id]] wird ein Link auf die Quellenseite.
"""
import json, math, re

from tools import color as C, export as X
from pages import task as TP
from web import theme

esc = C.esc


def warn_once(site, msg):
    """WARNUNG nur einmal je Build, auch wenn beide Sprachen sie auslösen."""
    if msg not in site.warnings:
        site.warn(msg)


N_SECTIONS = 16
CITE = re.compile(r"\[\[([a-z0-9-]+)\]\]")
TOKEN = re.compile(r"\{([a-z0-9_]+)\}")
CMP_KINDS = ("normal", "protan", "deutan", "tritan", "gray")


def dec(x, lang):
    """Dezimalzahl aus den Daten (keine Messzahl) mit Komma oder Punkt, ohne Exponent und Endnullen."""
    s = ("%.10f" % x).rstrip("0").rstrip(".")
    return s.replace(".", ",") if lang == "de" else s


def pct_up1(v, lang):
    """Obergrenze in Prozent, auf eine Stelle aufgerundet (zur ungünstigen Seite)."""
    n = math.ceil(v * 1000 - 1e-9)
    return X.fixed(n, 1, lang) + (C.NNBSP + "%" if lang == "de" else "%")


def pct(v, lang):
    """Festlegung als Prozent (keine Messzahl), ohne Endnullen: 0.1 → „10 %“."""
    return dec(v * 100, lang) + (C.NNBSP + "%" if lang == "de" else "%")


def own_tokens(site, lang):
    """Zahlen der Festlegungen (Abschnitt 11) aus den Generatoren und Regeln, nicht abgeschrieben: Reserve über der
    Schwelle (website TEXT_T/LINE_T, slides LIGHT_T/LINE_T, müssen gleich sein), Buntheit im Dunkeln (DARK_C),
    Suchstart der Linkfarbe (website TEXT_L0) und der Schnitt für direkte Beschriftung (Regel chart-direct-labels)."""
    gw, gs = site.gens.get("website"), site.gens.get("slides")
    rule = site.rules.get("chart-direct-labels") or {}
    if gw is None or gs is None or not rule.get("show_if"):
        msg = "Methode: Generator website oder slides oder Regel chart-direct-labels fehlt, Festlegungen ohne Zahl"
        if not site.allow_missing:
            raise ValueError(msg)
        warn_once(site, msg)
        return {}
    res = [gw.TEXT_T / 4.5, gw.LINE_T / 3.0, gs.LIGHT_T / 7.0, gs.LINE_T / 3.0]
    if max(res) - min(res) > 1e-9 or gw.DARK_C != gs.DARK_C:
        raise ValueError("Methode: Reserve oder Buntheit im Dunkeln in tools/gen/website.py und slides.py verschieden")
    return {"reserve": pct(res[0] - 1, lang), "dark_c": pct(gw.DARK_C, lang),
            "l0_light": dec(gw.TEXT_L0[-1], lang), "l0_dark": dec(gw.TEXT_L0[1], lang),
            "cut": C.fmt_count(rule["show_if"]["value"], lang)}


def gray_deviation():
    """Größte Verschiebung durch das 8-Bit-Anzeigegrau gray_hex: (relativ für Y + 0,05 einer Farbe, relativ für den
    Kontrast zweier Graus). Gerechnet an jeder Rundungsgrenze (k + 0,5)/255 in kodiertem sRGB, wo quantize springt."""
    up, down = 0.0, 0.0
    for k in range(255):
        ym = C.lin((k + 0.5) / 255)
        up = max(up, (C.lin((k + 1) / 255) + 0.05) / (ym + 0.05) - 1)
        down = min(down, (C.lin(k / 255) + 0.05) / (ym + 0.05) - 1)
    return max(up, -down), (1 + up) / (1 + down) - 1


def tokens(site, lang):
    k = site.D["files"]["color-constants"]
    p = k["projector"]
    cfg = site.D.get("check") or {"repair_grid": {"from": 20, "to": 95, "div": 100}}
    g = cfg["repair_grid"]
    digits = len(str(g["div"])) - 1
    one, two = gray_deviation()
    w = k["wcag_lum"]
    tok = {"version": esc(k["version"]), "jnd": dec(k["jnd"], lang), "eps": dec(k["eps"], lang), "powerless": dec(k["powerless_c"], lang),
           "lin_t": dec(k["srgb_lin_threshold"], lang), "gam_t": dec(k["srgb_gam_threshold"], lang),
           "wcag": f"{dec(w[0], lang)} · R + {dec(w[1], lang)} · G + {dec(w[2], lang)} · B",
           "native": C.fmt_count(p["native"], lang), "white_lx": C.fmt_count(p["white_lx"], lang),
           "dim_lx": C.fmt_count(p["ambient_lx"]["dim"], lang), "normal_lx": C.fmt_count(p["ambient_lx"]["normal"], lang),
           "bright_lx": C.fmt_count(p["ambient_lx"]["bright"], lang),
           "grid_from": X.fixed(g["from"], digits, lang), "grid_to": X.fixed(g["to"], digits, lang), "grid_step": X.fixed(1, digits, lang),
           "gray_dev1": pct_up1(one, lang), "gray_dev2": pct_up1(two, lang)}
    for mode in ("light", "dark"):
        for name in ("ink", "ground"):
            tok[f"th_{name}_{mode}"] = theme.PALETTES[mode][name]
    tok.update(own_tokens(site, lang))
    return tok


def counts(site):
    tv = site.D["files"].get("testvectors") or {}
    n = sum(len(v) for sec in tv.values() if isinstance(sec, dict) for v in sec.values() if isinstance(v, list))
    seeds = json.loads((site.roots[0] / "tests" / "parity_seeds.json").read_text(encoding="utf-8"))
    return {"vectors": n, "seeds": len(seeds["seeds"])}


def cite(site, lang, page, sid):
    """[[id]] als Quellenangabe in Klammern mit Link auf die Quellenseite."""
    s = site.sources.get(sid)
    if s is None:
        msg = f"Methode: Quelle {sid} fehlt (data/sources/*.json)"
        if not site.allow_missing:
            raise ValueError(msg)
        warn_once(site, msg)
        return f'<span class="m-src">({esc(site.copy[lang]["method"]["src_missing"])}: {esc(sid)})</span>'
    href = site.rel(page, site.path(lang, "sources")) + "#" + sid
    sl = f' lang="{esc(s["short_lang"])}"' if s.get("short_lang") and s["short_lang"] != lang else ""
    return f'(<a class="m-src" href="{href}"{sl}>{esc(s.get("short_" + lang) or s["title"])}</a>)'


def text(site, lang, page, t, tok, cnt):
    t = TOKEN.sub(lambda m: tok[m.group(1)] if m.group(1) in tok else m.group(0), t)
    t = CITE.sub(lambda m: cite(site, lang, page, m.group(1)), t)
    return C.render_text(t, {"refs": site.refs, "counts": cnt, "date": site.date}, lang, False)[0]


def paras(site, lang, page, items, tok, cnt):
    return "".join(f"<p>{text(site, lang, page, p, tok, cnt)}</p>" for p in items)


def matrix_pre(m, frac=False):
    rows = []
    for row in m:
        cells = [f"{n}/{d}" for n, d in row] if frac else [("%.5f" % v) for v in row]
        rows.append("[ " + ",  ".join(cells) + " ]")
    return "\n".join(rows)


def tol_scheme(site, key):
    ds = site.datasets.get("tol")
    for sch in (ds or {}).get("schemes") or []:
        if key in str(sch.get("id", "")).lower():
            return [c["hex"] for c in sch.get("colors") or []]
    return None


def comparison_table(site, lang, T):
    """Vergleichstabelle (4.1.8, 3.10 Abschnitt 6), beim Bau aus den Datensätzen gerechnet."""
    F = site.copy[lang]["frame"]
    rows = [("okabe-ito", site.refs.get("okabe-ito-7", {}).get("colors")), ("tol-bright", tol_scheme(site, "bright")),
            ("tol-muted", tol_scheme(site, "muted")), ("naive-rainbow", site.refs.get("naive-rainbow-7", {}).get("colors"))]
    head = "".join(f'<th scope="col">{esc(F["kind." + k])}</th>' for k in CMP_KINDS)
    body = []
    for rid, cols in rows:
        name = esc(T["s6.row." + rid])
        if not cols or len(cols) < 2:
            msg = f"Methode: Vergleichstabelle, Zeile {rid}: Datensatz fehlt"
            if not site.allow_missing:
                raise ValueError(msg)
            warn_once(site, msg)
            body.append(f'<tr><th scope="row">{name}</th><td colspan="{len(CMP_KINDS)}">{esc(T["s6.missing"])}</td></tr>')
            continue
        sw = "".join(f'<span class="sw" style="background:{c}"></span>' for c in cols)
        cells = []
        for k in CMP_KINDS:
            md = C.min_distance(cols, [k])
            v = C.render_text("{dist:" + md["a"] + "/" + md["b"] + "/" + k + "}", {}, lang, False)[0]
            cells.append(f'<td data-label="{esc(F["kind." + k])}">{v}<small>{md["a"]}/{md["b"]}</small></td>')
        body.append(f'<tr><th scope="row">{name}<span class="m-sw" aria-hidden="true">{sw}</span></th>{"".join(cells)}</tr>')
    # eigener Name der scrollbaren Region, nicht derselbe wie der des Abschnitts (R4-16)
    return (f'<div class="cmp-wrap" role="region" tabindex="0" aria-label="{esc(TP.fill(T["tbl_l"], {"name": T["s6.h"]}))}"><table class="cmp"><thead><tr><th scope="col">{esc(T["s6.th"])}</th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def findings_table(site, lang, T):
    cfg = site.D.get("check") or {"findings": []}
    RR = {"lang": lang, "T": site.copy[lang]["frame"], "tc": {}, "sources": site.sources}
    rows = []
    for f in cfg["findings"]:
        r = site.rules.get(f["rule"])
        if r is None:
            continue
        rows.append(f'<tr><th scope="row">{esc(T["s9.name." + f["id"]])} <code>{esc(f["id"])}</code></th>'
                    f'<td data-label="{esc(T["s9.th.l"])}">{TP.level_tags(RR, r)}</td><td data-label="{esc(T["s9.th.s"])}">{TP.source_links(RR, r)}</td></tr>')
    return (f'<div class="cmp-wrap" role="region" tabindex="0" aria-label="{esc(TP.fill(T["tbl_l"], {"name": T["s9.h"]}))}"><table class="cmp"><thead><tr><th scope="col">{esc(T["s9.th.f"])}</th><th scope="col">{esc(T["s9.th.l"])}</th>'
            f'<th scope="col">{esc(T["s9.th.s"])}</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def gate_state(site, T, g):
    """Stand eines Release-Gates. Beim Gate models kommt der Stand je Bildmodell aus data/models.json (P4), beim Gate office
    der Stand der Menüwege aus der Aufgabe slides (P3); die Office-Bezeichnungen selbst bleiben beim Stand aus COPY."""
    models = (site.D.get("models") or {}).get("models") or []
    if g.get("id") == "models" and models:
        # Ist die gelesene Doku eine Archivfassung (data/models.json, checked = Datum der Archivfassung), steht das dabei
        return (T["gate_models"] + " " + ", ".join(esc(f'{m.get("name", m.get("id"))} {m.get("checked")}')
                                                   + (" " + T["gate_archive"] if "://web.archive.org/" in str(m.get("source")) else "")
                                                   for m in models) + ". " + T["gate_state"] + " " + g["state"])
    paths = [m for m in (site.task_by_id.get("slides") or {}).get("menu_paths") or [] if m.get("checked")]
    if g.get("id") == "office" and paths:
        return T["gate_office"] + " " + ", ".join(esc(f'{m["app"]} {m["checked"]}') for m in paths) + ". " + T["gate_state"] + " " + g["state"]
    return T["gate_state"] + " " + g["state"]


def page(site, lang):
    page_path = site.path(lang, "method")
    T = site.copy[lang]["method"]
    F = site.copy[lang]["frame"]
    H = site.copy[lang]["home"]
    tok, cnt = tokens(site, lang), counts(site)
    RR = {"lang": lang, "T": F, "tc": {}, "sources": site.sources}

    def P(key):
        return paras(site, lang, page_path, T[key], tok, cnt)
    k = site.D["files"]["color-constants"]
    cvd = site.D["files"]["cvd"]
    extra = {
        1: f'<p class="hint">{esc(T["s1.pre"])}</p><pre class="code" tabindex="0"><code>{esc(matrix_pre(k["srgb_to_xyz"], True))}</code></pre>',
        5: (f'<p class="hint">{esc(T["s5.pre"])}</p><pre class="code" tabindex="0"><code>'
            + esc("\n\n".join([F["kind.protan"] + "\n" + matrix_pre(cvd["vienot1999"]["protan"]),
                               F["kind.deutan"] + "\n" + matrix_pre(cvd["vienot1999"]["deutan"]),
                               F["kind.tritan"] + " (m1, m2, n)\n" + matrix_pre(cvd["brettel1997"]["tritan"]["m1"]) + "\n\n"
                               + matrix_pre(cvd["brettel1997"]["tritan"]["m2"]) + "\n\n" + matrix_pre([cvd["brettel1997"]["tritan"]["n"]])]))
            + "</code></pre>"),
        6: comparison_table(site, lang, T),
        8: ('<dl class="levels">' + "".join(f'<div><dt>{TP.level_tags(RR, {"level": lv})}</dt><dd>{esc(H["level." + lv])}</dd></div>'
                                           for lv in ("norm", "research", "convention", "unproven")) + "</dl>" + '<div class="prose">' + P("s8.after") + '</div>'),
        9: ('<dl class="levels">' + "".join(f'<div><dt><span class="tag-sub">{sym} {esc(site.copy[lang]["check"]["sev." + sv] if sv != "pass" else site.copy[lang]["check"]["rep.pass"])}</span></dt>'
                                           f'<dd>{esc(T["s9.sev." + sv])}</dd></div>'
                                           for sv, sym in (("fail", "■"), ("check", "▲"), ("note", "●"), ("pass", "✓"))) + "</dl>"
            + findings_table(site, lang, T) + '<div class="prose">' + P("s9.after") + '</div>'),
        10: '<ul class="plain">' + "".join(f"<li>{esc(x)}</li>" for x in T["s10.list"]) + "</ul>",
        11: '<ul class="m-own">' + "".join(f'<li>{TP.level_tags(RR, {"level": "convention", "own": True})} {text(site, lang, page_path, x, tok, cnt)}</li>'
                                          for x in T["s11.list"]) + "</ul>",
        16: ('<ul class="m-gates">' + "".join(f'<li>{esc(g["text"])} <small>{text(site, lang, page_path, gate_state(site, T, g), tok, cnt)}</small></li>'
                                            for g in T["s16.gates"])
             + "</ul>" + '<div class="prose">' + P("s16.after") + '</div>'),
    }
    out = [site.head(lang, page_path, T["title"], T["desc"], "method", main_class="t-method")]
    out.append(f'<section class="mast"><div class="wrap"><h1>{esc(T["h1"])}</h1><p class="lede">{esc(T["lede"])}</p></div></section>')
    toc = "".join(f'<li><a href="#m{i}">{esc(T[f"s{i}.h"])}</a></li>' for i in range(1, N_SECTIONS + 1))
    out.append(f'<div class="wrap m-page"><nav class="m-toc" aria-label="{esc(T["toc_l"])}"><ol class="plain">{toc}</ol></nav>')
    for i in range(1, N_SECTIONS + 1):
        out.append(f'<section class="m-sec" id="m{i}" aria-labelledby="m{i}-h"><h2 id="m{i}-h">{esc(T[f"s{i}.h"])}</h2>'
                   f'<div class="prose">{P(f"s{i}.p")}</div>{extra.get(i, "")}</section>')
    out.append("</div>")
    out.append(site.foot(lang, page_path, ["site.js", "ui/explained.js"]))  # Sprachlink mit Sprungziel
    return "".join(out)
