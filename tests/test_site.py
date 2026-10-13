"""Gebaute Website (Spezifikation 7.9, Muster Bildsprache test_site und Designsprache test_explorer):
13 Seiten je Sprache, interne Links lösen auf, eindeutige IDs, html lang, <title>, alt, genau ein h1 und ein
main, og:image absolut, keine typischen deutschen Wörter im sichtbaren EN-Text, Größenbudget (7.11),
README ohne __N_, Impressum und Schwesterprojekte von jeder Seite aus verlinkt. Läuft über docs/ und die Testaufgabe;
ohne Build übersprungen, außer FARBSPRACHE_REQUIRE_BUILD=1 (CI), dann schlägt er fehl."""
import hashlib, html, html.parser, json, os, re, sys, unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

DOCS = ROOT / "docs"
FIX = ROOT / "tests" / "out" / "fixtures" / "docs"
REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
# klein oder am Satzanfang groß geschrieben; „MIT“ (die Lizenz) zählt nicht
GERMAN_WORDS = {"und", "der", "die", "das", "nicht", "mit", "für"}
GERMAN_WORDS |= {w.capitalize() for w in GERMAN_WORDS}
WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# task nach Z von 200 auf 240 KB angehoben (Spezifikation 7.11): #task-data ist schon auf die Felder gekürzt, die
# site.js liest, die größte Seite (Website) läge sonst nur rund 5 % unter der Grenze.
BUDGET = {"task": 240 * 1024, "home": 80 * 1024, "js": 160 * 1024, "css": 40 * 1024}


# Selbst ausgelieferte Schriften (R-02/T-04): je Datei höchstens 32 KB, zusammen höchstens 160 KB
FONT_BUDGET = {"file": 32 * 1024, "all": 160 * 1024}


