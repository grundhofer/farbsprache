"""Fachfälle der Aufgabe Text auf Bild (Paket P3, Bauspezifikation 4.1.15, 4.7, 5.8, 8 Abnahme P3).

Schleier-Erwartungen 42 / 54 / 66 / 46 / 85 % mit Nachprüfung in Gleitkomma und 8 Bit (bei 65 % nur 6,97:1, bei
84 % nur 4,46:1), schlimmster Pixel nach F83, Schleier-CSS, Werte und Agent-Prompt nur mit Hex-Werten, keine
Bild-Upload-Funktion. Seiten-Tests laufen über docs/ (ohne Build übersprungen, außer FARBSPRACHE_REQUIRE_BUILD=1)."""
import json, os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C  # noqa: E402
from tools.gen import image_text as G  # noqa: E402

REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
DOCS = ROOT / "docs"
TASK = json.loads((ROOT / "data" / "tasks" / "image-text.json").read_text(encoding="utf-8"))
CTX = {"datasets": {}, "comparisons": None, "lang": None, "data": {}}


def build(sc, tc="#FFFFFF", tg="4.5"):
    inp = {"seed": C.parse(sc, False)["hex"], "colors": None, "options": {"tc": C.parse(tc, False)["hex"], "tg": tg}}
    pal = G.build(TASK, inp, CTX)
    pal["input"] = inp
    return pal


def mix(scrim, pixel, a):
    s, p = C.hex_to_srgb(scrim), C.hex_to_srgb(pixel)
    return [a * s[i] + (1 - a) * p[i] for i in range(3)]


