'use strict';
// Fachfälle der Aufgaben Website oder App und Statusfarben im Browser-Generator.
// Lädt web/color.js, web/export.js, web/gen/website.js und web/gen/status.js unverändert in node:vm.
// Die Parität zu Python prüft tests/parity.test.cjs; hier stehen feste Erwartungswerte.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { ROOT, jload, load, plain } = require('./helpers.cjs');

const ctx = load(['color.js', 'export.js', 'gen/website.js', 'gen/status.js']);
const C = ctx.FS.color, W = ctx.FS.gen.website, S = ctx.FS.gen.status;
const TASK = { website: jload('data/tasks/website.json'), status: jload('data/tasks/status.json') };
const GCTX = { datasets: { 'okabe-ito': jload('data/datasets/okabe-ito.json') }, comparisons: jload('data/comparisons.json'), lang: null, data: {} };
const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';

function inp(task, seed, opts) {
  const o = {};
  for (const c of task.controls) o[c.id] = c.default;
  Object.assign(o, opts || {});
  return { seed: C.parse(seed).hex, colors: null, options: o };
}
function build(tid, seed, opts) { return plain((tid === 'website' ? W : S).build(TASK[tid], inp(TASK[tid], seed, opts), GCTX)); }
const cr = (a, b) => C.fmtRatio(C.contrast(a, b), 'de').slice(0, -2);
const dist = (d) => C.fmtDist(d, 'de');

test('Petrol hell und dunkel: Rollenfarben und Kontraste', () => {
  const p = build('website', 'oklch(0.48 0.08 215)');
  const l = p.roles.light, d = p.roles.dark;
  assert.deepEqual([l.bg, l.text, l['text-muted'], l.border, l['border-strong'], l.accent, l['accent-text'], l['on-accent']],
    ['#F8FBFB', '#182123', '#60696B', '#D2D9DB', '#838C8F', '#11697A', '#11697A', '#FFFFFF']);
  assert.deepEqual([cr(l.text, l.bg), cr(l['text-muted'], l['surface-2']), cr(l['border-strong'], l.bg), cr(l.border, l.bg),
    cr(l['on-accent'], l.accent), cr(l['accent-text'], l.text)], ['15,76', '4,95', '3,30', '1,37', '6,31', '2,59']);
  assert.deepEqual([d.bg, d.text, d.accent, d['on-accent'], d['accent-text']], ['#101516', '#E8ECED', '#276876', '#E8ECED', '#4E8D9C']);
  assert.deepEqual([cr(d['on-accent'], d.accent), cr(d['accent-text'], d.bg), cr(d['accent-text'], d.surface), cr(d['accent-text'], d.text),
    cr(d['accent-text'], d['surface-2']), cr(d.accent, d.bg)], ['5,30', '4,92', '4,50', '3,14', '4,03', '2,91']);
});

test('Kräftiges Rot #E63946: weiße Schrift 4,16:1, Akzent wird #DF3141 mit 4,51:1', () => {
  const p = build('website', '#E63946');
  const ch = p.changes.find((c) => c.role === 'accent' && c.mode === 'light');
  assert.equal(ch.key, 'accent-darker');
  assert.equal(ch.to, '#DF3141');
  assert.equal(C.fmtRatio(ch.values.before, 'de'), '4,16:1');
  assert.equal(C.fmtRatio(ch.values.after, 'de'), '4,51:1');
});

test('Statusfarben Petrol: Farben und kleinste Abstände, in beiden Aufgaben', () => {
  for (const tid of ['website', 'status']) {
    const p = build(tid, 'oklch(0.48 0.08 215)');
    const l = p.roles.light;
    assert.deepEqual([l.danger, l.warning, l.success, l.info], ['#B6433C', '#723F00', '#007329', '#004D9A']);
    const d = {}; for (const x of p.distinct) d[x.mode] = x;
    assert.deepEqual([dist(d.light.value), d.light.a, d.light.b, d.light.kind, dist(d.light.compare.value)], ['6,0', 'warning', 'success', 'deutan', '3,6']);
    assert.deepEqual([dist(d.dark.value), d.dark.a, d.dark.b, d.dark.kind, dist(d.dark.compare.value)], ['11,5', 'danger', 'warning', 'deutan', '3,3']);
  }
});

