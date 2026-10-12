"""Fachfälle der Aufgaben Website oder App und Statusfarben (Spezifikation 4.2, 4.3, 5.4, 5.6, 5.8, 8 P1).
Erwartungswerte stehen nur hier im Test, nie in Daten oder Texten. Formatiert wird mit den Formatierern des
Kerns, also abgeschnitten wie auf der Seite."""
import itertools, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import color as C, export as X  # noqa: E402
from tools.gen import website as W  # noqa: E402

DATE = "2026-10-11"


def cr(a, b, lang="de"):
    return C.fmt_ratio(C.contrast(a, b), lang)[:-2]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = build.Site([build.ROOT], build.ROOT / "tests" / "out" / "unused", DATE, allow_missing=True)
        cls.site.prepare()

    def task(self, tid):
        return self.site.task_by_id[tid]

    def pal(self, tid, pid):
        return self.site.palettes[tid][pid]

    def custom(self, tid, seed, **opts):
        t = self.task(tid)
        o = {c["id"]: c["default"] for c in t["controls"]}
        o.update(opts)
        return self.site.gens[tid].build(t, {"seed": C.parse(seed)["hex"], "colors": None, "options": o}, self.site.gen_ctx(t))

    def ectx(self, tid, pal, lang, pid=None):
        t = self.task(tid)
        rules = [self.site.rules[r] for r in t["rules"]]
        return {"date": DATE, "url": self.site.abs_url(lang, tid) + ("?p=" + pid if pid else ""), "name": pal.get("name_" + lang) or "x",
                "task_name": t["name_" + lang], "core": self.site.copy[lang]["export"], "text": self.site.copy[lang][tid],
                "rules": [r for r in rules if X.show_if(r.get("show_if"), pal)], "sources": self.site.sources,
                "refs": self.site.refs, "datasets": self.site.datasets, "data": {}}


