"""Fachfälle der Aufgabe Diagramm (Spezifikation 3.3, 4.4, 4.1.12, 5.8, Abnahme P2).
Okabe-Ito auf Weiß und Dunkel, viridis-Richtung und Monotonie, ColorBrewer-Klassen und Pflichtsatz, Rot-Grün-Ablehnung,
keine gemischten Familien, eigene Farbe auf 3:1, Hervorhebung, JS-Array nach 5.8, Muster-Variablen."""
import copy, itertools, json, math, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C, export as X  # noqa: E402
from tools.gen import charts as G  # noqa: E402


def jload(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


TASK = jload("data/tasks/charts.json")
DS = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (ROOT / "data" / "datasets").glob("*.json")}
CTX = {"datasets": DS, "comparisons": jload("data/comparisons.json"), "lang": None, "data": {}}
RULES = [r for f in ("core", "charts") for r in jload(f"data/rules/{f}.json")["rules"] if r["id"] in TASK["rules"]]
CB_NOTICE = "This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/)."
FAMS = {"cat": ["okabe-ito", "tol-bright", "tol-muted"], "seq": ["viridis", "cb-blues", "seed"],
        "div": ["blue-orange", "cb-rdbu", "cb-puor", "seed"], "hl": ["gray"]}
NS = {"cat": [2, 4, 6, 8], "seq": [3, 5, 9], "div": [3, 5, 7, 9], "hl": [1]}
SEEDS = [None, "#F2A900", "#E63946", "#11697A", "#000000", "#FFFFFF", "#808080", "#16191D", "#2CA02C", "#0000FF", "#FFFF00"]


def opts(**kw):
    o = {"t": "cat", "n": 4, "pr": False, "bg": "light", "mark": "lines", "fam": "okabe-ito"}
    o.update(kw)
    return o


def build(seed=None, **kw):
    return G.build(TASK, {"seed": seed, "colors": None, "options": opts(**kw)}, CTX)


def data_roles(pal, prefix):
    r = pal["roles"]["default"]
    return [r[k] for k in sorted((k for k in r if k.startswith(prefix)), key=lambda k: int(k.rsplit("-", 1)[1]))]


def matrix():
    for t in ("cat", "seq", "div", "hl"):
        for fam, n, bg, pr in itertools.product(FAMS[t], NS[t], ("light", "dark"), (False, True)):
            for mark in (("lines", "areas") if t == "cat" else ("lines",)):
                yield dict(t=t, fam=fam, n=n, bg=bg, pr=pr, mark=mark)


def export_ctx(pal, lang="de"):
    from web.copy import charts as copy_charts, core as copy_core
    return {"date": "2026-10-11", "url": "https://grundhofer.github.io/farbsprache/de/diagramm/?p=cat-okabe", "name": pal["name_" + lang],
            "task_name": TASK["name_" + lang], "core": copy_core.COPY[lang]["export"], "text": copy_charts.COPY[lang]["charts"],
            "rules": [], "sources": {}, "refs": C.reference_values(), "datasets": DS, "data": {}}