test('Änderungshinweise: Farbe bleibt, dunkle Schrift, heller und dunkler, Grenzfälle jenseits der Flächen', () => {
  assert.deepEqual(build('website', 'oklch(0.48 0.08 215)').extra.summary, ['sum.light.keep-light', 'sum.dark.keep-light']);
  const senf = build('website', 'oklch(0.80 0.15 85)');
  assert.deepEqual(senf.extra.summary, ['sum.light.keep-dark', 'sum.dark.keep-dark']);
  const red = build('website', 'oklch(0.6 0.3 30)');
  assert.ok(red.changes.some((c) => c.mode === 'dark' && c.key === 'accent-lighter'));
  assert.ok(red.changes.some((c) => c.mode === 'light' && c.key === 'accent-darker'));
  // solveL ab L_s wäre hier mixed-sides; die Linkfarbe startet dann bei TEXT_L0 und erfüllt jedes Paar
  for (const seed of ['#FFFFFF', '#FCFCFC', '#000000', '#111827', '#0F172A', '#18181B']) {
    const p = build('website', seed);
    assert.ok(p.pairs.every((q) => q.pass), seed);
    for (const mode of ['light', 'dark']) {
      const r = p.roles[mode];
      assert.ok(Math.min(C.contrast(r['accent-text'], r.bg), C.contrast(r['accent-text'], r.surface)) >= 4.5, seed + ' ' + mode);
    }
  }
  assert.equal(build('website', '#000000').roles.dark['accent-text'], build('website', '#2A2A2A').roles.dark['accent-text']);
  assert.deepEqual(build('website', '#FFFFFF').changes.map((c) => c.key + '@' + c.mode), ['accent-text-darker@light']);
});

test('Konflikt Akzent und Fehler nur bei rotem, buntem Akzent', () => {
  assert.ok(build('status', '#E63946').findings.some((f) => f.id === 'accent-error-conflict' && f.mode === null));
  assert.ok(!build('status', 'oklch(0.55 0 0)').findings.some((f) => f.id === 'accent-error-conflict'));
  assert.ok(!build('status', 'oklch(0.48 0.08 215)').findings.some((f) => f.id === 'accent-error-conflict'));
});

test('Diagrammfarben: Linkfarbe zuerst, Okabe-Ito mit 3:1, hell nur vier', () => {
  const p = build('website', 'oklch(0.48 0.08 215)');
  for (const [mode, n] of [['light', 4], ['dark', 5]]) {
    const r = p.roles[mode];
    const charts = [1, 2, 3, 4, 5].map((i) => r['chart-' + i]).filter(Boolean);
    assert.equal(charts.length, n);
    assert.equal(charts[0], r['accent-text']);
    for (const c of charts) assert.ok(C.contrast(c, r.bg) >= 3);
  }
});

test('Statusoptimierung bleibt schnell (Node, nur Richtwert)', () => {
  const seeds = ['#11697A', '#2B4EA7', '#EAB532', '#777777', '#00AA55', '#8844CC', '#CC4488', '#334455'];
  const t0 = process.hrtime.bigint();
  for (const s of seeds) build('status', s);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6 / seeds.length;
  assert.ok(ms < 50, ms + ' ms je Palette');
});

