"""Rahmen jeder Aufgabenseite: Blöcke A bis J aus Spezifikation 3.0, Kopierleiste und #task-data.

Die Aufgabenpakete liefern nur Aufgabendaten, Generator, Muster und Texte (7.4). Die dynamischen
Teile (Farbstreifen, Änderungshinweise, Rollen, Prüfbericht, Regeln, Exporte) baut web/site.js mit
denselben Funktionen neu (FS.site.render). tests/export.test.cjs vergleicht beide Ausgaben für
Startpalette 1 Byte für Byte; Änderungen hier gehören deshalb immer auch in site.js.
"""
import re

from tools import color as C, export as X

esc = C.esc
COPY_ICON = ('<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
             '<path d="M5 1h9v11H5z M2 4h2v1H3v9h8v-1h1v2H2z" fill="currentColor"/></svg>')
TOKEN = re.compile(r"\{([a-z_]+)\}")
CODE = re.compile(r"`([^`<>]+)`")
KINDS_SIM = ("normal", "gray", "deutan", "protan", "tritan")


# ---- gemeinsame Hilfen (Spiegel in site.js)

def fill(tmpl, values):
    """Ersetzt {name}-Token (ohne Doppelpunkt) in einem Durchgang; unbekannte bleiben stehen."""
    return TOKEN.sub(lambda m: values[m.group(1)] if m.group(1) in values else m.group(0), tmpl)


def label(R, key):
    """Text aus den Aufgabentexten, sonst aus dem Rahmen. Fehlt beides: KeyError (Build-Fehler)."""
    if key in R["tc"]:
        return R["tc"][key]
    return R["T"][key]


def plural(R, key, n):
    """Zählform aus dem Rahmen: key_1 für genau eins, sonst key („1 Paar“, „2 Paare“)."""
    return R["T"][key + "_1"] if n == 1 and key + "_1" in R["T"] else R["T"][key]


def in_sentence(name, lang):
    """Name mitten im englischen Satz in Sentence case („on background“). Klein wird nur ein Großbuchstabe vor einem
    Kleinbuchstaben; Abkürzungen wie CSS bleiben. Deutsch bleibt unverändert."""
    return name[0].lower() + name[1:] if lang == "en" and re.match(r"[A-Z][a-z]", name) else name


def code_spans(html):
    """Markdown-Codespannen `x` als <code> (nur auf der Seite, Exporte behalten die Backticks). Je Wort ein <code>,
    damit der Browser nur an Leerzeichen umbricht und nie mitten im Token."""
    return CODE.sub(lambda m: " ".join("<code>" + w + "</code>" for w in m.group(1).split(" ") if w), html)


def fmt_inline(R, fmt):
    """Formatname mitten im Satz, etwa im Hauptknopf („Copy fact sheet“): fmt.<fmt>.inline, sonst der Tab-Name."""
    key = "fmt." + fmt + ".inline"
    return R["tc"][key] if key in R["tc"] else R["T"][key] if key in R["T"] else label(R, "fmt." + fmt)


def role_index(task):
    return {r["id"]: r for r in task["roles"]}


def num_tag(R, tmpl, roles=None, mode=None):
    """Zahl-Platzhalter als <data>-Element; roles optional für Rollen-IDs."""
    ctx = {"refs": R["refs"]}
    if roles is not None:
        ctx["roles"], ctx["mode"] = roles, mode
    return C.render_text(tmpl, ctx, R["lang"], False)[0]


def cr_tag(R, a, b):
    return num_tag(R, "{cr:" + a + "/" + b + "}")


def mode_head(R, pal, mode):
    return f'<h3 class="mode-h">{esc(R["T"]["label." + mode])}</h3>' if len(pal["modes"]) > 1 else ""


def mode_prefix(R, pal, mode):
    return esc(R["T"]["label." + mode]) + ": " if mode and len(pal["modes"]) > 1 else ""


def render_copy(R, tmpl, pal, mode=None, extra=None):
    """Vertrauenswürdige Vorlage (COPY) mit Platzhaltern zur Palette, nicht escaped; Codespannen als <code>."""
    return code_spans(C.render_text(tmpl, X.rctx(pal, mode, extra, {"refs": R["refs"], "date": R["date"]}), R["lang"], False)[0])


# ---- Block C: Farbstreifen, Änderungshinweise, Rollen

def strips(R, pal):
    out = []
    for mode in pal["modes"]:
        cells = "".join(f'<span style="background:{pal["roles"][mode][r["id"]]}"></span>'
                        for r in R["task"]["roles"] if r.get("core") and r["id"] in pal["roles"][mode])
        out.append(f'<div class="strip" data-mode="{mode}" aria-hidden="true">{cells}</div>')
    return "".join(out)


def notes(R, pal, error=None):
    out = []
    for ch in pal.get("changes") or []:
        text = render_copy(R, label(R, "change." + ch["key"]), pal, ch["mode"], {"from": ch["from"], "to": ch["to"]})
        out.append(f'<div class="note" role="note"><p>{mode_prefix(R, pal, ch["mode"])}{text}</p></div>')
    if error:
        msg = R["tc"].get("solve." + error) or R["T"].get("solve." + error) or R["T"]["solve.error"]
        out.append(f'<div class="note" role="alert"><p>{msg}</p></div>')
    return "".join(out)


def summary(R, pal):
    """Kurzergebnis unter dem Farbstreifen: palette.extra.summary nennt Textschlüssel der Aufgabe (Liste oder einer),
    etwa für die Mindestdeckkraft. Platzhalter mit Rollen der Palette, jede Zahl berechnet."""
    keys = (pal.get("extra") or {}).get("summary") or []
    keys = [keys] if isinstance(keys, str) else keys
    return "".join(f'<p class="pal-sum">{render_copy(R, label(R, k), pal)}</p>' for k in keys)


