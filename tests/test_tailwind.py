"""Tailwind-v4-Export: die Prüfung aus tools/tailwind_check.py.

Ohne Pakete läuft nur der Selbsttest der Prüfung: Sie erkennt eine richtige Ausgabe in der Form von Tailwind 4.3.3 und
schlägt bei falschem Wert, fehlender Klasse oder falscher Deklaration an. Mit FARBSPRACHE_TAILWIND=<Pfad zur
Tailwind-4-CLI> kompiliert der Test zusätzlich den Export jeder Startpalette (Opt-in, Anleitung in tools/tailwind_check.py)."""
import os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import tailwind_check as TW  # noqa: E402


def fake_compile(text):
    """So legt Tailwind 4.3.3 den Export ab: Utilities in @layer utilities, :root und @media unverändert danach."""
    names, classes = TW.utilities(text)
    util = "".join(f"  .{c} {{\n    {TW.PROP[c.split('-', 1)[0]]}: var(--{c.split('-', 1)[1]});\n  }}\n" for c in classes)
    body = text.split('@import "tailwindcss";', 1)[1].split("@theme inline {", 1)[0]
    return "@layer theme {\n  :root, :host {\n    --font-sans: x;\n  }\n}\n@layer utilities {\n" + util + "}\n" + body.strip() + "\n"


class TestTailwindCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = TW.cases(("en",))

    def test_all_starter_palettes(self):
        self.assertEqual(len({(c["task"], c["preset"]) for c in self.cases}), 22)
        self.assertTrue(any(c["offered"] for c in self.cases) and any(len(c["modes"]) == 2 for c in self.cases))

    def test_verify_accepts_tailwind_output(self):
        for c in self.cases:
            with self.subTest(case=c["key"]):
                self.assertEqual(TW.verify(c["text"], fake_compile(c["text"]), c["want"], c["modes"]), [])

    def test_verify_catches_errors(self):
        c = next(x for x in self.cases if len(x["modes"]) == 2)
        css = fake_compile(c["text"])
        dark = c["modes"][1]
        name, hx = next(iter(c["want"][dark].items()))
        i = css.index("@media")
        wrong = css[:i] + css[i:].replace(f"--{name}: {hx};", f"--{name}: #000001;", 1)
        self.assertTrue(any(f"{dark}: --{name}" in e for e in TW.verify(c["text"], wrong, c["want"], c["modes"])))
        self.assertTrue(any(e.startswith(".bg-") for e in TW.verify(c["text"], re.sub(r"\n  \.bg-[a-z0-9-]+ \{[^}]*\}", "", css, count=1), c["want"], c["modes"])))
        self.assertTrue(any("color: #" in e for e in TW.verify(c["text"], css.replace("color: var(--", "color: #FFFFFF; x: var(--", 1), c["want"], c["modes"])))

    def test_real_tailwind(self):
        cli = os.environ.get("FARBSPRACHE_TAILWIND")
        if not cli:
            self.skipTest("FARBSPRACHE_TAILWIND nicht gesetzt (Opt-in, siehe tools/tailwind_check.py)")
        log = []
        with TW.tempdir(cli) as tmp:
            bad = TW.run(cli, tmp, TW.cases(), log.append)
        self.assertEqual(bad, 0, "\n".join(x for x in log if "FEHLER" in x or x.startswith("    ")))


if __name__ == "__main__":
    unittest.main()
