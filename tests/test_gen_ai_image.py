"""Fachfälle der Aufgabe KI-Bild.

Geprüft: 33 Pflicht- und 40 Golden-Namen, keine Sperrwörter, Startsets mit den Erwartungs-Hex, Farbblock
für FLUX.2, Ideogram und Recraft wörtlich, keine Hex-Werte in Ideogram (Prompt), Midjourney und gpt-image,
Recraft-Gewichte höchstens 1, Vorbehalte nur außerhalb der Kopiertexte, Stand je Modell sichtbar, Vorrang f vor c vor p,
Vorschläge nach festen Formeln, Textzeile nur ab 4,5:1, kein Teal-Orange-Startset."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_gen_brand import export, make, site  # noqa: E402
from tools import color as C  # noqa: E402
from tools.gen import ai_image as A  # noqa: E402

MANDATORY = [("#000000", "black"), ("#FFFFFF", "white"), ("#777777", "mid gray"), ("#EDF1F2", "off-white"),
             ("#F6F3ED", "off-white with a warm tint"), ("#FF0000", "vivid red"), ("#00FF00", "vivid green"),
             ("#0000FF", "vivid blue"), ("#FFFF00", "yellow"), ("#00FFFF", "cyan"), ("#FF00FF", "vivid magenta"),
             ("#E69F00", "orange-yellow"), ("#56B4E9", "light blue"), ("#009E73", "blue-green"), ("#F0E442", "yellow"),
             ("#6A4225", "brown"), ("#6B7941", "dark yellow-green"), ("#0072B2", "blue"), ("#D55E00", "red-orange"),
             ("#CC79A7", "magenta"), ("#11697A", "teal"), ("#2B4EA7", "blue"), ("#000080", "dark blue"),
             ("#8B4513", "brown"), ("#808000", "dark yellow"), ("#FFC0CB", "pale pink"), ("#4B0082", "deep purple"),
             ("#1B3A76", "deep blue"), ("#D33B36", "red"), ("#225A31", "deep green"), ("#E6E9E6", "off-white"),
             ("#F0D947", "yellow"), ("#E9DCC8", "pale muted orange-yellow")]
FLUX_SET1 = ("Color palette: deep blue (#1B3A76) as the dominant color, about 60% of the image, on [BACKGROUND AND LARGE SHAPES]; "
             "off-white with a warm tint (#F6F3ED) for secondary areas, about 30%, on [SECONDARY ELEMENTS]; a single accent of "
             "red (#D33B36) only on [THE FOCAL ELEMENT], under 10%. No other hues. Neutral white balance, no warm or yellow cast, "
             "no teal-and-orange grading. Flat color areas: no gradients, glow or color fringes. Any text in deep blue (#1B3A76) "
             "on off-white with a warm tint (#F6F3ED).")
IDEOGRAM_SET1 = ("Color palette: deep blue as the dominant color, about 60% of the image, on [BACKGROUND AND LARGE SHAPES]; "
                 "off-white with a warm tint for secondary areas, about 30%, on [SECONDARY ELEMENTS]; a single accent of red only "
                 "on [THE FOCAL ELEMENT], under 10%. No other hues. Neutral white balance, no warm or yellow cast, no "
                 "teal-and-orange grading. Flat color areas: no gradients, glow or color fringes. Any text in deep blue on "
                 "off-white with a warm tint.")
RECRAFT_SET1 = ('{"controls": {"colors": [{"rgb": [27, 58, 118], "weight": 0.6}, {"rgb": [246, 243, 237], "weight": 0.3}, '
                '{"rgb": [211, 59, 54], "weight": 0.1}]}}')
MODELS = ("flux2", "ideogram3", "recraft", "midjourney", "gpt-image")
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
CAVEATS = ("guarantee", "Garantie", "eyedropper", "Pipette", "not checked", "nicht geprüft", "Farbsprache", "http")


def cn():
    return site().D["colornames"]


class TestNames(unittest.TestCase):
    def test_mandatory_33(self):
        for hx, name in MANDATORY:
            with self.subTest(hex=hx):
                self.assertEqual(A.color_name(hx, cn()), name)

    def test_golden_40_contains_mandatory(self):
        g = cn()["golden"]
        self.assertEqual(len(g), 40)
        self.assertEqual([(x["hex"], x["name"]) for x in g[:33]], MANDATORY)
        for x in g:
            self.assertEqual(A.color_name(x["hex"], cn()), x["name"], x["hex"])

    def test_no_blocked_word_anywhere(self):
        blocked = cn()["blocked_words"]
        names = {A.color_name("#%02X%02X%02X" % (r, g, b), cn()) for r in range(0, 256, 15) for g in range(0, 256, 15) for b in range(0, 256, 15)}
        self.assertGreater(len(names), 40)
        for n in names:
            for w in blocked:
                self.assertIsNone(re.search(r"(?<![a-z])" + w + r"(?![a-z])", n), (n, w))

    def test_lighter_darker(self):
        self.assertEqual(A.block_names(["#1B3A76", "#2B4EA7", "#F6F3ED"], cn())[:2], ["deep blue", "blue"])
        names = A.block_names(["#E63946", "#D33B36"], cn())
        self.assertEqual(names, ["lighter red", "darker red"])
        self.assertEqual(A.block_names(["#777777", "#787878"], cn()), ["mid gray", "mid gray"])
        # Gleiche Hex-Werte heißen gleich, ohne „lighter“ und „darker“; same-names greift
        self.assertEqual(A.block_names(["#FF0000", "#FF0000", "#00FF00"], cn())[:2], ["vivid red", "vivid red"])
        self.assertEqual(len(set(A.block_names(["#FFFFFF"] * 4, cn()))), 1)
        self.assertEqual(A.block_names(["#E63946", "#E63946", "#D33B36"], cn()), ["lighter red", "lighter red", "darker red"])
        pal, _, _ = make("ai-image", f=["#FF0000", "#FF0000", "#00FF00"])
        self.assertIn("same-names", [f["id"] for f in pal["findings"]])
        for mdl in ("flux2", "ideogram3"):
            pal, _, _ = make("ai-image", f=["#FF0000", "#FF0000", "#00FF00"], mdl=mdl)
            text = export("ai-image", pal, "prompt", "en")[0]["text"]
            self.assertNotRegex(text, r"\b(lighter|darker) vivid red\b", mdl)


class TestPalettes(unittest.TestCase):
    def test_startsets(self):
        want = {"dunkelblau": (("#1B3A76", "deep blue"), ("#F6F3ED", "off-white with a warm tint"), ("#D33B36", "red")),
                "gruen": (("#225A31", "deep green"), ("#E6E9E6", "off-white"), ("#F0D947", "yellow")),
                "erdtoene": (("#6A4225", "brown"), ("#E9DCC8", "pale muted orange-yellow"), ("#6B7941", "dark yellow-green"))}
        for pid, cols in want.items():
            pal, _, _ = make("ai-image", pid)
            r, names = pal["roles"]["default"], pal["extra"]["names"]
            with self.subTest(preset=pid):
                for role, (hx, name) in zip(("dominant", "secondary", "accent"), cols):
                    self.assertEqual((r[role], names[role]), (hx, name))
                bases = [n.split(" ")[-1] for n in names.values()]
                self.assertFalse(any(b in ("teal", "cyan", "blue-green") for b in bases) and any(b in ("orange", "red-orange", "orange-yellow") for b in bases))

    def test_text_pair_set1(self):
        pal, _, _ = make("ai-image", "dunkelblau")
        self.assertEqual(pal["extra"]["text_pair"], ["dominant", "secondary"])
        self.assertEqual(C.fmt_ratio(pal["pairs"][0]["ratio"], "de"), "9,90:1")
        self.assertEqual(C.fmt_ratio(C.contrast("#D33B36", "#1B3A76"), "de"), "2,32:1")
        for p in pal["pairs"]:
            self.assertNotEqual({p["fg"], p["bg"]}, {"accent", "dominant"})

    def test_no_text_line_below_45(self):
        pal, _, _ = make("ai-image", f=["#777777", "#8A8A8A", "#E63946"])
        self.assertIsNone(pal["extra"]["text_pair"])
        self.assertIn("no-text-line", [f["id"] for f in pal["findings"]])
        self.assertNotIn("Any text", export("ai-image", pal, "prompt", "en")[0]["text"])

    def test_priority_f_c_p(self):
        f = ["#123456", "#FEDCBA", "#E63946"]
        pal, _, _ = make("ai-image", "gruen", seed="#11697A", f=f)
        self.assertEqual([pal["roles"]["default"][r] for r in ("dominant", "secondary", "accent")], f)
        self.assertEqual(pal["extra"]["source"], "f")
        pal, _, _ = make("ai-image", "gruen", seed="#11697A")
        self.assertEqual(pal["roles"]["default"]["dominant"], "#11697A")
        self.assertEqual(pal["extra"]["source"], "seed")
        with self.assertRaises(C.SolveError) as e:
            make("ai-image", f=["#123456"])
        self.assertEqual(e.exception.key, "few-colors")
        self.assertIn("solve.few-colors", site().copy["de"]["ai-image"])

    def test_suggestion_formulas(self):
        for seed in ("#11697A", "#E63946", "#F2A900", "#1B3A76", "#777777", "#FFFFFF"):
            L, Cs, h = C.hex_to_oklch(seed)
            h = 0.0 if h is None else h
            want = {
                "calm": [seed, C.oklch_to_hex(0.95, min(0.02, Cs), h) if L < 0.7 else C.oklch_to_hex(0.30, min(0.04, Cs), h),
                         C.oklch_to_hex(L - 0.25, Cs, h) if L >= 0.5 else C.oklch_to_hex(L + 0.30, Cs, h)],
                "contrast": [seed, C.oklch_to_hex(0.96, 0.01, h), C.oklch_to_hex(0.70 if L < 0.55 else 0.45, min(max(Cs, 0.10), 0.16), (h + 180) % 360)],
                "signal": [C.oklch_to_hex(0.95, 0.008, h), C.oklch_to_hex(0.30, 0.01, h), seed]}
            for kind, cols in want.items():
                pal, _, _ = make("ai-image", seed=seed, s=kind)
                with self.subTest(seed=seed, kind=kind):
                    self.assertEqual([pal["roles"]["default"][r] for r in ("dominant", "secondary", "accent")], cols)
                    v = A.suggest_values(seed, kind)
                    self.assertAlmostEqual(v["redgreen"], C.min_distance(cols, ["deutan", "protan"])["value"], places=12)

    def test_weights_and_background(self):
        pal, _, _ = make("ai-image", f=["#1B3A76", "#F6F3ED"])
        self.assertEqual(pal["extra"]["weights"], {"dominant": 80, "secondary": 20})
        pal, _, _ = make("ai-image", w="50-40-10")
        self.assertEqual(pal["extra"]["weights"], {"dominant": 50, "secondary": 40, "accent": 10})
        pal, _, _ = make("ai-image", f=["#1B3A76", "#F6F3ED", "#D33B36", "#FFFFFF"], mdl="recraft")
        blocks = export("ai-image", pal, "prompt", "de")
        self.assertIn('"background_color": {"rgb": [255, 255, 255]}', blocks[1]["text"])
        self.assertIn("on [LARGE SHAPES]", blocks[0]["text"])
        self.assertIn("the background in white", blocks[0]["text"])

    def test_distinct_four_kinds(self):
        pal, _, _ = make("ai-image", "dunkelblau")
        self.assertEqual([d["kind"] for d in pal["distinct"]], ["normal", "deutan", "protan", "gray"])
        for d in pal["distinct"]:
            r = pal["roles"]["default"]
            self.assertAlmostEqual(d["value"], C.distance(r[d["a"]], r[d["b"]], d["kind"]), places=12)


class TestPrompt(unittest.TestCase):
    def test_spec_examples_word_for_word(self):
        for lang in ("de", "en"):
            pal, _, _ = make("ai-image", "dunkelblau")
            self.assertEqual(export("ai-image", pal, "prompt", lang, "dunkelblau")[0]["text"], FLUX_SET1)
            pal, _, _ = make("ai-image", "dunkelblau", mdl="ideogram3")
            b = export("ai-image", pal, "prompt", lang)
            self.assertEqual(b[0]["text"], IDEOGRAM_SET1)
            self.assertEqual(b[1]["text"], "#1B3A76 #F6F3ED #D33B36")
            pal, _, _ = make("ai-image", "dunkelblau", mdl="recraft")
            b = export("ai-image", pal, "prompt", lang)
            self.assertEqual(b[0]["text"], IDEOGRAM_SET1)
            self.assertEqual(b[1]["text"], RECRAFT_SET1)

    def test_hex_only_where_documented_and_weights(self):
        for pid in ("dunkelblau", "gruen", "erdtoene"):
            for mdl in MODELS:
                pal, _, _ = make("ai-image", pid, mdl=mdl)
                for lang in ("de", "en"):
                    b = export("ai-image", pal, "prompt", lang)
                    with self.subTest(preset=pid, model=mdl, lang=lang):
                        self.assertEqual(b[0]["lang"], "en")
                        if mdl == "flux2":
                            self.assertTrue(HEX.search(b[0]["text"]))
                        else:
                            self.assertIsNone(HEX.search(b[0]["text"]), b[0]["text"])
                        self.assertNotIn("--sref", b[0]["text"])
                        if mdl == "recraft":
                            ws = [float(x) for x in re.findall(r'"weight": ([0-9.]+)', b[1]["text"])]
                            self.assertLessEqual(sum(ws), 1.0 + 1e-12)
                            self.assertEqual(json.loads(b[1]["text"])["controls"]["colors"][0]["rgb"],
                                             [int(pal["roles"]["default"]["dominant"][i:i + 2], 16) for i in (1, 3, 5)])
                        if mdl == "gpt-image":
                            self.assertTrue(b[0]["text"].endswith("Keep this palette. Natural color balance, avoid dramatic color grading."))
                        self.assertEqual(len(b), 2 if mdl in ("ideogram3", "recraft") else 1)

    def test_caveats_outside_and_stand_visible(self):
        s = site()
        models = {m["id"]: m for m in s.D["models"]["models"]}
        for mdl in MODELS:
            pal, _, _ = make("ai-image", "dunkelblau", mdl=mdl)
            for lang in ("de", "en"):
                duty = s.copy[lang]["ai-image"]["note.duty"]
                for b in export("ai-image", pal, "prompt", lang):
                    with self.subTest(model=mdl, lang=lang, label=b["label"]):
                        for w in CAVEATS:
                            self.assertNotIn(w, b["text"])
                        self.assertIn(duty, b["note"])
                        self.assertIn(models[mdl]["checked"], b["note"])
                        if models[mdl].get("quote"):
                            self.assertIn(C.esc(models[mdl]["quote"]), b["note"])

    def test_hex_list_names_own_colors(self):
        pal, _, _ = make("ai-image", "gruen", f=["#123456", "#FEDCBA"])
        for lang, name in (("de", "Eigene Farben"), ("en", "Your colors")):
            head = export("ai-image", pal, "hex", lang)[0]["text"].split("\n")[0]
            self.assertIn(" · " + name + " · ", head)
            self.assertNotIn(pal["name_" + lang], head)
        pal, _, _ = make("ai-image", "gruen")
        self.assertIn(" · " + pal["name_de"] + " · ", export("ai-image", pal, "hex", "de", "gruen")[0]["text"].split("\n")[0])

    def test_parts_from_text_fields(self):
        pal, _, _ = make("ai-image", "dunkelblau", b1=" the wall ", b2="", b3="the door")
        t = export("ai-image", pal, "prompt", "en")[0]["text"]
        self.assertIn("on the wall;", t)
        self.assertIn("on [SECONDARY ELEMENTS];", t)
        self.assertIn("only on the door,", t)

    def test_models_file(self):
        s = site()
        ms = s.D["models"]["models"]
        self.assertEqual([m["id"] for m in ms], list(MODELS))
        want = {"flux2": "hex-in-prompt", "ideogram3": "palette-field", "recraft": "api-weights", "midjourney": "words-only", "gpt-image": "words-only"}
        for m in ms:
            self.assertEqual(m["method"], want[m["id"]])
            self.assertIn(m["source_id"], s.sources)
            self.assertRegex(m["checked"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(ms[0]["quote"], "precision matching — no approximation")
        self.assertEqual(ms[1]["quote"], "a direction, not an exact color match")
        self.assertEqual(ms[1]["max_colors"], 8)


if __name__ == "__main__":
    unittest.main()
