"""Generische Export-Renderer von Farbsprache (Spezifikation 5.0 bis 5.7, 7.5). Spiegel von web/export.js.

Jeder Renderer ist eine reine Funktion render(palette, task, ctx, lang, opts) und liefert einen
String oder eine Liste von Blöcken {label, text, suffix, lang}. Quelle ist immer das Palettenobjekt
(6.14). Jede Zahl kommt aus den Formatierern in tools/color.py. Abschnittstexte kommen aus ctx
(Texte der Seite), nie aus dem Renderer.

ctx: {date, url, name, task_name, core, text, rules, sources, refs, datasets, data}
  core   COPY[lang]["export"] (web/copy/core.py)
  text   COPY[lang][<task>]    (web/copy/<task>.py)
  rules  sichtbare Regelobjekte der Aufgabe in Reihenfolge (show_if bereits ausgewertet)
  data   Datendateien aus dem Aufgabenfeld data_files ({name: Inhalt}), sonst {}
Export renderers (Python mirror of web/export.js)."""
import json, math, re

from tools import color as C

FORMATS = ("css", "tailwind", "dtcg", "hex", "agent", "rationale")
EXT = {"css": "css", "tailwind": "css", "dtcg": "tokens.json", "hex": "txt", "agent": "md", "rationale": "txt",
       "html": "html", "js": "js", "scrim": "css", "values": "txt", "factsheet": "md", "prompt": "txt",
       "report": "md", "json": "json"}
MIME = {"css": "text/css", "json": "application/json", "md": "text/markdown", "txt": "text/plain",
        "js": "text/javascript", "html": "text/html", "tokens.json": "application/design-tokens+json"}
NS = "io.github.grundhofer.farbsprache"


# ---- Hilfen (auch vom Seitenrahmen genutzt)

def unesc(s):
    """Genau die fünf Entitäten, die color.esc erzeugt, in einem Durchgang zurück."""
    return re.sub(r"&(amp|lt|gt|quot|#x27);", lambda m: {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "#x27": "'"}[m.group(1)], s)


def presub(template, ctx):
    """Vor-Ersetzung der Text-Token {palette}, {task}, {date_iso}, {url} (keine Zahlen)."""
    return (template.replace("{palette}", ctx.get("name") or "").replace("{task}", ctx.get("task_name") or "")
            .replace("{date_iso}", ctx.get("date") or "").replace("{url}", ctx.get("url") or ""))


def plain(template, rctx, lang):
    """Platzhalter auflösen und als reinen Text liefern (für Exporte)."""
    out, _ = C.render_text(template, rctx, lang, True)
    return unesc(re.sub(r"<[^>]*>", "", out))


def rctx(palette, mode=None, extra=None, ctx=None):
    """Kontext für render_text aus einem Palettenobjekt; extra ergänzt Rollen im Modus (from, to)."""
    roles = {m: dict(r) for m, r in palette["roles"].items()}
    if extra and mode:
        roles[mode].update(extra)
    r = {"roles": roles, "mode": mode}
    if ctx and ctx.get("refs") is not None:
        r["refs"] = ctx["refs"]
    if ctx and ctx.get("date"):
        r["date"] = ctx["date"]
    return r


def fixed(n, d, lang):
    """Ganzzahl n als Dezimalzahl mit d Stellen (wie color._fixed)."""
    sep = "," if lang == "de" else "."
    s = str(abs(n))
    if d:
        s = s.rjust(d + 1, "0")
        s = s[:-d] + sep + s[-d:]
    return ("-" if n < 0 else "") + s


def dec(n, d):
    """Ganzzahl n mit d Nachkommastellen als JSON-Zahl ohne überflüssige Nullen: 4510, 4 → 0.451."""
    s = fixed(n, d, "en")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_threshold(x, lang):
    """Schwelle aus den Daten (4.5, 3, 7) als „4,5:1“ / „3:1“. Eingabe, kein Messwert."""
    n = math.floor(x * 100 + 0.5)
    return dec(n, 2).replace(".", "," if lang == "de" else ".") + ":1"


def ratio2(x, lang, threshold=None):
    """Kontrast ohne „:1“, abgeschnitten: 15,76."""
    return C.fmt_ratio(x, lang, threshold)[:-2]


