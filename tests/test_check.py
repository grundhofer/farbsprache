"""Palette prüfen (Spezifikation 3.8, 4.9, 5.8, Abnahme P5): Scanner mit CSS-Kontexten, Rollen-Raten,
Befundstufen, Reparatur, URL-Zustand und Prüfbericht in tools/check.py. Die JS-Seite prüft tests/check.test.cjs."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import check as CK, color as C  # noqa: E402

CFG = json.loads((ROOT / "data" / "check.json").read_text(encoding="utf-8"))
REFS = C.reference_values()
CONVENTION = ("check-duplicates", "check-cvd", "check-gray", "check-neutral-missing", "check-gamut", "check-alpha")

SHADCN4 = """:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
}
.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
}"""
SHADCN3 = """@layer base {
  :root { --background: 0 0% 100%; --foreground: 222.2 84% 4.9%; --primary: 222.2 47.4% 11.2%;
          --primary-foreground: 210 40% 98%; --ring: var(--primary); }
  .dark { --background: 222.2 84% 4.9%; --foreground: 210 40% 98%; --ring: var(--missing); }
}"""
TAILWIND = """@theme {
  --color-background: #ffffff;
  --color-foreground: #111827;
  --color-primary: #4f46e5;
}
@media (prefers-color-scheme: dark) {
  :root { --color-background: #0b1020; --color-foreground: #f3f4f6; }
}
[data-theme="dark"] { --color-primary: #a5b4fc; }"""
PALETTES = ["#0F172B #F8FAFC #E69F00", SHADCN4, SHADCN3, TAILWIND,
            "#E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7 #FFFFFF",
            "#FFFFFF #FEFEFE #777777 #787878 #FF0000 #00A000 #0000FF #000000",
            "hsl(0 100% 50%) hsl(51 100% 50%) hsl(103 100% 50%) hsl(154 100% 50%) hsl(206 100% 50%) hsl(257 100% 50%)",
            ":root{--bg:#fff;--text:#999;--border-strong:#ddd;--accent:#ff8800;--on-accent:#ffffff;--danger:#ff5555}"]


def model(text, state=None):
    return CK.analyze(CK.scan(text, CFG), CFG, REFS, state)


def findings(m):
    return [f for cx in m["ctxs"] for f in cx["findings"]]


def confirm(m):
    return {"roles": [c["role"] for c in m["colors"]], "confirmed": True, "bgi": None}


class TestScanner(unittest.TestCase):
    def test_plain_list(self):
        sc = CK.scan(CFG["example"], CFG)
        self.assertEqual([c["hex"] for c in sc["colors"]], ["#0F172B", "#F8FAFC", "#E69F00"])
        self.assertEqual({c["ctx"] for c in sc["colors"]}, {"light"})
        self.assertEqual(sc["colors"][2]["spans"], [[16, 23]])

    def test_shadcn_root_and_dark_are_split(self):
        m = model(SHADCN4)
        light = [c for c in m["colors"] if c["ctx"] == "light"]
        dark = [c for c in m["colors"] if c["ctx"] == "dark"]
        self.assertEqual([c["hex"] for c in light], ["#FFFFFF", "#0A0A0A", "#171717", "#FAFAFA", "#F5F5F5", "#737373", "#E7000B", "#E5E5E5"])
        self.assertEqual([c["hex"] for c in dark], ["#0A0A0A", "#FAFAFA", "#171717", "#E5E5E5", "#A1A1A1", "#FF6467", "#FFFFFF", "#FFFFFF"])
        self.assertEqual([c["alpha"] < 1 for c in dark], [False] * 6 + [True, True])
        self.assertEqual([c["role"] for c in light], ["bg", "text", "accent", "on-accent", None, "text-muted", "danger", "border"])
        self.assertEqual([c["role"] for c in dark], ["bg", "text", "surface", "accent", "text-muted", "danger", "border", "border-strong"])
        self.assertEqual([c["names"] for c in light][0], ["background", "card"])
        self.assertEqual([cx["ctx"] for cx in m["ctxs"]], ["light", "dark"])

    def test_tailwind_theme_and_dark_variants(self):
        m = model(TAILWIND)
        self.assertEqual([(c["hex"], c["ctx"], c["role"]) for c in m["colors"]],
                         [("#FFFFFF", "light", "bg"), ("#111827", "light", "text"), ("#4F46E5", "light", "accent"),
                          ("#0B1020", "dark", "bg"), ("#F3F4F6", "dark", "text"), ("#A5B4FC", "dark", "accent")])

    def test_shadcn_channels_and_var(self):
        sc = CK.scan(SHADCN3, CFG)
        light = [c for c in sc["colors"] if c["ctx"] == "light"]
        self.assertEqual(light[0]["hex"], "#FFFFFF")
        self.assertIn("ring", light[2]["names"])  # var(--primary) eine Ebene aufgelöst
        self.assertEqual(sc["notes"], [{"key": "var", "name": "ring", "ref": "missing"}])

    def test_comments_names_functions(self):
        sc = CK.scan("/* #FF0000 */ tomato, rgb(0 0 255 / 50%), oklch(0.7 0.3 150), color(display-p3 1 0 0) background-color", CFG)
        self.assertEqual([c["hex"] for c in sc["colors"]], ["#FF6347", "#0000FF", "#00C248", "#FF0B0C"])
        self.assertEqual([c["oog"] for c in sc["colors"]], [False, False, True, True])
        self.assertEqual(sc["colors"][1]["alpha"], 0.5)

    def test_duplicates_merged_and_limit(self):
        sc = CK.scan("#fff #FFFFFF white " + " ".join("#%02X0000" % i for i in range(1, 15)), CFG)
        self.assertEqual(len(sc["colors"]), CFG["max_colors"])
        self.assertEqual(len(sc["colors"][0]["spans"]), 3)
        self.assertEqual(sc["notes"], [{"key": "dropped", "ctx": "light", "n": 3}])


class TestSeverity(unittest.TestCase):
    def test_fails_need_confirmed_roles(self):
        for text in PALETTES:
            m = model(text)
            with self.subTest(text=text[:30]):
                self.assertNotIn("fail", [f["sev"] for f in findings(m)])
        m = model(PALETTES[-1])
        self.assertTrue(any(f["sev"] == "check" and f.get("open") == "unconfirmed" for f in findings(m)))
        m2 = model(PALETTES[-1], confirm(m))
        fails = [f for f in findings(m2) if f["sev"] == "fail"]
        self.assertTrue(fails)
        for f in fails:
            self.assertIn(f["id"], ("check-text", "check-nontext"))
            rule = CK._rule_of({"cfg": CFG, "rules": {r["id"]: r for p in (ROOT / "data" / "rules").glob("*.json")
                                                     for r in json.loads(p.read_text(encoding="utf-8"))["rules"]}}, f["id"])
            self.assertEqual(rule["level"], "norm")

    def test_without_roles_only_check(self):
        m = model("#0F172B #F8FAFC #E69F00", {"roles": [None, None, None], "confirmed": True})
        self.assertEqual({f["sev"] for f in findings(m)}, {"check"})

    def test_conventions_are_notes(self):
        seen = set()
        for text in PALETTES:
            for state in (None, "confirm"):
                m = model(text)
                if state:
                    m = model(text, confirm(m))
                for f in findings(m):
                    if f["id"] in CONVENTION:
                        seen.add(f["id"])
                        self.assertEqual(f["sev"], "note", f)
        self.assertGreaterEqual(seen, {"check-duplicates", "check-cvd", "check-gray", "check-neutral-missing", "check-gamut", "check-alpha"})

    def test_okabe_not_below_itself(self):
        m = model("#E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7 #FFFFFF")
        self.assertNotIn("check-cvd", [f["id"] for f in findings(m)])


class TestRepair(unittest.TestCase):
    def apply(self, text, m, f):
        rp = f["repair"]
        for s, e in sorted(m["colors"][rp["i"]]["spans"], reverse=True):
            text = text[:s] + rp["to"] + text[e:]
        return text

    def test_contrast_repairs_meet_threshold(self):
        n = 0
        for text in PALETTES:
            m = model(text)
            for f in findings(m):
                if f["id"] in ("check-text", "check-nontext") and f["repair"]["to"]:
                    n += 1
                    for o in f["on"]:
                        self.assertGreaterEqual(C.contrast(f["repair"]["to"], m["colors"][o]["eff"]), f["min"])
                    L0, C0, h0 = C.hex_to_oklch(f["repair"]["from"])
                    L1, C1, h1 = C.hex_to_oklch(f["repair"]["to"])
                    if h0 is not None and h1 is not None and C0 > 0.05:
                        # gleicher Farbton bis auf das Clipping im Gamut-Mapping (lokales MINDE, CSS Color 4)
                        self.assertLess(min(abs(h0 - h1), 360 - abs(h0 - h1)), 10)
        self.assertGreater(n, 5)

    def test_repair_text_says_what_the_calculation_does(self):
        """M-05: Der Löser setzt nur L neu; das Gamut-Mapping senkt danach oft die Buntheit (#FF6347 → #FFC8B9 verliert
        rund zwei Drittel). Der Vorschlagstext darf keine gleiche Buntheit des Ergebnisses behaupten."""
        seen = 0
        for text in ("#B22222 #FF6347", "#FFFFFF #00FF00", "#4A2A10 #BC641E", "tomato #FFFFFF"):
            for bgi in (0, 1):
                m = model(text, {"roles": None, "confirmed": False, "bgi": bgi})
                for f in findings(m):
                    rp = f.get("repair")
                    if f["id"] not in ("check-text", "check-nontext") or not rp or not rp["to"]:
                        continue
                    c0, c1 = C.hex_to_oklch(rp["from"])[1], C.hex_to_oklch(rp["to"])[1]
                    for lang in ("de", "en"):
                        msg = CK._plain(CK.repair_text(CK.test_context(lang), m, f))
                        with self.subTest(text=text, bgi=bgi, lang=lang, to=rp["to"]):
                            self.assertNotRegex(msg, r"gleiche[mr]? (Farbton|Buntheit)|same hue|same chroma")
                            self.assertIn("soweit sRGB" if lang == "de" else "as far as sRGB", msg)
                    seen += c1 < 0.8 * c0
        self.assertGreater(seen, 0, "kein Fall, in dem die Buntheit beim Abbilden deutlich sinkt")

    def test_gray_message_claims_no_print_result(self):
        """R-17: Der Befund rechnet nur Graustufen nach WCAG-Leuchtdichte; über Druck und Kopierer sagt er nichts Sicheres."""
        m = model("#FFFFFF #777777 #E69F00 #F0E442 #56B4E9")
        gray = [f for f in findings(m) if f["id"] == "check-gray"]
        self.assertTrue(gray)
        for lang in ("de", "en"):
            msg = CK._plain(CK.finding_message(CK.test_context(lang), m, gray[0]))
            self.assertNotRegex(msg, r"gedruckt oder kopiert fallen|photocopied in black and white, they practically coincide")
            self.assertIn("ähnlich aussehen" if lang == "de" else "may look similar", msg)

    def test_distance_repairs_reach_target_and_keep_contrast(self):
        n = 0
        for text in PALETTES:
            m = model(text)
            passes = {(p["id"], p["i"]) for cx in m["ctxs"] for p in cx["passes"]}
            for f in findings(m):
                if f["id"] not in ("check-duplicates", "check-cvd", "check-gray") or not f["repair"]["to"]:
                    continue
                n += 1
                m2 = model(self.apply(text, m, f))
                if len(m2["colors"]) != len(m["colors"]):
                    continue
                self.assertNotIn(f["key"], [g["key"] for g in findings(m2)])
                after = {(p["id"], p["i"]) for cx in m2["ctxs"] for p in cx["passes"]}
                # ohne Rolle steht „als Linie“ nur, solange „als Text“ verfehlt; erfüllt Text, ist Linie mit erfüllt
                after |= {("check-nontext", i) for k, i in after if k == "check-text"}
                self.assertLessEqual(passes, after)
        self.assertGreater(n, 3)

    def test_view_phrases_read_correctly(self):
        # Sichtweise im Satz: „bei normalem Sehen“, nicht „bei normales Sehen“
        m = model("#0072B2 #1F77B4 #2266AA #2B6FB0 #FFFFFF")
        for lang, good, bad in (("de", "bei normalem Sehen", "bei normales"), ("en", "with normal vision", "with normales")):
            R = CK.test_context(lang)
            text = " ".join(CK._plain(CK.finding_message(R, m, f) + " " + CK.repair_text(R, m, f)) for f in findings(m))
            self.assertIn(good, text)
            self.assertNotIn(bad, text)
        self.assertTrue({"check-duplicates", "check-cvd"} <= {f["id"] for f in findings(m)})

    def test_distance_repairs_never_lower_contrast(self):
        # „keine Kontrastprüfung verschlechtert“ (4.9): auch eine schon verfehlte Prüfung sinkt nicht weiter
        n = 0
        for text in PALETTES + ["#FFFFFF #0F172B #E69F00 #56B4E9", "#000000 #F0E442 #FFFF66 #777777"]:
            m = model(text)
            for cx in m["ctxs"]:
                hx = {g: m["colors"][g]["eff"] for g in cx["idx"]}
                for f in cx["findings"]:
                    rp = f.get("repair")
                    if f["id"] not in ("check-duplicates", "check-cvd", "check-gray") or not rp["to"]:
                        continue
                    n += 1
                    trial = dict(hx)
                    trial[rp["i"]] = rp["to"]
                    for it in CK._contrast_items(m, CFG, cx):
                        b, a = CK._measure(it, hx)[0], CK._measure(it, trial)[0]
                        self.assertFalse(CK._worse(it, b, a), (text, f["key"], it))
        self.assertGreater(n, 3)

    def test_new_findings_are_marked(self):
        m = model("#0F172B #F8FAFC #E69F00")
        R = CK.test_context("de")
        f = findings(m)[0]
        html = CK.render(m, R, {"new_keys": [f["key"]], "changed": [f["repair"]["i"]]})
        self.assertIn('data-new', html)
        self.assertIn('<span class="tag-sub f-new">neu</span>', html)
        self.assertIn("data-undo", html)


class TestStateAndReport(unittest.TestCase):
    def test_query_roundtrip(self):
        m = model(SHADCN4)
        mc = model(SHADCN4, confirm(m))
        q = CK.query(mc, 3)
        rq = CK.read_query("?" + q, CFG)
        self.assertFalse(rq["dirty"])
        self.assertEqual(rq["bgi"], 3)
        roles, confirmed = CK.state_roles(rq["r"])
        self.assertTrue(confirmed)
        m2 = model(CK.state_text(rq["f"], rq["r"]), {"roles": roles, "confirmed": True, "bgi": rq["bgi"]})
        self.assertEqual([(c["eff"], c["ctx"], c["role"]) for c in m2["colors"]], [(c["eff"], c["ctx"], c["role"]) for c in mc["colors"]])
        self.assertEqual(CK.query(m2, 3), q)

    def test_unconfirmed_roundtrip_keeps_contexts(self):
        # Ohne Bestätigung trägt r nur den Kontext: nach dem Neuladen bleiben hell und dunkel getrennt, Rollen entstehen nicht
        for text in (SHADCN4, TAILWIND):
            m = model(text)
            q = CK.query(m)
            r = re.search(r"r=([^&]*)", q).group(1).split(",")
            self.assertEqual(set(r), {"-", "-.d"})
            rq = CK.read_query("?" + q, CFG)
            self.assertFalse(rq["dirty"])
            self.assertEqual(CK.state_roles(rq["r"]), (None, False))
            m2 = model(CK.state_text(rq["f"], rq["r"]))
            self.assertEqual([(c["eff"], c["ctx"]) for c in m2["colors"]], [(c["eff"], c["ctx"]) for c in m["colors"]])
            self.assertFalse(m2["has_names"] or m2["confirmed"])
            self.assertNotIn("fail", [f["sev"] for f in findings(m2)])
            self.assertEqual(CK.query(m2), q)
        self.assertNotIn("r=", CK.query(model("#0F172B #F8FAFC #E69F00")))

    def test_shared_roles_stay_addressable(self):
        """M-03: Teilen sich Farben eine Rolle oder einen Namen, bekommt jede im CSS-Export und im Eingabetext aus dem Link
        einen eigenen Namen (zweiter „surface-b“), vor und nach dem Teilen. Kein Suffix trifft ein anderes Rollenmuster."""
        rq = CK.read_query("?f=FFFFFF,0A0A0A,FAFAFA,F5F5F5,171717,737373&r=bg,text,surface,surface,accent,text-muted", CFG)
        text = CK.state_text(rq["f"], rq["r"])
        self.assertIn("--surface: #FAFAFA;\n  --surface-b: #F5F5F5;", text)
        roles, confirmed = CK.state_roles(rq["r"])
        m = model(text, {"roles": roles, "confirmed": confirmed, "bgi": rq["bgi"]})
        R = CK.test_context("de")
        R["url"], R["date"] = "https://example.org/", "2026-10-11"
        for mm in (m, model(":root { --surface: #FAFAFA; }\n:root { --surface: #F5F5F5; }\n.dark { --text: #111111; --text: #EEEEEE; }")):
            css = CK.css(mm, R)
            for block in css.split("@media"):
                names = re.findall(r"^\s*--([A-Za-z0-9_-]+):", block, re.M)
                self.assertEqual(len(names), len(set(names)), names)
            for c in mm["colors"]:
                self.assertIn(c["eff"], css)
        self.assertEqual(CK.query(m, rq["bgi"]), "f=FFFFFF,0A0A0A,FAFAFA,F5F5F5,171717,737373&r=bg,text,surface,surface,accent,text-muted")
        # die Suffixe erzeugen keine fremde Rolle beim erneuten Raten (anders als text-2 → gedämpfter Text)
        for role in [r["id"] for r in CFG["roles"]]:
            for k in range(2, 6):
                twin = CK._uniq(role, {role} | {role + "-" + "bcdefghijklmnopqrstuvwxyz"[j] for j in range(k - 2)})
                guess = CK.guess_roles([{"names": [twin], "ctx": "light"}], CFG)[0]
                self.assertIn(guess, (None, role), twin)

    def test_read_query_canonical_order(self):
        rq = CK.read_query("?f=111111,FFFFFF,000000&r=text.d,bg,-&bgi=0", CFG)
        self.assertEqual((rq["f"], rq["r"], rq["bgi"], rq["dirty"]), (["#FFFFFF", "#000000", "#111111"], ["bg", "-", "text.d"], 2, True))
        m = model(CK.state_text(rq["f"], rq["r"]), {"roles": CK.state_roles(rq["r"])[0], "confirmed": True, "bgi": rq["bgi"]})
        self.assertEqual([(c["hex"], c["ctx"], c["role"]) for c in m["colors"]], [("#FFFFFF", "light", "bg"), ("#000000", "light", None), ("#111111", "dark", "text")])

    def test_read_query_drops_invalid(self):
        self.assertEqual(CK.read_query("?f=zz&r=bg", CFG), {"f": None, "r": None, "bgi": None, "dirty": True})
        rq = CK.read_query("?f=FFFFFF,000000&r=bg,nope&bgi=7&x=1", CFG)
        self.assertEqual((rq["f"], rq["r"], rq["bgi"], rq["dirty"]), (["#FFFFFF", "#000000"], None, None, True))

    def test_report_format(self):
        R = CK.test_context("de")
        m = model(SHADCN4)
        rep = CK.report(m, R)
        for part in ("# Prüfbericht", "Berechnet am 2026-10-11", R["url"], "## Hell: Verfehlt (0)", "## Dunkel: Prüfen",
                     "## Hell: Hinweise", "## Hell: Erfüllt", "Viénot, Brettel und Mollon 1999", "Nicht geprüft:"):
            self.assertIn(part, rep)
        self.assertNotRegex(rep, r"None|undefined|NaN")
        en = CK.report(m, CK.test_context("en"))
        self.assertIn("## Light: Fails (0)", en)
        css = CK.css(m, R)
        self.assertIn("@media (prefers-color-scheme: dark)", css)
        self.assertIn("--background:", css)
        exp = CK.export_html(m, R)
        for name in ("farbsprache-check-eigen.md", "farbsprache-check-eigen.txt", "farbsprache-check-eigen.css"):  # Schema 5.0
            self.assertIn(f'data-filename="{name}"', exp)

    def test_counts_have_singular_forms(self):
        """T-02/R4-14: „1 weiterer Befund“ und „1 weitere Farbe ist weggelassen“ statt der Mehrzahl, bei zwei Mehrzahl."""
        thirteen = " ".join("#%02X%02X%02X" % (i * 17 % 256, i * 53 % 256, i * 91 % 256) for i in range(1, 15))
        cases = {"de": ("1 weiterer Befund", "3 weitere Befunde", "1 weitere Farbe ist weggelassen.", "2 weitere Farben sind weggelassen."),
                 "en": ("1 more finding", "3 more findings", "1 more color is left out.", "2 more colors are left out.")}
        text = lambda m, R: re.sub(r"<[^>]+>", "", CK.render(m, R, {}))  # Zahlen stehen in <data class="count">
        for lang, (one, two, drop1, drop2) in cases.items():
            R = CK.test_context(lang)
            with self.subTest(lang=lang):
                m = model("#222 #fff #E63946 #bbb #ccc")
                self.assertEqual(len(findings(m)), CFG["open_findings"] + 1, "Testfall: genau ein weiterer Befund")
                self.assertIn(one, text(m, R))
                self.assertIn(f"<summary>{one}</summary>", CK.render(m, R, {}))
                m = model("#222 #fff #E63946 #bbb #ccc #eee")
                self.assertEqual(len(findings(m)), CFG["open_findings"] + 3)
                self.assertIn(two, text(m, R))
                m = model(" ".join(thirteen.split()[:13]))
                self.assertEqual(m["notes"][0]["n"], 1)
                self.assertIn(drop1, text(m, R))
                self.assertIn(drop2, text(model(thirteen), R))
        for lang in ("de", "en"):
            T = CK.test_context(lang)["T"]
            self.assertNotIn("{n}", T["live.done_1"])

    def test_config_references(self):
        rules = {r["id"] for p in (ROOT / "data" / "rules").glob("*.json") for r in json.loads(p.read_text(encoding="utf-8"))["rules"]}
        for f in CFG["findings"]:
            self.assertIn(f["rule"], rules)
        strings = re.findall(r'"([a-z0-9-]+)"', json.dumps(CFG))
        for core in ("non-text-contrast", "no-rounding", "text-contrast"):
            self.assertIn(core, strings, "Kernregel muss in data/check.json stehen (Waisenprüfung)")


if __name__ == "__main__":
    unittest.main()
