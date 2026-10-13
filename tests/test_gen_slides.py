"""Fachfälle der Aufgabe Präsentation.

Beamer-Erwartungen 5,98 / 3,14 / 3,99 (dazu 96,19 und 2,66), Folienschrift ≥ 7:1 bei allen Startpaletten,
Ansicht „Beamer“ über view_vars, Office-Reihenfolge der Hex-Liste, Menüwege mit Quelle und Datum,
Änderungshinweise und Hinweise, Lösbarkeit sehr heller und sehr dunkler eigener Farben.
Die Seiten-Tests laufen über docs/ und werden ohne Build übersprungen, außer FARBSPRACHE_REQUIRE_BUILD=1."""
import json, os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C, export as X  # noqa: E402
from tools.gen import slides as G  # noqa: E402

REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
DOCS = ROOT / "docs"


def jload(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


TASK = jload("data/tasks/slides.json")
CTX = {"datasets": {"okabe-ito": jload("data/datasets/okabe-ito.json")}, "comparisons": jload("data/comparisons.json"), "lang": None, "data": {}}


def options(**kw):
    o = {c["id"]: c["default"] for c in TASK["controls"]}
    o.update(kw)
    return o


def build(seed, **kw):
    hx = C.parse(seed, False)["hex"]
    pal = G.build(TASK, {"seed": hx, "colors": None, "options": options(**kw)}, CTX)
    pal["input"] = {"seed": hx, "colors": None, "options": options(**kw)}  # wie frame_palette
    return pal


def preset_palettes():
    out = {}
    for p in TASK["presets"]:
        out[p["id"]] = build(p["seed"], **p["options"])
    return out


class TestProjector(unittest.TestCase):
    """Beamer-Modell: feste Erwartungswerte, angezeigt mit fmt_ratio."""

    def test_expected_values(self):
        cases = [("#000000", "#FFFFFF", "normal", 5.9850, "5,98:1"), ("#767676", "#FFFFFF", "normal", 3.1448, "3,14:1"),
                 ("#595959", "#FFFFFF", "normal", 3.9953, "3,99:1"), ("#000000", "#FFFFFF", "dim", 96.19, "96,19:1"),
                 ("#000000", "#FFFFFF", "bright", 2.66, "2,66:1")]
        for a, b, room, raw, shown in cases:
            with self.subTest(a=a, room=room):
                k = C.projected_contrast(a, b, room)
                self.assertLess(abs(k - raw), 0.005)
                self.assertEqual(C.fmt_ratio(k, "de"), shown)
                self.assertEqual(C.projected_contrast(a, b, room), C.projected_contrast(b, a, room))

    def test_ambient_ratios(self):
        self.assertEqual([C.ambient_ratio(r) for r in ("dim", "normal", "bright")], [0.01, 0.2, 0.6])

    def test_view_vars(self):
        pal = build("oklch(0.48 0.08 215)")
        self.assertEqual(G.view_vars(pal, "default", {"view": "screen"}), {})
        for room in ("dim", "normal", "bright"):
            p2 = build("oklch(0.48 0.08 215)", room=room)
            v = G.view_vars(p2, "default", {"view": "projector"})
            self.assertEqual(set(v), set(p2["roles"]["default"]) | {"cap-text", "cap-bg"})
            for rid, hx in p2["roles"]["default"].items():
                self.assertEqual(v[rid], C.projector_hex(hx, room))
            # Modellbeschriftung in den Bildschirmfarben, damit sie auch im hellen Raum lesbar bleibt
            self.assertEqual((v["cap-text"], v["cap-bg"]), (p2["roles"]["default"]["text"], p2["roles"]["default"]["slide"]))
        # Beamer hebt Schwarz an: im hellen Raum wird die dunkle Folie deutlich heller
        dark = build("oklch(0.72 0.13 75)", bg="dark", room="bright")
        v = G.view_vars(dark, "default", {"view": "projector"})
        self.assertGreater(C.rel_lum(v["slide"]), C.rel_lum(dark["roles"]["default"]["slide"]) + 0.2)

    def test_room_changes_only_projection(self):
        a, b = build("#2B4EA7", room="dim"), build("#2B4EA7", room="bright")
        self.assertEqual(a["roles"], b["roles"])
        self.assertEqual(a["extra"]["pair_note"], "pair.dim")
        self.assertEqual(b["extra"]["summary"], ["summary.bright"])


class TestPalette(unittest.TestCase):
    def test_presets_text_at_least_7(self):
        for pid, pal in preset_palettes().items():
            r = pal["roles"]["default"]
            for fg in ("text", "text-2", "accent-text"):
                for bg in ("slide", "slide-2"):
                    with self.subTest(preset=pid, fg=fg, bg=bg):
                        self.assertGreaterEqual(C.contrast(r[fg], r[bg]), 7.0)
            with self.subTest(preset=pid, fg="text reserve"):
                self.assertGreaterEqual(C.contrast(r["text"], r["slide"]), 7.7)
            for fg in ("accent", "line", "chart-1", "chart-2", "chart-3", "chart-4"):
                with self.subTest(preset=pid, fg=fg):
                    self.assertGreaterEqual(C.contrast(r[fg], r["slide"]), 3.0)
            self.assertTrue(all(p["pass"] for p in pal["pairs"]), pid)

    def test_constructions(self):
        pal = build("oklch(0.48 0.08 215)")
        r = pal["roles"]["default"]
        L, Cs, h = C.hex_to_oklch(r["accent"])
        t = min(max(0.1 * Cs, 0.004), 0.012)
        self.assertEqual(r["slide"], C.oklch_to_hex(0.985, 0.4 * t, h))
        self.assertEqual(r["slide-2"], C.oklch_to_hex(0.95, 0.6 * t, h))
        self.assertEqual(r["accent"], "#11697A")
        self.assertEqual(r["chart-1"], r["accent"])
        okabe = G.okabe_colors(CTX)
        pool = [r["accent"]] + [x for x in okabe if C.contrast(x, r["slide"]) >= 3.0]
        self.assertEqual([r[c] for c in G.CHARTS], C.pick_distinct(pool, 4, C.WORST_KINDS, r["accent"], r["slide"]))
        self.assertTrue(all(x in okabe for x in (r["chart-2"], r["chart-3"], r["chart-4"])))
        dark = build("oklch(0.72 0.13 75)", bg="dark")
        d = dark["roles"]["default"]
        Ld, Cd, hd = C.hex_to_oklch(C.parse("oklch(0.72 0.13 75)")["hex"])
        self.assertEqual(d["slide"], C.oklch_to_hex(0.20, min(max(0.1 * Cd, 0.004), 0.012), hd))
        self.assertGreater(C.rel_lum(d["text"]), C.rel_lum(d["slide"]))

    def test_changes_have_numbers(self):
        pal = build("oklch(0.48 0.08 215)")
        keys = [c["key"] for c in pal["changes"]]
        self.assertEqual(keys, ["accent-text"])
        light = build("#F2A900")  # Safran: zu hell für 3:1 auf der hellen Folie
        self.assertEqual([c["key"] for c in light["changes"]], ["accent-darker", "accent-text"])
        ch = light["changes"][0]
        self.assertLess(C.contrast(ch["from"], light["roles"]["default"]["slide"]), 3.0)
        self.assertGreaterEqual(C.contrast(ch["to"], light["roles"]["default"]["slide"]), 3.0)
        dark = build("oklch(0.72 0.13 75)", bg="dark")
        self.assertEqual([c["key"] for c in dark["changes"]], ["accent-dark", "accent-text-dark"])
        # Hinweise nennen die Ausgangsfarbe auf beiden Flächen, Änderungstexte gibt es in beiden Sprachen
        from web.copy import slides as copy  # noqa: PLC0415
        for lang in ("de", "en"):
            for key in ("accent-text", "accent-text-dark"):
                self.assertIn("{cr:from/slide-2}", copy.COPY[lang]["slides"]["change." + key])
        deep = build("#1B2A4A", bg="dark")
        self.assertEqual(deep["changes"][0]["key"], "accent-lighter")

    def test_findings(self):
        self.assertEqual(build("#2B4EA7")["findings"], [])
        self.assertEqual([f["id"] for f in build("#2B4EA7", bg="dark")["findings"]], ["dark-slide"])
        self.assertEqual([f["id"] for f in build("#2B4EA7", room="bright")["findings"]], ["bright-room"])

    def test_extreme_seeds_are_solvable(self):
        for seed in ("#FFFFFF", "#000000", "#FFFF00", "#0B0B0B", "#FAFAFA", "#808080"):
            for bg in ("light", "dark"):
                with self.subTest(seed=seed, bg=bg):
                    pal = build(seed, bg=bg)
                    self.assertTrue(all(p["pass"] for p in pal["pairs"]))
                    self.assertTrue(json.dumps(pal, allow_nan=False))

    def test_print_adds_gray_distance(self):
        pal = build("oklch(0.48 0.08 215)", pr=True)
        ids = [d["id"] for d in pal["distinct"]]
        self.assertEqual(ids, ["chart", "chart-gray"])
        g = pal["distinct"][1]
        r = pal["roles"]["default"]
        self.assertAlmostEqual(g["value"], C.gray_distance(r[g["a"]], r[g["b"]]), places=12)
        self.assertEqual([d["id"] for d in build("oklch(0.48 0.08 215)")["distinct"]], ["chart"])

    def test_lang_independent_and_deterministic(self):
        a = build("#E63946")
        b = build("#E63946")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


class TestOffice(unittest.TestCase):
    def ctx(self, pal, lang):
        from web.copy import core, slides as copy  # noqa: PLC0415
        return {"date": "2026-10-11", "url": "https://grundhofer.github.io/farbsprache/x/?p=petrol", "name": "Petrol",
                "task_name": "Präsentation", "core": core.COPY[lang]["export"], "text": copy.COPY[lang]["slides"],
                "rules": [], "sources": {}, "refs": C.reference_values(), "datasets": CTX["datasets"], "data": {}}

    def test_order_and_mapping(self):
        pal = build("oklch(0.48 0.08 215)")
        rows = pal["extra"]["office"]
        self.assertEqual([x["slot"] for x in rows], ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4",
                                                    "accent5", "accent6", "hlink", "folHlink"])
        self.assertEqual([x["role"] for x in rows], ["text", "slide", "text-2", "slide-2", "accent", "chart-2", "chart-3", "chart-4",
                                                    "text-2", "line", "accent-text", "text-2"])
        r = pal["roles"]["default"]
        self.assertNotIn(r["accent"], [r[x["role"]] for x in rows[5:8]], "Akzent 2 bis 4 ohne Dopplung mit dem Akzent")

    def test_hex_export(self):
        for lang in ("de", "en"):
            pal = build("oklch(0.48 0.08 215)")
            b = G.exports["hex"](pal, TASK, self.ctx(pal, lang), lang)[0]
            lines = b["text"].splitlines()
            self.assertEqual(len([ln for ln in lines if re.search(r"  #[0-9A-F]{6}  slide-", ln)]), 12)
            self.assertIn("Okabe", b["text"])
            self.assertTrue(b["note"].count("<br>") == 3 and b["note"].count("2026-10-11") == 3)
            dark = build("oklch(0.72 0.13 75)", bg="dark")
            self.assertIn(self.ctx(dark, lang)["text"]["office.dark"], G.exports["hex"](dark, TASK, self.ctx(dark, lang), lang)[0]["text"])
            self.assertNotIn(self.ctx(pal, lang)["text"]["office.dark"], b["text"])

    def test_rationale_numbers(self):
        for room in ("dim", "normal", "bright"):
            for lang in ("de", "en"):
                pal = build("#2B4EA7", room=room)
                text = G.exports["rationale"](pal, TASK, self.ctx(pal, lang), lang)
                r = pal["roles"]["default"]
                allowed = {C.fmt_ratio(C.contrast(r["text"], r["slide"]), lang), C.fmt_ratio(C.projected_contrast(r["text"], r["slide"], room), lang),
                           "3:1", "4,5:1", "4.5:1", "7:1"}
                with self.subTest(room=room, lang=lang):
                    for m in re.finditer(r"\d+[.,]?\d*:1", text):
                        self.assertIn(m.group(0), allowed)
                    self.assertIn(C.fmt_ratio(C.projected_contrast(r["text"], r["slide"], room), lang), text)


