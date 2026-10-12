"""Startseite (Spezifikation 2.5): eine Frage, sieben Aufgaben, Farbfeld, Vertrauensblock.

Die Kacheln entstehen aus data/tasks/_order.json. Fehlt eine Aufgabe (nur mit --allow-missing),
steht dort eine Platzhalterkachel. Die Mini-Vorschauen sind statisch: patterns/<task>-mini.svg,
gefüllt mit Startpalette 1 über --d-*-Variablen, ohne Neuberechnung im Browser.
"""
from tools import color as C

esc = C.esc
START = "oklch(0.48 0.08 215)"  # Startwert Petrol des Farbfelds (2.5)


def seed_line(c, lang, hx):
    """Berechnete Zeile unter dem Farbfeld: Kontrast zu Weiß und Schwarz und ein Satz aus drei Vorlagen."""
    ctx = {"roles": {"default": {"c": hx}}, "mode": "default"}
    line = C.render_text(c["line"], ctx, lang, False)[0]
    if C.contrast(hx, "#FFFFFF") >= 4.5:
        key = "use_white"
    elif C.contrast(hx, "#000000") >= 4.5:
        key = "use_dark"
    else:
        key = "use_none"
    return line + " " + c[key]


def tile(site, lang, page, tid):
    task = site.task_by_id.get(tid)
    href = site.rel(page, site.path(lang, tid))
    if task is None:
        c = site.copy[lang]["home"]
        return (f'<li><a class="tile missing" href="{href}"><span class="mini" aria-hidden="true"></span>'
                f'<span class="tile-t"><b>{esc(tid)}</b><span>{esc(c["missing"])}</span></span></a></li>')
    pal = site.palettes[tid][task["presets"][0]["id"]]
    mode = pal["modes"][0]
    vars_ = "".join(f"--d-{k}:{v};" for k, v in pal["roles"][mode].items())
    mini = site.pattern(tid, lang)["mini"]
    return (f'<li><a class="tile" href="{href}" data-carry><span class="mini" aria-hidden="true" style="{vars_}">{mini}</span>'
            f'<span class="tile-t"><b>{esc(task["name_" + lang])}</b><span>{esc(task["summary_" + lang])}</span></span>'
            f'<span class="arr" aria-hidden="true">→</span></a></li>')


def page(site, lang):
    page = site.path(lang, "home")
    c = site.copy[lang]["home"]
    T = site.copy[lang]["frame"]
    start = C.parse(START)["hex"]
    out = [site.head(lang, page, c["title"], c["desc"], "home", main_class="home")]

    seedbox = (f'<div class="seedbox js-only" data-home>'
               f'<label class="ctl-label" for="seed">{esc(c["seed_label"])}</label>'
               f'<div class="seed-row"><input id="seed" class="seed-input" type="text" placeholder="#11697A" autocapitalize="off" '
               f'autocomplete="off" spellcheck="false" enterkeyhint="done" aria-describedby="seed-hint seed-err">'
               f'<label class="btn pick"><input type="color" id="seed-pick" value="{start}"><span>{esc(T["pick"])}</span></label>'
               f'<button type="button" class="btn" data-seed-reset>{esc(T["reset"])}</button></div>'
               f'<p class="hint" id="seed-hint">{esc(T["seed.hint"])}</p><p class="err" id="seed-err" aria-live="polite"></p>'
               f'<p class="hint" id="seed-note" hidden></p>'
               f'<button type="button" class="chip last" data-last hidden></button>'
               f'<div class="seed-result"><span class="swatch big" id="seed-swatch" style="background:{start}"></span>'
               f'<p class="seed-line" id="seed-line" data-start="{start}">{seed_line(c, lang, start)}</p></div></div>')
    out.append(f'<section class="mast"><div class="wrap mast-in">'
               f'<div><p class="eyebrow">{esc(c["eyebrow"])}</p><h1>{c["h1"]}</h1><p class="lede">{c["lede"]}</p></div>'
               f'{seedbox}</div></section>')

    tiles = "".join(tile(site, lang, page, tid) for tid in site.order)
    box = (f'<li class="tile-box"><h2>{esc(c["box_h"])}</h2><p>{esc(c["box_p"])}</p>'
           f'<a class="btn primary" href="{site.rel(page, site.path(lang, "check"))}">{esc(c["box_btn"])}</a></li>')
    out.append(f'<section class="wrap tasks-sec" aria-label="{esc(c["tiles_l"])}"><ul class="tiles">{tiles}{box}</ul>'
               f'<p class="print-line">{esc(c["print_line"])}</p></section>')

    facts = "".join(f'<div><b>{C.render_text("{count:" + k + "}", {"counts": site.counts}, lang, False)[0]}</b>'
                    f'<span>{esc(c["fact." + k])}</span></div>' for k in ("pairs", "presets", "sources"))
    levels = "".join(f'<div><dt><span class="tag-level">{esc(T["level." + k])}</span></dt><dd>{esc(c["level." + k])}</dd></div>'
                     for k in ("norm", "research", "convention", "unproven"))
    out.append(f'<section class="wrap sec trust" aria-labelledby="trust-h"><div class="sec-head"><h2 id="trust-h">{esc(c["trust_h"])}</h2>'
               f'<p>{esc(c["trust_p"])}</p></div><div class="facts">{facts}</div><dl class="levels">{levels}</dl>'
               f'<p class="more"><a href="{site.rel(page, site.path(lang, "method"))}">{esc(c["method_link"])}</a></p></section>')
    out.append(site.jscript({"line": c["line"], "use_white": c["use_white"], "use_dark": c["use_dark"],
                             "use_none": c["use_none"], "start": start}, "home-data"))
    out.append(site.foot(lang, page, ["color.js", "site.js"]))
    return "".join(out)
