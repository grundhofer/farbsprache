'use strict';
// Fachfälle der Aufgabe Text auf Bild in JS: Schleier-Erwartungen 42 / 54 / 66 / 46 / 85 % mit Nachprüfung in
// Gleitkomma und 8 Bit, schlimmster Pixel, SolveError ohne Lösung, viewVars, keine CSS-Variablen im Agent-Prompt und
// Byte-Gleichheit der Exporte scrim, values und agent mit Python für alle Startpaletten und Ziele.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { spawnSync } = require('node:child_process');
const { ROOT, load, jload, plain } = require('./helpers.cjs');

const ctx = load(['color.js', 'export.js', 'gen/image-text.js']);
const C = ctx.FS.color, X = ctx.FS.export, G = ctx.FS.gen['image-text'];
const TASK = jload('data/tasks/image-text.json');
const GCTX = { datasets: {}, comparisons: null, lang: null, data: {} };

function build(sc, tc, tg) {
  const inp = { seed: C.parse(sc, false).hex, colors: null, options: { tc: tc || '#FFFFFF', tg: tg || '4.5' } };
  const pal = G.build(TASK, JSON.parse(JSON.stringify(inp)), GCTX);
  pal.input = inp;
  return pal;
}
function mix(s, p, a) {
  const sv = C.hexToSrgb(s), pv = C.hexToSrgb(p);
  return [0, 1, 2].map((i) => a * sv[i] + (1 - a) * pv[i]);
}

test('Schleier: 42 / 54 / 66 / 46 / 85 %, Nachprüfung in Gleitkomma und 8 Bit', () => {
  const cases = [['#FFFFFF', '#000000', 3, 42], ['#FFFFFF', '#000000', 4.5, 54], ['#FFFFFF', '#000000', 7, 66],
    ['#000000', '#FFFFFF', 4.5, 46], ['#FFFFFF', '#11697A', 4.5, 85]];
  for (const [t, s, target, pct] of cases) {
    const r = C.scrimAlpha(t, s, target);
    assert.equal(r.percent, pct, `${t}/${s}/${target}`);
    assert.equal(C.fmtPctUp(r.percent / 100, 'en'), pct + '%');
    const c = mix(s, r.worst, pct / 100);
    assert.ok(C.contrast(t, c) >= target);
    assert.ok(C.contrast(t, C.srgbToHex(c)) >= target);
  }
  assert.equal(C.fmtRatio(C.contrast('#FFFFFF', mix('#000000', '#FFFFFF', 0.65)), 'de'), '6,97:1');
  assert.equal(C.fmtRatio(C.contrast('#FFFFFF', mix('#11697A', '#FFFFFF', 0.84)), 'de'), '4,46:1');
});

test('Generator: schlimmster Pixel, Ziel aus der Option, Fehler ohne Lösung', () => {
  assert.equal(build('#000000').roles.default['worst-pixel'], '#FFFFFF');
  assert.equal(build('#FFFFFF', '#000000').roles.default['worst-pixel'], '#000000');
  const p3 = build('#000000', '#FFFFFF', '3');
  assert.equal(p3.extra.scrim.percent, 42);
  assert.equal(p3.pairs[0].min, 3);
  assert.throws(() => build('#E63946'), (e) => e instanceof C.SolveError && e.key === 'scrim-unreachable');
  const v = G.viewVars(build('#000000'), 'default', {});
  assert.equal(v.alpha, '0.54');
  assert.equal(v['ref-white'], '#FFFFFF');
  assert.equal(v['ref-black'], '#000000');
});