class TestData(unittest.TestCase):
    def test_menu_paths(self):
        srcs = {s["id"]: s for s in jload("data/sources/slides.json")["sources"]}
        apps = [m["app"] for m in TASK["menu_paths"]]
        self.assertEqual(apps, ["PowerPoint", "Keynote", "Google Slides"])
        for m in TASK["menu_paths"]:
            with self.subTest(app=m["app"]):
                self.assertIn(m["source"], srcs)
                self.assertEqual(m["url"], srcs[m["source"]]["url"])
                self.assertRegex(m["checked"], r"^2026-\d\d-\d\d$")
                self.assertEqual(srcs[m["source"]]["access"], "fulltext")
                self.assertTrue(m["text_de"] and m["text_en"])

    def test_own_checks_clean(self):
        from tools import checks, checks_slides  # noqa: PLC0415
        D, errs = checks.load_all([ROOT])
        self.assertEqual(checks_slides.check(D, lambda m: None), [])

    def test_no_hand_numbers_in_pattern_texts(self):
        from web.copy import slides as copy  # noqa: PLC0415
        for lang in ("de", "en"):
            for k, v in copy.COPY[lang]["slides"].items():
                for x in (v if isinstance(v, list) else [v]):
                    for m in re.finditer(r"\d+([.,]\d+)?\s*:\s*1(?![0-9])", re.sub(r"\{[^{}]*\}", "", x)):
                        self.assertIn(m.group(0), ("3:1", "4,5:1", "4.5:1", "7:1", "21:1"), k)


