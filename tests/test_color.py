"""Tests für den Farbkern tools/color.py: alle Testvektoren aus data/testvectors.json, Formatierer,
Löser, pick_distinct, Simulation, Graustufen, Parser, Paarbewertung, Platzhalter, Daten des Farbkerns
und der Grep-Test gegen Rundungsfunktionen."""
import json, math, random, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C  # noqa: E402

TV = json.loads((ROOT / "data" / "testvectors.json").read_text(encoding="utf-8"))
UNCHECKED_KINDS = {"lab_d50", "lch_d50", "xyz_d50"}


def jload(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ---- gemeinsamer Vektor-Runner (gleiche Semantik wie tests/color.test.cjs)

def resolve(a):
    if isinstance(a, dict):
        if "$oklch" in a:
            v = C.hex_to_oklch(a["$oklch"])[a["i"]]
            for m in a.get("mul", []):
                v = v * m
            return v
        if "$oklch_hex" in a:
            return C.oklch_to_hex(*resolve(a["$oklch_hex"]))
        if "$solve_hex" in a:
            return C.solve_l(*resolve(a["$solve_hex"]))["hex"]
        if "$min_contrast" in a:
            return [x for x in a["$min_contrast"] if C.contrast(x, a["bg"]) >= a["min"]]
        if "$mix" in a:
            s, p, al = a["$mix"]
            sv, pv = C.hex_to_srgb(s), C.hex_to_srgb(p)
            return [al * sv[i] + (1 - al) * pv[i] for i in range(3)]
        raise ValueError(f"unbekanntes Makro {a}")
    if isinstance(a, list):
        return [resolve(x) for x in a]
    return a


def call(fn, args):
    if fn == "len":
        return len(args[0])
    if fn == "identity":
        return args[0]
    return getattr(C, fn)(*args)


def same(v, e, tol=0.0):
    if e is None:
        return v is None or (isinstance(v, float) and v != v)
    if isinstance(e, bool):
        return v is e
    if isinstance(e, str):
        return v == e
    if isinstance(e, (int, float)):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - e) <= tol
    if isinstance(e, list):
        return isinstance(v, list) and len(v) == len(e) and all(same(x, y, tol) for x, y in zip(v, e))
    raise ValueError(f"unbekannte Erwartung {e!r}")


def run_case(case):
    value = call(case["fn"], resolve(case["args"]))
    for p in case.get("pick", []):
        value = value[p]
    if "fields" in case:
        value = [value[f] for f in case["fields"]]
    if "format" in case:
        value = call(case["format"][0], [value] + case["format"][1:])
    return value


