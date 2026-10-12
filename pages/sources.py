"""Seite Quellen und Lizenzen (Spezifikation 3.11, 9.4): Quellen nach Art, Datensätze, Pflichtvermerke,
Lizenzvolltexte (data/licenses/, auch die der mitgelieferten Schriften) und die Lizenzen dieses Projekts.

„Zitiert in“ entsteht invers aus den Regeln, den Erklärt-Einträgen, den Verweisen [[id]] der Methode und Quellen-IDs,
die eine Aufgabe direkt nennt (etwa menu_paths[].source). Regeln heißen dort nach Aufgabe und Regelanfang und verlinken
auf ihren Anker regel-<id> (pages/task.py, web/site.js).
Sprache fremder Teile aus den Daten, nie geraten: title_lang der Quelle („en“, „de“, „en/de“ für „English / Deutsch“)
und Zitate in [en]…[/en] bzw. [de]…[/de] in claim_* und unverified_*.
"""
import re

from tools import checks, color as C, export as X
from pages import method as M

esc = C.esc
GROUPS = (("norm", ("norm",)), ("spec", ("spec",)), ("paper", ("paper",)), ("lit", ("review", "book")),
          ("docs", ("docs",)), ("code", ("code",)), ("sec", ("press", "secondary")))
LICENSES = (("mit", "MIT.txt"), ("w3c", "W3C-Software-and-Document-2023.txt"), ("bsd", "BSD-3-Clause.txt"),
            ("apache", "Apache-2.0.txt"), ("ofl-inter", "OFL-1.1-Inter.txt"), ("ofl-plex", "OFL-1.1-IBM-Plex.txt"))


NAME_NL = re.compile(r"\b(van der|van den|van de)( [A-Z])")
MARK = re.compile(r"\[(de|en)\](.+?)\[/\1\]")


def foreign(s, lang):
    """Text Dritter: niederländische Namenszusätze (van der Walt) mit lang="nl", Zitate in [en]…[/en] und [de]…[/de]
    mit lang="en" bzw. lang="de" (die Anführungszeichen stehen außen und folgen der Sprache des Satzes)."""
    e = NAME_NL.sub(lambda m: f'<span lang="nl">{m.group(1)}</span>{m.group(2)}', esc(s))
    return MARK.sub(lambda m: m.group(2) if m.group(1) == lang else f'<span lang="{m.group(1)}">{m.group(2)}</span>', e)


def title_html(s, lang):
    """Quellentitel mit lang aus title_lang: „en“, „de“ oder „en/de“ für zweisprachige Titel „English / Deutsch“.
    Ausgezeichnet wird jeder Teil, dessen Sprache nicht die der Seite ist; null heißt sprachneutral (Dateiname)."""
    tl = s.get("title_lang")
    langs = tl.split("/") if tl else [None]
    parts = s["title"].split(" / ") if len(langs) > 1 else [s["title"]]
    out = []
    for part, pl in zip(parts, langs):
        e = foreign(part, lang)
        out.append(f'<span lang="{pl}">{e}</span>' if pl and pl != lang else e)
    return " / ".join(out)


QNUM = re.compile(r"(\d+(?:[.,]\d+)?)\s*:\s*1(?![0-9])")
THRESHOLDS = ("3:1", "4,5:1", "4.5:1", "7:1", "21:1")


def claim_html(site, lang, s):
    """Belegte Aussage der Quelle. Verhältnisse, die keine Schwelle sind, zitieren eine Zahl der Quelle (6.0 erlaubt das
    in claim_*): Sie stehen als <q class="qnum">, damit sie sich von den berechneten Zahlen der Seite (<data>)
    unterscheiden. Die ganze Aussage steht in einem Element mit data-claim; nur dort nimmt tests/test_honesty.py
    Quellzahlen von der x:1-Prüfung aus. Die eigene Rechnung daneben (6.7, Platzhalter 6.12) kommt aus
    calc_de/calc_en der Quelle oder, wenn die Quelle keine trägt, aus calc.<id> in web/copy/sources.py."""
    T = site.copy[lang]["sources"]
    html = foreign(s["claim_" + lang], lang)

    def q(m):
        if re.sub(r"\s", "", m.group(0)) in THRESHOLDS:
            return m.group(0)
        return f'<q class="qnum" title="{esc(T["qnum_t"])}">{m.group(1)}:1</q>'
    out = f'<span class="claim" data-claim>{QNUM.sub(q, html)}</span>'
    calc = s.get("calc_" + lang) or T.get("calc." + str(s.get("id")))
    if calc:
        out += f' <span class="src-calc">{esc(T["calc"])} {site.render(calc, {}, lang, True)}</span>'
    return out


