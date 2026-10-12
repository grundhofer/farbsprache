"""Datenprüfungen (Spezifikation 7.8, 7.9): check_all ist grün, und jede wichtige Prüfung schlägt an, wenn man
eine Kopie der Daten gezielt kaputt macht (Mutationstests nach dem Muster von Designsprache). Die Kopie im
Temp-Verzeichnis enthält nur die Dateien von P0 und die Testaufgabe, damit sie nicht von Paketen abhängt."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import checks  # noqa: E402

SEG = dict(build.SEG, **build.FIXTURE_SEG)
P0_FILES = ["data/color-constants.json", "data/cvd.json", "data/css-names.json", "data/testvectors.json",
            "data/comparisons.json", "data/datasets/okabe-ito.json", "data/rules/core.json", "data/sources/core.json",
            "web/copy/core.py", "web/readme.de.md", "web/readme.en.md", "tools/blocklist.txt"]


def twin(lang, page):
    return build.PAGE_TWIN(lang, page, SEG)


class Sandbox:
    """P0-Dateien und tests/fixtures/ in einem Temp-Verzeichnis; mutate(rel, fn) ändert eine Datei."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in P0_FILES:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, self.root / rel)
        for sub in ("data", "web", "patterns", "tools"):
            src = build.FIXTURES / sub
            if src.exists():
                shutil.copytree(src, self.root / sub, dirs_exist_ok=True)
        (self.root / "data" / "explain").mkdir(parents=True, exist_ok=True)

    def json(self, rel, fn):
        f = self.root / rel
        d = json.loads(f.read_text(encoding="utf-8"))
        fn(d)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def text(self, rel, old, new):
        f = self.root / rel
        s = f.read_text(encoding="utf-8")
        assert old in s, f"{old!r} nicht in {rel}"
        f.write_text(s.replace(old, new, 1), encoding="utf-8")

    def write(self, rel, text):
        f = self.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def errors(self, allow_missing=False, warnings=None):
        return checks.check_all(self.root, allow_missing=allow_missing, date="2026-10-11", warnings=warnings, seg=SEG, twin=twin)

    def close(self):
        self.tmp.cleanup()


TASK = "data/tasks/fixture.json"
COPY = "web/copy/fixture.py"
PATTERN = "patterns/fixture.html"


