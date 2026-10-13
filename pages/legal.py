"""Seite Impressum: Angaben nach § 5 DDG und § 18 Abs. 2 MStV aus data/legal.json (die einzige Stelle im Repo),
Überschriften und Sätze aus web/copy/legal.py. Die Fußzeile jeder Seite, die Sprachweiche und die Fehlerseite verlinken
hierher (build.py). Die Anschrift bleibt deutsch; auf der englischen Seite trägt sie lang="de".
"""
import json
import re

from tools import color as C

esc = C.esc
FIELDS = ("name", "address", "email", "vat_id", "responsible")
ADDRESS_LANG = "de"
# Form der Angaben, ohne ihre Werte zu wiederholen: Vor- und Nachname, E-Mail-Adresse, deutsche Umsatzsteuer-ID
# (DE und neun Ziffern), Anschrift in vier Zeilen: c/o-Zeile (ihr gilt der Paket-Hinweis aus web/copy/legal.py),
# Straße mit Hausnummer, Postleitzahl mit Ort, Land. So fällt auch eine versehentlich gekürzte Angabe auf.
SHAPE = {"name": r"\S+(?: \S+)+", "responsible": r"\S+(?: \S+)+", "email": r"[^@\s]+@[^@\s]+\.[a-z]{2,}",
         "vat_id": r"DE\d{9}"}
ADDRESS = (r"c/o \S.*", r".*\S \d+[a-zA-Z]?", r"\d{5} \S.*", r"\D+")


def check(d):
    """Meldungen zu den Angaben aus data/legal.json (leer: alles in Ordnung)."""
    errs = [f"{k} fehlt oder ist leer" for k in FIELDS if not d.get(k)]
    errs += [f"{k} hat nicht die erwartete Form" for k, rx in SHAPE.items()
             if d.get(k) and not (isinstance(d[k], str) and re.fullmatch(rx, d[k]))]
    a = d.get("address")
    if a and not (isinstance(a, list) and len(a) == len(ADDRESS)
                  and all(isinstance(x, str) and re.fullmatch(rx, x) for x, rx in zip(a, ADDRESS))):
        errs.append("address: erwartet vier Zeilen (c/o, Straße mit Hausnummer, Postleitzahl mit Ort, Land)")
    return errs


def load(site):
    """data/legal.json lesen; fehlt eine Angabe oder hat sie nicht die erwartete Form, bricht der Build ab (kein
    Impressum mit Lücken)."""
    d = json.loads((site.roots[0] / "data" / "legal.json").read_text(encoding="utf-8"))
    errs = check(d)
    if errs:
        raise ValueError("data/legal.json: " + "; ".join(errs))
    return d


def postal(name, address, lang):
    lines = "<br>".join(esc(x) for x in address)
    if lang != ADDRESS_LANG:
        lines = f'<span lang="{ADDRESS_LANG}">{lines}</span>'
    return f"<p>{esc(name)}<br>{lines}</p>"


def page(site, lang):
    page_path = site.path(lang, "legal")
    T = site.copy[lang]["legal"]
    L = load(site)

    def sec(key, body):
        return f'<section class="lg-sec"><h2>{esc(T[key])}</h2>{body}</section>'
    out = [site.head(lang, page_path, T["title"], T["desc"], "legal", main_class="t-legal")]
    out.append(f'<section class="mast"><div class="wrap"><h1>{esc(T["h1"])}</h1></div></section>')
    out.append('<div class="wrap lg-page">')
    out.append(sec("h.provider", postal(L["name"], L["address"], lang) + f'<p>{esc(T["parcels"])}</p>'))
    out.append(sec("h.contact", f'<p>{esc(T["email"])} <a href="mailto:{esc(L["email"])}">{esc(L["email"])}</a></p>'))
    out.append(sec("h.vat", f'<p>{esc(T["vat"])}<br>{esc(L["vat_id"])}</p>'))
    out.append(sec("h.responsible", postal(L["responsible"], L["address"], lang)))
    out.append("</div>")
    out.append(site.foot(lang, page_path))
    return "".join(out)
