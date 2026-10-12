'use strict';
// Parität Python/JS (Spezifikation 7.9): dieselben Eingaben wie tools/parity.py durch FS.gen[<aufgabe>].build.
// Hex und Texte exakt, Gleitkomma mit Toleranz 1e-9 (relativ ab Betrag 1). Keine Bitgleichheit behauptet.
// Fälle opt:… sind eigene Zustände ohne eigene Farbe; mit Namenshaken vergleicht der Test auch displayName.
// Vorher: python3 tools/parity.py (schreibt tests/out/parity.json).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT, jload, constants, js } = require('./helpers.cjs');

const FILE = path.join(ROOT, 'tests', 'out', 'parity.json');
const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';

function context(genFiles) {
  const ctx = { FS_CONST: constants() };
  vm.createContext(ctx);
  for (const f of ['web/color.js', 'web/export.js', 'web/site.js'].concat(genFiles)) {
    vm.runInContext(fs.readFileSync(f.startsWith('web/') ? js(f) : path.join(ROOT, f), 'utf8'), ctx, { filename: f });
  }
  return ctx;
}
function datasets() {
  const out = {};
  for (const dir of ['data/datasets', 'tests/fixtures/data/datasets']) {
    const abs = path.join(ROOT, dir);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs).sort()) if (f.endsWith('.json')) out[f.slice(0, -5)] = jload(path.join(dir, f));
  }
  return out;
}
// Vergleich nach JSON (NaN → null, undefined fällt weg); null und fehlend gelten als gleich.
function diff(a, b, where, out) {
  if (out.length > 20) return out;
  if (typeof a === 'number' && typeof b === 'number') {
    const tol = 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
    if (Math.abs(a - b) > tol) out.push(`${where}: ${a} gegen ${b}`);
    return out;
  }
  if ((a === null || a === undefined) && (b === null || b === undefined)) return out;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) { out.push(`${where}: Länge ${a.length} gegen ${b.length}`); return out; }
    a.forEach((x, i) => diff(x, b[i], `${where}[${i}]`, out));
    return out;
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    for (const k of new Set(Object.keys(a).concat(Object.keys(b)))) diff(a[k], b[k], `${where}.${k}`, out);
    return out;
  }
  if (a !== b) out.push(`${where}: ${JSON.stringify(a)} gegen ${JSON.stringify(b)}`);
  return out;
}

test('parity.json liegt vor (python3 tools/parity.py)', (t) => {
  if (!fs.existsSync(FILE)) {
    if (REQUIRE) assert.fail('tests/out/parity.json fehlt – erst python3 tools/parity.py');
    t.skip('tests/out/parity.json fehlt – erst python3 tools/parity.py');
    return;
  }
  const data = JSON.parse(fs.readFileSync(FILE, 'utf8'));
  assert.equal(data.version, 1);
  assert.ok(Object.keys(data.tasks).length >= 1);
  assert.ok(data.tasks.fixture, 'die Testaufgabe fehlt in parity.json');
});

const data = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE, 'utf8')) : { tasks: {} };
const DS = datasets();
const COMP = jload('data/comparisons.json');
for (const [tid, entry] of Object.entries(data.tasks)) {
  test(`Parität Python/JS: ${tid} (${entry.cases.length} Fälle)`, () => {
    const ctx = context(entry.gen_js);
    const gen = ctx.FS.gen[tid];
    assert.ok(gen && typeof gen.build === 'function', `FS.gen[${tid}].build fehlt`);
    const errs = [];
    let seeds = 0;
    for (const c of entry.cases) {
      if (c.label.startsWith('seed:')) seeds++;
      const inp = JSON.parse(JSON.stringify(c.inp));
      let got;
      try {
        const pal = gen.build(entry.task, inp, { datasets: DS, comparisons: COMP, lang: null, data: entry.data || {} });
        const pr = c.preset ? entry.task.presets.find((p) => p.id === c.preset) : null;
        got = { ok: true, palette: JSON.parse(JSON.stringify(ctx.FS.site.framePalette(entry.task, pr, JSON.parse(JSON.stringify(c.inp)), pal, entry.custom_names))) };
      } catch (e) {
        got = { ok: false, error: e && e.key ? e.key : String(e) };
      }
      if (got.ok !== c.ok) { errs.push(`${c.label}: Python ${c.ok ? 'ok' : c.error}, JS ${got.ok ? 'ok' : got.error}`); continue; }
      if (!c.ok) { if (got.error !== c.error) errs.push(`${c.label}: Fehler ${c.error} gegen ${got.error}`); continue; }
      for (const d of diff(c.palette, got.palette, c.label, [])) errs.push(d);
      // Namenshaken: gleicher Name aus der JS-Palette wie aus der Python-Palette
      for (const l of Object.keys(c.names || {})) {
        const n = gen.displayName(got.palette, entry.name_text[l], l);
        if (n !== c.names[l]) errs.push(`${c.label}: Name ${l} ${JSON.stringify(c.names[l])} gegen ${JSON.stringify(n)}`);
      }
    }
    if (entry.name_text) assert.ok(entry.cases.some((c) => c.names), `${tid}: kein Fall mit Namenshaken`);
    assert.equal(seeds, 60, 'alle 60 Seeds aus tests/parity_seeds.json');
    assert.deepEqual(errs.slice(0, 20), []);
  });
}