class TestVectors(unittest.TestCase):
    def test_srgb_oklch(self):
        sec = TV["srgb_oklch"]
        tol = sec["tol"]
        self.assertEqual(len(sec["vectors"]), 18)
        checked = unchecked = 0
        for vec in sec["vectors"]:
            inp = vec["input"]
            kind, val = next(iter(inp.items()))
            lch_in = srgb = lab = None
            if kind == "hex":
                srgb = C.hex_to_srgb(val)
            elif kind == "css":
                srgb = C.parse(val)["srgb"]
            elif kind == "srgb":
                srgb = val
            elif kind == "oklch":
                lch_in = val
                lab = C.oklch_to_oklab(val)
                srgb = C.oklab_to_srgb(lab)
            elif kind == "p3":
                srgb, lab = C.p3_to_srgb(val), C.p3_to_oklab(val)
            elif kind == "xyz":
                lab = C.xyz_to_oklab(val)
            if lab is None and srgb is not None:
                lab = C.srgb_to_oklab(srgb)
            for e in vec["expect"]:
                with self.subTest(id=vec["id"], kind=e["as"]):
                    if e.get("checked") is False:
                        self.assertIn(e["as"], UNCHECKED_KINDS)
                        unchecked += 1
                        continue
                    checked += 1
                    t = e.get("tol", 0.0005)
                    if e["as"] == "oklch":
                        self.assert_lch(C.oklab_to_oklch(lab), e["value"], tol)
                    elif e["as"] == "hex":
                        got = C.oklch_to_hex(*lch_in) if lch_in else C.srgb_to_hex(srgb)
                        self.assertEqual(got, e["value"])
                    elif e["as"] == "srgb":
                        self.assertTrue(same(srgb, e["value"], t), (srgb, e["value"]))
                    elif e["as"] == "srgb_linear":
                        self.assertTrue(same([C.lin(x) for x in srgb], e["value"], t))
                    elif e["as"] == "xyz_d65":
                        self.assertTrue(same(C.srgb_to_xyz(srgb), e["value"], t))
                    elif e["as"] == "p3":
                        self.assert_lch(C.oklab_to_oklch(C.p3_to_oklab(e["value"])), lch_in, tol)
                    else:
                        self.fail(f"unbekannte Erwartung {e['as']}")
        self.assertEqual((checked, unchecked), (16, 8), "geprüfte und dokumentiert ungeprüfte Teilerwartungen")

    def assert_lch(self, got, exp, tol):
        self.assertLessEqual(abs(got[0] - exp[0]), tol["L"], (got, exp))
        self.assertLessEqual(abs(got[1] - exp[1]), tol["C"], (got, exp))
        if exp[1] > tol["h_min_c"]:
            d = abs(got[2] - exp[2]) % 360
            self.assertLessEqual(min(d, 360 - d), tol["h"], (got, exp))

    def test_ottosson(self):
        sec = TV["ottosson"]
        for vec in sec["vectors"]:
            with self.subTest(xyz=vec["xyz"]):
                self.assertTrue(same(C.xyz_to_oklab(vec["xyz"]), vec["oklab"], sec["tol"]))

    def test_wcag(self):
        sec = TV["wcag"]
        for vec in sec["vectors"]:
            with self.subTest(a=vec["a"]):
                self.assertAlmostEqual(C.contrast(vec["a"], vec["b"]), vec["expect"], delta=sec["tol"])
                self.assertEqual(C.contrast(vec["a"], vec["b"]), C.contrast(vec["b"], vec["a"]))

    def test_gamut(self):
        sec = TV["gamut"]
        for vec in sec["vectors"]:
            with self.subTest(id=vec["id"]):
                if vec["fn"] == "oklab_to_srgb_of_oklch":
                    got = C.oklab_to_srgb(C.oklch_to_oklab(vec["input"]))
                elif vec["fn"] == "gamut_map_p3":
                    got = C.gamut_map(*C.oklab_to_oklch(C.p3_to_oklab(vec["input"])))
                else:
                    got = C.gamut_map(*vec["input"])
                self.assertTrue(same(got, vec["expect"], sec["tol"]), (got, vec["expect"]))
                if "hex" in vec:
                    self.assertEqual(C.srgb_to_hex(got), vec["hex"])
                    self.assertTrue(all(0 <= x <= 1 for x in got))

    def test_cvd_display(self):
        for vec in TV["cvd_display"]["vectors"]:
            for kind in ("protan", "deutan", "tritan"):
                with self.subTest(hex=vec["in"], kind=kind):
                    self.assertEqual(C.sim_hex(vec["in"], kind), vec[kind])

    def test_parser(self):
        vecs = TV["parser"]["vectors"]
        self.assertGreaterEqual(len(vecs), 30)
        for vec in vecs:
            with self.subTest(s=vec["in"]):
                bare = vec.get("bare", True)
                r = C.parse(vec["in"], bare)
                if "error" in vec:
                    self.assertIsNone(r)
                    self.assertEqual(C.parse_error(vec["in"], bare), vec["error"])
                    continue
                self.assertIsNotNone(r, C.parse_error(vec["in"], bare))
                self.assertIsNone(C.parse_error(vec["in"], bare))
                self.assertEqual(r["hex"], vec["hex"])
                self.assertAlmostEqual(r["alpha"], vec.get("alpha", 1.0), delta=1e-12)
                if "oog" in vec:
                    self.assertIs(r["out_of_gamut"], vec["oog"])
                if r["out_of_gamut"]:
                    self.assertGreater(r["mapped_distance"], 0)
                else:
                    self.assertIsNone(r["mapped_distance"])
                self.assertTrue(all(0 <= x <= 1 for x in r["srgb"]))
                self.assertEqual(C.srgb_to_hex(r["srgb"]), r["hex"])

    def test_format(self):
        for vec in TV["format"]["vectors"]:
            with self.subTest(fn=vec["fn"], args=vec["args"]):
                self.assertEqual(call(vec["fn"], vec["args"]), vec["expect"])

    def test_cases(self):
        for case in TV["cases"]["vectors"]:
            with self.subTest(id=case["id"]):
                if "raises" in case:
                    with self.assertRaises(getattr(C, case["raises"])) as cm:
                        run_case(case)
                    self.assertEqual(cm.exception.key, case["key"])
                    continue
                got = run_case(case)
                self.assertTrue(same(got, case["expect"], case.get("tol", 0.0)), (got, case["expect"]))

    def test_placeholders(self):
        for vec in TV["placeholders"]["vectors"]:
            with self.subTest(t=vec["template"], lang=vec["lang"]):
                html, tags = C.render_text(vec["template"], {}, vec["lang"])
                self.assertEqual(len(tags), 1)
                self.assertEqual(tags[0]["text"], vec["text"])
                self.assertTrue(html.startswith('<data class="num" ') and html.endswith(">" + vec["text"] + "</data>"), html)
                attrs = dict(re.findall(r' (data-[a-z]+|value)="([^"]*)"', html))
                self.assertEqual(C.data_tag_text(attrs, vec["lang"]), vec["text"])