class TestWebsite(Base):
    def test_petrol_light_42(self):
        r = self.pal("website", "petrol")["roles"]["light"]
        want = {"bg": "#F8FBFB", "text": "#182123", "text-muted": "#60696B", "border": "#D2D9DB", "border-strong": "#838C8F",
                "accent": "#11697A", "accent-text": "#11697A", "on-accent": "#FFFFFF"}
        self.assertEqual({k: r[k] for k in want}, want)
        self.assertEqual(cr(r["text"], r["bg"]), "15,76")
        self.assertEqual(cr(r["text-muted"], r["surface-2"]), "4,95")
        self.assertEqual(cr(r["border-strong"], r["bg"]), "3,30")
        self.assertEqual(cr(r["border"], r["bg"]), "1,37")
        self.assertEqual(cr(r["on-accent"], r["accent"]), "6,31")
        self.assertEqual(cr(r["accent-text"], r["text"]), "2,59")

    def test_petrol_dark_42(self):
        r = self.pal("website", "petrol")["roles"]["dark"]
        want = {"bg": "#101516", "text": "#E8ECED", "accent": "#276876", "on-accent": "#E8ECED", "accent-text": "#4E8D9C"}
        self.assertEqual({k: r[k] for k in want}, want)
        self.assertEqual(cr(r["on-accent"], r["accent"]), "5,30")
        self.assertEqual([cr(r["accent-text"], r[b]) for b in ("bg", "surface", "text", "surface-2")], ["4,92", "4,50", "3,14", "4,03"])
        self.assertEqual(cr(r["accent"], r["bg"]), "2,91")

    def test_signal_red_accent_42(self):
        p = self.custom("website", "#E63946")
        self.assertEqual(p["roles"]["light"]["accent"], "#DF3141")
        ch = next(c for c in p["changes"] if c["role"] == "accent" and c["mode"] == "light")
        self.assertEqual((ch["key"], ch["from"], ch["to"]), ("accent-darker", "#E63946", "#DF3141"))
        self.assertEqual(C.fmt_ratio(ch["values"]["before"], "de"), "4,16:1")
        self.assertEqual(C.fmt_ratio(ch["values"]["after"], "de"), "4,51:1")

    def test_tone(self):
        self.assertEqual(W.tint(0.08, "neutral"), 0.0)
        self.assertEqual(W.tint(0.08, "tinted"), 0.008)
        self.assertEqual(W.tint(0.01, "tinted"), 0.004)
        self.assertEqual(W.tint(0.30, "tinted"), 0.012)
        self.assertEqual(W.tint(0.08, "strong"), 0.02)
        self.assertEqual(W.tint(0.30, "strong"), 0.03)
        neutral = self.custom("website", "oklch(0.48 0.08 215)", tone="neutral")["roles"]["light"]
        self.assertEqual(neutral["bg"], "#FAFAFA")
        self.assertEqual(C.hex_to_oklch(neutral["text"])[1] < 0.000004, True)
        strong = self.custom("website", "oklch(0.48 0.08 215)", tone="strong")["roles"]["light"]
        self.assertNotEqual(strong["bg"], self.pal("website", "petrol")["roles"]["light"]["bg"])
        # unbunte Farbe: Tönung 0 auch bei „kräftig“
        gray = self.custom("website", "oklch(0.55 0 0)", tone="strong")["roles"]["light"]
        self.assertEqual(gray["bg"], "#FAFAFA")

    def test_change_cases(self):
        """Farbe bleibt, dunkle Schrift, Farbe angepasst (dunkler und heller), Grenzfälle ohne Lösung ab L_s (8, P1)."""
        petrol = self.pal("website", "petrol")
        # dunkel: Linkfarbe #4E8D9C statt des dunklen Kandidaten #276876, mit Hinweis (M-08, 3.0 C)
        self.assertEqual([(c["key"], c["mode"], c["from"], c["to"]) for c in petrol["changes"]],
                         [("accent-text-lighter", "dark", "#276876", "#4E8D9C")])
        self.assertEqual(petrol["extra"]["summary"], ["sum.light.keep-light", "sum.dark.keep-light"])
        senf = self.pal("website", "senf")
        self.assertEqual(senf["extra"]["summary"], ["sum.light.keep-dark", "sum.dark.keep-dark"])
        self.assertEqual(senf["roles"]["light"]["on-accent"], senf["roles"]["light"]["text"])
        self.assertEqual([c["key"] for c in senf["changes"]], ["accent-text-darker"])
        red = self.custom("website", "oklch(0.6 0.3 30)")
        self.assertIn("accent-lighter", [c["key"] for c in red["changes"] if c["mode"] == "dark"])
        self.assertIn("accent-darker", [c["key"] for c in red["changes"] if c["mode"] == "light"])
        for ch in red["changes"]:
            self.assertGreaterEqual(ch["values"]["after"], 4.5)
            self.assertLess(ch["values"]["before"], 4.5)
        # Eigene Farbe jenseits der Flächen (solve_l ab L_s wäre mixed-sides): die Linkfarbe wird trotzdem
        # berechnet, jedes Paar erfüllt, und die Suche ab TEXT_L0 trifft dieselbe Grenze wie ab einem L_s davor
        for seed in ("#FFFFFF", "#FCFCFC", "#000000", "#111827", "#0F172A", "#18181B"):
            for tone in ("neutral", "tinted", "strong"):
                p = self.custom("website", seed, tone=tone)
                self.assertTrue(all(q["pass"] for q in p["pairs"]), (seed, tone))
                for mode in ("light", "dark"):
                    r = p["roles"][mode]
                    self.assertGreaterEqual(min(C.contrast(r["accent-text"], r["bg"]), C.contrast(r["accent-text"], r["surface"])), 4.5)
        self.assertEqual(self.custom("website", "#000000")["roles"]["dark"]["accent-text"],
                         self.custom("website", "#2A2A2A")["roles"]["dark"]["accent-text"])
        self.assertEqual(self.custom("website", "#FFFFFF")["roles"]["light"]["accent-text"],
                         self.custom("website", "#F5F5F5")["roles"]["light"]["accent-text"])
        white = self.custom("website", "#FFFFFF")
        self.assertEqual([(c["key"], c["mode"]) for c in white["changes"]], [("accent-text-darker", "light")])
        for lang in ("de", "en"):
            tc = self.site.copy[lang]["website"]
            for k in ("change.accent-darker", "change.accent-lighter", "change.accent-text-darker", "change.accent-text-lighter",
                      "sum.light.keep-light", "sum.light.keep-dark", "sum.dark.keep-light", "sum.dark.keep-dark"):
                self.assertIn(k, tc)
            # unlösbare Fälle zeigt der Rahmen mit seinen Texten solve.unreachable und solve.mixed-sides
            self.assertNotIn("solve.mixed-sides", tc)
            self.assertIn("solve.mixed-sides", self.site.copy[lang]["frame"])
            # jede Zahl der Hinweise ist ein Platzhalter
            for k in ("change.accent-darker", "change.accent-lighter", "change.accent-text-darker"):
                self.assertNotRegex(re.sub(r"\{[^{}]*\}", "", tc[k]), r"\d")
            self.assertNotRegex(re.sub(r"\{[^{}]*\}", "", tc["change.accent-text-lighter"]).replace("4,5:1", "").replace("4.5:1", ""), r"\d")

    def test_link_color_never_changes_silently(self):
        """M-08: Weicht die Linkfarbe von ihrer Ausgangsfarbe ab (hell die eigene Farbe, dunkel der dunkle Kandidat
        oklch(L, 0,85·C, h)), steht in jedem Modus ein Änderungshinweis mit den Werten davor und danach."""
        seeds = ["oklch(0.48 0.08 215)", "oklch(0.45 0.15 265)", "oklch(0.80 0.15 85)", "#E63946", "#FFFFFF", "#000000",
                 "#111827", "#F0E442", "#2CA02C", "#808080", "#0000FF", "#FFFF00", "#7F00FF", "#00A0A0"]
        seen = 0
        for seed in seeds:
            for tone in ("neutral", "tinted", "strong"):
                p = self.custom("website", seed, tone=tone)
                L, cs, h, t, h0 = W.seed_lch(C.parse(seed)["hex"], tone)
                start = {"light": C.parse(seed)["hex"], "dark": C.oklch_to_hex(L, W.DARK_C * cs, h)}
                for mode, key in (("light", "accent-text-darker"), ("dark", "accent-text-lighter")):
                    ch = [c for c in p["changes"] if c["role"] == "accent-text" and c["mode"] == mode]
                    moved = p["roles"][mode]["accent-text"] != start[mode]
                    with self.subTest(seed=seed, tone=tone, mode=mode):
                        self.assertEqual(len(ch), 1 if moved else 0)
                        if moved:
                            self.assertEqual((ch[0]["key"], ch[0]["from"], ch[0]["to"]), (key, start[mode], p["roles"][mode]["accent-text"]))
                            self.assertGreaterEqual(ch[0]["values"]["after"], 4.5)
                            seen += mode == "dark"
        self.assertGreater(seen, 0, "kein dunkler Fall mit geänderter Linkfarbe")

    def test_rendered_notes(self):
        """Die Texte der drei Fälle lösen sich mit berechneten Zahlen auf."""
        p = self.custom("website", "#E63946")
        R = {"roles": p["roles"]}
        ch = p["changes"][0]
        html = C.render_text(self.site.copy["de"]["website"]["change." + ch["key"]],
                             X.rctx(p, ch["mode"], {"from": ch["from"], "to": ch["to"]}), "de", False)[0]
        self.assertIn(">4,16:1<", html)
        self.assertIn(">4,51:1<", html)
        self.assertTrue(R)

    def test_findings(self):
        self.assertEqual({f["id"] + "@" + str(f["mode"]) for f in self.pal("website", "petrol")["findings"]},
                         {"unsafe-surface@dark", "accent-fill-low@dark", "link-underline@light", "status-close@light"})
        # Konflikt Akzent und Fehler: Hue-Grenzen und Chroma
        fs = []
        W.conflict(0.15, 56.9, fs); W.conflict(0.15, 357.5, fs)
        self.assertEqual(len(fs), 2)
        fs = []
        W.conflict(0.15, 57.0, fs); W.conflict(0.10, 27.0, fs); W.conflict(0.2, None, fs)
        self.assertEqual(fs, [])

    def test_link_window(self):
        """Link-Fenster 4.1.13: leer bei #333333 auf Weiß, sonst Hinweis link-underline."""
        self.assertTrue(C.link_window("#333333", ["#FFFFFF"])["empty"])
        r = self.pal("website", "petrol")["roles"]["light"]
        self.assertFalse(C.link_window(r["text"], [r["bg"], r["surface"]])["empty"])

    def test_charts_option(self):
        pal = self.pal("website", "petrol")
        ok = [c["hex"] for c in self.site.datasets["okabe-ito"]["schemes"][0]["colors"] if c["name"] != "black"]
        for mode, n in (("light", 4), ("dark", 5)):
            r = pal["roles"][mode]
            charts = [r[f"chart-{i}"] for i in range(1, 6) if f"chart-{i}" in r]
            self.assertEqual(len(charts), n, mode)
            self.assertEqual(charts[0], r["accent-text"])
            self.assertTrue(all(c in ok for c in charts[1:]))
            self.assertTrue(all(C.contrast(c, r["bg"]) >= 3.0 for c in charts))
        t = self.task("website")
        for lang, word in (("de", "nur 4 Farben"), ("en", "only 4 colors")):
            ctx = self.ectx("website", pal, lang, "petrol")
            off = W.css(pal, t, ctx, lang, {"charts": False})
            on = W.css(pal, t, ctx, lang, {"charts": True})
            self.assertNotIn("--chart-", off)
            self.assertNotIn("Okabe", off)
            self.assertEqual(on.count(word), 1, "Hinweis nur im hellen Block")
            self.assertEqual(len(re.findall(r"--chart-\d", on)), 9)
            self.assertIn("Okabe", on)
            self.assertEqual(off, X.css(pal, t, ctx, lang, {"charts": False}))

    def test_agent_format_54(self):
        pal = self.pal("website", "petrol")
        t = self.task("website")
        text = W.agent(pal, t, self.ectx("website", pal, "de", "petrol"), "de", {})
        heads = [ln for ln in text.split("\n") if ln.startswith("#")]
        self.assertEqual(heads, ["# Farbsystem „Petrol“ für eine Website oder App, hell und dunkel", "## Idee", "## Tokens",
                                 "## Geprüfte Paare", "## Regeln", "## Bekannte Schwachstellen dieser Palette", "## Vermeiden",
                                 "## Prüfung im Produkt", "## Tipp"])
        weak = text.split("## Bekannte Schwachstellen dieser Palette\n", 1)[1].split("\n\n", 1)[0].split("\n")
        self.assertEqual(len(weak), 4)
        self.assertIn("Hell: Bei simulierter Rot-Grün-Schwäche (Deuteranopie) liegen die Statusfarben nur 6,0 auseinander, "
                      "am engsten Warnung und Erfolg. Okabe-Ito kommt auf 7,9. In Graustufen liegen Fehler und Erfolg 2,3 auseinander.",
                      weak[3])
        self.assertIn("- Dunkel: `--accent-text` auf `--surface-2` hat nur 4,03:1.", weak[0])
        self.assertIn("2,91:1", weak[1])
        self.assertIn("- Status, mindestens 4,5:1: danger/bg 5,23 · danger/surface 5,44 · danger/danger-subtle 4,84", text)
        self.assertIn("- Bedienelemente, mindestens 3:1: border-strong/bg 3,30 · border-strong/surface 3,43", text)
        self.assertNotIn("{", text.split("```", 2)[2].replace("{palette}", ""))

    def test_agent_idea_by_tone(self):
        t = self.task("website")
        cases = [("oklch(0.48 0.08 215)", "tinted", "Leicht getönte Neutraltöne"), ("oklch(0.48 0.08 215)", "neutral", "Neutrale Grautöne"),
                 ("oklch(0.48 0.08 215)", "strong", "Kräftig getönte Neutraltöne"), ("oklch(0.55 0 0)", "tinted", "Neutrale Grautöne")]
        for seed, tone, want in cases:
            p = self.custom("website", seed, tone=tone)
            p["input"] = {"seed": C.parse(seed)["hex"], "colors": None, "options": {"tone": tone, "m": "both"}}
            text = W.agent(p, t, self.ectx("website", p, "de"), "de", {})
            self.assertIn("## Idee\n" + want, text, (seed, tone))

    def test_agent_and_rationale_numbers(self):
        """Wie tests/test_exports.py für die generischen Renderer: jede Zahl „a/b 15,76“ aus den Tokens nachgerechnet."""
        for tid in ("website", "status"):
            t = self.task(tid)
            for p in t["presets"]:
                pal = self.pal(tid, p["id"])
                for lang in ("de", "en"):
                    ctx = self.ectx(tid, pal, lang, p["id"])
                    text = self.site.gens[tid].exports["agent"](pal, t, ctx, lang, {})
                    sep = "," if lang == "de" else "."
                    n = 0
                    for mode in pal["modes"]:
                        part = text.split(ctx["core"]["h_pairs"], 1)[1].split(ctx["core"]["h_rules"], 1)[0]
                        part = part.split("\n" + ctx["core"]["label." + mode] + "\n", 1)[1].split("\n\n", 1)[0]
                        for m in re.finditer(r"([a-z0-9-]+)/([a-z0-9-]+) (\d+" + re.escape(sep) + r"\d\d)", part):
                            self.assertEqual(m.group(3), cr(pal["roles"][mode][m.group(1)], pal["roles"][mode][m.group(2)], lang))
                            n += 1
                    self.assertEqual(n, len(pal["pairs"]) + len(pal["decorative"]))
                    self.assertNotRegex(text, r"\bNone\b|undefined|NaN|\{(pair_dist|kind|a|b|status_why)\}")
                    rat = self.site.gens[tid].exports["rationale"](pal, t, ctx, lang, {})
                    self.assertNotIn("{", rat)
                    d = next(x for x in pal["distinct"] if x["mode"] == "light")
                    self.assertIn(C.fmt_dist(d["value"], lang), rat)
                    kind = ctx["text"]["cvd." + d["kind"]]
                    if tid == "status":
                        self.assertIn(kind, rat)
                        self.assertIn(ctx["text"]["st." + d["a"]] + (" and " if lang == "en" else " und ") + ctx["text"]["st." + d["b"]], rat)
                    else:  # wie 5.6: Sichtweise in der Satzmitte, ohne Paarnamen
                        self.assertIn(kind[:1].lower() + kind[1:], rat)

    def test_rationale_sentences_56(self):
        """5.6: 4 bis 6 Sätze vor der Quellenzeile, auch mit der bedingten Konfliktregel und ohne Hinweis status-close."""
        cases = [(tid, p["id"], None) for tid in ("website", "status") for p in self.task(tid)["presets"]]
        cases += [("website", None, "#E63946"), ("status", None, "#E63946"), ("website", None, "#808080")]
        for tid, pid, seed in cases:
            t = self.task(tid)
            pal = self.pal(tid, pid) if pid else self.custom(tid, seed)
            for close in (True, False):
                p = dict(pal)
                if not close:
                    p["findings"] = [f for f in pal["findings"] if f["id"] != "status-close"]
                for lang in ("de", "en"):
                    ctx = self.ectx(tid, p, lang, pid)
                    rat = self.site.gens[tid].exports["rationale"](p, t, ctx, lang, {})
                    body = rat.split(X.presub(ctx["core"]["rationale_end"], ctx))[0]
                    n = len(re.findall(r"\.(?= [A-ZÄÖÜ])|\.$", body.strip()))
                    self.assertTrue(4 <= n <= 6, (tid, pid, seed, close, lang, n, body))
                    self.assertNotIn("{", rat)

    def test_rationale_without_close(self):
        pal = dict(self.pal("website", "petrol"))
        pal["findings"] = [f for f in pal["findings"] if f["id"] != "status-close"]
        t = self.task("website")
        rat = W.rationale(pal, t, self.ectx("website", pal, "de", "petrol"), "de", {})
        self.assertNotIn("auseinander", rat)
        self.assertNotIn("{", rat)


