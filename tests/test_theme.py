"""Kontraste der Seiten-Tokens (web/theme.py) nach WCAG 2.2 mit dem Farbkern, wie in Bildsprache:
ink, ink-2, ink-3, accent und brass mindestens 4,5:1 auf ground, surface und surface-2;
accent-ink auf accent mindestens 4,5:1; ink auf den Tag-Flächen 4,5:1, ink-3 dort 3:1."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C  # noqa: E402
from web import theme  # noqa: E402


class TestThemeContrast(unittest.TestCase):
    def test_text_tokens(self):
        for mode, p in theme.PALETTES.items():
            for fg in ("ink", "ink-2", "ink-3", "accent", "brass"):
                for bg in ("ground", "surface", "surface-2"):
                    with self.subTest(mode=mode, fg=fg, bg=bg):
                        self.assertGreaterEqual(C.contrast(p[fg], p[bg]), 4.5)
            with self.subTest(mode=mode, pair="accent-ink/accent"):
                self.assertGreaterEqual(C.contrast(p["accent-ink"], p["accent"]), 4.5)
            for tag in ("tag-style", "tag-motif", "tag-guard"):
                with self.subTest(mode=mode, tag=tag):
                    self.assertGreaterEqual(C.contrast(p["ink"], p[tag]), 4.5)
                    self.assertGreaterEqual(C.contrast(p["ink-3"], p[tag]), 3.0)

    def test_tokens_unchanged_from_bildsprache(self):
        """Swiss-Theme unverändert (ground #FFFFFF/#0B0B0B, accent #C8050F/#FF4D52)."""
        self.assertEqual((theme.PALETTES["light"]["ground"], theme.PALETTES["dark"]["ground"]), ("#FFFFFF", "#0B0B0B"))
        self.assertEqual((theme.PALETTES["light"]["ink"], theme.PALETTES["dark"]["ink"]), ("#0B0B0B", "#FFFFFF"))
        self.assertEqual((theme.PALETTES["light"]["accent"], theme.PALETTES["dark"]["accent"]), ("#C8050F", "#FF4D52"))
        self.assertEqual((theme.PALETTES["light"]["accent-ink"], theme.PALETTES["dark"]["accent-ink"]), ("#FFFFFF", "#0B0B0B"))
        self.assertEqual(set(theme.PALETTES["light"]), set(theme.PALETTES["dark"]))

    def test_storage_key(self):
        js = (ROOT / "web" / "theme.js").read_text(encoding="utf-8")
        self.assertIn("var KEY = 'farbsprache.theme';", js)
        css = theme.css()
        self.assertIn('@media (prefers-color-scheme: dark) { :root:not([data-theme="light"])', css)
        self.assertIn(':root[data-theme="dark"]', css)
        self.assertIn('hidden', theme.controls("de"))


if __name__ == "__main__":
    unittest.main()
