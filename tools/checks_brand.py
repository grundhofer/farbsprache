"""Prüfungen von Paket P4 (Spezifikation 4.8.1, 6.9, 6.10, 9.10), eingehängt über tools/checks.py: check(D, warn).

Vokabular: Sperrliste vollständig (darf nur wachsen), jeder Golden-Name stimmt mit dem Algorithmus, kein ausgegebener
Name enthält ein Sperrwort oder ein Wort außerhalb des festen Vokabulars (geprüft an allen Golden-Fällen und an einem
Raster über den sRGB-Würfel). Modelle: genau die fünf aus 6.9, bekannte Methode, Quelle vorhanden und mit derselben URL, Zitat mit eigener Quelle. Startsets: kein
Teal-Orange-Paar. Meldungen deutsch nach dem Muster „Kontext id: Problem (was tun)“."""
import re

BLOCKED_MIN = ("petrol", "plum", "peach", "coral", "rust", "saffron", "squash", "amber", "lime", "olive", "lemon",
               "cherry", "wine", "salmon", "mint", "sand", "chocolate", "coffee", "cream", "ivory", "gold", "silver", "sky",
               "ocean", "forest", "grass", "brick", "rose", "lavender", "mustard", "honey", "caramel", "emerald", "ruby",
               "sapphire", "jade", "turquoise", "navy", "violet", "indigo", "beige", "khaki", "charcoal", "slate", "macaroni")
MODELS = ("flux2", "ideogram3", "recraft", "midjourney", "gpt-image")
METHODS = ("hex-in-prompt", "palette-field", "api-weights", "words-only")
TEAL = ("teal", "cyan", "blue-green")
ORANGE = ("orange", "red-orange", "orange-yellow")
GRID = range(0, 256, 17)  # 16 Stufen je Kanal, 4.096 Farben


def name_problems(name, cn):
    """Sperrwörter und Wörter außerhalb des Vokabulars in einem ausgegebenen Namen."""
    out = []
    allowed = set(cn.get("allowed_words") or [])
    for w in cn.get("blocked_words") or []:
        if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", name):
            out.append(f"Sperrwort „{w}“")
    for tok in name.split(" "):
        if tok not in allowed and not all(p in allowed for p in tok.split("-")):
            out.append(f"Wort „{tok}“ steht nicht im Vokabular")
    return out


def check(D, warn):
    errs = []
    cn, models = D.get("colornames"), D.get("models")
    if cn is None and models is None:
        return errs
    from tools.gen import ai_image as A  # noqa: PLC0415  (Farbkern erst nach den generischen Prüfungen)
    if cn is not None:
        c = "data/colornames.json"
        for k in ("allowed_words", "blocked_words", "neutral_c_max", "neutral_steps", "tint", "sectors", "teal_cyan_l",
                  "substitutions", "lightness", "chroma", "lightness_words", "golden"):
            if k not in cn:
                errs.append(f"{c}: Feld {k} fehlt")
        if errs:
            return errs
        for w in BLOCKED_MIN:
            if w not in cn["blocked_words"]:
                errs.append(f"{c}: Sperrwort {w} fehlt in blocked_words (die Liste darf nur wachsen, 4.8.1)")
        for w in cn["allowed_words"]:
            if w in cn["blocked_words"]:
                errs.append(f"{c}: {w} steht in allowed_words und in blocked_words")
        if len(cn["golden"]) != 40:
            errs.append(f"{c}: golden hat {len(cn['golden'])} Einträge, verlangt sind 40 (6.10)")
        for g in cn["golden"]:
            got = A.color_name(g["hex"], cn)
            if got != g["name"]:
                errs.append(f"{c} golden {g['hex']}: Algorithmus liefert „{got}“, erwartet „{g['name']}“ (Grenze geändert? begründen)")
            errs += [f"{c} golden {g['hex']}: {p}" for p in name_problems(g["name"], cn)]
        seen = set()
        for r in GRID:
            for gr in GRID:
                for b in GRID:
                    n = A.color_name("#%02X%02X%02X" % (r, gr, b), cn)
                    if n not in seen:
                        seen.add(n)
                        errs += [f"{c}: Name „{n}“ (#%02X%02X%02X): {p}" % (r, gr, b) for p in name_problems(n, cn)]
        task = (D.get("tasks") or {}).get("ai-image")
        if task:
            from tools import color as C  # noqa: PLC0415
            for p in task.get("presets") or []:
                names = [A.color_name(C.parse(x["value"], False)["hex"], cn) for x in p.get("colors") or []]
                bases = [n.split(" ")[-1] for n in names]
                if any(b in TEAL for b in bases) and any(b in ORANGE for b in bases):
                    errs.append(f"Aufgabe ai-image Startset {p.get('id')}: kombiniert Teal und Orange (9.10, Startsets ohne dieses Paar)")
    if models is not None:
        c = "data/models.json"
        ms = models.get("models") or []
        ids = [m.get("id") for m in ms]
        if sorted(ids) != sorted(MODELS):
            errs.append(f"{c}: Modelle {ids}, verlangt sind genau {list(MODELS)} (6.9)")
        for m in ms:
            mc = f"{c} {m.get('id')}"
            for k in ("name", "vendor", "method", "note_de", "note_en", "source", "source_id", "checked"):
                if not m.get(k):
                    errs.append(f"{mc}: Feld {k} fehlt")
            if m.get("method") not in METHODS:
                errs.append(f"{mc}: method muss eines von {', '.join(METHODS)} sein")
            if not str(m.get("source", "")).startswith("https://"):
                errs.append(f"{mc}: source muss mit https:// beginnen")
            if m.get("source_id") and m["source_id"] not in D.get("sources", {}):
                errs.append(f"{mc}: Quelle {m['source_id']} gibt es nicht (data/sources/*.json)")
            elif m.get("source_id") and D["sources"][m["source_id"]].get("url") != m.get("source"):
                errs.append(f"{mc}: source weicht von der URL der Quelle {m['source_id']} ab (beide gleich setzen)")
            if m.get("quote") and m.get("quote_source_id") not in D.get("sources", {}):
                errs.append(f"{mc}: quote braucht quote_source_id mit einer Quelle aus data/sources/*.json")
            if m.get("quote") and not m.get("quote_is_vendor_claim"):
                errs.append(f"{mc}: quote nur als Herstellerangabe (quote_is_vendor_claim: true)")
            if m.get("method") == "palette-field" and not isinstance(m.get("max_colors"), int):
                errs.append(f"{mc}: palette-field braucht max_colors")
            for lang in ("de", "en"):
                if m.get("method") in ("palette-field", "api-weights") and not m.get("field_note_" + lang):
                    errs.append(f"{mc}: field_note_{lang} fehlt (Hinweis neben dem zweiten Kopierblock)")
    return errs