def role_defs(task, palette, mode, opts=None):
    """Rollen der Aufgabe in Reihenfolge, soweit im Modus vorhanden und per Option eingeschlossen."""
    opts = opts or {}
    have = palette["roles"].get(mode, {})
    return [r for r in task["roles"] if r["id"] in have and (not r.get("export_option") or opts.get(r["export_option"]))]


def css_name(r):
    return r.get("css_name") or r["id"]


def css_names(task):
    """Rollen-ID → Exportname (6.3). Paare in Prompt und DTCG nennen dieselben Namen wie die Tokens."""
    return {r["id"]: css_name(r) for r in task["roles"]}


def comment_safe(s):
    return s.replace("*/", "* /")


def mode_word(ctx, mode):
    return ctx["core"].get("mode." + mode, mode)


def _show_value(cond, palette, mode):
    roles = palette["roles"].get(mode, {})

    def col(x):
        if x is None:
            return None
        if x.startswith("#"):
            return C.norm_hex(x)
        return roles.get(x)
    m = cond["metric"]
    if m == "finding":
        return any(f["id"] == cond.get("a") and (f.get("mode") in (None, mode)) for f in palette.get("findings") or [])
    if m == "count":
        pre = cond.get("a") or ""
        return sum(1 for k in roles if k.startswith(pre))
    a, b = col(cond.get("a")), col(cond.get("b"))
    if a is None or b is None:
        return None
    if m == "cr":
        return C.contrast(a, b)
    if m == "dist":
        return C.distance(a, b, cond.get("kind") or "normal")
    if m == "gs":
        return C.gray_distance(a, b)
    raise ValueError(f"show_if: unbekannte Kennzahl {m!r}")


def show_if(cond, palette):
    """Bedingung einer Regel (6.5) für ein Palettenobjekt. Ohne Modus gilt sie, wenn sie in einem Modus gilt.
    metric: cr | dist | gs | count | finding. count zählt Rollen mit Präfix a; finding prüft palette.findings."""
    if not cond:
        return True
    modes = [cond["mode"]] if cond.get("mode") else list(palette["modes"])
    for mode in modes:
        v = _show_value(cond, palette, mode)
        if v is None:
            continue
        if cond["metric"] == "finding":
            if v:
                return True
            continue
        op, x = cond.get("op", ">="), cond["value"]
        if (op == "<" and v < x) or (op == ">=" and v >= x):
            return True
    return False


def blocks(x):
    """String oder Blockliste → Liste von {label, text, suffix, lang, note, ext}. note ist eine Vorlage aus COPY
    (vertrauenswürdiges HTML mit Platzhaltern 6.12), die der Rahmen außerhalb des Kopiertexts zeigt. ext ist eine eigene
    Endung des Blocks für „Als Datei speichern“ (etwa json für den Recraft-Block), sonst None."""
    if isinstance(x, str):
        return [{"label": None, "text": x, "suffix": "", "lang": None, "note": None, "ext": None}]
    out = []
    for b in x:
        out.append({"label": b.get("label"), "text": b["text"], "suffix": b.get("suffix") or "", "lang": b.get("lang"),
                    "note": b.get("note"), "ext": b.get("ext")})
    return out


def _notices(palette, ctx, task=None, opts=None):
    """Lizenzpflichtige Nennungen der benutzten Datensätze. palette.extra.datasets ist eine Liste von IDs
    (immer nennen) oder {id: [rollen]} (nur nennen, wenn eine dieser Rollen im Export steht)."""
    out = []
    spec = (palette.get("extra") or {}).get("datasets") or []
    if isinstance(spec, dict):
        inc = {r["id"] for m in palette["modes"] for r in role_defs(task, palette, m, opts)} if task else None
        ids = [d for d, rids in spec.items() if inc is None or not rids or any(x in inc for x in rids)]
    else:
        ids = list(spec)
    for ds in ids:
        t = ctx["core"].get("notice." + ds)
        if t is None:
            d = (ctx.get("datasets") or {}).get(ds) or {}
            t = d.get("required_notice") or d.get("attribution")
        if t and t not in out:
            out.append(t)
    return out


def _header(ctx, mode=None):
    key = "header_mode" if mode else "header"
    t = presub(ctx["core"][key], ctx)
    return t.replace("{mode}", mode_word(ctx, mode)) if mode else t


