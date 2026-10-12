"""Rahmen der Aufgabenseiten nach der Zusammenführung Z (Spezifikation 3.0, 5.0, 5.4, 11): Zählformen im Prüfbericht,
Sentence case im Englischen (Hauptknopf, Badge), zusammengefasste Normquellen im Agent-Prompt, Codespannen auf der
Seite, eindeutige Dateinamen und dieselbe Quellenmenge für die Export-Renderer in Python und im Browser.
Die Prüfungen auf den gebauten Seiten brauchen docs/ (python3 build.py)."""
import json, os, re, sys, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from pages import task as P  # noqa: E402
from tools import export as X  # noqa: E402

DOCS = ROOT / "docs"
REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
TAG = re.compile(r"<[^>]+>")


def task_pages():
    out = []
    for lang in ("de", "en"):
        base = DOCS / lang
        for d in sorted(base.iterdir()) if base.is_dir() else []:
            f = d / "index.html"
            if f.is_file() and 'id="task-data"' in f.read_text(encoding="utf-8"):
                out.append((lang, f))
    return out


def block(html, bid):
    m = re.search(r"<!--fs:" + re.escape(bid) + r"-->(.*?)<!--/fs:" + re.escape(bid) + r"-->", html, re.S)
    return m.group(1) if m else None


