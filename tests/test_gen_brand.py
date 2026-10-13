"""Fachfälle der Aufgabe Logo und Marke und gemeinsamer Export-Abzug der Aufgaben Logo und Marke sowie KI-Bild.

    python3 -m unittest tests.test_gen_brand
    python3 tests/test_gen_brand.py --dump     JSON aller Exportfälle dieser beiden Aufgaben (für tests/gen-brand.test.cjs)

Geprüft: Schriftfarbe ist der höhere Kontrast, Textvarianten erreichen 4,5:1 bei gleichem Farbton, die Markenfarbe
bleibt unverändert, Änderungshinweise genau dann, wenn eine Variante abweicht, AAA-Hinweis nur unter 7:1, zweite Farbe
mit Abständen, sehr dunkle und sehr helle Farben ohne Abbruch, Steckbrief mit Druck- und Rechtszeile in beiden
Sprachen und ohne gesperrte Namen. Läuft ohne gebaute Seite (Python-Generator direkt)."""
import copy, json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import color as C, export as X  # noqa: E402

DATE = "2026-10-11"
_SITE = []


def site():
    if not _SITE:
        s = build.Site([build.ROOT], build.ROOT / "tests" / "out" / "unused", DATE, allow_missing=True)
        s.prepare()
        _SITE.append(s)
    return _SITE[0]


def make(tid, preset=None, seed=None, **opts):
    """Palettenobjekt wie im Build (Startpalette) oder wie im Browser (eigene Eingabe)."""
    s = site()
    t = s.task_by_id[tid]
    p = next(x for x in t["presets"] if x["id"] == preset) if preset else t["presets"][0]
    inp = s.make_input(t, p)
    if seed:
        inp["seed"] = C.parse(seed, False)["hex"]
    inp["options"].update(opts)
    pal = s.gens[tid].build(t, copy.deepcopy(inp), s.gen_ctx(t))
    custom = bool(seed) or bool(opts)
    return build.frame_palette(t, None if seed else p, inp, pal, s.custom_names()), t, (None if custom else p)


def ectx(tid, pal, lang, preset_id):
    """Exportkontext wie pages/task.py (Startpalette) bzw. FS.site.render.exportCtx (eigene Eingabe)."""
    s = site()
    t = s.task_by_id[tid]
    rules = [s.rules[r] for r in t["rules"] if r in s.rules]
    return {"date": DATE, "url": s.abs_url(lang, tid) + ("?p=" + preset_id if preset_id else "?c=000000"),
            "name": pal["name_" + lang], "task_name": t["name_" + lang], "core": s.copy[lang]["export"],
            "text": s.copy[lang][tid], "rules": [r for r in rules if X.show_if(r.get("show_if"), pal)],
            "sources": s.sources, "refs": s.refs, "datasets": s.datasets, "data": s.gen_data(t)}


def export(tid, pal, fmt, lang, preset_id=None):
    s = site()
    t = s.task_by_id[tid]
    return X.render(fmt, pal, t, ectx(tid, pal, lang, preset_id), lang, {}, s.gens[tid])


CASES = [
    ("brand", "tinte", None, {}), ("brand", "safran", None, {}), ("brand", "kraeftiges-rot", None, {}),
    ("brand", None, "#11697A", {}), ("brand", None, "#000000", {}), ("brand", None, "#FFFFFF", {}),
    ("brand", None, "#2B4EA7", {"c2": "#E63946"}), ("brand", None, "#E63946", {"c2": "#E83A47"}),
    ("ai-image", "dunkelblau", None, {}), ("ai-image", "gruen", None, {}), ("ai-image", "erdtoene", None, {}),
    ("ai-image", None, "#11697A", {"s": "calm"}), ("ai-image", None, "#11697A", {"s": "contrast"}),
    ("ai-image", None, "#E63946", {"s": "signal"}), ("ai-image", None, "#777777", {"s": "contrast"}),
    ("ai-image", None, None, {"f": ["#1B3A76", "#F6F3ED", "#D33B36", "#FFFFFF"]}),
    ("ai-image", None, None, {"f": ["#1B3A76", "#F6F3ED"]}),
    ("ai-image", None, None, {"f": ["#777777", "#787878", "#E63946"]}),
    ("ai-image", None, None, {"f": ["#FF0000", "#FF0000", "#00FF00"]}), ("ai-image", None, None, {"f": ["#E63946", "#E63946", "#D33B36"]}),
    ("ai-image", None, None, {"w": "70-20-10", "b1": "the wall", "b2": " the floor ", "b3": ""}),
] + [("ai-image", p, None, {"mdl": m}) for p in ("dunkelblau", "erdtoene")
     for m in ("flux2", "ideogram3", "recraft", "midjourney", "gpt-image")]


