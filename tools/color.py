"""Farbkern von Farbsprache: Parser, Umrechnung, Gamut-Mapping, Kontrast, Graustufen,
Simulation von Farbsehschwäche, Abstände, Formatierer, Löser, Beamer, Schleier,
Paarbewertung und Platzhalter. Rein und deterministisch; Spiegel von web/color.js.

Konstanten aus data/color-constants.json (CSS Color 4, CRD 2026-10-09, §19) und data/cvd.json
(libDaltonLens), Farbnamen aus data/css-names.json. Jede Prüfung rechnet auf dem quantisierten Hex.
Color core of Farbsprache (Python mirror of web/color.js).

Aus CSS Color 4 übernommen oder abgeleitet: Matrizen, sRGB-Übertragung, Umrechnung zwischen XYZ, OKLab und OKLCH, ΔEOK, HSL-Umrechnung, Gamut-Mapping und die Tabelle der Farbnamen
(W3C Software and Document License, Text in data/licenses/W3C-Software-and-Document-2023.txt). Relative Leuchtdichte
und Kontrast folgen WCAG 2.2 (W3C Document License, Vermerk in build.py WCAG_NOTICE):
This software includes material copied from or derived from CSS Color Module Level 4
(https://www.w3.org/TR/2026/CRD-css-color-4-20261009/). Copyright © 2026 World Wide Web Consortium.
https://www.w3.org/copyright/software-license-2023/"""
import json, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---- Konstanten

def _jload(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return json.load(f)


def load_constants():
    """Konstanten wie FS_CONST im Browser: color-constants ∪ cvd ∪ {css_names}."""
    k = dict(_jload("data/color-constants.json"))
    k.update(_jload("data/cvd.json"))
    k["css_names"] = {n: v for n, v in _jload("data/css-names.json").items() if not n.startswith("_")}
    return k


K = load_constants()


def _rat(m):
    return [[n / d for n, d in row] for row in m]


SRGB_XYZ, XYZ_SRGB, P3_XYZ = _rat(K["srgb_to_xyz"]), _rat(K["xyz_to_srgb"]), _rat(K["p3_to_xyz"])
XYZ_LMS, LMS_OK, LMS_XYZ, OK_LMS = K["xyz_to_lms"], K["lms_to_oklab"], K["lms_to_xyz"], K["oklab_to_lms"]
WCAG = K["wcag_lum"]
LIN_T, GAM_T = K["srgb_lin_threshold"], K["srgb_gam_threshold"]
JND, EPS, POWERLESS = K["jnd"], K["eps"], K["powerless_c"]
VP, VD = K["vienot1999"]["protan"], K["vienot1999"]["deutan"]
T1, T2, TN = K["brettel1997"]["tritan"]["m1"], K["brettel1997"]["tritan"]["m2"], K["brettel1997"]["tritan"]["n"]
NAMES = K["css_names"]
VERSION = K["version"]
KINDS = ("normal", "deutan", "protan", "tritan", "gray")
WORST_KINDS = ("normal", "deutan", "protan")
# Einzige feste Abstandsschwelle: unter 100 · JND (= 2) fallen zwei Farben praktisch zusammen (4.1.8)
JND_DISTANCE = 100 * JND
# Gleitkommarauschen beim Gamut-Test der Eingabe (oklch(100% 0 0) liefert 1,0000000000000004).
# Wirkt nur auf das Etikett out_of_gamut, nicht auf das Hex.
GAMUT_NOISE = 1e-9
NNBSP = "\u202f"


# ---- Grundfunktionen

def _mul(m, v):
    return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]]


def lin(c):
    """sRGB-Kanal (kodiert) → linear, gespiegelt für negative Werte (CSS Color 4 §19)."""
    a = abs(c)
    if a <= LIN_T:
        return c / 12.92
    return math.copysign(((a + 0.055) / 1.055) ** 2.4, c)


def gam(c):
    """Linearer Kanal → kodiertes sRGB, gespiegelt für negative Werte."""
    a = abs(c)
    if a > GAM_T:
        return math.copysign(1.055 * a ** (1 / 2.4) - 0.055, c)
    return 12.92 * c


def _finite(x, what="Zahl"):
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
        raise ValueError(f"{what} ist keine endliche Zahl: {x!r}")
    return x


def _clamp01(x):
    return min(1.0, max(0.0, x))


# ---- Hex und Quantisierung

_HEX6 = re.compile(r"#[0-9a-fA-F]{6}")


def norm_hex(h):
    """'#rrggbb' in beliebiger Schreibung → '#RRGGBB'. Alles andere ist ein Fehler."""
    if not isinstance(h, str) or not _HEX6.fullmatch(h):
        raise ValueError(f"kein Hex #RRGGBB: {h!r}")
    return h.upper()


def hex_to_srgb(h):
    h = norm_hex(h)
    return [int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255]


def quantize(x):
    """Die eine Quantisierung: byte = floor(clamp(x, 0, 1) · 255 + 0.5)."""
    _finite(x, "Kanal")
    return math.floor(_clamp01(x) * 255 + 0.5)


def srgb_to_hex(rgb):
    return "#%02X%02X%02X" % (quantize(rgb[0]), quantize(rgb[1]), quantize(rgb[2]))


# ---- OKLab, OKLCH, Display-P3

def srgb_to_xyz(rgb):
    return _mul(SRGB_XYZ, [lin(rgb[0]), lin(rgb[1]), lin(rgb[2])])


def xyz_to_oklab(xyz):
    lms = _mul(XYZ_LMS, xyz)
    return _mul(LMS_OK, [math.cbrt(lms[0]), math.cbrt(lms[1]), math.cbrt(lms[2])])


def oklab_to_xyz(lab):
    q = _mul(OK_LMS, lab)
    return _mul(LMS_XYZ, [q[0] * q[0] * q[0], q[1] * q[1] * q[1], q[2] * q[2] * q[2]])