// Mit gebauter Seite: Exporte mit Option „Diagrammfarben einschließen“ und HTML-Snippet aus den echten Texten
const PAGE = path.join(ROOT, 'docs', 'de', 'website', 'index.html');
function taskData(file) {
  const html = fs.readFileSync(file, 'utf8');
  return JSON.parse(html.match(/<script type="application\/json" id="task-data">([\s\S]*?)<\/script>/)[1].replace(/<\\\//g, '</'));
}
function ectx(data, pal) {
  return { date: data.date, url: data.url, name: pal['name_' + data.lang], task_name: data.task['name_' + data.lang], core: data.core,
    text: data.text, rules: data.rules, sources: data.sources, refs: data.refs, datasets: data.datasets, data: {} };
}
test('CSS mit Diagrammfarben: Hinweis genau in Blöcken mit weniger als fünf Farben', (t) => {
  if (!fs.existsSync(PAGE)) { if (REQUIRE) assert.fail('docs/ fehlt'); t.skip('docs/ fehlt'); return; }
  const data = taskData(PAGE);
  for (const pid of Object.keys(data.palettes)) {
    const pal = data.palettes[pid], e = ectx(data, pal);
    const on = W.exports.css(pal, data.task, e, 'de', { charts: true });
    const off = W.exports.css(pal, data.task, e, 'de', { charts: false });
    assert.equal(off, ctx.FS.export.css(pal, data.task, e, 'de', { charts: false }));
    const blocks = on.split('@media');
    pal.modes.forEach((mode, i) => {
      const n = Object.keys(pal.roles[mode]).filter((k) => k.startsWith('chart-')).length;
      assert.equal(/nur \d Farben 3:1/.test(blocks[i]), n < 5, `${pid} ${mode}`);
    });
    const stripped = on.split('\n').filter((l) => !/Auf diesem Hintergrund erreichen nur/.test(l)).join('\n');
    assert.equal(stripped, ctx.FS.export.css(pal, data.task, e, 'de', { charts: true }));
  }
});
// Jeder Export mit den Diagrammfarben nennt die Lücke je Modus (Zählform bei einer Farbe), Tailwind legt Utilities nur
// für Rollen an, die jeder Modus definiert; Python und JS liefern dieselben Bytes.
test('Diagrammfarben: Hinweis in CSS, Tailwind, Prompt, Hex-Liste und Design-Tokens, Utilities nur für Rollen jedes Modus', (t) => {
  if (!fs.existsSync(PAGE)) { if (REQUIRE) assert.fail('docs/ fehlt'); t.skip('docs/ fehlt'); return; }
  const { execFileSync } = require('node:child_process');
  const FMTS = ['css', 'tailwind', 'agent', 'hex', 'dtcg'], jobs = {}, got = {};
  for (const lang of ['de', 'en']) {
    const data = taskData(path.join(ROOT, 'docs', lang, 'website', 'index.html'));
    const pals = Object.keys(data.palettes).map((pid) => [pid, data.palettes[pid]]);
    // erfundener Grenzfall: hell genau eine Diagrammfarbe (Zählform css.charts_few_1)
    const one = JSON.parse(JSON.stringify(data.palettes[data.first]));
    for (const k of Object.keys(one.roles.light)) if (/^chart-[2-9]$/.test(k)) delete one.roles.light[k];
    pals.push(['one', one]);
    for (const [pid, pal] of pals) {
      const e = ectx(data, pal);
      for (const f of FMTS) {
        const key = [lang, pid, f].join(' ');
        jobs[key] = { fmt: f, pal, task: data.task, ctx: e, lang, opts: { charts: true } };
        got[key] = ctx.FS.export.render(f, pal, data.task, e, lang, { charts: true }, W).map((b) => b.text);
        const text = got[key].join('\n'), tw = f === 'tailwind' ? text.split('@theme inline {') : null;
        pal.modes.forEach((mode, i) => {
          const n = Object.keys(pal.roles[mode]).filter((k) => k.startsWith('chart-')).length;
          const note = n >= 5 ? null : data.text[n === 1 ? 'css.charts_few_1' : 'css.charts_few'].split('{n}').join(C.fmtCount(n, lang));
          const part = f === 'dtcg' ? got[key][i] : f === 'hex' ? text.split('\n\n')[i] : text.split('@media')[i];
          assert.equal(note === null || part.includes(note), true, `${key} ${mode}: Hinweis fehlt`);
          if (note) assert.equal(text.split(note).length - 1, 1, `${key} ${mode}: Hinweis genau einmal`);
          if (tw) {
            for (const m of tw[1].matchAll(/--color-([a-z0-9-]+): var\(--([a-z0-9-]+)\);/g)) {
              assert.ok(new RegExp('--' + m[2] + ': #').test(tw[0].split(':root {')[i + 1]), `${key}: --color-${m[1]} ohne --${m[2]} im Modus ${mode}`);
            }
          }
        });
        if (f === 'dtcg') for (const b of got[key]) JSON.parse(b);
      }
    }
    assert.ok(got[lang + ' one css'].join('').includes(data.text['css.charts_few_1'].split('{n}').join('1')), 'Zählform bei einer Farbe');
  }
  const py = 'import json, sys\nsys.path.insert(0, sys.argv[1])\nfrom tools import export as X\nfrom tools.gen import website as W\n' +
    'jobs = json.load(sys.stdin)\nprint(json.dumps({k: [b["text"] for b in X.render(j["fmt"], j["pal"], j["task"], j["ctx"], j["lang"], j["opts"], W)] for k, j in jobs.items()}))';
  const want = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c', py, ROOT], { input: JSON.stringify(jobs), maxBuffer: 1 << 28, cwd: ROOT }).toString());
  for (const k of Object.keys(jobs)) assert.ok(JSON.stringify(got[k]) === JSON.stringify(want[k]), `${k}: Python und JS weichen ab`);
});
test('HTML-Snippet: vier Meldungen, role="alert" nur beim Fehler', (t) => {
  const file = path.join(ROOT, 'docs', 'en', 'status', 'index.html');
  if (!fs.existsSync(file)) { if (REQUIRE) assert.fail('docs/ fehlt'); t.skip('docs/ fehlt'); return; }
  const data = taskData(file), pal = data.palettes[data.first];
  const h = S.exports.html(pal, data.task, ectx(data, pal), 'en', {});
  assert.deepEqual([...h.matchAll(/<div class="msg msg-([a-z]+)" role="([a-z]+)">/g)].map((m) => m[1] + ':' + m[2]),
    ['danger:alert', 'warning:status', 'success:status', 'info:status']);
  assert.deepEqual([...h.matchAll(/<strong>([^<]+)<\/strong>/g)].map((m) => m[1]), ['Error:', 'Warning:', 'Done:', 'Note:']);
});
