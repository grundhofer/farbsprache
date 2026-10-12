"""Datensätze Paul Tol, ColorBrewer, viridis (Spezifikation 6.8, 9.4, Abnahme P2).
Schema 6.8 je Datei, Spot-Checks gegen die Primärdateien (Werte aus tol_colors.py, colorbrewer.json und colormaps.py,
abgerufen am 2026-10-11; die Prüfsummen der gelesenen Dateien stehen in machine_sha256), Pflichtsatz wörtlich und
das Importskript tools/datasets.py auf kleinen Beispielen der Quellformate (ohne Netz).
Den vollständigen Abgleich mit den Primärdateien macht python3 -I tools/datasets.py … --check (nicht in der CI)."""
import json, math, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import datasets as D  # noqa: E402

CB_NOTICE = "This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/)."
SHA = {"tol": "149ca0aa2e7936a866a25444c70598cf160dabd94d26eecfc4b4005e3e83cb90",
       "colorbrewer": "729cb527c1edcf3267c4521df29ede5092f3e6171c5a259e2ebdd252335840b9",
       "viridis": "b7478d10e2ccfdb22128867e137f16f55b687e9c225065e91bcbd6bb9e6c0352"}
REQUIRED = ("id", "name", "authors", "year", "source_url", "machine_source", "machine_sha256", "retrieved", "license",
            "license_note_de", "license_note_en", "attribution", "required_notice", "reliability", "kind", "schemes")


def load(name):
    return json.loads((ROOT / "data" / "datasets" / f"{name}.json").read_text(encoding="utf-8"))