# ---- Formatierer

class TestFormat(unittest.TestCase):
    def test_pct_roundtrip(self):
        for p in range(101):
            self.assertEqual(C.fmt_pct_up(p / 100, "en"), f"{p}%")
            self.assertEqual(C.fmt_pct_up(p / 100, "de"), f"{p}\u202f%")

    def test_ratio_never_rounds_up(self):
        rng = random.Random(7)
        for _ in range(2000):
            x = 1 + rng.random() * 20
            s = C.fmt_ratio(x, "en")
            self.assertLessEqual(float(s[:-2]), x + 1e-9)
            self.assertLess(x - float(s[:-2]), 0.01 + 1e-9)
        for t in (3.0, 4.5, 7.0, 4.95, 3.3):
            self.assertLess(float(C.fmt_ratio(t - 1e-12, "en", t)[:-2]), t)

    def test_dist_and_L(self):
        self.assertEqual(C.fmt_dist(2.0, "de"), "2,0")
        self.assertEqual(C.fmt_dist(1.95, "de"), "1,9")
        self.assertEqual(C.fmt_L(0.4515, "en"), "0.452")

    def test_errors(self):
        for fn in (C.fmt_ratio, C.fmt_dist, C.fmt_pct_up, C.fmt_L):
            with self.assertRaises(ValueError):
                fn(float("nan"), "de")
            with self.assertRaises(ValueError):
                fn(1.0, "fr")
        with self.assertRaises(ValueError):
            C.fmt_count(1.5, "de")
        with self.assertRaises(ValueError):
            C.quantize(float("nan"))


# ---- Löser, Auswahl, Simulation, Graustufen

