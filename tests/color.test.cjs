'use strict';
// Farbkern web/color.js: dieselben Testvektoren wie tests/test_color.py, Formatierer, Parser,
// Invarianten und der Grep-Test gegen toFixed( und Math.round(.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { ROOT, jload, load, plain, camel } = require('./helpers.cjs');

const extra = { comparisons: jload('data/comparisons.json'), datasets: { 'okabe-ito': jload('data/datasets/okabe-ito.json') } };
const ctx = load(['color.js'], extra);
const C = ctx.FS.color;
const TV = jload('data/testvectors.json');
const UNCHECKED_KINDS = ['lab_d50', 'lch_d50', 'xyz_d50'];

// ---- gemeinsamer Vektor-Runner (gleiche Semantik wie tests/test_color.py)
function resolve(a) {
  if (Array.isArray(a)) return a.map(resolve);
  if (a && typeof a === 'object') {
    if ('$oklch' in a) { let v = C.hexToOklch(a.$oklch)[a.i]; for (const m of a.mul || []) v = v * m; return v; }
    if ('$oklch_hex' in a) { const r = resolve(a.$oklch_hex); return C.oklchToHex(r[0], r[1], r[2]); }
    if ('$solve_hex' in a) return C.solveL.apply(null, resolve(a.$solve_hex)).hex;
    if ('$min_contrast' in a) return a.$min_contrast.filter((x) => C.contrast(x, a.bg) >= a.min);
    if ('$mix' in a) {
      const [s, p, al] = a.$mix; const sv = C.hexToSrgb(s); const pv = C.hexToSrgb(p);
      return [0, 1, 2].map((i) => al * sv[i] + (1 - al) * pv[i]);
    }
    throw new Error('unbekanntes Makro ' + JSON.stringify(a));
  }
  return a;
}
function call(fn, args) {
  if (fn === 'len') return args[0].length;
  if (fn === 'identity') return args[0];
  const f = C[camel(fn)];
  assert.equal(typeof f, 'function', 'Funktion fehlt in FS.color: ' + camel(fn));
  return f.apply(null, args);
}
function same(v, e, tol) {
  tol = tol || 0;
  if (e === null) return v === null || v === undefined || (typeof v === 'number' && v !== v);
  if (typeof e === 'boolean') return v === e;
  if (typeof e === 'string') return v === e;
  if (typeof e === 'number') return typeof v === 'number' && Math.abs(v - e) <= tol;
  if (Array.isArray(e)) return v !== null && typeof v === 'object' && v.length === e.length && e.every((x, i) => same(v[i], x, tol));
  throw new Error('unbekannte Erwartung ' + JSON.stringify(e));
}
function runCase(c) {
  let value = call(c.fn, resolve(c.args));
  for (const p of c.pick || []) value = value[p];
  if (c.fields) value = c.fields.map((f) => value[f]);
  if (c.format) value = call(c.format[0], [value].concat(c.format.slice(1)));
  return value;
}
function assertLch(got, exp, tol, label) {
  assert.ok(Math.abs(got[0] - exp[0]) <= tol.L, label + ' L ' + got + ' / ' + exp);
  assert.ok(Math.abs(got[1] - exp[1]) <= tol.C, label + ' C ' + got + ' / ' + exp);
  if (exp[1] > tol.h_min_c) {
    const d = Math.abs(got[2] - exp[2]) % 360;
    assert.ok(Math.min(d, 360 - d) <= tol.h, label + ' h ' + got + ' / ' + exp);
  }
}