def badge(R, pal, mode, rid):
    names = role_index(R["task"])
    for p in pal.get("pairs") or []:
        if p["mode"] == mode and p["fg"] == rid:
            key = "badge.pass" if p["pass"] else "badge.fail"
            hx = pal["roles"][mode]
            return '<span class="badge">' + fill(R["T"][key], {
                "ratio": cr_tag(R, hx[p["fg"]], hx[p["bg"]]), "bg": esc(in_sentence(names[p["bg"]]["name_" + R["lang"]], R["lang"])),
                "min": X.fmt_threshold(p["min"], R["lang"])}) + "</span>"
    # dekorative Paare, dann Hinweispaare (palette.advisory, etwa Datenfarben als Flächen): Wert ohne Urteil
    for field, key in (("decorative", "badge.decor"), ("advisory", "badge.adv")):
        for p in pal.get(field) or []:
            if p["mode"] == mode and p["fg"] == rid:
                hx = pal["roles"][mode]
                return '<span class="badge">' + fill(R["T"][key], {
                    "ratio": cr_tag(R, hx[p["fg"]], hx[p["bg"]]), "bg": esc(in_sentence(names[p["bg"]]["name_" + R["lang"]], R["lang"]))}) + "</span>"
    return ""


def role_row(R, pal, mode, r):
    lang, hx = R["lang"], pal["roles"][mode][r["id"]]
    name = esc(r["name_" + lang])
    use = (pal.get("usage") or {}).get(mode, {}).get(r["id"])
    use_html = f'<span class="use">{esc(R["T"]["usage." + use])}</span>' if use else ""
    aria = esc(fill(R["T"]["copy_hex_l"], {"name": r["name_" + lang], "value": hx}))
    return (f'<li class="role"><span class="swatch" style="background:{hx}"></span>'
            f'<span class="role-t"><b>{name}</b> <small>{esc(r["use_" + lang])}</small></span>'
            f'<code class="hex">{hx}</code>{badge(R, pal, mode, r["id"])}{use_html}'
            f'<button type="button" class="btn icon" data-copy="{hx}" aria-label="{aria}">{COPY_ICON}</button></li>')


def roles(R, pal):
    out = []
    for mode in pal["modes"]:
        have = pal["roles"][mode]
        rs = [r for r in R["task"]["roles"] if r["id"] in have]
        core = "".join(role_row(R, pal, mode, r) for r in rs if r.get("core"))
        rest = [r for r in rs if not r.get("core")]
        more = ""
        if rest:
            summ = esc(fill(R["T"]["more_roles"], {"n": C.fmt_count(len(rest), R["lang"])}))
            more = (f'<details class="more-roles"><summary>{summ}</summary><ul class="roles">'
                    + "".join(role_row(R, pal, mode, r) for r in rest) + "</ul></details>")
        out.append(f'<div class="pal-mode" data-mode="{mode}">{mode_head(R, pal, mode)}<ul class="roles">{core}</ul>{more}</div>')
    return "".join(out)


# ---- Block F: Prüfbericht

def calc_line(R, a, b):
    lang = R["lang"]
    ya, yb = C.rel_lum(a), C.rel_lum(b)
    hi, lo = (ya, yb) if ya >= yb else (yb, ya)
    return fill(R["T"]["calc"], {"a": a, "ya": C.fmt_lum(ya, lang), "b": b, "yb": C.fmt_lum(yb, lang),
                                 "hi": C.fmt_lum(hi, lang), "lo": C.fmt_lum(lo, lang), "k": X.fixed(5, 2, lang),
                                 "r": cr_tag(R, a, b)})


def pair_note(R, pal, mode, a, b):
    """Zusatz je geprüftem Paar: palette.extra.pair_note ist ein Textschlüssel der Aufgabe mit den Pseudo-Rollen
    pair-fg und pair-bg (etwa „Am Beamer: {proj:pair-fg/pair-bg/normal}“)."""
    key = (pal.get("extra") or {}).get("pair_note")
    if not key:
        return ""
    return f'<small class="pair-note">{render_copy(R, label(R, key), pal, mode, {"pair-fg": a, "pair-bg": b})}</small>'


def compare_name(R, cid):
    """Name eines Vergleichs: Text compare.<id> der Aufgabe, sonst der Name aus data/comparisons.json."""
    if "compare." + cid in R["tc"]:
        return R["tc"]["compare." + cid]
    for cmp in R["comparisons"]:
        if cmp["id"] == cid:
            return cmp["name_" + R["lang"]]
    return label(R, "compare." + cid)


def pair_label(R, p):
    names = role_index(R["task"])
    return fill(R["T"]["pair"], {"fg": "<b>" + esc(names[p["fg"]]["name_" + R["lang"]]) + "</b>",
                                 "bg": "<b>" + esc(names[p["bg"]]["name_" + R["lang"]]) + "</b>"})


def check_sum(R, pal):
    ps = pal.get("pairs") or []
    counts = {"n": len(ps), "k": sum(1 for p in ps if p["pass"])}
    words = {"pairs": plural(R, "chk.pairs", counts["n"]), "pass": plural(R, "chk.pass", counts["k"])}
    return C.render_text(fill(R["T"]["chk.summary"], words), {"counts": counts}, R["lang"], False)[0]