def _lin_to_oklab(l):
    return xyz_to_oklab(_mul(SRGB_XYZ, l))


def srgb_to_oklab(rgb):
    return _lin_to_oklab([lin(rgb[0]), lin(rgb[1]), lin(rgb[2])])


def oklab_to_srgb(lab):
    """OKLab → kodiertes sRGB, ungeklemmt (Werte außerhalb [0, 1] = außerhalb von sRGB)."""
    l = _mul(XYZ_SRGB, oklab_to_xyz(lab))
    return [gam(l[0]), gam(l[1]), gam(l[2])]


def oklab_to_oklch(lab):
    """[L, a, b] → [L, C, h]; h in Grad auf [0, 360), None bei C ≤ 0.000004 (powerless)."""
    L, a, b = lab
    C = math.sqrt(a * a + b * b)
    h = math.atan2(b, a) * 180 / math.pi
    if h < 0:
        h += 360
    if h >= 360:
        h -= 360
    return [L, C, None if C <= POWERLESS else h]


def oklch_to_oklab(lch):
    L, C, h = lch
    if h is None or h != h:
        h = 0.0
    r = h * math.pi / 180
    return [L, C * math.cos(r), C * math.sin(r)]


def p3_to_lin_srgb(p3):
    return _mul(XYZ_SRGB, _mul(P3_XYZ, [lin(p3[0]), lin(p3[1]), lin(p3[2])]))


def p3_to_srgb(p3):
    """Display-P3 (kodiert) → kodiertes sRGB, ungeklemmt."""
    l = p3_to_lin_srgb(p3)
    return [gam(l[0]), gam(l[1]), gam(l[2])]


def p3_to_oklab(p3):
    return xyz_to_oklab(_mul(P3_XYZ, [lin(p3[0]), lin(p3[1]), lin(p3[2])]))


def delta_eok(x, y):
    """ΔEOK: euklidischer Abstand in OKLab (ohne Faktor 100)."""
    d0, d1, d2 = x[0] - y[0], x[1] - y[1], x[2] - y[2]
    return math.sqrt(d0 * d0 + d1 * d1 + d2 * d2)


def hex_to_oklch(h):
    return oklab_to_oklch(srgb_to_oklab(hex_to_srgb(h)))


# ---- Gamut-Mapping (CSS Color 4 §14.2.2, binäre Suche mit lokalem MINDE)

def _in_gamut(rgb):
    return 0.0 <= rgb[0] <= 1.0 and 0.0 <= rgb[1] <= 1.0 and 0.0 <= rgb[2] <= 1.0


def _clip(rgb):
    return [_clamp01(rgb[0]), _clamp01(rgb[1]), _clamp01(rgb[2])]


def gamut_map(L, C, h):
    """OKLCH → kodiertes sRGB in [0, 1] nach dem Pseudocode aus CSS Color 4 §14.2.2."""
    _finite(L, "L"), _finite(C, "C")
    if L >= 1:
        return [1.0, 1.0, 1.0]
    if L <= 0:
        return [0.0, 0.0, 0.0]
    origin = oklch_to_oklab([L, C, h])
    rgb = oklab_to_srgb(origin)
    if _in_gamut(rgb):
        return rgb
    clipped = _clip(rgb)
    if delta_eok(srgb_to_oklab(clipped), origin) < JND:
        return clipped
    lo, hi, lo_in = 0.0, C, True
    while hi - lo > EPS:
        ch = (lo + hi) / 2
        cur = oklch_to_oklab([L, ch, h])
        rgb = oklab_to_srgb(cur)
        if lo_in and _in_gamut(rgb):
            lo = ch
            continue
        clipped = _clip(rgb)
        e = delta_eok(srgb_to_oklab(clipped), cur)
        if e < JND:
            if JND - e < EPS:
                return clipped
            lo_in = False
            lo = ch
        else:
            hi = ch
    return clipped


def oklch_to_hex(L, C, h):
    return srgb_to_hex(gamut_map(L, C, h))


# ---- Parser (4.1.1)

_WS = "[ \t\n\r\f\v\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]"
_TRIM = re.compile(f"^{_WS}+|{_WS}+$")
_SPLIT = re.compile(f"{_WS}+")
_NUMRE = re.compile(r"[+-]?(?:[0-9]+|[0-9]*\.[0-9]+)(?:e[+-]?[0-9]+)?")
_FUNC = re.compile(r"([a-z][a-z0-9-]*)\(([^()]*)\)")
_HEXDIG = re.compile(r"[0-9a-f]+")
_HEXBARE = re.compile(r"[0-9a-f]{6}")


def _num(tok):
    return float(tok) if _NUMRE.fullmatch(tok) else None


def _pct(tok):
    return float(tok[:-1]) if tok.endswith("%") and _NUMRE.fullmatch(tok[:-1]) else None


def _hue(tok):
    """Farbton in Grad (Zahl oder 'deg'); 'turn', 'rad', 'grad' sind Fehler."""
    if tok == "none":
        return None
    for unit in ("grad", "turn", "rad"):
        if tok.endswith(unit) and _num(tok[: -len(unit)]) is not None:
            raise _ParseError("hue-unit")
    v = _num(tok[:-3]) if tok.endswith("deg") else _num(tok)
    if v is None or not math.isfinite(v):
        raise _ParseError("unknown")
    r = math.fmod(v, 360.0)
    if r < 0:
        r += 360.0
    if r >= 360.0:
        r -= 360.0
    return r


class _ParseError(Exception):
    pass