def header(ctx, mode=None):
    """Kopfzeile jedes Exports (5.0): „Farbsprache · {Palette} · {Aufgabe} · berechnet am {Datum}“, mit mode
    zusätzlich der Modus. Für aufgabenspezifische Renderer (Spiegel: FS.export.header)."""
    return _header(ctx, mode)


def notices(palette, ctx, task=None, opts=None):
    """Lizenzpflichtige Nennungen (5.0) der Datensätze aus palette.extra.datasets, jede einmal. Gehören in den
    Kopiertext jedes Exports, der solche Farben enthält (Spiegel: FS.export.notices)."""
    return _notices(palette, ctx, task, opts)


# ---- CSS (5.1)

def _css_body(palette, task, ctx, lang, opts):
    modes = palette["modes"]
    lines = []
    width = 0
    per = []
    for mode in modes:
        rs = role_defs(task, palette, mode, opts)
        per.append((mode, rs))
        for r in rs:
            width = max(width, len(css_name(r)) + 3)
    for i, (mode, rs) in enumerate(per):
        ind = "  " if i == 0 else "    "
        if i == 0:
            lines.append(":root {")
        else:
            lines.append(f"@media (prefers-color-scheme: {mode}) {{")
            lines.append("  :root {")
        if mode in ("light", "dark"):
            lines.append(f"{ind}color-scheme: {mode};")
        for r in rs:
            hx = palette["roles"][mode][r["id"]]
            ok = C.shortest_oklch(hx)
            use = r["use_" + lang]
            note = (ok + " · " + use) if ok else use
            lines.append(ind + ("--" + css_name(r) + ":").ljust(width + 1) + hx + "; /* " + comment_safe(note) + " */")
        lines.append("}" if i == 0 else "  }")
        if i:
            lines.append("}")
    return lines


def css(palette, task, ctx, lang, opts=None, header=True):
    lines = []
    if header:
        head = [_header(ctx), ctx["core"]["css_checked"]] + _notices(palette, ctx, task, opts) + [presub(ctx["core"]["link"], ctx)]
        lines.append("/* " + comment_safe(head[0]))
        lines += ["   " + comment_safe(x) for x in head[1:]]
        lines[-1] += " */"
    return "\n".join(lines + _css_body(palette, task, ctx, lang, opts))


# ---- Tailwind v4 (5.2)

def _stem(name):
    """Rollenfamilie für die Zeilen im Tailwind-Export: ohne on- vorn und ohne -subtle, -strong, -muted, -text,
    -light, -dark oder Ziffern hinten (danger-subtle → danger, on-accent → accent, chart-3 → chart)."""
    s = name[3:] if name.startswith("on-") else name
    while True:
        t = re.sub(r"-(subtle|strong|muted|text|light|dark|[0-9]+)$", "", s)
        if t == s:
            return s
        s = t


def _same_line(prev, r):
    """Gleiche Familie oder zwei Flächen hintereinander (bg, surface, surface-2) stehen in einer Zeile (5.2)."""
    return _stem(css_name(prev)) == _stem(css_name(r)) or (prev["kind"] == "surface" and r["kind"] == "surface")


def tailwind(palette, task, ctx, lang, opts=None):
    core = ctx["core"]
    prefix = {"surface": "bg-", "text": "text-", "ui": "border-", "decor": "border-", "data": "bg-"}
    first = role_defs(task, palette, palette["modes"][0], opts)
    ex = [prefix.get(r["kind"], "bg-") + css_name(r) for r in first if r.get("core")][:5]
    head = [_header(ctx), core["tw_line"], core["tw_line2"].replace("{examples}", ", ".join(ex))] + _notices(palette, ctx, task, opts)
    head.append(presub(core["link"], ctx))
    lines = ["/* " + comment_safe(head[0])] + ["   " + comment_safe(x) for x in head[1:]]
    lines[-1] += " */"
    lines.append('@import "tailwindcss";')
    lines.append("")
    names, seen = [], []
    for i, mode in enumerate(palette["modes"]):
        rs = role_defs(task, palette, mode, opts)
        ind = "  " if i == 0 else "    "
        if i == 0:
            lines.append(":root {")
        else:
            lines.append(f"@media (prefers-color-scheme: {mode}) {{")
            lines.append("  :root {")
        cur, last = [], None
        for r in rs:
            if cur and not _same_line(last, r):
                lines.append(ind + " ".join(cur))
                cur = []
            cur.append("--" + css_name(r) + ": " + palette["roles"][mode][r["id"]] + ";")
            last = r
            if css_name(r) not in names:
                names.append(css_name(r))
        seen.append({css_name(r) for r in rs})
        if cur:
            lines.append(ind + " ".join(cur))
        lines.append("}" if i == 0 else "  }")
        if i:
            lines.append("}")
    lines.append("")
    lines.append("@theme inline {")
    # Utilities nur für Rollen, die jeder Modus definiert (5.2): sonst färbt etwa bg-chart-5 hell nichts
    for n in names:
        if all(n in s for s in seen):
            lines.append(f"  --color-{n}: var(--{n});")
    lines.append("}")
    return "\n".join(lines)