def check(R, pal):
    T, lang = R["T"], R["lang"]
    out = []
    for mode in pal["modes"]:
        hx = pal["roles"][mode]
        rows = []
        for p in pal.get("pairs") or []:
            if p["mode"] != mode:
                continue
            a, b = hx[p["fg"]], hx[p["bg"]]
            res = T["res.pass"] if p["pass"] else T["res.fail"]
            rows.append(f'<tr class="{"ok" if p["pass"] else "bad"}"><td data-label="{esc(T["th.pair"])}">{pair_label(R, p)} '
                        f'<code>{esc(p["fg"])}/{esc(p["bg"])}</code></td>'
                        f'<td data-label="{esc(T["th.ratio"])}">{cr_tag(R, a, b)}{pair_note(R, pal, mode, a, b)}</td>'
                        f'<td data-label="{esc(T["th.min"])}">{X.fmt_threshold(p["min"], lang)} '
                        f'<small>{esc(fill(T["crit"], {"c": p["criterion"]}))}</small></td>'
                        f'<td data-label="{esc(T["th.res"])}"><span class="res">{res}</span>'
                        f'<details class="calc"><summary>{esc(T["calc_l"])}</summary><p>{calc_line(R, a, b)}</p></details></td></tr>')
        table = ""
        if rows:
            table = (f'<table class="report"><thead><tr><th scope="col">{esc(T["th.pair"])}</th><th scope="col">{esc(T["th.ratio"])}</th>'
                     f'<th scope="col">{esc(T["th.min"])}</th><th scope="col">{esc(T["th.res"])}</th></tr></thead>'
                     f'<tbody>{"".join(rows)}</tbody></table>')
        dec_html = ""
        # „Nur dekorativ“ und „Nur als Hinweis“ (palette.advisory): Paare mit Wert, ohne Schwelle im Ergebnis.
        # Ebene unter der Modusüberschrift (h3), ohne Modus selbst h3 (keine Lücke nach dem h2 der Zusammenfassung)
        hd = "h4" if len(pal["modes"]) > 1 else "h3"
        for field, head in (("decorative", "decor_h"), ("advisory", "adv_h")):
            dec = [p for p in pal.get(field) or [] if p["mode"] == mode]
            if dec:
                items = "".join(f'<li>{pair_label(R, p)}: {cr_tag(R, hx[p["fg"]], hx[p["bg"]])}</li>' for p in dec)
                dec_html += f'<{hd}>{esc(T[head])}</{hd}><ul class="plain">{items}</ul>'
        out.append(f'<div class="chk-mode" data-mode="{mode}">{mode_head(R, pal, mode)}{table}{dec_html}</div>')
    dist = pal.get("distinct") or []
    if dist:
        names = role_index(R["task"])
        items = []
        for d in dist:
            hx = pal["roles"][d["mode"]]
            line = fill(T["distinct"], {
                "label": esc(label(R, "distinct." + d["id"])),
                "value": num_tag(R, "{dist:" + hx[d["a"]] + "/" + hx[d["b"]] + "/" + d["kind"] + "}"),
                "a": esc(in_sentence(names[d["a"]]["name_" + lang], lang)), "b": esc(in_sentence(names[d["b"]]["name_" + lang], lang)),
                "kind": esc(T["kind." + d["kind"]])})
            c = d.get("compare")
            if c:
                if c.get("a") and c.get("b") and c.get("kind"):
                    val = num_tag(R, "{dist:" + c["a"] + "/" + c["b"] + "/" + c["kind"] + "}")
                else:
                    val = num_tag(R, "{ref:" + c["id"] + "}")
                line += " " + fill(T["distinct.compare"], {"name": esc(compare_name(R, c["id"])), "value": val})
            items.append(f'<li>{mode_prefix(R, pal, d["mode"])}{line}</li>')
        refs = " · ".join(esc(cmp["name_" + lang]) + " " + num_tag(R, "{ref:" + cmp["id"] + "}") for cmp in R["comparisons"])
        out.append(f'<h3>{esc(T["distinct_h"])}</h3><ul class="plain">{"".join(items)}</ul>'
                   f'<p class="muted">{fill(T["distinct.refs"], {"list": refs})}</p>')
    fs = pal.get("findings") or []
    if fs:
        items = "".join(f'<li>{mode_prefix(R, pal, f.get("mode"))}{render_copy(R, label(R, "finding." + f["id"]), pal, f.get("mode"))}</li>'
                        for f in fs)
        out.append(f'<h3>{esc(T["findings_h"])}</h3><ul class="plain">{items}</ul>')
    nc = R["task"].get("not_checked_" + lang) or []
    out.append(f'<h3>{esc(T["not_checked_h"])}</h3><p>{esc(", ".join(nc))}</p>')
    return "".join(out)


# ---- Block G: Regeln

def level_tags(R, obj):
    T = R["T"]
    tags = [f'<span class="tag-level">{esc(T["level." + obj["level"]])}</span>']
    if obj.get("strength"):
        tags.append(f'<span class="tag-sub">{esc(T["strength." + obj["strength"]])}</span>')
    if obj.get("myth"):
        tags.append(f'<span class="tag-sub">{esc(T["myth"])}</span>')
    if obj.get("own"):
        tags.append(f'<span class="tag-sub">{esc(T["own"])}</span>')
    return " ".join(tags)


def source_links(R, obj):
    T, lang, srcs = R["T"], R["lang"], R["sources"]
    inf = obj.get("informative") or []
    first = [i for i in obj.get("normative") or []] + [i for i in obj.get("sources") or []
                                                         if i not in (obj.get("normative") or []) and i not in inf]
    parts = []
    for i in first + inf:
        s = srcs.get(i)
        if not s:
            continue
        acc = T["access." + s["access"]]
        if i in inf:
            acc = T["informative"] + ", " + acc
        # short_lang: Sprache einer unübersetzten Kurzangabe (etwa „Understanding 1.4.3“), ausgezeichnet auf der anderen Seite
        sl = f' lang="{esc(s["short_lang"])}"' if s.get("short_lang") and s["short_lang"] != lang else ""
        parts.append(f'<a href="{esc(s["url"])}" rel="noopener"{sl}>{esc(s.get("short_" + lang) or s["title"])}</a> <small>({esc(acc)})</small>')
    return f'<p class="src">{esc(T["src_l"])} ' + " · ".join(parts) + "</p>" if parts else ""