class TestSolver(unittest.TestCase):
    def test_results_pass_after_quantization(self):
        rng = random.Random(11)
        n_ok = n_err = 0
        for _ in range(150):
            C0, h = rng.random() * 0.25, rng.random() * 360
            light = rng.random() < 0.5
            target = rng.choice((3.0, 4.5, 4.95, 7.0))
            against = ["#FFFFFF", "#F8FBFB"] if light else ["#101516", "#16191D"]
            L0 = 0.4 + rng.random() * 0.3
            try:
                r = C.solve_l(C0, h, against, target, -1 if light else 1, L0)
            except C.SolveError as e:
                self.assertEqual(e.key, "unreachable")
                n_err += 1
                continue
            n_ok += 1
            self.assertGreaterEqual(min(C.contrast(r["hex"], b) for b in against), target)
            self.assertEqual(r["hex"], C.oklch_to_hex(r["L"], r["C"], h))
            self.assertAlmostEqual(r["ratio"], min(C.contrast(r["hex"], b) for b in against), delta=1e-12)
            if r["changed"]:
                self.assertGreater(r["distance"], 0)
            else:
                self.assertEqual(r["L"], L0)
        self.assertGreater(n_ok, 100)

    def test_direction_checked(self):
        with self.assertRaises(ValueError):
            C.solve_l(0.1, 10, ["#FFFFFF"], 4.5, 0, 0.5)
        with self.assertRaises(C.SolveError) as cm:
            C.solve_l(0.1, 200, ["#FFFFFF"], 4.5, 1, 0.6)
        self.assertEqual(cm.exception.key, "mixed-sides")


class TestPickDistinct(unittest.TestCase):
    OKABE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

    def test_deterministic_prefix(self):
        full = C.pick_distinct(self.OKABE, 7, bg="#16191D")
        self.assertEqual(full, C.pick_distinct(self.OKABE, 7, bg="#16191D"))
        for k in range(1, 8):
            self.assertEqual(C.pick_distinct(self.OKABE, k, bg="#16191D"), full[:k])
        self.assertEqual(sorted(full), sorted(self.OKABE))

    def test_start_and_rules(self):
        r = C.pick_distinct(self.OKABE, 3, start="#11697a")
        self.assertEqual(r[0], "#11697A")
        self.assertEqual(len(r), 3)
        self.assertEqual(C.pick_distinct(self.OKABE[:2], 5), self.OKABE[:2])
        with self.assertRaises(ValueError):
            C.pick_distinct(self.OKABE, 3, kinds=("normal", "tritan"))


