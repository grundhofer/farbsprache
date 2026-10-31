#!/usr/bin/env python3
"""Tailwind-v4-Export in einer echten Tailwind-4-Installation prüfen (Opt-in, braucht Node und npm-Pakete).

    npm install --prefix /tmp/tw --no-save --ignore-scripts tailwindcss@4.3.3 @tailwindcss/cli@4.3.3
    python3 tools/tailwind_check.py /tmp/tw/node_modules/.bin/tailwindcss

Für jede Startpalette jeder Aufgabe, in beiden Sprachen und mit jeder Exportoption aus und an, schreibt das Skript den
Tailwind-Export der Python-Renderer (tools/export.py; web/export.js ist Byte für Byte gleich, tests/export.test.cjs),
eine HTML-Datei mit bg-*, text-* und border-* jeder --color-* und kompiliert beides mit der Tailwind-CLI. Geprüft wird:
Exit-Code 0 ohne Warnung, jede Klasse steht als Utility mit var(--rolle) im CSS, und :root (erster Modus) bzw.
@media (prefers-color-scheme: <modus>) setzt jede Rolle exakt auf den Hex-Wert der Palette. Bietet eine Aufgabe
Tailwind nicht an, prüft das Skript den generischen Renderer trotzdem.

Die Kern-Builds hängen davon nicht ab: tests/test_tailwind.py läuft nur mit FARBSPRACHE_TAILWIND=<Pfad zur CLI>, die
CI hat dafür einen eigenen Job. Exit-Code 1 bei jedem Fehler, 2 ohne oder mit falscher CLI.
Checks the Tailwind v4 export against a real Tailwind 4 CLI (opt-in)."""
import re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
from tools import export as X  # noqa: E402

DATE = "2026-10-31"
PROP = {"bg": "background-color", "text": "color", "border": "border-color"}


def cases(langs=("de", "en")):
    """[{key, task, preset, lang, opts, offered, modes, text, want: {modus: {name: hex}}}] für alle Startpaletten."""
    import build
    site = build.Site([build.ROOT], build.ROOT / "tests" / "out" / "unused", DATE)
    site.prepare()
    out = []
    for t in site.tasks:
        rules = [site.rules[r] for r in t["rules"]]
        offered = "tailwind" in t["exports"]["visible"] + (t["exports"].get("more") or [])
        opt_ids = [o["id"] for o in t["exports"].get("options") or []]
        variants = [{o: False for o in opt_ids}] + ([{o: True for o in opt_ids}] if opt_ids else [])
        for p in t["presets"]:
            pal = site.palettes[t["id"]][p["id"]]
            for lang in langs:
                ctx = {"date": DATE, "url": site.abs_url(lang, t["id"]) + "?p=" + p["id"], "name": pal["name_" + lang],
                       "task_name": t["name_" + lang], "core": site.copy[lang]["export"], "text": site.copy[lang][t["id"]],
                       "rules": [r for r in rules if X.show_if(r.get("show_if"), pal)], "sources": site.sources,
                       "refs": site.refs, "datasets": site.datasets, "data": site.gen_data(t)}
                for opts in variants:
                    on = [k for k, v in opts.items() if v]
                    text = (X.render("tailwind", pal, t, ctx, lang, opts, site.gens[t["id"]])[0]["text"] if offered
                            else X.tailwind(pal, t, ctx, lang, opts))
                    want = {m: {X.css_name(r): pal["roles"][m][r["id"]] for r in X.role_defs(t, pal, m, opts)}
                            for m in pal["modes"]}
                    out.append({"key": "--".join([t["id"], p["id"], lang] + on), "task": t["id"], "preset": p["id"],
                                "lang": lang, "opts": opts, "offered": offered, "modes": pal["modes"], "text": text,
                                "want": want})
    return out


def utilities(text):
    """Namen aus @theme inline (--color-x: var(--x)) und die Klassen bg-/text-/border-* dazu."""
    names = re.findall(r"--color-([a-z0-9-]+): var\(--\1\);", text.split("@theme inline {", 1)[1])
    return names, [f"{p}-{n}" for n in names for p in PROP]


def page_html(classes):
    return "<!doctype html>\n<html><body>\n" + "\n".join(f'<div class="{c}">{c}</div>' for c in classes) + "\n</body></html>\n"