def strings(o):
    """Alle Zeichenketten eines JSON-Baums."""
    if isinstance(o, str):
        return {o}
    vals = o.values() if isinstance(o, dict) else o if isinstance(o, list) else ()
    out = set()
    for v in vals:
        out |= strings(v)
    return out


def license_text(site, name):
    return (site.roots[0] / "data" / "licenses" / name).read_text(encoding="utf-8").rstrip("\n")


def method_citations(site, lang):
    """{quellen-id: [Abschnittsnummern]} aus den Texten der Methode."""
    T = site.copy[lang].get("method") or {}
    out = {}
    for i in range(1, M.N_SECTIONS + 1):
        for key in (f"s{i}.p", f"s{i}.after", f"s{i}.list", f"s{i}.gates"):
            for t in T.get(key) or []:
                if isinstance(t, dict):  # Release-Gate: Verweise stehen im Stand
                    t = t.get("state") or ""
                for sid in M.CITE.findall(t):
                    out.setdefault(sid, [])
                    if i not in out[sid]:
                        out[sid].append(i)
    return out


def rule_start(r, lang, words=8):
    """Anfang einer Regel für „Zitiert in“: der erste Satz bis zum ersten Platzhalter oder Code, höchstens words
    Wörter, gekürzt mit „…“. Klartext, ohne Zahlen aus Platzhaltern (die Quellenseite hat keine Palette)."""
    first = re.split(r"(?<=[.!?])\s", r["text_" + lang], maxsplit=1)[0]
    cut = re.split(r"[{`]", first, maxsplit=1)[0].rstrip(" ,:;(")
    w = cut.split()
    short = len(w) > words or cut != first
    return " ".join(w[:words]).rstrip(",:;") + (" …" if short else "")


def cited_in(site, lang, page, sid, mcite):
    T = site.copy[lang]["sources"]
    parts = []
    for rid, r in site.rules.items():
        if sid in (r.get("sources") or []) + (r.get("normative") or []) + (r.get("informative") or []):
            users = site.rule_users.get(rid) or []
            cfg = site.D.get("check") or {}
            where = None
            if users:
                task = site.task_by_id[users[0]]
                where = task["name_" + lang]
                # Anker der Regel, wenn sie bei Startpalette 1 sichtbar ist; sonst der Regelblock (show_if)
                pal = site.palettes[task["id"]][task["presets"][0]["id"]]
                anchor = "#regel-" + rid if X.show_if(r.get("show_if"), pal) else "#regeln"
                href = site.rel(page, site.path(lang, users[0])) + anchor
            elif any(f.get("rule") == rid or f.get("also") == rid for f in cfg.get("findings") or []):
                where = site.copy[lang]["ui"]["page.check"]
                href = site.rel(page, site.path(lang, "check")) + "#regel-" + rid
            else:
                href = None
            label = esc(T["cited.rule"].replace("{task}", where or "").replace("{text}", rule_start(r, lang))) if where else \
                f'{esc(T["cited.rule_bare"])} <code>{esc(rid)}</code>'
            parts.append(f'<a href="{href}">{label}</a>' if href else label)
    for eid, e in site.explain.items():
        if sid in (e.get("sources") or []):
            parts.append(f'<a href="{site.rel(page, site.path(lang, "explained"))}#{esc(eid)}">{esc(T["cited.explain"])}: {esc(e["title_" + lang])}</a>')
    for i in mcite.get(sid, []):
        title = site.copy[lang]["method"][f"s{i}.h"]
        parts.append(f'<a href="{site.rel(page, site.path(lang, "method"))}#m{i}">{esc(T["cited.method"])}: {esc(title)}</a>')
    for task in site.tasks:  # Verweise direkt in der Aufgabe, etwa menu_paths[].source (Präsentation)
        if sid in strings(task):
            parts.append(f'<a href="{site.rel(page, site.path(lang, task["id"]))}">{esc(T["cited.task"])}: {esc(task["name_" + lang])}</a>')
    return parts


def source_item(site, lang, page, sid, s, mcite):
    T, F = site.copy[lang]["sources"], site.copy[lang]["frame"]
    meta = []
    if s.get("authors"):
        meta.append(foreign(", ".join(s["authors"]), lang))
    if s.get("publisher"):
        meta.append(foreign(s["publisher"], lang))
    if s.get("date"):
        meta.append(esc(s["date"]))
    meta.append(esc(T["retrieved"]) + " " + esc(s["retrieved"]))
    meta.append(esc(F["access." + s["access"]]))
    if s.get("normative"):
        meta.append(esc(T["normative"]))
    un = s.get("unverified_" + lang)
    un_html = f'<p class="src-un"><b>{esc(T["unverified"])}</b> {foreign(un, lang)}</p>' if un else ""
    cit = cited_in(site, lang, page, sid, mcite)
    cit_html = " · ".join(cit) if cit else esc(T["cited.none"])
    return (f'<li class="src-item" id="{esc(sid)}"><p class="src-t"><a href="{esc(s["url"])}" rel="noopener">{title_html(s, lang)}</a></p>'
            f'<p class="src-meta">{" · ".join(meta)}</p><p><b>{esc(T["claim"])}</b> {claim_html(site, lang, s)}</p>{un_html}'
            f'<p class="src-meta">{esc(T["cited"])} {cit_html}</p></li>')