@unittest.skipUnless(REQUIRE or (DOCS / "de" / "folien" / "index.html").exists(), "docs/ fehlt – erst python3 build.py")
class TestPage(unittest.TestCase):
    def page(self, lang):
        seg = "folien" if lang == "de" else "slides"
        return (DOCS / lang / seg / "index.html").read_text(encoding="utf-8")

    def test_model_label_and_toggle(self):
        for lang, label in (("de", "Modellrechnung, vereinfacht: lineare Wiedergabe, keine Gammakurve des Projektors, kein Leinwandgewinn."),
                            ("en", "Simplified model: linear reproduction, no projector gamma curve, no screen gain.")):
            html = self.page(lang)
            self.assertIn(label, html)
            self.assertIn('data-toggle="view"', html)
            self.assertIn('data-val="projector"', html)

    def test_projected_values_on_page(self):
        html = self.page("de")
        for a, shown in (("#000000", "5,98:1"), ("#595959", "3,99:1"), ("#767676", "3,14:1")):
            self.assertRegex(html, r'<data class="num" value="[0-9.]+" data-m="proj" data-a="' + a + r'" data-b="#FFFFFF" data-t="normal">' + re.escape(shown) + "</data>")

    def test_no_upload(self):
        for lang in ("de", "en"):
            self.assertNotIn('type="file"', self.page(lang))
