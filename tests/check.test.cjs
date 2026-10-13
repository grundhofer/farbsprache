'use strict';
// Palette prüfen: web/check.js gegen tools/check.py und gegen die gebaute Seite.
// 1. Parität: tools/check.py --dump rechnet dieselben Eingaben; Modell mit Toleranz 1e-9, HTML und Exporte Byte für Byte.
// 2. Die statischen Blöcke von docs/<lang>/pruefen|check/ (Beispiel) gleichen der JS-Ausgabe Byte für Byte.
// 3. Fachregeln in JS: Kontexte hell/dunkel, Befundstufen, URL-Zustand.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT, jload, load, plain } = require('./helpers.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const PYTHON = process.env.PYTHON || 'python3';
const ctx = load(['color.js', 'export.js', 'check.js']);
const CK = ctx.FS.check;
const CFG = jload('data/check.json');

const SHADCN = ':root {\n  --background: oklch(1 0 0);\n  --foreground: oklch(0.145 0 0);\n  --primary: oklch(0.205 0 0);\n' +
  '  --primary-foreground: oklch(0.985 0 0);\n  --muted-foreground: oklch(0.556 0 0);\n  --destructive: oklch(0.577 0.245 27.325);\n' +
  '  --border: oklch(0.922 0 0);\n  --input: oklch(0.922 0 0);\n}\n.dark {\n  --background: oklch(0.145 0 0);\n  --foreground: oklch(0.985 0 0);\n' +
  '  --card: oklch(0.205 0 0);\n  --primary: oklch(0.922 0 0);\n  --input: oklch(1 0 0 / 15%);\n  --ring: var(--nope);\n}';
const CASES = [
  { text: CFG.example, opts: { example: true } },
  { text: SHADCN },
  { text: SHADCN, state: { roles: ['bg', 'text', 'accent', 'on-accent', 'text-muted', 'danger', 'border', 'bg', 'text', 'surface', 'accent', 'border-strong'], confirmed: true, bgi: null } },
  { text: '@theme { --color-background: #fff; --color-primary: #4f46e5 }\n@media (prefers-color-scheme: dark) { :root { --color-background: #0b1020 } }\n[data-theme="dark"] { --color-primary: #a5b4fc }' },
  { text: '/* #123456 */ tomato, rgb(0 0 255 / 50%), hsl(120 100% 25%), oklch(0.7 0.3 150), color(display-p3 1 0 0), #abc, #12345678, gold', state: { bgi: 2 } },
  { text: '#E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7 #FFFFFF' },
  { text: '#FFFFFF #FEFEFE #777777 #787878 #FF0000 #00A000 #0000FF #000000', opts: { new_keys: ['light|check-duplicates|0|1'], changed: [2] } },
  { text: 'hsl(0 100% 50%) hsl(51 100% 50%) hsl(103 100% 50%) hsl(154 100% 50%) hsl(206 100% 50%) hsl(257 100% 50%) hsl(309 100% 50%)' },
  { text: Array.from({ length: 15 }, (_, i) => '#' + [17, 53, 91].map((k) => ((i + 1) * k % 256).toString(16).padStart(2, '0')).join('')).join(' ') },
  { text: ':root{--bg:#fff;--text:#999;--border-strong:#ddd;--accent:#ff8800;--on-accent:#ffffff;--danger:#ff5555}' },
  { text: '#11697A' },
  { text: '#0072B2 #1F77B4 #2266AA #2B6FB0 #FFFFFF' },
  { text: '#FFFFFF #0F172B #E69F00 #56B4E9' },
  { text: '#000000 #F0E442 #FFFF66 #777777' },
  { text: CK.stateText(['#111111', '#FFFFFF', '#E69F00', '#FFFFFF80'], ['-', '-', '-.d', '-.d']) },
  // zwei Farben mit derselben Rolle bzw. demselben Namen im Block
  { text: CK.stateText(['#FFFFFF', '#0A0A0A', '#FAFAFA', '#F5F5F5', '#171717', '#737373'], ['bg', 'text', 'surface', 'surface', 'accent', 'text-muted']),
    state: { roles: ['bg', 'text', 'surface', 'surface', 'accent', 'text-muted'], confirmed: true, bgi: null } },
  { text: ':root { --surface: #FAFAFA; }\n:root { --surface: #F5F5F5; --bg: #FFFFFF; --text: #0A0A0A; }' },
  // genau ein weiterer Befund und genau eine weggelassene Farbe (Einzahl in Python und JS)
  { text: '#222 #fff #E63946 #bbb #ccc' },
  { text: Array.from({ length: 13 }, (_, i) => '#' + [17, 53, 91].map((k) => ((i + 1) * k % 256).toString(16).padStart(2, '0')).join('')).join(' ') },
  { text: 'nichts' }
];

