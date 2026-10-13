"""Seiten Palette prüfen, Kurz erklärt, Methode und Quellen im Build: Methode mit 16 Abschnitten und gerechneter Vergleichstabelle,
Quellen mit allen Lizenzvolltexten und Pflichtvermerken, Kurz erklärt mit allen Einträgen, Prüfseite mit Daten.
Ohne Build übersprungen, außer FARBSPRACHE_REQUIRE_BUILD=1. Dazu Einheitentests der Seitenmodule ohne Build
(Demo-Variablen, zitierte Verhältnisse aus Quellen, Stand der Release-Gates, Quellenangaben der Methode)."""
import html, json, os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C  # noqa: E402
from pages import method as M  # noqa: E402

DOCS = ROOT / "docs"
REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
PAGES = {"check": ("pruefen", "check"), "explained": ("erklaert", "explained"), "method": ("methode", "method"), "sources": ("quellen", "sources")}


def read(kind, lang):
    seg = PAGES[kind][0 if lang == "de" else 1]
    return (DOCS / lang / seg / "index.html").read_text(encoding="utf-8")


def visible(t):
    t = re.sub(r"<(script|style|pre)[^>]*>.*?</\1>", " ", t, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def datasets():
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (ROOT / "data" / "datasets").glob("*.json")}


