"""Generator der Aufgabe Statusfarben (Spiegel von web/gen/status.js).

T2 nach Spezifikation 4.3 auf den Neutraltönen von T1 (4.2): Hintergrund, Fläche und Text aus der Akzentfarbe,
dazu Fehler, Warnung, Erfolg und Info mit eigener Meldungsfläche, optimiert wie in tools/gen/website.py. Die
Akzentfarbe selbst ist keine Rolle; sie bestimmt Tönung und Konfliktprüfung. Eigenes Format: HTML-Snippet (5.8).
"""
from tools import color as C, export as X
from tools.gen import website as W

ICONS = {
    "danger": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "warning": '<path d="M12 3 2 20h20Z"/><path d="M12 9v5"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/>',
    "success": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><circle cx="12" cy="7.5" r="1" fill="currentColor" stroke="none"/>',
}


def build(task, inp, ctx):
    o = inp["options"]
    L, cs, h, t, h0 = W.seed_lch(inp["seed"], o["tone"])
    base = W.neutrals(h, t)
    roles = {m: {k: base[m][k] for k in ("bg", "surface", "text")} for m in ("light", "dark")}
    findings = []
    distinct = W.status_colors(roles, findings)
    ev = C.evaluate(task, roles, "skip")
    W.status_findings(distinct, ctx, findings)
    W.conflict(cs, h0, findings)
    return {"task": task["id"], "preset": None, "input": inp, "name_de": None, "name_en": None,
            "modes": list(task["modes"]), "roles": roles, "pairs": ev["pairs"], "decorative": ev["decorative"],
            "distinct": distinct, "changes": [], "findings": findings, "usage": {}, "extra": {"summary": ["sum.gray"]}}


def html(palette, task, ctx, lang, opts=None):
    """HTML-Snippet (5.8): vier Meldungen mit Icon und Wort, dazu die Regeln .msg-<status>."""
    T = ctx["text"]
    head = [X.header(ctx), T["html.needs"]] + X.notices(palette, ctx, task, opts) + [X.presub(ctx["core"]["link"], ctx)]
    out = ["<!-- " + head[0]] + ["     " + x for x in head[1:]]
    out[-1] += " -->"
    out += ["<style>",
            ".msg{display:flex;gap:.5em;align-items:flex-start;padding:.75em 1em;margin:0 0 .5em}",
            ".msg svg{flex:none;width:1.25em;height:1.25em;margin-top:.1em}",
            ".msg p{margin:0}"]
    out += [f".msg-{s}{{color:var(--{s});background:var(--{s}-subtle);border-left:4px solid var(--{s})}}" for s, _ in W.STATUS]
    out.append("</style>")
    for s, _ in W.STATUS:
        out.append(f'<div class="msg msg-{s}" role="{"alert" if s == "danger" else "status"}">')
        out.append('  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                   f'stroke-linejoin="round" aria-hidden="true">{ICONS[s]}</svg>')
        out.append(f'  <p><strong>{C.esc(T["html.word." + s])}</strong> {C.esc(T["html.text." + s])}</p>')
        out.append("</div>")
    return "\n".join(out)


exports = {"html": html, "agent": W.agent, "rationale": W.rationale}