test('Vektoren srgb_oklch (CSS Color 4)', () => {
  const sec = TV.srgb_oklch; const tol = sec.tol;
  assert.equal(sec.vectors.length, 18);
  let checked = 0; let unchecked = 0;
  for (const vec of sec.vectors) {
    const kind = Object.keys(vec.input)[0]; const val = vec.input[kind];
    let lchIn = null; let srgb = null; let lab = null;
    if (kind === 'hex') srgb = C.hexToSrgb(val);
    else if (kind === 'css') srgb = C.parse(val).srgb;
    else if (kind === 'srgb') srgb = val;
    else if (kind === 'oklch') { lchIn = val; lab = C.oklchToOklab(val); srgb = C.oklabToSrgb(lab); } else if (kind === 'p3') { srgb = C.p3ToSrgb(val); lab = C.p3ToOklab(val); } else if (kind === 'xyz') lab = C.xyzToOklab(val);
    if (lab === null && srgb !== null) lab = C.srgbToOklab(srgb);
    for (const e of vec.expect) {
      const label = vec.id + ' ' + e.as;
      if (e.checked === false) { assert.ok(UNCHECKED_KINDS.includes(e.as), label); unchecked++; continue; }
      checked++;
      const t = e.tol === undefined ? 0.0005 : e.tol;
      if (e.as === 'oklch') assertLch(C.oklabToOklch(lab), e.value, tol, label);
      else if (e.as === 'hex') assert.equal(lchIn ? C.oklchToHex(lchIn[0], lchIn[1], lchIn[2]) : C.srgbToHex(srgb), e.value, label);
      else if (e.as === 'srgb') assert.ok(same(srgb, e.value, t), label);
      else if (e.as === 'srgb_linear') assert.ok(same(srgb.map(C.lin), e.value, t), label);
      else if (e.as === 'xyz_d65') assert.ok(same(C.srgbToXyz(srgb), e.value, t), label);
      else if (e.as === 'p3') assertLch(C.oklabToOklch(C.p3ToOklab(e.value)), lchIn, tol, label);
      else assert.fail('unbekannte Erwartung ' + label);
    }
  }
  assert.deepEqual([checked, unchecked], [16, 8]);
});

test('Vektoren ottosson, wcag, gamut, cvd_display', () => {
  for (const vec of TV.ottosson.vectors) assert.ok(same(C.xyzToOklab(vec.xyz), vec.oklab, TV.ottosson.tol), JSON.stringify(vec));
  for (const vec of TV.wcag.vectors) {
    assert.ok(Math.abs(C.contrast(vec.a, vec.b) - vec.expect) <= TV.wcag.tol, vec.a);
    assert.equal(C.contrast(vec.a, vec.b), C.contrast(vec.b, vec.a));
  }
  for (const vec of TV.gamut.vectors) {
    let got;
    if (vec.fn === 'oklab_to_srgb_of_oklch') got = C.oklabToSrgb(C.oklchToOklab(vec.input));
    else if (vec.fn === 'gamut_map_p3') { const l = C.oklabToOklch(C.p3ToOklab(vec.input)); got = C.gamutMap(l[0], l[1], l[2]); } else got = C.gamutMap(vec.input[0], vec.input[1], vec.input[2]);
    assert.ok(same(got, vec.expect, TV.gamut.tol), vec.id + ' ' + got);
    if (vec.hex) { assert.equal(C.srgbToHex(got), vec.hex, vec.id); assert.ok(got.every((x) => x >= 0 && x <= 1)); }
  }
  for (const vec of TV.cvd_display.vectors) {
    for (const kind of ['protan', 'deutan', 'tritan']) assert.equal(C.simHex(vec.in, kind), vec[kind], vec.in + ' ' + kind);
  }
});

test('Parser: Leerraum am Rand wird linear getrimmt, auch Unicode-Leerraum', () => {
  for (const w of [' ', '\t', '\n', '\r', '\f', '\v', '\u00a0', '\u1680', '\u2003', '\u2028', '\u202f', '\u3000', '\ufeff']) {
    assert.equal(C.parse(w + w + '#E63946' + w).hex, '#E63946', JSON.stringify(w));
    assert.equal(C.parse('rgb(' + w + '1 2 3' + w + ')').hex, '#010203', JSON.stringify(w));
  }
  assert.equal(C.parse('\u200b#E63946'), null, 'Nullbreite ist kein Leerraum nach CSS');
  const sp = ' '.repeat(200000), t0 = Date.now();
  assert.equal(C.parse('x' + sp + 'x'), null);
  assert.equal(C.parse(sp + '#11697A' + sp).hex, '#11697A');
  assert.ok(Date.now() - t0 < 1000, `zu langsam: ${Date.now() - t0} ms`);
});

