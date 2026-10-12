"""Seite Palette prüfen (Spezifikation 3.8): Eingabe, Ergebnisblöcke 2 bis 8, Export (Block 9).

Statisch steht das Beispiel aus data/check.json, berechnet mit tools/check.py. Jede eigene Eingabe rechnet
web/check.js im Browser mit denselben Funktionen (web/ui/check.js bindet das DOM an). tests/check.test.cjs
vergleicht die JS-Ausgabe für das Beispiel Byte für Byte mit dem statischen HTML.
"""
from tools import check as CK, color as C
from pages import task as TP

esc = C.esc


def rule_ids(cfg):
    """Regeln der Befundarten (rule und also), in der Reihenfolge von data/check.json."""
    out = []
    for f in cfg["findings"]:
        for r in [f["rule"]] + ([f["also"]] if f.get("also") else []):
            if r not in out:
                out.append(r)
    return out


def make_r(site, lang, page):
    """Kontext für tools/check.py: Texte, Konfiguration, Regeln, Quellen, Vergleichswerte, Pfade."""
    cfg = site.D["check"]
    if not cfg:
        raise ValueError("data/check.json fehlt")
    rules = {r: site.rules[r] for r in rule_ids(cfg) if r in site.rules}
    missing = [r for r in rule_ids(cfg) if r not in site.rules]
    if missing:
        raise ValueError("Palette prüfen: Regeln fehlen: " + ", ".join(missing))
    src_ids = []
    for r in rules.values():
        for s in (r.get("normative") or []) + (r.get("informative") or []) + (r.get("sources") or []):
            if s not in src_ids and s in site.sources:
                src_ids.append(s)
    paths = {"explained": site.rel(page, site.path(lang, "explained")),
             "website": site.rel(page, site.path(lang, "website")),
             "charts": site.rel(page, site.path(lang, "charts"))}
    return {"lang": lang, "T": site.copy[lang]["check"], "F": site.copy[lang]["frame"], "refs": site.refs, "cfg": cfg,
            "rules": rules, "sources": {s: site.sources[s] for s in src_ids}, "comparisons": site.comparisons,
            "paths": paths, "url": site.abs_url(lang, "check"), "date": site.date}


def example(site, R):
    """Beispiel-Modell und URL mit Zustand."""
    cfg = R["cfg"]
    m = CK.analyze(CK.scan(cfg["example"], cfg), cfg, site.refs, {})
    R = dict(R, url=R["url"] + "?" + CK.query(m))
    return m, R


def rules_html(site, lang, R):
    T = site.copy[lang]["check"]
    RR = {"lang": lang, "T": site.copy[lang]["frame"], "tc": {}, "sources": site.sources}
    items = []
    for rid in rule_ids(R["cfg"]):
        r = site.rules[rid]
        text = C.render_text(r["text_" + lang], {"refs": site.refs}, lang, True)[0]
        items.append(f'<li class="rule" id="regel-{esc(rid)}" data-rule="{esc(rid)}"><div class="rule-h">{TP.level_tags(RR, r)}</div>'
                     f'<p>{text}</p>{TP.source_links(RR, r)}</li>')
    n = C.render_text(site.copy[lang]["frame"]["rules.summary"], {"counts": {"n": len(items)}}, lang, False)[0]
    return (f'<details class="blk blk-g chk-rules" id="regeln"><summary><h2>{n}</h2></summary>'
            f'<p class="hint">{esc(T["rules.h"])}</p><ul class="rules">{"".join(items)}</ul></details>')


def page(site, lang):
    page_path = site.path(lang, "check")
    T = site.copy[lang]["check"]
    R = make_r(site, lang, page_path)
    m, R_ex = example(site, R)
    results = CK.render(m, R_ex, {"example": True})
    exports = CK.export_html(m, R_ex)
    out = [site.head(lang, page_path, T["title"], T["desc"], "check", main_class="t-check")]
    out.append(f'<section class="mast"><div class="wrap"><h1>{esc(T["h1"])}</h1><p class="lede">{esc(T["lede"])}</p></div></section>')
    out.append('<div class="wrap chk" id="check">')
    out.append(f'<section class="chk-in js-only" aria-labelledby="chk-in-l"><label class="ctl-label" id="chk-in-l" for="chk-input">{esc(T["in.label"])}</label>'
               f'<textarea id="chk-input" class="chk-text" rows="5" placeholder="{esc(T["in.placeholder"])}" autocapitalize="off" autocomplete="off" '
               f'spellcheck="false" aria-describedby="chk-hint chk-count"></textarea>'
               f'<p class="hint" id="chk-hint">{esc(T["in.hint"])}</p>'
               f'<div class="chk-run"><button type="button" class="btn primary" id="chk-run">{esc(T["btn.check"])}</button>'
               f'<p class="hint" id="chk-count" aria-live="polite"></p></div></section>')
    out.append(f'<noscript><p class="note">{esc(T["noscript"])}</p></noscript>')
    out.append(f'<section class="sec chk-res" aria-labelledby="res-h"><div class="sec-head"><h2 id="res-h">{esc(T["res.h"])}</h2></div>'
               f'<div id="chk-out" data-show="light"><!--fs:chk-out-->{results}<!--/fs:chk-out--></div></section>')
    out.append(f'<section class="sec chk-exp" id="kopieren" aria-labelledby="kopieren-h"><div class="sec-head"><h2 id="kopieren-h">{esc(T["exp.h"])}</h2></div>'
               f'<div id="chk-exp"><!--fs:chk-exp-->{exports}<!--/fs:chk-exp--></div></section>')
    out.append(rules_html(site, lang, R))
    retrieved = max([s["retrieved"] for s in R["sources"].values()] or [site.date])
    F = R["F"]
    stand = (C.render_text(F["stand_build"], {"date": site.date}, lang, False)[0] + " "
             + C.render_text(F["stand_sources"], {"date": retrieved}, lang, False)[0])
    out.append(f'<p class="stand">{stand}</p>')
    out.append("</div>")
    data = {"v": 1, "lang": lang, "date": site.date, "cfg": R["cfg"], "T": T, "F": R["F"], "refs": site.refs,
            "comparisons": site.comparisons, "rules": R["rules"], "sources": R["sources"], "paths": R["paths"],
            "url": R["url"], "example_url": R_ex["url"]}
    out.append(site.jscript(data, "check-data"))
    out.append(site.foot(lang, page_path, ["color.js", "export.js", "check.js", "site.js", "ui/check.js"]))
    return "".join(out)
