"""Belege, Recht, Ton und Zweisprachigkeit: Aussagen nicht stärker als ihre Quelle, eigene Festlegungen als solche
gekennzeichnet, DE und EN mit denselben Einschränkungen, Lizenzen für jede Datei, keine Verweise auf die nicht
veröffentlichte Spezifikation, fremdsprachige Stellen mit lang. Die Datentests laufen ohne Build, die Seitentests
brauchen docs/ (FARBSPRACHE_REQUIRE_BUILD=1 erzwingt ihn, sonst übersprungen)."""
import html, json, os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import checks  # noqa: E402
from web.copy import core as CORE, slides as SLIDES, method as METHOD, charts as CHARTS, check as CHECK, sources as SOURCES  # noqa: E402
from web.copy import image_text as IMAGE_TEXT  # noqa: E402

DOCS = ROOT / "docs"
REQUIRE = os.environ.get("FARBSPRACHE_REQUIRE_BUILD") == "1"
LANGS = ("de", "en")


def jload(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def by_id(kind, key):
    out = {}
    for f in sorted((ROOT / "data" / kind).glob("*.json")):
        if not f.name.startswith("_"):
            for x in json.loads(f.read_text(encoding="utf-8"))[key]:
                out[x["id"]] = x
    return out


RULES, EXPLAIN, SOURCES_D = by_id("rules", "rules"), by_id("explain", "entries"), by_id("sources", "sources")
TASKS = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (ROOT / "data" / "tasks").glob("*.json") if not f.name.startswith("_")}


def user_texts():
    D, errs = checks.load_all([ROOT])
    assert not errs, errs
    return checks.texts(D)