class TestSimulation(unittest.TestCase):
    def sample(self):
        rng = random.Random(3)
        return ["#%02X%02X%02X" % (rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(300)]

    def test_invariants(self):
        for kind in C.KINDS:
            self.assertEqual(C.sim_hex("#FFFFFF", kind), "#FFFFFF")
            self.assertEqual(C.sim_hex("#000000", kind), "#000000")
        for h in self.sample():
            for kind in ("protan", "deutan"):
                hx = C.sim_hex(h, kind)
                self.assertEqual(hx[1:3], hx[3:5], (h, kind, hx))
                lab = C.sim_oklab(h, kind)
                self.assertEqual(len(lab), 3)
            self.assertEqual(C.distance(h, h, "deutan"), 0)
        with self.assertRaises(ValueError):
            C.sim_hex("#123456", "achromat")

    def test_gray_faithful(self):
        for h in self.sample()[:100]:
            y = C.rel_lum(h)
            self.assertAlmostEqual(C.rel_lum([C.gam(y)] * 3), y, delta=1e-12)
            g = C.gray_hex(h)
            self.assertTrue(g[1:3] == g[3:5] == g[5:7])
        self.assertAlmostEqual(C.distance("#0000FF", "#FFFF00", "gray"), C.gray_distance("#0000FF", "#FFFF00"), delta=1e-12)
        self.assertAlmostEqual(C.gray_value("#808080"), C.hex_to_oklch("#808080")[0], delta=1e-12)

    def test_worst_and_min_distance(self):
        a, b = "#009E73", "#CC79A7"
        self.assertEqual(C.worst_distance(a, b), min(C.distance(a, b, k) for k in ("normal", "deutan", "protan")))
        self.assertIsNone(C.min_distance(["#000000"]))
        md = C.min_distance(["#009E73", "#CC79A7", "#FFFFFF"])
        self.assertEqual((md["i"], md["j"], md["kind"]), (0, 1, "deutan"))


class TestConversions(unittest.TestCase):
    def test_roundtrip_and_luminance_row(self):
        rng = random.Random(5)
        for _ in range(500):
            rgb = [rng.random() for _ in range(3)]
            back = C.oklab_to_srgb(C.srgb_to_oklab(rgb))
            self.assertTrue(same(back, rgb, 1e-12))
        self.assertTrue(same(C.SRGB_XYZ[1], [0.2126, 0.7152, 0.0722], 0.0001))

    def test_powerless_and_hue_range(self):
        self.assertIsNone(C.hex_to_oklch("#808080")[2])
        self.assertIsNone(C.hex_to_oklch("#FFFFFF")[2])
        for h in ("#FF0000", "#00FF00", "#0000FF", "#FF00FF"):
            self.assertTrue(0 <= C.hex_to_oklch(h)[2] < 360)

    def test_in_gamut_unchanged(self):
        for h in ("#11697A", "#000000", "#FFFFFF", "#E63946"):
            self.assertEqual(C.oklch_to_hex(*C.hex_to_oklch(h)), h)

    def test_composite(self):
        self.assertEqual(C.composite("#000000", 0.5, "#FFFFFF"), "#808080")
        self.assertEqual(C.composite("#11697A", 1.0, "#FFFFFF"), "#11697A")
        self.assertEqual(C.composite("#11697A", 0.0), "#FFFFFF")

    def test_shortest_roundtrip(self):
        rng = random.Random(9)
        for _ in range(300):
            h = "#%02X%02X%02X" % (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            s = C.shortest_oklch(h)
            self.assertIsNotNone(s, h)
            self.assertEqual(C.parse(s)["hex"], h)


# ---- Paarbewertung und Platzhalter

TASK = {"id": "probe", "modes": ["light", "dark"],
        "pairs": [{"fg": "text", "on": ["bg", "surface"], "min": 4.5, "criterion": "1.4.3", "rule": "text-contrast"}],
        "decorative": [{"fg": "border", "on": ["bg"]}],
        "advisory": [{"fg": "accent", "on": ["bg"], "min": 3.0, "finding": "accent-fill-low"}]}
ROLES = {"light": {"bg": "#F8FBFB", "surface": "#FFFFFF", "text": "#182123", "border": "#D2D9DB", "accent": "#11697A"},
         "dark": {"bg": "#101516", "surface": "#161C1D", "text": "#E8ECED", "border": "#2C3436", "accent": "#276876"}}


class TestEvaluate(unittest.TestCase):
    def test_pairs(self):
        r = C.evaluate(TASK, ROLES)
        self.assertEqual(len(r["pairs"]), 4)
        self.assertEqual([p["mode"] for p in r["pairs"]], ["light", "light", "dark", "dark"])
        p0 = r["pairs"][0]
        self.assertEqual((p0["fg"], p0["bg"], p0["min"], p0["criterion"], p0["rule"]), ("text", "bg", 4.5, "1.4.3", "text-contrast"))
        self.assertEqual(p0["ratio"], C.contrast("#182123", "#F8FBFB"))
        self.assertIs(p0["pass"], True)
        self.assertEqual(len(r["decorative"]), 2)
        self.assertNotIn("pass", r["decorative"][0])
        adv = r["advisory"]
        self.assertEqual(adv[1]["finding"], "accent-fill-low")
        self.assertIs(adv[1]["pass"], C.contrast("#276876", "#101516") >= 3.0)

    def test_missing(self):
        roles = {"light": dict(ROLES["light"]), "dark": dict(ROLES["dark"])}
        del roles["dark"]["surface"]
        with self.assertRaises(ValueError):
            C.evaluate(TASK, roles)
        self.assertEqual(len(C.evaluate(TASK, roles, missing="skip")["pairs"]), 3)
        with self.assertRaises(ValueError):
            C.evaluate(TASK, {"light": ROLES["light"]})


class TestRenderText(unittest.TestCase):
    CTX = {"roles": ROLES, "counts": {"pairs": 1234}, "date": "2026-10-11"}

    def test_roles_modes_and_tags(self):
        tpl = ("Link {cr:accent/text@light} und {cr:accent/text@dark}, {hex:accent@dark}, {dist:accent/text/deutan@light}, "
               "{gs:accent/bg@light}, {gray:accent@light}, {proj:text/bg/normal@light}, {count:pairs} Paare, Stand {date}.")
        html, tags = C.render_text(tpl, self.CTX, "de")
        self.assertIn(C.fmt_ratio(C.contrast("#11697A", "#182123"), "de"), html)
        self.assertIn('<data class="hex" value="#276876"><code>#276876</code></data>', html)
        self.assertIn('<data class="count" value="1234">1.234</data>', html)
        self.assertIn('<data class="date" value="2026-10-11">11. Oktober 2026</data>', html)
        nums = [t for t in tags if t["m"] not in ("hex", "count", "date")]
        self.assertEqual(len(nums), 6)
        for t in nums:
            attrs = {"data-m": t["m"], "data-a": t["a"], "data-b": t["b"], "data-k": t["k"], "data-t": t["t"], "data-id": t["id"]}
            self.assertEqual(C.data_tag_text(attrs, "de"), t["text"])
        en, _ = C.render_text("{date}", self.CTX, "en")
        self.assertEqual(en, '<data class="date" value="2026-10-11">October 11, 2026</data>')

    def test_escaping_and_errors(self):
        html, _ = C.render_text("a < b & {cr:#000000/#FFFFFF}", {}, "en")
        self.assertTrue(html.startswith("a &lt; b &amp; <data"))
        raw, _ = C.render_text("<b>{cr:#000000/#FFFFFF}</b>", {}, "en", escape=False)
        self.assertTrue(raw.startswith("<b><data"))
        self.assertEqual(C.render_text(":root{--bg: #fff}", {}, "de")[0], ":root{--bg: #fff}")
        for bad in ("{cr:#000000}", "{cr:accent/text}", "{cr:accent/nope@light}", "{dist:#000000/#FFFFFF/achromat}",
                    "{scrim:#777777/#777777/4.5}", "{ref:unknown}", "{count:x}", "{date}", "{cr:#00000/#FFFFFF}"):
            with self.subTest(bad=bad), self.assertRaises(C.RenderError):
                C.render_text(bad, {"roles": ROLES}, "de")
        self.assertEqual(C.find_placeholders("x {cr:a/b@light} {date}"), [("cr", "a/b@light"), ("date", None)])


# ---- Daten des Farbkerns

FORBIDDEN = {"contrast", "ratio", "kontrast", "delta", "distance", "abstand", "result", "ergebnis", "pass", "cr"}


def all_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from all_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from all_keys(v)


class TestData(unittest.TestCase):
    def test_css_names(self):
        names = {k: v for k, v in jload("data/css-names.json").items() if not k.startswith("_")}
        self.assertEqual(len(names), 148)
        self.assertEqual(len(set(names.values())), 139)
        for n, v in names.items():
            self.assertRegex(v, r"^#[0-9A-F]{6}$")
            self.assertEqual(C.parse(n)["hex"], v)
            self.assertEqual(C.parse(n.upper())["hex"], v)

    def test_okabe_ito(self):
        d = jload("data/datasets/okabe-ito.json")
        cols = d["schemes"][0]["colors"]
        self.assertEqual(len(cols), 8)
        for col in cols:
            self.assertEqual(col["hex"], "#%02X%02X%02X" % tuple(col["origin"]["rgb"]))
        self.assertRegex(d["machine_sha256"], r"^[0-9a-f]{64}$")
        for key in ("license", "attribution", "source_url", "machine_source", "retrieved", "reliability", "kind"):
            self.assertIn(key, d)

    def test_comparisons_definitions_only(self):
        d = jload("data/comparisons.json")
        self.assertEqual([c["id"] for c in d["comparisons"]], ["okabe-ito-7", "naive-rainbow-7"])
        refs = C.reference_values()
        self.assertEqual(set(refs), {"okabe-ito-7", "naive-rainbow-7"})
        self.assertEqual(len(refs["okabe-ito-7"]["colors"]), 7)

    def test_no_result_keys(self):
        for rel in ("data/color-constants.json", "data/cvd.json", "data/css-names.json", "data/comparisons.json",
                    "data/datasets/okabe-ito.json", "data/testvectors.json"):
            with self.subTest(rel=rel):
                self.assertFalse(FORBIDDEN & set(all_keys(jload(rel))))

    def test_constants_shape(self):
        k = C.K
        for key in ("srgb_to_xyz", "xyz_to_srgb", "p3_to_xyz"):
            self.assertTrue(all(len(row) == 3 and all(len(p) == 2 and p[1] > 0 for p in row) for row in k[key]))
        for key in ("xyz_to_lms", "lms_to_oklab", "lms_to_xyz", "oklab_to_lms"):
            self.assertTrue(all(len(row) == 3 for row in k[key]) and len(k[key]) == 3)
        self.assertEqual(k["version"], "CSS Color 4, CRD 2026-10-09")
        self.assertEqual(C.ambient_ratio("normal"), 0.2)

    def test_parity_seeds(self):
        d = jload("tests/parity_seeds.json")
        self.assertEqual(len(d["seeds"]), 60)
        grid = [f"oklch({L} {Cc} {h})" for L in d["L"] for Cc in d["C"] for h in d["h"]]
        self.assertEqual(d["seeds"], grid)
        self.assertEqual((d["L"], d["C"], d["h"]), ([0.3, 0.5, 0.7], [0.03, 0.08, 0.15, 0.22], [0, 72, 144, 216, 288]))
        for s in d["seeds"]:
            self.assertIsNotNone(C.parse(s), s)


# ---- API des Farbkerns

API = ["parse", "lin", "gam", "hex_to_srgb", "srgb_to_hex", "quantize", "srgb_to_oklab", "oklab_to_srgb", "oklab_to_oklch",
          "oklch_to_oklab", "p3_to_srgb", "gamut_map", "oklch_to_hex", "hex_to_oklch", "rel_lum", "contrast", "gray_value",
          "gray_hex", "gray_distance", "sim_oklab", "sim_hex", "distance", "worst_distance", "min_distance", "fmt_ratio",
          "fmt_dist", "fmt_pct_up", "fmt_L", "fmt_count", "fmt_lum", "shortest_oklch", "solve_l", "SolveError", "pick_distinct",
          "link_window", "projected_contrast", "projector_hex", "scrim_alpha", "evaluate", "render_text", "reference_values"]


class TestApi(unittest.TestCase):
    def test_complete(self):
        for name in API:
            self.assertTrue(callable(getattr(C, name, None)), name)
        self.assertEqual(C.JND_DISTANCE, 2.0)


# ---- Grep-Test

class TestNoRounding(unittest.TestCase):
    def test_python_files(self):
        files = [ROOT / "tools" / "color.py", ROOT / "tools" / "export.py"] + sorted((ROOT / "tools" / "gen").glob("*.py"))
        self.assertTrue(files[0].exists())
        for f in files:
            if f.exists():
                with self.subTest(file=f.name):
                    self.assertNotIn("round(", f.read_text(encoding="utf-8"))

    def test_js_files(self):
        files = [ROOT / "web" / "color.js", ROOT / "web" / "export.js"] + sorted((ROOT / "web" / "gen").glob("*.js"))
        self.assertTrue(files[0].exists())
        for f in files:
            if not f.exists():
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(file=f.name, line=n):
                    self.assertNotIn("toFixed(", line)
                    if "Math.round(" in line:
                        self.assertIn("// quantize", line)


if __name__ == "__main__":
    unittest.main()