class TestScrim(unittest.TestCase):
    def test_expected_percentages(self):
        cases = [("#FFFFFF", "#000000", 3.0, 0.4162, 42), ("#FFFFFF", "#000000", 4.5, 0.5347, 54),
                 ("#FFFFFF", "#000000", 7.0, 0.6508, 66), ("#000000", "#FFFFFF", 4.5, 0.4553, 46),
                 ("#FFFFFF", "#11697A", 4.5, 0.8435, 85)]
        for t, s, target, alpha, pct in cases:
            with self.subTest(text=t, scrim=s, target=target):
                r = C.scrim_alpha(t, s, target)
                self.assertLess(abs(r["alpha"] - alpha), 0.0001)
                self.assertEqual(r["percent"], pct)
                self.assertEqual(C.fmt_pct_up(r["percent"] / 100, "de"), f"{pct} %")
                # Nachprüfung bei percent/100 in Gleitkomma und mit 8-Bit-Mischfarbe
                c = mix(s, r["worst"], pct / 100)
                self.assertGreaterEqual(C.contrast(t, c), target)
                self.assertGreaterEqual(C.contrast(t, C.srgb_to_hex(c)), target)
                self.assertEqual(r["mix_hex"], C.srgb_to_hex(c))

    def test_one_percent_less_fails(self):
        self.assertEqual(C.fmt_ratio(C.contrast("#FFFFFF", mix("#000000", "#FFFFFF", 0.65)), "de"), "6,97:1")
        self.assertEqual(C.fmt_ratio(C.contrast("#FFFFFF", mix("#11697A", "#FFFFFF", 0.84)), "de"), "4,46:1")
        self.assertLess(C.contrast("#FFFFFF", mix("#000000", "#FFFFFF", 0.53)), 4.5)

    def test_worst_pixel(self):
        self.assertEqual(build("#000000")["roles"]["default"]["worst-pixel"], "#FFFFFF")
        dark_text = build("#FFFFFF", tc="#000000")
        self.assertEqual(dark_text["roles"]["default"]["worst-pixel"], "#000000")
        self.assertEqual(dark_text["extra"]["summary"], ["summary.alpha.4.5", "summary.low.8bit", "summary.worst.black"])

    def test_smaller_ratio_named(self):
        """4.7: Es zählt der kleinere Kontrast aus Gleitkomma und 8 Bit; das Kurzergebnis sagt, welcher es ist."""
        for sc, tc, tg in (("#000000", "#FFFFFF", "4.5"), ("#FFFFFF", "#000000", "4.5"), ("oklch(0.48 0.08 215)", "#FFFFFF", "4.5"),
                           ("#000000", "#FFFFFF", "3"), ("#FFFF00", "#000000", "4.5"), ("#000000", "#808080", "4.5")):
            pal = build(sc, tc=tc, tg=tg)
            s = pal["extra"]["scrim"]
            with self.subTest(sc=sc, tc=tc, tg=tg):
                want = "summary.low.8bit" if s["ratio_8bit"] <= s["ratio"] + 1e-9 else "summary.low.float"
                self.assertEqual(pal["extra"]["summary"][1], want)
        self.assertEqual(build("#000000")["extra"]["summary"][1], "summary.low.float")  # 4,58:1 in Gleitkomma, 4,60:1 mit 8 Bit

    def test_checked_pair_names_8bit(self):
        """R-13: Badge und Prüfbericht zeigen den Kontrast der 8-Bit-Mischfarbe (das Hex, das <data> nachrechnet) und sagen
        das; der kleinere Gleitkommawert steht im Kurzergebnis und im Format „Werte“."""
        from pages import task as P
        from web.copy import core as copy_core, image_text as copy_it
        pal = build("#000000")
        pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
        for lang, word in (("de", "auf Mischfarbe (8 Bit)"), ("en", "on blended color (8-bit)")):
            R = {"lang": lang, "T": copy_core.COPY[lang]["frame"], "tc": copy_it.COPY[lang]["image-text"], "task": TASK,
                 "refs": {}, "date": "2026-10-11", "sources": {}, "rules": [], "comparisons": []}
            badge = P.badge(R, pal, "default", "text")
            row = re.sub(r"<[^>]+>", "", P.check(R, pal).split("<tbody>")[1].split("</tr>", 1)[0])
            with self.subTest(lang=lang):
                self.assertIn(word, re.sub(r"<[^>]+>", "", badge))
                self.assertIn("(8 Bit)" if lang == "de" else "(8-bit)", row)
                self.assertIn(C.fmt_ratio(C.contrast(pal["roles"]["default"]["text"], pal["roles"]["default"]["composite"]), lang), row)

    def test_tie_counts_as_8bit(self):
        """M-04: Fällt die Mischfarbe genau auf einen 8-Bit-Wert, sind beide Kontraste gleich. Ein Unterschied im letzten Bit
        (Python 1 ulp größer als JS) darf den Satz nicht kippen: Gleichstand bis 1e-9 heißt „8 Bit“, in Python wie in JS."""
        for sc in ("#FAFAFA", "#787878", "#7D7D7D"):
            pal = build(sc, tc="#000000", tg="3")
            s = pal["extra"]["scrim"]
            with self.subTest(sc=sc):
                self.assertLessEqual(abs(s["ratio_8bit"] - s["ratio"]), 1e-9, "Gleichstand innerhalb der Rechengenauigkeit")
                self.assertEqual(pal["extra"]["summary"][1], "summary.low.8bit")

    def test_presets(self):
        want = {"white-on-black": 54, "black-on-white": 46, "white-on-color": 85}
        for p in TASK["presets"]:
            pal = build(p["seed"], **{k: v for k, v in p["options"].items()})
            with self.subTest(preset=p["id"]):
                self.assertEqual(pal["extra"]["scrim"]["percent"], want[p["id"]])
                self.assertEqual([x["min"] for x in pal["pairs"]], [4.5])
                self.assertTrue(all(x["pass"] for x in pal["pairs"]))
                self.assertEqual(pal["findings"], [])
                self.assertEqual(pal["changes"], [])

    def test_target_from_option(self):
        pal = build("#000000", tg="3")
        self.assertEqual(pal["extra"]["scrim"]["percent"], 42)
        self.assertEqual(pal["pairs"][0]["min"], 3.0)
        self.assertEqual(pal["extra"]["summary"][0], "summary.alpha.3")

    def test_unreachable(self):
        with self.assertRaises(C.SolveError) as cm:
            build("#E63946")  # Weiß auf #E63946 (Kräftiges Rot) erreicht auch bei voller Deckkraft keine 4,5:1
        self.assertEqual(cm.exception.key, "scrim-unreachable")
        from web.copy import image_text as copy  # noqa: PLC0415
        for lang in ("de", "en"):
            self.assertIn("solve.scrim-unreachable", copy.COPY[lang]["image-text"])

    def test_view_vars(self):
        v = G.view_vars(build("#000000"), "default", {"fmt": "16x9", "safe": "off"})
        self.assertEqual(v["alpha"], "0.54")
        self.assertEqual((v["ref-white"], v["ref-black"]), ("#FFFFFF", "#000000"))
        self.assertEqual(G.view_vars(build("#FFFFFF", tc="#000000"), "default", {})["alpha"], "0.46")


