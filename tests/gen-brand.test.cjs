'use strict';
// Paket P4 (Logo und Marke, KI-Bild): JS-Generatoren und JS-Exporte gegen Python, über alle Fälle aus
// tests/test_gen_brand.py (Startpaletten, eigene Farben, zweite Markenfarbe, alle fünf Bildmodelle, eigene Farben f,
// Bildteile), beide Sprachen, alle Formate der Aufgaben, Hinweise neben den Blöcken eingeschlossen. Hex und Texte exakt,
// Gleitkomma mit Toleranz 1e-9. Dazu Farbnamen auf einem Raster von 4.096 Farben. Startet python3 selbst (PYTHON
// überschreibt den Befehl); ohne Python schlägt der Test fehl, statt still zu überspringen.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const { test } = require('node:test');
const { ROOT, jload, load, plain } = require('./helpers.cjs');

const DUMP = JSON.parse(execFileSync(process.env.PYTHON || 'python3', [path.join('tests', 'test_gen_brand.py'), '--dump'],
  { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }));
const ctx = load(['color.js', 'export.js', 'site.js', 'gen/brand.js', 'gen/ai-image.js']);
const { FS } = ctx;

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
    for (const k of new Set(Object.keys(a).concat(Object.keys(b)))) diff(a[k], b[k], `${where}.${k}`, out);
    return out;
  }
  if (a !== b) out.push(`${where}: ${JSON.stringify(a)} gegen ${JSON.stringify(b)}`);
  return out;
}

test('Abzug aus Python liegt vor und deckt beide Aufgaben ab', () => {
  assert.ok(DUMP.cases.length >= 25);
  assert.deepEqual([...new Set(DUMP.cases.map((c) => c.task))].sort(), ['ai-image', 'brand']);
  assert.ok(FS.gen.brand && FS.gen['ai-image'], 'FS.gen.brand und FS.gen["ai-image"] sind registriert');
});

DUMP.cases.forEach((c, n) => {
  const task = DUMP.tasks[c.task];
  const label = `${c.task} ${c.preset || 'eigen'} ${JSON.stringify(c.inp.seed)} ${JSON.stringify(c.inp.options.mdl || c.inp.options.c2 || c.inp.options.f || '')}`;
  test(`Palette und Exporte JS = Python (${n}): ${label}`, () => {
    const gen = FS.gen[c.task];
    const pr = c.frame_preset ? task.presets.find((p) => p.id === c.frame_preset) : null;
    const pal = FS.site.framePalette(task, pr, plain(c.inp), gen.build(task, plain(c.inp), plain(c.gen_ctx)), c.custom_names);
    assert.deepEqual(diff(c.palette, plain(pal), 'palette', []), []);
    for (const lang of ['de', 'en']) {
      const e = c.exports[lang];
      for (const fmt of Object.keys(e.blocks)) {
        const js = plain(FS.export.render(fmt, pal, task, e.ctx, lang, {}, gen));
        assert.deepEqual(js, e.blocks[fmt], `${lang} ${fmt}`);
        for (const b of js) assert.ok(!/undefined|NaN|\bnull\b|\bNone\b/.test(b.text), `${lang} ${fmt}: undefined, NaN, null oder None im Kopiertext`);
      }
    }
  });
});

test('Farbnamen JS = Python auf einem Raster von 4.096 Farben', () => {
  const cn = jload('data/colornames.json');
  const bad = [];
  for (const [hx, name] of Object.entries(DUMP.names)) {
    const got = FS.gen['ai-image'].colorName(hx, cn);
    if (got !== name) bad.push(`${hx}: ${got} gegen ${name}`);
  }
  assert.equal(Object.keys(DUMP.names).length, 4096);
  assert.deepEqual(bad.slice(0, 10), []);
});

test('Marke: Schriftfarbe ist der höhere Kontrast, die Markenfarbe bleibt, Varianten erreichen 4,5:1', () => {
  const task = DUMP.tasks.brand, C = FS.color;
  for (const seed of ['#2B4EA7', '#F2A900', '#E63946', '#000000', '#FFFFFF', '#16191D', '#7F7F7F']) {
    const pal = FS.gen.brand.build(task, { seed, colors: null, options: { c2: null } }, { datasets: {}, comparisons: null, lang: null, data: {} });
    const r = pal.roles.default;
    assert.equal(r.brand, seed);
    assert.equal(r['on-brand'], C.contrast(seed, '#FFFFFF') >= C.contrast(seed, '#000000') ? '#FFFFFF' : '#000000');
    assert.ok(C.contrast(r['brand-text-light'], '#FFFFFF') >= 4.5, seed + ' auf Weiß');
    assert.ok(C.contrast(r['brand-text-dark'], '#16191D') >= 4.5, seed + ' auf Dunkel');
    for (const ch of pal.changes) assert.equal(ch.from, seed);
  }
});