# ---- Design-Tokens nach DTCG 2025.10 (5.3)

def _component(byte):
    return dec((2 * byte * 10000 + 255) // 510, 4)


def _js(s):
    return json.dumps(s, ensure_ascii=False)


def _ratio_json(x, threshold=None):
    """Kontrast für JSON: abgeschnitten wie fmt_ratio (auch die Schwellenregel), Punkt, ohne Endnullen."""
    s = ratio2(x, "en", threshold)
    return s.rstrip("0").rstrip(".") if "." in s else s


def _pair_obj(p, names, with_min=True):
    s = '{"fg": ' + _js(names[p["fg"]]) + ', "bg": ' + _js(names[p["bg"]]) + ', "ratio": ' + _ratio_json(p["ratio"], p["min"] if with_min else None)
    if with_min:
        s += ', "min": ' + dec(math.floor(p["min"] * 100 + 0.5), 2) + ', "criterion": ' + _js(p["criterion"])
    return s + "}"


def _list(items, ind):
    if not items:
        return "[]"
    if len(items) == 1:
        return "[" + items[0] + "]"
    return "[\n" + ",\n".join(ind + "  " + x for x in items) + "\n" + ind + "]"


def dtcg(palette, task, ctx, lang, opts=None):
    out = []
    core = ctx["core"]
    nm = css_names(task)
    for mode in palette["modes"]:
        rs = role_defs(task, palette, mode, opts)
        desc = (_header(ctx, mode) if mode in ("light", "dark") else _header(ctx)) + " · " + ctx["url"]
        width = max([len(_js(css_name(r))) + 1 for r in rs] or [0])
        toks = []
        for r in rs:
            hx = palette["roles"][mode][r["id"]]
            comp = ", ".join(_component(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
            toks.append("    " + (_js(css_name(r)) + ":").ljust(width + 1) + '{"$type": "color", "$value": {"colorSpace": "srgb", "components": ['
                        + comp + '], "alpha": 1, "hex": ' + _js(hx) + '}, "$description": ' + _js(r["use_" + lang]) + "}")
        pairs = [_pair_obj(p, nm) for p in palette.get("pairs") or [] if p["mode"] == mode]
        decor = [_pair_obj(p, nm, False) for p in palette.get("decorative") or [] if p["mode"] == mode]
        ext = ['      "standard": ' + _js(core["dtcg_standard"])]
        for n in _notices(palette, ctx, task, opts):
            ext.append('      "notice": ' + _js(n))
        ext.append('      "pairs": ' + _list(pairs, "      "))
        ext.append('      "decorative": ' + _list(decor, "      "))
        text = ("{\n  \"$description\": " + _js(desc) + ",\n  \"color\": {\n" + ",\n".join(toks) + "\n  },\n"
                "  \"$extensions\": {\n    " + _js(NS) + ": {\n" + ",\n".join(ext) + "\n    }\n  }\n}")
        suffix = "-" + mode if mode in ("light", "dark") else ""
        label = ctx["core"].get("label." + mode) if len(palette["modes"]) > 1 else None
        out.append({"label": label, "text": text, "suffix": suffix, "lang": None})
    return out


# ---- Hex-Liste (5.7)

def hex_list(palette, task, ctx, lang, opts=None):
    parts = []
    for mode in palette["modes"]:
        rs = role_defs(task, palette, mode, opts)
        width = max([len(css_name(r)) for r in rs] or [0]) + 2
        head = _header(ctx, mode) if mode in ("light", "dark") else _header(ctx)
        rows = [css_name(r).ljust(width) + palette["roles"][mode][r["id"]] + "  " + r["use_" + lang] for r in rs]
        parts.append("\n".join([head] + rows))
    tail = _notices(palette, ctx, task, opts) + [presub(ctx["core"]["link"], ctx)]
    return "\n\n".join(parts) + "\n\n" + "\n".join(tail)


hex = hex_list  # Spezifikation 7.5: FS.export.hex ↔ export.hex


# ---- Prompt für Coding-Agenten (5.4)

def _join_and(items, core):
    """Aufzählung mit core["and"] vor dem letzten Glied: „a“, „a und b“, „a, b und c“."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " " + core["and"] + " " + items[-1]


def _norm_list(shorts, core):
    """Normquellen derselben Norm zusammengefasst: „WCAG 2.2, 2.4.7“ und „WCAG 2.2, 1.4.11“ → „WCAG 2.2, 2.4.7 und 1.4.11“.
    Die Norm ist der Teil der Kurzangabe vor dem letzten „, “; verschiedene Normen trennt „; “."""
    groups, order = {}, []
    for s in shorts:
        head, sep, tail = s.rpartition(", ")
        key = (head, True) if sep else (s, False)
        if key not in groups:
            groups[key] = []
            order.append(key)
        if sep:
            groups[key].append(tail)
    return "; ".join(k[0] + ", " + _join_and(groups[k], core) if k[1] else k[0] for k in order)


def level_note(rule, ctx, lang):
    """Klammer hinter einer Regel: (Norm: WCAG 2.2, 2.4.7 und 1.4.11; Technik G183, informativ)."""
    core, srcs = ctx["core"], ctx.get("sources") or {}

    def short(i):
        s = srcs.get(i) or {}
        return s.get("short_" + lang) or s.get("title") or i
    t = core["level." + rule["level"]]
    if rule["level"] == "norm":
        t += ": " + _norm_list([short(i) for i in rule.get("normative") or []], core)
        inf = rule.get("informative") or []
        if inf:
            t += "; " + "; ".join(short(i) + ", " + core["informative"] for i in inf)
    elif rule["level"] == "research" and rule.get("strength"):
        t += ", " + core["strength." + rule["strength"]]
    if rule.get("own"):
        t += ", " + core["own"]
    return "(" + t + ")"


def finding_text(f, palette, task, ctx, lang):
    tmpl = ctx["text"]["finding." + f["id"]]
    t = plain(presub(tmpl, ctx), rctx(palette, f.get("mode"), None, ctx), lang)
    if f.get("mode") and len(palette["modes"]) > 1:
        t = ctx["core"]["label." + f["mode"]] + ": " + t
    return t


def pair_groups(palette, task, mode):
    """Paare eines Modus gruppiert nach group (sonst Kriterium) und Schwelle; Gruppen nach Schwelle absteigend,
    bei gleicher Schwelle in der Reihenfolge des ersten Paars."""
    lines = {}
    for line in task.get("pairs") or []:
        lines.setdefault(line["fg"], []).append(line)
    groups, order = {}, []
    for p in palette.get("pairs") or []:
        if p["mode"] != mode:
            continue
        g = None
        for line in lines.get(p["fg"], []):
            if p["bg"] in line["on"] and line["rule"] == p["rule"]:
                g = line.get("group")
                break
        key = (g or p["criterion"], p["min"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    order.sort(key=lambda k: -k[1])  # strengere Schwelle zuerst, sonst Reihenfolge des Schemas (stabil)
    return [(k, groups[k]) for k in order]


def group_label(key, ctx):
    return ctx["text"].get("pairs.group." + key) or ctx["core"].get("pairs.group." + key) or key


def agent(palette, task, ctx, lang, opts=None):
    core, text = ctx["core"], ctx["text"]
    nm = css_names(task)
    out = [core["agent_intro"], "", "# " + presub(text["agent.title"], ctx), "", core["h_idea"],
           plain(presub(text["agent.idea"], ctx), rctx(palette, palette["modes"][0], None, ctx), lang), "",
           core["h_tokens"], "```css"]
    out += _css_body(palette, task, ctx, lang, opts)
    out += ["```", "", core["h_pairs"], core["agent_pairs_intro"]]
    for mode in palette["modes"]:
        out.append("")
        if len(palette["modes"]) > 1:
            out.append(core["label." + mode])
        for (key, mn), ps in pair_groups(palette, task, mode):
            items = " · ".join(f'{nm[p["fg"]]}/{nm[p["bg"]]} {ratio2(p["ratio"], lang, p["min"])}' for p in ps)
            out.append("- " + core["agent_group"].replace("{label}", group_label(key, ctx)).replace("{min}", fmt_threshold(mn, lang)) + " " + items)
        # Dekorative Paare und Hinweispaare (palette.advisory, etwa Datenfarben als Flächen) mit ihrem Wert
        for field, key in (("decorative", "agent_decor"), ("advisory", "agent_adv")):
            dec_ = [p for p in palette.get(field) or [] if p["mode"] == mode]
            if dec_:
                out.append("- " + core[key] + " " + " · ".join(f'{nm[p["fg"]]}/{nm[p["bg"]]} {ratio2(p["ratio"], lang, p.get("min"))}' for p in dec_))
    out += ["", core["agent_pairs_end"], "", core["h_rules"]]
    for r in ctx.get("rules") or []:
        out.append("- " + plain(presub(r["text_" + lang], ctx), rctx(palette, None, None, ctx), lang) + " " + level_note(r, ctx, lang))
    out += ["", core["h_weak"]]
    fs = palette.get("findings") or []
    if fs:
        out += ["- " + finding_text(f, palette, task, ctx, lang) for f in fs]
    else:
        out.append("- " + core["agent_weak_none"])
    out += ["", core["h_avoid"]]
    out += ["- " + plain(presub(x, ctx), rctx(palette, None, None, ctx), lang) for x in text["agent.avoid"]]
    out += ["", core["h_check"]]
    checks = core["agent_checks_before"] + text["agent.checks"] + core["agent_checks_after"]
    out += ["- " + plain(presub(x, ctx), rctx(palette, None, None, ctx), lang) for x in checks]
    out += ["", core["h_tip"], plain(presub(text["agent.tip"], ctx), rctx(palette, None, None, ctx), lang), "", "---"]
    src = core["agent_source_custom" if palette.get("preset") is None else "agent_source"]
    out.append(presub(src, ctx))
    out += _notices(palette, ctx, task, opts)
    return "\n".join(out)


# ---- Begründung (5.6)

def rationale(palette, task, ctx, lang, opts=None):
    parts = []
    for entry in ctx["text"]["rationale"]:
        if isinstance(entry, dict):
            if not show_if(entry.get("show_if"), palette):
                continue
            entry = entry["text"]
        parts.append(plain(presub(entry, ctx), rctx(palette, None, None, ctx), lang))
    parts.append(presub(ctx["core"]["rationale_end"], ctx))
    return " ".join(parts + _notices(palette, ctx, task, opts))


RENDERERS = {"css": css, "tailwind": tailwind, "dtcg": dtcg, "hex": hex_list, "agent": agent, "rationale": rationale}


def renderer(fmt, gen=None):
    """Aufgabenspezifische Renderer (gen.exports) gehen den generischen vor."""
    ex = getattr(gen, "exports", None) or {}
    if fmt in ex:
        return ex[fmt]
    if fmt in RENDERERS:
        return RENDERERS[fmt]
    raise KeyError(f"kein Renderer für das Format {fmt!r}")


def render(fmt, palette, task, ctx, lang, opts=None, gen=None):
    """Export eines Formats als Blockliste."""
    return blocks(renderer(fmt, gen)(palette, task, ctx, lang, opts or {}))


def filename(task_id, preset, fmt, suffix="", fmts=None, ext=None):
    """farbsprache-{task}-{preset|eigen}{suffix}.{ext} (5.0). Hat ein anderes Format aus fmts (alle Formate der
    Aufgabe) dieselbe Endung, steht das Format im Namen: farbsprache-{task}-{preset|eigen}-{fmt}{suffix}.{ext}.
    ext: eigene Endung des Blocks (blocks()[i]["ext"]), sonst die des Formats."""
    ext = ext or EXT.get(fmt, "txt")
    part = "-" + fmt if any(f != fmt and EXT.get(f, "txt") == ext for f in fmts or []) else ""
    return f"farbsprache-{task_id}-{preset or 'eigen'}{part}{suffix}.{ext}"


def mime(fmt, ext=None):
    """Medientyp zur Endung; Design-Tokens nach DTCG 2025.10 §4.1 als application/design-tokens+json."""
    ext = ext or EXT.get(fmt, "txt")
    return MIME.get(ext) or MIME.get(ext.rsplit(".", 1)[-1], "text/plain")
