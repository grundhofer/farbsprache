"""Ehrlichkeitstest: Jede gebaute Seite wird geparst. Jedes <data class="num"> wird mit
tools/color.py aus seinen data-*-Attributen nachgerechnet und der angezeigte Text mit dem Formatierer
verglichen. Im sichtbaren Text steht keine „x:1“-Angabe außerhalb von <data>, außer den erlaubten
Schwellen, und nirgends „ΔE“. Ausgenommen von der x:1-Prüfung ist nur Text in Elementen mit dem Attribut
data-claim: die belegten Aussagen der Quellen (Quellenseite), die Zahlen der Quelle zitieren dürfen,
wie claim_* in tools/checks.py. Kopiertexte in <pre> prüft tests/test_exports.py.
Läuft über docs/ und tests/out/fixtures/docs/; ohne Build übersprungen, außer FARBSPRACHE_REQUIRE_BUILD=1."""
import html.parser, os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import color as C  # noqa: E402

SITES = [ROOT / "docs", ROOT / "tests" / "out" / "fixtures" / "docs"]
REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
ALLOWED = {"3:1", "4,5:1", "4.5:1", "7:1", "21:1"}
RATIO = re.compile(r"\d+(?:[.,]\d+)?\s*:\s*1(?![0-9])")
SKIP = {"script", "style", "pre", "template"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang, self.stack, self.tags, self.visible, self.cur = None, [], [], [], None
        self.claims, self.claim_open = [], []  # Text in data-claim-Elementen (Quellzahlen), eigene Liste

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag in VOID:
            return
        self.stack.append(tag)
        self.claim_open.append("data-claim" in a)
        if tag == "data":
            self.cur = {"attrs": a, "text": ""}

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            t = self.stack.pop()
            self.claim_open.pop()
            if t == tag:
                break
        if tag == "data" and self.cur is not None:
            self.tags.append(self.cur)
            self.cur = None

    def handle_data(self, data):
        if any(t in SKIP for t in self.stack):
            return
        if self.cur is not None:
            self.cur["text"] += data
        elif any(self.claim_open):
            self.claims.append(data)
        else:
            self.visible.append(data)


def built_pages():
    out = []
    for site in SITES:
        if (site / "de" / "index.html").exists():
            out += sorted(site.rglob("*.html"))
    return out


@unittest.skipUnless(REQUIRE or (SITES[0] / "de" / "index.html").exists(), "docs/ fehlt – erst python3 build.py --fixtures")
class TestHonesty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = built_pages()
        cls.refs = C.reference_values()

    def test_sites_built(self):
        for site in SITES:
            self.assertTrue((site / "de" / "index.html").exists(), f"{site.relative_to(ROOT)} fehlt (python3 build.py --fixtures)")

    def test_every_number_is_recalculated(self):
        n = 0
        for f in self.pages:
            p = Page()
            p.feed(f.read_text(encoding="utf-8"))
            lang = "en" if p.lang == "en" else "de"
            for tag in p.tags:
                a, cls = tag["attrs"], tag["attrs"].get("class")
                with self.subTest(page=str(f.relative_to(ROOT)), tag=a):
                    if cls == "num":
                        self.assertIn("data-m", a)
                        want = C.data_tag_text(a, lang, {"refs": self.refs})
                        self.assertEqual(tag["text"], want)
                        n += 1
                    elif cls == "count":
                        self.assertEqual(tag["text"], C.fmt_count(int(a["value"]), lang))
                    elif cls == "hex":
                        self.assertRegex(a["value"], r"^#[0-9A-F]{6}$")
                        self.assertEqual(tag["text"], a["value"])
                    elif cls == "date":
                        self.assertEqual(tag["text"], C.render_text("{date}", {"date": a["value"]}, lang)[1][0]["text"])
                    else:
                        self.fail(f"<data> ohne bekannte Klasse: {a}")
        self.assertGreater(n, 0, "keine einzige berechnete Zahl gefunden")

    def test_no_hand_numbers_in_visible_text(self):
        for f in self.pages:
            p = Page()
            p.feed(f.read_text(encoding="utf-8"))
            text = " ".join(p.visible)
            with self.subTest(page=str(f.relative_to(ROOT))):
                bad = [m.group(0) for m in RATIO.finditer(text) if re.sub(r"\s", "", m.group(0)) not in ALLOWED]
                self.assertEqual(bad, [])
                self.assertNotIn("ΔE", text + " ".join(p.claims))

    def test_claim_exception_only_for_source_claims(self):
        """data-claim gibt es nur auf der Quellenseite, und dort nur um die belegte Aussage einer Quelle."""
        n = 0
        for f in self.pages:
            src = f.read_text(encoding="utf-8")
            k = src.count("data-claim")
            if k:
                with self.subTest(page=str(f.relative_to(ROOT))):
                    self.assertIn(f.parent.name, ("quellen", "sources"))
                    self.assertEqual(k, len(re.findall(r'<span class="claim" data-claim>', src)))
                n += k
        if (SITES[0] / "de" / "quellen" / "index.html").exists():
            self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
