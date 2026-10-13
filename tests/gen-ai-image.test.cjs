'use strict';
// KI-Bild im Browser-Code (FS.gen['ai-image'], FS.ui['ai-image']): Golden-Namen, Sperrwörter, Vorbehalte nur
// außerhalb der Kopiertexte, keine Hex-Werte, wo die Doku keine vorsieht, Recraft-Gewichte, Vorrang f vor c vor p.
// Die Gleichheit mit Python prüft tests/gen-brand.test.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');
const { jload, load, plain, js } = require('./helpers.cjs');

const ctx = load(['color.js', 'export.js', 'site.js', 'gen/ai-image.js']);
const G = ctx.FS.gen['ai-image'];
const CN = jload('data/colornames.json');
const MODELS = jload('data/models.json');
const TASK = jload('data/tasks/ai-image.json');
const GCTX = { datasets: {}, comparisons: null, lang: null, data: { models: MODELS, colornames: CN } };
const HEX = /#[0-9A-Fa-f]{6}/;

// Minimale Textbausteine für die Renderer (pr.guard gekürzt, Hinweistexte als Marken). Die echten Texte aus
// web/copy/ai_image.py prüft tests/gen-brand.test.cjs gegen Python.
function copyText() {
  return { 'pr.open': 'Color palette: ', 'pr.dominant': '{c} as the dominant color, about {w}% of the image, on {p}',
    'pr.secondary': '{c} for secondary areas, about {w}%, on {p}', 'pr.accent': 'a single accent of {c} only on {p}, under {w}%',
    'pr.background': 'the background in {c}', 'pr.guard': 'No other hues.', 'pr.text': 'Any text in {a} on {b}.',
    'pr.gpt': 'Keep this palette. Natural color balance, avoid dramatic color grading.',
    'note.model': '{c} ({w}, {p}):', 'note.quote': '“{c}”.', 'note.duty': 'DUTY', 'blk.prompt': 'Prompt', 'blk.palette': 'Palette', 'blk.json': 'JSON' };
}
function input(colors, options) {
  const o = { mdl: 'flux2', w: '60-30-10', s: 'calm', f: null, b1: '[BACKGROUND AND LARGE SHAPES]', b2: '[SECONDARY ELEMENTS]', b3: '[THE FOCAL ELEMENT]' };
  return { seed: null, colors, options: Object.assign(o, options || {}) };
}
const SET1 = [{ value: '#1B3A76', role: 'dominant' }, { value: '#F6F3ED', role: 'secondary' }, { value: '#D33B36', role: 'accent' }];

test('Golden-Namen: alle 40 aus data/colornames.json, die 33 Pflichtfälle zuerst', () => {
  assert.equal(CN.golden.length, 40);
  for (const g of CN.golden) assert.equal(G.colorName(g.hex, CN), g.name, g.hex);
  assert.equal(CN.golden[32].hex, '#E9DCC8');
});

test('Kein ausgegebener Name enthält ein Sperrwort', () => {
  for (let r = 0; r < 256; r += 15) for (let g = 0; g < 256; g += 15) for (let b = 0; b < 256; b += 15) {
    const hx = '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('').toUpperCase();
    const n = G.colorName(hx, CN);
    for (const w of CN.blocked_words) assert.ok(!new RegExp('(^|[^a-z])' + w + '([^a-z]|$)').test(n), `${hx} ${n} ${w}`);
  }
});

test('Startset 1 mit FLUX.2: Hex an jedem Namen, Textzeile ab 4,5:1, Vorbehalte nur im Hinweis', () => {
  const pal = G.build(TASK, input(SET1), GCTX);
  assert.deepEqual(plain(pal.extra.text_pair), ['dominant', 'secondary']);
  const blocks = G.exports.prompt(pal, TASK, { text: copyText(), data: GCTX.data }, 'de');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].lang, 'en');
  assert.ok(blocks[0].text.startsWith('Color palette: deep blue (#1B3A76) as the dominant color, about 60% of the image'));
  assert.ok(blocks[0].text.endsWith('Any text in deep blue (#1B3A76) on off-white with a warm tint (#F6F3ED).'));
  assert.ok(!/DUTY|precision matching/.test(blocks[0].text));
  assert.ok(blocks[0].note.includes('DUTY') && blocks[0].note.includes('precision matching') && blocks[0].note.includes(MODELS.models[0].checked));
});

test('Keine Hex-Werte in Ideogram (Prompt), Midjourney und gpt-image; Recraft-Gewichte summieren höchstens 1', () => {
  for (const f of [null, ['#1B3A76', '#F6F3ED'], ['#1B3A76', '#F6F3ED', '#D33B36', '#FFFFFF']]) {
    for (const w of ['60-30-10', '70-20-10', '50-40-10']) {
      for (const m of MODELS.models) {
        const pal = G.build(TASK, input(SET1, { mdl: m.id, w, f }), GCTX);
        const b = G.exports.prompt(pal, TASK, { text: copyText(), data: GCTX.data }, 'en');
        if (m.method === 'hex-in-prompt') assert.ok(HEX.test(b[0].text)); else assert.ok(!HEX.test(b[0].text), m.id + ' ' + b[0].text);
        if (m.method === 'api-weights') {
          const j = JSON.parse(b[1].text);
          const sum = j.controls.colors.reduce((s, c) => s + c.weight, 0);
          assert.ok(sum <= 1 + 1e-12, `${m.id} ${w}: Summe ${sum}`);
          assert.equal('background_color' in j.controls, !!(f && f.length === 4));
        }
        if (m.id === 'gpt-image') assert.ok(b[0].text.endsWith('Keep this palette. Natural color balance, avoid dramatic color grading.'));
        assert.ok(!b[0].text.includes('--sref'));
      }
    }
  }
});

test('Vorrang f vor c vor p, zu wenige eigene Farben ergeben einen Lösungsfehler', () => {
  let pal = G.build(TASK, Object.assign(input(SET1, { f: ['#123456', '#FEDCBA'] }), { seed: '#11697A' }), GCTX);
  assert.equal(pal.roles.default.dominant, '#123456');
  assert.equal(pal.extra.source, 'f');
  pal = G.build(TASK, Object.assign(input(SET1), { seed: '#11697A' }), GCTX);
  assert.equal(pal.extra.source, 'seed');
  assert.deepEqual(plain([pal.roles.default.dominant, pal.roles.default.secondary, pal.roles.default.accent]), plain(G.suggest('#11697A', 'calm')));
  assert.throws(() => G.build(TASK, input(SET1, { f: ['#123456'] }), GCTX), (e) => e.key === 'few-colors');
});

test('UI-Haken lädt ohne DOM-Zugriff und registriert init und render', () => {
  const c = { FS: { gen: {} } };
  vm.createContext(c);
  vm.runInContext(fs.readFileSync(js('ui/ai-image.js'), 'utf8'), c);
  assert.equal(typeof c.FS.ui['ai-image'].init, 'function');
  assert.equal(typeof c.FS.ui['ai-image'].render, 'function');
});