class TestSchema(unittest.TestCase):
    def test_fields_6_8(self):
        for name in ("tol", "colorbrewer", "viridis"):
            ds = load(name)
            with self.subTest(ds=name):
                for k in REQUIRED:
                    self.assertIn(k, ds)
                self.assertEqual(ds["id"], name)
                self.assertTrue(ds["source_url"].startswith("https://") and ds["machine_source"].startswith("https://"))
                self.assertEqual(ds["machine_sha256"], SHA[name])
                self.assertRegex(ds["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIn(ds["reliability"], ("defined", "computed", "measured", "consensus"))
                self.assertIn(ds["kind"], ("categorical", "sequential", "diverging", "mixed"))
                for path in re.findall(r'"hex": "([^"]*)"', json.dumps(ds)):
                    self.assertRegex(path, r"^#[0-9A-F]{6}$")
        self.assertEqual(load("tol")["license"], "BSD-3-Clause")
        self.assertEqual(load("colorbrewer")["license"], "Apache-2.0")
        self.assertEqual(load("viridis")["license"], "CC0-1.0")

    def test_colorbrewer_notice_and_flags(self):
        ds = load("colorbrewer")
        self.assertEqual(ds["required_notice"], CB_NOTICE)
        self.assertEqual([s["id"] for s in ds["schemes"]], ["blues", "rdbu", "puor"], "nur Blues, RdBu, PuOr (9.4)")
        self.assertEqual([s["kind"] for s in ds["schemes"]], ["sequential", "diverging", "diverging"])
        self.assertEqual(ds["kind"], "mixed", "verschiedene Arten je Palette, oben deshalb mixed")
        for s in ds["schemes"]:
            self.assertEqual(set(s), {"id", "name", "kind", "classes", "flags_quoted"})
            want = [str(n) for n in range(3, 10 if s["id"] == "blues" else 12)]
            self.assertEqual(list(s["classes"]), want, "alle Klassenstufen")
            for c, cols in s["classes"].items():
                self.assertEqual(len(cols), int(c))
                for col in cols:
                    self.assertEqual(col["hex"], "#%02X%02X%02X" % tuple(col["origin"]["rgb"]))
            self.assertEqual(set(s["flags_quoted"]), {"blind", "print", "copy"})
            for k, v in s["flags_quoted"].items():
                self.assertEqual(list(v), want)
                self.assertTrue(set(v.values()) <= {0, 1, 2})
        self.assertIn("colorbrewer2.org", ds["flags_note_de"] + ds["flags_note_en"])

    def test_tol_and_viridis_origin(self):
        for s in load("tol")["schemes"]:
            self.assertFalse(s["interpolate"])
            for c in s["colors"]:
                self.assertEqual(c["hex"], c["origin"]["hex"].upper())
        cols = load("viridis")["schemes"][0]["colors"]
        self.assertEqual(len(cols), 256)
        for c in cols:
            q = [int(math.floor(min(max(x, 0.0), 1.0) * 255 + 0.5)) for x in c["origin"]["srgb"]]
            self.assertEqual(c["hex"], "#%02X%02X%02X" % tuple(q))


class TestSpotChecks(unittest.TestCase):
    """Werte, die beim Import am 2026-10-11 in den Primärdateien selbst nachgelesen wurden."""

    def test_tol(self):
        s = {x["id"]: x for x in load("tol")["schemes"]}
        self.assertEqual([c["hex"] for c in s["bright"]["colors"]], ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"])
        self.assertEqual([c["name"] for c in s["bright"]["colors"]], ["blue", "red", "green", "yellow", "cyan", "purple", "grey"])
        self.assertEqual([c["hex"] for c in s["muted"]["colors"]],
                         ["#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE", "#882255", "#44AA99", "#999933", "#AA4499"])
        self.assertEqual(load("tol")["required_notice"], "Copyright (c) 2022, Paul Tol. All rights reserved.")

    def test_colorbrewer(self):
        s = {x["id"]: x for x in load("colorbrewer")["schemes"]}
        hx = lambda sid, n: [c["hex"] for c in s[sid]["classes"][str(n)]]
        self.assertEqual(hx("blues", 5), ["#EFF3FF", "#BDD7E7", "#6BAED6", "#3182BD", "#08519C"])
        self.assertEqual(hx("blues", 9)[-1], "#08306B")
        self.assertEqual(hx("rdbu", 5), ["#CA0020", "#F4A582", "#F7F7F7", "#92C5DE", "#0571B0"])
        self.assertEqual(hx("puor", 5), ["#E66101", "#FDB863", "#F7F7F7", "#B2ABD2", "#5E3C99"])
        self.assertEqual(s["blues"]["flags_quoted"]["copy"]["3"], 1)
        self.assertEqual(s["rdbu"]["flags_quoted"]["copy"]["3"], 0)
        self.assertEqual(s["puor"]["flags_quoted"]["print"]["5"], 2)

    def test_viridis(self):
        cols = [c["hex"] for c in load("viridis")["schemes"][0]["colors"]]
        self.assertEqual((cols[0], cols[255]), ("#440154", "#FDE725"))
        self.assertEqual(load("viridis")["schemes"][0]["colors"][0]["origin"]["srgb"], [0.267004, 0.004874, 0.329415])
        self.assertEqual(load("viridis")["schemes"][0]["colors"][255]["origin"]["srgb"], [0.993248, 0.906157, 0.143936])


class TestImportScript(unittest.TestCase):
    """tools/datasets.py liest die Quellformate als Text; hier mit gekürzten Beispielen im gleichen Format."""

    def test_parse_tol(self):
        src = ('"""\nCopyright (c) 2022, Paul Tol\nAll rights reserved.\n\nLicense:  Standard 3-clause BSD\n"""\n__version__ = "2022.10"\n'
               "    if colorset == 'bright':\n        cset = namedtuple('Bcset',\n                    'blue red black')\n"
               "        return cset('#4477AA', '#EE6677',\n                    '#000000')\n"
               "    if colorset == 'muted':\n        cset = namedtuple('Mcset',\n                    'rose pale_grey black')\n"
               "        return cset('#CC6677', '#DDDDDD', '#000000')\n")
        sets, year, version = D.parse_tol(src)
        self.assertEqual(sets["bright"], [("blue", "#4477AA"), ("red", "#EE6677")])
        self.assertEqual(sets["muted"], [("rose", "#CC6677")])
        self.assertEqual((year, version), (2022, "2022.10"))

    def test_parse_colorbrewer_flags_and_notice(self):
        line = ("Blues:  {3: ['rgb(222,235,247)', 'rgb(158,202,225)', 'rgb(49,130,189)'], 4: ['rgb(239,243,255)', 'rgb(189,215,231)', "
                "'rgb(107,174,214)', 'rgb(33,113,181)'], 'properties':{'type': 'seq','blind':[1],'print':[1,2],'copy':[1,0],'screen':[1,2] } } ,")
        flags, typ, vals = D.parse_cb_flags(line, "Blues", ["3", "4"])
        self.assertEqual(typ, "seq")
        self.assertEqual(flags, {"blind": {"3": 1, "4": 1}, "print": {"3": 1, "4": 2}, "copy": {"3": 1, "4": 0}})
        self.assertEqual(vals["3"], [[222, 235, 247], [158, 202, 225], [49, 130, 189]])
        lic = ('2. The end-user documentation ... must\ninclude the following acknowledgment: "This product includes color\n'
               'specifications and designs developed by Cynthia Brewer\n(http://colorbrewer.org/)." Alternately')
        self.assertEqual(D.parse_notice(lic), CB_NOTICE)

    def test_parse_viridis(self):
        rows = ",\n".join("[%.6f, %.6f, %.6f]" % (i / 255, 0.5, 1 - i / 255) for i in range(256))
        src = "# released under the CC0 license / public domain dedication.\n_magma_data = [[0.1, 0.1, 0.1]]\n_viridis_data = [" + rows + "]\n"
        data = D.parse_viridis(src)
        self.assertEqual(len(data), 256)
        self.assertEqual(data[0], [0.0, 0.5, 1.0])
        self.assertEqual(D.quantize(0.5), 128)
        self.assertEqual(D.hex_of([0, 114, 178]), "#0072B2")

    def test_dumps_one_color_per_line(self):
        text = D.dumps({"a": [{"hex": "#000000", "origin": {"rgb": [0, 0, 0]}}, {"hex": "#FFFFFF", "origin": {"rgb": [255, 255, 255]}}]})
        self.assertEqual(json.loads(text)["a"][1]["hex"], "#FFFFFF")
        self.assertIn('\n    {"hex": "#000000", "origin": {"rgb": [0, 0, 0]}},\n', text)


if __name__ == "__main__":
    unittest.main()