def dump():
    """Alle Fälle von Logo und Marke sowie KI-Bild mit Eingabe, Kontexten und Python-Ergebnis (Palette und Exportblöcke je Format und Sprache)."""
    s = site()
    out = []
    for tid, preset, seed, opts in CASES:
        pal, t, pr = make(tid, preset, seed, **opts)
        case = {"task": tid, "preset": pr["id"] if pr else None, "frame_preset": pal["preset"], "inp": pal["input"], "palette": pal,
                "gen_ctx": {"datasets": {}, "comparisons": s.D["comparisons"], "lang": None, "data": s.gen_data(t)},
                "custom_names": s.custom_names(), "exports": {}}
        for lang in ("de", "en"):
            c = ectx(tid, pal, lang, pr["id"] if pr else None)
            case["exports"][lang] = {"ctx": dict(c, datasets={}, sources={}), "blocks": {}}  # beide ungenutzt in den Formaten dieser Aufgaben
            for fmt in t["exports"]["visible"] + (t["exports"].get("more") or []):
                case["exports"][lang]["blocks"][fmt] = X.render(fmt, pal, t, c, lang, {}, s.gens[tid])
        out.append(case)
    from tools.gen import ai_image as A  # noqa: PLC0415
    cn = s.D["colornames"]
    grid = ["#%02X%02X%02X" % (r, g, b) for r in range(0, 256, 17) for g in range(0, 256, 17) for b in range(0, 256, 17)]
    return {"tasks": {tid: s.task_by_id[tid] for tid in ("brand", "ai-image")}, "cases": out,
            "names": {hx: A.color_name(hx, cn) for hx in grid}}