def task_data(html):
    m = re.search(r'<script type="application/json" id="task-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def plain(html):
    return X.unesc(TAG.sub("", html))


class TestFrameHelpers(unittest.TestCase):
    CORE = {"and": "und"}

    def test_norm_sources_of_one_standard_are_merged(self):
        ctx = {"core": {"level.norm": "Norm", "informative": "informativ", "and": "und", "own": "x"},
               "sources": {"a": {"short_de": "WCAG 2.2, 2.4.7"}, "b": {"short_de": "WCAG 2.2, 1.4.11"},
                           "c": {"short_de": "WCAG 2.2, 1.4.3"}, "d": {"short_de": "CSS Color 4, 14.2"},
                           "u": {"short_de": "Understanding 2.4.7"}, "t": {"title": "Ohne Kurzangabe"}}}
        rule = {"level": "norm", "normative": ["a", "b"], "informative": ["u"]}
        self.assertEqual(X.level_note(rule, ctx, "de"), "(Norm: WCAG 2.2, 2.4.7 und 1.4.11; Understanding 2.4.7, informativ)")
        rule = {"level": "norm", "normative": ["c", "a", "b"], "informative": []}
        self.assertEqual(X.level_note(rule, ctx, "de"), "(Norm: WCAG 2.2, 1.4.3, 2.4.7 und 1.4.11)")
        rule = {"level": "norm", "normative": ["a", "d", "b", "t"], "informative": []}
        self.assertEqual(X.level_note(rule, ctx, "de"), "(Norm: WCAG 2.2, 2.4.7 und 1.4.11; CSS Color 4, 14.2; Ohne Kurzangabe)")
        self.assertEqual(X.level_note({"level": "norm", "normative": ["c"]}, ctx, "de"), "(Norm: WCAG 2.2, 1.4.3)")

    def test_filename_names_the_format_only_when_endings_collide(self):
        fmts = ["factsheet", "css", "hex", "dtcg", "rationale"]
        self.assertEqual(X.filename("brand", "tinte", "hex", "", fmts), "farbsprache-brand-tinte-hex.txt")
        self.assertEqual(X.filename("brand", "tinte", "rationale", "", fmts), "farbsprache-brand-tinte-rationale.txt")
        self.assertEqual(X.filename("brand", "tinte", "css", "", fmts), "farbsprache-brand-tinte.css")
        self.assertEqual(X.filename("brand", None, "dtcg", "-light", fmts), "farbsprache-brand-eigen-light.tokens.json")
        self.assertEqual(X.filename("ai-image", None, "prompt", "-palette", ["prompt", "hex"]), "farbsprache-ai-image-eigen-prompt-palette.txt")
        self.assertEqual(X.filename("check", None, "report"), "farbsprache-check-eigen.md")
        # M-10: eigene Endung eines Blocks (Recraft-JSON) und DTCG mit dem Medientyp aus DTCG 2025.10 §4.1
        self.assertEqual(X.filename("ai-image", "dunkelblau", "prompt", "-controls", ["prompt", "hex"], "json"),
                         "farbsprache-ai-image-dunkelblau-controls.json")
        self.assertEqual((X.mime("prompt", "json"), X.mime("prompt"), X.mime("dtcg"), X.mime("css")),
                         ("application/json", "text/plain", "application/design-tokens+json", "text/css"))

    def test_text_forms(self):
        R = {"T": {"w": "Paare", "w_1": "Paar"}}
        self.assertEqual([P.plural(R, "w", n) for n in (0, 1, 2)], ["Paare", "Paar", "Paare"])
        self.assertEqual(P.in_sentence("Background", "en"), "background")
        self.assertEqual(P.in_sentence("CSS", "en"), "CSS")
        self.assertEqual(P.in_sentence("Hintergrund", "de"), "Hintergrund")
        self.assertEqual(P.code_spans("nimm `--border-strong`, nicht `a b`"), "nimm <code>--border-strong</code>, nicht <code>a</code> <code>b</code>")
        self.assertEqual(P.code_spans("`<data>x</data>`"), "`<data>x</data>`")


class TestFramePages(unittest.TestCase):
    def setUp(self):
        if not (DOCS / "de" / "index.html").is_file():
            if REQUIRE:
                self.fail("docs/ fehlt – erst python3 build.py")
            self.skipTest("docs/ fehlt")
        self.pages = [(lang, f, f.read_text(encoding="utf-8")) for lang, f in task_pages()]
        self.assertTrue(self.pages)

    def test_check_summary_counts_singular_and_plural(self):
        forms = {"de": (r"Geprüft: (\d+) (Paare?), (\d+) erfüllt", ("Paar", "Paare"), None),
                 "en": (r"Checked: (\d+) (pairs?), (\d+) (pass(?:es)?)", ("pair", "pairs"), ("passes", "pass"))}
        seen_one = 0
        for lang, f, html in self.pages:
            text = plain(block(html, "chk-sum"))
            rx, nouns, verbs = forms[lang]
            m = re.fullmatch(rx, text)
            self.assertIsNotNone(m, f"{f}: {text}")
            n, k = int(m.group(1)), int(m.group(3))
            self.assertEqual(m.group(2), nouns[0] if n == 1 else nouns[1], f"{f}: {text}")
            if verbs:
                self.assertEqual(m.group(4), verbs[0] if k == 1 else verbs[1], f"{f}: {text}")
            seen_one += n == 1
        self.assertGreater(seen_one, 0, "keine Seite mit genau einem Paar (Text auf Bild, KI-Bild)")

    def test_english_main_button_and_badges_in_sentence_case(self):
        for lang, f, html in self.pages:
            if lang != "en":
                continue
            for m in re.finditer(r"<button[^>]*data-main(?:-bar)?>([^<]*)</button>", html):
                self.assertNotRegex(m.group(1), r"^Copy [A-Z][a-z]", f"{f}: {m.group(1)}")
            for m in re.finditer(r'<span class="badge">(.*?)</span>', block(html, "pal-roles"), re.S):
                self.assertNotRegex(plain(m.group(1)), r" on [A-Z][a-z]", f"{f}: {plain(m.group(1))}")
        check = (DOCS / "en" / "check" / "index.html").read_text(encoding="utf-8")
        main = re.findall(r'class="btn primary" data-copy-from="#exp-report-0">([^<]*)<', check)
        self.assertIn("Copy check report", main, "Hauptknopf der Prüfseite")

    def test_agent_prompt_merges_norm_sources(self):
        merged = 0
        for lang, f, html in self.pages:
            for m in re.finditer(r'<pre class="code" id="exp-agent-\d+"[^>]*><code>(.*?)</code></pre>', html, re.S):
                for note in re.findall(r"\((?:Norm|Standard): [^)]*\)", X.unesc(m.group(1))):
                    self.assertNotRegex(note, r"WCAG 2\.2, [^;]*WCAG 2\.2", f"{f}: {note}")
                    merged += bool(re.search(r"2\.4\.7 (und|and) 1\.4\.11", note))
        self.assertGreater(merged, 0, "keine Regel mit zwei Normquellen geprüft (Fokus)")

    def test_code_spans_on_page_backticks_in_exports(self):
        spans = 0
        for lang, f, html in self.pages:
            for bid in ("pal-notes", "pal-sum", "chk", "rules"):
                part = block(html, bid)
                self.assertNotIn("`", part, f"{f} {bid}: Backtick auf der Seite")
                spans += part.count("<code>--")
        self.assertGreater(spans, 0, "keine Codespanne auf einer Seite")
        web = (DOCS / "de" / "website" / "index.html").read_text(encoding="utf-8")
        agent = X.unesc(re.search(r'id="exp-agent-0"[^>]*><code>(.*?)</code>', web, re.S).group(1))
        self.assertIn("`--border-strong`", agent, "Exporte behalten die Backticks")

    def test_download_names_unique_per_page(self):
        for lang, f, html in self.pages:
            names = re.findall(r'data-filename="([^"]+)"', html)
            self.assertEqual(len(names), len(set(names)), f"{f}: {names}")
            # Endung und Medientyp passen zueinander, Design-Tokens als application/design-tokens+json (M-10)
            for name, mime in re.findall(r'data-filename="([^"]+)" data-mime="([^"]+)"', html):
                want = {"css": "text/css", "md": "text/markdown", "txt": "text/plain", "js": "text/javascript", "html": "text/html",
                        "json": "application/design-tokens+json" if name.endswith(".tokens.json") else "application/json"}
                self.assertEqual(mime, want[name.rsplit(".", 1)[1]], f"{f}: {name}")


class TestExportContextSources(unittest.TestCase):
    """Python übergibt den Export-Renderern genau die Quellen, die auch im Browser ankommen (#task-data): die Quellen der
    Regeln und die, die die Aufgabe direkt nennt (menu_paths[].source)."""

    def test_same_sources_as_task_data(self):
        site = build.Site([build.ROOT], build.ROOT / "tests" / "out" / "unused", "2026-10-11", allow_missing=True)
        site.prepare()
        seen = []
        real = X.render

        def spy(fmt, palette, task, ctx, lang, opts=None, gen=None):
            seen.append(ctx["sources"])
            return real(fmt, palette, task, ctx, lang, opts, gen)
        for t in site.tasks:
            for lang in ("de", "en"):
                seen.clear()
                with mock.patch.object(X, "render", spy):
                    html = P.page(site, lang, t)
                data = task_data(html)
                self.assertTrue(seen, t["id"])
                for s in seen:
                    self.assertEqual(s, data["sources"], f"{t['id']} {lang}")
                direct = {m["source"] for m in t.get("menu_paths") or []}
                self.assertTrue(direct <= set(data["sources"]), f"{t['id']}: Quellen aus menu_paths fehlen")


if __name__ == "__main__":
    unittest.main()