function close(a, b, where) {
  if (typeof a === 'number' && typeof b === 'number') { assert.ok(Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(b)), `${where}: ${a} != ${b}`); return; }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') { assert.equal(a, b, where); return; }
  assert.equal(Array.isArray(a), Array.isArray(b), where);
  assert.deepEqual(Object.keys(a).sort(), Object.keys(b).sort(), where + ' (Schlüssel)');
  for (const k of Object.keys(a)) close(a[k], b[k], where + '.' + k);
}
function strip(m) {
  const pick = (o, ks) => { const r = {}; for (const k of ks) if (k in o) r[k] = o[k] === undefined ? null : o[k]; return r; };
  const fin = (f) => pick(f, ['id', 'sev', 'i', 'j', 'key', 'value', 'kind', 'open', 'repair']);
  return plain({ colors: m.colors.map((c) => pick(c, ['hex', 'eff', 'alpha', 'role', 'role_src', 'ctx', 'oklch', 'best', 'chroma'])),
    ctxs: m.ctxs.map((cx) => ({ ctx: cx.ctx, bg: cx.bg, set: cx.set, findings: cx.findings.map(fin), passes: cx.passes.map(fin), dist: cx.dist })),
    confirmed: m.confirmed, has_names: m.has_names, notes: m.notes });
}
function firstDiff(a, b) { let k = 0; while (k < a.length && a[k] === b[k]) k++; return `@${k}\nJS: ${a.slice(k - 60, k + 100)}\nPY: ${b.slice(k - 60, k + 100)}`; }

test('Parität mit tools/check.py (Modell, HTML, Exporte)', (t) => {
  const dir = path.join(ROOT, 'tests', 'out');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, 'check-cases.json');
  fs.writeFileSync(file, JSON.stringify(CASES));
  const r = spawnSync(PYTHON, ['tools/check.py', '--dump', file, '--html'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 1 << 28 });
  if (r.error || r.status !== 0) {
    if (REQUIRE) assert.fail('tools/check.py --dump lief nicht: ' + (r.error ? r.error.message : r.stderr));
    t.skip('python3 nicht verfügbar');
    return;
  }
  const py = JSON.parse(r.stdout);
  CASES.forEach((c, i) => {
    const sc = CK.scan(c.text, CFG);
    close(plain(sc), py.res[i].scan, `Fall ${i} scan`);
    const m = CK.analyze(sc, CFG, py.R.de.refs, c.state ? plain(c.state) : undefined);
    close(strip(m), py.res[i].model, `Fall ${i} Modell`);
    assert.equal(CK.query(m, (c.state || {}).bgi), py.res[i].query, `Fall ${i} query`);
    for (const lang of ['de', 'en']) {
      const h = CK.render(m, py.R[lang], c.opts), e = CK.exportHtml(m, py.R[lang]);
      assert.ok(h === py.res[i]['html_' + lang], `Fall ${i} HTML ${lang} ${firstDiff(h, py.res[i]['html_' + lang])}`);
      assert.ok(e === py.res[i]['exp_' + lang], `Fall ${i} Export ${lang} ${firstDiff(e, py.res[i]['exp_' + lang])}`);
    }
  });
});