def _comp(tok, pct_scale, num_div, allow_none=True):
    """Komponente: Zahl / num_div oder Prozent / 100 · pct_scale; 'none' = 0."""
    if tok == "none" and allow_none:
        return 0.0
    v = _pct(tok)
    if v is not None:
        r = v / 100 * pct_scale
    else:
        v = _num(tok)
        if v is None:
            raise _ParseError("unknown")
        r = v / num_div
    if not math.isfinite(r):
        raise _ParseError("unknown")
    return r


def _hsl_pc(tok):
    """Sättigung oder Helligkeit in Prozent ('50%' oder modern auch '50'); 'none' = 0."""
    if tok == "none":
        return 0.0
    v = _pct(tok)
    if v is None:
        v = _num(tok)
    if v is None or not math.isfinite(v):
        raise _ParseError("unknown")
    return v


def _alpha(tok, allow_none=True):
    return _clamp01(_comp(tok, 1.0, 1.0, allow_none))


def _hsl_to_rgb(hue, sat, light):
    """CSS Color 4 §7.1 (Beispielcode); sat und light in Prozent, hue in [0, 360)."""
    sat /= 100
    light /= 100

    def f(n):
        k = (n + hue / 30) % 12
        a = sat * min(light, 1 - light)
        return light - a * max(-1, min(k - 3, 9 - k, 1))
    return [f(0), f(8), f(4)]


def _finish(source, alpha, srgb=None, lab=None, lch=None):
    if lab is None:
        lab = srgb_to_oklab(srgb) if srgb is not None else oklch_to_oklab(lch)
    if srgb is None:
        srgb = oklab_to_srgb(lab)
    oog = any(c < -GAMUT_NOISE or c > 1 + GAMUT_NOISE for c in srgb)
    if not oog:
        rgb = _clip(srgb)
        hx = srgb_to_hex(rgb)
        md = None
    else:
        L, C, h = lch if lch is not None else oklab_to_oklch(lab)
        rgb = gamut_map(L, C, h)
        hx = srgb_to_hex(rgb)
        md = 100 * delta_eok(lab, srgb_to_oklab(hex_to_srgb(hx)))
    return {"hex": hx, "srgb": rgb, "alpha": alpha, "source": source, "out_of_gamut": oog, "mapped_distance": md}


def _parse_hex(d):
    if len(d) in (3, 4):
        d = "".join(ch + ch for ch in d)
    if len(d) not in (6, 8):
        raise _ParseError("unknown")
    rgb = [int(d[0:2], 16) / 255, int(d[2:4], 16) / 255, int(d[4:6], 16) / 255]
    alpha = int(d[6:8], 16) / 255 if len(d) == 8 else 1.0
    return _finish("hex", alpha, srgb=rgb)


def _parse_func(name, inner):
    if "," in inner:
        if name not in ("rgb", "rgba", "hsl", "hsla") or "/" in inner:
            raise _ParseError("unknown")
        parts = [_TRIM.sub("", p) for p in inner.split(",")]
        if len(parts) not in (3, 4) or any(not p or _SPLIT.search(p) or p == "none" for p in parts):
            raise _ParseError("unknown")
        comps, atok, legacy = parts[:3], (parts[3] if len(parts) == 4 else None), True
    else:
        halves = inner.split("/")
        if len(halves) > 2:
            raise _ParseError("unknown")
        first = _TRIM.sub("", halves[0])
        comps = _SPLIT.split(first) if first else []
        atok = None
        if len(halves) == 2:
            atok = _TRIM.sub("", halves[1])
            if not atok or _SPLIT.search(atok):
                raise _ParseError("unknown")
        legacy = False
    alpha = 1.0 if atok is None else _alpha(atok, not legacy)
    if name in ("rgb", "rgba"):
        if len(comps) != 3:
            raise _ParseError("unknown")
        if legacy and len({c.endswith("%") for c in comps}) != 1:
            raise _ParseError("unknown")
        rgb = [_clamp01(_comp(c, 1.0, 255.0)) for c in comps]
        return _finish("rgb", alpha, srgb=rgb)
    if name in ("hsl", "hsla"):
        if len(comps) != 3:
            raise _ParseError("unknown")
        h = _hue(comps[0])
        if legacy and not (comps[1].endswith("%") and comps[2].endswith("%")):
            raise _ParseError("unknown")
        s = max(0.0, _hsl_pc(comps[1]))
        l = _hsl_pc(comps[2])
        return _finish("hsl", alpha, srgb=_hsl_to_rgb(0.0 if h is None else h, s, l))
    if name == "oklch":
        if len(comps) != 3:
            raise _ParseError("unknown")
        L = _clamp01(_comp(comps[0], 1.0, 1.0))
        C = max(0.0, _comp(comps[1], 0.4, 1.0))
        h = _hue(comps[2])
        return _finish("oklch", alpha, lch=[L, C, h])
    if name == "oklab":
        if len(comps) != 3:
            raise _ParseError("unknown")
        lab = [_clamp01(_comp(comps[0], 1.0, 1.0)), _comp(comps[1], 0.4, 1.0), _comp(comps[2], 0.4, 1.0)]
        return _finish("oklab", alpha, lab=lab)
    if name == "color":
        if len(comps) != 4 or comps[0] not in ("srgb", "display-p3"):
            raise _ParseError("unknown")
        v = [_comp(c, 1.0, 1.0) for c in comps[1:]]
        if comps[0] == "srgb":
            return _finish("srgb", alpha, srgb=v)
        return _finish("display-p3", alpha, srgb=p3_to_srgb(v), lab=p3_to_oklab(v))
    raise _ParseError("unknown")


