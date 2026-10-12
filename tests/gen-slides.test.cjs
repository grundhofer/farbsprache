'use strict';
// Fachfälle der Aufgabe Präsentation in JS (Paket P3): Beamer-Erwartungen, Ansicht „Beamer“, Office-Reihenfolge,
// lösbare Extremfarben und Byte-Gleichheit der Exporte hex, rationale und css mit Python für alle Startpaletten
// und Optionen (nicht nur Startpalette 1 wie tests/export.test.cjs). Python läuft dafür als Kindprozess.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { spawnSync } = require('node:child_process');
const { ROOT, load, jload, plain } = require('./helpers.cjs');

const ctx = load(['color.js', 'export.js', 'gen/slides.js']);
const C = ctx.FS.color, X = ctx.FS.export, G = ctx.FS.gen.slides;
const TASK = jload('data/tasks/slides.json');
const GCTX = { datasets: { 'okabe-ito': jload('data/datasets/okabe-ito.json') }, comparisons: jload('data/comparisons.json'), lang: null, data: {} };

function options(extra) {
  const o = {};
  for (const c of TASK.controls) o[c.id] = c.default;
  return Object.assign(o, extra || {});
}
function build(seed, extra) {
  const hex = C.parse(seed, false).hex;
  const inp = { seed: hex, colors: null, options: options(extra) };
  const pal = G.build(TASK, inp, GCTX);
  pal.input = JSON.parse(JSON.stringify(inp));
  return pal;
}

test('Beamer-Modell: 5,98 / 3,14 / 3,99 bei normalem Raumlicht, 96,19 abgedunkelt, 2,66 hell', () => {
  assert.equal(C.fmtRatio(C.projectedContrast('#000000', '#FFFFFF', 'normal'), 'de'), '5,98:1');
  assert.equal(C.fmtRatio(C.projectedContrast('#767676', '#FFFFFF', 'normal'), 'de'), '3,14:1');
  assert.equal(C.fmtRatio(C.projectedContrast('#595959', '#FFFFFF', 'normal'), 'de'), '3,99:1');
  assert.equal(C.fmtRatio(C.projectedContrast('#000000', '#FFFFFF', 'dim'), 'en'), '96.19:1');
  assert.equal(C.fmtRatio(C.projectedContrast('#000000', '#FFFFFF', 'bright'), 'en'), '2.66:1');
});

test('Startpaletten: Schrift am Bildschirm mindestens 7:1 auf beiden Folienflächen', () => {
  for (const p of TASK.presets) {
    const r = build(p.seed, p.options).roles.default;
    for (const fg of ['text', 'text-2', 'accent-text']) {
      for (const bg of ['slide', 'slide-2']) assert.ok(C.contrast(r[fg], r[bg]) >= 7, `${p.id} ${fg}/${bg}`);
    }
    for (const fg of ['accent', 'line', 'chart-1', 'chart-2', 'chart-3', 'chart-4']) assert.ok(C.contrast(r[fg], r.slide) >= 3, `${p.id} ${fg}`);
  }
});

test('Ansicht „Beamer“: viewVars rechnet jede Rolle mit projectorHex beim gewählten Raumlicht', () => {
  for (const room of ['dim', 'normal', 'bright']) {
    const pal = build('oklch(0.48 0.08 215)', { room });
    assert.deepEqual(plain(G.viewVars(pal, 'default', { view: 'screen' })), {});
    const v = G.viewVars(pal, 'default', { view: 'projector' });
    for (const [rid, hx] of Object.entries(pal.roles.default)) assert.equal(v[rid], C.projectorHex(hx, room));
    assert.equal(v['cap-text'], pal.roles.default.text);
    assert.equal(v['cap-bg'], pal.roles.default.slide);
  }
});

test('Office-Reihenfolge dk1 … folHlink, Akzent 2 bis 4 ohne Dopplung mit dem Akzent', () => {
  const pal = build('oklch(0.48 0.08 215)');
  assert.deepEqual(plain(pal.extra.office).map((x) => x.slot), ['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink']);
  assert.deepEqual(plain(pal.extra.office).map((x) => x.role), ['text', 'slide', 'text-2', 'slide-2', 'accent', 'chart-2', 'chart-3', 'chart-4', 'text-2', 'line', 'accent-text', 'text-2']);
});

test('Sehr helle und sehr dunkle eigene Farben bleiben lösbar, hell und dunkel', () => {
  for (const seed of ['#FFFFFF', '#000000', '#FFFF00', '#0B0B0B', '#FAFAFA', '#808080']) {
    for (const bg of ['light', 'dark']) {
      const pal = build(seed, { bg });
      assert.ok(pal.pairs.every((p) => p.pass), `${seed} ${bg}`);
    }
  }
});