for (const [lang, seg] of [['de', 'pruefen'], ['en', 'check']]) {
  test(`Gebaute Prüfseite ${lang}: Beispiel statisch = JS`, (t) => {
    const f = path.join(ROOT, 'docs', lang, seg, 'index.html');
    if (!fs.existsSync(f)) { if (REQUIRE) assert.fail(`${f} fehlt (python3 build.py)`); t.skip('docs/ fehlt'); return; }
    const html = fs.readFileSync(f, 'utf8');
    const m0 = html.match(/<script type="application\/json" id="check-data">([\s\S]*?)<\/script>/);
    if (!m0) { t.skip('Platzhalterseite (pages/check.py nicht gebaut)'); return; }
    const D = JSON.parse(m0[1].replace(/<\\\//g, '</'));
    const grab = (id) => html.match(new RegExp('<!--fs:' + id + '-->([\\s\\S]*?)<!--/fs:' + id + '-->'))[1];
    const m = CK.analyze(CK.scan(D.cfg.example, D.cfg), D.cfg, D.refs, {});
    const R = { lang: D.lang, T: D.T, F: D.F, refs: D.refs, cfg: D.cfg, rules: D.rules, sources: D.sources, comparisons: D.comparisons, paths: D.paths, url: D.example_url, date: D.date };
    assert.equal(D.example_url, D.url + '?' + CK.query(m));
    const out = CK.render(m, R, { example: true });
    assert.ok(out === grab('chk-out'), 'Ergebnis ' + firstDiff(out, grab('chk-out')));
    const ex = CK.exportHtml(m, R);
    assert.ok(ex === grab('chk-exp'), 'Export ' + firstDiff(ex, grab('chk-exp')));
    // genau die ausgelieferten, kompaktierten Dateien (color.js mit FS_CONST)
    const shipped = {};
    vm.createContext(shipped);
    for (const a of ['color.js', 'export.js', 'check.js']) vm.runInContext(fs.readFileSync(path.join(ROOT, 'docs', 'assets', a), 'utf8'), shipped, { filename: a });
    const S = shipped.FS.check, ms = S.analyze(S.scan(D.cfg.example, D.cfg), D.cfg, D.refs, {});
    assert.ok(S.render(ms, R, { example: true }) === grab('chk-out'), 'ausgelieferte check.js');
    for (const s of ['color.js', 'export.js', 'check.js', 'site.js', 'ui/check.js']) assert.match(html, new RegExp('assets/' + s.replace('.', '\\.') + '\\?v='));
  });
}

test('Kontexte: :root hell, .dark dunkel (shadcn), Rollen geraten', () => {
  const m = CK.analyze(CK.scan(SHADCN, CFG), CFG, ctx.FS.color.referenceValues(jload('data/comparisons.json'), { 'okabe-ito': jload('data/datasets/okabe-ito.json') }));
  assert.deepEqual(plain(m.ctxs.map((c) => c.ctx)), ['light', 'dark']);
  assert.deepEqual(plain(m.colors.filter((c) => c.ctx === 'light').map((c) => c.role)), ['bg', 'text', 'accent', 'on-accent', 'text-muted', 'danger', 'border']);
  assert.deepEqual(plain(m.colors.filter((c) => c.ctx === 'dark').map((c) => c.role)), ['bg', 'text', 'surface', 'accent', 'border-strong']);
  assert.deepEqual(plain(m.notes), [{ key: 'var', name: 'ring', ref: 'nope' }]);
});

test('Befundstufen: Verfehlt nur mit bestätigten Rollen, Konventionen nur als Hinweis', () => {
  const refs = ctx.FS.color.referenceValues(jload('data/comparisons.json'), { 'okabe-ito': jload('data/datasets/okabe-ito.json') });
  for (const c of CASES) {
    const m = CK.analyze(CK.scan(c.text, CFG), CFG, refs);
    for (const cx of m.ctxs) for (const f of cx.findings) {
      assert.notEqual(f.sev, 'fail', c.text.slice(0, 20));
      if (!/^check-(text|nontext)$/.test(f.id)) assert.equal(f.sev, 'note', f.id);
    }
    const roles = m.colors.map((x) => x.role);
    const m2 = CK.analyze(CK.scan(c.text, CFG), CFG, refs, { roles, confirmed: true, bgi: null });
    for (const cx of m2.ctxs) for (const f of cx.findings) {
      if (f.sev === 'fail') { assert.ok(/^check-(text|nontext)$/.test(f.id)); assert.ok(m2.colors[f.i].role); }
      if (!/^check-(text|nontext)$/.test(f.id)) assert.equal(f.sev, 'note');
    }
  }
});

test('CSS-Export: jede geprüfte Farbe eindeutig adressierbar, auch nach dem Teilen über den Link', () => {
  const refs = ctx.FS.color.referenceValues(jload('data/comparisons.json'), { 'okabe-ito': jload('data/datasets/okabe-ito.json') });
  const R = { lang: 'de', T: { 'hex.head': 'Kopf {date}', 'css.checked': 'geprüft', 'hex.link': 'Link {url}', 'ctx.light': 'Hell', 'ctx.dark': 'Dunkel' },
    cfg: CFG, url: 'https://example.org/', date: '2026-10-11' };
  const rq = CK.readQuery('?f=FFFFFF,0A0A0A,FAFAFA,F5F5F5,171717,737373&r=bg,text,surface,surface,accent,text-muted', CFG);
  const st = CK.stateRoles(rq.r);
  const text = CK.stateText(rq.f, rq.r);
  assert.match(text, /--surface: #FAFAFA;\n {2}--surface-b: #F5F5F5;/);
  const m = CK.analyze(CK.scan(text, CFG), CFG, refs, { roles: st.roles, confirmed: true, bgi: rq.bgi });
  for (const src of [text, ':root { --surface: #FAFAFA; }\n:root { --surface: #F5F5F5; }\n.dark { --a: #111111; --a: #222222; }']) {
    const mm = src === text ? m : CK.analyze(CK.scan(src, CFG), CFG, refs);
    const css = CK.css(mm, R);
    for (const block of css.split('@media')) {
      const names = [...block.matchAll(/^\s*--([A-Za-z0-9_-]+):/gm)].map((x) => x[1]);
      assert.equal(new Set(names).size, names.length, `doppelte Custom Property: ${names}`);
    }
    for (const c of mm.colors) assert.ok(css.includes(c.eff), `${c.eff} fehlt im CSS`);
  }
  // Rundlauf: derselbe Link ergibt dieselben Namen und Rollen
  assert.equal(CK.query(m, rq.bgi), 'f=FFFFFF,0A0A0A,FAFAFA,F5F5F5,171717,737373&r=bg,text,surface,surface,accent,text-muted');
  assert.deepEqual(plain(m.colors.map((c) => c.role)), ['bg', 'text', 'surface', 'surface', 'accent', 'text-muted']);
});

test('Scanner und Parser bleiben bei langen Leerraumfolgen linear, Trimmen und !important wie zuvor', () => {
  const C = ctx.FS.color, sp = ' '.repeat(200000);
  let t0 = Date.now();
  CK.scan(':root{--a:' + sp + 'x' + sp + 'y}', CFG);
  CK.scan(':root{--a:' + sp + 'x' + sp + '!importan}', CFG);
  assert.equal(C.parse('x' + sp + 'x'), null);
  assert.equal(C.parse(sp + 'red' + sp).hex, '#FF0000');
  assert.ok(Date.now() - t0 < 1500, `zu langsam: ${Date.now() - t0} ms`);
  const sc = CK.scan(':root { --a: #fff !important ; --b: red!IMPORTANT;\t--c:\n #000 \n}', CFG);
  assert.deepEqual(plain(sc.colors.map((c) => [c.hex, c.names[0], c.raw])), [['#FFFFFF', 'a', '#fff'], ['#FF0000', 'b', 'red'], ['#000000', 'c', '#000']]);
});

test('URL-Zustand: f, r, bgi', () => {
  const rq = CK.readQuery('?f=0F172B,F8FAFC,FFFFFF80&r=text,bg,-.d&bgi=1', CFG);
  assert.deepEqual(plain(rq), { f: ['#0F172B', '#F8FAFC', '#FFFFFF80'], r: ['text', 'bg', '-.d'], bgi: 1, dirty: false });
  const text = CK.stateText(rq.f, rq.r);
  assert.equal(text, ':root {\n  --text: #0F172B;\n  --bg: #F8FAFC;\n}\n.dark {\n  #FFFFFF80;\n}');
  assert.deepEqual(plain(CK.stateRoles(rq.r)), { roles: ['text', 'bg', null], confirmed: true });
  const refs = ctx.FS.color.referenceValues(jload('data/comparisons.json'), { 'okabe-ito': jload('data/datasets/okabe-ito.json') });
  const m = CK.analyze(CK.scan(text, CFG), CFG, refs, { roles: ['text', 'bg', null], confirmed: true, bgi: 1 });
  assert.equal(CK.query(m, 1), 'f=0F172B,F8FAFC,FFFFFF80&r=text,bg,-.d&bgi=1');
  assert.equal(plain(CK.readQuery('?f=xyz&bgi=4', CFG)).dirty, true);
  // ohne Bestätigung: r trägt nur den Kontext, nach dem Neuladen bleiben hell und dunkel getrennt, ohne Rollen
  const mu = CK.analyze(CK.scan(SHADCN, CFG), CFG, refs);
  const qu = CK.query(mu);
  assert.match(qu, /&r=(-(\.d)?,)*-(\.d)?$/);
  const ru = CK.readQuery('?' + qu, CFG);
  assert.deepEqual(plain(CK.stateRoles(ru.r)), { roles: null, confirmed: false });
  const mu2 = CK.analyze(CK.scan(CK.stateText(ru.f, ru.r), CFG), CFG, refs);
  assert.deepEqual(plain(mu2.colors.map((c) => [c.eff, c.ctx])), plain(mu.colors.map((c) => [c.eff, c.ctx])));
  assert.equal(mu2.has_names, false);
  assert.equal(CK.query(mu2), qu);
  assert.equal(CK.query(CK.analyze(CK.scan('#0F172B #F8FAFC', CFG), CFG, refs)), 'f=0F172B,F8FAFC');
  // Reihenfolge wie scan (hell vor dunkel), bgi wandert mit
  assert.deepEqual(plain(CK.readQuery('?f=111111,FFFFFF,000000&r=text.d,bg,-&bgi=0', CFG)),
    { f: ['#FFFFFF', '#000000', '#111111'], r: ['bg', '-', 'text.d'], bgi: 2, dirty: true });
});