def _parse(s, bare=True):
    if not isinstance(s, str):
        return "empty" if s is None else "unknown"
    t = _TRIM.sub("", s).lower()
    if not t:
        return "empty"
    try:
        if t == "transparent":
            return "transparent"
        if t.startswith("#"):
            if not _HEXDIG.fullmatch(t[1:]):
                return "unknown"
            return _parse_hex(t[1:])
        if bare and _HEXBARE.fullmatch(t):
            return _parse_hex(t)
        if t in NAMES:
            return _finish("name", 1.0, srgb=hex_to_srgb(NAMES[t]))
        m = _FUNC.fullmatch(t)
        if m:
            return _parse_func(m.group(1), m.group(2))
        return "unknown"
    except _ParseError as e:
        return str(e)


def parse(s, bare=True):
    """Farbe aus einem String → {hex, srgb, alpha, source, out_of_gamut, mapped_distance} oder None.

    hex ist die deckende Farbe (Alpha getrennt in alpha); srgb sind die Kanäle vor der
    Quantisierung (bei out_of_gamut nach dem Gamut-Mapping). mapped_distance = ΔEOK·100
    zwischen Eingabe und dem abgebildeten Hex, sonst None. bare=False verbietet Hex ohne '#'."""
    r = _parse(s, bare)
    return r if isinstance(r, dict) else None


def parse_error(s, bare=True):
    """Fehlerschlüssel ('empty', 'transparent', 'hue-unit', 'unknown') oder None, wenn gültig."""
    r = _parse(s, bare)
    return None if isinstance(r, dict) else r


def composite(fg, alpha, bg="#FFFFFF"):
    """Mischung in kodiertem sRGB wie im Browser: c = α·f + (1 − α)·b, quantisiert."""
    f = hex_to_srgb(fg) if isinstance(fg, str) else fg
    b = hex_to_srgb(bg) if isinstance(bg, str) else bg
    return srgb_to_hex([alpha * f[i] + (1 - alpha) * b[i] for i in range(3)])


# ---- Kontrast (WCAG 2.2) und Graustufen

def _rgb(c):
    return hex_to_srgb(c) if isinstance(c, str) else c


def rel_lum(c):
    """Relative Leuchtdichte Y nach WCAG 2.2; c ist Hex oder [r, g, b] kodiert in [0, 1]."""
    r, g, b = _rgb(c)
    return WCAG[0] * lin(r) + WCAG[1] * lin(g) + WCAG[2] * lin(b)


def contrast(a, b):
    ya, yb = rel_lum(a), rel_lum(b)
    hi, lo = (ya, yb) if ya >= yb else (yb, ya)
    return (hi + 0.05) / (lo + 0.05)


def gray_value(c):
    """Graustufe auf der OKLab-L-Skala: ∛Y."""
    return math.cbrt(rel_lum(c))


def gray_hex(c):
    """Anzeige der Graustufe: neutrales Grau gleicher Leuchtdichte, quantize(gam(Y)) in allen Kanälen."""
    return srgb_to_hex([gam(rel_lum(c))] * 3)


def gray_distance(a, b):
    return abs(gray_value(a) - gray_value(b)) * 100


# ---- Farbsehschwäche (4.1.7) und Abstände (4.1.8)

_SIM_CACHE = {}


def _sim_lin(h, kind):
    l = [lin(c) for c in hex_to_srgb(h)]
    if kind == "normal":
        return l
    if kind == "protan":
        o = _mul(VP, l)
    elif kind == "deutan":
        o = _mul(VD, l)
    elif kind == "tritan":
        o = _mul(T1 if TN[0] * l[0] + TN[1] * l[1] + TN[2] * l[2] >= 0 else T2, l)
    elif kind == "gray":
        y = WCAG[0] * l[0] + WCAG[1] * l[1] + WCAG[2] * l[2]
        o = [y, y, y]
    else:
        raise ValueError(f"unbekannte Sichtweise: {kind!r}")
    return _clip(o)


def sim_oklab(h, kind):
    """Simulierte Farbe für Messungen: linear, geklemmt, unquantisiert → OKLab.
    'gray' liefert [∛Y, 0, 0] (eine Graustufendefinition für die ganze Seite)."""
    key = (kind, h)
    r = _SIM_CACHE.get(key)
    if r is None:
        if kind == "gray":
            r = [gray_value(h), 0.0, 0.0]
        else:
            r = _lin_to_oklab(_sim_lin(h, kind))
        if len(_SIM_CACHE) > 20000:
            _SIM_CACHE.clear()
        _SIM_CACHE[key] = r
    return list(r)


def sim_hex(h, kind):
    """Simulierte Farbe für die Anzeige: gam und Quantisierung."""
    if kind == "normal":
        return norm_hex(h)
    if kind == "gray":
        return gray_hex(h)
    l = _sim_lin(h, kind)
    return srgb_to_hex([gam(l[0]), gam(l[1]), gam(l[2])])


def distance(a, b, kind="normal"):
    """Abstand = 100 · ΔEOK der simulierten Farben; bei 'gray' der Graustufenabstand."""
    if kind == "gray":
        return gray_distance(a, b)
    return 100 * delta_eok(sim_oklab(a, kind), sim_oklab(b, kind))


def worst_distance(a, b, kinds=WORST_KINDS):
    return min(distance(a, b, k) for k in kinds)


def min_distance(colors, kinds=WORST_KINDS):
    """Kleinster Abstand über alle Paare und Sichtweisen → {value, i, j, a, b, kind} oder None (< 2 Farben).
    Ein Paar ersetzt das bisherige nur, wenn es um mehr als 1e-12 kleiner ist."""
    best = None
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            for k in kinds:
                d = distance(colors[i], colors[j], k)
                if best is None or d < best["value"] - 1e-12:
                    best = {"value": d, "i": i, "j": j, "a": norm_hex(colors[i]), "b": norm_hex(colors[j]), "kind": k}
    return best


# ---- Formatierer (4.1.9): Ausgabe immer aus Ganzzahlen gebaut

def _sep(lang):
    if lang == "de":
        return ","
    if lang == "en":
        return "."
    raise ValueError(f"unbekannte Sprache: {lang!r}")