def variables(css):
    """Unverschachteltes :root und :root in @media (prefers-color-scheme: x) → {None | x: {name: Wert}}.
    :root, :host in @layer theme (Tailwinds eigenes Theme) zählt nicht."""
    out = {}
    for m in re.finditer(r"(?:^|\n)(?:@media \(prefers-color-scheme: ([a-z]+)\) \{\s*)?:root \{([^}]*)\}", css):
        out.setdefault(m.group(1), {}).update(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", m.group(2)))
    return out


def verify(text, css, want, modes):
    """Fehlerliste für einen Export (text), die kompilierte Ausgabe (css) und die Palettenwerte (want)."""
    errs = []
    names, classes = utilities(text)
    if not names:
        errs.append("keine --color-* in @theme inline")
    for c in classes:
        p, n = c.split("-", 1)
        m = re.search(r"\n\s*\." + re.escape(c) + r" \{\s*([^}]*)\}", css)
        if not m:
            errs.append(f".{c} fehlt im CSS")
        elif m.group(1).strip() != f"{PROP[p]}: var(--{n});":
            errs.append(f".{c}: {m.group(1).strip()!r}")
    got = variables(css)
    extra = set(got) - {None} - set(modes[1:])
    if extra:
        errs.append(f"unerwartete Blöcke {sorted(extra)}")
    for i, mode in enumerate(modes):
        res = dict(got.get(None) or {})
        if i:
            res.update(got.get(mode) or {})
        for name, hx in want[mode].items():
            if res.get(name) != hx:
                errs.append(f"{mode}: --{name} ist {res.get(name)!r}, Palette {hx}")
        for n in names:
            if n not in want[mode]:
                errs.append(f"{mode}: Utility {n} ohne Palettenwert")
    return errs


def version(cli):
    r = subprocess.run([cli, "--help"], capture_output=True, text=True)
    m = re.search(r"tailwindcss v(\d+\.\d+\.\d+\S*)", r.stdout + r.stderr)
    return m.group(1) if m else None


def install_root(cli):
    """Ordner mit node_modules, in dem die CLI liegt: Nur darunter löst @import "tailwindcss" auf."""
    for d in Path(cli).absolute().parents:
        if d.name == "node_modules":
            return d.parent
    raise SystemExit(f"{cli} liegt nicht in einem node_modules-Ordner")


def tempdir(cli):
    return tempfile.TemporaryDirectory(prefix="farbsprache-tw-", dir=install_root(cli))


def run(cli, workdir, items=None, echo=print):
    """Kompiliert alle Fälle unter workdir und gibt die Zahl der fehlerhaften Fälle zurück."""
    ver = version(cli)
    if not ver or not ver.startswith("4."):
        raise SystemExit(f"keine Tailwind-4-CLI: {cli} meldet {ver!r}")
    echo(f"tailwindcss v{ver}")
    items = cases() if items is None else items
    bad = 0
    for c in items:
        d = Path(workdir) / c["key"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "input.css").write_text(c["text"], encoding="utf-8")
        names, classes = utilities(c["text"])
        (d / "page.html").write_text(page_html(classes), encoding="utf-8")
        r = subprocess.run([cli, "-i", "input.css", "-o", "out.css"], cwd=d, capture_output=True, text=True)
        css = (d / "out.css").read_text(encoding="utf-8") if (d / "out.css").exists() else ""
        errs = ([f"Exit {r.returncode}"] if r.returncode else []) + verify(c["text"], css, c["want"], c["modes"])
        if re.search(r"(?i)\b(warn|warning|error)\b", r.stdout + r.stderr):
            errs.append("CLI meldet: " + " | ".join(x for x in (r.stdout + r.stderr).splitlines() if x.strip()))
        n = sum(len(v) for v in c["want"].values())
        echo(f"{c['key']}: Exit {r.returncode}, {len(classes)} Klassen, {n} Werte in {'/'.join(c['modes'])}"
             f"{'' if c['offered'] else ', Format nicht angeboten'} -> {'OK' if not errs else 'FEHLER'}")
        for e in errs:
            echo("    " + e)
        bad += bool(errs)
    echo(f"{len(items) - bad} von {len(items)} Fällen OK, {len({(c['task'], c['preset']) for c in items})} Startpaletten")
    return bad


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    if len(argv) == 3:  # eigener Arbeitsordner, muss unter dem Ordner der Installation liegen
        return 1 if run(argv[1], argv[2]) else 0
    with tempdir(argv[1]) as tmp:
        return 1 if run(argv[1], tmp) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