const PY = `
import json, sys
sys.path.insert(0, ".")
import build as B
from tools import color as C, export as X
from tools.gen import image_text as G
from web.copy import core, image_text as copy
task = json.load(open("data/tasks/image-text.json", encoding="utf-8"))
rules = {r["id"]: r for r in json.load(open("data/rules/slides.json", encoding="utf-8"))["rules"]}
srcs = {}
for f in ("core", "slides"):
    for s in json.load(open("data/sources/" + f + ".json", encoding="utf-8"))["sources"]:
        srcs[s["id"]] = s
cases = json.loads(sys.argv[1])
out = []
for c in cases:
    inp = {"seed": C.parse(c["seed"], False)["hex"], "colors": None, "options": c["options"]}
    try:
        pal = G.build(task, json.loads(json.dumps(inp)), {"datasets": {}, "comparisons": None, "lang": None, "data": {}})
    except C.SolveError as e:
        out.append({"error": e.key})
        continue
    pal = B.frame_palette(task, None, inp, pal, {"de": "Eigene Farbe", "en": "Your color"})
    res = {}
    for lang in ("de", "en"):
        ectx = {"date": "2026-10-11", "url": "https://example.org/?sc=000000", "name": pal["name_" + lang], "task_name": task["name_" + lang],
                "core": core.COPY[lang]["export"], "text": copy.COPY[lang]["image-text"], "rules": [rules[r] for r in task["rules"]],
                "sources": srcs, "refs": C.reference_values(), "datasets": {}, "data": {}}
        res[lang] = {f: X.render(f, pal, task, ectx, lang, {}, G) for f in ("scrim", "values", "agent")}
    out.append({"palette": pal, "exports": res,
                "texts": {l: {"core": core.COPY[l]["export"], "text": copy.COPY[l]["image-text"]} for l in ("de", "en")}})
print(json.dumps({"out": out, "rules": [rules[r] for r in task["rules"]], "sources": srcs}, ensure_ascii=False))
`;

test('Exporte und Paletten JS = Python für Startpaletten, beide Ziele und Fehlerfälle', () => {
  const cases = [];
  for (const p of TASK.presets) {
    for (const tg of ['3', '4.5']) cases.push({ seed: C.parse(p.seed, false).hex, options: { tc: p.options.tc || '#FFFFFF', tg } });
  }
  for (const [sc, tc] of [['#E63946', '#FFFFFF'], ['#E63946', '#000000'], ['#FFD98A', '#1B1B1B'], ['#808080', '#FFFFFF'], ['#FFFFFF', '#FFFFFF']]) {
    cases.push({ seed: sc, options: { tc, tg: '4.5' } });
  }
  // Gleichstand von Gleitkomma und 8 Bit (Mischfarbe genau #5A5A5A); Python liegt dort 1 ulp höher als JS
  for (const sc of ['#FAFAFA', '#787878', '#7D7D7D']) cases.push({ seed: sc, options: { tc: '#000000', tg: '3' } });
  const r = spawnSync('python3', ['-c', PY, JSON.stringify(cases)], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, r.stderr);
  const py = JSON.parse(r.stdout);
  const refs = C.referenceValues(jload('data/comparisons.json'), { 'okabe-ito': jload('data/datasets/okabe-ito.json') });
  let n = 0;
  cases.forEach((c, i) => {
    const want = py.out[i];
    let pal;
    try { pal = G.build(TASK, JSON.parse(JSON.stringify({ seed: c.seed, colors: null, options: c.options })), GCTX); } catch (e) {
      assert.equal(e.key, want.error, `Fehler ${JSON.stringify(c)}`);
      return;
    }
    assert.ok(!want.error, `Python wirft ${want.error}, JS nicht: ${JSON.stringify(c)}`);
    assert.deepEqual(plain(pal.roles), want.palette.roles);
    assert.deepEqual(plain(pal.extra.summary), want.palette.extra.summary);
    const p = JSON.parse(JSON.stringify(want.palette));
    for (const lang of ['de', 'en']) {
      const ectx = { date: '2026-10-11', url: 'https://example.org/?sc=000000', name: p['name_' + lang], task_name: TASK['name_' + lang],
        core: want.texts[lang].core, text: want.texts[lang].text, rules: py.rules, sources: py.sources, refs, datasets: {}, data: {} };
      for (const f of ['scrim', 'values', 'agent']) {
        const js = plain(X.render(f, p, TASK, ectx, lang, {}, G));
        assert.deepEqual(js, want.exports[lang][f], `${f} ${lang} ${JSON.stringify(c)}`);
        assert.ok(!/var\(--|undefined|NaN|\bnull\b/.test(js[0].text), `${f} ${lang}`);
      }
    }
    n++;
  });
  assert.ok(n >= 6, 'zu wenige lösbare Fälle');
});