def _fixed(n, d, lang):
    """Ganzzahl n als Dezimalzahl mit d Nachkommastellen (n = Wert · 10^d)."""
    sep = _sep(lang)
    neg = n < 0
    s = str(abs(n))
    if d:
        s = s.rjust(d + 1, "0")
        s = s[:-d] + sep + s[-d:]
    return ("-" if neg else "") + s


def fmt_ratio(x, lang, threshold=None):
    """Kontrast, abgeschnitten auf 2 Stellen: 4,4781 → '4,47:1'. Mit Schwelle nie aufgerundet über sie."""
    _finite(x)
    n = math.floor(x * 100 + 1e-9)
    if threshold is not None and x < threshold and n / 100 >= threshold:
        n = math.floor(threshold * 100 + 0.5) - 1
    return _fixed(n, 2, lang) + ":1"


def fmt_dist(x, lang):
    """Abstand, abgeschnitten auf 1 Stelle: 7,9048 → '7,9'."""
    _finite(x)
    return _fixed(math.floor(x * 10 + 1e-9), 1, lang)


def fmt_pct_up(alpha, lang):
    """Nötige Deckkraft, aufgerundet auf ganze Prozent: 0,6508 → '66 %' / '66%'."""
    _finite(alpha)
    p = math.ceil(alpha * 100 - 1e-9)
    return str(p) + (NNBSP + "%" if _sep(lang) == "," else "%")


def fmt_L(x, lang):
    """OKLCH-Helligkeit auf 3 Stellen, halb aufrunden: 0,96798 → '0,968'."""
    _finite(x)
    return _fixed(math.floor(x * 1000 + 0.5), 3, lang)


