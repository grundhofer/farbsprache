#!/usr/bin/env python3
"""Schreibt tests/out/parity.json für den Paritätstest (Spezifikation 7.9).

    python3 tools/parity.py

Für jede Aufgabe (alle vorhandenen aus data/tasks/ und die Testaufgabe aus tests/fixtures/) rechnet der
Python-Generator alle Preset-Eingaben, die 60 Seeds aus tests/parity_seeds.json und je Startpalette jeden anderen
gültigen Wert eines Steuerelements (Label opt:…, eigene Zustände ohne eigene Farbe). tests/parity.test.cjs
rechnet dieselben Eingaben mit FS.gen[<aufgabe>].build und vergleicht: Hex exakt, Gleitkomma mit
Toleranz 1e-9. Eine SolveError wird als Fehlerschlüssel festgehalten; JS muss denselben Schlüssel werfen.
Hat der Generator einen Namenshaken (display_name, JS displayName), steht dessen Name je Sprache unter names.

Format (Vertrag nach P0): {"version": 1, "tasks": {id: {"site", "task", "gen_js": [Pfade], "custom_names",
"data": {name: Inhalt der Datei aus data_files}, "name_text"?: {lang: {name.*: Text}},
"cases": [{"label", "preset", "inp", "ok", "palette" | "error", "names"?}]}}}
"""
import copy, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import color as C  # noqa: E402

OUT = ROOT / "tests" / "out" / "parity.json"


def seed_input(task, seed):
    """Eigene Farbe mit den Standardoptionen der Steuerelemente (ohne Startpalette)."""
    opts = {c["id"]: c["default"] for c in task["controls"]}
    for c in task["controls"]:
        case = (c.get("cases") or {}).get(str(opts.get(c.get("by")))) if c.get("by") else None
        if case and "default" in case:
            opts[c["id"]] = case["default"]
        if c["type"] == "color" and opts.get(c["id"]):
            opts[c["id"]] = C.parse(opts[c["id"]], False)["hex"]
        if c["type"] == "colors" and opts.get(c["id"]):
            opts[c["id"]] = [C.parse(x, False)["hex"] for x in opts[c["id"]]]
    return {"seed": C.parse(seed, False)["hex"], "colors": None, "options": opts}


def _case(ctl, opts):
    cs = (ctl.get("cases") or {}).get(str(opts.get(ctl.get("by")))) if ctl.get("by") else None
    return cs or {}


def _valid(ctl, v, opts):
    cs = _case(ctl, opts)
    if ctl["type"] == "chips":
        return v in (cs.get("values") or ctl.get("values") or [])
    if ctl["type"] == "stepper":
        lo, hi, st = cs.get("min", ctl["min"]), cs.get("max", ctl["max"]), cs.get("step", ctl.get("step") or 1)
        return isinstance(v, int) and lo <= v <= hi and (v - lo) % st == 0
    return True


def option_inputs(site, task):
    """Je Startpalette jeder andere gültige Wert eines Steuerelements (chips, toggle, stepper; ohne Ansicht und
    seed_control). Folgewerte, die im neuen Fall nicht gelten, fallen auf den Standard des Falls oder der Startpalette,
    wie effectiveOptions in web/site.js. → [(Label, Eingabe)]"""
    out = []
    for p in task["presets"]:
        base = site.make_input(task, p)
        for ctl in task["controls"]:
            if ctl["id"] == "m" or ctl.get("view") or ctl["id"] == task.get("seed_control") or ctl["type"] not in ("chips", "toggle", "stepper"):
                continue
            if ctl["type"] == "chips":
                vals = list(ctl.get("values") or [])
                for cs in (ctl.get("cases") or {}).values():
                    vals += [v for v in cs.get("values") or [] if v not in vals]
            elif ctl["type"] == "toggle":
                vals = [True, False]
            else:
                cases = list((ctl.get("cases") or {}).values())
                vals = list(range(min([ctl["min"]] + [c.get("min", ctl["min"]) for c in cases]),
                                  max([ctl["max"]] + [c.get("max", ctl["max"]) for c in cases]) + 1))
            for v in vals:
                if v == base["options"][ctl["id"]]:
                    continue
                inp = copy.deepcopy(base)
                o = inp["options"]
                o[ctl["id"]] = v
                for c2 in task["controls"]:
                    if c2["type"] in ("chips", "stepper") and not _valid(c2, o[c2["id"]], o):
                        o[c2["id"]] = _case(c2, o).get("default", base["options"][c2["id"]])
                if o[ctl["id"]] == v and all(_valid(c2, o[c2["id"]], o) for c2 in task["controls"]):
                    out.append((f"opt:{p['id']}:{ctl['id']}={json.dumps(v)}", inp))
    return out


def run(site, task, preset, inp, label):
    gen = site.gens[task["id"]]
    try:
        pal = gen.build(task, copy.deepcopy(inp), site.gen_ctx(task))
        pal = build.frame_palette(task, preset, copy.deepcopy(inp), pal, site.custom_names())
        return {"label": label, "preset": preset["id"] if preset else None, "inp": inp, "ok": True, "palette": pal}
    except C.SolveError as e:
        return {"label": label, "preset": preset["id"] if preset else None, "inp": inp, "ok": False, "error": e.key}


def collect(site, label):
    seeds = json.loads((ROOT / "tests" / "parity_seeds.json").read_text(encoding="utf-8"))["seeds"]
    out = {}
    for task in site.tasks:
        cases = [run(site, task, p, site.make_input(task, p), "preset:" + p["id"]) for p in task["presets"]]
        cases += [run(site, task, None, seed_input(task, s), "seed:" + s) for s in seeds]
        cases += [run(site, task, None, inp, lab) for lab, inp in option_inputs(site, task)]
        js = [str(site.gen_js[g].relative_to(ROOT)) for g in list(task.get("gen_deps") or []) + [task["generator"]]]
        out[task["id"]] = {"site": label, "task": task, "gen_js": js, "custom_names": site.custom_names(),
                           "data": site.gen_data(task), "cases": cases}
        gen = site.gens[task["id"]]
        if hasattr(gen, "display_name"):
            text = {lang: {k: v for k, v in site.copy[lang][task["id"]].items() if k.startswith("name.")} for lang in ("de", "en")}
            out[task["id"]]["name_text"] = text
            for c in cases:
                if c["ok"] and c["label"].startswith("opt:"):
                    c["names"] = {lang: gen.display_name(c["palette"], text[lang], lang) for lang in ("de", "en")}
    return out


def main():
    date = build.build_date(None)
    tasks = {}
    for roots, label, seg in (([build.ROOT], "docs", None), ([build.ROOT, build.FIXTURES], "fixtures", build.FIXTURE_SEG)):
        site = build.Site(roots, build.ROOT / "tests" / "out" / "unused", date, allow_missing=True, seg=seg)
        try:
            site.prepare()
        except build.BuildError as e:
            for p in e.errors:
                print("  FEHLER", p, file=sys.stderr)
            sys.exit(f"{len(e.errors)} Fehler – parity.json nicht geschrieben")
        for tid, v in collect(site, label).items():
            if tid in tasks and label == "fixtures":
                continue  # echte Aufgaben nur einmal
            tasks[tid] = v
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "tasks": tasks}, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    n = sum(len(v["cases"]) for v in tasks.values())
    print(f"  {len(tasks)} Aufgaben, {n} Fälle -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
