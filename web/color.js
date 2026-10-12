/* Farbkern von Farbsprache (FS.color): Parser, Umrechnung, Gamut-Mapping, Kontrast,
   Graustufen, Simulation, Abstände, Formatierer, Löser, Beamer, Schleier, Paarbewertung
   und Platzhalter. Rein, ohne DOM. Spiegel von tools/color.py.
   Konstanten kommen aus FS_CONST = color-constants ∪ cvd ∪ {css_names}.
   Aus CSS Color 4 übernommen oder abgeleitet: Matrizen, sRGB-Übertragung, Umrechnung zwischen XYZ, OKLab und OKLCH, ΔEOK, HSL-Umrechnung, Gamut-Mapping und die Tabelle der Farbnamen
   (W3C Software and Document License, Text in data/licenses/W3C-Software-and-Document-2023.txt). Relative Leuchtdichte
   und Kontrast folgen WCAG 2.2 (W3C Document License). Die ausgelieferte color.js trägt beide Vermerke in der ersten
   Zeile (build.py, W3C_NOTICE und WCAG_NOTICE):
   This software includes material copied from or derived from CSS Color Module Level 4
   (https://www.w3.org/TR/2026/CRD-css-color-4-20261009/). Copyright © 2026 World Wide Web Consortium.
   https://www.w3.org/copyright/software-license-2023/ */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.color = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  var K = root.FS_CONST;
  if (!K || !K.srgb_to_xyz || !K.vienot1999) { throw new Error('FS_CONST fehlt (data/color-constants.json und data/cvd.json)'); }
  if (!K.css_names) { throw new Error('FS_CONST.css_names fehlt (data/css-names.json)'); }

  // ---------- Konstanten
  function rat(m) {
    var out = [], i, j, row;
    for (i = 0; i < 3; i++) { row = []; for (j = 0; j < 3; j++) { row.push(m[i][j][0] / m[i][j][1]); } out.push(row); }
    return out;
  }
  var SRGB_XYZ = rat(K.srgb_to_xyz), XYZ_SRGB = rat(K.xyz_to_srgb), P3_XYZ = rat(K.p3_to_xyz);
  var XYZ_LMS = K.xyz_to_lms, LMS_OK = K.lms_to_oklab, LMS_XYZ = K.lms_to_xyz, OK_LMS = K.oklab_to_lms;
  var WCAG = K.wcag_lum, LIN_T = K.srgb_lin_threshold, GAM_T = K.srgb_gam_threshold;
  var JND = K.jnd, EPS = K.eps, POWERLESS = K.powerless_c;
  var VP = K.vienot1999.protan, VD = K.vienot1999.deutan;
  var T1 = K.brettel1997.tritan.m1, T2 = K.brettel1997.tritan.m2, TN = K.brettel1997.tritan.n;
  var NAMES = K.css_names;
  var KINDS = ['normal', 'deutan', 'protan', 'tritan', 'gray'];
  var WORST_KINDS = ['normal', 'deutan', 'protan'];
  // Einzige feste Abstandsschwelle: unter 100 · JND (= 2) fallen zwei Farben praktisch zusammen (4.1.8)
  var JND_DISTANCE = 100 * JND;
  // Gleitkommarauschen beim Gamut-Test der Eingabe (oklch(100% 0 0) liefert 1,0000000000000004).
  var GAMUT_NOISE = 1e-9;
  var NNBSP = '\u202f';

  // ---------- Grundfunktionen
  function mul(m, v) {
    return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
      m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
      m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]];
  }
  function lin(c) {
    var a = Math.abs(c);
    if (a <= LIN_T) { return c / 12.92; }
    var v = Math.pow((a + 0.055) / 1.055, 2.4);
    return c < 0 ? -v : v;
  }
  function gam(c) {
    var a = Math.abs(c);
    if (a > GAM_T) { var v = 1.055 * Math.pow(a, 1 / 2.4) - 0.055; return c < 0 ? -v : v; }
    return 12.92 * c;
  }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }
  function finite(x, what) {
    if (!isNum(x)) { throw new Error((what || 'Zahl') + ' ist keine endliche Zahl: ' + x); }
    return x;
  }
  function clamp01(x) { return Math.min(1, Math.max(0, x)); }
  function endsWith(s, t) { return s.length >= t.length && s.slice(s.length - t.length) === t; }

  // ---------- Hex und Quantisierung
  var HEX6 = /^#[0-9a-fA-F]{6}$/;
  function normHex(h) {
    if (typeof h !== 'string' || !HEX6.test(h)) { throw new Error('kein Hex #RRGGBB: ' + h); }
    return h.toUpperCase();
  }
  function hexToSrgb(h) {
    h = normHex(h);
    return [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];
  }
  // Die eine Quantisierung: byte = floor(clamp(x, 0, 1) · 255 + 0.5)
  function quantize(x) {
    finite(x, 'Kanal');
    return Math.floor(clamp01(x) * 255 + 0.5); // quantize
  }
  function byteHex(n) { var s = n.toString(16).toUpperCase(); return s.length < 2 ? '0' + s : s; }
  function srgbToHex(rgb) { return '#' + byteHex(quantize(rgb[0])) + byteHex(quantize(rgb[1])) + byteHex(quantize(rgb[2])); }

  // ---------- OKLab, OKLCH, Display-P3
  function srgbToXyz(rgb) { return mul(SRGB_XYZ, [lin(rgb[0]), lin(rgb[1]), lin(rgb[2])]); }
  function xyzToOklab(xyz) {
    var lms = mul(XYZ_LMS, xyz);
    return mul(LMS_OK, [Math.cbrt(lms[0]), Math.cbrt(lms[1]), Math.cbrt(lms[2])]);
  }
  function oklabToXyz(lab) {
    var q = mul(OK_LMS, lab);
    return mul(LMS_XYZ, [q[0] * q[0] * q[0], q[1] * q[1] * q[1], q[2] * q[2] * q[2]]);
  }
  function linToOklab(l) { return xyzToOklab(mul(SRGB_XYZ, l)); }
  function srgbToOklab(rgb) { return linToOklab([lin(rgb[0]), lin(rgb[1]), lin(rgb[2])]); }
  function oklabToSrgb(lab) {
    var l = mul(XYZ_SRGB, oklabToXyz(lab));
    return [gam(l[0]), gam(l[1]), gam(l[2])];
  }
  function oklabToOklch(lab) {
    var L = lab[0], a = lab[1], b = lab[2];
    var C = Math.sqrt(a * a + b * b);
    var h = Math.atan2(b, a) * 180 / Math.PI;
    if (h < 0) { h += 360; }
    if (h >= 360) { h -= 360; }
    return [L, C, C <= POWERLESS ? NaN : h];
  }
  function oklchToOklab(lch) {
    var h = lch[2];
    if (h === null || h === undefined || h !== h) { h = 0; }
    var r = h * Math.PI / 180;
    return [lch[0], lch[1] * Math.cos(r), lch[1] * Math.sin(r)];
  }
  function p3ToLinSrgb(p3) { return mul(XYZ_SRGB, mul(P3_XYZ, [lin(p3[0]), lin(p3[1]), lin(p3[2])])); }
  function p3ToSrgb(p3) { var l = p3ToLinSrgb(p3); return [gam(l[0]), gam(l[1]), gam(l[2])]; }
  function p3ToOklab(p3) { return xyzToOklab(mul(P3_XYZ, [lin(p3[0]), lin(p3[1]), lin(p3[2])])); }
  function deltaEok(x, y) {
    var d0 = x[0] - y[0], d1 = x[1] - y[1], d2 = x[2] - y[2];
    return Math.sqrt(d0 * d0 + d1 * d1 + d2 * d2);
  }
  function hexToOklch(h) { return oklabToOklch(srgbToOklab(hexToSrgb(h))); }

  // ---------- Gamut-Mapping (CSS Color 4 §14.2.2, binäre Suche mit lokalem MINDE)
  function inGamut(rgb) { return rgb[0] >= 0 && rgb[0] <= 1 && rgb[1] >= 0 && rgb[1] <= 1 && rgb[2] >= 0 && rgb[2] <= 1; }
  function clip(rgb) { return [clamp01(rgb[0]), clamp01(rgb[1]), clamp01(rgb[2])]; }
  function gamutMap(L, C, h) {
    finite(L, 'L'); finite(C, 'C');
    if (L >= 1) { return [1, 1, 1]; }
    if (L <= 0) { return [0, 0, 0]; }
    var origin = oklchToOklab([L, C, h]);
    var rgb = oklabToSrgb(origin);
    if (inGamut(rgb)) { return rgb; }
    var clipped = clip(rgb);
    if (deltaEok(srgbToOklab(clipped), origin) < JND) { return clipped; }
    var lo = 0, hi = C, loIn = true, ch, cur, e;
    while (hi - lo > EPS) {
      ch = (lo + hi) / 2;
      cur = oklchToOklab([L, ch, h]);
      rgb = oklabToSrgb(cur);
      if (loIn && inGamut(rgb)) { lo = ch; continue; }
      clipped = clip(rgb);
      e = deltaEok(srgbToOklab(clipped), cur);
      if (e < JND) {
        if (JND - e < EPS) { return clipped; }
        loIn = false; lo = ch;
      } else { hi = ch; }
    }
    return clipped;
  }
  function oklchToHex(L, C, h) { return srgbToHex(gamutMap(L, C, h)); }

  // ---------- Parser (4.1.1)
  var WS = '[ \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff]';
  var WS1 = new RegExp('^' + WS + '$');
  var SPLIT = new RegExp(WS + '+');
  var NUMRE = /^[+-]?(?:[0-9]+|[0-9]*\.[0-9]+)(?:e[+-]?[0-9]+)?$/;
  var FUNC = /^([a-z][a-z0-9-]*)\(([^()]*)\)$/;
  var HEXDIG = /^[0-9a-f]+$/;
  var HEXBARE = /^[0-9a-f]{6}$/;
  function ParseErr(key) { this.key = key; }
  // Trimmen per Schleife statt per Regex: WS+$ wäre bei langen Leerraumfolgen quadratisch
  function trim(s) { var a = 0, b = s.length; while (a < b && WS1.test(s.charAt(a))) { a++; } while (b > a && WS1.test(s.charAt(b - 1))) { b--; } return s.slice(a, b); }
  function num(tok) { return NUMRE.test(tok) ? parseFloat(tok) : null; }
  function pct(tok) { return endsWith(tok, '%') && NUMRE.test(tok.slice(0, -1)) ? parseFloat(tok.slice(0, -1)) : null; }
  function hue(tok) {
    if (tok === 'none') { return null; }
    var units = ['grad', 'turn', 'rad'], i, v, r;
    for (i = 0; i < units.length; i++) {
      if (endsWith(tok, units[i]) && num(tok.slice(0, -units[i].length)) !== null) { throw new ParseErr('hue-unit'); }
    }
    v = endsWith(tok, 'deg') ? num(tok.slice(0, -3)) : num(tok);
    if (v === null || !isFinite(v)) { throw new ParseErr('unknown'); }
    r = v % 360;
    if (r < 0) { r += 360; }
    if (r >= 360) { r -= 360; }
    return r;
  }
  function comp(tok, pctScale, numDiv, allowNone) {
    if (tok === 'none' && allowNone !== false) { return 0; }
    var v = pct(tok), r;
    if (v !== null) { r = v / 100 * pctScale; } else {
      v = num(tok);
      if (v === null) { throw new ParseErr('unknown'); }
      r = v / numDiv;
    }
    if (!isFinite(r)) { throw new ParseErr('unknown'); }
    return r;
  }
  function hslPc(tok) {
    if (tok === 'none') { return 0; }
    var v = pct(tok);
    if (v === null) { v = num(tok); }
    if (v === null || !isFinite(v)) { throw new ParseErr('unknown'); }
    return v;
  }
  function alphaOf(tok, allowNone) { return clamp01(comp(tok, 1, 1, allowNone)); }
  function hslToRgb(hueDeg, sat, light) {
    sat /= 100; light /= 100;
    function f(n) {
      var k = (n + hueDeg / 30) % 12;
      var a = sat * Math.min(light, 1 - light);
      return light - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    }
    return [f(0), f(8), f(4)];
  }
  function finish(source, alpha, srgb, lab, lch) {
    if (!lab) { lab = srgb ? srgbToOklab(srgb) : oklchToOklab(lch); }
    if (!srgb) { srgb = oklabToSrgb(lab); }
    var oog = false, i, rgb, hx, md, l;
    for (i = 0; i < 3; i++) { if (srgb[i] < -GAMUT_NOISE || srgb[i] > 1 + GAMUT_NOISE) { oog = true; } }
    if (!oog) { rgb = clip(srgb); hx = srgbToHex(rgb); md = null; } else {
      l = lch || oklabToOklch(lab);
      rgb = gamutMap(l[0], l[1], l[2]);
      hx = srgbToHex(rgb);
      md = 100 * deltaEok(lab, srgbToOklab(hexToSrgb(hx)));
    }
    return { hex: hx, srgb: rgb, alpha: alpha, source: source, out_of_gamut: oog, mapped_distance: md };
  }
  function parseHex(d) {
    var i, e = '';
    if (d.length === 3 || d.length === 4) { for (i = 0; i < d.length; i++) { e += d.charAt(i) + d.charAt(i); } d = e; }
    if (d.length !== 6 && d.length !== 8) { throw new ParseErr('unknown'); }
    var rgb = [parseInt(d.slice(0, 2), 16) / 255, parseInt(d.slice(2, 4), 16) / 255, parseInt(d.slice(4, 6), 16) / 255];
    var alpha = d.length === 8 ? parseInt(d.slice(6, 8), 16) / 255 : 1;
    return finish('hex', alpha, rgb);
  }
  function parseFunc(name, inner) {
    var comps, atok = null, legacy, parts, i, halves, first, alpha, h, L, C, v, rgb, pc;
    if (inner.indexOf(',') >= 0) {
      if (['rgb', 'rgba', 'hsl', 'hsla'].indexOf(name) < 0 || inner.indexOf('/') >= 0) { throw new ParseErr('unknown'); }
      parts = inner.split(',');
      for (i = 0; i < parts.length; i++) {
        parts[i] = trim(parts[i]);
        if (!parts[i] || SPLIT.test(parts[i]) || parts[i] === 'none') { throw new ParseErr('unknown'); }
      }
      if (parts.length !== 3 && parts.length !== 4) { throw new ParseErr('unknown'); }
      comps = parts.slice(0, 3); atok = parts.length === 4 ? parts[3] : null; legacy = true;
    } else {
      halves = inner.split('/');
      if (halves.length > 2) { throw new ParseErr('unknown'); }
      first = trim(halves[0]);
      comps = first ? first.split(SPLIT) : [];
      if (halves.length === 2) {
        atok = trim(halves[1]);
        if (!atok || SPLIT.test(atok)) { throw new ParseErr('unknown'); }
      }
      legacy = false;
    }
    alpha = atok === null ? 1 : alphaOf(atok, !legacy);
    if (name === 'rgb' || name === 'rgba') {
      if (comps.length !== 3) { throw new ParseErr('unknown'); }
      if (legacy) {
        pc = endsWith(comps[0], '%');
        if (endsWith(comps[1], '%') !== pc || endsWith(comps[2], '%') !== pc) { throw new ParseErr('unknown'); }
      }
      rgb = [clamp01(comp(comps[0], 1, 255)), clamp01(comp(comps[1], 1, 255)), clamp01(comp(comps[2], 1, 255))];
      return finish('rgb', alpha, rgb);
    }
    if (name === 'hsl' || name === 'hsla') {
      if (comps.length !== 3) { throw new ParseErr('unknown'); }
      h = hue(comps[0]);
      if (legacy && !(endsWith(comps[1], '%') && endsWith(comps[2], '%'))) { throw new ParseErr('unknown'); }
      var s = Math.max(0, hslPc(comps[1])), l = hslPc(comps[2]);
      return finish('hsl', alpha, hslToRgb(h === null ? 0 : h, s, l));
    }
    if (name === 'oklch') {
      if (comps.length !== 3) { throw new ParseErr('unknown'); }
      L = clamp01(comp(comps[0], 1, 1));
      C = Math.max(0, comp(comps[1], 0.4, 1));
      h = hue(comps[2]);
      return finish('oklch', alpha, null, null, [L, C, h === null ? NaN : h]);
    }
    if (name === 'oklab') {
      if (comps.length !== 3) { throw new ParseErr('unknown'); }
      return finish('oklab', alpha, null, [clamp01(comp(comps[0], 1, 1)), comp(comps[1], 0.4, 1), comp(comps[2], 0.4, 1)]);
    }
    if (name === 'color') {
      if (comps.length !== 4 || (comps[0] !== 'srgb' && comps[0] !== 'display-p3')) { throw new ParseErr('unknown'); }
      v = [comp(comps[1], 1, 1), comp(comps[2], 1, 1), comp(comps[3], 1, 1)];
      if (comps[0] === 'srgb') { return finish('srgb', alpha, v); }
      return finish('display-p3', alpha, p3ToSrgb(v), p3ToOklab(v));
    }
    throw new ParseErr('unknown');
  }
  function parseAny(s, bare) {
    if (typeof s !== 'string') { return s === null || s === undefined ? 'empty' : 'unknown'; }
    var t = trim(s).toLowerCase(), m;
    if (!t) { return 'empty'; }
    try {
      if (t === 'transparent') { return 'transparent'; }
      if (t.charAt(0) === '#') {
        if (!HEXDIG.test(t.slice(1))) { return 'unknown'; }
        return parseHex(t.slice(1));
      }
      if (bare !== false && HEXBARE.test(t)) { return parseHex(t); }
      if (Object.prototype.hasOwnProperty.call(NAMES, t)) { return finish('name', 1, hexToSrgb(NAMES[t])); }
      m = FUNC.exec(t);
      if (m) { return parseFunc(m[1], m[2]); }
      return 'unknown';
    } catch (e) {
      if (e instanceof ParseErr) { return e.key; }
      throw e;
    }
  }
  // parse(s, bare): {hex, srgb, alpha, source, out_of_gamut, mapped_distance} oder null
  function parse(s, bare) { var r = parseAny(s, bare); return typeof r === 'string' ? null : r; }
  // parseError(s, bare): 'empty' | 'transparent' | 'hue-unit' | 'unknown' oder null, wenn gültig
  function parseError(s, bare) { var r = parseAny(s, bare); return typeof r === 'string' ? r : null; }
  function composite(fg, alpha, bg) {
    var f = typeof fg === 'string' ? hexToSrgb(fg) : fg;
    var b = typeof bg === 'string' ? hexToSrgb(bg) : (bg || [1, 1, 1]);
    return srgbToHex([alpha * f[0] + (1 - alpha) * b[0], alpha * f[1] + (1 - alpha) * b[1], alpha * f[2] + (1 - alpha) * b[2]]);
  }

  // ---------- Kontrast (WCAG 2.2) und Graustufen
  function rgbOf(c) { return typeof c === 'string' ? hexToSrgb(c) : c; }
  function relLum(c) {
    var v = rgbOf(c);
    return WCAG[0] * lin(v[0]) + WCAG[1] * lin(v[1]) + WCAG[2] * lin(v[2]);
  }
  function contrast(a, b) {
    var ya = relLum(a), yb = relLum(b), hi = ya >= yb ? ya : yb, lo = ya >= yb ? yb : ya;
    return (hi + 0.05) / (lo + 0.05);
  }
  function grayValue(c) { return Math.cbrt(relLum(c)); }
  function grayHex(c) { var g = gam(relLum(c)); return srgbToHex([g, g, g]); }
  function grayDistance(a, b) { return Math.abs(grayValue(a) - grayValue(b)) * 100; }

  // ---------- Farbsehschwäche (4.1.7) und Abstände (4.1.8)
  var simCache = {}, simCount = 0;
  function simLin(h, kind) {
    var s = hexToSrgb(h), l = [lin(s[0]), lin(s[1]), lin(s[2])], o, y;
    if (kind === 'normal') { return l; }
    if (kind === 'protan') { o = mul(VP, l); } else if (kind === 'deutan') { o = mul(VD, l); } else if (kind === 'tritan') {
      o = mul(TN[0] * l[0] + TN[1] * l[1] + TN[2] * l[2] >= 0 ? T1 : T2, l);
    } else if (kind === 'gray') {
      y = WCAG[0] * l[0] + WCAG[1] * l[1] + WCAG[2] * l[2]; o = [y, y, y];
    } else { throw new Error('unbekannte Sichtweise: ' + kind); }
    return clip(o);
  }
  function simOklab(h, kind) {
    var key = kind + '|' + h, r = simCache[key];
    if (r === undefined) {
      r = kind === 'gray' ? [grayValue(h), 0, 0] : linToOklab(simLin(h, kind));
      if (simCount > 20000) { simCache = {}; simCount = 0; }
      simCache[key] = r; simCount++;
    }
    return [r[0], r[1], r[2]];
  }
  function simHex(h, kind) {
    if (kind === 'normal') { return normHex(h); }
    if (kind === 'gray') { return grayHex(h); }
    var l = simLin(h, kind);
    return srgbToHex([gam(l[0]), gam(l[1]), gam(l[2])]);
  }
  function distance(a, b, kind) {
    kind = kind || 'normal';
    if (kind === 'gray') { return grayDistance(a, b); }
    return 100 * deltaEok(simOklab(a, kind), simOklab(b, kind));
  }
  function worstDistance(a, b, kinds) {
    kinds = kinds || WORST_KINDS;
    var m = Infinity, i, d;
    for (i = 0; i < kinds.length; i++) { d = distance(a, b, kinds[i]); if (d < m) { m = d; } }
    return m;
  }
  function minDistance(colors, kinds) {
    kinds = kinds || WORST_KINDS;
    var best = null, i, j, k, d;
    for (i = 0; i < colors.length; i++) {
      for (j = i + 1; j < colors.length; j++) {
        for (k = 0; k < kinds.length; k++) {
          d = distance(colors[i], colors[j], kinds[k]);
          if (best === null || d < best.value - 1e-12) {
            best = { value: d, i: i, j: j, a: normHex(colors[i]), b: normHex(colors[j]), kind: kinds[k] };
          }
        }
      }
    }
    return best;
  }

  // ---------- Formatierer (4.1.9): Ausgabe immer aus Ganzzahlen gebaut
  function sep(lang) {
    if (lang === 'de') { return ','; }
    if (lang === 'en') { return '.'; }
    throw new Error('unbekannte Sprache: ' + lang);
  }
  function fixed(n, d, lang) {
    var sp = sep(lang), neg = n < 0, s = String(Math.abs(n));
    if (d) {
      while (s.length < d + 1) { s = '0' + s; }
      s = s.slice(0, s.length - d) + sp + s.slice(s.length - d);
    }
    return (neg ? '-' : '') + s;
  }
  function fmtRatio(x, lang, threshold) {
    finite(x);
    var n = Math.floor(x * 100 + 1e-9);
    if (threshold !== null && threshold !== undefined && x < threshold && n / 100 >= threshold) {
      n = Math.floor(threshold * 100 + 0.5) - 1;
    }
    return fixed(n, 2, lang) + ':1';
  }
  function fmtDist(x, lang) { finite(x); return fixed(Math.floor(x * 10 + 1e-9), 1, lang); }
  function fmtPctUp(alpha, lang) {
    finite(alpha);
    var p = Math.ceil(alpha * 100 - 1e-9);
    return String(p) + (sep(lang) === ',' ? NNBSP + '%' : '%');
  }
  function fmtL(x, lang) { finite(x); return fixed(Math.floor(x * 1000 + 0.5), 3, lang); }
  function fmtCount(n, lang) {
    if (!isNum(n) || Math.floor(n) !== n) { throw new Error('keine Ganzzahl: ' + n); }
    var sp = sep(lang) === ',' ? '.' : ',', s = String(Math.abs(n)), out = '';
    while (s.length > 3) { out = sp + s.slice(s.length - 3) + out; s = s.slice(0, s.length - 3); }
    return (n < 0 ? '-' : '') + s + out;
  }
  function fmtLum(y, lang) { finite(y); return fixed(Math.floor(y * 10000 + 0.5), 4, lang || 'en'); }

  // ---------- Kürzeste OKLCH-Schreibweise (4.1.10)
  var P10 = [1, 10, 100, 1000, 10000, 100000];
  function shortestOklch(h, maxP) {
    var hx = normHex(h), lch = hexToOklch(hx), p, sL, sC, nh, s, r;
    if (maxP === undefined || maxP === null) { maxP = 3; }
    for (p = 0; p <= maxP; p++) {
      sL = fixed(Math.floor(lch[0] * 100 * P10[p] + 0.5), p, 'en');
      if (lch[2] !== lch[2]) { s = 'oklch(' + sL + '% 0 0)'; } else {
        sC = fixed(Math.floor(lch[1] * P10[p + 2] + 0.5), p + 2, 'en');
        nh = Math.floor(lch[2] * P10[p] + 0.5);
        if (nh >= 360 * P10[p]) { nh -= 360 * P10[p]; }
        s = 'oklch(' + sL + '% ' + sC + ' ' + fixed(nh, p, 'en') + ')';
      }
      r = parse(s);
      if (r !== null && r.hex === hx) { return s; }
    }
    return null;
  }

  // ---------- L-Löser (4.1.11)
  function SolveError(key, values) {
    this.name = 'SolveError'; this.key = key; this.values = values || {}; this.message = key;
    if (Error.captureStackTrace) { Error.captureStackTrace(this, SolveError); } else { this.stack = (new Error(key)).stack; }
  }
  SolveError.prototype = Object.create(Error.prototype);
  SolveError.prototype.constructor = SolveError;
  function fmin(hx, against) {
    var m = Infinity, i, r;
    for (i = 0; i < against.length; i++) { r = contrast(hx, against[i]); if (r < m) { m = r; } }
    return m;
  }
  function solveL(C, h, against, target, direction, L0) {
    if (direction !== -1 && direction !== 1) { throw new Error('direction muss -1 oder +1 sein: ' + direction); }
    if (!against || !against.length) { throw new Error('against ist leer'); }
    finite(C, 'C'); finite(L0, 'L0'); finite(target, 'target');
    var ag = [], i;
    for (i = 0; i < against.length; i++) { ag.push(normHex(against[i])); }
    var start = oklchToHex(L0, C, h), best = { ratio: -1, hex: null };
    function f(L, c) {
      var hx = oklchToHex(L, c, h), r = fmin(hx, ag);
      if (r > best.ratio) { best.ratio = r; best.hex = hx; }
      return [hx, r];
    }
    function done(L, c, hx, r, changed) {
      return { hex: hx, L: L, C: c, changed: changed, ratio: r, distance: changed ? distance(start, hx, 'normal') : 0 };
    }
    var c = C, attempt, res, y0, yb, end, good, bad, mid, L, steps, b;
    for (attempt = 0; attempt < 6; attempt++) {
      if (attempt) { c = c * 0.9; }
      res = f(L0, c);
      if (res[1] >= target) { return done(L0, c, res[0], res[1], attempt > 0); }
      y0 = relLum(res[0]);
      for (b = 0; b < ag.length; b++) {
        yb = relLum(ag[b]);
        if ((direction < 0 && yb < y0) || (direction > 0 && yb > y0)) {
          throw new SolveError('mixed-sides', { hex: res[0], surface: ag[b], direction: direction });
        }
      }
      end = direction < 0 ? 0 : 1;
      res = f(end, c);
      if (res[1] < target) { continue; }
      good = end; bad = L0;
      for (i = 0; i < 40; i++) {
        mid = (good + bad) / 2;
        if (f(mid, c)[1] >= target) { good = mid; } else { bad = mid; }
      }
      L = good;
      res = f(L, c);
      steps = 0;
      while (res[1] < target && steps < 20) {
        L = clamp01(L + direction * 0.001);
        res = f(L, c);
        steps++;
      }
      if (res[1] >= target) { return done(L, c, res[0], res[1], true); }
    }
    throw new SolveError('unreachable', { target: target, best: best.ratio, best_hex: best.hex });
  }

  // ---------- Unterscheidbare Farben auswählen (4.1.12)
  function pickDistinct(pool, k, kinds, start, bg) {
    kinds = kinds || WORST_KINDS;
    if (kinds.indexOf('tritan') >= 0) { throw new Error('Tritan geht in keine Auswahl ein'); }
    var cand = [], chosen = [], i, j, c, best, pick, r, m, s;
    for (i = 0; i < pool.length; i++) { c = normHex(pool[i]); if (cand.indexOf(c) < 0) { cand.push(c); } }
    if (k <= 0) { return chosen; }
    if (start !== null && start !== undefined) {
      s = normHex(start); chosen.push(s);
      if (cand.indexOf(s) >= 0) { cand.splice(cand.indexOf(s), 1); }
    } else if (cand.length) {
      pick = cand[0];
      if (bg !== null && bg !== undefined) {
        best = null;
        for (i = 0; i < cand.length; i++) {
          r = contrast(cand[i], bg);
          if (best === null || r > best + 1e-9) { best = r; pick = cand[i]; }
        }
      }
      chosen.push(pick); cand.splice(cand.indexOf(pick), 1);
    }
    while (chosen.length < k && cand.length) {
      best = null; pick = null;
      for (i = 0; i < cand.length; i++) {
        m = Infinity;
        for (j = 0; j < chosen.length; j++) { r = worstDistance(cand[i], chosen[j], kinds); if (r < m) { m = r; } }
        if (best === null || m > best + 1e-9) { best = m; pick = cand[i]; }
      }
      chosen.push(pick); cand.splice(cand.indexOf(pick), 1);
    }
    return chosen;
  }

  // ---------- Link-Fenster (4.1.13), Beamer (4.1.14), Schleier (4.1.15)
  function linkWindow(text, bgs) {
    if (!bgs || !bgs.length) { throw new Error('bgs ist leer'); }
    var yt = relLum(text), ys = [], i, allLight = true, allDark = true, lo, hi, pol, v;
    for (i = 0; i < bgs.length; i++) {
      ys.push(relLum(bgs[i]));
      if (!(ys[i] >= yt)) { allLight = false; }
      if (!(ys[i] <= yt)) { allDark = false; }
    }
    if (allLight) {
      lo = 3 * (yt + 0.05) - 0.05; hi = Infinity;
      for (i = 0; i < ys.length; i++) { v = (ys[i] + 0.05) / 4.5 - 0.05; if (v < hi) { hi = v; } }
      pol = 'dark-text';
    } else if (allDark) {
      lo = -Infinity;
      for (i = 0; i < ys.length; i++) { v = 4.5 * (ys[i] + 0.05) - 0.05; if (v > lo) { lo = v; } }
      hi = (yt + 0.05) / 3 - 0.05;
      pol = 'light-text';
    } else { throw new Error('Flächen liegen auf beiden Seiten des Texts'); }
    return { lo: lo, hi: hi, empty: lo > hi, polarity: pol };
  }
  function ambientRatio(room) {
    var p = K.projector;
    if (!Object.prototype.hasOwnProperty.call(p.ambient_lx, room)) { throw new Error('unbekanntes Raumlicht: ' + room); }
    return p.ambient_lx[room] / p.white_lx;
  }
  function ambientOf(a) { return typeof a === 'string' ? ambientRatio(a) : finite(a, 'Raumlicht'); }
  function projectedContrast(a, b, ambient) {
    var amb = ambientOf(ambient), n = K.projector.native;
    var ya = relLum(a), yb = relLum(b), hi = ya >= yb ? ya : yb, lo = ya >= yb ? yb : ya;
    return (hi * (1 - 1 / n) + 1 / n + amb) / (lo * (1 - 1 / n) + 1 / n + amb);
  }
  function projectorHex(h, ambient) {
    var amb = ambientOf(ambient), n = K.projector.native, s = hexToSrgb(h), out = [], i;
    for (i = 0; i < 3; i++) { out.push(gam((lin(s[i]) * (1 - 1 / n) + 1 / n + amb) / (1 + amb))); }
    return srgbToHex(out);
  }
  function scrimAlpha(text, scrim, target) {
    var t = normHex(text), s = normHex(scrim);
    finite(target, 'target');
    var worst = relLum(t) > relLum(s) ? '#FFFFFF' : '#000000', p = hexToSrgb(worst), sv = hexToSrgb(s);
    function mix(a) { return [a * sv[0] + (1 - a) * p[0], a * sv[1] + (1 - a) * p[1], a * sv[2] + (1 - a) * p[2]]; }
    if (contrast(t, mix(1)) < target) { return null; }
    var lo = 0, hi = 1, i, mid, pc, c, r, q, r8;
    for (i = 0; i < 60; i++) {
      mid = (lo + hi) / 2;
      if (contrast(t, mix(mid)) >= target) { hi = mid; } else { lo = mid; }
    }
    pc = Math.ceil(hi * 100 - 1e-9);
    for (;;) {
      c = mix(pc / 100); r = contrast(t, c); q = srgbToHex(c); r8 = contrast(t, q);
      if ((r >= target && r8 >= target) || pc >= 100) { break; }
      pc++;
    }
    return { alpha: hi, percent: pc, ratio_at_percent: r, ratio_at_percent_8bit: r8, worst: worst, mix_hex: q };
  }

  // ---------- Paarbewertung aus dem Rollenschema (4.1.16)
  function evaluate(task, rolesByMode, missing) {
    var out = { pairs: [], decorative: [], advisory: [] };
    var modes = task.modes && task.modes.length ? task.modes : Object.keys(rolesByMode);
    function role(roles, mode, rid) {
      if (Object.prototype.hasOwnProperty.call(roles, rid)) { return roles[rid]; }
      if (missing === 'skip') { return null; }
      throw new Error('evaluate ' + task.id + ': Rolle ' + rid + ' fehlt im Modus ' + mode);
    }
    var mi, li, bi, mode, roles, line, ons, a, b, r, lines;
    for (mi = 0; mi < modes.length; mi++) {
      mode = modes[mi];
      if (!Object.prototype.hasOwnProperty.call(rolesByMode, mode)) { throw new Error('evaluate ' + task.id + ': Modus ' + mode + ' fehlt'); }
      roles = rolesByMode[mode];
      lines = task.pairs || [];
      for (li = 0; li < lines.length; li++) {
        line = lines[li];
        for (bi = 0; bi < line.on.length; bi++) {
          a = role(roles, mode, line.fg); b = role(roles, mode, line.on[bi]);
          if (a === null || b === null) { continue; }
          r = contrast(a, b);
          out.pairs.push({ mode: mode, fg: line.fg, bg: line.on[bi], ratio: r, min: line.min, criterion: line.criterion, rule: line.rule, pass: r >= line.min });
        }
      }
      lines = task.decorative || [];
      for (li = 0; li < lines.length; li++) {
        line = lines[li];
        for (bi = 0; bi < line.on.length; bi++) {
          a = role(roles, mode, line.fg); b = role(roles, mode, line.on[bi]);
          if (a === null || b === null) { continue; }
          out.decorative.push({ mode: mode, fg: line.fg, bg: line.on[bi], ratio: contrast(a, b) });
        }
      }
      lines = task.advisory || [];
      for (li = 0; li < lines.length; li++) {
        line = lines[li];
        ons = typeof line.on === 'string' ? [line.on] : line.on;
        for (bi = 0; bi < ons.length; bi++) {
          a = role(roles, mode, line.fg); b = role(roles, mode, ons[bi]);
          if (a === null || b === null) { continue; }
          r = contrast(a, b);
          out.advisory.push({ mode: mode, fg: line.fg, bg: ons[bi], ratio: r, min: line.min, finding: line.finding, pass: r >= line.min });
        }
      }
    }
    return out;
  }

  // ---------- Vergleichswerte (4.1.8)
  function comparisonColors(spec, datasets) {
    var out = [], i, ds, scheme, ex, n;
    if (spec.generate !== undefined) {
      if (spec.generate !== 'hsl-hues') { throw new Error('unbekannter Generator: ' + spec.generate); }
      n = spec.n;
      for (i = 0; i < n; i++) { out.push(srgbToHex(hslToRgb(i * 360 / n, spec.s, spec.l))); }
      return out;
    }
    ds = datasets && datasets[spec.dataset];
    if (!ds) { throw new Error('Datensatz fehlt: ' + spec.dataset); }
    for (i = 0; i < ds.schemes.length; i++) { if (ds.schemes[i].id === spec.scheme) { scheme = ds.schemes[i]; } }
    if (!scheme) { throw new Error('Schema fehlt: ' + spec.scheme); }
    ex = spec.exclude || [];
    for (i = 0; i < scheme.colors.length; i++) { if (ex.indexOf(scheme.colors[i].name) < 0) { out.push(normHex(scheme.colors[i].hex)); } }
    return out;
  }
  var refCache = null;
  // referenceValues(comparisons, datasets): ohne Argumente aus FS_CONST.comparisons und FS_CONST.datasets
  function referenceValues(comparisons, datasets) {
    var dflt = comparisons === undefined && datasets === undefined;
    if (dflt && refCache) { return refCache; }
    var comps = comparisons || K.comparisons, dss = datasets || K.datasets, out = {}, i, comp, cols, md;
    if (!comps || !dss) { throw new Error('referenceValues braucht comparisons und datasets (data/comparisons.json, data/datasets/*.json)'); }
    for (i = 0; i < comps.comparisons.length; i++) {
      comp = comps.comparisons[i];
      cols = comparisonColors(comp.colors, dss);
      md = minDistance(cols, comp.kinds);
      out[comp.id] = { value: md.value, a: md.a, b: md.b, kind: md.kind, colors: cols, kinds: comp.kinds.slice() };
    }
    if (dflt) { refCache = out; }
    return out;
  }

  // ---------- Platzhalter (6.12)
  function RenderError(message) {
    this.name = 'RenderError'; this.message = message;
    if (Error.captureStackTrace) { Error.captureStackTrace(this, RenderError); } else { this.stack = (new Error(message)).stack; }
  }
  RenderError.prototype = Object.create(Error.prototype);
  RenderError.prototype.constructor = RenderError;
  var PLACEHOLDER_SRC = '\\{(cr|dist|gray|gs|L|proj|scrim|ref|hex|count|date)(?::([^{}]*))?\\}';
  var ARITY = { cr: 2, dist: 3, gray: 1, gs: 2, L: 1, proj: 3, scrim: 3, ref: 1, hex: 1, count: 1, date: 0 };
  var MONTHS = {
    de: ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'],
    en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  };
  var DATE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/;
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
  }
  function findPlaceholders(template) {
    var re = new RegExp(PLACEHOLDER_SRC, 'g'), out = [], m;
    while ((m = re.exec(template)) !== null) { out.push([m[1], m[2] === undefined ? null : m[2]]); }
    return out;
  }
  function rolesByModeOf(ctx) {
    if (ctx.roles) { return ctx.roles; }
    return ctx.palette ? ctx.palette.roles : null;
  }
  function firstKey(o) { var k; for (k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) { return k; } } return null; }
  function operand(tok, mode, ctx, where) {
    if (tok.charAt(0) === '#') {
      if (!HEX6.test(tok)) { throw new RenderError(where + ': kein Hex #RRGGBB: ' + tok); }
      return tok.toUpperCase();
    }
    var rbm = rolesByModeOf(ctx), m;
    if (!rbm || firstKey(rbm) === null) { throw new RenderError(where + ': Rolle ' + tok + ' ohne Palette'); }
    m = mode || ctx.mode || null;
    if (m === null) {
      if (Object.keys(rbm).length !== 1) { throw new RenderError(where + ': Rolle ' + tok + ' ohne Modus (@light/@dark)'); }
      m = firstKey(rbm);
    }
    if (!Object.prototype.hasOwnProperty.call(rbm, m) || !Object.prototype.hasOwnProperty.call(rbm[m], tok)) {
      throw new RenderError(where + ': Rolle ' + tok + ' fehlt im Modus ' + m);
    }
    return normHex(rbm[m][tok]);
  }
  function numberOf(tok, where) {
    var v = num(tok);
    if (v === null || !isFinite(v)) { throw new RenderError(where + ': keine Zahl: ' + tok); }
    return v;
  }
  function refValue(rid, ctx, where) {
    var refs = ctx && ctx.refs ? ctx.refs : null, v;
    if (refs === null) {
      try { refs = referenceValues(); } catch (e) { throw new RenderError(where + ': ' + e.message); }
    }
    if (!Object.prototype.hasOwnProperty.call(refs, rid)) { throw new RenderError(where + ': unbekannter Vergleichswert ' + rid); }
    v = refs[rid];
    return typeof v === 'object' && v !== null ? v.value : v;
  }
  function compute(m, a, b, k, t, rid, ctx, where) {
    var r;
    if (m === 'cr') { return contrast(a, b); }
    if (m === 'dist') {
      if (KINDS.indexOf(k) < 0) { throw new RenderError(where + ': unbekannte Sichtweise ' + k); }
      return distance(a, b, k);
    }
    if (m === 'gray') { return grayValue(a); }
    if (m === 'gs') { return grayDistance(a, b); }
    if (m === 'L') { return hexToOklch(a)[0]; }
    if (m === 'proj') {
      return projectedContrast(a, b, Object.prototype.hasOwnProperty.call(K.projector.ambient_lx, t) ? t : numberOf(t, where));
    }
    if (m === 'scrim') {
      r = scrimAlpha(a, b, numberOf(t, where));
      if (r === null) { throw new RenderError(where + ': Schleier erreicht das Ziel ' + t + ' nicht'); }
      return r.percent / 100;
    }
    if (m === 'ref') { return refValue(rid, ctx, where); }
    throw new RenderError(where + ': unbekannte Kennzahl ' + m);
  }
  function display(m, x, lang) {
    if (m === 'cr' || m === 'proj') { return fmtRatio(x, lang); }
    if (m === 'dist' || m === 'gs' || m === 'ref') { return fmtDist(x, lang); }
    if (m === 'scrim') { return fmtPctUp(x, lang); }
    return fmtL(x, lang);
  }
  function machine(m, x) {
    if (m === 'cr' || m === 'proj') { return fmtRatio(x, 'en').slice(0, -2); }
    if (m === 'scrim') { return String(Math.ceil(x * 100 - 1e-9)); }
    return display(m, x, 'en');
  }
  function tagHtml(tag) {
    var attrs = [['value', tag.value_attr], ['data-m', tag.m]], keys = ['a', 'b', 'k', 't', 'id', 'mode'], i, s = '<data class="num"';
    for (i = 0; i < keys.length; i++) { if (tag[keys[i]] !== null) { attrs.push(['data-' + keys[i], tag[keys[i]]]); } }
    for (i = 0; i < attrs.length; i++) { s += ' ' + attrs[i][0] + '="' + esc(attrs[i][1]) + '"'; }
    return s + '>' + esc(tag.text) + '</data>';
  }
  // dataTagText(attrs, lang, ctx): erwarteter Anzeigetext eines <data class="num"> (für test_honesty)
  function dataTagText(attrs, lang, ctx) {
    function g(key) { return attrs['data-' + key] !== undefined ? attrs['data-' + key] : (attrs[key] !== undefined ? attrs[key] : null); }
    var m = g('m'), where = '<data data-m=' + m + '>';
    var a = g('a') ? normHex(g('a')) : null, b = g('b') ? normHex(g('b')) : null;
    return display(m, compute(m, a, b, g('k'), g('t'), g('id'), ctx || {}, where), lang);
  }
  // renderText(template, ctx, lang, opts) → {html, tags}; opts.escape = false für vertrauenswürdiges HTML
  function renderText(template, ctx, lang, opts) {
    ctx = ctx || {};
    sep(lang);
    var escape = !(opts && opts.escape === false);
    var re = new RegExp(PLACEHOLDER_SRC, 'g'), out = [], tags = [], pos = 0, mt, lit, name, arg, where, mode, parts, i;
    var d, dm, y, mo, da, txt, counts, n, hx, a, b, k, t, rid, usesRole, x, tag, at;
    while ((mt = re.exec(template)) !== null) {
      lit = template.slice(pos, mt.index);
      out.push(escape ? esc(lit) : lit);
      pos = mt.index + mt[0].length;
      name = mt[1]; arg = mt[2] === undefined ? null : mt[2]; where = mt[0];
      if (name === 'date') {
        if (arg !== null) { throw new RenderError(where + ': date hat keine Argumente'); }
        d = ctx.date;
        dm = DATE.exec(typeof d === 'string' ? d : '');
        if (!dm) { throw new RenderError(where + ': ctx.date fehlt oder ist kein JJJJ-MM-TT'); }
        y = parseInt(dm[1], 10); mo = parseInt(dm[2], 10); da = parseInt(dm[3], 10);
        if (mo < 1 || mo > 12 || da < 1 || da > 31) { throw new RenderError(where + ': ungültiges Datum ' + d); }
        txt = lang === 'de' ? da + '. ' + MONTHS.de[mo - 1] + ' ' + y : MONTHS.en[mo - 1] + ' ' + da + ', ' + y;
        out.push('<data class="date" value="' + d + '">' + txt + '</data>');
        tags.push({ m: 'date', value: d, text: txt });
        continue;
      }
      if (arg === null) { throw new RenderError(where + ': Argumente fehlen'); }
      mode = null;
      at = arg.lastIndexOf('@');
      if (at >= 0) {
        mode = arg.slice(at + 1); arg = arg.slice(0, at);
        if (!mode) { throw new RenderError(where + ': leerer Modus'); }
      }
      parts = arg.split('/');
      if (parts.length !== ARITY[name]) { throw new RenderError(where + ': erwartet ' + ARITY[name] + ' Argumente'); }
      for (i = 0; i < parts.length; i++) { if (parts[i] === '') { throw new RenderError(where + ': erwartet ' + ARITY[name] + ' Argumente'); } }
      if (name === 'count') {
        counts = ctx.counts || {};
        if (!Object.prototype.hasOwnProperty.call(counts, parts[0])) { throw new RenderError(where + ': Zähler ' + parts[0] + ' fehlt in ctx.counts'); }
        n = counts[parts[0]];
        txt = fmtCount(n, lang);
        out.push('<data class="count" value="' + n + '">' + esc(txt) + '</data>');
        tags.push({ m: 'count', value: n, text: txt });
        continue;
      }
      if (name === 'hex') {
        hx = operand(parts[0], mode, ctx, where);
        out.push('<data class="hex" value="' + hx + '"><code>' + hx + '</code></data>');
        tags.push({ m: 'hex', value: hx, text: hx });
        continue;
      }
      a = null; b = null; k = null; t = null; rid = null;
      if (name === 'ref') {
        if (mode !== null) { throw new RenderError(where + ': ref hat keinen Modus'); }
        rid = parts[0];
      } else {
        a = operand(parts[0], mode, ctx, where);
        if (['cr', 'dist', 'gs', 'proj', 'scrim'].indexOf(name) >= 0) { b = operand(parts[1], mode, ctx, where); }
        if (name === 'dist') { k = parts[2]; }
        if (name === 'proj' || name === 'scrim') { t = parts[2]; }
      }
      usesRole = name !== 'ref' && (parts[0].charAt(0) !== '#' || (parts.length > 1 && parts[1].charAt(0) !== '#'));
      x = compute(name, a, b, k, t, rid, ctx, where);
      txt = display(name, x, lang);
      tag = { m: name, a: a, b: b, k: k, t: t, id: rid,
        mode: usesRole ? (mode || ctx.mode || firstKey(rolesByModeOf(ctx))) : null,
        value: x, value_attr: machine(name, x), text: txt };
      out.push(tagHtml(tag));
      tags.push(tag);
    }
    lit = template.slice(pos);
    out.push(escape ? esc(lit) : lit);
    return { html: out.join(''), tags: tags };
  }

  return {
    version: K.version, KINDS: KINDS, WORST_KINDS: WORST_KINDS, JND_DISTANCE: JND_DISTANCE,
    parse: parse, parseError: parseError, composite: composite,
    lin: lin, gam: gam, quantize: quantize, normHex: normHex, hexToSrgb: hexToSrgb, srgbToHex: srgbToHex,
    srgbToXyz: srgbToXyz, xyzToOklab: xyzToOklab, oklabToXyz: oklabToXyz,
    srgbToOklab: srgbToOklab, oklabToSrgb: oklabToSrgb, oklabToOklch: oklabToOklch, oklchToOklab: oklchToOklab,
    p3ToSrgb: p3ToSrgb, p3ToOklab: p3ToOklab, deltaEok: deltaEok,
    gamutMap: gamutMap, oklchToHex: oklchToHex, hexToOklch: hexToOklch,
    relLum: relLum, contrast: contrast, grayValue: grayValue, grayHex: grayHex, grayDistance: grayDistance,
    simOklab: simOklab, simHex: simHex, distance: distance, worstDistance: worstDistance, minDistance: minDistance,
    fmtRatio: fmtRatio, fmtDist: fmtDist, fmtPctUp: fmtPctUp, fmtL: fmtL, fmtCount: fmtCount, fmtLum: fmtLum,
    shortestOklch: shortestOklch, solveL: solveL, SolveError: SolveError, pickDistinct: pickDistinct,
    linkWindow: linkWindow, ambientRatio: ambientRatio, projectedContrast: projectedContrast, projectorHex: projectorHex,
    scrimAlpha: scrimAlpha, evaluate: evaluate, referenceValues: referenceValues,
    renderText: renderText, RenderError: RenderError, dataTagText: dataTagText, findPlaceholders: findPlaceholders, esc: esc
  };
}));