def fmt_count(n, lang):
    """Ganzzahl mit Tausenderpunkt (DE) bzw. -komma (EN)."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError(f"keine Ganzzahl: {n!r}")
    sep = "." if _sep(lang) == "," else ","
    return f"{n:,}".replace(",", sep)


def fmt_lum(y, lang="en"):
    """Leuchtdichte auf 4 Stellen, halb aufrunden (nur Rechenweg)."""
    _finite(y)
    return _fixed(math.floor(y * 10000 + 0.5), 4, lang)


# ---- Kürzeste OKLCH-Schreibweise (4.1.10)

_P10 = (1, 10, 100, 1000, 10000, 100000)


def shortest_oklch(h, max_p=3):
    """Kürzeste oklch()-Schreibweise, die über den Parser exakt auf dasselbe Hex führt, sonst None.
    Stufe p: L in Prozent mit p, C mit p + 2, h mit p Nachkommastellen. max_p < 3 nur für Tests."""
    hx = norm_hex(h)
    L, C, hue = hex_to_oklch(hx)
    for p in range(max_p + 1):
        sL = _fixed(math.floor(L * 100 * _P10[p] + 0.5), p, "en")
        if hue is None:
            s = f"oklch({sL}% 0 0)"
        else:
            sC = _fixed(math.floor(C * _P10[p + 2] + 0.5), p + 2, "en")
            nh = math.floor(hue * _P10[p] + 0.5)
            if nh >= 360 * _P10[p]:
                nh -= 360 * _P10[p]
            s = f"oklch({sL}% {sC} {_fixed(nh, p, 'en')})"
        r = parse(s)
        if r is not None and r["hex"] == hx:
            return s
    return None


# ---- L-Löser (4.1.11)

class SolveError(Exception):
    """Löser ohne Ergebnis: key 'mixed-sides' oder 'unreachable', values mit Details."""

    def __init__(self, key, values=None):
        super().__init__(key)
        self.key = key
        self.values = values or {}


def _fmin(hx, against):
    return min(contrast(hx, b) for b in against)


def solve_l(C, h, against, target, direction, L0):
    """Kleinste L-Änderung ab L0 in Richtung direction (−1 dunkler, +1 heller), bis das
    quantisierte Hex gegen alle Flächen in against ≥ target erreicht.
    → {hex, L, C, changed, ratio, distance}; sonst SolveError."""
    if direction not in (-1, 1):
        raise ValueError(f"direction muss −1 oder +1 sein: {direction!r}")
    if not against:
        raise ValueError("against ist leer")
    _finite(C, "C"), _finite(L0, "L0"), _finite(target, "target")
    against = [norm_hex(b) for b in against]
    start = oklch_to_hex(L0, C, h)
    best = {"ratio": -1.0, "hex": None}

    def f(L, c):
        hx = oklch_to_hex(L, c, h)
        r = _fmin(hx, against)
        if r > best["ratio"]:
            best["ratio"], best["hex"] = r, hx
        return hx, r

    def done(L, c, hx, r, changed):
        return {"hex": hx, "L": L, "C": c, "changed": changed, "ratio": r,
                "distance": distance(start, hx, "normal") if changed else 0.0}

    c = C
    for attempt in range(6):
        if attempt:
            c = c * 0.9
        hx, r = f(L0, c)
        if r >= target:
            return done(L0, c, hx, r, attempt > 0)
        y0 = rel_lum(hx)
        for b in against:
            yb = rel_lum(b)
            if (direction < 0 and yb < y0) or (direction > 0 and yb > y0):
                raise SolveError("mixed-sides", {"hex": hx, "surface": b, "direction": direction})
        end = 0.0 if direction < 0 else 1.0
        hx, r = f(end, c)
        if r < target:
            continue
        good, bad = end, L0
        for _ in range(40):
            mid = (good + bad) / 2
            if f(mid, c)[1] >= target:
                good = mid
            else:
                bad = mid
        L = good
        hx, r = f(L, c)
        steps = 0
        while r < target and steps < 20:
            L = _clamp01(L + direction * 0.001)
            hx, r = f(L, c)
            steps += 1
        if r >= target:
            return done(L, c, hx, r, True)
    raise SolveError("unreachable", {"target": target, "best": best["ratio"], "best_hex": best["hex"]})


# ---- Unterscheidbare Farben auswählen (4.1.12)

def pick_distinct(pool, k, kinds=WORST_KINDS, start=None, bg=None):
    """Gierige Max-Min-Auswahl. Erste Farbe: start, sonst höchster Kontrast zu bg (sonst die erste).
    Gleichstand (Differenz < 1e-9): frühere Farbe in der Reihenfolge von pool."""
    if "tritan" in kinds:
        raise ValueError("Tritan geht in keine Auswahl ein")
    cand = []
    for c in pool:
        c = norm_hex(c)
        if c not in cand:
            cand.append(c)
    chosen = []
    if k <= 0:
        return chosen
    if start is not None:
        s = norm_hex(start)
        chosen.append(s)
        cand = [c for c in cand if c != s]
    elif cand:
        first = cand[0]
        if bg is not None:
            best = None
            for c in cand:
                r = contrast(c, bg)
                if best is None or r > best + 1e-9:
                    best, first = r, c
        chosen.append(first)
        cand.remove(first)
    while len(chosen) < k and cand:
        best, pick = None, None
        for c in cand:
            m = min(worst_distance(c, s, kinds) for s in chosen)
            if best is None or m > best + 1e-9:
                best, pick = m, c
        chosen.append(pick)
        cand.remove(pick)
    return chosen


# ---- Link-Fenster (4.1.13), Beamer (4.1.14), Schleier (4.1.15)

def link_window(text, bgs):
    """Leuchtdichte-Fenster für Links ohne Unterstreichung (G183) → {lo, hi, empty, polarity}.
    Dunkler Text auf hellen Flächen nach Spezifikation, heller Text auf dunklen Flächen gespiegelt."""
    yt = rel_lum(text)
    ys = [rel_lum(b) for b in bgs]
    if not ys:
        raise ValueError("bgs ist leer")
    if all(y >= yt for y in ys):
        lo = 3 * (yt + 0.05) - 0.05
        hi = min((y + 0.05) / 4.5 - 0.05 for y in ys)
        pol = "dark-text"
    elif all(y <= yt for y in ys):
        lo = max(4.5 * (y + 0.05) - 0.05 for y in ys)
        hi = (yt + 0.05) / 3 - 0.05
        pol = "light-text"
    else:
        raise ValueError("Flächen liegen auf beiden Seiten des Texts")
    return {"lo": lo, "hi": hi, "empty": lo > hi, "polarity": pol}


def ambient_ratio(room):
    """Raumlicht / Projektorweiß für 'dim', 'normal', 'bright' (TI DLPA088)."""
    p = K["projector"]
    return p["ambient_lx"][room] / p["white_lx"]


def _ambient(a):
    return ambient_ratio(a) if isinstance(a, str) else _finite(a, "Raumlicht")


def projected_contrast(a, b, ambient):
    """Projizierter Kontrast K = P(Y_hell) / P(Y_dunkel), P(Y) = Y·(1 − 1/N) + 1/N + a."""
    amb, n = _ambient(ambient), K["projector"]["native"]
    ya, yb = rel_lum(a), rel_lum(b)
    hi, lo = (ya, yb) if ya >= yb else (yb, ya)
    return (hi * (1 - 1 / n) + 1 / n + amb) / (lo * (1 - 1 / n) + 1 / n + amb)


def projector_hex(h, ambient):
    """Darstellung „Beamer“: je Kanal linear (c·(1 − 1/N) + 1/N + a)/(1 + a), dann gam."""
    amb, n = _ambient(ambient), K["projector"]["native"]
    l = [lin(c) for c in hex_to_srgb(h)]
    return srgb_to_hex([gam((c * (1 - 1 / n) + 1 / n + amb) / (1 + amb)) for c in l])


def scrim_alpha(text, scrim, target):
    """Mindestdeckkraft eines Schleiers über dem schlimmsten Pixel (F83) → dict oder None.
    percent ist die ganze Prozentzahl nach Nachprüfung in Gleitkomma und 8 Bit."""
    t, s = norm_hex(text), norm_hex(scrim)
    _finite(target, "target")
    worst = "#FFFFFF" if rel_lum(t) > rel_lum(s) else "#000000"
    p, sv = hex_to_srgb(worst), hex_to_srgb(s)

    def mix(a):
        return [a * sv[0] + (1 - a) * p[0], a * sv[1] + (1 - a) * p[1], a * sv[2] + (1 - a) * p[2]]
    if contrast(t, mix(1.0)) < target:
        return None
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if contrast(t, mix(mid)) >= target:
            hi = mid
        else:
            lo = mid
    pct = math.ceil(hi * 100 - 1e-9)
    while True:
        c = mix(pct / 100)
        r, q = contrast(t, c), srgb_to_hex(c)
        r8 = contrast(t, q)
        if (r >= target and r8 >= target) or pct >= 100:
            break
        pct += 1
    return {"alpha": hi, "percent": pct, "ratio_at_percent": r, "ratio_at_percent_8bit": r8, "worst": worst, "mix_hex": q}


# ---- Paarbewertung aus dem Rollenschema (4.1.16)

def evaluate(task, roles_by_mode, missing="error"):
    """Alle Paare aus task.pairs, task.decorative, task.advisory für jeden Modus.
    missing='error' (Standard) bricht bei fehlender Rolle ab, 'skip' lässt das Paar aus."""
    out = {"pairs": [], "decorative": [], "advisory": []}
    modes = task.get("modes") or list(roles_by_mode)

    def role(roles, mode, rid):
        if rid in roles:
            return roles[rid]
        if missing == "skip":
            return None
        raise ValueError(f"evaluate {task.get('id')}: Rolle {rid} fehlt im Modus {mode}")
    for mode in modes:
        if mode not in roles_by_mode:
            raise ValueError(f"evaluate {task.get('id')}: Modus {mode} fehlt")
        roles = roles_by_mode[mode]
        for line in task.get("pairs", []):
            for bg in line["on"]:
                a, b = role(roles, mode, line["fg"]), role(roles, mode, bg)
                if a is None or b is None:
                    continue
                r = contrast(a, b)
                out["pairs"].append({"mode": mode, "fg": line["fg"], "bg": bg, "ratio": r, "min": line["min"],
                                     "criterion": line["criterion"], "rule": line["rule"], "pass": r >= line["min"]})
        for line in task.get("decorative", []) or []:
            for bg in line["on"]:
                a, b = role(roles, mode, line["fg"]), role(roles, mode, bg)
                if a is None or b is None:
                    continue
                out["decorative"].append({"mode": mode, "fg": line["fg"], "bg": bg, "ratio": contrast(a, b)})
        for line in task.get("advisory", []) or []:
            ons = line["on"] if isinstance(line["on"], list) else [line["on"]]
            for bg in ons:
                a, b = role(roles, mode, line["fg"]), role(roles, mode, bg)
                if a is None or b is None:
                    continue
                r = contrast(a, b)
                out["advisory"].append({"mode": mode, "fg": line["fg"], "bg": bg, "ratio": r, "min": line["min"],
                                        "finding": line["finding"], "pass": r >= line["min"]})
    return out


# ---- Vergleichswerte (4.1.8)

def _comparison_colors(spec, datasets):
    if "generate" in spec:
        if spec["generate"] != "hsl-hues":
            raise ValueError(f"unbekannter Generator: {spec['generate']!r}")
        n = spec["n"]
        return [srgb_to_hex(_hsl_to_rgb(i * 360 / n, spec["s"], spec["l"])) for i in range(n)]
    ds = datasets.get(spec["dataset"]) if datasets is not None else None
    if ds is None:
        ds = _jload(f"data/datasets/{spec['dataset']}.json")
    scheme = next(s for s in ds["schemes"] if s["id"] == spec["scheme"])
    ex = set(spec.get("exclude", []))
    return [norm_hex(c["hex"]) for c in scheme["colors"] if c["name"] not in ex]


_REF_CACHE = {}


def reference_values(comparisons=None, datasets=None):
    """Vergleichswerte aus data/comparisons.json → {id: {value, a, b, kind, colors, kinds}}."""
    default = comparisons is None and datasets is None
    if default and "all" in _REF_CACHE:
        return _REF_CACHE["all"]
    comps = comparisons if comparisons is not None else _jload("data/comparisons.json")
    out = {}
    for comp in comps["comparisons"]:
        cols = _comparison_colors(comp["colors"], datasets)
        md = min_distance(cols, comp["kinds"])
        out[comp["id"]] = {"value": md["value"], "a": md["a"], "b": md["b"], "kind": md["kind"],
                           "colors": cols, "kinds": list(comp["kinds"])}
    if default:
        _REF_CACHE["all"] = out
    return out


# ---- Platzhalter (6.12)

class RenderError(ValueError):
    """Platzhalter, der sich nicht auflösen lässt."""


PLACEHOLDER = re.compile(r"\{(cr|dist|gray|gs|L|proj|scrim|ref|hex|count|date)(?::([^{}]*))?\}")
_ARITY = {"cr": 2, "dist": 3, "gray": 1, "gs": 2, "L": 1, "proj": 3, "scrim": 3, "ref": 1, "hex": 1, "count": 1, "date": 0}
_MONTHS = {"de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
           "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
_DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")


def esc(s):
    """HTML-Escape wie html.escape(s, quote=True)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")


