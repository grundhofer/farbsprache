"""Startpaletten (Spezifikation 6.4, 7.9): je Aufgabe Gleichheit mit tests/golden/<aufgabe>.json, kein
normatives Paar verfehlt, expect in beide Richtungen. Läuft über alle vorhandenen Aufgaben und die
Testaufgabe aus tests/fixtures/. Golden neu schreiben nur bewusst: python3 build.py --update-golden."""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

DATE = "2026-10-11"


def sites():
    out = []
    for roots, seg in (([build.ROOT], None), ([build.ROOT, build.FIXTURES], build.FIXTURE_SEG)):
        site = build.Site(roots, build.ROOT / "tests" / "out" / "unused", DATE, allow_missing=True, seg=seg)
        site.prepare()
        out.append(site)
    return out


class TestPresets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.sites = sites()
            cls.error = None
        except build.BuildError as e:
            cls.sites, cls.error = [], e.errors

    def test_build_prepares(self):
        self.assertIsNone(self.error, "\n".join(self.error or []))
        tasks = [t["id"] for s in self.sites for t in s.tasks]
        self.assertIn("fixture", tasks)

    def test_golden(self):
        for site in self.sites:
            for t in site.tasks:
                with self.subTest(task=t["id"]):
                    f = site.golden_path(t["id"])
                    self.assertTrue(f.exists(), f"{f.relative_to(ROOT)} fehlt (python3 build.py --update-golden)")
                    self.assertEqual(json.loads(f.read_text(encoding="utf-8")), site.golden(t["id"]))

    def test_no_normative_failure_and_expect(self):
        for site in self.sites:
            for t in site.tasks:
                for p in t["presets"]:
                    pal = site.palettes[t["id"]][p["id"]]
                    with self.subTest(task=t["id"], preset=p["id"]):
                        bad = [f"{x['fg']}/{x['bg']} ({x['mode']})" for x in pal["pairs"] if not x["pass"] or x["ratio"] < x["min"]]
                        self.assertEqual(bad, [])
                        got = {f["id"] + ("@" + f["mode"] if f.get("mode") else "") for f in pal["findings"]}
                        self.assertEqual(got, set(p["expect"]))

    def test_validation_catches_drift(self):
        """Der Rahmen erkennt eine verfehlte Norm, falsche Kontrastwerte und expect in beide Richtungen."""
        site = self.sites[-1]
        t = site.task_by_id["fixture"]
        p = t["presets"][0]
        pal = json.loads(json.dumps(site.palettes["fixture"][p["id"]]))
        pal["pairs"][0]["pass"] = False
        pal["pairs"][1]["ratio"] += 0.01
        pal["findings"].append({"id": "neu", "mode": "light", "severity": "note", "values": {}})
        errs = build.validate_palette(site, t, dict(p, expect=p["expect"] + ["fehlt@dark"]), pal, "Startpalette petrol (fixture)")
        text = "\n".join(errs)
        self.assertIn("Startpalette petrol (fixture, hell): text/bg", text)
        self.assertIn("ratio passt nicht zum Hex", text)
        self.assertIn("Hinweis neu@light berechnet, steht aber nicht in expect", text)
        self.assertIn("expect nennt fehlt@dark, berechnet wurde es nicht", text)


if __name__ == "__main__":
    unittest.main()