test('Vektoren parser', () => {
  assert.ok(TV.parser.vectors.length >= 30);
  for (const vec of TV.parser.vectors) {
    const bare = vec.bare === undefined ? true : vec.bare;
    const r = C.parse(vec.in, bare);
    if (vec.error !== undefined) {
      assert.equal(r, null, vec.in);
      assert.equal(C.parseError(vec.in, bare), vec.error, vec.in);
      continue;
    }
    assert.notEqual(r, null, vec.in + ' ' + C.parseError(vec.in, bare));
    assert.equal(C.parseError(vec.in, bare), null);
    assert.equal(r.hex, vec.hex, vec.in);
    assert.ok(Math.abs(r.alpha - (vec.alpha === undefined ? 1 : vec.alpha)) <= 1e-12, vec.in);
    if (vec.oog !== undefined) assert.equal(r.out_of_gamut, vec.oog, vec.in);
    if (r.out_of_gamut) assert.ok(r.mapped_distance > 0); else assert.equal(r.mapped_distance, null);
    assert.ok(r.srgb.every((x) => x >= 0 && x <= 1));
    assert.equal(C.srgbToHex(r.srgb), r.hex);
  }
});

test('Vektoren format', () => {
  for (const vec of TV.format.vectors) assert.equal(call(vec.fn, vec.args), vec.expect, vec.fn + ' ' + JSON.stringify(vec.args));
});

test('Vektoren cases (Fachfälle)', () => {
  for (const c of TV.cases.vectors) {
    if (c.raises) {
      assert.throws(() => runCase(c), (e) => e instanceof C[c.raises] && e.key === c.key, c.id);
      continue;
    }
    const got = runCase(c);
    assert.ok(same(got, c.expect, c.tol), c.id + ': ' + JSON.stringify(got) + ' statt ' + JSON.stringify(c.expect));
  }
});

test('Vektoren placeholders', () => {
  for (const vec of TV.placeholders.vectors) {
    const r = C.renderText(vec.template, {}, vec.lang);
    assert.equal(r.tags.length, 1);
    assert.equal(r.tags[0].text, vec.text);
    assert.ok(r.html.startsWith('<data class="num" ') && r.html.endsWith('>' + vec.text + '</data>'), r.html);
    const attrs = {}; const re = / (data-[a-z]+|value)="([^"]*)"/g; let m;
    while ((m = re.exec(r.html)) !== null) attrs[m[1]] = m[2];
    assert.equal(C.dataTagText(attrs, vec.lang), vec.text);
  }
});

test('Formatierer: Prozent-Rundlauf, Abschneiden, Fehler', () => {
  for (let p = 0; p <= 100; p++) {
    assert.equal(C.fmtPctUp(p / 100, 'en'), p + '%');
    assert.equal(C.fmtPctUp(p / 100, 'de'), p + '\u202f%');
  }
  for (const t of [3.0, 4.5, 7.0, 4.95, 3.3]) assert.ok(parseFloat(C.fmtRatio(t - 1e-12, 'en', t)) < t);
  assert.throws(() => C.fmtRatio(NaN, 'de'));
  assert.throws(() => C.fmtDist(1, 'fr'));
  assert.throws(() => C.fmtCount(1.5, 'de'));
  assert.throws(() => C.quantize(NaN));
});

