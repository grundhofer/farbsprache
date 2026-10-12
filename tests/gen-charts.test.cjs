'use strict';
// Generator Diagramm (FS.gen.charts): Parität mit tools/gen/charts.py über eine breite Matrix aus Datentyp, Familie,
// Anzahl, Hintergrund, Darstellung, Druck und eigenen Farben (über die 60 Seeds des generischen Paritätstests hinaus,
// die nur die Standardoptionen nutzen). Python rechnet dieselben Fälle in einem Kindprozess (python3 oder $PYTHON):
// Palette, Muster-Variablen und JS-Array-Export, verglichen Hex und Text exakt, Zahlen mit Toleranz 1e-9.
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { test } = require('node:test');
const { ROOT, jload, load, plain } = require('./helpers.cjs');

const FAMS = { cat: ['okabe-ito', 'tol-bright', 'tol-muted'], seq: ['viridis', 'cb-blues', 'seed'], div: ['blue-orange', 'cb-rdbu', 'cb-puor', 'seed'], hl: ['gray'] };
const NS = { cat: [2, 5, 8], seq: [3, 6, 9], div: [3, 5, 9], hl: [1] };
const SEEDS = [null, '#F2A900', '#E63946', '#000000', '#FFFFFF', '#808080', '#16191D', '#2CA02C'];

function cases() {
  const out = [];
  for (const t of Object.keys(FAMS)) {
    for (const fam of FAMS[t]) for (const n of NS[t]) for (const bg of ['light', 'dark']) for (const pr of [false, true]) {
      for (const mark of t === 'cat' ? ['lines', 'areas'] : ['lines']) {
        for (const seed of SEEDS) out.push({ seed, colors: null, options: { t, n, pr, bg, mark, fam } });
      }
    }
  }
  return out;
}

const PY = `
import json, sys
sys.path.insert(0, sys.argv[1])
from tools import color as C, export as X
from tools.gen import charts as G
from web.copy import charts as CC, core as CO
root = sys.argv[1]
def jl(p): return json.load(open(root + '/' + p, encoding='utf-8'))
task = jl('data/tasks/charts.json')
ds = {n: jl('data/datasets/' + n + '.json') for n in ('okabe-ito', 'tol', 'colorbrewer', 'viridis')}
ctx = {'datasets': ds, 'comparisons': jl('data/comparisons.json'), 'lang': None, 'data': {}}
out = []
for inp in json.load(sys.stdin):
    try:
        pal = G.build(task, inp, ctx)
    except C.SolveError as e:
        out.append({'ok': False, 'error': e.key}); continue
    pal.update({'preset': None, 'name_de': 'Eigene Farbe', 'name_en': 'Your color'})
    ex = {}
    for lang in ('de', 'en'):
        ectx = {'date': '2026-10-11', 'url': 'https://example.org/?x=1', 'name': pal['name_' + lang], 'task_name': task['name_' + lang],
                'core': CO.COPY[lang]['export'], 'text': CC.COPY[lang]['charts'], 'rules': [], 'sources': {}, 'refs': {}, 'datasets': ds, 'data': {}}
        ex[lang] = {'ctx': ectx, 'js': G.exports['js'](pal, task, ectx, lang, {}),
                    'name': G.display_name(pal, CC.COPY[lang]['charts'], lang),
                    'fmts': {f: [b['text'] for b in X.render(f, pal, task, ectx, lang, {}, G)] for f in ('hex', 'css', 'dtcg', 'agent')}}
    out.append({'ok': True, 'palette': pal, 'view': G.view_vars(pal, 'default', {}), 'ex': ex})
print(json.dumps(out, allow_nan=False))
`;

function diff(a, b, where, out) {
  if (out.length > 20) return out;
  if (typeof a === 'number' && typeof b === 'number') {
    if (Math.abs(a - b) > 1e-9 * Math.max(1, Math.abs(a), Math.abs(b))) out.push(`${where}: ${a} gegen ${b}`);
    return out;
  }
  if ((a === null || a === undefined) && (b === null || b === undefined)) return out;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) { out.push(`${where}: Länge ${a.length} gegen ${b.length}`); return out; }
    a.forEach((x, i) => diff(x, b[i], `${where}[${i}]`, out));
    return out;
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const ka = Object.keys(a), kb = Object.keys(b);
    if (JSON.stringify(ka) !== JSON.stringify(kb)) out.push(`${where}: Schlüssel ${ka} gegen ${kb}`);
    for (const k of new Set(ka.concat(kb))) diff(a[k], b[k], `${where}.${k}`, out);
    return out;
  }
  if (a !== b) out.push(`${where}: ${JSON.stringify(a)} gegen ${JSON.stringify(b)}`);
  return out;
}

const CASES = cases();
let PYOUT = null, PYERR = null;
try {
  PYOUT = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c', PY, ROOT], { input: JSON.stringify(CASES), maxBuffer: 1 << 30, cwd: ROOT }).toString());
} catch (e) { PYERR = e; }

test(`Python rechnet die Matrix (${CASES.length} Fälle)`, () => {
  assert.equal(PYERR, null, PYERR && String(PYERR));
  assert.equal(PYOUT.length, CASES.length);
});