def dataset_block(site, lang, did, ds):
    T = site.copy[lang]["sources"]
    rows = []

    def row(k, v):
        rows.append(f"<div><dt>{esc(T[k])}</dt><dd>{v}</dd></div>")
    if ds.get("authors"):
        row("ds.authors", foreign(", ".join(ds["authors"]), lang))
    if ds.get("year"):
        row("ds.year", esc(ds["year"]))
    row("ds.source", f'<a href="{esc(ds["source_url"])}" rel="noopener">{esc(ds["source_url"])}</a>')
    row("ds.machine", f'<a href="{esc(ds["machine_source"])}" rel="noopener">{esc(ds["machine_source"])}</a>')
    row("ds.sha", f'<code class="sha">{esc(ds["machine_sha256"])}</code>')
    row("ds.retrieved", esc(ds["retrieved"]))
    row("ds.reliability", esc(T.get("rel." + ds["reliability"], ds["reliability"])))
    note = ds.get("license_note_" + lang)
    if ds["license"] == "none-stated":
        row("ds.license", esc(note or T["lic.none-stated"]))
    else:
        row("ds.license", esc(ds["license"]) + (" · " + esc(note) if note else ""))
    row("ds.attribution", foreign(ds["attribution"], lang))
    if ds.get("required_notice"):
        row("ds.notice", f'<q lang="en">{esc(ds["required_notice"])}</q>')
    return f'<section class="ds" id="ds-{esc(did)}"><h3>{esc(ds.get("name") or did)}</h3><dl class="ds-dl">{"".join(rows)}</dl></section>'


def notices_html(site, lang):
    T = site.copy[lang]["sources"]
    E = site.copy[lang]["export"]
    out = []
    # Der Pflichtsatz steht immer wörtlich da (9.4), aus dem Datensatz oder, solange er fehlt, aus tools/checks.py.
    cb = site.datasets.get("colorbrewer")
    notice = checks.COLORBREWER_NOTICE
    if cb is not None and cb.get("required_notice") != notice:
        raise ValueError("Quellen: required_notice von ColorBrewer ist nicht der wörtliche Pflichtsatz")
    if cb is None:
        msg = "Quellen: Datensatz colorbrewer fehlt, Pflichtsatz steht ohne Datensatz"
        if not site.allow_missing:
            raise ValueError(msg)
        M.warn_once(site, msg)
    out.append(f'<div class="ntc"><h3>{esc(T["n.colorbrewer"])}</h3><blockquote lang="en"><p>{esc(notice)}</p></blockquote>'
               f'<p class="hint">{esc(T["n.colorbrewer.extra"])}{"" if cb is not None else " " + esc(T["n.missing"])}</p></div>')
    # Der Tol-Vermerk ist der wörtliche englische Copyright-Satz aus tol_colors.py, auf beiden Seiten gleich.
    for did, key, nkey, nlang in (("okabe-ito", "n.okabe", "notice.okabe-ito", None), ("tol", "n.tol", "notice.tol", "en"),
                                  ("viridis", "n.viridis", "notice.viridis", None)):
        have = did in site.datasets
        if not have:
            msg = f"Quellen: Datensatz {did} fehlt, Vermerk steht ohne Datensatz"
            if not site.allow_missing:
                raise ValueError(msg)
            M.warn_once(site, msg)
        bq = f' lang="{nlang}"' if nlang and nlang != lang else ""
        out.append(f'<div class="ntc"><h3>{esc(T[key])}</h3><blockquote{bq}><p>{foreign(E[nkey], lang)}</p></blockquote><p class="hint">{T[key + ".extra"]}'
                   f'{"" if have else " " + esc(T["n.missing"])}</p></div>')
    return "".join(out)


