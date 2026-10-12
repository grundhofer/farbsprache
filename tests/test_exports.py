"""Exporte (Spezifikation 5.0 bis 5.7, 7.9) aus den Python-Renderern für alle Startpaletten aller Aufgaben
und der Testaufgabe: alle Rollen vorhanden, kein None/undefined/NaN, jede Zahl der Form „a/b 15,76“ im
Prompt und in den DTCG-$extensions aus den Tokens desselben Exports nachgerechnet, Tailwind und DTCG
strukturell gültig, jede x:1-Angabe der Begründung ist ein Kontrast zweier Rollen der Palette."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import color as C, export as X  # noqa: E402

DATE = "2026-10-11"


def cases():
    """(site, task, preset, palette, lang, ctx, opts) für alle Kombinationen."""
    out = []
    for roots, seg in (([build.ROOT], None), ([build.ROOT, build.FIXTURES], build.FIXTURE_SEG)):
        site = build.Site(roots, build.ROOT / "tests" / "out" / "unused", DATE, allow_missing=True, seg=seg)
        site.prepare()
        for t in site.tasks:
            rules = [site.rules[r] for r in t["rules"]]
            for p in t["presets"]:
                pal = site.palettes[t["id"]][p["id"]]
                for lang in ("de", "en"):
                    ctx = {"date": DATE, "url": site.abs_url(lang, t["id"]) + "?p=" + p["id"], "name": pal["name_" + lang],
                           "task_name": t["name_" + lang], "core": site.copy[lang]["export"], "text": site.copy[lang][t["id"]],
                           "rules": [r for r in rules if X.show_if(r.get("show_if"), pal)], "sources": site.sources,
                           "refs": site.refs, "datasets": site.datasets, "data": site.gen_data(t)}
                    opt_ids = [o["id"] for o in t["exports"].get("options") or []]
                    for opts in [{o: False for o in opt_ids}, {o: True for o in opt_ids}]:
                        out.append((site, t, p, pal, lang, ctx, opts))
    return out


def generic(site, t, fmt):
    """Bietet die Aufgabe das Format an und nutzt dafür den generischen Renderer (kein gen.exports)?"""
    fmts = t["exports"]["visible"] + (t["exports"].get("more") or [])
    return fmt in fmts and fmt not in (getattr(site.gens[t["id"]], "exports", None) or {})


def included(t, pal, mode, opts):
    return [r["id"] for r in X.role_defs(t, pal, mode, opts)]


def css_vars(text):
    """{name: hex} je Block (:root, dark), Reihenfolge erhalten."""
    blocks, cur = [], None
    for line in text.splitlines():
        if line.strip().startswith(":root {"):
            cur = {}
            blocks.append(cur)
        for m in re.finditer(r"--([a-z0-9-]+):\s*(#[0-9A-F]{6});", line):
            if cur is not None:
                cur[m.group(1)] = m.group(2)
    return blocks


class TestExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = cases()

    def test_have_cases(self):
        self.assertTrue(any(t["id"] == "fixture" for _, t, *_ in self.cases))
        for fmt in ("agent", "rationale"):
            self.assertTrue(any(generic(s, t, fmt) for s, t, *_ in self.cases), f"kein Fall für das generische Format {fmt}")

    def test_no_placeholders_left(self):
        for site, t, p, pal, lang, ctx, opts in self.cases:
            gen = site.gens[t["id"]]
            for f in t["exports"]["visible"] + (t["exports"].get("more") or []):
                for b in X.render(f, pal, t, ctx, lang, opts, gen):
                    with self.subTest(task=t["id"], preset=p["id"], lang=lang, fmt=f):
                        self.assertNotRegex(b["text"], r"\bNone\b|undefined|\bNaN\b|\{(palette|task|date_iso|url)\}|__N_")
                        self.assertNotRegex(b["text"], r"\{(cr|dist|gray|gs|L|proj|scrim|ref|hex|count):", "Platzhalter nicht aufgelöst")
                        self.assertNotIn("<data", b["text"])

    def test_css_and_hex_have_every_role(self):
        for site, t, p, pal, lang, ctx, opts in self.cases:
            css = X.css(pal, t, ctx, lang, opts)
            hexl = X.hex_list(pal, t, ctx, lang, opts)
            blocks = css_vars(css)
            self.assertEqual(len(blocks), len(pal["modes"]))
            for i, mode in enumerate(pal["modes"]):
                want = {X.css_name(r): pal["roles"][mode][r["id"]] for r in X.role_defs(t, pal, mode, opts)}
                with self.subTest(task=t["id"], preset=p["id"], lang=lang, mode=mode, opts=opts):
                    self.assertEqual(blocks[i], want)
                    for name, hx in want.items():
                        self.assertRegex(hexl, re.escape(name) + r" +" + hx)
                    for r in t["roles"]:
                        if r.get("export_option") and not opts.get(r["export_option"]):
                            self.assertNotIn("--" + X.css_name(r) + ":", css)
            # OKLCH-Kommentare führen exakt auf das Hex zurück
            for m in re.finditer(r"(#[0-9A-F]{6}); /\* (oklch\([^)]*\))", css):
                self.assertEqual(C.parse(m.group(2))["hex"], m.group(1), m.group(0))

    def test_tailwind_structure(self):
        for site, t, p, pal, lang, ctx, opts in self.cases:
            for tw in (X.tailwind(pal, t, ctx, lang, opts), X.render("tailwind", pal, t, ctx, lang, opts, site.gens[t["id"]])[0]["text"]):
                with self.subTest(task=t["id"], preset=p["id"], lang=lang, opts=opts):
                    self.assertIn('@import "tailwindcss";', tw)
                    theme = tw.split("@theme inline {", 1)[1]
                    refs = re.findall(r"--color-([a-z0-9-]+): var\(--([a-z0-9-]+)\);", theme)
                    defined = set(re.findall(r"--([a-z0-9-]+): #[0-9A-F]{6};", tw.split("@theme inline {")[0]))
                    # 5.2: jede --color-x verweist auf eine --x, die jeder Modus definiert (sonst färbt die Utility dort nichts)
                    per_mode = [set(re.findall(r"--([a-z0-9-]+): #[0-9A-F]{6};", b)) for b in tw.split("@theme inline {")[0].split(":root {")[1:]]
                    self.assertEqual(len(per_mode), len(pal["modes"]))
                    self.assertTrue(refs)
                    self.assertEqual(len({a for a, _ in refs}), len(refs), "doppelte --color-*")
                    for a, b in refs:
                        self.assertEqual(a, b)
                        self.assertIn(b, defined, f"--color-{a} verweist auf undefiniertes --{b}")
                        for i, names in enumerate(per_mode):
                            self.assertIn(b, names, f"--color-{a}: --{b} fehlt im Modus {pal['modes'][i]}")
                for mode in pal["modes"]:
                    for rid in included(t, pal, mode, opts):
                        self.assertIn(X.css_name(next(r for r in t["roles"] if r["id"] == rid)), defined)

    def test_dtcg_valid_and_recalculated(self):
        for site, t, p, pal, lang, ctx, opts in self.cases:
            blocks = X.dtcg(pal, t, ctx, lang, opts)
            self.assertEqual(len(blocks), len(pal["modes"]))
            for mode, b in zip(pal["modes"], blocks):
                with self.subTest(task=t["id"], preset=p["id"], lang=lang, mode=mode):
                    doc = json.loads(b["text"])
                    toks = doc["color"]
                    # Token-Namen sind die Exportnamen nach 6.3 (css_name), wie in CSS und Hex-Liste
                    names = X.css_names(t)
                    self.assertEqual(list(toks), [names[rid] for rid in included(t, pal, mode, opts)])
                    for rid in included(t, pal, mode, opts):
                        tok = toks[names[rid]]
                        self.assertEqual(tok["$type"], "color")
                        v = tok["$value"]
                        self.assertEqual(v["colorSpace"], "srgb")
                        self.assertEqual(len(v["components"]), 3)
                        self.assertTrue(all(0 <= c <= 1 for c in v["components"]))
                        self.assertEqual(v["hex"], pal["roles"][mode][rid])
                        rgb = [int(v["hex"][i:i + 2], 16) for i in (1, 3, 5)]
                        self.assertEqual([round(c * 255) for c in v["components"]], rgb)
                    ext = doc["$extensions"][X.NS]
                    hx = {name: tok["$value"]["hex"] for name, tok in toks.items()}
                    # jedes Paar nennt Tokens derselben Datei (kein Rückgriff auf Rollen-IDs)
                    for pr in ext["pairs"] + ext["decorative"]:
                        r = C.contrast(hx[pr["fg"]], hx[pr["bg"]])
                        self.assertAlmostEqual(pr["ratio"], int(r * 100 + 1e-9) / 100, places=9, msg=str(pr))
                    self.assertEqual(len(ext["pairs"]), sum(1 for x in pal["pairs"] if x["mode"] == mode))

    def test_agent_numbers_recalculated(self):
        seen = set()
        for site, t, p, pal, lang, ctx, opts in self.cases:
            fmts = t["exports"]["visible"] + (t["exports"].get("more") or [])
            if "agent" not in fmts:
                continue
            # der Renderer, den die Seite nutzt (gen.exports vor dem generischen); Prompts ohne Token-Block (Text auf Bild) fallen weg
            text = X.render("agent", pal, t, ctx, lang, opts, site.gens[t["id"]])[0]["text"]
            if "```css" not in text or ctx["core"]["h_pairs"] not in text:
                continue
            seen.add(t["id"])
            sep = "," if lang == "de" else "."
            tokens = text.split("```css", 1)[1].split("```", 1)[0]
            blocks = css_vars(tokens)
            mode_of = {mode: blocks[i] for i, mode in enumerate(pal["modes"])}
            n = 0
            for mode in pal["modes"]:
                part = text.split(ctx["core"]["h_pairs"], 1)[1].split(ctx["core"]["h_rules"], 1)[0]
                if len(pal["modes"]) > 1:
                    part = part.split("\n" + ctx["core"]["label." + mode] + "\n", 1)[1].split("\n\n", 1)[0]
                for m in re.finditer(r"([a-z0-9-]+)/([a-z0-9-]+) (\d+" + re.escape(sep) + r"\d\d)", part):
                    v = mode_of[mode]
                    # Jeder Name eines Paars ist ein Token desselben Prompts (5.4, T-05), kein Rückgriff auf Rollen-IDs
                    with self.subTest(task=t["id"], preset=p["id"], lang=lang, pair=m.group(0)):
                        self.assertIn(m.group(1), v, f"{m.group(1)} steht nicht im Token-Block")
                        self.assertIn(m.group(2), v, f"{m.group(2)} steht nicht im Token-Block")
                        self.assertEqual(m.group(3), C.fmt_ratio(C.contrast(v[m.group(1)], v[m.group(2)]), lang)[:-2])
                    n += 1
            want = len(pal["pairs"]) + len(pal["decorative"]) + len(pal.get("advisory") or [])
            self.assertEqual(n, want, f"{t['id']} {p['id']} {lang}: Paare im Prompt")
            self.assertIn(ctx["url"], text)
        self.assertTrue({"website", "status", "charts", "fixture"} <= seen, seen)

    def test_rationale_numbers_are_role_contrasts(self):
        for site, t, p, pal, lang, ctx, opts in self.cases:
            if not generic(site, t, "rationale"):
                continue
            text = X.rationale(pal, t, ctx, lang, opts)
            allowed = set()
            for mode in pal["modes"]:
                hs = list(pal["roles"][mode].values())
                for a in hs:
                    for b in hs:
                        allowed.add(C.fmt_ratio(C.contrast(a, b), lang))
            allowed |= {"3:1", "4,5:1", "4.5:1", "7:1", "21:1"}
            for m in re.finditer(r"\d+[.,]?\d*:1", text):
                with self.subTest(task=t["id"], preset=p["id"], lang=lang, value=m.group(0)):
                    self.assertIn(m.group(0), allowed)
            self.assertIn(ctx["url"], text)


if __name__ == "__main__":
    unittest.main()