class TestCategorical(unittest.TestCase):
    def test_okabe_on_white(self):
        pal = build()
        self.assertEqual(data_roles(pal, "series-"), ["#0072B2", "#D55E00", "#009E73", "#CC79A7"])
        cols = data_roles(pal, "series-")
        got = [C.fmt_dist(C.min_distance(cols[:k])["value"], "de") for k in (2, 3, 4)]
        self.assertEqual(got, ["22,3", "11,2", "7,9"])
        d = pal["distinct"][0]
        self.assertEqual((d["id"], C.fmt_dist(d["value"], "de"), d["kind"]), ("series", "7,9", "deutan"))
        self.assertEqual(pal["extra"]["datasets"], ["okabe-ito"])
        self.assertEqual(pal["findings"], [])

    def test_okabe_white_pool_is_four(self):
        pal = build(n=7)
        self.assertEqual(len(data_roles(pal, "series-")), 4, "genau vier Linienfarben auf Weiß")
        self.assertIn("summary.pool", pal["extra"]["summary"])

    def test_okabe_on_dark_all_seven(self):
        pal = build(n=7, bg="dark")
        cols = data_roles(pal, "series-")
        self.assertEqual(len(cols), 7)
        self.assertEqual(cols[0], "#F0E442")
        low = min(cols, key=lambda c: C.contrast(c, "#16191D"))
        self.assertEqual((low, C.fmt_ratio(C.contrast(low, "#16191D"), "de")), ("#0072B2", "3,40:1"))
        self.assertNotIn("summary.pool", pal["extra"]["summary"])

    def test_areas_take_all_colors_with_usage(self):
        pal = build(n=7, mark="areas")
        cols = data_roles(pal, "series-")
        self.assertEqual(len(cols), 7)
        use = pal["usage"]["default"]
        for i, c in enumerate(cols, 1):
            r = C.contrast(c, "#FFFFFF")
            self.assertEqual(use[f"series-{i}"], "text" if r >= 4.5 else "lines" if r >= 3 else "area")
        self.assertTrue(any(f["id"] == "low-contrast" for f in pal["findings"]))
        self.assertFalse(any(p["fg"].startswith("series-") for p in pal["pairs"]), "Flächen sind keine Normpaare")
        vv = G.view_vars(pal, "default", {})
        for i in range(1, 8):
            self.assertEqual(vv[f"e{i}"], "#222222" if use[f"series-{i}"] == "area" else "transparent")

    def test_seed_becomes_series_1_at_3_1(self):
        pal = build("#F2A900")
        s1 = pal["roles"]["default"]["series-1"]
        self.assertNotEqual(s1, "#F2A900")
        self.assertGreaterEqual(C.contrast(s1, "#FFFFFF"), 3.0)
        self.assertLess(C.hex_to_oklch(s1)[0], C.hex_to_oklch("#F2A900")[0], "dunklere Variante")
        L, Cs, h = C.hex_to_oklch("#F2A900")
        self.assertEqual(s1, C.solve_l(Cs, h, ["#FFFFFF"], 3.0, -1, L)["hex"], "nur L in OKLCH verschoben")
        ch = pal["changes"][0]
        self.assertEqual((ch["role"], ch["from"], ch["to"], ch["key"]), ("series-1", "#F2A900", s1, "series-1"))
        self.assertEqual(build("#0072B2")["changes"], [], "eine Farbe mit 3:1 bleibt unverändert")
        dark = build("#000000", bg="dark")
        self.assertGreaterEqual(C.contrast(dark["roles"]["default"]["series-1"], "#16191D"), 3.0)
        self.assertGreater(C.rel_lum(dark["roles"]["default"]["series-1"]), C.rel_lum("#16191D"))

    def test_print_adds_gray(self):
        pal = build(pr=True)
        ids = [d["id"] for d in pal["distinct"]]
        self.assertEqual(ids, ["series", "series-gray"])
        g = pal["distinct"][1]
        self.assertEqual(g["kind"], "gray")
        self.assertIn("summary.cat-pr", pal["extra"]["summary"])
        cols = data_roles(pal, "series-")
        pool = [c for c in [x["hex"] for x in DS["okabe-ito"]["schemes"][0]["colors"] if x["name"] != "black"] if C.contrast(c, "#FFFFFF") >= 3]
        self.assertEqual(cols, C.pick_distinct(pool, 4, ["normal", "deutan", "protan", "gray"], None, "#FFFFFF"))


