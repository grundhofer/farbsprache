'use strict';
// Exporte und dynamische Blöcke (Spezifikation 5.0, 7.9): Für Startpalette 1 jeder Aufgabe gleicht die
// JS-Ausgabe Byte für Byte dem statischen HTML aus dem Python-Build. Geladen werden genau die
// ausgelieferten Dateien aus docs/assets/ (color.js mit FS_CONST, export.js, gen/*.js, site.js).
// Vorher: python3 build.py --fixtures (Datum über --date fest).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT } = require('./helpers.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const SITES = [['docs', path.join(ROOT, 'docs')], ['fixtures', path.join(ROOT, 'tests', 'out', 'fixtures', 'docs')]];

function taskPages(dir) {
  const out = [];
  for (const lang of ['de', 'en']) {
    const base = path.join(dir, lang);
    if (!fs.existsSync(base)) continue;
    for (const seg of fs.readdirSync(base)) {
      const f = path.join(base, seg, 'index.html');
      if (fs.existsSync(f) && fs.readFileSync(f, 'utf8').includes('id="task-data"')) out.push(f);
    }
  }
  return out;
}
function taskData(html) {
  const m = html.match(/<script type="application\/json" id="task-data">([\s\S]*?)<\/script>/);
  return JSON.parse(m[1].replace(/<\\\//g, '</'));
}
function scripts(html, file) {
  const out = [];
  const re = /<script src="([^"?]+)\?v=[^"]*" defer><\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.push(path.resolve(path.dirname(file), m[1]));
  return out;
}
function load(files) {
  const ctx = {};
  vm.createContext(ctx);
  for (const f of files) {
    if (/\/ui\//.test(f)) continue; // DOM-Haken, nicht rein
    vm.runInContext(fs.readFileSync(f, 'utf8'), ctx, { filename: f });
  }
  return ctx;
}
function grab(html, id) {
  const m = html.match(new RegExp('<!--fs:' + id.replace(/[-]/g, '\\-') + '-->([\\s\\S]*?)<!--/fs:' + id.replace(/[-]/g, '\\-') + '-->'));
  return m ? m[1] : null;
}
function unesc(s) { return s.replace(/&(amp|lt|gt|quot|#x27);/g, (m, k) => ({ amp: '&', lt: '<', gt: '>', quot: '"', '#x27': "'" })[k]); }

for (const [name, dir] of SITES) {
  test(`Gebaute Seite ${name} liegt vor`, (t) => {
    if (!fs.existsSync(path.join(dir, 'de', 'index.html'))) {
      if (REQUIRE) assert.fail(`${name}/ fehlt – erst python3 build.py --fixtures`);
      t.skip(`${name}/ fehlt – erst python3 build.py --fixtures`);
    }
  });
  for (const file of taskPages(dir)) {
    const rel = path.relative(ROOT, file);
    test(`Startpalette 1 JS = Python: ${rel}`, () => {
      const html = fs.readFileSync(file, 'utf8');
      const data = taskData(html);
      const ctx = load(scripts(html, file));
      const S = ctx.FS.site, gen = ctx.FS.gen[data.task.id] || ctx.FS.gen[data.gen];
      assert.ok(S && gen, 'FS.site oder FS.gen fehlt');
      const st = { c: null, p: null, o: {}, t: {} };
      const pal = data.palettes[data.first];
      const exp = {};
      for (const o of data.task.exports.options || []) exp[o.id] = !!o.default;
      const out = S.render.all(data, pal, st, gen, { exp });
      const parts = [['pal-strip', out.strip], ['bar-strip', out.strip], ['pal-sum', out.sum], ['pal-notes', out.notes], ['pal-roles', out.roles],
        ['chk-sum', out.chkSum], ['chk', out.chk], ['rules-sum', out.rulesSum], ['rules', out.rules]];
      for (const f of Object.keys(out.exports)) { parts.push(['exp-' + f, out.exports[f].blocks]); parts.push(['exp-' + f + '-note', out.exports[f].note]); }
      for (const [id, js] of parts) {
        const py = grab(html, id);
        assert.notEqual(py, null, `Block ${id} fehlt im HTML`);
        assert.equal(js, py, `Block ${id} weicht ab`);
      }
      // Prompt und Design-Tokens nennen in den Paaren dieselben Namen wie ihre Tokens (5.4, 6.3; T-05, M-07)
      const exps = data.task.exports.visible.concat(data.task.exports.more || []);
      for (const b of exps.includes('agent') ? ctx.FS.export.render('agent', pal, data.task, S.render.exportCtx(data, pal, st, false), data.lang, exp, gen) : []) {
        if (!b.text.includes('```css')) continue;
        const tokens = new Set([...b.text.split('```css')[1].split('```')[0].matchAll(/--([a-z0-9-]+):/g)].map((m) => m[1]));
        const part = b.text.split(data.core.h_pairs)[1].split(data.core.h_rules)[0];
        for (const m of part.matchAll(/([a-z0-9-]+)\/([a-z0-9-]+) \d/g)) {
          assert.ok(tokens.has(m[1]) && tokens.has(m[2]), `${rel}: ${m[0]} nennt keinen Token des Prompts`);
        }
      }
      for (const b of exps.includes('dtcg') ? ctx.FS.export.render('dtcg', pal, data.task, S.render.exportCtx(data, pal, st, false), data.lang, exp, gen) : []) {
        const doc = JSON.parse(b.text), ext = doc.$extensions[ctx.FS.export.NS];
        for (const q of ext.pairs.concat(ext.decorative)) assert.ok(q.fg in doc.color && q.bg in doc.color, `${rel}: DTCG-Paar ${q.fg}/${q.bg}`);
      }
      // Die Kopiertexte selbst: <pre> im HTML gegen den JS-Renderer
      for (const f of data.task.exports.visible.concat(data.task.exports.more || [])) {
        const ectx = S.render.exportCtx(data, pal, st, false);
        const blocks = ctx.FS.export.render(f, pal, data.task, ectx, data.lang, exp, gen);
        blocks.forEach((b, i) => {
          const m = html.match(new RegExp('<pre class="code" id="exp-' + f + '-' + i + '"[^>]*><code>([\\s\\S]*?)</code></pre>'));
          assert.ok(m, `pre exp-${f}-${i} fehlt`);
          assert.equal(b.text, unesc(m[1]), `Export ${f} Block ${i} weicht ab`);
          assert.ok(!/undefined|NaN|\bnull\b|\bNone\b/.test(b.text), `Export ${f} enthält undefined, NaN, null oder None`);
        });
      }
    });
  }
}

test('Exporte der Testaufgabe enthalten jede Rolle und die Kopf- und Fußzeile', (t) => {
  const file = path.join(SITES[1][1], 'de', 'testaufgabe', 'index.html');
  if (!fs.existsSync(file)) { if (REQUIRE) assert.fail('Testaufgabe nicht gebaut'); t.skip('Testaufgabe nicht gebaut'); return; }
  const html = fs.readFileSync(file, 'utf8');
  const data = taskData(html);
  const ctx = load(scripts(html, file));
  const S = ctx.FS.site, X = ctx.FS.export, gen = ctx.FS.gen.fixture;
  for (const pid of Object.keys(data.palettes)) {
    const pal = data.palettes[pid];
    const ectx = S.render.exportCtx(data, pal, { c: null, p: pid, o: {}, t: {} }, false);
    for (const opts of [{ charts: false }, { charts: true }]) {
      const css = X.render('css', pal, data.task, ectx, 'de', opts, gen)[0].text;
      assert.ok(css.startsWith('/* Farbsprache · ' + pal.name_de + ' · Testaufgabe · berechnet am ' + data.date), 'Kopfzeile');
      assert.ok(css.includes('Werte und Prüfung: ' + data.url + '?p=' + pid), 'Link mit Zustand');
      for (const mode of pal.modes) {
        for (const [rid, hx] of Object.entries(pal.roles[mode])) {
          const r = data.task.roles.find((x) => x.id === rid);
          if (r.export_option && !opts[r.export_option]) { assert.ok(!css.includes('--' + rid + ':'), rid + ' ohne Option'); continue; }
          assert.ok(css.includes('--' + rid + ':') && css.includes(hx), `${pid} ${mode} ${rid} fehlt im CSS`);
        }
      }
      assert.equal(css.includes('Okabe'), opts.charts, 'Okabe-Ito-Nennung genau dann, wenn eine Okabe-Farbe im Export steht');
    }
  }
});

// #task-data ist gekürzt (pages/task.py browser_rule/browser_source, Budget 7.11): Regeln nur in der Seitensprache,
// Quellen nur mit title, url, access, short_<lang>, die Aufgabe ohne _comment. Mit den vollen Daten aus data/ muss
// der Browser für jede Startpalette und für eigene Farben genau dasselbe rendern und exportieren.
test('Gekürztes #task-data rendert wie die vollen Daten', (t) => {
  const dir = SITES[0][1];
  if (!fs.existsSync(path.join(dir, 'de', 'index.html'))) { if (REQUIRE) assert.fail('docs/ fehlt'); t.skip('docs/ fehlt'); return; }
  const rules = {}, sources = {};
  for (const f of fs.readdirSync(path.join(ROOT, 'data', 'rules'))) for (const r of JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'rules', f), 'utf8')).rules) rules[r.id] = r;
  for (const f of fs.readdirSync(path.join(ROOT, 'data', 'sources'))) for (const s of JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'sources', f), 'utf8')).sources) sources[s.id] = s;
  let n = 0;
  for (const file of taskPages(dir)) {
    const html = fs.readFileSync(file, 'utf8');
    const data = taskData(html);
    const full = JSON.parse(JSON.stringify(data));
    full.task = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'tasks', data.task.id + '.json'), 'utf8'));
    full.rules = data.rules.map((r) => rules[r.id]);
    full.sources = {};
    for (const k of Object.keys(data.sources)) full.sources[k] = sources[k];
    for (const r of data.rules) assert.ok(!('text_' + (data.lang === 'de' ? 'en' : 'de') in r), 'Regel mit Text der anderen Sprache');
    for (const s of Object.values(data.sources)) assert.ok(!('claim_de' in s) && !('unverified_de' in s), 'Quelle mit belegter Aussage');
    const ctx = load(scripts(html, file));
    const S = ctx.FS.site, gen = ctx.FS.gen[data.task.id] || ctx.FS.gen[data.gen];
    const exp = {};
    for (const o of data.task.exports.options || []) exp[o.id] = !!o.default;
    const flip = {};
    for (const k of Object.keys(exp)) flip[k] = !exp[k];
    const states = Object.keys(data.palettes).map((p) => ({ c: null, p, o: {}, t: {} }));
    for (const c of ['#E63946', '#2B4EA7', '#F0E442']) states.push({ c, p: null, o: {}, t: {} });
    for (const st of states) {
      const a = S.compute(data, st, gen, data.lang), b = S.compute(full, st, gen, data.lang);
      assert.equal(a.error, b.error, `${path.relative(ROOT, file)} ${JSON.stringify(st)}`);
      if (!a.palette) continue;
      for (const e of [exp, flip]) {
        const x = S.render.all(data, a.palette, st, gen, { exp: e }), y = S.render.all(full, b.palette, st, gen, { exp: e });
        assert.equal(JSON.stringify(x), JSON.stringify(y), `${path.relative(ROOT, file)} ${JSON.stringify(st)}`);
        n++;
      }
    }
  }
  assert.ok(n > 0);
});