class TestBrand(unittest.TestCase):
    def test_presets_text_color_and_variants(self):
        want_on = {"tinte": "#FFFFFF", "safran": "#000000", "kraeftiges-rot": "#000000"}
        for pid, on in want_on.items():
            pal, t, _ = make("brand", pid)
            r = pal["roles"]["default"]
            with self.subTest(preset=pid):
                self.assertEqual(r["on-brand"], on)
                self.assertEqual(r["brand"], C.parse(next(p["seed"] for p in t["presets"] if p["id"] == pid), False)["hex"])
                self.assertGreaterEqual(C.contrast(r["brand-text-light"], "#FFFFFF"), 4.5)
                self.assertGreaterEqual(C.contrast(r["brand-text-dark"], "#16191D"), 4.5)
                self.assertEqual(r["brand-gray"], C.gray_hex(r["brand"]))
                self.assertTrue(all(p["pass"] for p in pal["pairs"]))
                self.assertEqual(len(pal["pairs"]), 3)

    def test_variant_keeps_hue_and_changes_are_reported(self):
        for seed in ("#2B4EA7", "#F2A900", "#E63946", "#11697A", "#6B7941", "#C92695"):
            pal, _, _ = make("brand", seed=seed)
            r = pal["roles"]["default"]
            h0 = C.hex_to_oklch(seed)[2]
            changed = {ch["role"] for ch in pal["changes"]}
            for rid in ("brand-text-light", "brand-text-dark"):
                with self.subTest(seed=seed, role=rid):
                    self.assertEqual(rid in changed, r[rid] != r["brand"])
                    if r[rid] != r["brand"]:  # gleicher Farbton im Löser; das Gamut-Mapping darf ihn leicht verschieben
                        self.assertLess(abs(((C.hex_to_oklch(r[rid])[2] - h0 + 180) % 360) - 180), 10.0)
            for ch in pal["changes"]:
                self.assertEqual(ch["from"], r["brand"])
                self.assertEqual(ch["to"], r[ch["role"]])
                self.assertLess(ch["values"]["before"], 4.5)
                self.assertGreaterEqual(ch["values"]["after"], 4.5)

    def test_extreme_seeds_do_not_fail(self):
        for seed in ("#000000", "#0A0A0A", "#101010", "#16191D", "#FFFFFF", "#FAFAFA", "#808080"):
            pal, _, _ = make("brand", seed=seed)
            r = pal["roles"]["default"]
            with self.subTest(seed=seed):
                self.assertGreaterEqual(C.contrast(r["brand-text-light"], "#FFFFFF"), 4.5)
                self.assertGreaterEqual(C.contrast(r["brand-text-dark"], "#16191D"), 4.5)
                self.assertGreaterEqual(C.contrast(r["on-brand"], r["brand"]), 4.5)

    def test_aaa_gap_rule_only_below_7(self):
        s = site()
        rule = s.rules["brand-aaa-gap"]
        for pid in ("tinte", "safran", "kraeftiges-rot"):
            pal, _, _ = make("brand", pid)
            best = max(C.contrast(pal["roles"]["default"]["brand"], x) for x in ("#FFFFFF", "#000000"))
            with self.subTest(preset=pid):
                self.assertEqual(X.show_if(rule["show_if"], pal), best < 7)
        self.assertTrue(X.show_if(rule["show_if"], make("brand", "kraeftiges-rot")[0]))

    def test_second_color(self):
        pal, _, _ = make("brand", seed="#2B4EA7", c2="#E63946")
        r = pal["roles"]["default"]
        self.assertEqual(r["brand-2"], "#E63946")
        ids = [d["id"] for d in pal["distinct"]]
        self.assertEqual(ids, ["brand2", "brand2-gray"])
        md = C.min_distance(["#2B4EA7", "#E63946"], C.WORST_KINDS)
        self.assertAlmostEqual(pal["distinct"][0]["value"], md["value"], places=12)
        self.assertAlmostEqual(pal["distinct"][1]["value"], C.gray_distance("#2B4EA7", "#E63946"), places=12)
        self.assertIn({"mode": "default", "fg": "brand-2", "bg": "brand", "ratio": C.contrast("#E63946", "#2B4EA7")}, pal["decorative"])
        self.assertEqual(pal["extra"]["summary"], ["summary.c2"])
        self.assertEqual(pal["findings"], [])
        close, _, _ = make("brand", seed="#E63946", c2="#E83A47")
        self.assertEqual([f["id"] for f in close["findings"]], ["brand2-close"])

    def test_factsheet_has_print_and_law_lines(self):
        s = site()
        for args in (("tinte", None, {}), ("kraeftiges-rot", None, {}), (None, "#2B4EA7", {"c2": "#E63946"})):
            pal, t, pr = make("brand", args[0], args[1], **args[2])
            for lang in ("de", "en"):
                text = export("brand", pal, "factsheet", lang, pr["id"] if pr else None)[0]["text"]
                tc = s.copy[lang]["brand"]
                with self.subTest(case=args, lang=lang):
                    self.assertIn(tc["fs.print"], text)
                    self.assertIn(tc["fs.law"], text)
                    self.assertIn("- Hex: " + pal["roles"]["default"]["brand"], text)
                    self.assertIn("rgb(", text)
                    self.assertIn("oklch(", text)
                    self.assertNotRegex(text, r"\{(cr|dist|gs|hex|palette|url):?")
                    self.assertEqual("## " + tc["fs.h_c2"] in text, "brand-2" in pal["roles"]["default"])
                    for term in s.D["blocklist"]:
                        self.assertIsNone(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I), term)
                    ok = C.shortest_oklch(pal["roles"]["default"]["brand"])
                    self.assertEqual(C.parse(ok)["hex"], pal["roles"]["default"]["brand"])
                    for m in re.finditer(r"(\d+[.,]\d\d):1", text):
                        self.assertIn(m.group(0), {C.fmt_ratio(C.contrast(a, b), lang) for a in pal["roles"]["default"].values()
                                                   for b in list(pal["roles"]["default"].values()) + ["#FFFFFF", "#000000"]})

    def test_aaa_lines_in_factsheet(self):
        for pid, gap in (("tinte", False), ("safran", False), ("kraeftiges-rot", True)):
            pal, _, pr = make("brand", pid)
            text = export("brand", pal, "factsheet", "de", pid)[0]["text"]
            with self.subTest(preset=pid):
                self.assertEqual("Mit keiner der beiden Schriftfarben" in text, gap)

    def test_spec_texts(self):
        s = site()
        de, en = s.copy["de"]["brand"], s.copy["en"]["brand"]
        self.assertEqual(de["h1"], "Eine Markenfarbe, die überall funktioniert")
        self.assertEqual(en["h1"], "A brand color that works everywhere")
        self.assertEqual(de["fs.print"], "- CMYK und Sonderfarbe legst du mit der Druckerei fest. Prüfe einen Softproof im Zielprofil.")
        self.assertIn("Prüfe, ob in deiner Branche eine Farbmarke eingetragen ist (DPMA, EUIPO).", de["fs.law"])
        self.assertEqual(s.rules["brand-aaa-gap"]["text_de"].split(". ")[0] + ".",
                         "Mit keiner der beiden Schriftfarben erreicht deine Farbe 7:1.")
        t = s.task_by_id["brand"]
        self.assertEqual([p["seed"] for p in t["presets"]], ["#2B4EA7", "#F2A900", "#E63946"])
        self.assertEqual(t["exports"]["primary"], "factsheet")
        self.assertEqual(t["exports"]["visible"], ["factsheet", "css", "hex"])
        self.assertEqual(t["exports"]["more"], ["dtcg", "rationale"])
        self.assertEqual([c["id"] for c in t["controls"] if c["visible"]], ["c2"])


if __name__ == "__main__":
    if "--dump" in sys.argv:
        sys.stdout.write(json.dumps(dump(), ensure_ascii=False, allow_nan=False))
    else:
        unittest.main()