// Python rechnet dieselben Fälle und liefert Palette und Exporte; JS muss Byte für Byte gleich sein.
const PY = `
import json, sys
sys.path.insert(0, ".")
import build as B
from tools import color as C, export as X
from tools.gen import slides as G
from web.copy import core, slides as copy
task = json.load(open("data/tasks/slides.json", encoding="utf-8"))
ds = {"okabe-ito": json.load(open("data/datasets/okabe-ito.json", encoding="utf-8"))}
gctx = {"datasets": ds, "comparisons": json.load(open("data/comparisons.json", encoding="utf-8")), "lang": None, "data": {}}
rules = {r["id"]: r for r in json.load(open("data/rules/slides.json", encoding="utf-8"))["rules"]}
cases = json.loads(sys.argv[1])
out = []
for c in cases:
    inp = {"seed": C.parse(c["seed"], False)["hex"], "colors": None, "options": c["options"]}
    pal = G.build(task, json.loads(json.dumps(inp)), gctx)
    pal = B.frame_palette(task, None, inp, pal, {"de": "Eigene Farbe", "en": "Your color"})
    res = {}
    for lang in ("de", "en"):
        ectx = {"date": "2026-10-11", "url": "https://example.org/?q=1", "name": pal["name_" + lang], "task_name": task["name_" + lang],
                "core": core.COPY[lang]["export"], "text": copy.COPY[lang]["slides"], "rules": [], "sources": {},
                "refs": C.reference_values(), "datasets": ds, "data": {}}
        res[lang] = {f: X.render(f, pal, task, ectx, lang, {}, G) for f in ("hex", "css", "rationale", "dtcg")}
    out.append({"palette": pal, "exports": res})
print(json.dumps(out, ensure_ascii=False))
`;

test('Exporte und Paletten JS = Python für alle Startpaletten und Optionen', () => {
  const cases = [];
  for (const p of TASK.presets) {
    for (const room of ['dim', 'normal', 'bright']) {
      for (const pr of [false, true]) cases.push({ seed: C.parse(p.seed, false).hex, options: options(Object.assign({}, p.options, { room, pr })) });
    }
  }
  for (const seed of ['#E63946', '#F2A900', '#FFFFFF', '#000000', '#1B2A4A']) {
    for (const bg of ['light', 'dark']) cases.push({ seed, options: options({ bg }) });
  }
  const r = spawnSync('python3', ['-c', PY, JSON.stringify(cases)], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, r.stderr);
  const py = JSON.parse(r.stdout);
  assert.equal(py.length, cases.length);
  cases.forEach((c, i) => {
    const pal = G.build(TASK, JSON.parse(JSON.stringify({ seed: c.seed, colors: null, options: c.options })), GCTX);
    const want = py[i].palette;
    assert.deepEqual(plain(pal.roles), want.roles, `Rollen ${JSON.stringify(c)}`);
    assert.deepEqual(plain(pal.extra.office), want.extra.office);
    assert.deepEqual(plain(pal.findings).map((f) => f.id), want.findings.map((f) => f.id));
    assert.deepEqual(plain(pal.changes).map((f) => [f.key, f.to]), want.changes.map((f) => [f.key, f.to]));
  });
  // Exporte: Kontexte mit den Texten, die Python mitliefert
  const T = spawnSync('python3', ['-c', 'import json,sys;sys.path.insert(0,".");from web.copy import core, slides;print(json.dumps({l:{"core":core.COPY[l]["export"],"text":slides.COPY[l]["slides"]} for l in ("de","en")},ensure_ascii=False))'], { cwd: ROOT, encoding: 'utf8' });
  assert.equal(T.status, 0, T.stderr);
  const TX = JSON.parse(T.stdout);
  const refs = C.referenceValues(jload('data/comparisons.json'), GCTX.datasets);
  cases.forEach((c, i) => {
    const pal = JSON.parse(JSON.stringify(py[i].palette));
    for (const lang of ['de', 'en']) {
      const ectx = { date: '2026-10-11', url: 'https://example.org/?q=1', name: pal['name_' + lang], task_name: TASK['name_' + lang],
        core: TX[lang].core, text: TX[lang].text, rules: [], sources: {}, refs, datasets: GCTX.datasets, data: {} };
      for (const f of ['hex', 'css', 'rationale', 'dtcg']) {
        const js = plain(X.render(f, pal, TASK, ectx, lang, {}, G));
        assert.deepEqual(js, py[i].exports[lang][f], `${f} ${lang} ${JSON.stringify(c)}`);
      }
    }
  });
});