test('Parität Python/JS: Palette, Muster-Variablen, Name, JS-Array und Exporte über die ganze Matrix', () => {
  const ctx = load(['color.js', 'export.js', 'gen/charts.js']);
  const G = ctx.FS.gen.charts;
  const task = jload('data/tasks/charts.json');
  const ds = {};
  for (const n of ['okabe-ito', 'tol', 'colorbrewer', 'viridis']) ds[n] = jload(`data/datasets/${n}.json`);
  const gctx = { datasets: ds, comparisons: jload('data/comparisons.json'), lang: null, data: {} };
  const errs = [];
  let ok = 0, changed = 0, low = 0, grayHl = 0;
  CASES.forEach((inp, i) => {
    const py = PYOUT[i], label = JSON.stringify(inp);
    let pal;
    try { pal = G.build(task, JSON.parse(JSON.stringify(inp)), gctx); } catch (e) {
      if (py.ok || e.key !== py.error) errs.push(`${label}: JS ${e.key || e}, Python ${py.ok ? 'ok' : py.error}`);
      return;
    }
    if (!py.ok) { errs.push(`${label}: Python ${py.error}, JS ok`); return; }
    pal.preset = null; pal.name_de = 'Eigene Farbe'; pal.name_en = 'Your color';
    for (const d of diff(py.palette, plain(pal), label, [])) errs.push(d);
    for (const d of diff(py.view, plain(G.viewVars(pal, 'default', {})), label + ' view', [])) errs.push(d);
    for (const lang of ['de', 'en']) {
      const js = G.exports.js(pal, task, py.ex[lang].ctx, lang, {});
      if (js !== py.ex[lang].js) errs.push(`${label} js ${lang}:\n${js}\n--- Python:\n${py.ex[lang].js}`);
      // Name eigener Zustände (gen.displayName) und die Exporte mit Exportnamen und Zweck unter 3:1 (nach Z)
      const name = G.displayName(pal, py.ex[lang].ctx.text, lang);
      if (name !== py.ex[lang].name) errs.push(`${label} Name ${lang}: ${name} gegen ${py.ex[lang].name}`);
      for (const f of Object.keys(py.ex[lang].fmts)) {
        const got = ctx.FS.export.render(f, pal, task, py.ex[lang].ctx, lang, {}, G).map((b) => b.text);
        if (JSON.stringify(got) !== JSON.stringify(py.ex[lang].fmts[f])) errs.push(`${label} ${f} ${lang}:\n${got.join('\n')}\n--- Python:\n${py.ex[lang].fmts[f].join('\n')}`);
      }
    }
    ok++; changed += pal.changes.length ? 1 : 0; low += pal.findings.some((f) => f.id === 'low-contrast') ? 1 : 0;
    grayHl += pal.changes.some((c) => c.key === 'highlight-gray') ? 1 : 0;
  });
  assert.deepEqual(errs.slice(0, 10), []);
  assert.equal(ok, CASES.length, 'jeder Fall rechnet');
  assert.ok(changed > 0 && low > 0, 'die Matrix deckt Änderungshinweise und Flächen unter 3:1 ab');
  assert.ok(grayHl > 0, 'die Matrix deckt den Rückfall auf Okabe-Blau bei der Hervorhebung ab');
});

test('JS: Okabe-Ito auf Weiß, Rot-Grün-Regel, Kachelkarte', () => {
  const ctx = load(['color.js', 'export.js', 'gen/charts.js']);
  const G = ctx.FS.gen.charts;
  const task = jload('data/tasks/charts.json');
  const ds = { 'okabe-ito': jload('data/datasets/okabe-ito.json') };
  const pal = G.build(task, { seed: null, colors: null, options: { t: 'cat', n: 7, pr: false, bg: 'light', mark: 'lines', fam: 'okabe-ito' } },
    { datasets: ds, comparisons: jload('data/comparisons.json'), lang: null, data: {} });
  assert.deepEqual(plain(pal.roles.default), { 'series-1': '#0072B2', 'series-2': '#D55E00', 'series-3': '#009E73', 'series-4': '#CC79A7',
    bg: '#FFFFFF', text: '#222222', 'text-2': '#555555', grid: '#DEDEDE' });
  assert.ok(pal.extra.summary.indexOf('summary.pool') >= 0);
  assert.deepEqual(plain(G.redGreen(30, 140)), [255, true]);
  assert.deepEqual(plain(G.redGreen(140, 30)), [255, true]);
  assert.deepEqual(plain(G.redGreen(30, 210)), [210, false]);
  for (let h = 0; h < 360; h++) assert.equal(G.redGreen(h, (h + 180) % 360)[1], false);
  for (let n = 3; n <= 9; n++) {
    const bins = new Set(G.TILE.map((v) => Math.floor(v * n / 100)));
    assert.equal(bins.size, n, `n=${n}`);
  }
});

test('Grep: kein round(, toFixed( oder Math.round( in den Diagramm-Skripten', () => {
  const fs = require('node:fs');
  for (const f of ['web/gen/charts.js', 'web/ui/charts.js', 'tools/gen/charts.py']) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    for (const bad of ['round(', 'toFixed(', 'Math.round(']) assert.ok(!src.includes(bad), `${f}: ${bad}`);
  }
});
