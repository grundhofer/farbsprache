'use strict';
// Theme-Schalter System/Hell/Dunkel (Muster tests/theme.test.cjs aus Designsprache): gleicher Controller im
// head jeder Seite, Schlüssel farbsprache.theme, gesperrter Speicher, Tabs und Zurück-Cache synchron.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT } = require('./helpers.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const DOCS = path.join(ROOT, 'docs');
const KEY = 'farbsprache.theme';
const routes = ['index.html', 'de/index.html', 'en/index.html', '404.html'];
const built = fs.existsSync(path.join(DOCS, 'de', 'index.html'));
const pages = built ? routes.map((r) => fs.readFileSync(path.join(DOCS, r), 'utf8')) : [];
const scripts = pages.map((p) => p.match(/<script id="theme-controller">([\s\S]*?)<\/script>/)[1]);
const source = fs.readFileSync(path.join(ROOT, 'web', 'theme.js'), 'utf8');

function mount({ storage = new Map(), blocked = false, script = source } = {}) {
  let ready;
  const events = {};
  const classes = new Set();
  const root = { hidden: false, dataset: {}, classList: { add: (c) => classes.add(c), contains: (c) => classes.has(c) } };
  const group = { hidden: true };
  const buttons = ['system', 'light', 'dark'].map((themeChoice) => ({ dataset: { themeChoice }, attrs: {}, listeners: {},
    setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(k, fn) { this.listeners[k] = fn; } }));
  const document = { documentElement: root, addEventListener(k, fn) { ready = fn; },
    querySelectorAll: (sel) => ({ '[data-theme-choice]': buttons, '[data-theme-controls]': [group] })[sel] || [] };
  const window = { localStorage: {
    getItem(k) { if (blocked) throw Error('blocked'); return storage.get(k) || null; },
    setItem(k, v) { if (blocked) throw Error('blocked'); storage.set(k, v); } },
  addEventListener(k, fn) { events[k] = fn; } };
  vm.runInNewContext(script, { document, window });
  const initial = root.dataset.theme;
  const jsBefore = classes.has('js');
  ready();
  return { root, group, buttons, storage, events, window, initial, jsBefore };
}

test('theme: gebaute Seiten liegen vor', (t) => { if (!built) { if (REQUIRE) assert.fail('docs/ fehlt'); t.skip('docs/ fehlt'); } });

test('theme: jede Seite lädt denselben Controller im head, mit drei Wahlmöglichkeiten', () => {
  for (let i = 0; i < pages.length; i++) {
    assert.equal(scripts[i].trim(), source.trim(), routes[i]);
    assert.ok(pages[i].indexOf('id="theme-controller"') < pages[i].indexOf('</head>'), routes[i]);
    assert.ok(pages[i].includes('@media (prefers-color-scheme: dark) { :root:not([data-theme="light"])'), routes[i]);
    assert.ok(pages[i].includes(':root[data-theme="dark"]'), routes[i]);
  }
  for (const r of ['de/index.html', 'en/index.html']) {
    const p = pages[routes.indexOf(r)];
    for (const choice of ['system', 'light', 'dark']) assert.equal((p.match(new RegExp(`data-theme-choice="${choice}"`, 'g')) || []).length, 1);
    assert.ok(p.includes('data-theme-controls role="group"'));
  }
  assert.ok(source.includes(`var KEY = '${KEY}';`), 'Schlüssel farbsprache.theme');
  assert.ok(!/bildsprache|designsprache/.test(source), 'kein fremder Schlüssel');
});
test('theme: setzt sofort html.js; Standard und ungültige Werte folgen live dem System', () => {
  for (const saved of [null, 'system', 'invalid', '<script>']) {
    const m = mount({ storage: new Map(saved ? [[KEY, saved]] : []) });
    assert.equal(m.jsBefore, true);
    assert.equal(m.initial, 'system'); assert.equal(m.buttons[0].attrs['aria-pressed'], 'true');
    assert.equal(m.group.hidden, false);
  }
});
test('theme: Wahl bleibt über Seiten erhalten, System stellt die Automatik wieder her', () => {
  const storage = new Map([['farbsprache.language', 'de']]);
  const a = mount({ storage }); a.buttons[2].listeners.click(); assert.equal(a.root.dataset.theme, 'dark');
  assert.equal(storage.get(KEY), 'dark');
  const b = mount({ storage }); assert.equal(b.initial, 'dark');
  b.buttons[1].listeners.click(); assert.equal(b.root.dataset.theme, 'light'); assert.equal(b.buttons[2].attrs['aria-pressed'], 'false');
  const c = mount({ storage }); c.buttons[0].listeners.click(); assert.equal(storage.get(KEY), 'system');
  assert.equal(storage.get('farbsprache.language'), 'de');
});
test('theme: Umschalten funktioniert auch mit gesperrtem Speicher', () => {
  const m = mount({ blocked: true }); assert.equal(m.initial, 'system');
  for (const [i, mode] of ['system', 'light', 'dark'].entries()) {
    assert.doesNotThrow(() => m.buttons[i].listeners.click()); assert.equal(m.root.dataset.theme, mode);
  }
  m.events.pageshow({ persisted: true }); assert.equal(m.root.dataset.theme, 'dark');
});
test('theme: offene Tabs und Zurück-Cache synchronisieren, ohne die Wahl zu überschreiben', () => {
  const m = mount();
  m.events.storage({ key: KEY, newValue: 'light', storageArea: m.window.localStorage }); assert.equal(m.root.dataset.theme, 'light');
  assert.equal(m.storage.has(KEY), false);
  m.events.storage({ key: 'farbsprache.language', newValue: 'en' }); assert.equal(m.root.dataset.theme, 'light');
  m.events.storage({ key: KEY, newValue: 'dark', storageArea: {} }); assert.equal(m.root.dataset.theme, 'light');
  m.events.storage({ key: null, newValue: null }); assert.equal(m.root.dataset.theme, 'system');
  m.storage.set(KEY, 'dark'); m.events.pageshow({ persisted: true }); assert.equal(m.root.dataset.theme, 'dark');
});
test('theme: storage-Ereignis wirft nicht, wenn schon der Zugriff auf localStorage scheitert (T-16)', () => {
  const events = {};
  const root = { hidden: false, dataset: {}, classList: { add() {}, contains: () => false } };
  const document = { documentElement: root, addEventListener() {}, querySelectorAll: () => [] };
  const window = { addEventListener(k, fn) { events[k] = fn; } };
  Object.defineProperty(window, 'localStorage', { get() { throw new Error('SecurityError: blocked'); } });
  vm.runInNewContext(source, { document, window });
  assert.equal(root.dataset.theme, 'system');
  assert.doesNotThrow(() => events.storage({ key: KEY, newValue: 'dark', storageArea: {} }));
  assert.equal(root.dataset.theme, 'system', 'fremder Speicher ändert nichts');
});