@unittest.skipUnless(REQUIRE or (DOCS / "de" / "index.html").exists(), "docs/ fehlt – erst python3 build.py")
class TestBuiltPages(unittest.TestCase):
    def setUp(self):
        for kind in PAGES:
            if '<main id="main" class="stub">' in read(kind, "de"):
                self.skipTest(f"Seite {kind} ist ein Platzhalter")

    def test_method_sections(self):
        for lang in ("de", "en"):
            t = read("method", lang)
            ids = re.findall(r'<section class="m-sec" id="m(\d+)"', t)
            self.assertEqual(ids, [str(i) for i in range(1, M.N_SECTIONS + 1)], lang)
            self.assertNotRegex(visible(t), r"\[\[|\{[a-z_0-9]+\}|\{(cr|dist|ref|scrim|proj|count):", lang)

    def test_method_comparison_table_is_calculated(self):
        refs = C.reference_values()
        ds = datasets()
        t = read("method", "de")
        table = re.search(r'<table class="cmp">(.*?)</table>', t, re.S).group(1)
        rows = re.findall(r"<tr><th scope=\"row\">(.*?)</tr>", table, re.S)
        self.assertEqual(len(rows), 4)
        def tol(key):
            for sch in (ds.get("tol") or {}).get("schemes", []):
                if key in sch["id"].lower():
                    return [c["hex"] for c in sch["colors"]]
            return None
        want = [refs["okabe-ito-7"]["colors"], tol("bright"), tol("muted"), refs["naive-rainbow-7"]["colors"]]
        for row, cols in zip(rows, want):
            tags = re.findall(r'<data class="num" value="[^"]*" data-m="dist" data-a="([^"]*)" data-b="([^"]*)" data-k="([^"]*)">', row)
            if cols is None:
                self.assertEqual(tags, [])
                self.assertIn("Datensatz fehlt noch", row)
                continue
            self.assertEqual([k for _, _, k in tags], list(M.CMP_KINDS))
            for a, b, k in tags:
                md = C.min_distance(cols, [k])
                self.assertEqual((a, b), (md["a"], md["b"]), k)

    def test_method_gray_deviation(self):
        one, two = M.gray_deviation()
        self.assertGreater(two, one)
        for lang in ("de", "en"):
            v = visible(read("method", lang))
            self.assertIn(M.pct_up1(one, lang), v)
            self.assertIn(M.pct_up1(two, lang), v)

    def test_method_settings_come_from_generators(self):
        # Abschnitt 11: Zahlen der Festlegungen aus tools/gen (nicht abgeschrieben), Texte ohne Handzahlen
        from tools.gen import website as GW, slides as GS
        from web.copy import method as CM
        for lang in ("de", "en"):
            sec = re.search(r'<section class="m-sec" id="m11".*?</section>', read("method", lang), re.S).group(0)
            v = visible(sec)
            for want in (M.pct(GW.TEXT_T / 4.5 - 1, lang), M.pct(GS.LIGHT_T / 7.0 - 1, lang), M.pct(GW.DARK_C, lang),
                         M.dec(GW.TEXT_L0[-1], lang), M.dec(GW.TEXT_L0[1], lang)):
                self.assertIn(want, v, lang)
            self.assertIn('data-m="ref" data-id="okabe-ito-7"', sec)
            for item in CM.COPY[lang]["method"]["s11.list"]:
                bare = re.sub(r"\{[^{}]*\}|\[\[[a-z0-9-]+\]\]", "", item)
                self.assertNotRegex(bare, r"\d", f"{lang}: Handzahl in s11.list: {item}")

    def test_sources_every_source_cited(self):
        for lang, none in (("de", "noch nirgends"), ("en", "not yet cited")):
            t = read("sources", lang)
            self.assertNotIn(none, t, f"{lang}: Quelle ohne Verweis")

    def test_sources_licenses_and_notices(self):
        ds = datasets()
        n_src = sum(len(json.loads(f.read_text(encoding="utf-8"))["sources"]) for f in (ROOT / "data" / "sources").glob("*.json"))
        for lang in ("de", "en"):
            t = read("sources", lang)
            for name, probe in (("MIT.txt", "Permission is hereby granted"), ("BSD-3-Clause.txt", "Neither the name of the copyright holder"),
                                ("Apache-2.0.txt", "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION"),
                                ("ColorBrewer.txt", "Apache-Style Software License for ColorBrewer"),
                                # mitgelieferte Schriften: Lizenztexte auf der Quellenseite
                                ("OFL-1.1-Inter.txt", "SIL OPEN FONT LICENSE Version 1.1"), ("OFL-1.1-IBM-Plex.txt", 'Reserved Font Name "Plex"'),
                                # Material aus CSS Color 4: Lizenztext und Vermerk
                                ("W3C-Software-and-Document-2023.txt", "provided that you include the following on ALL copies")):
                body = (ROOT / "data" / "licenses" / name).read_text(encoding="utf-8")
                self.assertIn(probe, body)
                for line in [ln for ln in body.splitlines() if ln.strip()][2:6]:
                    self.assertIn(html.escape(line.strip(), quote=True), t, f"{name}: {line}")
            self.assertIn("Copyright (c) 2022, Paul Tol", t)
            self.assertIn(html.escape("This software includes material copied from or derived from CSS Color Module Level 4", quote=True), t)
            self.assertIn("Copyright (c) 2026 Sebastian Grundhöfer", t)
            self.assertEqual(t.count("data-claim"), n_src, lang)
            self.assertIn("Masataka Okabe", t)
            notice = "This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/)."
            self.assertIn(html.escape(notice), t, lang)  # immer wörtlich, auch solange der Datensatz fehlt
            if "colorbrewer" in ds:
                self.assertEqual(ds["colorbrewer"]["required_notice"], notice)
            for f in (ROOT / "data" / "sources").glob("*.json"):
                for s in json.loads(f.read_text(encoding="utf-8"))["sources"]:
                    self.assertIn(f'id="{s["id"]}"', t)

    def test_explained_entries(self):
        order = json.loads((ROOT / "data" / "explain" / "_order.json").read_text(encoding="utf-8"))["order"]
        have = {e["id"] for f in (ROOT / "data" / "explain").glob("*.json") if not f.name.startswith("_")
                for e in json.loads(f.read_text(encoding="utf-8"))["entries"]}
        for lang in ("de", "en"):
            t = read("explained", lang)
            ids = re.findall(r'<li class="ex-entry" id="([^"]+)"', t)
            self.assertEqual(ids, [e for e in order if e in have])

    def test_check_page_data(self):
        cfg = json.loads((ROOT / "data" / "check.json").read_text(encoding="utf-8"))
        for lang in ("de", "en"):
            t = read("check", lang)
            self.assertIn('id="chk-input"', t)
            d = json.loads(re.search(r'<script type="application/json" id="check-data">(.*?)</script>', t, re.S).group(1).replace("<\\/", "</"))
            # Die Seite trägt die Daten ohne die Arbeitsnotizen _comment (build.py no_comments)
            self.assertEqual(d["cfg"], {k: v for k, v in cfg.items() if k != "_comment"})
            self.assertNotIn('"_comment"', t)
            for rid in ("text-contrast", "non-text-contrast", "no-rounding", "check-cvd", "check-gamut"):
                self.assertIn(rid, d["rules"])
                self.assertIn(f'data-rule="{rid}"', t)