def rules(R, pal):
    """→ (Anzahl sichtbarer Regeln, HTML)."""
    items = []
    for r in R["rules"]:
        if not X.show_if(r.get("show_if"), pal):
            continue
        text = code_spans(C.render_text(r["text_" + R["lang"]], X.rctx(pal, None, None, {"refs": R["refs"], "date": R["date"]}), R["lang"], True)[0])
        items.append(f'<li class="rule" id="regel-{esc(r["id"])}" data-rule="{esc(r["id"])}"><div class="rule-h">{level_tags(R, r)}</div>'
                     f'<p>{text}</p>{source_links(R, r)}</li>')
    return len(items), f'<ul class="rules">{"".join(items)}</ul>'


def rules_sum(R, n):
    return C.render_text(R["T"]["rules.summary"], {"counts": {"n": n}}, R["lang"], False)[0]


# ---- Block D: Variablen der Muster

def demo_vars(R, pal, mode, view_vars=None, toggles=None):
    roles = dict(pal["roles"][mode])
    if view_vars:
        roles.update(view_vars(pal, mode, toggles or {}))
    return "".join(f"--d-{k}:{v};" for k, v in roles.items())


# ---- #task-data: nur, was site.js und export.js lesen (Budget 7.11; tests/export.test.cjs belegt die Gleichheit)

def _strings(o):
    """Alle Zeichenketten eines JSON-Baums (für Quellen, die eine Aufgabe direkt nennt)."""
    if isinstance(o, str):
        return {o}
    vals = o.values() if isinstance(o, dict) else o if isinstance(o, list) else ()
    return set().union(*(_strings(v) for v in vals))


def browser_rule(r, lang):
    """Regel ohne den Text der anderen Sprache."""
    other = "en" if lang == "de" else "de"
    return {k: v for k, v in r.items() if k != "text_" + other}


def browser_source(s, lang):
    """Quelle nur mit den Feldern für Quellenlinks und Agent-Prompt: Titel, URL, Zugang, Kurzangabe der Sprache, dazu
    short_lang (Sprache einer unübersetzten Kurzangabe).
    Belegte Aussage, Ungeprüftes und Herausgeber stehen auf der Quellenseite."""
    return {k: s[k] for k in ("title", "url", "access", "short_" + lang, "short_lang") if k in s}


# ---- Seite

def _controls(site, R, task, page, opts):
    lang, T = R["lang"], R["T"]
    vis, more, mctl = [], [], ""
    for ctl in task["controls"]:
        if ctl["id"] == task.get("seed_control"):
            continue  # steht bei den Startpaletten (seed_control)
        html = control_html(R, ctl, opts.get(ctl["id"]))
        if ctl["id"] == "m":
            mctl = html
        elif ctl.get("visible"):
            vis.append(html)
        else:
            more.append(html)
    more_html = (f'<details class="more-opts js-only"><summary>{esc(T["more_opts"])}</summary>'
                 f'<div class="ctl-grid">{"".join(more)}</div></details>') if more else ""
    return "".join(vis), more_html, mctl


def _value_label(R, ctl, v):
    return label(R, ctl["label_key"] + "." + str(v))


def chip_values(ctl):
    """Alle Werte eines Chip-Steuerelements, auch die aus cases (in Reihenfolge, ohne Dubletten)."""
    vals = list(ctl.get("values") or [])
    for cs in (ctl.get("cases") or {}).values():
        vals += [v for v in cs.get("values") or [] if v not in vals]
    return vals


def case_field(ctl, opts, name, default=None):
    """Feld eines Steuerelements im aktuellen Fall (cases nach by), sonst das Feld selbst (Spiegel: site.js field)."""
    cs = (ctl.get("cases") or {}).get(str(opts.get(ctl.get("by")))) if ctl.get("by") else None
    if cs and name in cs:
        return cs[name]
    return ctl.get(name, default)


def current_values(ctl, opts):
    return case_field(ctl, opts, "values") or []