def css_rules(css):
    """(Selektor, Deklarationen) der innersten Regeln, @media-Klammern übersprungen; Kommentare entfernt."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def shipped_css():
    return (DOCS / "assets" / "site.css").read_text(encoding="utf-8")


class Collector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.lang, self.no_alt, self.h1, self.main = [], [], None, 0, 0, 0
        self.stack, self.en_text, self.og_image, self.scripts = [], [], None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "img":
            self.refs.append(a.get("src"))
            if a.get("alt") is None:
                self.no_alt += 1
        if tag in ("a", "link") and a.get("href"):
            self.refs.append(a["href"])
        if tag == "script" and a.get("src"):
            self.refs.append(a["src"])
            self.scripts.append(a["src"])
        if tag == "meta" and a.get("property") == "og:image":
            self.og_image = a.get("content")
        if a.get("id"):
            self.ids.append(a["id"])
        self.h1 += tag == "h1"
        self.main += tag == "main"
        if tag not in VOID:
            self.stack.append((tag, a.get("lang")))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            if self.stack.pop()[0] == tag:
                break

    def handle_data(self, data):
        tags = [t for t, _ in self.stack]
        if any(t in ("script", "style", "pre", "code") for t in tags):
            return
        langs = [lg for _, lg in self.stack if lg]
        if (langs[-1] if langs else self.lang) == "en":
            self.en_text.append(data)


def parse(f):
    c = Collector()
    c.feed(f.read_text(encoding="utf-8"))
    return c


def lang_pages(site):
    return sorted(p for lang in ("de", "en") for p in (site / lang).rglob("index.html"))


def resolve(site, page, ref):
    ref = ref.split("#")[0].split("?")[0]
    if ref.startswith("/farbsprache/"):
        target = site / ref[len("/farbsprache/"):]
    else:
        target = (page.parent / ref).resolve()
    if target.is_dir():
        target = target / "index.html"
    return target


@unittest.skipUnless(REQUIRE or (DOCS / "de" / "index.html").exists(), "docs/ fehlt – erst python3 build.py --fixtures")
class TestSite(unittest.TestCase):
    def sites(self):
        return [s for s in (DOCS, FIX) if (s / "de" / "index.html").exists()]

    def test_built(self):
        self.assertTrue((DOCS / "de" / "index.html").exists(), "docs/ fehlt (python3 build.py)")
        self.assertTrue((FIX / "de" / "index.html").exists(), "Testaufgabe fehlt (python3 build.py --fixtures)")

    def test_pages_per_language(self):
        for lang in ("de", "en"):
            self.assertEqual(len(list((DOCS / lang).rglob("index.html"))), build.N_PAGES_PER_LANG, lang)
        for f in ("index.html", "404.html", "og.png", ".nojekyll", "assets/site.css", "assets/site.js", "assets/color.js"):
            if f == "og.png" and not (ROOT / "og.png").exists():
                continue
            self.assertTrue((DOCS / f).exists(), f)
        de = [p.relative_to(DOCS / "de") for p in (DOCS / "de").rglob("index.html")]
        self.assertEqual(len(de), len(list((DOCS / "en").rglob("index.html"))))

    def test_internal_links_resolve(self):
        missing = []
        for site in self.sites():
            for page in sorted(site.rglob("*.html")):
                for ref in parse(page).refs:
                    if not ref or re.match(r"^(https?:|mailto:|data:|#)", ref):
                        continue
                    if not resolve(site, page, ref).exists():
                        missing.append(f"{page.relative_to(ROOT)} -> {ref}")
        self.assertEqual(missing[:20], [])

    def test_internal_fragments_resolve(self):
        """Sprungziele interner Links gibt es auf der Zielseite, etwa #regel-<id> aus „Zitiert in“ (T-11). Nur die echte
        Website: Im Fixture-Bau sind Kurz erklärt und Quellen Platzhalter ohne Einträge."""
        missing, n = [], 0
        for site in (DOCS,):
            ids = {}
            for page in sorted(site.rglob("*.html")):
                for ref in parse(page).refs:
                    if not ref or "#" not in ref or re.match(r"^(https?:|mailto:|data:)", ref):
                        continue
                    frag = ref.split("#", 1)[1]
                    target = page if ref.startswith("#") else resolve(site, page, ref)
                    if not frag or not target.exists():
                        continue
                    if target not in ids:
                        ids[target] = set(parse(target).ids)
                    n += 1
                    if frag not in ids[target]:
                        missing.append(f"{page.relative_to(ROOT)} -> {ref}")
        self.assertGreater(n, 100)
        self.assertEqual(missing[:20], [])

    def test_no_internal_notes_shipped(self):
        """R-12, T-06: research/ wird nicht veröffentlicht. Keine Seite und kein Skript verweist auf die Spezifikation
        oder interne Arbeitspakete, auch nicht in eingebetteten Daten (_comment fällt beim Bau weg)."""
        bad = re.compile(r"Spezifikation \d|Bauspezifikation|specification \d|build specification|Arbeitspaket|"
                         r"[Ww]ork package|Eigentümer P\d|\bP0\b|\"_comment\"")
        for f in sorted(DOCS.rglob("*.html")) + sorted(DOCS.rglob("*.js")):
            m = bad.search(f.read_text(encoding="utf-8"))
            self.assertIsNone(m, f"{f.relative_to(ROOT)}: {m and m.group(0)}")
        # nur Skripte: nackte Abschnittsnummern wie „(4.1.7)“ und Paketnamen (im HTML stehen legitime WCAG-Nummern)
        for f in sorted(DOCS.rglob("*.js")):
            m = re.search(r"\(\d\.\d+(\.\d+)?\)|\bPaket\b", f.read_text(encoding="utf-8"))
            self.assertIsNone(m, f"{f.relative_to(ROOT)}: {m and m.group(0)}")

    def test_page_structure(self):
        for site in self.sites():
            for page in lang_pages(site):
                c = parse(page)
                text = page.read_text(encoding="utf-8")
                with self.subTest(page=str(page.relative_to(ROOT))):
                    self.assertIn(c.lang, ("de", "en"))
                    self.assertRegex(text, r"<title>[^<]{5,}</title>")
                    self.assertEqual(c.no_alt, 0)
                    self.assertEqual(len(c.ids), len(set(c.ids)), "doppelte id: " + ", ".join(sorted({i for i in c.ids if c.ids.count(i) > 1})))
                    self.assertEqual(c.h1, 1, "genau ein h1")
                    self.assertEqual(c.main, 1, "genau ein main")
                    self.assertTrue(c.og_image and c.og_image.startswith("https://"), "og:image absolut")
                    self.assertIn("farbsprache.language", text, "Sprachwahl merken")
                    self.assertIn('rel="canonical"', text)
            for f in ("index.html", "404.html"):
                c = parse(site / f)
                with self.subTest(page=f):
                    self.assertEqual(len(c.ids), len(set(c.ids)))
                    self.assertEqual(c.h1, 1)
        nf = (DOCS / "404.html").read_text(encoding="utf-8")
        self.assertIn('href="/farbsprache/de/"', nf)
        self.assertIn('href="/farbsprache/en/"', nf)
        self.assertTrue(parse(DOCS / "index.html").og_image.startswith("https://"))

    def test_no_german_in_english_text(self):
        for site in self.sites():
            for page in sorted((site / "en").rglob("index.html")):
                words = [w for w in WORD.findall(" ".join(parse(page).en_text)) if w in GERMAN_WORDS]
                with self.subTest(page=str(page.relative_to(ROOT))):
                    self.assertEqual(words, [])

    def test_size_budget(self):
        css = (DOCS / "assets" / "site.css").stat().st_size
        self.assertLessEqual(css, BUDGET["css"], "site.css")
        for site in self.sites():
            for page in lang_pages(site):
                text = page.read_text(encoding="utf-8")
                size = len(text.encode("utf-8"))
                with self.subTest(page=str(page.relative_to(ROOT))):
                    if 'id="task-data"' in text:
                        self.assertLessEqual(size, BUDGET["task"], "HTML der Aufgabenseite")
                    if 'id="task-data"' in text or 'id="check-data"' in text:  # auch die Prüfseite lädt den Farbkern
                        js = sum(resolve(site, page, s).stat().st_size for s in parse(page).scripts)
                        self.assertLessEqual(js, BUDGET["js"], f"JS der Aufgaben- oder Prüfseite: {js} Bytes")
                    elif page.parent.name in ("de", "en"):
                        self.assertLessEqual(size, BUDGET["home"], "HTML der Startseite")

    def test_readmes(self):
        for name in ("README.md", "README.de.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("__N_", text, name)
        for f in DOCS.rglob("*"):
            if f.suffix in (".html", ".js", ".css"):
                self.assertNotIn("__N_", f.read_text(encoding="utf-8"), str(f))

    def test_no_requests_to_other_hosts(self):
        """R-02/T-04: Keine Seite lädt etwas von fremden Servern, auch keine Schrift (Links zum Folgen sind erlaubt)."""
        bad = []
        for site in self.sites():
            for page in sorted(site.rglob("*.html")):
                text = page.read_text(encoding="utf-8")
                for tag, attr, val in re.findall(r"<(link|script|img|iframe|source|video|audio)\b([^>]*?)\b(?:href|src)=\"([^\"]+)\"", text):
                    if re.match(r"(https?:)?//", val) and not re.search(r'rel="(canonical|alternate)"', attr):
                        bad.append(f"{page.relative_to(ROOT)}: <{tag} {val}>")
                if re.search(r"googleapis|gstatic", text):
                    bad.append(f"{page.relative_to(ROOT)}: Google Fonts")
        css = shipped_css()
        self.assertNotIn("@import", css)
        self.assertEqual(re.findall(r"url\((?!fonts/)[^)]*\)", css), [], "url() nur für mitgelieferte Schriften")
        self.assertEqual(bad[:10], [])

    def test_fonts_shipped(self):
        """R-02/T-04: Inter 400/500/700 und IBM Plex Mono 400/500 als woff2 unter assets/fonts/, font-display:swap,
        versioniert; die Vorladelinks zeigen auf genau die Dateien aus site.css; OFL-Texte liegen bei; Budget;
        Sprachweiche und 404 nennen nur Systemschriften."""
        css = shipped_css()
        faces = [d for s, d in css_rules(css) if s == "@font-face"]
        got = {(re.search(r'font-family:"([^"]+)"', d).group(1), re.search(r"font-weight:(\d+)", d).group(1)) for d in faces}
        self.assertEqual(got, {("Inter", "400"), ("Inter", "500"), ("Inter", "700"), ("IBM Plex Mono", "400"), ("IBM Plex Mono", "500")})
        total = 0
        for d in faces:
            self.assertIn("font-display:swap", d)
            for name, ver in re.findall(r"url\(fonts/([^)?]+\.woff2)\?v=([0-9a-f]{10})\)", d):
                f = DOCS / "assets" / "fonts" / name
                self.assertTrue(f.exists(), name)
                self.assertEqual(build.asset_version(f.read_bytes()), ver, name)
                self.assertLessEqual(f.stat().st_size, FONT_BUDGET["file"], name)
                total += f.stat().st_size
        self.assertLessEqual(total, FONT_BUDGET["all"])
        for name in build.FONT_LICENSES:
            self.assertEqual((DOCS / "assets" / "fonts" / name).read_bytes(), (ROOT / "data" / "licenses" / name).read_bytes())
        # Herkunft: CONTRIBUTING nennt die Prüfsumme jeder mitgelieferten Datei (Abschnitt Schriften, deutsch und englisch)
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for f in sorted((ROOT / "web" / "fonts").glob("*.woff2")):
            self.assertEqual(contributing.count(f"| `{f.name}` | `{hashlib.sha256(f.read_bytes()).hexdigest()}` |"), 2, f.name)
        for page in lang_pages(DOCS):
            pre = re.findall(r'<link rel="preload" href="([^"]+)" as="font" type="font/woff2" crossorigin>', page.read_text(encoding="utf-8"))
            self.assertEqual(len(pre), len(build.PRELOAD_FONTS), str(page))
            for href in pre:
                self.assertIn("url(fonts/" + href.split("assets/fonts/")[1] + ")", css, href)
        # Sprachweiche und 404 laden kein site.css: Ihr Inline-CSS nennt keine Schrift, die nur site.css mitliefert
        for site in self.sites():
            for f in ("index.html", "404.html"):
                text = (site / f).read_text(encoding="utf-8")
                with self.subTest(page=str((site / f).relative_to(ROOT))):
                    self.assertNotRegex(text, r"<link\b[^>]*stylesheet")
                    self.assertNotRegex(" ".join(re.findall(r"<style>(.*?)</style>", text, re.S)), r"\b(Inter|IBM Plex)\b")

    def test_w3c_notice_shipped(self):
        """Material aus CSS Color 4 (W3C Software and Document License): Vermerk in der ersten Zeile der ausgelieferten
        color.js, wörtlich gleich auf der Quellenseite, Lizenztext im Repo."""
        from web.copy import sources as SOURCES
        first = (DOCS / "assets" / "color.js").read_text(encoding="utf-8").split("\n", 1)[0]
        self.assertEqual(first, "/* " + build.W3C_NOTICE + " " + build.WCAG_NOTICE + " */")
        self.assertTrue((ROOT / "data" / "licenses" / "W3C-Software-and-Document-2023.txt").exists())
        for lang in ("de", "en"):
            self.assertEqual(SOURCES.COPY[lang]["sources"]["lic.w3c.text"], build.W3C_NOTICE, lang)
            self.assertEqual(SOURCES.COPY[lang]["sources"]["lic.wcag.sw"], build.WCAG_NOTICE, lang)

    def test_buttons_hidden_without_js(self):
        """R4-12/T-17: Ohne JS tut kein Knopf etwas (alle sind type=button); site.css blendet sie, die Reiterleiste und die
        leere Steuerleiste aus. Palette und Exporte bleiben lesbar."""
        hidden = {s.strip() for sel, d in css_rules(shipped_css()) if "display:none" in d.replace(" ", "") for s in sel.split(",")}
        for sel in ("html:not(.js) button", "html:not(.js) .tabs", "html:not(.js) .task-bar", "html:not(.js) .js-only"):
            self.assertIn(sel, hidden)
        for page in lang_pages(DOCS):
            text = page.read_text(encoding="utf-8")
            self.assertEqual(re.findall(r'<button(?![^>]*type="button")[^>]*>', text), [], f"{page}: Knopf ohne type=button")

    def test_disclosure_marker_not_in_name(self):
        """R4-07/M-01: Jeder Aufklapper mit eigener Darstellung zeigt + und −; das Zeichen hat einen leeren Alternativtext,
        damit es nicht im zugänglichen Namen landet."""
        rules = css_rules(shipped_css())
        flex = {re.sub(r"\s*>\s*", " > ", s.strip()) for sel, d in rules if re.search(r"display:\s*(inline-)?flex", d) for s in sel.split(",") if "summary" in s and "::" not in s}
        marked = {re.sub(r"\s*>\s*", " > ", s.strip()).replace("::before", "") for sel, d in rules if "content:" in d for s in sel.split(",") if "summary::before" in s}
        for sel, d in rules:
            if "summary::before" in sel and "content:" in d:
                self.assertRegex(d, r'content:\s*"[^"]*"\s*/\s*""', sel)
        for s in flex:
            base = s.replace(" > summary", "").replace(" summary", "")
            self.assertTrue(any(m.startswith(base) for m in marked), f"{s}: kein + / −")

    def test_target_sizes(self):
        """R4-08/T-08, Spezifikation 2.2 und 11: Trefferflächen mindestens 44 px, auch in der Kopfleiste unter 600 px, für Chips,
        „Mehr dazu →“, Fußzeilen-, Inhaltsverzeichnis- und Quellenlinks und die Brotkrumen."""
        rules = css_rules(shipped_css())
        self.assertEqual([s for s, d in rules if re.search(r"min-(height|width):\s*(\d|[1-3]\d|4[0-3])px", d)], [], "keine Mindestgröße unter 44 px")
        def decl(sel):
            return " ".join(d for s, d in rules if sel in [x.strip() for x in s.split(",")])
        for sel in (".ex-more a", ".more a", "footer.foot a", ".t-sources .m-toc a", ".t-explained .ex-toc a", ".tb-lang a", ".theme-switch button", ".tb-brand"):
            self.assertRegex(decl(sel), r"min-height:44px", sel)
        for sel in (".chip", ".tb-lang a", ".theme-switch button"):
            self.assertIn("min-width:44px", decl(sel), sel)
        crumbs = decl(".crumbs a").replace(" ", "")
        self.assertIn("padding:15px6px", crumbs)  # 15 + Zeile + 15 ≥ 44 und 6 + Wort + 6, ohne höhere Zeile (margin:-15px -6px)
        self.assertIn("margin:-15px-6px", crumbs)
        self.assertIn("position:relative", crumbs)

    def test_placeholder_contrast(self):
        """R4-11: Platzhalter in --ink-3 (tests/test_theme.py: 4,5:1 in beiden Themes), ohne abgeschwächte Deckkraft."""
        ph = [d for s, d in css_rules(shipped_css()) if s.strip() == "::placeholder"]
        self.assertEqual(len(ph), 1)
        self.assertIn("color:var(--ink-3)", ph[0].replace(" ", ""))
        self.assertIn("opacity:1", ph[0].replace(" ", ""))

    def test_form_fields_16px(self):
        """T-09, Spezifikation 7.7: Eingaben 16 px (kein Zoom auf iOS). Felder: input, select, textarea und jede Klasse, die
        der Rahmen oder ein Paket einem solchen Element gibt (auch per JS gerendert, etwa select.rl-sel)."""
        classes = set()
        for f in list((ROOT / "web").rglob("*.js")) + list((ROOT / "pages").glob("*.py")) + list((ROOT / "tools").glob("*.py")):
            for m in re.finditer(r"<(?:input|select|textarea)\b[^>]*?class=\\?[\"']([^\"'\\]+)", f.read_text(encoding="utf-8")):
                classes |= set(m.group(1).split())
        classes -= {"pick"}  # Farbwähler ohne Text
        bad = []
        for sel, d in css_rules(shipped_css()):
            for s in sel.split(","):
                last = s.strip().split(" ")[-1]
                if "::" in last or ":" in last.replace(":not(", ""):
                    continue
                if re.match(r"(input|select|textarea)\b", last) or any(re.search(r"\." + re.escape(c) + r"\b", last) for c in classes):
                    m = re.search(r"font(?:-size)?:[^;]*?(\d+(?:\.\d+)?)px", d)
                    if m and float(m.group(1)) < 16:
                        bad.append(f"{s.strip()}: {m.group(1)}px")
        self.assertEqual(bad, [])

    def test_patterns_have_no_controls(self):
        """R4-13/M-01: Muster sind Vorschauen; keine Links, Knöpfe, Felder oder Tabstopps darin."""
        for f in sorted((ROOT / "patterns").glob("*.html")):
            text = f.read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"<(a|button|input|select|textarea)\b|tabindex", text), [], f.name)

    def test_heading_levels_without_gaps(self):
        """R4-16: Auf keiner Seite springt die Überschriftenebene nach unten um mehr als eins (h2 → h4)."""
        for site in self.sites():
            for page in lang_pages(site):
                text = page.read_text(encoding="utf-8")
                text = re.sub(r"<script.*?</script>|<template.*?</template>", "", text, flags=re.S)
                levels = [int(n) for n in re.findall(r"<h([1-6])\b", text)]
                jumps = [(a, b) for a, b in zip(levels, levels[1:]) if b > a + 1]
                with self.subTest(page=str(page.relative_to(ROOT))):
                    self.assertEqual(jumps, [])

    def test_region_names_unique(self):
        """R4-16: Regionen tragen eindeutige Namen (eine Tabelle heißt nicht wie ihr Abschnitt)."""
        for page in lang_pages(DOCS):
            text = page.read_text(encoding="utf-8")
            names = []
            for m in re.finditer(r'<section[^>]*aria-labelledby="([^"]+)"', text):
                h = re.search(r'id="' + re.escape(m.group(1)) + r'"[^>]*>(.*?)</h[1-6]>', text, re.S)
                if h:
                    names.append(re.sub(r"<[^>]+>", "", h.group(1)).strip())
            names += [html.unescape(n) for n in re.findall(r'role="region"[^>]*aria-label="([^"]+)"', text)]
            dup = sorted({n for n in names if names.count(n) > 1})
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(dup, [])

    def test_color_and_text_controls(self):
        """T-06: Textfelder höchstens 200 Zeichen. T-07: Farbsteuerelemente mit Fehlerzeile, die das Feld beschreibt.
        T-20: Ein leeres Farbsteuerelement zeigt im Wähler keine Farbe (data-empty)."""
        seen = set()
        for page in lang_pages(DOCS):
            text = page.read_text(encoding="utf-8")
            for part in text.split('<div class="ctl" data-ctl="')[1:]:
                m = re.match(r'([^"]+)" data-type="([a-z]+)">', part)
                cid, typ, body = m.group(1), m.group(2), part[m.end():]
                if typ not in ("color", "colors", "text"):
                    continue
                body = body[:body.index('<p class="err"')] if typ != "text" else body[:body.index("</div>")]
                seen.add(typ)
                with self.subTest(page=str(page.relative_to(ROOT)), ctl=cid):
                    if typ == "text":
                        self.assertRegex(body, r'<input id="ctl-' + cid + r'" type="text" maxlength="200"')
                        continue
                    self.assertIn(f'<p class="err" id="ctl-{cid}-err" aria-live="polite"></p>', text)
                    fields = re.findall(r'<input[^>]*class="seed-input"[^>]*>', body)
                    self.assertTrue(fields)
                    for inp in fields:
                        self.assertIn(f'aria-describedby="ctl-{cid}-err"', inp)
                    for pk in re.findall(r'<input type="color"[^>]*>', body):
                        empty = re.search(r'class="seed-input" type="text" value=""', body) is not None
                        self.assertEqual("data-empty" in pk, empty, pk)
        self.assertEqual(seen, {"color", "colors", "text"})

    def test_legal_notice_everywhere(self):
        """Impressum: Jede HTML-Seite verlinkt es mit einem Klick, jede Sprachseite das ihrer Sprache, Sprachweiche und 404
        beide, auch in der Testaufgabe. Die Seite zeigt die Angaben aus data/legal.json für Anbieter und Verantwortlichen."""
        for site in self.sites():
            legal = {lang: site / build.path(lang, "legal") / "index.html" for lang in ("de", "en")}
            for page in sorted(site.rglob("*.html")):
                got = {resolve(site, page, r) for r in parse(page).refs if r and not re.match(r"^(https?:|mailto:|data:|#)", r)}
                first = page.relative_to(site).parts[0]
                want = [legal[first]] if first in legal else list(legal.values())
                with self.subTest(page=str(page.relative_to(ROOT))):
                    for w in want:
                        self.assertIn(w, got)
        from web.copy import legal as LEGAL
        L = json.loads((ROOT / "data" / "legal.json").read_text(encoding="utf-8"))
        addr = "<br>".join(html.escape(x) for x in L["address"])
        for lang in ("de", "en"):
            t = (DOCS / build.path(lang, "legal") / "index.html").read_text(encoding="utf-8")
            T = LEGAL.COPY[lang]["legal"]
            with self.subTest(lang=lang):
                self.assertNotIn('class="stub"', t)
                for k in ("h.provider", "parcels", "h.contact", "h.vat", "vat", "h.responsible"):
                    self.assertIn(html.escape(T[k]), t, k)
                self.assertIn(f'{html.escape(T["email"])} <a href="mailto:{L["email"]}">{L["email"]}</a>', t)
                self.assertIn(f'{html.escape(T["vat"])}<br>{L["vat_id"]}</p>', t)
                self.assertIn(f'<p>{html.escape(L["name"])}<br>', t)
                self.assertIn(f'<p>{html.escape(L["responsible"])}<br>', t)
                self.assertEqual(t.count(addr), 2, "Anschrift bei Anbieter und Verantwortlichem")
                if lang == "en":
                    self.assertEqual(t.count(f'<span lang="de">{addr}</span>'), 2, "deutsche Anschrift mit lang")

    def test_sibling_links(self):
        """Bildsprache und Designsprache: jede Sprachseite verlinkt beide in ihrer Sprache, Sprachweiche und 404 die Startseite."""
        for site in self.sites():
            for page in sorted(site.rglob("*.html")):
                refs = parse(page).refs
                first = page.relative_to(site).parts[0]
                with self.subTest(page=str(page.relative_to(ROOT))):
                    for _, url in build.SIBLINGS:
                        self.assertIn(url + (first + "/" if first in ("de", "en") else ""), refs)

    def test_assets_versioned(self):
        for page in lang_pages(DOCS):
            for ref in parse(page).refs:
                if "assets/" in ref:
                    self.assertRegex(ref, r"\?v=[0-9a-f]{10}$", ref)


class TestLegalData(unittest.TestCase):
    def test_legal_details_only_in_data(self):
        """Die Angaben des Impressums stehen genau einmal im Repo (data/legal.json), nicht von Hand in Seiten oder Texten."""
        L = json.loads((ROOT / "data" / "legal.json").read_text(encoding="utf-8"))
        unique = [L["vat_id"], L["email"], L["address"][0], L["address"][1]]
        files = [ROOT / n for n in ("build.py", "CONTRIBUTING.md", "README.md", "README.de.md", "LICENSE", "LICENSE-CONTENT.md")]
        for d in ("pages", "web", "tools", "data", "tests", "patterns", ".github"):
            files += [f for f in (ROOT / d).rglob("*") if f.is_file() and f.suffix not in (".pyc", ".woff2", ".png")
                      and "out" not in f.relative_to(ROOT / d).parts[:1]]
        self.assertGreater(len(files), 50)
        for f in files:
            if f == ROOT / "data" / "legal.json":
                continue
            text = f.read_text(encoding="utf-8")
            for u in unique:
                self.assertNotIn(u, text, str(f.relative_to(ROOT)))

    def test_legal_details_shape(self):
        """pages/legal.check erkennt gekürzte Angaben (der Build bricht dann ab), ohne die Werte zu wiederholen."""
        from pages import legal
        L = json.loads((ROOT / "data" / "legal.json").read_text(encoding="utf-8"))
        self.assertEqual(legal.check(L), [])
        bad = [dict(L, address=L["address"][:i] + L["address"][i + 1:]) for i in range(len(L["address"]))]
        bad += [dict(L, vat_id=L["vat_id"][:-1]), dict(L, email=L["email"].rsplit(".", 1)[0]),
                dict(L, name=L["name"].split()[0]), dict(L, responsible=""), {k: v for k, v in L.items() if k != "email"}]
        for i, d in enumerate(bad):
            with self.subTest(case=i):
                self.assertNotEqual(legal.check(d), [])


class TestCompact(unittest.TestCase):
    """T-15: ausgelieferte Skripte und site.css werden kompaktiert (7.11); dabei fällt nur Leerraum und Kommentar weg."""
    CASES = [("var a = b - -c;", "var a=b- -c;"), ("x = y + +z;", "x=y+ +z;"), ("i++ + 1", "i++ +1"),
             ("if (a < !b) { c = d-- > e; }", "if(a< !b){c=d-- >e;}"), ("return /a b/.test(s);", "return /a b/.test(s);"),
             ("s.replace(/[ /]+/g, ' ')", "s.replace(/[ /]+/g,' ')"), ("var t = 'a  b'; // x  y", "var t='a  b'; // x  y"),
             ("a = b / c / d;", "a=b / c / d;"), ("var ä = 1;", "var ä=1;"), ("typeof x === 'string'", "typeof x==='string'"),
             ("case 'a': return [1, 2];", "case'a':return[1,2];"), ("f('it\\'s', \"x  y\")", "f('it\\'s',\"x  y\")"),
             ("x = 'offen", "x = 'offen"), ("a = /* b  c */ d", "a= /* b  c */ d"),
             ("var A = /[ \\t]/;", "var A= /[ \\t]/;"), ("re = /a b/g;", "re= /a b/g;"),
             ("return / x/.test(s)", "return / x/.test(s)"), ("x = a ? /[ ]/ : b", "x=a? /[ ]/ :b")]

    def test_squeeze_cases(self):
        for src, want in self.CASES:
            with self.subTest(src=src):
                self.assertEqual(build.squeeze_js(src), want)

    def test_only_whitespace_and_comments_removed(self):
        files = sorted(list((ROOT / "web").glob("*.js")) + list((ROOT / "web" / "gen").glob("*.js")) + list((ROOT / "web" / "ui").glob("*.js")))
        for f in files:
            if f.name == "theme.js":
                continue
            src = f.read_text(encoding="utf-8")
            lines = build.compact_js(src)
            with mock.patch.object(build, "squeeze_js", lambda s: s):
                base = build.compact_js(src)
            with self.subTest(file=f.name):
                self.assertEqual(re.sub(r"\s", "", lines), re.sub(r"\s", "", base))
                self.assertEqual(lines.count("\n"), base.count("\n"), "Zeilenumbrüche bleiben (ASI)")
                self.assertLess(len(lines), len(base))
        css = "a { color:red; } /* x */\n  b > c { margin:0 }\n"
        self.assertEqual(build.compact_css(css), "a { color:red; }\nb > c { margin:0 }\n")


if __name__ == "__main__":
    unittest.main()