class TestProjectData(unittest.TestCase):
    def test_check_all_passes(self):
        """check_all() == [] (fehlende Aufgaben anderer Pakete nur als WARNUNG, wie beim Bau mit --allow-missing)."""
        warns = []
        self.assertEqual(checks.check_all(ROOT, allow_missing=True, warnings=warns), [])

    def test_no_short_imperatives_in_project(self):
        """T-01: Die Projekttexte enthalten keinen Kurzimperativ, auch nicht nach einem Komma (Agent-Prompt „frag nach“)."""
        warns = []
        checks.check_all(ROOT, allow_missing=True, warnings=warns)
        self.assertEqual([w for w in warns if "Kurzimperativ" in w], [])

    def test_strict_only_misses_packages(self):
        """Ohne --allow-missing nennt die Prüfung nur fehlende Teile anderer Pakete, sonst nichts."""
        errs = checks.check_all(ROOT)
        order = json.loads((ROOT / "data" / "tasks" / "_order.json").read_text(encoding="utf-8"))["order"]
        if all((ROOT / "data" / "tasks" / f"{t}.json").exists() for t in order):
            self.assertEqual(errs, [])
        else:
            allowed = ("fehlt (Aufgabe anlegen oder mit --allow-missing bauen)", "der Eintrag fehlt", "von keiner Aufgabe verwendet")
            self.assertEqual([e for e in errs if not any(a in e for a in allowed)], [])
            self.assertTrue(errs)

    def test_fixture_overlay_passes(self):
        self.assertEqual(checks.check_all(ROOT, [build.FIXTURES], allow_missing=True, seg=SEG, twin=twin), [])

    def test_fixture_overlay_ignores_package_data(self):
        """Die Testaufgabe liegt nur über dem Kern von P0. Aufgaben, Regeln, Texte und Prüfungen der Pakete im
        Projekt (hier absichtlich kaputt) dürfen den Fixture-Bau nicht stören."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in P0_FILES:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, root / rel)
            (root / "data" / "tasks").mkdir(parents=True)
            (root / "data" / "tasks" / "_order.json").write_text('{"order": ["website"]}', encoding="utf-8")
            (root / "data" / "tasks" / "website.json").write_text("{kaputt", encoding="utf-8")
            (root / "data" / "rules" / "website.json").write_text('{"rules": [{"id": "verwaist"}]}', encoding="utf-8")
            (root / "data" / "explain").mkdir(parents=True)
            (root / "data" / "explain" / "website.json").write_text('{"entries": [{"id": "contrast"}]}', encoding="utf-8")
            (root / "web" / "copy" / "website.py").write_text("raise RuntimeError('Paket')\n", encoding="utf-8")
            (root / "tools" / "checks_website.py").write_text("def check(D, warn):\n    return ['Paketprüfung im Fixture-Bau']\n", encoding="utf-8")
            self.assertTrue(checks.check_all(root, allow_missing=True, seg=SEG, twin=twin), "ohne Überlagerung zählen die Paketdateien")
            self.assertEqual(checks.check_all(root, [build.FIXTURES], allow_missing=True, seg=SEG, twin=twin), [])

    def test_seg_and_page_twin(self):
        self.assertEqual(checks.check_seg(build.SEG, build.PAGE_TWIN), [])
        self.assertEqual(build.PAGE_TWIN("de", "de/diagramm/"), "en/charts/")
        self.assertEqual(build.PAGE_TWIN("en", "en/text-on-image/"), "de/text-auf-bild/")
        self.assertEqual(build.PAGE_TWIN("de", "de/"), "en/")
        self.assertEqual(build.path("de", "home"), "de/")
        self.assertEqual(build.path("en", "check"), "en/check/")
        self.assertEqual(build.rel("de/website/", "assets/site.css"), "../../assets/site.css")
        bad = dict(build.SEG, slides={"de": "diagramm", "en": "slides"})
        self.assertTrue(any("kommt bei" in e for e in checks.check_seg(bad, lambda l, p: build.PAGE_TWIN(l, p, bad))))


class TestMutations(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.addCleanup(self.sb.close)

    def assertError(self, needle, allow_missing=False):
        errs = self.sb.errors(allow_missing)
        self.assertTrue(any(needle in e for e in errs), f"erwartet „{needle}“, erhalten: {errs[:8]}")

    def test_baseline_is_clean(self):
        warns = []
        self.assertEqual(self.sb.errors(False, warns), [])

    def test_broken_json_is_an_error_not_a_traceback(self):
        self.sb.write(TASK, '{"id": "fixture",')
        self.assertError("kein gültiges JSON")
        self.sb.write("data/rules/core.json", "{")
        self.assertError("data/rules/core.json: kein gültiges JSON")

    def test_required_fields_and_language_pairs(self):
        self.sb.json(TASK, lambda d: d.pop("summary_en"))
        self.assertError("Feld summary_en fehlt")
        self.assertError("summary_de ohne summary_en")

    def test_copy_keys_in_both_languages(self):
        self.sb.text(COPY, '"pattern.button": "Aktion",', '"pattern.button": "Aktion", "nur.de": "x",')
        self.assertError("Schlüssel fixture.nur.de nur in de")

    def test_slugs_and_unique_ids(self):
        self.sb.json(TASK, lambda d: d["presets"][0].update(id="Petrol!"))
        self.assertError("ungültige ID")
        sb2 = Sandbox()
        self.addCleanup(sb2.close)
        sb2.json("data/rules/fixture.json", lambda d: d["rules"].append(dict(d["rules"][0])))
        errs = sb2.errors()
        self.assertTrue(any("doppelt" in e for e in errs), errs[:5])

    def test_foreign_keys(self):
        self.sb.json(TASK, lambda d: d["rules"].append("gibt-es-nicht"))
        self.assertError("Regel gibt-es-nicht gibt es nicht")
        self.sb.json("data/rules/fixture.json", lambda d: d["rules"][0]["sources"].append("unbekannt"))
        self.assertError("Quelle unbekannt gibt es nicht")

    def test_orphans(self):
        self.sb.json(TASK, lambda d: d["rules"].remove("text-contrast-aaa"))
        self.assertError("Regel text-contrast-aaa: von keiner Aufgabe verwendet")
        errs = self.sb.errors(allow_missing=True)
        self.assertFalse(any("text-contrast-aaa" in e for e in errs), "mit --allow-missing nur eine WARNUNG")

    def test_evidence_levels(self):
        self.sb.json("data/rules/core.json", lambda d: d["rules"][0].update(normative=[]))
        self.assertError("Norm braucht normative")
        self.sb.json("data/rules/fixture.json", lambda d: d["rules"][0].update(level="research", strength=None))
        self.assertError("Forschung braucht strength")

    def test_normative_flag_of_sources(self):
        self.sb.json("data/sources/core.json", lambda d: d["sources"][5].update(normative=True))  # F81
        self.assertError("steht unter informative, die Quelle ist aber normativ")

    def test_sources(self):
        self.sb.json("data/sources/core.json", lambda d: d["sources"][0].update(url="http://www.w3.org/TR/WCAG22/", retrieved="11.10.2026"))
        self.assertError("url muss mit https:// beginnen")
        self.assertError("retrieved muss ein ISO-Datum")

    def test_forbidden_result_keys(self):
        self.sb.json(TASK, lambda d: d["presets"][0].update(ratio=4.5))
        self.assertError("Schlüssel ratio ist in data/ verboten")

    def test_hand_numbers(self):
        self.sb.text(COPY, '"pattern.title": "Musterseite"', '"pattern.title": "Musterseite mit 4,47:1"')
        self.assertError("Kontrastzahl „4,47:1“ von Hand")
        self.sb.json(TASK, lambda d: d.update(summary_de="Abstand 7,9 zwischen allen Stufen."))
        self.assertError("Zahl hinter „Abstand“")

    def test_thresholds_and_placeholders_are_allowed(self):
        self.sb.text(COPY, '"pattern.title": "Musterseite"', '"pattern.title": "Musterseite mit 4,5:1 und {cr:#777777/#FFFFFF}"')
        self.assertEqual(self.sb.errors(), [])

    def test_tone(self):
        self.sb.text(COPY, '"pattern.button": "Aktion"', '"pattern.button": "Los!"')
        self.assertError("Ausrufezeichen")
        self.sb.text(COPY, '"pattern.link": "Link"', '"pattern.link": "Link — hier"')
        self.assertError("Geviertstrich")
        self.sb.text(COPY, '"pattern.legend": "Legende: Stufe 1, 2, 3"', '"pattern.legend": "Hier finden Sie die Legende"')
        self.assertError("Anrede „Sie“")
        self.sb.text(COPY, '"pattern.title": "Sample page"', '"pattern.title": "Sample colour page"')
        self.assertError("britische Schreibweise „colour“")
        self.sb.json(TASK, lambda d: d.update(summary_de="Sicher für Farbenblinde."))
        self.assertError("sicher für Farbenblinde")

    def test_tone_warnings(self):
        self.sb.text(COPY, '"pattern.title": "Musterseite"', '"pattern.title": "Wähl eine Musterseite, ganz einfach"')
        warns = []
        self.assertEqual(self.sb.errors(False, warns), [])
        self.assertTrue(any("Kurzimperativ „Wähl“" in w for w in warns), warns)
        self.assertTrue(any("Hype-Wort „einfach“" in w for w in warns), warns)

    def test_short_imperative_only_in_imperative_position(self):
        """Das Substantiv „Speicher“ löst nichts aus, der Kurzimperativ am Satzanfang oder nach „und“ schon."""
        self.sb.text(COPY, '"pattern.title": "Musterseite"', '"pattern.title": "Die Farbe bleibt im Speicher. Der Speicher ist lokal."')
        warns = []
        self.assertEqual(self.sb.errors(False, warns), [])
        self.assertFalse(any("Kurzimperativ" in w for w in warns), warns)
        self.sb.text(COPY, "Der Speicher ist lokal.", "Speicher sie lokal. Wähle eine Farbe und kopier die Palette.")
        warns = []
        self.assertEqual(self.sb.errors(False, warns), [])
        self.assertTrue(any("Kurzimperativ „Speicher“" in w for w in warns), warns)
        self.assertTrue(any("Kurzimperativ „kopier“" in w for w in warns), warns)

    def test_missing_rule_and_explain_ids_warn_with_allow_missing(self):
        """Regeln und Erklärt-Einträge anderer Pakete: streng ein FEHLER, mit --allow-missing nur eine WARNUNG."""
        self.sb.json(TASK, lambda d: (d["rules"].append("fremde-regel"), d["explain"].append("fremder-eintrag"),
                                      d["pairs"][0].update(rule="fremde-paarregel")))
        self.assertError("Regel fremde-regel gibt es nicht")
        self.assertError("Erklärt-Eintrag fremder-eintrag gibt es nicht")
        self.assertError("Regel fremde-paarregel gibt es nicht")
        warns = []
        errs = self.sb.errors(allow_missing=True, warnings=warns)
        self.assertFalse(any("fremd" in e for e in errs), errs)
        for needle in ("Regel fremde-regel", "Erklärt-Eintrag fremder-eintrag", "Regel fremde-paarregel"):
            self.assertTrue(any(needle in w for w in warns), (needle, warns))

    def test_preset_without_seed_needs_dataset_or_preset_control(self):
        """Eine Startpalette ohne seed und colors ist nur erlaubt, wenn sie auf einem Datensatz beruht oder die
        Aufgabe sie über preset_control wählt."""
        self.sb.json(TASK, lambda d: d["presets"][0].pop("seed"))  # petrol nennt dataset okabe-ito
        self.assertEqual(self.sb.errors(), [])
        self.sb.json(TASK, lambda d: d["presets"][1].pop("seed"))  # signal ohne dataset
        self.assertError("Startpalette signal: seed oder colors fehlt")
        self.sb.json(TASK, lambda d: d.update(preset_control="k"))
        self.assertFalse(any("seed oder colors fehlt" in e for e in self.sb.errors()))

    def test_dataset_kind(self):
        self.sb.json("data/datasets/okabe-ito.json", lambda d: d.update(kind="mixed"))
        self.assertFalse(any("kind muss" in e for e in self.sb.errors()))
        self.sb.json("data/datasets/okabe-ito.json", lambda d: d.update(kind="gemischt"))
        self.assertError("Datensatz okabe-ito: kind muss eines von categorical, sequential, diverging, mixed sein")

    def test_rights(self):
        self.sb.json(TASK, lambda d: d["presets"][0].update(name_de="Pantone Blau"))
        self.assertError("enthält das Sperrwort „Pantone“")
        self.sb.text(COPY, '"pattern.body": "Ein Absatz mit Text und einem"', '"pattern.body": "RAL 5002 entspricht etwa #1F3A93 und einem"')
        self.assertError("Sperrwort „RAL“ und ein Hex-Wert im selben Satz")

    def test_datasets(self):
        self.sb.json("data/datasets/okabe-ito.json", lambda d: d["schemes"][0]["colors"][1].update(hex="#E69F01"))
        self.assertError("passt nicht zu origin.rgb")
        self.sb.json("data/datasets/okabe-ito.json", lambda d: d.update(machine_sha256="abc", license=None))
        self.assertError("machine_sha256 ist keine SHA-256-Prüfsumme")
        self.assertError("Feld license fehlt")
        ds = json.loads((ROOT / "data" / "datasets" / "okabe-ito.json").read_text(encoding="utf-8"))
        ds.update(id="colorbrewer", required_notice="Colors by Cynthia Brewer.")
        self.sb.write("data/datasets/colorbrewer.json", json.dumps(ds))
        self.assertError("wörtlich der ColorBrewer-Pflichtsatz")

    def test_models_checked_age(self):
        self.sb.write("data/models.json", json.dumps({"models": [{"id": "flux2", "checked": "2025-01-01", "quote": "precision matching — no approximation"}]}))
        warns = []
        self.sb.errors(False, warns)
        self.assertTrue(any("Tage alt" in w for w in warns), warns)
        self.assertFalse(any("Geviertstrich" in e for e in self.sb.errors()), "das Zitat ist ausgenommen")

    def test_patterns(self):
        self.sb.text(PATTERN, '<div class="fx-card">', '<script>alert(1)</script><div class="fx-card" onclick="x()">')
        self.assertError("<script> ist in Mustern verboten")
        self.assertError("on*-Attribute sind verboten")
        sb2 = Sandbox()
        self.addCleanup(sb2.close)
        sb2.text(PATTERN, ".demo-fixture .fx-muted { color:var(--d-text-muted); margin:0; }", ".fx-muted { color:#666666; } .demo-fixture b { color:white; }")
        errs = sb2.errors()
        self.assertTrue(any("beginnt nicht mit .demo-fixture" in e for e in errs), errs)
        self.assertTrue(any("Farbliteral in color: #666666" in e for e in errs), errs)
        self.assertTrue(any("Farbname in color: white" in e for e in errs), errs)
        sb3 = Sandbox()
        self.addCleanup(sb3.close)
        sb3.text(PATTERN, '<a href="#">', '<a href="https://example.com" id="x">')
        errs = sb3.errors()
        self.assertTrue(any("verweist nach außen" in e for e in errs), errs)
        self.assertTrue(any("id-Attribute sind verboten" in e for e in errs), errs)

    def test_patterns_strict(self):
        """Farbliterale auch in eigenen Variablen, fremde Variablen in jeder Farbeigenschaft, genaues Präfix,
        und jedes weitere patterns/*.html (etwa die Demo für Kurz erklärt) nach denselben Regeln."""
        self.sb.text(PATTERN, ".demo-fixture .fx-muted { color:var(--d-text-muted); margin:0; }",
                     ".demo-fixture .fx-muted { --ink:#666666; border:1px solid var(--rule); } .demo-fixturex b { margin:0; }")
        self.sb.write("patterns/demo-context.html", "<style>.demo-context { background:var(--d-ground); } .x { color:red; }</style><div>Text</div>")
        errs = self.sb.errors()
        self.assertTrue(any("Farbliteral in --ink: #666666" in e for e in errs), errs)
        self.assertTrue(any("border nutzt eine Variable außerhalb von --d-*" in e for e in errs), errs)
        self.assertTrue(any("„.demo-fixturex b“ beginnt nicht mit .demo-fixture" in e for e in errs), errs)
        self.assertTrue(any("patterns/demo-context.html: Selektor „.x“ beginnt nicht mit .demo-context" in e for e in errs), errs)
        self.assertTrue(any("patterns/demo-context.html: Farbname in color: red" in e for e in errs), errs)

    def test_explain_demo_needs_pattern(self):
        self.sb.json("data/explain/fixture.json", lambda d: d["entries"][0].update(demo="context"))
        self.assertError("Demo patterns/demo-context.html fehlt")
        self.sb.write("patterns/demo-context.html", "<style>.demo-context { background:var(--d-ground); }</style><div></div>")
        self.assertFalse(any("demo-context" in e for e in self.sb.errors()))

    def test_seed_control(self):
        self.sb.json(TASK, lambda d: d.update(seed_control="k"))
        self.assertError("seed_control k muss ein Chip-Steuerelement der Aufgabe sein")
        self.sb.json(TASK, lambda d: d.update(seed_control="m"))
        self.assertError("seed_control m braucht visible: false")

    def test_controls_and_presets(self):
        self.sb.json(TASK, lambda d: [c.update(visible=True) for c in d["controls"]])
        self.assertError("mehr als drei sichtbare Steuerelemente")
        self.sb.json(TASK, lambda d: d["presets"].pop())
        self.assertError("genau 3 Startpaletten nötig")
        self.sb.json(TASK, lambda d: d["presets"][0].update(expect=["kein gültiger Eintrag"]))
        self.assertError("hat nicht die Form befund@modus")
        self.sb.json(TASK, lambda d: d["presets"][0]["options"].update(k=9))
        self.assertError("liegt nicht zwischen min und max")

    def test_task_texts(self):
        self.sb.text(COPY, '"ctl.steps": "Stufen",', "")
        self.assertError("Text ctl.steps fehlt in COPY[de]['fixture']")
        self.sb.text(COPY, '"agent.tip": "Halte', '"agent.tipp": "Halte')
        self.assertError("Text agent.tip fehlt")

    def test_explain_entries(self):
        self.sb.json("data/explain/fixture.json", lambda d: d["entries"][0].update(body_de="Zu kurz."))
        self.assertError("body_de hat 2 Wörter, erlaubt sind 60 bis 120")
        self.sb.json("data/explain/_order.json", lambda d: d["order"].pop())
        self.assertError("fehlt in data/explain/_order.json")

    def test_readme_placeholders(self):
        self.sb.text("web/readme.de.md", "__N_TASKS__", "__N_AUFGABEN__")
        self.assertError("unbekannter Platzhalter __N_AUFGABEN__")

    def test_package_checks_are_loaded(self):
        self.sb.write("tools/checks_fixture.py", "def check(D, warn):\n    warn('Paketprüfung lief')\n    return ['Paket: ' + ','.join(sorted(D['tasks']))]\n")
        warns = []
        errs = self.sb.errors(False, warns)
        self.assertIn("Paket: fixture", errs)
        self.assertIn("Paketprüfung lief", warns)

    def test_short_imperative_after_comma(self):
        """T-01: „Fehlt eine Rolle, frag nach“ ist ein Kurzimperativ nach einem Komma, „Frag“ auch am Satzanfang."""
        self.sb.text(COPY, '"pattern.title": "Musterseite"', '"pattern.title": "Fehlt eine Rolle, frag nach. Frag vorher."')
        warns = []
        self.assertEqual(self.sb.errors(False, warns), [])
        self.assertTrue(any("Kurzimperativ „frag“" in w for w in warns), warns)
        self.assertTrue(any("Kurzimperativ „Frag“" in w for w in warns), warns)

    def test_typography_by_language(self):
        """T-12, T-07: Prozent im Deutschen mit U+202F, Anführungszeichen nach der Sprache des Satzes."""
        self.sb.json(TASK, lambda d: d.update(summary_de="Etwa 8 % der Fläche, „Fläche“ genannt”.", summary_en="Called „Fläche“ in German."))
        self.assertError("Prozent mit normalem Leerzeichen")
        self.assertError("deutsche Anführungszeichen im englischen Text")
        self.assertError("englisches Schlusszeichen ” im deutschen Text")
        self.sb.json(TASK, lambda d: d.update(summary_de="Etwa 8 % der Fläche.", summary_en="Called “Fläche” in German."))
        self.assertEqual(self.sb.errors(), [])

    def test_short_lang_only_for_untranslated_labels(self):
        """R4-10: short_lang nennt die Sprache einer unübersetzten Kurzangabe; eine übersetzte hat keine eigene Sprache."""
        src = "data/sources/fixture.json"
        self.sb.json(src, lambda d: d["sources"][0].update(short_lang="en"))
        self.assertError("short_lang (de oder en) gibt es nur, wenn short_de und short_en gleich sind")
        sb2 = Sandbox()
        self.addCleanup(sb2.close)
        sb2.json(src, lambda d: d["sources"][0].update(short_de="Test source", short_lang="en"))
        self.assertEqual(sb2.errors(), [])

    def test_source_language(self):
        """T-07, R4-10: title_lang passt zum Titel, Sprachmarken [en]/[de] nur in Quellentexten und vollständig."""
        src = "data/sources/fixture.json"
        self.sb.json(src, lambda d: d["sources"][0].update(claim_de="Zitat „[en]as is[/en]“ und „[en]offen“.", claim_en="Says [en]x[/en]."))
        self.assertError("claim_de hat unvollständige Sprachmarken")
        self.assertError("claim_en markiert die eigene Sprache")
        self.sb.json(src, lambda d: d["sources"][0].update(claim_de="Gut.", claim_en="Fine.", title="Use colors / Farben nutzen"))
        self.assertError("zweisprachiger Titel „A / B“ braucht title_lang en/de")
        self.sb.json(src, lambda d: d["sources"][0].pop("title_lang"))
        self.assertError("Feld title_lang fehlt")
        sb2 = Sandbox()
        self.addCleanup(sb2.close)
        sb2.json(TASK, lambda d: d.update(summary_en="Called [de]Fläche[/de] in German."))
        self.assertTrue(any("Sprachmarke [en]/[de] gibt es nur in claim_* und unverified_*" in e for e in sb2.errors()))

    def test_own_settings_are_conventions(self):
        """R-06: Eine Festlegung von Farbsprache trägt die Stufe Konvention; nennt der Text eine Festlegung, ist own wahr."""
        rules = "data/rules/fixture.json"
        self.sb.json(rules, lambda d: d["rules"][0].update(level="research", strength="partial"))
        self.assertError("own: true (Festlegung von Farbsprache) trägt die Stufe convention")
        sb2 = Sandbox()
        self.addCleanup(sb2.close)
        sb2.json(rules, lambda d: d["rules"][0].update(own=False, text_de="Ab drei Stufen beschrifte jede Stufe direkt, als Festlegung."))
        self.assertTrue(any("nennt eine Festlegung, die Regel hat aber own: false" in e for e in sb2.errors()))

    def test_ral_names_are_not_preset_names(self):
        """R-05: Keine Startpalette heißt wie eine RAL-Classic-Farbe der Signal-Reihe (Signalrot ist RAL 3001)."""
        self.sb.json(TASK, lambda d: d["presets"][1].update(name_de="Signalrot", name_en="Signal red"))
        self.assertError("enthält das Sperrwort „Signalrot“")
        self.assertError("enthält das Sperrwort „Signal red“")

    def test_control_lang_only_for_text(self):
        """R4-10: lang beschreibt die Sprache eines Textfelds und gibt es nur dort."""
        self.sb.json(TASK, lambda d: d["controls"][0].update(lang="en"))
        self.assertError("Steuerelement m: lang gibt es nur bei type text")


if __name__ == "__main__":
    unittest.main()