def find_placeholders(template):
    """Alle Platzhalter einer Vorlage als [(name, argumente)] (für Datenprüfungen)."""
    return [(m.group(1), m.group(2)) for m in PLACEHOLDER.finditer(template)]


def _roles_by_mode(ctx):
    if ctx.get("roles") is not None:
        return ctx["roles"]
    pal = ctx.get("palette")
    return pal.get("roles") if pal else None


def _operand(tok, mode, ctx, where):
    if tok.startswith("#"):
        try:
            return norm_hex(tok)
        except ValueError:
            raise RenderError(f"{where}: kein Hex #RRGGBB: {tok}") from None
    rbm = _roles_by_mode(ctx)
    if not rbm:
        raise RenderError(f"{where}: Rolle {tok} ohne Palette")
    m = mode or ctx.get("mode")
    if m is None:
        if len(rbm) != 1:
            raise RenderError(f"{where}: Rolle {tok} ohne Modus (@light/@dark)")
        m = next(iter(rbm))
    if m not in rbm or tok not in rbm[m]:
        raise RenderError(f"{where}: Rolle {tok} fehlt im Modus {m}")
    return norm_hex(rbm[m][tok])


def _number(tok, where):
    v = _num(tok)
    if v is None or not math.isfinite(v):
        raise RenderError(f"{where}: keine Zahl: {tok}")
    return v


def _ref_value(rid, ctx, where):
    refs = ctx.get("refs") if ctx else None
    if refs is None:
        refs = reference_values()
    if rid not in refs:
        raise RenderError(f"{where}: unbekannter Vergleichswert {rid}")
    v = refs[rid]
    return v["value"] if isinstance(v, dict) else v