class TestOrdered(unittest.TestCase):
    def test_viridis_dark_is_more_on_white(self):
        for n in range(3, 10):
            pal = build(t="seq", fam="viridis", n=n)
            steps = data_roles(pal, "step-")
            ls = [C.hex_to_oklch(s)[0] for s in steps]
            self.assertTrue(all(a > b for a, b in zip(ls, ls[1:])), f"n={n}: auf Weiß wird es dunkler")
            self.assertEqual(steps[-1], "#440154")
            self.assertEqual(steps[0], "#FDE725")
            table = [c["hex"] for c in DS["viridis"]["schemes"][0]["colors"]]
            want = [table[math.floor(i / (n - 1) * 255 + 0.5)] for i in range(n)][::-1]
            self.assertEqual(steps, want)
            self.assertFalse(any(f["id"] == "not-monotone" for f in pal["findings"]))

    def test_viridis_not_reversed_on_dark(self):
        steps = data_roles(build(t="seq", fam="viridis", n=5, bg="dark"), "step-")
        self.assertEqual((steps[0], steps[-1]), ("#440154", "#FDE725"))

    def test_colorbrewer_classes_exact(self):
        cb = {s["id"]: s for s in DS["colorbrewer"]["schemes"]}
        for n in range(3, 10):
            self.assertEqual(data_roles(build(t="seq", fam="cb-blues", n=n), "step-"), [c["hex"] for c in cb["blues"]["classes"][str(n)]])
        for fam, sid in (("cb-rdbu", "rdbu"), ("cb-puor", "puor")):
            for n in (3, 5, 7, 9):
                pal = build(t="div", fam=fam, n=n)
                self.assertEqual(data_roles(pal, "step-"), [c["hex"] for c in cb[sid]["classes"][str(n)]][::-1], "kühle Seite zuerst")
                self.assertEqual(pal["extra"]["datasets"], ["colorbrewer"])

    def test_blue_orange_construction(self):
        steps = data_roles(build(t="div", n=5), "step-")
        for i, s in enumerate(steps):
            u = (2 * i - 4) / 4
            hue = 255 if u < 0 else 50 if u > 0 else 0
            self.assertEqual(s, C.oklch_to_hex(0.97 - 0.55 * abs(u), 0.13 * abs(u), hue))
        self.assertIsNone(C.hex_to_oklch(steps[2])[2], "Mitte unbunt")

    def test_monotone_everywhere(self):
        for o in matrix():
            if o["t"] not in ("seq", "div"):
                continue
            for seed in SEEDS:
                pal = build(seed, **o)
                with self.subTest(seed=seed, **o):
                    self.assertTrue(G._monotone(data_roles(pal, "step-"), o["t"]))
                    self.assertFalse(any(f["id"] == "not-monotone" for f in pal["findings"]))
        self.assertFalse(G._monotone(["#000000", "#FFFFFF", "#808080"], "seq"))
        self.assertFalse(G._monotone(["#000000", "#FFFFFF", "#000000"], "seq"))
        self.assertTrue(G._monotone(["#000000", "#FFFFFF", "#000000"], "div"))

    def test_seed_gradient(self):
        pal = build("#11697A", t="seq", fam="seed", n=5)
        steps = data_roles(pal, "step-")
        h = C.hex_to_oklch("#11697A")[2]
        for i, s in enumerate(steps):
            t = i / 4
            self.assertEqual(s, C.oklch_to_hex(0.96 - 0.64 * t, 0.02 + 0.10 * math.sin(math.pi * min(1.0, 1.1 * t)), h))
        self.assertEqual(pal["extra"]["datasets"], [])
        self.assertIn("summary.seed-unused", build("#11697A", t="seq", fam="viridis")["extra"]["summary"])
        self.assertIn("summary.seed-missing", build(None, t="seq", fam="seed")["extra"]["summary"])
        gray = data_roles(build("#808080", t="seq", fam="seed"), "step-")
        self.assertTrue(all(C.hex_to_oklch(s)[2] is None for s in gray), "unbunte Farbe gibt einen grauen Verlauf")