def control_html(R, ctl, value):
    T = R["T"]
    cid, typ = ctl["id"], ctl["type"]
    lab = esc(label(R, ctl["label_key"]))
    if typ == "chips":
        vals = chip_values(ctl)
        chips = "".join(f'<button type="button" class="chip" data-val="{esc(v)}" aria-pressed="{"true" if v == value else "false"}"'
                        f'{"" if v in current_values(ctl, R["opts"]) else " hidden"}>{esc(_value_label(R, ctl, v))}</button>' for v in vals)
        return (f'<div class="ctl" data-ctl="{cid}" data-type="chips"><span class="ctl-label" id="ctl-{cid}-l">{lab}</span>'
                f'<div class="chips" role="group" aria-labelledby="ctl-{cid}-l">{chips}</div></div>')
    if typ == "toggle":
        return (f'<div class="ctl" data-ctl="{cid}" data-type="toggle"><button type="button" class="chip toggle" '
                f'aria-pressed="{"true" if value else "false"}">{lab}</button></div>')
    if typ == "stepper":
        return (f'<div class="ctl" data-ctl="{cid}" data-type="stepper"><label class="ctl-label" for="ctl-{cid}">{lab}</label>'
                f'<div class="stepper"><button type="button" class="btn" data-step="-1" aria-label="{esc(T["step_down"])}">−</button>'
                f'<input id="ctl-{cid}" type="number" inputmode="numeric" min="{case_field(ctl, R["opts"], "min")}" '
                f'max="{case_field(ctl, R["opts"], "max")}" step="{case_field(ctl, R["opts"], "step", 1)}" value="{value}">'
                f'<button type="button" class="btn" data-step="1" aria-label="{esc(T["step_up"])}">+</button></div></div>')
    if typ == "color":
        hx = value or ""
        return (f'<div class="ctl" data-ctl="{cid}" data-type="color"><label class="ctl-label" for="ctl-{cid}">{lab}</label>'
                f'<div class="seed-row"><input id="ctl-{cid}" class="seed-input" type="text" value="{esc(hx)}" autocapitalize="off" '
                f'autocomplete="off" spellcheck="false" enterkeyhint="done" aria-describedby="ctl-{cid}-err">'
                f'<input type="color" class="pick" value="{esc(hx or "#000000")}"{"" if hx else " data-empty"} aria-label="{esc(T["pick"])}"></div>'
                f'<p class="err" id="ctl-{cid}-err" aria-live="polite"></p></div>')
    if typ == "colors":
        vals = value or []
        n = ctl.get("max", 4)
        fields = "".join(f'<input class="seed-input" type="text" data-idx="{i}" value="{esc(vals[i] if i < len(vals) else "")}" '
                         f'aria-label="{esc(fill(T["color_n"], {"n": str(i + 1)}))}" autocapitalize="off" autocomplete="off" spellcheck="false" '
                         f'aria-describedby="ctl-{cid}-err">' for i in range(n))
        return (f'<div class="ctl" data-ctl="{cid}" data-type="colors"><span class="ctl-label">{lab}</span><div class="colors">{fields}</div>'
                f'<p class="err" id="ctl-{cid}-err" aria-live="polite"></p></div>')
    if typ == "text":
        # lang: Sprache des Inhalts (etwa englische Bildteile im Prompt), ausgezeichnet, wenn sie nicht die der Seite ist
        tl = f' lang="{esc(ctl["lang"])}"' if ctl.get("lang") and ctl["lang"] != R["lang"] else ""
        return (f'<div class="ctl" data-ctl="{cid}" data-type="text"><label class="ctl-label" for="ctl-{cid}">{lab}</label>'
                f'<input id="ctl-{cid}" type="text" maxlength="200"{tl} value="{esc(value or "")}"></div>')
    raise ValueError(f"unbekannter Steuerelementtyp {typ}")


def preset_chip(p, pressed, lang):
    note = p.get("note_" + lang)
    title = f' title="{esc(note)}"' if note else ""
    return (f'<button type="button" class="chip" data-preset="{esc(p["id"])}" aria-pressed="{"true" if pressed else "false"}"{title}>'
            f'{esc(p["name_" + lang])}</button>')


def mode_ctl(html):
    return f'<div class="js-only mode-ctl">{html}</div>' if html else ""


def seed_field(site, R, task, presets_html):
    T, tc = R["T"], R["tc"]
    lab = esc(tc.get("seed.label") or T["seed.label"])
    cross = tc.get("crossref")
    cross_html = f'<p class="crossref">{cross}</p>' if cross else ""
    return (f'<div class="ctl ctl-seed js-only"><label class="ctl-label" for="seed">{lab}</label>'
            f'<div class="seed-row"><input id="seed" class="seed-input" type="text" placeholder="#11697A" autocapitalize="off" '
            f'autocomplete="off" spellcheck="false" enterkeyhint="done" aria-describedby="seed-hint seed-err">'
            f'<label class="btn pick"><input type="color" id="seed-pick" value="#11697A"><span>{esc(T["pick"])}</span></label>'
            f'<button type="button" class="btn" data-seed-reset>{esc(T["reset"])}</button></div>'
            f'<p class="hint" id="seed-hint">{esc(T["seed.hint"])}</p><p class="err" id="seed-err" aria-live="polite"></p>'
            f'<p class="hint" id="seed-note" hidden></p>'
            f'<button type="button" class="chip last" data-last hidden></button>{cross_html}</div>{presets_html}')


def export_panels(site, R, task, pal, gen, ectx, opts):
    lang, T = R["lang"], R["T"]
    ex = task["exports"]
    fmts = list(ex["visible"]) + list(ex.get("more") or [])
    tabs = "".join(f'<button type="button" role="tab" class="tab" id="tab-{f}" data-tab="{f}" aria-controls="panel-{f}" '
                   f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=\"-1\""}>{esc(label(R, "fmt." + f))}</button>'
                   for i, f in enumerate(ex["visible"]))
    more = ""
    if ex.get("more"):
        more = (f'<div class="tabs-more"><span class="ctl-label">{esc(T["more_fmts"])}</span>'
                + "".join(f'<button type="button" role="tab" class="tab chip" id="tab-{f}" data-tab="{f}" aria-controls="panel-{f}" '
                          f'aria-selected="false" tabindex="-1">{esc(label(R, "fmt." + f))}</button>' for f in ex["more"]) + "</div>")
    opt_html = ""
    if ex.get("options"):
        opt_html = (f'<div class="chips exp-opts js-only" role="group" aria-label="{esc(T["exp_opts"])}">'
                    + "".join(f'<button type="button" class="chip" data-opt="{o["id"]}" aria-pressed="{"true" if o.get("default") else "false"}">'
                              f'{esc(label(R, "opt." + o["id"]))}</button>' for o in ex["options"]) + "</div>")
    panels = []
    for i, f in enumerate(fmts):
        bl = X.render(f, pal, task, ectx, lang, opts, gen)
        note_html = f'<div class="exp-note" id="exp-{f}-note"><!--fs:exp-{f}-note-->{export_note(R, pal, f)}<!--/fs:exp-{f}-note--></div>'
        sub = R["tc"].get("fmt." + f + ".sub") or T.get("fmt." + f + ".sub")
        sub_html = f'<p class="hint">{esc(sub)}</p>' if sub else ""
        panels.append(f'<div class="tabpanel{" on" if i == 0 else ""}" id="panel-{f}" role="tabpanel" aria-labelledby="tab-{f}" data-fmt="{f}">'
                      f'<h3 class="panel-h">{esc(label(R, "fmt." + f))}</h3>{sub_html}{note_html}'
                      f'<div class="exp-blocks" id="exp-{f}"><!--fs:exp-{f}-->{export_blocks(R, task, pal, f, bl)}<!--/fs:exp-{f}--></div></div>')
    return tabs, more, opt_html, "".join(panels)