def licenses_html(site, lang):
    T = site.copy[lang]["sources"]
    holder = ""
    lic = (site.roots[0] / "LICENSE").read_text(encoding="utf-8").splitlines()
    for line in lic:
        if line.startswith("Copyright"):
            holder = line.strip()
            break
    out = []
    for key, name in LICENSES:
        text = license_text(site, name)
        if key == "mit" and holder:
            text = text.replace("Copyright (c) <year> <copyright holders>", holder)
        if key == "bsd":
            text = text.replace("Copyright (c) <year> <owner>. ", T["lic.bsd.holder"]).replace("Copyright (c) <year> <owner>.", T["lic.bsd.holder"])
        pre = ""
        if key == "apache":
            pre = (f'<p class="hint">{esc(T["lic.colorbrewer"])}</p><pre class="code lic" lang="en" tabindex="0"><code>'
                   f'{esc(license_text(site, "ColorBrewer.txt"))}</code></pre>')
        if key == "w3c":
            pre = (f'<p class="hint">{esc(T["lic.w3c.hint"])}</p><pre class="code lic" lang="en" tabindex="0"><code>'
                   f'{esc(T["lic.w3c.text"])}\n\n{esc(T["lic.w3c.orig"])}\n\n{esc(T["lic.wcag.sw"])}\n\n{esc(T["lic.wcag.doc"])}</code></pre>')
        out.append(f'<section class="lic" id="lic-{key}"><h3>{esc(T["lic." + key])}</h3>{pre}'
                   f'<pre class="code lic" lang="en" tabindex="0"><code>{esc(text)}</code></pre></section>')
    return "".join(out)


def page(site, lang):
    page_path = site.path(lang, "sources")
    T = site.copy[lang]["sources"]
    out = [site.head(lang, page_path, T["title"], T["desc"], "sources", main_class="t-sources")]
    out.append(f'<section class="mast"><div class="wrap"><h1>{esc(T["h1"])}</h1><p class="lede">{esc(T["lede"])}</p></div></section>')
    toc = "".join(f'<li><a href="#{a}">{esc(T["toc." + b])}</a></li>' for a, b in
                  (("quellen-liste", "sources"), ("datensaetze", "datasets"), ("pflichtvermerke", "notices"), ("lizenztexte", "licenses"), ("projekt", "project")))
    out.append(f'<div class="wrap s-page"><nav class="m-toc" aria-label="{esc(T["toc_l"])}"><ol class="plain">{toc}</ol></nav>')
    mcite = method_citations(site, lang)
    groups = []
    for gid, kinds in GROUPS:
        items = sorted(((sid, s) for sid, s in site.sources.items() if s.get("kind") in kinds), key=lambda t: (t[1]["title"].lower(), t[0]))
        if items:
            groups.append(f'<section class="src-group"><h3>{esc(T["group." + gid])}</h3><ul class="src-list">'
                          + "".join(source_item(site, lang, page_path, sid, s, mcite) for sid, s in items) + "</ul></section>")
    body = "".join(groups) or f'<p class="note">{esc(T["none"])}</p>'
    out.append(f'<section class="sec" id="quellen-liste" aria-labelledby="quellen-h"><div class="sec-head"><h2 id="quellen-h">{esc(T["sources.h"])}</h2>'
               f'<p>{esc(T["sources.intro"])}</p></div><p class="hint src-note">{esc(T["claims_note"])}</p>{body}</section>')
    ds = "".join(dataset_block(site, lang, did, site.datasets[did]) for did in sorted(site.datasets))
    out.append(f'<section class="sec" id="datensaetze" aria-labelledby="ds-h"><div class="sec-head"><h2 id="ds-h">{esc(T["datasets.h"])}</h2>'
               f'<p>{esc(T["datasets.intro"])}</p></div>{ds}</section>')
    out.append(f'<section class="sec" id="pflichtvermerke" aria-labelledby="ntc-h"><div class="sec-head"><h2 id="ntc-h">{esc(T["notices.h"])}</h2>'
               f'<p>{esc(T["notices.intro"])}</p></div>{notices_html(site, lang)}</section>')
    out.append(f'<section class="sec" id="lizenztexte" aria-labelledby="lic-h"><div class="sec-head"><h2 id="lic-h">{esc(T["licenses.h"])}</h2>'
               f'<p>{esc(T["licenses.intro"])}</p></div>{licenses_html(site, lang)}</section>')
    links = T["project.links"]
    for k, (label, url) in {"cc_by": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
                            "cc0": ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
                            "ofl": ("SIL Open Font License 1.1", "https://openfontlicense.org/"),
                            "repo": ("LICENSE-CONTENT.md", "https://github.com/grundhofer/farbsprache/blob/main/LICENSE-CONTENT.md")}.items():
        links = links.replace("{" + k + "}", f'<a href="{url}" rel="noopener">{esc(label)}</a>')
    out.append(f'<section class="sec" id="projekt" aria-labelledby="proj-h"><div class="sec-head"><h2 id="proj-h">{esc(T["project.h"])}</h2></div>'
               f'<ul class="plain">{"".join(f"<li>{esc(x)}</li>" for x in T["project.list"])}</ul><p class="more">{links}</p></section>')
    out.append("</div>")
    out.append(site.foot(lang, page_path, ["site.js", "ui/explained.js"]))  # Sprachlink mit Sprungziel
    return "".join(out)