test('Löser: Ergebnisse bestehen nach Quantisierung', () => {
  let ok = 0; let seed = 11;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  for (let n = 0; n < 150; n++) {
    const C0 = rnd() * 0.25; const h = rnd() * 360; const light = rnd() < 0.5;
    const target = [3.0, 4.5, 4.95, 7.0][Math.floor(rnd() * 4)];
    const against = light ? ['#FFFFFF', '#F8FBFB'] : ['#101516', '#16191D'];
    const L0 = 0.4 + rnd() * 0.3;
    let r;
    try { r = C.solveL(C0, h, against, target, light ? -1 : 1, L0); } catch (e) {
      assert.ok(e instanceof C.SolveError && e.key === 'unreachable', String(e)); continue;
    }
    ok++;
    assert.ok(Math.min(...against.map((b) => C.contrast(r.hex, b))) >= target);
    assert.equal(r.hex, C.oklchToHex(r.L, r.C, h));
    if (!r.changed) assert.equal(r.L, L0);
  }
  assert.ok(ok > 100);
  assert.throws(() => C.solveL(0.1, 10, ['#FFFFFF'], 4.5, 0, 0.5));
  assert.throws(() => C.solveL(0.1, 200, ['#FFFFFF'], 4.5, 1, 0.6), (e) => e instanceof C.SolveError && e.key === 'mixed-sides');
});

test('pick_distinct: deterministisch, Präfixe, Tritan ausgeschlossen', () => {
  const okabe = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7'];
  const full = plain(C.pickDistinct(okabe, 7, null, null, '#16191D'));
  for (let k = 1; k <= 7; k++) assert.deepEqual(plain(C.pickDistinct(okabe, k, null, null, '#16191D')), full.slice(0, k));
  assert.equal(C.pickDistinct(okabe, 3, null, '#11697a')[0], '#11697A');
  assert.throws(() => C.pickDistinct(okabe, 3, ['normal', 'tritan']));
});

test('Simulation und Graustufen: Invarianten', () => {
  for (const kind of C.KINDS) { assert.equal(C.simHex('#FFFFFF', kind), '#FFFFFF'); assert.equal(C.simHex('#000000', kind), '#000000'); }
  let seed = 3;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return Math.floor(seed / 2147483648 * 256); };
  for (let n = 0; n < 300; n++) {
    const h = C.srgbToHex([rnd() / 255, rnd() / 255, rnd() / 255]);
    for (const kind of ['protan', 'deutan']) { const s = C.simHex(h, kind); assert.equal(s.slice(1, 3), s.slice(3, 5), h + ' ' + kind); }
    const y = C.relLum(h); const g = C.gam(y);
    assert.ok(Math.abs(C.relLum([g, g, g]) - y) <= 1e-12);
  }
  assert.ok(Math.abs(C.grayValue('#808080') - C.hexToOklch('#808080')[0]) <= 1e-12);
  assert.equal(C.minDistance(['#000000']), null);
  assert.throws(() => C.simHex('#123456', 'achromat'));
});