def export_note(R, pal, fmt):
    note = R["tc"].get("fmt." + fmt + ".note") or R["T"].get("fmt." + fmt + ".note")
    return render_copy(R, note, pal) if note else ""


def block_note(R, pal, b):
    """Hinweis eines Exportblocks (b.note, Vorlage aus COPY) außerhalb des Kopiertexts, etwa je Bildmodell."""
    return f'<p class="exp-bnote">{render_copy(R, b["note"], pal)}</p>' if b.get("note") else ""


def export_blocks(R, task, pal, fmt, bl):
    T = R["T"]
    out = []
    fmts = list(task["exports"]["visible"]) + list(task["exports"].get("more") or [])
    for i, b in enumerate(bl):
        pid = f"exp-{fmt}-{i}"
        fname = X.filename(task["id"], pal.get("preset"), fmt, b["suffix"], fmts, b.get("ext"))
        lab = f'<p class="exp-label">{esc(b["label"])}</p>' if b["label"] else ""
        lang_attr = f' lang="{b["lang"]}"' if b["lang"] else ""
        out.append(f'<div class="exp-block">{lab}<pre class="code" id="{pid}" tabindex="0"{lang_attr}><code>{esc(b["text"])}</code></pre>'
                   f'<div class="exp-act"><button type="button" class="btn primary" data-copy-from="#{pid}">{esc(T["copy"])}</button>'
                   f'<button type="button" class="btn js-only" data-download="#{pid}" data-filename="{esc(fname)}" data-mime="{X.mime(fmt, b.get("ext"))}">{esc(T["download"])}</button>'
                   f'<button type="button" class="btn js-only" data-wrap="#{pid}" aria-pressed="false">{esc(T["wrap"])}</button></div>'
                   f'{block_note(R, pal, b)}</div>')
    return "".join(out)


