"""Seite Kurz erklärt: alle Einträge aus data/explain/*.json in der Reihenfolge von
data/explain/_order.json, je mit Anker, Belegstufe, Text, Quellen und „Steht bei“ (invers aus den Aufgaben).

Einziges Demo in v1: context („Gleiche Farbe, anderer Eindruck“), Muster patterns/demo-context.html.
Vertrag mit dem Muster: Die Seite setzt am Element .demo.demo-context je Eintrag in demo_vars des Erklärt-Eintrags
(Eingaben, etwa {"ground-a": "oklch(0.70 0.18 55)", …}) die Variable --d-<name> als beim Bau berechnetes Hex und das
Attribut data-bridge="off|on"; der Knopf „Brücke zeigen“ (web/ui/explained.js) schaltet es um. Fehlt demo_vars, gelten
die Eingaben aus DEMOS. Die Bildunterschrift nennt das Hex der Farbe, die kein Grund ist.
Texte {{schlüssel}} kommen aus pattern.<schlüssel>.
"""
import re

from tools import color as C
from pages import method as M, task as TP

esc = C.esc
# Eingaben der Demo, keine Messwerte: zwei Gründe und ein Grau darauf
DEMOS = {"context": {"ground-a": "oklch(0.70 0.18 55)", "ground-b": "oklch(0.50 0.18 260)", "sample": "oklch(0.62 0 0)"}}


def pattern_text(site, lang, key):
    """Text zu {{key}}: zuerst Kurz erklärt, dann jede andere Seite mit pattern.<key> (etwa die Texte einer Aufgabe)."""
    own = site.copy[lang].get("explained", {})
    if "pattern." + key in own:
        return own["pattern." + key]
    for page in sorted(site.copy[lang]):
        if "pattern." + key in site.copy[lang][page]:
            return site.copy[lang][page]["pattern." + key]
    M.warn_once(site, f"Kurz erklärt: Text pattern.{key} für das Demo fehlt ({lang})")
    return ""


def demo(site, lang, eid, did, given=None):
    """(Stil für den Kopf, HTML des Demos) oder ("", "") ohne Muster. given: demo_vars des Eintrags."""
    src = (site.D.get("extra_patterns") or {}).get(f"patterns/demo-{did}.html")
    if src is None:
        M.warn_once(site, f"Kurz erklärt {eid}: Muster patterns/demo-{did}.html fehlt, Demo ausgelassen")
        return "", ""
    T = site.copy[lang]["explained"]
    styles = "".join(f"<style>{s}</style>" for s in re.findall(r"<style[^>]*>(.*?)</style>", src, re.S | re.I))
    markup = re.sub(r"<style[^>]*>.*?</style>|<!--.*?-->", "", src, flags=re.S | re.I).strip()  # Kommentar des Musters nicht ausliefern
    markup = re.sub(r"\{\{([a-z0-9_.-]+)\}\}", lambda m: esc(pattern_text(site, lang, m.group(1))), markup)
    cols = {}
    for k, v in (given or DEMOS.get(did) or {}).items():
        p = C.parse(str(v), False)
        if p is None or not re.fullmatch(r"[a-z0-9-]+", k):
            raise ValueError(f"Kurz erklärt {eid}: demo_vars.{k} = {v!r} ist keine lesbare Farbe")
        cols[k] = p["hex"]
    style = "".join(f"--d-{k}:{v};" for k, v in cols.items())
    sample = [v for k, v in cols.items() if not k.startswith("ground")]
    cap = ""
    if sample:
        cap = '<p class="hint">' + C.render_text(T["demo.caption"].replace("{color}", "{hex:" + sample[0] + "}"), {}, lang, False)[0] + "</p>"
    html = (f'<div class="ex-demo"><div class="demo demo-{did}" data-bridge="off" style="{style}">{markup}</div>'
            f'<button type="button" class="btn js-only" data-bridge-toggle aria-pressed="false">{esc(T["demo.btn"])}</button>{cap}</div>')
    return styles, html


def users(site, lang, page, eid):
    """„Steht bei“: Aufgaben, die den Eintrag zeigen, und die Prüfseite, wenn data/check.json ihn nennt."""
    out = []
    for tid in site.explain_users.get(eid, []):
        t = site.task_by_id[tid]
        out.append(f'<a href="{site.rel(page, site.path(lang, tid))}">{esc(t["name_" + lang])}</a>')
    cfg = site.D.get("check") or {}
    if any(f.get("explain") == eid for f in cfg.get("findings") or []):
        out.append(f'<a href="{site.rel(page, site.path(lang, "check"))}">{esc(site.copy[lang]["ui"]["page.check"])}</a>')
    return out


def page(site, lang):
    page_path = site.path(lang, "explained")
    T = site.copy[lang]["explained"]
    F = site.copy[lang]["frame"]
    R = {"lang": lang, "T": F, "tc": {}, "sources": site.sources}
    ids = [e for e in site.explain_order if e in site.explain]
    styles, items, toc = [], [], []
    for eid in ids:
        e = site.explain[eid]
        body = "".join(f"<p>{C.render_text(par, {'refs': site.refs}, lang, True)[0]}</p>" for par in e["body_" + lang].split("\n\n"))
        dhtml = ""
        if e.get("demo"):
            st, dhtml = demo(site, lang, eid, e["demo"], e.get("demo_vars"))
            if st and st not in styles:
                styles.append(st)
        us = users(site, lang, page_path, eid)
        at = f'<p class="ex-at">{esc(T["at"])} ' + (" · ".join(us) if us else esc(T["at.none"])) + "</p>"
        items.append(f'<li class="ex-entry" id="{esc(eid)}"><h2>{esc(e["title_" + lang])}</h2>'
                     f'<div class="ex-head">{TP.level_tags(R, e)}</div><div class="prose">{body}</div>{dhtml}'
                     f'{TP.source_links(R, e)}{at}</li>')
        toc.append(f'<li><a href="#{esc(eid)}">{esc(e["title_" + lang])}</a></li>')
    out = [site.head(lang, page_path, T["title"], T["desc"], "explained", extra_head="".join(styles), main_class="t-explained")]
    out.append(f'<section class="mast"><div class="wrap"><h1>{esc(T["h1"])}</h1><p class="lede">{esc(T["lede"])}</p></div></section>')
    out.append('<div class="wrap ex-page">')
    if items:
        out.append(f'<nav class="ex-toc" aria-label="{esc(T["toc_l"])}"><ol class="plain">{"".join(toc)}</ol></nav>')
        out.append(f'<p class="hint ex-legend">{esc(T["legend"])}</p>')
        out.append(f'<ol class="ex-list">{"".join(items)}</ol>')
    else:
        out.append(f'<p class="note">{esc(T["empty"])}</p>')
    out.append("</div>")
    out.append(site.foot(lang, page_path, ["site.js", "ui/explained.js"]))
    return "".join(out)