test('evaluate und renderText mit Rollen', () => {
  const task = { id: 'probe', modes: ['light', 'dark'],
    pairs: [{ fg: 'text', on: ['bg', 'surface'], min: 4.5, criterion: '1.4.3', rule: 'text-contrast' }],
    decorative: [{ fg: 'border', on: ['bg'] }],
    advisory: [{ fg: 'accent', on: ['bg'], min: 3.0, finding: 'accent-fill-low' }] };
  const roles = { light: { bg: '#F8FBFB', surface: '#FFFFFF', text: '#182123', border: '#D2D9DB', accent: '#11697A' },
    dark: { bg: '#101516', surface: '#161C1D', text: '#E8ECED', border: '#2C3436', accent: '#276876' } };
  const r = plain(C.evaluate(task, roles));
  assert.equal(r.pairs.length, 4);
  assert.deepEqual(r.pairs.map((p) => p.mode), ['light', 'light', 'dark', 'dark']);
  assert.equal(r.pairs[0].ratio, C.contrast('#182123', '#F8FBFB'));
  assert.equal(r.advisory[1].finding, 'accent-fill-low');
  const html = C.renderText('{cr:accent/text@light}, {hex:accent@dark}, {count:pairs}, {date}', { roles, counts: { pairs: 1234 }, date: '2026-10-11' }, 'de').html;
  assert.ok(html.includes('<data class="hex" value="#276876"><code>#276876</code></data>'));
  assert.ok(html.includes('<data class="count" value="1234">1.234</data>'));
  assert.ok(html.includes('<data class="date" value="2026-10-11">11. Oktober 2026</data>'));
  assert.equal(C.renderText('a < b', {}, 'en').html, 'a &lt; b');
  assert.equal(C.renderText(':root{--bg: #fff}', {}, 'de').html, ':root{--bg: #fff}');
  assert.deepEqual(plain(C.findPlaceholders('x {cr:a/b@light} {date}')), [['cr', 'a/b@light'], ['date', null]]);
  assert.equal(C.composite('#000000', 0.5, '#FFFFFF'), '#808080');
  assert.equal(C.composite('#11697A', 0), '#FFFFFF');
  assert.equal(C.renderText('<b>x</b>', {}, 'en', { escape: false }).html, '<b>x</b>');
  for (const bad of ['{cr:#000000}', '{cr:accent/text}', '{dist:#000000/#FFFFFF/achromat}', '{scrim:#777777/#777777/4.5}', '{date}']) {
    assert.throws(() => C.renderText(bad, { roles }, 'de'), (e) => e instanceof C.RenderError, bad);
  }
});

test('Daten: CSS-Namen, Okabe-Ito, Seeds', () => {
  const names = jload('data/css-names.json');
  const keys = Object.keys(names).filter((k) => !k.startsWith('_'));
  assert.equal(keys.length, 148);
  assert.equal(new Set(keys.map((k) => names[k])).size, 139);
  for (const k of keys) assert.equal(C.parse(k).hex, names[k]);
  const seeds = jload('tests/parity_seeds.json').seeds;
  assert.equal(seeds.length, 60);
  for (const s of seeds) assert.notEqual(C.parse(s), null, s);
});

test('API des Farbkerns vollständig', () => {
  const names = ['parse', 'lin', 'gam', 'hexToSrgb', 'srgbToHex', 'quantize', 'srgbToOklab', 'oklabToSrgb', 'oklabToOklch',
    'oklchToOklab', 'p3ToSrgb', 'gamutMap', 'oklchToHex', 'hexToOklch', 'relLum', 'contrast', 'grayValue', 'grayHex',
    'grayDistance', 'simOklab', 'simHex', 'distance', 'worstDistance', 'minDistance', 'fmtRatio', 'fmtDist', 'fmtPctUp',
    'fmtL', 'fmtCount', 'fmtLum', 'shortestOklch', 'solveL', 'SolveError', 'pickDistinct', 'linkWindow',
    'projectedContrast', 'projectorHex', 'scrimAlpha', 'evaluate', 'renderText', 'referenceValues'];
  for (const n of names) assert.equal(typeof C[n], 'function', n);
  assert.equal(C.JND_DISTANCE, 2);
  assert.equal(ctx.FS.color, C);
});

test('Grep: kein toFixed( und kein Math.round( außerhalb von // quantize', () => {
  const files = [path.join(ROOT, 'web', 'color.js'), path.join(ROOT, 'web', 'export.js')];
  const gen = path.join(ROOT, 'web', 'gen');
  if (fs.existsSync(gen)) for (const f of fs.readdirSync(gen).sort()) if (f.endsWith('.js')) files.push(path.join(gen, f));
  assert.ok(fs.existsSync(files[0]));
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    fs.readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
      assert.ok(!line.includes('toFixed('), f + ':' + (i + 1));
      if (line.includes('Math.round(')) assert.ok(line.includes('// quantize'), f + ':' + (i + 1));
    });
  }
});