def page(site, lang, task):
    tid = task["id"]
    page_path = site.path(lang, tid)
    T = site.copy[lang]["frame"]
    tc = site.copy[lang][tid]
    gen = site.gens[tid]
    pids = [p["id"] for p in task["presets"]]
    pal = site.palettes[tid][pids[0]]
    rule_objs = [site.rules[r] for r in task["rules"] if r in site.rules]
    # Quellen der Regeln und Quellen, die die Aufgabe direkt nennt (etwa menu_paths[].source); dieselbe Menge geht
    # an die Export-Renderer in Python und im Browser (#task-data)
    src_ids = sorted({s for r in rule_objs for s in r.get("sources", []) + r.get("normative", []) + (r.get("informative") or [])}
                     | {s for s in _strings(task) if s in site.sources})
    R = {"lang": lang, "T": T, "tc": tc, "task": task, "refs": site.refs, "date": site.date,
         "sources": {i: site.sources[i] for i in src_ids if i in site.sources}, "rules": rule_objs,
         "comparisons": site.comparisons}
    bsources = {i: browser_source(s, lang) for i, s in R["sources"].items()}
    opts = dict(pal["input"]["options"])
    R["opts"] = opts
    view = opts.get("m", "all")
    toggles = {t["id"]: t["default"] for t in task.get("pattern_toggles") or []}
    view_vars = getattr(gen, "view_vars", None)

    # Exportkontext wie im Browser
    vis_rules = [r for r in rule_objs if X.show_if(r.get("show_if"), pal)]
    ectx = {"date": site.date, "url": site.abs_url(lang, tid) + "?p=" + pids[0], "name": pal["name_" + lang],
            "task_name": task["name_" + lang], "core": site.copy[lang]["export"], "text": tc, "rules": vis_rules,
            "sources": bsources, "refs": site.refs, "datasets": site.datasets, "data": site.gen_data(task)}
    exp_opts = {o["id"]: bool(o.get("default")) for o in task["exports"].get("options") or []}

    pat = site.pattern(tid, lang)
    title = task["name_" + lang] + " – Farbsprache"
    out = [site.head(lang, page_path, title, tc.get("desc") or task["summary_" + lang], "task",
                     extra_head=pat["style"], main_class="t-" + tid)]

    # A · Kopf
    out.append(f'<section class="mast task-mast"><div class="wrap">'
               f'<nav class="crumbs" aria-label="{esc(T["crumbs_l"])}"><a href="{site.rel(page_path, site.path(lang, "home"))}">{esc(T["crumbs_home"])}</a>'
               f' / <span aria-current="page">{esc(task["name_" + lang])}</span></nav>'
               f'<h1>{tc["h1"]}</h1><p class="lede">{tc["lede"]}</p><p class="outcome outcome-d">{tc["outcome"]}</p></div></section>')

    # B · Steuerleiste
    pchips = ""
    if not task.get("preset_control"):
        pchips = (f'<div class="ctl ctl-presets js-only"><span class="ctl-label" id="presets-l">{esc(T["presets"])}</span>'
                  f'<div class="chips" role="group" aria-labelledby="presets-l">'
                  + "".join(preset_chip(p, i == 0, lang) for i, p in enumerate(task["presets"])) + "</div></div>")
    vis, more, mctl = _controls(site, R, task, page_path, opts)
    sctl = next((c for c in task["controls"] if c["id"] == task.get("seed_control")), None)
    if sctl:  # Vorschläge aus der eigenen Farbe (3.7): site.js tauscht sie gegen die Startpaletten, solange c gesetzt ist
        pchips += f'<div class="ctl-seedvar js-only" data-seed-ctl hidden>{control_html(R, sctl, opts.get(sctl["id"]))}</div>'
    crossref = tc.get("crossref")
    if crossref:
        crossref = re.sub(r"\{href:([a-z0-9-]+)\}", lambda m: site.rel(page_path, site.path(lang, m.group(1))), crossref)
        R["tc"] = dict(tc, crossref=crossref)
    out.append(f'<div id="task" data-task="{tid}" data-view="{esc(view)}">')
    out.append(f'<div class="bar task-bar"><div class="wrap bar-in">{seed_field(site, R, task, pchips)}'
               f'<div class="ctl-vis js-only">{vis}</div>{more}<div data-slot="bar" hidden></div></div></div>')
    out.append(f'<noscript><div class="wrap"><p class="note">{esc(T["noscript"])}</p></div></noscript>')

    # C · Deine Palette
    tabs, more_tabs, opt_html, panels = export_panels(site, R, task, pal, gen, ectx, exp_opts)
    primary = task["exports"]["primary"]
    main_btn = (f'<button type="button" class="btn primary" data-copy-from="#exp-{primary}-0" data-main>'
                f'{esc(fill(T["copy_fmt"], {"fmt": fmt_inline(R, primary)}))}</button>')
    out.append('<div class="wrap sheet">')
    out.append(f'<section class="blk blk-c" id="palette" aria-labelledby="pal-h"><h2 id="pal-h">{esc(T["pal_h"])}</h2>'
               f'{mode_ctl(mctl)}'
               f'<div id="pal-strip"><!--fs:pal-strip-->{strips(R, pal)}<!--/fs:pal-strip--></div>'
               f'<div class="pal-act">{main_btn}<a class="more-link" href="#pal-notes" data-pal-msg hidden></a>'
               f'<a class="more-link" href="#kopieren">{esc(T["all_fmts"])}</a></div><p class="hint pal-cmp" hidden></p>'
               f'<div id="pal-sum"><!--fs:pal-sum-->{summary(R, pal)}<!--/fs:pal-sum--></div>'
               f'<div id="pal-notes"><!--fs:pal-notes-->{notes(R, pal)}<!--/fs:pal-notes--></div>'
               f'<div id="pal-roles"><!--fs:pal-roles-->{roles(R, pal)}<!--/fs:pal-roles--></div>'
               f'<div data-slot="palette" hidden></div><p class="outcome outcome-m">{tc["outcome"]}</p></section>')

    # D · So sieht sie aus
    ptog = ""
    for tg in task.get("pattern_toggles") or []:
        ptog += (f'<div class="ctl js-only" data-toggle="{tg["id"]}"><span class="ctl-label" id="tg-{tg["id"]}-l">{esc(label(R, "toggle." + tg["id"]))}</span>'
                 f'<div class="chips" role="group" aria-labelledby="tg-{tg["id"]}-l">'
                 + "".join(f'<button type="button" class="chip" data-val="{esc(v)}" aria-pressed="{"true" if v == tg["default"] else "false"}">'
                           f'{esc(label(R, "toggle." + tg["id"] + "." + v))}</button>' for v in tg["values"]) + "</div></div>")
    sim = (f'<div class="ctl sim-chips js-only"><span class="ctl-label" id="sim-l">{esc(T["sim_l"])}</span><div class="chips" role="group" aria-labelledby="sim-l">'
           + "".join(f'<button type="button" class="chip" data-sim="{k}" aria-pressed="{"true" if k == "normal" else "false"}">{esc(T["sim." + k])}</button>'
                     for k in KINDS_SIM) + "</div></div>")
    toggles_attr = "".join(f' data-{k}="{esc(v)}"' for k, v in toggles.items())
    demos = ""
    for mode in pal["modes"]:
        lab = f'<p class="demo-label">{esc(T["label." + mode])}</p>' if len(pal["modes"]) > 1 else ""
        demos += (f'<div class="demo-col" data-mode="{mode}">{lab}<div class="demo demo-{tid}" data-demo="{mode}"{toggles_attr} '
                  f'style="{demo_vars(R, pal, mode, view_vars, toggles)}">{pat["html"]}</div></div>')
    pair_tabs = ""
    if len(pal["modes"]) > 1:
        pair_tabs = (f'<div class="demo-tabs js-only chips" role="group" aria-label="{esc(T["demo_tabs_l"])}">'
                     + "".join(f'<button type="button" class="chip" data-demo-tab="{m}" aria-pressed="{"true" if i == 0 else "false"}">{esc(T["label." + m])}</button>'
                               for i, m in enumerate(pal["modes"])) + "</div>")
    out.append(f'<section class="blk blk-d" aria-labelledby="demo-h"><div class="d-in"><h2 id="demo-h">{esc(T["demo_h"])}</h2>'
               f'<div data-slot="preview" hidden></div>{ptog}{sim}<p class="sim-note">{esc(T["sim_note"])}</p>{pair_tabs}'
               f'<div class="demos" id="demos" data-tab="{pal["modes"][0]}">{demos}</div></div></section>')

    # E · Kopieren
    out.append(f'<section class="blk blk-e" id="kopieren" aria-labelledby="kopieren-h"><h2 id="kopieren-h">{esc(T["copy_h"])}</h2>'
               f'<p class="note exp-err" hidden>{esc(T["pal_msg.exp"])}</p><div data-slot="export" hidden></div>{opt_html}<div class="tabs" role="tablist" aria-label="{esc(T["fmts_l"])}">{tabs}{more_tabs}</div>'
               f'{panels}</section>')

    # F · Geprüft
    out.append(f'<details class="blk blk-f" id="geprueft"><summary><h2><span id="chk-sum"><!--fs:chk-sum-->{check_sum(R, pal)}<!--/fs:chk-sum--></span></h2></summary>'
               f'<div id="chk"><!--fs:chk-->{check(R, pal)}<!--/fs:chk--></div></details>')

    # G · Regeln
    n_rules, rules_html = rules(R, pal)
    out.append(f'<details class="blk blk-g" id="regeln"><summary><h2><span id="rules-sum"><!--fs:rules-sum-->{rules_sum(R, n_rules)}<!--/fs:rules-sum--></span></h2></summary>'
               f'<div id="rules"><!--fs:rules-->{rules_html}<!--/fs:rules--></div></details>')

    # H · Kurz erklärt
    ex_items = []
    href_ex = site.rel(page_path, site.path(lang, "explained"))
    for eid in task["explain"]:
        e = site.explain.get(eid)
        if not e:
            continue
        body = "".join(f"<p>{C.render_text(par, {'refs': site.refs}, lang, True)[0]}</p>" for par in e["body_" + lang].split("\n\n"))
        ex_items.append(f'<details class="ex"><summary><span class="ex-t">{esc(e["title_" + lang])}</span> {level_tags(R, e)}</summary>'
                        f'<div class="prose">{body}</div><p class="ex-more"><a href="{href_ex}#{esc(eid)}">{esc(T["more_about"])}</a></p></details>')
    out.append(f'<section class="blk blk-h" aria-labelledby="ex-h"><h2 id="ex-h">{esc(T["explained_h"])}</h2>{"".join(ex_items)}</section>')
    out.append("</div>")  # .sheet

    # I · Weiter
    nxt = []
    for rid in task.get("related") or []:
        if rid not in site.task_by_id:
            continue
        t2 = site.task_by_id[rid]
        txt = tc.get("next." + rid) or fill(T["next"], {"name": t2["name_" + lang]})
        nxt.append(f'<li><a href="{site.rel(page_path, site.path(lang, rid))}" data-carry>{esc(txt)}</a></li>')
    for s in task.get("siblings") or []:
        base = site.sibling_url(s["site"])
        nxt.append(f'<li><a href="{esc(base + s["path_" + lang])}" rel="noopener">{esc(label(R, s["label_key"]))}</a></li>')
    out.append(f'<section class="wrap blk-i" aria-labelledby="next-h"><h2 id="next-h">{esc(T["next_h"])}</h2><ul class="next">{"".join(nxt)}</ul></section>')

    # J · Stand
    retrieved = max([site.sources[i]["retrieved"] for i in R["sources"]] or [site.date])
    stand = (C.render_text(T["stand_build"], {"date": site.date}, lang, False)[0] + " "
             + C.render_text(T["stand_sources"], {"date": retrieved}, lang, False)[0])
    out.append(f'<p class="wrap stand">{stand}</p>')

    # Kopierleiste (unter 1000 px, darüber solange der Hauptknopf nicht zu sehen ist) und Daten für site.js
    out.append(f'<div class="copybar js-only" id="copybar" hidden><a class="more-link bar-msg" href="#pal-notes" data-pal-msg hidden></a>'
               f'<div id="bar-strip"><!--fs:bar-strip-->{strips(R, pal)}<!--/fs:bar-strip--></div>'
               f'{main_btn.replace(" data-main", " data-main-bar")}<a class="more-link" href="#kopieren">{esc(T["fmts_short"])}</a></div>')
    out.append("</div>")  # #task
    data = {"v": 1, "lang": lang, "date": site.date, "task": {k: v for k, v in task.items() if k != "_comment"}, "first": pids[0],
            "palettes": site.palettes[tid], "frame": T, "text": R["tc"], "core": site.copy[lang]["export"],
            "rules": [browser_rule(r, lang) for r in rule_objs],
            "sources": bsources,
            "refs": site.refs, "comparisons": site.D["comparisons"],
            "datasets": {d: site.datasets[d] for d in site.task_datasets(task) if d in site.datasets},
            "data": site.gen_data(task),
            "url": site.abs_url(lang, tid), "gen": task["generator"],
            "custom_names": {l: site.copy[l]["export"]["custom_name"] for l in ("de", "en")},
            "custom_names_colors": {l: site.copy[l]["export"]["custom_name_colors"] for l in ("de", "en")},
            "adjusted_names": {l: site.copy[l]["export"]["adjusted_name"] for l in ("de", "en")}}
    if hasattr(gen, "display_name"):  # Namenshaken des Generators: Texte name.* beider Sprachen (site.js customNames)
        data["name_text"] = {l: {k: v for k, v in site.copy[l][tid].items() if k.startswith("name.")} for l in ("de", "en")}
    out.append(site.jscript(data, "task-data"))
    scripts = ["color.js", "export.js"] + [f"gen/{g}.js" for g in task.get("gen_deps") or []] + [f"gen/{task['generator']}.js", "site.js"]
    if site.has_ui(tid):
        scripts.append(f"ui/{tid}.js")
    out.append(site.foot(lang, page_path, scripts))
    return "".join(out)