class TestStatus(Base):
    def test_status_light_43(self):
        r = self.pal("website", "petrol")["roles"]["light"]
        self.assertEqual([r[s] for s in ("danger", "warning", "success", "info")], ["#B6433C", "#723F00", "#007329", "#004D9A"])
        st = self.pal("status", "petrol")["roles"]["light"]
        self.assertEqual([st[s] for s in ("danger", "warning", "success", "info")], ["#B6433C", "#723F00", "#007329", "#004D9A"])

    def test_distances_43(self):
        for tid in ("website", "status"):
            d = {x["mode"]: x for x in self.pal(tid, "petrol")["distinct"]}
            self.assertEqual((C.fmt_dist(d["light"]["value"], "de"), d["light"]["a"], d["light"]["b"], d["light"]["kind"]),
                             ("6,0", "warning", "success", "deutan"))
            self.assertEqual(C.fmt_dist(d["light"]["compare"]["value"], "de"), "3,6")
            self.assertEqual((C.fmt_dist(d["dark"]["value"], "de"), d["dark"]["a"], d["dark"]["b"], d["dark"]["kind"]),
                             ("11,5", "danger", "warning", "deutan"))
            self.assertEqual(C.fmt_dist(d["dark"]["compare"]["value"], "de"), "3,3")

    def test_band_and_contrast(self):
        for tid in ("website", "status"):
            for pid, pal in self.site.palettes[tid].items():
                for mode in ("light", "dark"):
                    r = pal["roles"][mode]
                    lo, steps = W.BAND[mode]
                    for sid, hue in W.STATUS:
                        band = {C.oklch_to_hex(lo + i * 0.02, W.STATUS_C[mode], hue) for i in range(steps)}
                        self.assertIn(r[sid], band, f"{tid} {pid} {mode} {sid} liegt nicht im Band")
                        self.assertEqual(r[sid + "-subtle"], W.status_surface(mode, hue))
                        for b in ("bg", "surface", sid + "-subtle"):
                            self.assertGreaterEqual(C.contrast(r[sid], r[b]), 4.5)

    def test_optimum_bruteforce(self):
        """Unabhängige Suche ohne Abkürzung: Kein Kandidatensatz liegt weiter auseinander als das Ergebnis."""
        roles = self.pal("status", "petrol")["roles"]
        for mode in ("light", "dark"):
            r = roles[mode]
            lo, steps = W.BAND[mode]
            cands = []
            for sid, hue in W.STATUS:
                c = [C.oklch_to_hex(lo + i * 0.02, W.STATUS_C[mode], hue) for i in range(steps)]
                c = [x for x in dict.fromkeys(c) if all(C.contrast(x, b) >= 4.5 for b in (r["bg"], r["surface"], r[sid + "-subtle"]))]
                cands.append(c)
            best = max(C.min_distance(list(combo), W.KINDS3)["value"] for combo in itertools.product(*cands))
            got = C.min_distance([r[s] for s, _ in W.STATUS], W.KINDS3)["value"]
            self.assertAlmostEqual(best, got, places=9)

    def test_conflict_preset(self):
        self.assertIn("accent-error-conflict", [f["id"] for f in self.pal("status", "kraeftiges-rot")["findings"]])
        for pid in ("grau", "petrol"):
            self.assertNotIn("accent-error-conflict", [f["id"] for f in self.pal("status", pid)["findings"]])
        rule = self.site.rules["accent-error-conflict"]
        self.assertTrue(X.show_if(rule["show_if"], self.pal("status", "kraeftiges-rot")))
        self.assertFalse(X.show_if(rule["show_if"], self.pal("status", "grau")))

    def test_neutrals_from_accent(self):
        grau, petrol = self.pal("status", "grau")["roles"]["light"], self.pal("status", "petrol")["roles"]["light"]
        self.assertEqual(grau["bg"], "#FAFAFA")
        self.assertEqual(petrol["bg"], self.pal("website", "petrol")["roles"]["light"]["bg"])
        self.assertEqual(set(petrol), {"bg", "surface", "text", "danger", "danger-subtle", "warning", "warning-subtle",
                                       "success", "success-subtle", "info", "info-subtle"})

    def test_html_snippet_58(self):
        t = self.task("status")
        pal = self.pal("status", "grau")
        for lang, words in (("de", ["Fehler:", "Warnung:", "Erledigt:", "Hinweis:"]), ("en", ["Error:", "Warning:", "Done:", "Note:"])):
            h = self.site.gens["status"].exports["html"](pal, t, self.ectx("status", pal, lang, "grau"), lang, {})
            divs = re.findall(r'<div class="msg msg-([a-z]+)" role="([a-z]+)">', h)
            self.assertEqual(divs, [("danger", "alert"), ("warning", "status"), ("success", "status"), ("info", "status")])
            self.assertEqual(re.findall(r"<strong>([^<]+)</strong>", h), words)
            self.assertEqual(h.count('aria-hidden="true"'), 4)
            self.assertIn(".msg-danger{color:var(--danger);background:var(--danger-subtle);border-left:4px solid var(--danger)}", h)
            self.assertNotRegex(h.split("-->", 1)[1], r"#[0-9A-F]{6}")
            self.assertIn("?p=grau", h)


class TestFiles(unittest.TestCase):
    def test_patterns_use_declared_roles(self):
        import json
        for tid in ("website", "status"):
            t = json.loads((ROOT / "data" / "tasks" / f"{tid}.json").read_text(encoding="utf-8"))
            ids = {r["id"] for r in t["roles"]}
            for f in (f"patterns/{tid}.html", f"patterns/{tid}-mini.svg"):
                used = set(re.findall(r"var\(--d-([a-z0-9-]+)\)", (ROOT / f).read_text(encoding="utf-8")))
                self.assertTrue(used)
                self.assertEqual(used - ids, set(), f)

    def test_no_rounding_functions(self):
        for f in ("tools/gen/website.py", "tools/gen/status.py", "web/gen/website.js", "web/gen/status.js"):
            s = (ROOT / f).read_text(encoding="utf-8")
            for bad in ("round(", "toFixed(", "Math.round("):
                self.assertNotIn(bad, s, f)


if __name__ == "__main__":
    unittest.main()