class TestRedGreen(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(G.red_green(30.0, 140.0), (255.0, True))
        self.assertEqual(G.red_green(140.0, 30.0), (255.0, True))
        self.assertEqual(G.red_green(350.0, 125.0), (255.0, True))
        self.assertEqual(G.red_green(30.0, 210.0), (210.0, False))
        self.assertEqual(G.red_green(None, 140.0), (140.0, False))

    def test_div_with_own_color_replaces_opposite(self):
        """Rot-Grün-Ablehnung bei div mit eigener Farbe: Mit h_b = h_s + 180° liegen die Enden in OKLCH nie zugleich
        im Rot- und im Grünbereich (Befund, siehe Bericht). Der Pfad wird deshalb mit erzwungener Regel geprüft."""
        for h in range(0, 360):
            self.assertFalse(G.red_green(float(h), (h + 180.0) % 360.0)[1], f"h={h}")
        orig = G.red_green
        try:
            G.red_green = lambda a, b: (255.0, True)
            pal = build("#E63946", t="div", fam="seed", n=5)
        finally:
            G.red_green = orig
        steps = data_roles(pal, "step-")
        self.assertEqual(steps[-1], C.oklch_to_hex(0.42, 0.13, 255.0))
        ch = pal["changes"][0]
        self.assertEqual((ch["role"], ch["key"], ch["to"]), ("step-5", "red-green", steps[-1]))
        h_s = C.hex_to_oklch("#E63946")[2]
        self.assertEqual(ch["from"], C.oklch_to_hex(0.97 - 0.55, 0.13, (h_s + 180.0) % 360.0))
        from web.copy import charts as copy_charts
        for lang in ("de", "en"):
            text = copy_charts.COPY[lang]["charts"]["change.red-green"]
            html = C.render_text(text, X.rctx(pal, "default", {"from": ch["from"], "to": ch["to"]}, {}), lang, False)[0]
            self.assertIn(ch["to"], html)

    def test_div_own_color_normal(self):
        pal = build("#E63946", t="div", fam="seed", n=7)
        steps = data_roles(pal, "step-")
        h_s = C.hex_to_oklch("#E63946")[2]
        self.assertLess(abs(C.hex_to_oklch(steps[0])[2] - h_s), 2)
        self.assertEqual(pal["changes"], [])


class TestFamiliesAndPairs(unittest.TestCase):
    def test_no_palette_mixes_families(self):
        fam_sets = {"okabe-ito": {c["hex"] for c in DS["okabe-ito"]["schemes"][0]["colors"] if c["name"] != "black"},
                    "tol-bright": {c["hex"] for c in DS["tol"]["schemes"][0]["colors"]},
                    "tol-muted": {c["hex"] for c in DS["tol"]["schemes"][1]["colors"]}}
        cb = {s["id"]: s for s in DS["colorbrewer"]["schemes"]}
        viridis = {c["hex"] for c in DS["viridis"]["schemes"][0]["colors"]}
        for o in matrix():
            for seed in SEEDS:
                pal = build(seed, **o)
                with self.subTest(seed=seed, **o):
                    if o["t"] == "cat":
                        cols = data_roles(pal, "series-")
                        rest = cols[1:] if seed else cols
                        self.assertTrue(set(rest) <= fam_sets[o["fam"]])
                    elif o["fam"] == "viridis":
                        self.assertTrue(set(data_roles(pal, "step-")) <= viridis)
                    elif o["fam"].startswith("cb-"):
                        sid = {"cb-blues": "blues", "cb-rdbu": "rdbu", "cb-puor": "puor"}[o["fam"]]
                        self.assertTrue(set(data_roles(pal, "step-")) <= {c["hex"] for c in cb[sid]["classes"][str(o["n"])]})

    def test_normative_pairs_never_fail(self):
        for o in matrix():
            for seed in SEEDS:
                pal = build(seed, **o)
                with self.subTest(seed=seed, **o):
                    self.assertEqual([p for p in pal["pairs"] if not p["pass"]], [])
                    json.dumps(pal, allow_nan=False)
                    for d in pal["distinct"]:
                        hx = pal["roles"]["default"]
                        self.assertAlmostEqual(d["value"], C.distance(hx[d["a"]], hx[d["b"]], d["kind"]), places=12)

    def test_frame_roles(self):
        for bg, b, t, t2, grid in (("light", "#FFFFFF", "#222222", "#555555", 0.90), ("dark", "#16191D", "#E8E8E8", "#AEAEAE", 0.30)):
            r = build(bg=bg)["roles"]["default"]
            self.assertEqual((r["bg"], r["text"], r["text-2"]), (b, t, t2))
            self.assertGreaterEqual(C.contrast(r["text-2"], b), 4.5)
            self.assertEqual(r["grid"], C.oklch_to_hex(grid, 0, 0))

    def test_highlight(self):
        pal = build(t="hl", n=1, fam="gray")
        r = pal["roles"]["default"]
        self.assertEqual((r["highlight"], r["context"]), ("#0072B2", "#949494"))
        self.assertEqual(C.fmt_ratio(C.contrast(r["context"], "#FFFFFF"), "de"), "3,03:1")
        self.assertEqual(pal["extra"]["datasets"], ["okabe-ito"])
        own = build("#F2A900", t="hl", n=1, fam="gray")
        self.assertGreaterEqual(C.contrast(own["roles"]["default"]["highlight"], "#FFFFFF"), 3.0)
        self.assertEqual(own["changes"][0]["key"], "highlight")
        self.assertEqual(own["extra"]["datasets"], [])
        dark = build(t="hl", n=1, fam="gray", bg="dark")["roles"]["default"]
        self.assertGreaterEqual(C.contrast(dark["context"], "#16191D"), 3.0)

    def test_highlight_never_merges_with_context(self):
        """Weiß auf Weiß bzw. Schwarz auf Dunkel ergäbe auf 3:1 genau das Kontextgrau. Dann bleibt Okabe-Blau,
        mit Änderungshinweis; eine graue Farbe, die sich vom Kontext abhebt, bleibt stehen."""
        for seed, bg in (("#FFFFFF", "light"), ("#949494", "light"), ("#000000", "dark"), ("#16191D", "dark")):
            pal = build(seed, t="hl", n=1, fam="gray", bg=bg)
            r = pal["roles"]["default"]
            with self.subTest(seed=seed, bg=bg):
                self.assertEqual(r["highlight"], "#0072B2")
                self.assertEqual([(c["key"], c["from"], c["to"]) for c in pal["changes"]], [("highlight-gray", seed, "#0072B2")])
                self.assertEqual(pal["extra"]["datasets"], ["okabe-ito"])
                self.assertGreaterEqual(C.worst_distance(r["highlight"], r["context"]), C.JND_DISTANCE)
        for seed, bg in (("#000000", "light"), ("#808080", "light"), ("#FFFFFF", "dark")):
            pal = build(seed, t="hl", n=1, fam="gray", bg=bg)
            with self.subTest(seed=seed, bg=bg):
                self.assertEqual(pal["roles"]["default"]["highlight"], seed)
                self.assertEqual(pal["changes"], [])
        for o in matrix():
            if o["t"] != "hl":
                continue
            for seed in SEEDS:
                r = build(seed, **o)["roles"]["default"]
                with self.subTest(seed=seed, **o):
                    self.assertGreaterEqual(C.worst_distance(r["highlight"], r["context"]), C.JND_DISTANCE)


class TestExportsAndPattern(unittest.TestCase):
    def preset(self, pid):
        p = next(x for x in TASK["presets"] if x["id"] == pid)
        o = {c["id"]: c["default"] for c in TASK["controls"]}
        o.update(p["options"])
        pal = G.build(TASK, {"seed": None, "colors": None, "options": o}, CTX)
        pal.update({"preset": pid, "name_de": p["name_de"], "name_en": p["name_en"]})
        return pal

    def test_js_array_format_5_8(self):
        pal = self.preset("cat-okabe")
        text = G.exports["js"](pal, TASK, export_ctx(pal), "de", {})
        self.assertEqual(text.splitlines(), [
            "// Farbsprache · Diagramm · Gruppen vergleichen · Okabe-Ito, Linien auf Weiß · berechnet am 2026-10-11",
            "// Farben nach Masataka Okabe und Kei Ito, Color Universal Design (2002)",
            "// Reihenfolge berechnet: größter kleinster Abstand bei normalem Sehen, Deuteranopie und Protanopie.",
            'const chartColors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"];',
            "// Werte und Prüfung: https://grundhofer.github.io/farbsprache/de/diagramm/?p=cat-okabe"])

    def test_colorbrewer_notice_in_every_export(self):
        for fam, t in (("cb-blues", "seq"), ("cb-rdbu", "div"), ("cb-puor", "div")):
            pal = build(t=t, fam=fam, n=5)
            pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
            for lang in ("de", "en"):
                ctx = export_ctx(pal, lang)
                for f in TASK["exports"]["visible"] + TASK["exports"]["more"]:
                    blocks = X.render(f, pal, TASK, ctx, lang, {}, G)
                    with self.subTest(fam=fam, lang=lang, fmt=f):
                        self.assertTrue(all(CB_NOTICE in b["text"] for b in blocks))
        pal = build()
        pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
        self.assertNotIn(CB_NOTICE, X.render("hex", pal, TASK, export_ctx(pal), "de", {}, G)[0]["text"])

    def test_tol_copyright_in_every_export(self):
        # R-11: Exporte mit Tol-Farben tragen den Copyright-Vermerk aus tol_colors.py (required_notice des Datensatzes),
        # in jedem Format und beiden Sprachen; vorher stand dort nur „Paul Tol, tol_colors.py, BSD-3-Clause“.
        notice = jload("data/datasets/tol.json")["required_notice"]
        for fam in ("tol-bright", "tol-muted"):
            pal = build(fam=fam)
            pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
            for lang in ("de", "en"):
                ctx = export_ctx(pal, lang)
                for f in TASK["exports"]["visible"] + TASK["exports"]["more"]:
                    blocks = X.render(f, pal, TASK, ctx, lang, {}, G)
                    with self.subTest(fam=fam, lang=lang, fmt=f):
                        self.assertTrue(all(notice in b["text"] and "BSD-3-Clause" in b["text"] for b in blocks))

    def test_dataset_notices(self):
        for kw, want in (({"t": "seq", "fam": "viridis", "n": 5}, "viridis: van der Walt, Smith, Firing (CC0)"),
                         ({"fam": "tol-bright"}, "Paul Tol, tol_colors.py: Copyright (c) 2022, Paul Tol. All rights reserved. BSD-3-Clause"),
                         ({"t": "hl", "n": 1, "fam": "gray"}, "Farben nach Masataka Okabe und Kei Ito, Color Universal Design (2002)")):
            pal = build(**kw)
            pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
            self.assertIn(want, G.exports["js"](pal, TASK, export_ctx(pal), "de", {}))
        own = build("#E63946", t="seq", fam="seed")
        own.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
        self.assertEqual(X.notices(own, export_ctx(own), TASK, {}), [])

    def test_view_vars(self):
        pal = build(t="seq", fam="viridis", n=9)
        vv = G.view_vars(pal, "default", {})
        steps = {vv[f"c{i}"] for i in range(1, 36)}
        self.assertEqual(steps, set(data_roles(pal, "step-")), "die Kachelkarte nutzt jede Stufe")
        self.assertEqual((vv["v-tiles"], vv["v-lines"], vv["v-bars"]), ("block", "none", "none"))
        self.assertEqual([vv[f"t{k}"] for k in range(1, 10)], ["flex"] * 9)
        cat = G.view_vars(build(n=3), "default", {})
        self.assertEqual([cat[f"s{k}"] for k in range(1, 9)], ["flex"] * 3 + ["none"] * 5)
        self.assertEqual(G.view_vars(build(mark="areas"), "default", {})["v-lines"], "none")
        self.assertEqual(G.view_vars(build(bg="dark"), "default", {})["scheme"], "dark")
        for n in range(3, 10):
            self.assertEqual(sorted({v * n // 100 for v in G.TILE}), list(range(n)), f"n={n}: alle Stufen im Muster")

    def test_view_vars_outline_low_steps(self):
        """Stufen unter 3:1 bekommen in Kachelkarte und Legende eine Kontur in text (Regel chart-adjacent)."""
        for kw in ({"t": "seq", "fam": "viridis", "n": 5}, {"t": "div", "n": 7, "bg": "dark"}, {"t": "seq", "fam": "cb-blues", "n": 9}):
            pal = build(**kw)
            r, use = pal["roles"]["default"], pal["usage"]["default"]
            vv = G.view_vars(pal, "default", {})
            n = sum(1 for k in r if k.startswith("step-"))
            with self.subTest(**kw):
                for k in range(1, n + 1):
                    want = r["text"] if C.contrast(r[f"step-{k}"], r["bg"]) < 3.0 else "transparent"
                    self.assertEqual(vv[f"f{k}"], want)
                    self.assertEqual(use[f"step-{k}"] == "area", want != "transparent")
                for i, val in enumerate(G.TILE, 1):
                    self.assertEqual(vv[f"k{i}"], vv[f"f{val * n // 100 + 1}"])
                self.assertIn(r["text"], {vv[f"k{i}"] for i in range(1, 36)}, "mindestens eine Kachel mit Kontur")
        html = (ROOT / "patterns" / "charts.html").read_text(encoding="utf-8")
        for i in range(1, 36):
            self.assertIn(f"var(--d-k{i}, transparent)", html)
        for k in range(1, 10):
            self.assertIn(f"var(--d-f{k}, transparent)", html)

    def test_pattern_and_mini(self):
        html = (ROOT / "patterns" / "charts.html").read_text(encoding="utf-8")
        mini = (ROOT / "patterns" / "charts-mini.svg").read_text(encoding="utf-8")
        for k in range(1, 9):
            self.assertIn(f"var(--d-series-{k})", html)
            self.assertIn(f"var(--d-s{k}", html)
        for k in range(1, 10):
            self.assertIn(f"var(--d-step-{k})", html)
        for i in range(1, 36):
            self.assertIn(f"var(--d-c{i})", html)
        self.assertIn('[data-labels="direct"]', html)
        self.assertIn('viewBox="0 0 120 90"', mini, "Mini-Vorschau 4:3")
        roles = build()["roles"]["default"]
        for v in __import__("re").findall(r"var\(--d-([a-z0-9-]+)\)", mini):
            self.assertIn(v, roles, "Mini-Vorschau nutzt nur Rollen von Startpalette 1")

    def test_no_round_in_generator(self):
        for f in (ROOT / "tools" / "gen" / "charts.py", ROOT / "web" / "gen" / "charts.js", ROOT / "web" / "ui" / "charts.js"):
            src = f.read_text(encoding="utf-8")
            for bad in ("round(", "toFixed(", "Math.round("):
                self.assertNotIn(bad, src, f"{f.name}: {bad}")

    def test_every_text_key_renders(self):
        """Jeder Textschlüssel, den der Generator setzt (summary, change, finding, distinct), steht in beiden Sprachen
        und lässt sich mit der Palette rendern; das gilt auch für eigene Farben, die der Build nicht sieht."""
        from web.copy import charts as copy_charts
        seen = set()
        for o in matrix():
            for seed in SEEDS:
                pal = build(seed, **o)
                for lang in ("de", "en"):
                    tc = copy_charts.COPY[lang]["charts"]
                    keys = [(k, None) for k in pal["extra"]["summary"]]
                    keys += [("change." + c["key"], {"from": c["from"], "to": c["to"]}) for c in pal["changes"]]
                    keys += [("finding." + f["id"], None) for f in pal["findings"]]
                    keys += [("distinct." + d["id"], None) for d in pal["distinct"]]
                    for k, extra in keys:
                        seen.add(k)
                        with self.subTest(key=k, lang=lang, seed=seed, **o):
                            self.assertIn(k, tc)
                            C.render_text(tc[k], X.rctx(pal, "default", extra, {"refs": C.reference_values()}), lang, False)
        for k in ("summary.cat", "summary.cat-pr", "summary.seq", "summary.seq-dark", "summary.div", "summary.hl", "summary.pool",
                  "summary.seed-unused", "summary.seed-missing", "summary.seed-gray", "summary.seed-gray-div", "change.series-1",
                  "change.highlight", "change.highlight-gray", "finding.low-contrast"):
            self.assertIn(k, seen, f"{k} kommt in der Matrix vor")

    def test_exports_never_none_nan_undefined(self):
        """Kein Kopiertext eines Formats enthält „None“, „NaN“ oder „undefined“, auch nicht für eigene Farben."""
        from web.copy import charts as copy_charts
        fmts = TASK["exports"]["visible"] + TASK["exports"]["more"]
        for o in matrix():
            if o["pr"] or o["n"] not in (2, 3, 5, 8, 9, 1):
                continue
            for seed in (None, "#F2A900", "#FFFFFF", "#808080"):
                pal = build(seed, **o)
                pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
                for lang in ("de", "en"):
                    ctx = export_ctx(pal, lang)
                    ctx["rules"] = [r for r in RULES if X.show_if(r.get("show_if"), pal)]
                    for f in fmts:
                        for b in X.render(f, pal, TASK, ctx, lang, {}, G):
                            with self.subTest(seed=seed, lang=lang, fmt=f, **o):
                                for bad in ("None", "NaN", "undefined", "{", "}") if f in ("hex", "rationale") else ("None", "NaN", "undefined"):
                                    self.assertNotIn(bad, b["text"])
        self.assertTrue(copy_charts.COPY["de"]["charts"]["rationale"])

    def test_custom_name_names_only_the_family_shown(self):
        """Nach Z (R-01, M-06, T-11): Der Name eines eigenen Zustands ohne eigene Farbe nennt Familie, Anzahl und
        Hintergrund der gezeigten Farben, nie eine andere Familie und nie ColorBrewer (9.4). Die Pflichtnennungen
        (extra.datasets) passen zur Familie, aus der die Farben stammen."""
        from web.copy import charts as copy_charts
        dataset = {"okabe-ito": ["okabe-ito"], "tol-bright": ["tol"], "tol-muted": ["tol"], "viridis": ["viridis"],
                   "cb-blues": ["colorbrewer"], "cb-rdbu": ["colorbrewer"], "cb-puor": ["colorbrewer"], "blue-orange": [],
                   "gray": ["okabe-ito"]}
        for o in matrix():
            pal = build(**o)
            fam = G.DEFAULT_FAM[o["t"]] if o["fam"] == "seed" else o["fam"]
            n = len(data_roles(pal, "series-" if o["t"] == "cat" else "step-"))
            with self.subTest(**o):
                self.assertEqual(pal["extra"]["datasets"], dataset[fam])
                for lang in ("de", "en"):
                    tc = copy_charts.COPY[lang]["charts"]
                    name = G.display_name(pal, tc, lang)
                    others = [tc["name.fam." + f] for f in dataset if f not in (fam, "gray")]
                    self.assertEqual([x for x in others if x in name], [], name)
                    self.assertNotIn("ColorBrewer", name)
                    self.assertIn(tc["name.bg." + o["bg"]], name)
                    if o["t"] != "hl":
                        self.assertIn(tc["name.fam." + fam], name)
                        self.assertIn(C.fmt_count(n, lang), name)
        self.assertEqual(G.display_name(build(t="seq", fam="cb-blues", n=9), copy_charts.COPY["de"]["charts"], "de"), "Blues, 9 Stufen auf Weiß")
        self.assertEqual(G.display_name(build(fam="tol-bright", bg="dark", mark="areas", n=3), copy_charts.COPY["en"]["charts"], "en"),
                         "Tol bright, 3 colors, areas on dark")

    def test_series_below_3_1_are_areas_in_every_export(self):
        """M-02: Serien unter 3:1 (usage area) tragen in Hex-Liste, CSS, Design-Tokens und Prompt den Zweck
        „nur Flächen mit Kontur“ mit der Konturfarbe, nie „Linien, Punkte, Balken“."""
        from web.copy import charts as copy_charts
        seen = 0
        for o in matrix():
            if o["mark"] != "areas" or o["pr"]:
                continue
            for seed in (None, "#CF6BF8", "#F2A900"):
                pal = build(seed, **o)
                pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
                low = [k for k, u in pal["usage"]["default"].items() if u == "area" and k.startswith("series-")]
                for lang in ("de", "en"):
                    tc = copy_charts.COPY[lang]["charts"]
                    use = tc["use.area"].replace("{text}", pal["roles"]["default"]["text"])
                    lines_use = next(r for r in TASK["roles"] if r["id"] == "series-1")["use_" + lang]
                    for f in ("hex", "css", "dtcg", "agent"):
                        text = "\n".join(b["text"] for b in X.render(f, pal, TASK, export_ctx(pal, lang), lang, {}, G))
                        for rid in low:
                            cn = X.css_name(next(r for r in TASK["roles"] if r["id"] == rid))
                            rows = [x for x in text.split("\n") if x.lstrip().startswith((cn + " ", "--" + cn + ":", '"' + cn + '":'))]
                            with self.subTest(seed=seed, lang=lang, fmt=f, role=rid, **o):
                                self.assertTrue(rows)
                                for x in rows:
                                    self.assertIn(use, x)
                                    self.assertNotIn(lines_use, x)
                            seen += 1
        self.assertGreater(seen, 0, "kein Fall mit einer Serie unter 3:1")

    def test_every_data_color_has_a_checked_value(self):
        """MV-01: Auch Datenfarben ohne Normpaar (Verlauf, Abweichung, Flächen) stehen mit Kontrast zum Hintergrund im
        Palettenobjekt (advisory), in Block C und F der Seite und in den Paaren des Prompts."""
        from pages import task as P
        from web.copy import charts as copy_charts, core as copy_core
        for kw in ({"t": "seq", "fam": "viridis", "n": 5}, {"t": "div", "n": 7, "bg": "dark"}, {"mark": "areas", "fam": "tol-bright", "bg": "dark", "n": 3},
                   {"t": "seq", "fam": "cb-blues", "n": 9}):
            pal = build(**kw)
            pal.update({"preset": None, "name_de": "Eigene Farbe", "name_en": "Your color"})
            r = pal["roles"]["default"]
            data = [k for k in r if k.startswith(("series-", "step-"))]
            checked = {p["fg"] for p in pal["pairs"]} | {p["fg"] for p in pal["advisory"]}
            for lang in ("de", "en"):
                R = {"lang": lang, "T": copy_core.COPY[lang]["frame"], "tc": copy_charts.COPY[lang]["charts"], "task": TASK,
                     "refs": C.reference_values(), "date": "2026-10-11", "sources": {}, "rules": [], "comparisons": []}
                chk, roles = P.check(R, pal), P.roles(R, pal)
                agent = X.render("agent", pal, TASK, export_ctx(pal, lang), lang, {}, G)[0]["text"]
                part = agent.split(copy_core.COPY[lang]["export"]["h_pairs"])[1].split(copy_core.COPY[lang]["export"]["h_rules"])[0]
                with self.subTest(lang=lang, **kw):
                    self.assertEqual(set(data) - checked, set(), "jede Datenfarbe mit Wert")
                    for k in data:
                        tag = f'data-a="{r[k]}" data-b="{r["bg"]}"'
                        self.assertIn(tag, chk, f"Block F ohne {k}")
                        self.assertIn(tag, roles, f"Block C ohne {k}")
                        cn = X.css_name(next(x for x in TASK["roles"] if x["id"] == k))
                        self.assertRegex(part, re.escape(cn) + "/chart-bg " + re.escape(C.fmt_ratio(C.contrast(r[k], r["bg"]), lang, 3.0)[:-2]))

    def test_input_not_mutated(self):
        inp = {"seed": "#F2A900", "colors": None, "options": opts(t="div", fam="seed", n=7)}
        before = copy.deepcopy(inp)
        G.build(TASK, inp, CTX)
        self.assertEqual(inp, before)


if __name__ == "__main__":
    unittest.main()