class TestExports(unittest.TestCase):
    def ctx(self, pal, lang):
        from web.copy import core, image_text as copy  # noqa: PLC0415
        rules = {r["id"]: r for r in json.loads((ROOT / "data" / "rules" / "slides.json").read_text(encoding="utf-8"))["rules"]}
        return {"date": "2026-10-11", "url": "https://grundhofer.github.io/farbsprache/x/?p=white-on-black", "name": "Weiß auf Schwarz",
                "task_name": "Text auf Bild", "core": core.COPY[lang]["export"], "text": copy.COPY[lang]["image-text"],
                "rules": [rules[r] for r in TASK["rules"]], "sources": {}, "refs": C.reference_values(), "datasets": {}, "data": {}}

    def test_scrim_css(self):
        for lang in ("de", "en"):
            pal = build("#000000")
            css = G.exports["scrim"](pal, TASK, self.ctx(pal, lang), lang)
            self.assertIn("linear-gradient(to top, rgb(0 0 0 / 0.54) 0%, rgb(0 0 0 / 0.54) 40%, rgb(0 0 0 / 0) 70%)", css)
            self.assertIn("color: #FFFFFF;", css)
            self.assertTrue(css.startswith("/* Farbsprache · Weiß auf Schwarz · Text auf Bild · "))
            self.assertEqual(css.count("/*"), css.count("*/"))
        pal = build("oklch(0.48 0.08 215)")
        self.assertIn("rgb(17 105 122 / 0.85)", G.exports["scrim"](pal, TASK, self.ctx(pal, "en"), "en"))

    def test_values_have_both_ratios(self):
        pal = build("#000000")
        s = pal["extra"]["scrim"]
        txt = G.exports["values"](pal, TASK, self.ctx(pal, "de"), "de")
        f, q = C.fmt_ratio(s["ratio"], "de", 4.5), C.fmt_ratio(s["ratio_8bit"], "de", 4.5)
        self.assertIn(f, txt)
        self.assertIn(q, txt)
        self.assertIn("kleinere: " + C.fmt_ratio(min(s["ratio"], s["ratio_8bit"]), "de", 4.5), txt)
        self.assertIn("54 %", txt)

    def test_agent_hex_only(self):
        for lang in ("de", "en"):
            for sc, tc in (("#000000", "#FFFFFF"), ("#FFFFFF", "#000000"), ("oklch(0.48 0.08 215)", "#FFFFFF")):
                pal = build(sc, tc=tc)
                txt = G.exports["agent"](pal, TASK, self.ctx(pal, lang), lang)
                with self.subTest(lang=lang, sc=sc):
                    self.assertNotIn("var(--", txt)
                    self.assertNotRegex(txt, r"\bNone\b|undefined|\bNaN\b|\bnull\b|\{[a-z0-9]+\}")
                    self.assertIn(pal["roles"]["default"]["scrim"], txt)
                    hx8 = re.search(r"(#[0-9A-F]{6})([0-9A-F]{2}) ", txt)
                    self.assertGreaterEqual(int(hx8.group(2), 16) / 255, pal["extra"]["scrim"]["percent"] / 100)


@unittest.skipUnless(REQUIRE or (DOCS / "de" / "text-auf-bild" / "index.html").exists(), "docs/ fehlt – erst python3 build.py")
class TestPage(unittest.TestCase):
    def test_no_upload_and_reference_surfaces(self):
        for lang, seg in (("de", "text-auf-bild"), ("en", "text-on-image")):
            html = (DOCS / lang / seg / "index.html").read_text(encoding="utf-8")
            with self.subTest(lang=lang):
                self.assertNotIn('type="file"', html)
                self.assertNotRegex(html.lower(), r"filereader|drop zone|dropzone")
                self.assertEqual(html.count('class="it-tile"'), 3)
                self.assertIn("--d-ref-white:#FFFFFF;", html)
                self.assertIn("--d-ref-black:#000000;", html)
                self.assertIn("--d-alpha:0.54;", html)
                self.assertRegex(html, r'data-m="scrim" data-a="#FFFFFF" data-b="#000000" data-t="4.5"[^>]*>54(\u202f)?%')
        for f in ("web/gen/image-text.js", "tools/gen/image_text.py", "patterns/image-text.html"):
            src = (ROOT / f).read_text(encoding="utf-8").lower()
            self.assertNotIn("filereader", src)
            self.assertNotIn('type="file"', src)