def flat(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [x for w in v.values() for x in flat(w)]
    if isinstance(v, list):
        return [x for w in v for x in flat(w)]
    return []


def page(rel):
    return (DOCS / rel / "index.html").read_text(encoding="utf-8")


def visible(t):
    t = re.sub(r"<(script|style|pre)[^>]*>.*?</\1>", " ", t, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


class TestSourcesFaithful(unittest.TestCase):
    def test_ti_room_levels_follow_the_source(self):
        """R-04: TI nennt die 100 lx einen gedimmten Besprechungsraum („minimum, dimmed light level“). Die Seite darf sie
        nicht „normal, Licht an“ nennen; 5 und 300 lx sind als Annahmen von Farbsprache erkennbar."""
        ti = SOURCES_D["ti-dlpa088"]
        self.assertIn("minimum, dimmed light level", ti["claim_de"])
        self.assertIn("“minimum, dimmed light level”", ti["claim_en"])
        normal = re.compile(r"normal(em|es|e)? (Raum)?licht|normal, Licht|normal room light|normal ambient|normal light|"
                            r"normal, lights|abgedunkelt|darkened", re.I)
        texts = {"slides": SLIDES.COPY, "method.s7": [METHOD.COPY[l]["method"]["s7.p"] for l in LANGS],
                 "method.s11": [METHOD.COPY[l]["method"]["s11.list"] for l in LANGS],
                 "sources.calc": [SOURCES.COPY[l]["sources"]["calc.ti-dlpa088"] for l in LANGS],
                 "rule": RULES["slides-plan-7"], "explain": EXPLAIN["projector"], "source": ti}
        for name, v in texts.items():
            for s in flat(v):
                self.assertNotRegex(s, normal, name)
        for lang, dimmed, ti_word, assumed in (("de", "gedimmt", "Texas Instruments", "angenommen"),
                                               ("en", "dimmed", "Texas Instruments", "assumed")):
            T = SLIDES.COPY[lang]["slides"]
            self.assertIn(dimmed, T["ctl.room.normal"])
            self.assertIn(ti_word, T["summary.normal"])
            self.assertIn(ti_word, T["rationale.proj.normal"])
            for key in ("summary.dim", "summary.bright", "rationale.proj.dim", "rationale.proj.bright"):
                self.assertIn(assumed, T[key], (lang, key))
            m7 = METHOD.COPY[lang]["method"]["s7.p"][0]
            self.assertIn(dimmed, m7)

    def test_unproven_entries_do_not_call_themselves_supported(self):
        """R-07: „Unbelegt“ heißt keine auffindbare Quelle oder widerlegt (6.13). Ein Eintrag, der sich selbst „teilweise
        belegt“ nennt, trägt Forschung. Elliot 2015 stützt Blau und Vertrauen mit Studien aus mehreren Laboren."""
        for kind, items, field in (("rules", RULES, "text_"), ("explain", EXPLAIN, "body_")):
            for i, it in items.items():
                if it["level"] == "unproven":
                    for lang, words in (("de", ("teilweise belegt", "gut belegt")), ("en", ("partly supported", "well supported"))):
                        for w in words:
                            self.assertNotIn(w, it[field + lang], f"{kind} {i}")
        m = EXPLAIN["meaning"]
        self.assertEqual((m["level"], m["strength"]), ("research", "partial"))
        self.assertIn("mehreren Laboren", m["body_de"])
        self.assertIn("several labs", m["body_en"])
        self.assertNotIn("Einzelstudien", m["body_de"])
        self.assertNotIn("single studies", m["body_en"])

    def test_own_settings_are_marked(self):
        """R-06: Auf Dunkel heller = mehr ist eine Festlegung gegen die Empfehlung von Schloss et al. 2019. Sie steht als
        eigene Regel mit Stufe Konvention, im Kurzergebnis als Festlegung und in Methode §11."""
        for rid, r in RULES.items():
            if r["own"]:
                self.assertEqual(r["level"], "convention", rid)
            else:
                self.assertNotIn("Festlegung", r["text_de"], rid)
                self.assertNotIn("Farbsprache setting", r["text_en"], rid)
        own = RULES["chart-dark-lighter-more"]
        self.assertTrue(own["own"])
        self.assertIn("chart-dark-lighter-more", TASKS["charts"]["rules"])
        self.assertIn("Festlegung von Farbsprache", CHARTS.COPY["de"]["charts"]["summary.seq-dark"])
        self.assertIn("Farbsprache setting", CHARTS.COPY["en"]["charts"]["summary.seq-dark"])
        for lang in LANGS:
            self.assertTrue(any("[[schloss-2019]]" in x for x in METHOD.COPY[lang]["method"]["s11.list"]), lang)

    def test_wording_not_stronger_than_the_source(self):
        """R-15, R-16, R-19, T-08: Herkunft, Prüfumfang, Autoren und Abschwächungen wie in der Quelle, DE wie EN."""
        e = EXPLAIN["60-30-10"]
        self.assertNotIn("stammt aus", e["body_de"])
        self.assertNotIn("comes from", e["body_en"])
        self.assertNotIn("aus der Raumgestaltung", RULES["img-60-30-10"]["text_de"])
        self.assertNotIn("from interior design", RULES["img-60-30-10"]["text_en"])
        for m in jload("data/models.json")["models"]:
            self.assertNotIn("nicht dokumentiert", m.get("note_de") or "", m["id"])
            self.assertNotIn("not documented", m.get("note_en") or "", m["id"])
        cat = EXPLAIN["categories"]
        self.assertIn("Liu und Munzner", cat["body_de"])
        self.assertIn("Liu and Munzner", cat["body_en"])
        self.assertNotIn("Munzners", cat["body_de"])
        self.assertEqual((SOURCES_D["munzner-color-2020"]["short_de"], SOURCES_D["munzner-color-2020"]["short_en"]),
                         ("Liu und Munzner, Farbe", "Liu and Munzner, color"))
        rp = SOURCES_D["recraft-palettes"]
        self.assertIn("may", rp["claim_en"])
        self.assertIn("kann", rp["claim_de"])
        self.assertIn("meist", rp["claim_de"])
        self.assertIn("kann es einem Modell", RULES["img-2-3-colors"]["text_de"])
        self.assertTrue(SOURCES_D["datawrapper-colors-2018"]["claim_de"].startswith("Betrachte Grau"))
        self.assertTrue(RULES["chart-max-categories"]["text_en"].startswith("Where possible"))
        self.assertIn("möglichst", RULES["chart-max-categories"]["text_de"])

    def test_sister_projects_named_correctly(self):
        """R-09: Nur Bildsprache nutzt das Swiss-Theme mit #0B0B0B, Designsprache ein eigenes."""
        for lang, bad in (("de", ("Schwesterprojekte", "Familie")), ("en", ("sister projects", "family"))):
            T = METHOD.COPY[lang]["method"]
            for s in flat([T["s11.list"], T["s15.p"]]):
                for b in bad:
                    self.assertNotIn(b, s, lang)
            self.assertIn("Bildsprache", " ".join(T["s15.p"]))

    def test_slides_tile_matches_the_model(self):
        """R-10: Im hellen Raum bleibt am Beamer laut eigener Rechnung wenig Kontrast; die Kachel verspricht das nicht."""
        t = TASKS["slides"]
        self.assertNotRegex(t["summary_de"], r"hellen Raum")
        self.assertNotRegex(t["summary_en"], r"lit room|bright room")

    def test_readme_counts(self):
        """R-18: Die Regeln allein zitieren nicht alle Quellen; die README nennt die Gesamtzahl für alle Texte."""
        cited = {s for r in RULES.values() for s in r["sources"]}
        self.assertLess(len(cited), len(SOURCES_D))
        for f, rules_word, all_words in (("README.de.md", "Regeln tragen", "Regeln, Erklärt-Einträge, Methode und Menüwege"),
                                         ("README.md", "rules carry", "Rules, explained entries, method and menu paths")):
            t = (ROOT / f).read_text(encoding="utf-8")
            self.assertIn(f"{len(RULES)} {rules_word}", t)
            self.assertIn(all_words, t)
            self.assertRegex(t, rf"{all_words}[^.]*\b{len(SOURCES_D)}\b")
        self.assertIn("German start page", (ROOT / "README.md").read_text(encoding="utf-8"))


class TestLicenses(unittest.TestCase):
    def test_every_path_has_a_license(self):
        """R-14: Jede eigene Datei ist einer Lizenz zugeordnet: LICENSE (Code) oder LICENSE-CONTENT.md (Texte, Werte,
        Fremddaten)."""
        text = (ROOT / "LICENSE").read_text(encoding="utf-8") + (ROOT / "LICENSE-CONTENT.md").read_text(encoding="utf-8")
        skip = {".git", ".gitignore", ".DS_Store", "__pycache__", "docs", "docs.tmp", "research", "og.html", "LICENSE",
                "LICENSE-CONTENT.md"}
        names = [p.name + ("/" if p.is_dir() else "") for p in ROOT.iterdir() if p.name not in skip]
        names += ["data/" + p.name + ("/" if p.is_dir() else "") for p in (ROOT / "data").iterdir()]
        for n in names:
            self.assertTrue(n in text or n.rstrip("/") + "/" in text or n.rstrip("/") in text.replace("`", " ").split(), n)

    def test_dataset_colors_keep_their_terms(self):
        """R-11: Exporte stehen unter CC0, Farben aus Datensätzen nicht; der Tol-Vermerk trägt den Copyright-Satz."""
        tol = jload("data/datasets/tol.json")["required_notice"]
        for lang in LANGS:
            self.assertIn(tol, CORE.COPY[lang]["export"]["notice.tol"])
        de = " ".join(SOURCES.COPY["de"]["sources"]["project.list"])
        en = " ".join(SOURCES.COPY["en"]["sources"]["project.list"])
        self.assertIn("Ausgenommen sind Farben aus Datensätzen", de)
        self.assertIn("Colors from data sets (Okabe-Ito, Paul Tol, ColorBrewer, viridis) are excluded", en)
        lc = (ROOT / "LICENSE-CONTENT.md").read_text(encoding="utf-8")
        self.assertIn("Ausgenommen sind Farben aus Datensätzen Dritter", lc)
        self.assertIn("Copyright (c) 2022, Paul Tol. All rights", lc)
        self.assertIn("ohne Pflicht", lc)


class TestPublicTexts(unittest.TestCase):
    SPEC = re.compile(r"Spezifikation \d|Bauspezifikation|specification \d|build specification|\bP0\b|Arbeitspaket|"
                      r"[Ww]ork package|Paketarbeit|Anfrage an P")

    def test_no_references_to_the_unpublished_specification(self):
        """R-12, T-06, T-09: research/ wird nicht veröffentlicht. Nutzertexte, README und CONTRIBUTING verweisen weder auf
        die Spezifikation noch auf interne Arbeitspakete."""
        for ctx, lang, s, art in user_texts():
            self.assertNotRegex(s, self.SPEC, ctx)
        for f in ("CONTRIBUTING.md", "README.md", "README.de.md", "web/readme.de.md", "web/readme.en.md"):
            self.assertNotRegex((ROOT / f).read_text(encoding="utf-8"), self.SPEC, f)
        c = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("python3 build.py --fixtures ", c)
        self.assertIn("drei Startpaletten (Diagramm: vier)", c)
        self.assertIn("three starter palettes (charts: four)", c)

    def test_color_location_hint_is_true(self):
        """M-01: Die Farbe steht im Link und geht damit an den Webserver; der Hinweis sagt das statt „bleibt im Browser“."""
        bad = re.compile(r"bleib(t|en) in deinem Browser|stays? in your browser")
        for ctx, lang, s, art in user_texts():
            self.assertNotRegex(s, bad, ctx)
        for lang, word in (("de", "Adresse der Seite"), ("en", "page address")):
            self.assertIn(word, CORE.COPY[lang]["frame"]["seed.hint"])
            self.assertIn(word, CHECK.COPY[lang]["check"]["in.hint"])

    def test_one_term_per_thing(self):
        """T-10: dieselben Begriffe auf allen Seiten (Startpalette, dunkel/gedimmt/hell, with normal vision, data sets,
        Tol-Schreibweise, gedämpfte Schrift, Schriftfarbe) und Gebrauchsangaben im Englischen klein."""
        bad = {"de": re.compile(r"Startsets|abgedunkelt"),
               "en": re.compile(r"starter sets|darkened|under normal vision|in normal vision|\bdatasets\b|Paul Tol, (Bright|Muted)")}
        for ctx, lang, s, art in user_texts():
            if art == "data" or art == "copy" or art == "claim":
                self.assertNotRegex(s, bad[lang], ctx)
        self.assertEqual(IMAGE_TEXT.COPY["de"]["image-text"]["ctl.tc"], "Schriftfarbe")
        names = {t: {r["id"]: r for r in TASKS[t]["roles"]} for t in TASKS}
        self.assertEqual(names["slides"]["text-2"]["name_en"], names["website"]["text-muted"]["name_en"])
        for t, roles in names.items():
            for rid, r in roles.items():
                self.assertNotRegex(r["use_en"], r"^[A-Z][a-z]", f"{t} {rid}")
        self.assertEqual(METHOD.COPY["de"]["method"]["s6.row.tol-bright"], CHARTS.COPY["de"]["charts"]["ctl.fam.tol-bright"])

    def test_role_names_read_in_sentences(self):
        """T-03: Rollennamen stehen in „{fg} auf {bg}“ und „auf {bg}“; ein Name mit eigener Präposition ergäbe
        „auf … auf“, ein Name mit Adjektiv vorn „auf Zweite Farbe“."""
        for t, task in TASKS.items():
            bgs = {b for f in ("pairs", "decorative", "advisory") for p in task.get(f) or [] for b in p["on"]}
            for r in task["roles"]:
                self.assertNotRegex(r["name_de"], r" auf ", f"{t} {r['id']}")
                self.assertNotRegex(r["name_en"], r" on ", f"{t} {r['id']}")
                if r["id"] in bgs:
                    self.assertNotRegex(r["name_de"], r"^(Erste|Zweite|Dritte|Vierte|Schlimmste)", f"{t} {r['id']}")

    def test_number_and_label_format(self):
        """T-12, T-13: DE-Zahlen in Prosa mit Komma, Kommas im englischen Satz, verständliche Kurzlabels."""
        self.assertIn("1,0", SOURCES_D["recraft-api-usage"]["claim_de"])
        self.assertTrue(any(x.startswith("From {cut} series on, the page") for x in METHOD.COPY["en"]["method"]["s11.list"]))
        self.assertEqual(CHECK.COPY["de"]["check"]["mx.g"], "Große Schrift, Grafik")
        self.assertEqual(CHECK.COPY["en"]["check"]["mx.g"], "Large text, graphics")
        self.assertEqual(SOURCES.COPY["en"]["sources"]["claim"], "Supports:")


@unittest.skipUnless(REQUIRE or (DOCS / "de" / "index.html").exists(), "docs/ fehlt – erst python3 build.py")
class TestPages(unittest.TestCase):
    def test_foreign_parts_marked(self):
        """T-07, R4-10: englische Titel und Zitate auf der deutschen Quellenseite mit lang="en", deutsche Teile auf der
        englischen mit lang="de"; zweisprachige Titel je Teil, Anführungszeichen nach der Sprache des Satzes."""
        de, en = page("de/quellen"), page("en/sources")
        for sid, s in SOURCES_D.items():
            item_de = re.search(rf'<li class="src-item" id="{re.escape(sid)}">(.*?)</li>', de, re.S).group(1)
            item_en = re.search(rf'<li class="src-item" id="{re.escape(sid)}">(.*?)</li>', en, re.S).group(1)
            title_de = re.search(r'<p class="src-t">(.*?)</p>', item_de, re.S).group(1)
            title_en = re.search(r'<p class="src-t">(.*?)</p>', item_en, re.S).group(1)
            if s["title_lang"] == "en":
                self.assertIn('<span lang="en">', title_de, sid)
                self.assertNotIn("<span lang=", title_en, sid)
            if s["title_lang"] == "en/de":
                self.assertRegex(title_de, r'<span lang="en">[^<]*</span> / [^<]', sid)
                self.assertRegex(title_en, r'[^>] / <span lang="de">', sid)
        for t in (de, en):
            self.assertNotRegex(t, r"\[/?(en|de)\]", "Sprachmarken müssen ersetzt sein")
            for m in re.findall(r'<span lang="de">([^<]*)</span>', t):
                self.assertNotIn(" / ", m)
        self.assertIn("„<span lang=\"en\">at a nascent stage of development</span>“", de)
        self.assertIn("“<span lang=\"de\">Dunkel 1</span>”", en)
        self.assertIn("“<span lang=\"de\">Gefolgter Link</span>”", en)
        self.assertNotIn("„", visible(re.sub(r'<span lang="de">.*?</span>', "", en)))
        # Unübersetzte Kurzangaben (short_lang) in den Quellenzeilen der Regeln, Erklärt-Einträge und der Methode
        short = {s["url"]: s for s in SOURCES_D.values() if s.get("short_lang")}
        self.assertTrue(short)
        n = 0
        for d in sorted((DOCS / "de").glob("*/index.html")) + sorted((DOCS / "en").glob("*/index.html")):
            lang = d.relative_to(DOCS).parts[0]
            if d.parent.name in ("quellen", "sources"):  # dort steht der volle Titel mit title_lang (oben)
                continue
            for href, attrs in re.findall(r'<a href="([^"]+)"([^>]*)>', d.read_text(encoding="utf-8")):
                s = short.get(html.unescape(href))
                if s:
                    n += 1
                    if s["short_lang"] != lang:
                        self.assertIn(f'lang="{s["short_lang"]}"', attrs, (str(d), href))
                    else:
                        self.assertNotIn("lang=", attrs, (str(d), href))
        self.assertGreater(n, 10)
        for sid, s in SOURCES_D.items():
            if s.get("short_lang"):
                for rel in ("de/methode", "en/method"):
                    t = page(rel)
                    for m in re.finditer(rf'<a class="m-src" href="[^"]*#{re.escape(sid)}"([^>]*)>', t):
                        self.assertEqual('lang="en"' in m.group(1), rel.startswith("de"), (rel, sid))
        ki = page("de/ki-bild")
        self.assertIn('„<span lang="en">', ki)
        for b in ("b1", "b2", "b3"):
            self.assertRegex(ki, rf'<input id="ctl-{b}" type="text" maxlength="200" lang="en"')
        self.assertNotRegex(page("en/ai-image"), r'id="ctl-b1"[^>]*lang=')

    def test_cited_in_names_rules(self):
        """T-11: „Zitiert in“ nennt Aufgabe und Regelanfang statt einer englischen ID und verlinkt auf die Regel."""
        for rel, word in (("de/quellen", "Regel ("), ("en/sources", "Rule (")):
            t = page(rel)
            cit = re.findall(r'<p class="src-meta">(?:Zitiert in:|Cited in:) (.*?)</p>', t)
            self.assertTrue(cit)
            self.assertFalse(any("<code>" in c for c in cit), rel)
            self.assertTrue(any(word in c for c in cit), rel)
            hrefs = re.findall(r'<a href="([^"]+#regel[^"]*)">', " ".join(cit))
            self.assertTrue(hrefs, rel)
            for h in hrefs:
                self.assertRegex(h, r"#regel(n|-[a-z0-9-]+)$")

    def test_every_source_is_cited(self):
        """R-18: Die README sagt, Regeln, Erklärt-Einträge, Methode und Menüwege stützen sich auf alle Quellen. Das stimmt nur,
        wenn keine Quelle auf der Quellenseite „noch nirgends“ zitiert ist."""
        for rel, lang in (("de/quellen", "de"), ("en/sources", "en")):
            t = page(rel)
            self.assertEqual(len(re.findall(r'<li class="src-item"', t)), len(SOURCES_D), rel)
            self.assertNotIn(html.escape(SOURCES.COPY[lang]["sources"]["cited.none"]), t, rel)

    def test_check_distance_headings_use_everyday_words(self):
        """X:T-10: Die Überschriften unter „Kleinste Abstände“ sind die Sichtweisen der Simulation, nicht das Fachwort
        allein, und beginnen groß."""
        for rel, lang in (("de/pruefen", "de"), ("en/check", "en")):
            heads = re.findall(r'<div class="dist-k"><h4>([^<]+)</h4>', page(rel))
            F = CORE.COPY[lang]["frame"]
            self.assertEqual([html.unescape(h) for h in heads], [F["sim." + k] for k in ("normal", "deutan", "protan", "tritan", "gray")])

    def test_pair_labels_without_double_preposition(self):
        """T-03: kein „auf … auf“ in Tabelle, Dekor-Liste und Badges; im Englischen Rollennamen im Satz klein."""
        for d in sorted((DOCS / "de").glob("*/index.html")) + sorted((DOCS / "en").glob("*/index.html")):
            t = d.read_text(encoding="utf-8")
            word = " auf " if "/de/" in str(d) else " on "
            for fg, bg in re.findall(r"<b>([^<]*)</b>" + word + r"<b>([^<]*)</b>", t):
                self.assertNotIn(word, fg, d)
            for bg in re.findall(r'class="badge">.*?' + word.strip() + r" ([^·<]+) ·", t):
                self.assertNotRegex(bg, r"^(Zweite|Erste|Schlimmste)", d)
            if "/en/" in str(d):
                for a, b in re.findall(r"\(([^()/<>]+)/([^()/<>,]+), [a-z]", visible(t)):
                    self.assertNotRegex(a.strip(), r"^[A-Z][a-z]", d)
                    self.assertNotRegex(b.strip(), r"^[A-Z][a-z]", d)

    def test_hints_on_pages(self):
        """M-01: Startseite, Aufgaben und Prüfseite zeigen den wahren Hinweis."""
        for rel, word in (("de", "Adresse der Seite"), ("de/website", "Adresse der Seite"), ("de/pruefen", "Adresse der Seite"),
                          ("en", "page address"), ("en/website", "page address"), ("en/check", "page address")):
            t = page(rel)
            self.assertIn(word, t, rel)
            self.assertNotRegex(t, r"bleib(t|en) in deinem Browser|stays? in your browser", rel)


if __name__ == "__main__":
    unittest.main()