if __name__ == "__main__":
    unittest.main()


class FakeSite:
    """Kleinster Seitenkontext für Einheitentests der Seitenmodule (ohne Build)."""
    def __init__(self, **kw):
        from tools import checks
        D, _ = checks.load_all([ROOT])
        self.copy, self.D, self.warnings, self.allow_missing = D["copy"], D, [], True
        self.sources, self.task_by_id, self.refs, self.date = D["sources"], {}, C.reference_values(), "2026-10-11"
        self.__dict__.update(kw)

    def warn(self, msg):
        self.warnings.append(msg)

    def render(self, template, ctx, lang, escape=False):
        c = {"refs": self.refs, "date": self.date}
        c.update(ctx or {})
        return C.render_text(template, c, lang, escape)[0]


class TestPageUnits(unittest.TestCase):
    def test_explained_demo_uses_demo_vars(self):
        from pages import explained as E
        pat = ('<style>.demo-context .a{background:var(--d-ground-a)}</style><div class="a"></div>')
        site = FakeSite()
        site.D = dict(site.D, extra_patterns={"patterns/demo-context.html": pat})
        style, html_ = E.demo(site, "de", "context", "context", None)
        self.assertIn(".demo-context .a", style)
        want = {k: C.parse(v, False)["hex"] for k, v in E.DEMOS["context"].items()}
        self.assertIn(f'--d-sample:{want["sample"]};', html_)
        self.assertIn(f'<data class="hex" value="{want["sample"]}">', html_)  # Bildunterschrift: Hex aus dem Bau
        _, html2 = E.demo(site, "en", "context", "context", {"ground-a": "#FF0000", "ground-b": "#0000FF", "patch": "oklch(0.62 0 0)"})
        self.assertIn("--d-ground-a:#FF0000;--d-ground-b:#0000FF;--d-patch:", html2)
        self.assertIn('data-bridge="off"', html2)
        self.assertIn('aria-pressed="false"', html2)
        with self.assertRaises(ValueError):
            E.demo(site, "de", "context", "context", {"sample": "kein Farbwert"})

    def test_explained_demo_drops_pattern_comment(self):
        from pages import explained as E
        site = FakeSite()
        site.D = dict(site.D, extra_patterns={"patterns/demo-context.html": "<!-- intern -->\n<style>.demo-context .a{}</style><div class=\"a\"></div>"})
        _, html_ = E.demo(site, "en", "context", "context", None)
        self.assertNotIn("<!--", html_)
        self.assertIn('<div class="a"></div>', html_)

    def test_method_own_tokens(self):
        from types import SimpleNamespace as NS
        rules = {"chart-direct-labels": {"show_if": {"value": 6}}}
        gw = NS(TEXT_T=4.95, LINE_T=3.3, DARK_C=0.85, TEXT_L0={-1: 0.80, 1: 0.40})
        site = FakeSite(gens={"website": gw, "slides": NS(LIGHT_T=7.7, LINE_T=3.3, DARK_C=0.85)}, rules=rules)
        tok = M.own_tokens(site, "de")
        self.assertEqual((tok["reserve"], tok["dark_c"], tok["l0_light"], tok["l0_dark"], tok["cut"]),
                         ("10\u202f%", "85\u202f%", "0,8", "0,4", "6"))
        self.assertEqual(M.own_tokens(site, "en")["reserve"], "10%")
        bad = FakeSite(gens={"website": gw, "slides": NS(LIGHT_T=7.7, LINE_T=3.0, DARK_C=0.85)}, rules=rules)
        with self.assertRaises(ValueError):  # Reserve der Generatoren uneinheitlich
            M.own_tokens(bad, "de")
        missing = FakeSite(gens={}, rules=rules)
        self.assertEqual(M.own_tokens(missing, "de"), {})
        self.assertTrue(missing.warnings)
        missing.allow_missing = False
        with self.assertRaises(ValueError):
            M.own_tokens(missing, "de")

    def test_sources_quoted_ratio(self):
        from pages import sources as S
        site = FakeSite()
        s = {"claim_de": "Schwellen 4,5:1 und 3:1; 4,499:1 erfüllt 4,5:1 nicht.", "claim_en": "x"}
        out = S.claim_html(site, "de", s)
        self.assertIn("4,5:1", out)
        self.assertIn("3:1", out)
        self.assertIn('<q class="qnum"', out)
        # Quellzahl mit normalem Doppelpunkt, aber nur innerhalb der Aussage mit data-claim (Ausnahme in test_honesty)
        self.assertRegex(out, r'^<span class="claim" data-claim>[^<]*<q class="qnum"[^>]*>4,499:1</q>[^<]*</span>')
        self.assertNotIn("\u2236", out)
        s["calc_de"] = "Farbsprache: {proj:#000000/#FFFFFF/normal}"
        self.assertIn('data-m="proj"', S.claim_html(site, "de", s))
        # eigene Rechnung neben der Quellzahl auch ohne calc_* in der Quelle, aus web/copy/sources.py
        for lang in ("de", "en"):
            out = S.claim_html(site, lang, {"id": "ti-dlpa088", "claim_" + lang: "5,99:1"})
            self.assertIn('data-m="proj" data-a="#000000" data-b="#FFFFFF" data-t="normal"', out)
            self.assertIn(site.copy[lang]["sources"]["calc"], out)

    def test_method_gate_states(self):
        from pages import method as M
        T = FakeSite().copy["de"]["method"]
        gates = {g.get("id"): g for g in T["s16.gates"]}
        site = FakeSite(task_by_id={"slides": {"menu_paths": [{"app": "PowerPoint", "checked": "2026-10-11"}]}})
        site.D = dict(site.D, models={"models": [{"id": "x", "name": "Modell X", "checked": "2026-10-01"}]})
        self.assertIn("Modell X 2026-10-01", M.gate_state(site, T, gates["models"]))
        self.assertNotIn(T["gate_archive"], M.gate_state(site, T, gates["models"]))
        site.D = dict(site.D, models={"models": [{"id": "y", "name": "Modell Y", "checked": "2026-10-04",
                                                   "source": "https://web.archive.org/web/20261004/https://example.org/"}]})
        self.assertIn("Modell Y 2026-10-04 " + T["gate_archive"], M.gate_state(site, T, gates["models"]))
        self.assertIn("PowerPoint 2026-10-11", M.gate_state(site, T, gates["office"]))
        bare = FakeSite()
        bare.D = dict(bare.D, models=None)
        self.assertEqual(M.gate_state(bare, T, gates["models"]), T["gate_state"] + " " + gates["models"]["state"])

    def test_method_cites_in_parentheses(self):
        from pages import method as M
        site = FakeSite(seg=None)
        site.path = lambda lang, kind: f"{lang}/{kind}/"
        site.rel = lambda a, b: "../../" + b
        html_ = M.cite(site, "de", "de/methode/", "libdaltonlens")
        self.assertRegex(html_, r'^\(<a class="m-src" href="\.\./\.\./de/sources/#libdaltonlens">libDaltonLens</a>\)$')
        self.assertIn("(", M.cite(site, "de", "de/methode/", "gibt-es-nicht"))
        self.assertTrue(site.warnings)