def _compute(m, a, b, k, t, rid, ctx, where):
    """Rohwert eines Zahl-Platzhalters."""
    if m == "cr":
        return contrast(a, b)
    if m == "dist":
        if k not in KINDS:
            raise RenderError(f"{where}: unbekannte Sichtweise {k}")
        return distance(a, b, k)
    if m == "gray":
        return gray_value(a)
    if m == "gs":
        return gray_distance(a, b)
    if m == "L":
        return hex_to_oklch(a)[0]
    if m == "proj":
        amb = t if t in K["projector"]["ambient_lx"] else _number(t, where)
        return projected_contrast(a, b, amb)
    if m == "scrim":
        r = scrim_alpha(a, b, _number(t, where))
        if r is None:
            raise RenderError(f"{where}: Schleier erreicht das Ziel {t} nicht")
        return r["percent"] / 100
    if m == "ref":
        return _ref_value(rid, ctx, where)
    raise RenderError(f"{where}: unbekannte Kennzahl {m}")


def _display(m, x, lang):
    if m in ("cr", "proj"):
        return fmt_ratio(x, lang)
    if m in ("dist", "gs", "ref"):
        return fmt_dist(x, lang)
    if m == "scrim":
        return fmt_pct_up(x, lang)
    return fmt_L(x, lang)


def _machine(m, x):
    if m in ("cr", "proj"):
        return fmt_ratio(x, "en")[:-2]
    if m == "scrim":
        return str(math.ceil(x * 100 - 1e-9))
    return _display(m, x, "en")


def _tag_html(tag):
    attrs = [("value", tag["value_attr"]), ("data-m", tag["m"])]
    for key in ("a", "b", "k", "t", "id", "mode"):
        if tag[key] is not None:
            attrs.append(("data-" + key, tag[key]))
    return '<data class="num"' + "".join(f' {n}="{esc(v)}"' for n, v in attrs) + ">" + esc(tag["text"]) + "</data>"


def data_tag_text(attrs, lang, ctx=None):
    """Erwarteter Anzeigetext eines <data class="num">-Elements aus seinen data-*-Attributen
    (für test_honesty). attrs: {'data-m': …, 'data-a': …, …} oder {'m': …, 'a': …, …}."""
    def g(key):
        return attrs.get("data-" + key, attrs.get(key))
    m = g("m")
    where = f"<data data-m={m}>"
    a = norm_hex(g("a")) if g("a") else None
    b = norm_hex(g("b")) if g("b") else None
    return _display(m, _compute(m, a, b, g("k"), g("t"), g("id"), ctx or {}, where), lang)


def render_text(template, ctx, lang, escape=True):
    """Löst Platzhalter auf → (html, data_tags). ctx: {palette | roles, mode, refs, counts, date}.
    escape=True escapt den Text um die Platzhalter (Daten aus JSON); False für vertrauenswürdiges HTML."""
    ctx = ctx or {}
    _sep(lang)
    out, tags, pos = [], [], 0
    for mt in PLACEHOLDER.finditer(template):
        lit = template[pos:mt.start()]
        out.append(esc(lit) if escape else lit)
        pos = mt.end()
        name, arg = mt.group(1), mt.group(2)
        where = mt.group(0)
        if name == "date":
            if arg is not None:
                raise RenderError(f"{where}: date hat keine Argumente")
            d = ctx.get("date")
            dm = _DATE.fullmatch(d or "")
            if not dm:
                raise RenderError(f"{where}: ctx.date fehlt oder ist kein JJJJ-MM-TT")
            y, mo, da = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
            if not 1 <= mo <= 12 or not 1 <= da <= 31:
                raise RenderError(f"{where}: ungültiges Datum {d}")
            txt = f"{da}. {_MONTHS['de'][mo - 1]} {y}" if lang == "de" else f"{_MONTHS['en'][mo - 1]} {da}, {y}"
            out.append(f'<data class="date" value="{d}">{txt}</data>')
            tags.append({"m": "date", "value": d, "text": txt})
            continue
        if arg is None:
            raise RenderError(f"{where}: Argumente fehlen")
        mode = None
        if "@" in arg:
            arg, mode = arg.rsplit("@", 1)
            if not mode:
                raise RenderError(f"{where}: leerer Modus")
        parts = arg.split("/")
        if len(parts) != _ARITY[name] or any(p == "" for p in parts):
            raise RenderError(f"{where}: erwartet {_ARITY[name]} Argumente")
        if name == "count":
            counts = ctx.get("counts") or {}
            if parts[0] not in counts:
                raise RenderError(f"{where}: Zähler {parts[0]} fehlt in ctx.counts")
            n = counts[parts[0]]
            txt = fmt_count(n, lang)
            out.append(f'<data class="count" value="{n}">{esc(txt)}</data>')
            tags.append({"m": "count", "value": n, "text": txt})
            continue
        if name == "hex":
            hx = _operand(parts[0], mode, ctx, where)
            out.append(f'<data class="hex" value="{hx}"><code>{hx}</code></data>')
            tags.append({"m": "hex", "value": hx, "text": hx})
            continue
        a = b = k = t = rid = None
        if name == "ref":
            if mode is not None:
                raise RenderError(f"{where}: ref hat keinen Modus")
            rid = parts[0]
        else:
            a = _operand(parts[0], mode, ctx, where)
            if name in ("cr", "dist", "gs", "proj", "scrim"):
                b = _operand(parts[1], mode, ctx, where)
            if name == "dist":
                k = parts[2]
            if name in ("proj", "scrim"):
                t = parts[2]
        uses_role = any(not p.startswith("#") for p in parts[:2]) and name != "ref"
        x = _compute(name, a, b, k, t, rid, ctx, where)
        txt = _display(name, x, lang)
        tag = {"m": name, "a": a, "b": b, "k": k, "t": t, "id": rid,
               "mode": (mode or ctx.get("mode") or next(iter(_roles_by_mode(ctx)))) if uses_role else None,
               "value": x, "value_attr": _machine(name, x), "text": txt}
        out.append(_tag_html(tag))
        tags.append(tag)
    lit = template[pos:]
    out.append(esc(lit) if escape else lit)
    return "".join(out), tags
