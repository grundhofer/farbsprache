#!/usr/bin/env python3
"""Einmaliger Import der Datensätze Paul Tol, ColorBrewer und viridis aus den Primärdateien.

    python3 -I tools/datasets.py --tol tol_colors.py --colorbrewer colorbrewer.json \\
        --colorbrewer-js colorbrewer_schemes.js --colorbrewer-license LICENSE.txt --viridis colormaps.py \\
        [--retrieved JJJJ-MM-TT] [--check]

Quellen (vorher selbst in ein leeres Verzeichnis laden, etwa mit curl):
  tol_colors.py           https://sronpersonalpages.nl/~pault/data/tol_colors.py
  colorbrewer.json        https://colorbrewer2.org/export/colorbrewer.json
  colorbrewer_schemes.js  https://colorbrewer2.org/colorbrewer_schemes.js   (nur die Etiketten blind, print, copy)
  LICENSE.txt             https://colorbrewer2.org/export/LICENSE.txt         (Pflichtsatz wörtlich)
  colormaps.py            https://raw.githubusercontent.com/BIDS/colormap/master/colormaps.py

Die Dateien sind Daten. Das Skript führt sie nie aus und importiert sie nie: Python-Literale werden als Text
herausgeschnitten und mit ast.literal_eval gelesen, JSON mit json, die JS-Datei mit regulären Ausdrücken.
Es nutzt nur die Standardbibliothek und nichts aus dem Projekt, damit es mit python3 -I läuft.
Geschrieben werden data/datasets/tol.json, colorbrewer.json und viridis.json mit machine_sha256 der gelesenen
Datei und dem Abrufdatum. Werte werden nie abgetippt. --check rechnet alles neu und vergleicht mit den
vorhandenen Dateien (Abrufdatum ausgenommen); Abweichung → Exit 1. Läuft nicht in der CI (kein Netz).
Dataset import from primary files (never executed, parsed as text)."""
import argparse, ast, datetime, hashlib, json, math, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "datasets"
CB_SCHEMES = ("Blues", "RdBu", "PuOr")          # nur diese drei
CB_IDS = {"Blues": "blues", "RdBu": "rdbu", "PuOr": "puor"}
CB_KIND = {"seq": "sequential", "div": "diverging"}
TOL_SETS = ("bright", "muted")
TOL_DROP = ("black", "pale_grey")               # nicht Teil der veröffentlichten Schemata (Fig. 1, Fig. 4)
CB_NOTICE = ("This product includes color specifications and designs developed by Cynthia Brewer "
             "(http://colorbrewer.org/).")


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def text(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def quantize(x):
    """Wie tools/color.quantize: floor(clamp(x, 0, 1) · 255 + 0.5)."""
    return int(math.floor(min(max(x, 0.0), 1.0) * 255 + 0.5))


def hex_of(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


# ---- Paul Tol (tol_colors.py, Funktion tol_cset)

def parse_tol(src):
    out = {}
    for name in TOL_SETS:
        m = re.search(r"if colorset == '" + re.escape(name) + r"':\s*cset = namedtuple\('\w+',\s*'([^']*)'\)\s*"
                      r"return cset\(([^)]*)\)", src)
        if not m:
            raise SystemExit(f"tol_colors.py: Farbsatz {name} nicht gefunden")
        fields = m.group(1).split()
        values = ast.literal_eval("(" + m.group(2) + ",)")
        if len(fields) != len(values) or not all(isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in values):
            raise SystemExit(f"tol_colors.py: Farbsatz {name} hat ungleich viele Namen und Werte")
        out[name] = [(f, v) for f, v in zip(fields, values) if f not in TOL_DROP]
    m = re.search(r"Copyright \(c\) (\d{4}), Paul Tol\s*\n\s*All rights reserved\.", src)
    if not m or "Standard 3-clause BSD" not in src:
        raise SystemExit("tol_colors.py: Copyright- oder Lizenzvermerk nicht gefunden")
    version = re.search(r"__version__ = \"([^\"]+)\"", src)
    return out, int(m.group(1)), (version.group(1) if version else None)


def tol_dataset(path, retrieved):
    sets, year, version = parse_tol(text(path))
    schemes = []
    for name in TOL_SETS:
        cols = [{"name": f.replace("_", " "), "hex": v.upper(), "origin": {"hex": v}} for f, v in sets[name]]
        schemes.append({"id": name, "interpolate": False, "colors": cols})
    return {
        "_comment": ("Paul Tol, qualitative Farbsätze bright und muted. Werte per tools/datasets.py aus tol_colors.py "
                     f"(Version {version}, Funktion tol_cset) übernommen, nicht abgetippt; Datei per machine_sha256 "
                     "festgehalten. black (in tol_colors.py an jeden Satz angehängt) und pale_grey (bei muted nur für "
                     "fehlende Daten) gehören nicht zu den Schemata der Website (Fig. 1, Fig. 4) und fehlen hier. "
                     "Namen wörtlich wie in der Quelle (grey)."),
        "id": "tol",
        "name": "Paul Tol",
        "authors": ["Paul Tol"],
        "year": year,
        "source_url": "https://sronpersonalpages.nl/~pault/",
        "machine_source": "https://sronpersonalpages.nl/~pault/data/tol_colors.py",
        "machine_sha256": sha256(path),
        "retrieved": retrieved,
        "license": "BSD-3-Clause",
        "license_note_de": ("BSD-3-Clause gilt für die Datei tol_colors.py. Für die Schemata auf seiner Website nennt Paul Tol "
                            "keine eigene Lizenz. Copyright-Vermerk und Haftungsausschluss mitführen, den Namen nicht als "
                            "Empfehlung für eigene Produkte nutzen."),
        "license_note_en": ("BSD-3-Clause applies to the file tol_colors.py. Paul Tol states no separate license for the "
                            "schemes on his website. Keep the copyright notice and the disclaimer, and do not use the name "
                            "to endorse your own products."),
        "attribution": f"Paul Tol, tol_colors.py ({year}), BSD-3-Clause",
        "required_notice": f"Copyright (c) {year}, Paul Tol. All rights reserved.",
        "reliability": "defined",
        "kind": "categorical",
        "schemes": schemes,
    }


# ---- ColorBrewer (colorbrewer.json, Etiketten aus colorbrewer_schemes.js, Pflichtsatz aus LICENSE.txt)

def _rgb(s):
    m = re.fullmatch(r"rgb\((\d{1,3}),(\d{1,3}),(\d{1,3})\)", s.replace(" ", ""))
    if not m:
        raise SystemExit(f"colorbrewer: unbekannte Farbangabe {s!r}")
    return [int(m.group(i)) for i in (1, 2, 3)]


def parse_cb_flags(src, name, classes):
    """Etiketten blind, print, copy einer Palette, je Klassenzahl. Wie colorbrewer2.org/colorbrewer.js:
    Ein Eintrag gilt für alle Klassenzahlen, sonst steht an Position n − 3 der Wert für n Klassen."""
    line = next((ln for ln in src.splitlines() if re.match(re.escape(name) + r":\s*\{", ln.strip())), None)
    if line is None:
        raise SystemExit(f"colorbrewer_schemes.js: Palette {name} nicht gefunden")
    m = re.search(r"'properties':\s*\{([^{}]*)\}", line)
    props = json.loads("{" + m.group(1).replace("'", '"') + "}")
    out = {}
    for k in ("blind", "print", "copy"):
        arr = props[k]
        out[k] = {c: (arr[0] if len(arr) == 1 else arr[int(c) - 3]) for c in classes}
    js_vals = {}
    for c, body in re.findall(r"(\d+):\s*\[([^\]]*)\]", line):
        js_vals[c] = [_rgb(x.strip().strip("'")) for x in body.split("',")]
    return out, props.get("type"), js_vals


def parse_notice(src):
    m = re.search(r'"(This product includes color\s+specifications and designs developed by Cynthia\s+Brewer\s+'
                  r'\(http://colorbrewer\.org/\)\.)"', src)
    if not m:
        raise SystemExit("LICENSE.txt: Pflichtsatz nicht gefunden")
    notice = re.sub(r"\s+", " ", m.group(1))
    if notice != CB_NOTICE:
        raise SystemExit(f"LICENSE.txt: Pflichtsatz weicht ab: {notice!r}")
    return notice


def colorbrewer_dataset(path, js_path, lic_path, retrieved):
    data = json.loads(text(path))
    js = text(js_path)
    notice = parse_notice(text(lic_path))
    schemes = []
    for name in CB_SCHEMES:
        d = data[name]
        classes = sorted((k for k in d if k.isdigit()), key=int)
        flags, js_type, js_vals = parse_cb_flags(js, name, classes)
        if CB_KIND.get(d["type"]) is None or js_type != d["type"]:
            raise SystemExit(f"colorbrewer: Typ von {name} unklar ({d.get('type')!r}, {js_type!r})")
        cls = {}
        for c in classes:
            rgbs = [_rgb(x) for x in d[c]]
            if len(rgbs) != int(c):
                raise SystemExit(f"colorbrewer: {name} {c} hat {len(rgbs)} Farben")
            if js_vals.get(c) != rgbs:
                raise SystemExit(f"colorbrewer: {name} {c} weicht zwischen colorbrewer.json und colorbrewer_schemes.js ab")
            cls[c] = [{"hex": hex_of(v), "origin": {"rgb": v}} for v in rgbs]
        schemes.append({"id": CB_IDS[name], "name": name, "kind": CB_KIND[d["type"]], "classes": cls, "flags_quoted": flags})
    return {
        "_comment": ("ColorBrewer, nur Blues, RdBu und PuOr mit allen Klassenstufen. Werte per "
                     "tools/datasets.py aus colorbrewer.json übernommen und gegen colorbrewer_schemes.js abgeglichen, nicht "
                     "abgetippt. Reihenfolge wie in der Quelle (Blues hell nach dunkel, RdBu rot nach blau, PuOr orange nach "
                     "lila). flags_quoted sind Etiketten der Website colorbrewer2.org, keine Aussage von Farbsprache. kind auf "
                     "oberster Ebene „mixed“, weil Blues sequenziell und RdBu und PuOr divergierend sind; maßgeblich ist kind je "
                     "Palette."),
        "id": "colorbrewer",
        "name": "ColorBrewer",
        "authors": ["Cynthia Brewer", "Mark Harrower"],
        "year": 2002,
        "source_url": "https://colorbrewer2.org/",
        "machine_source": "https://colorbrewer2.org/export/colorbrewer.json",
        "machine_sha256": sha256(path),
        "flags_source": "https://colorbrewer2.org/colorbrewer_schemes.js",
        "flags_sha256": sha256(js_path),
        "notice_source": "https://colorbrewer2.org/export/LICENSE.txt",
        "notice_sha256": sha256(lic_path),
        "retrieved": retrieved,
        "license": "Apache-2.0",
        "license_note_de": ("Apache-2.0-artige Lizenz, Copyright 2002 Cynthia Brewer, Mark Harrower und The Pennsylvania State "
                            "University. Der Pflichtsatz steht in jedem Export mit einer ColorBrewer-Farbe und auf der "
                            "Quellenseite. Der Name ColorBrewer darf nicht im eigenen Produktnamen stehen. Etiketten nur "
                            "als Zitat."),
        "license_note_en": ("Apache-style license, copyright 2002 Cynthia Brewer, Mark Harrower and The Pennsylvania State "
                            "University. The required notice is part of every export with a ColorBrewer color and of the "
                            "sources page. The name ColorBrewer must not appear in your own product name. Labels only as "
                            "quotes."),
        "flags_note_de": ("Etiketten der Website colorbrewer2.org je Klassenzahl, wörtlich nach deren Skript: 1 heißt "
                          "„color blind friendly“, „print friendly“ oder „photocopy friendly“, 2 heißt „possibly not …“, "
                          "0 heißt „not …“. Farbsprache hat diese Etiketten nicht geprüft."),
        "flags_note_en": ("Labels from the website colorbrewer2.org per number of classes, worded as in its script: 1 means "
                          "“color blind friendly”, “print friendly” or “photocopy friendly”, 2 means “possibly not …”, "
                          "0 means “not …”. Farbsprache has not checked these labels."),
        "attribution": "Cynthia Brewer, Mark Harrower and The Pennsylvania State University: ColorBrewer (2002)",
        "required_notice": notice,
        "reliability": "defined",
        "kind": "mixed" if len({s["kind"] for s in schemes}) > 1 else schemes[0]["kind"],
        "schemes": schemes,
    }


# ---- viridis (BIDS colormaps.py, Liste _viridis_data)

def parse_viridis(src):
    key = "_viridis_data = "
    i = src.index(key) + len(key)
    j = src.index("]]", i) + 2
    data = ast.literal_eval(src[i:j])
    if len(data) != 256 or not all(len(c) == 3 and all(isinstance(x, float) for x in c) for c in data):
        raise SystemExit("colormaps.py: _viridis_data hat nicht 256 Einträge mit je drei Zahlen")
    if "released under the CC0 license" not in src:
        raise SystemExit("colormaps.py: CC0-Vermerk nicht gefunden")
    return data


def viridis_dataset(path, retrieved):
    data = parse_viridis(text(path))
    cols = [{"hex": hex_of([quantize(x) for x in c]), "origin": {"srgb": list(c)}} for c in data]
    return {
        "_comment": ("viridis, 256 Einträge in der Reihenfolge der Quelle (dunkel nach hell). Werte per tools/datasets.py aus "
                     "_viridis_data in colormaps.py übernommen, nicht abgetippt. origin.srgb sind die kodierten sRGB-Werte "
                     "der Quelle (0 bis 1), hex ist daraus mit floor(x · 255 + 0.5) quantisiert. Gegengeprüft: alle 256 Hex "
                     "stimmen mit d3-scale-chromatic 3.1.0 überein."),
        "id": "viridis",
        "name": "viridis",
        "authors": ["Stéfan van der Walt", "Nathaniel Smith", "Eric Firing"],
        "year": 2015,
        "source_url": "https://bids.github.io/colormap/",
        "machine_source": "https://raw.githubusercontent.com/BIDS/colormap/master/colormaps.py",
        "machine_sha256": sha256(path),
        "retrieved": retrieved,
        "license": "CC0-1.0",
        "license_note_de": "CC0, gemeinfrei gewidmet. Die Autoren bitten um Nennung, verlangen sie aber nicht.",
        "license_note_en": "CC0, dedicated to the public domain. The authors ask for credit but do not require it.",
        "attribution": "Stéfan van der Walt, Nathaniel Smith, Eric Firing: viridis (2015)",
        "required_notice": None,
        "reliability": "defined",
        "kind": "sequential",
        "schemes": [{"id": "viridis", "interpolate": True, "colors": cols}],
    }


# ---- Ausgabe

def dumps(obj, ind=0):
    """JSON mit 2 Leerzeichen; Farbeinträge (Objekte mit hex) stehen je in einer Zeile."""
    pad, pad2 = "  " * ind, "  " * (ind + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        if "hex" in obj:
            return json.dumps(obj, ensure_ascii=False)
        items = [f"{pad2}{json.dumps(k, ensure_ascii=False)}: {dumps(v, ind + 1)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list):
        if not obj or not any(isinstance(x, (dict, list)) for x in obj):
            return json.dumps(obj, ensure_ascii=False)
        return "[\n" + ",\n".join(pad2 + dumps(x, ind + 1) for x in obj) + "\n" + pad + "]"
    return json.dumps(obj, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Importiert Tol, ColorBrewer und viridis nach data/datasets/.")
    ap.add_argument("--tol", required=True, help="tol_colors.py")
    ap.add_argument("--colorbrewer", required=True, help="colorbrewer.json")
    ap.add_argument("--colorbrewer-js", required=True, help="colorbrewer_schemes.js (Etiketten)")
    ap.add_argument("--colorbrewer-license", required=True, help="LICENSE.txt (Pflichtsatz)")
    ap.add_argument("--viridis", required=True, help="colormaps.py")
    ap.add_argument("--retrieved", help="Abrufdatum JJJJ-MM-TT (sonst heute)")
    ap.add_argument("--check", action="store_true", help="nur vergleichen, nichts schreiben")
    a = ap.parse_args(argv)
    retrieved = a.retrieved or datetime.date.today().isoformat()
    datetime.date.fromisoformat(retrieved)
    sets = {"tol": tol_dataset(a.tol, retrieved),
            "colorbrewer": colorbrewer_dataset(a.colorbrewer, a.colorbrewer_js, a.colorbrewer_license, retrieved),
            "viridis": viridis_dataset(a.viridis, retrieved)}
    bad = 0
    for ds_id, ds in sets.items():
        f = OUT / f"{ds_id}.json"
        if a.check:
            old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
            new = dict(ds, retrieved=old.get("retrieved") if old else ds["retrieved"])
            same = old == json.loads(dumps(new))
            bad += not same
            print(f"  {f.relative_to(ROOT)}: {'unverändert' if same else 'WEICHT AB'}")
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(dumps(ds) + "\n", encoding="utf-8")
        print(f"  {f.relative_to(ROOT)} geschrieben ({sum(len(s.get('colors') or []) + sum(len(v) for v in (s.get('classes') or {}).values()) for s in ds['schemes'])} Farben)")
    if bad:
        sys.exit(f"{bad} Datensätze weichen von der Primärdatei ab")


if __name__ == "__main__":
    main()
