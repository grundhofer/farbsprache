'use strict';
// Sprachweiche docs/index.html (Muster landing.test.cjs aus Designsprache):
// ?lang= vor gespeicherter Wahl vor Browsersprache vor en; automatische Erkennung schreibt nie in den
// Speicher (writes === 0); Query und Hash bleiben, lang entfällt; ohne JS zwei Links.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT } = require('./helpers.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const FILE = path.join(ROOT, 'docs', 'index.html');
const page = fs.existsSync(FILE) ? fs.readFileSync(FILE, 'utf8') : '';
const script = page ? page.match(/<script id="lang-switch">([\s\S]*?)<\/script>/)[1] : '';

function run({ languages = ['de-DE'], language = 'de-DE', saved = null, search = '', hash = '', blocked = false } = {}) {
  let target = null, writes = 0, stored = saved;
  const location = { search, hash, replace(u) { target = u; } };
  const localStorage = {
    getItem() { if (blocked) throw Error('blocked'); return stored; },
    setItem(k, v) { if (blocked) throw Error('blocked'); writes++; stored = v; } };
  vm.runInNewContext(script, { location, localStorage, navigator: { languages, language } });
  return { target, writes };
}

test('landing: Sprachweiche liegt vor', (t) => { if (!page) { if (REQUIRE) assert.fail('docs/index.html fehlt'); t.skip('nicht gebaut'); } });
test('landing: Browsersprache mit Regionen, sonst Englisch; nie ein Schreibzugriff', () => {
  for (const [languages, want] of [[['de-AT'], 'de'], [['en-GB', 'de'], 'en'], [['fr-FR', 'de-CH'], 'de'], [['ja-JP'], 'en'], [['DE-de'], 'de'], [['deu'], 'en']]) {
    const r = run({ languages });
    assert.equal(r.target, want + '/', languages.join());
    assert.equal(r.writes, 0, 'die automatische Erkennung schreibt nie in den Speicher');
  }
  assert.equal(run({ languages: [], language: 'de' }).target, 'de/');
  assert.equal(run({ languages: [], language: null }).target, 'en/');
});
test('landing: ?lang schlägt gespeicherte Wahl, die schlägt den Browser', () => {
  assert.equal(run({ saved: 'en' }).target, 'en/');
  assert.equal(run({ saved: 'en', search: '?lang=de' }).target, 'de/');
  assert.equal(run({ saved: 'invalid', search: '?lang=xx', languages: ['fr'] }).target, 'en/');
  assert.equal(run({ saved: 'de', search: '?lang=xx', languages: ['en'] }).target, 'de/');
});
test('landing: lang entfällt, alle anderen Parameter und der Hash bleiben wörtlich', () => {
  assert.equal(run({ search: '?c=E63946&lang=en&f=E63946,11697A', hash: '#kopieren' }).target, 'en/?c=E63946&f=E63946,11697A#kopieren');
  assert.equal(run({ search: '?lang=de' }).target, 'de/');
  assert.equal(run({ search: '?x=%20a+b&lang=en&lang=de' }).target, 'en/?x=%20a+b');
  assert.equal(run({ search: '', hash: '#a' }).target, 'de/#a');
  assert.equal(run({ search: '?c=E63946' }).writes, 0);
});
test('landing: gesperrter Speicher hindert die Erkennung nicht', () => {
  assert.doesNotThrow(() => run({ blocked: true }));
  assert.equal(run({ blocked: true }).target, 'de/');
});
test('landing: ohne JS zwei Links, hreflang de/en/x-default, Theme inline, og-Meta absolut', () => {
  assert.ok(page.includes('<a href="de/" hreflang="de" lang="de">Deutsch</a>'));
  assert.ok(page.includes('<a href="en/" hreflang="en" lang="en">English</a>'));
  for (const h of ['hreflang="de"', 'hreflang="en"', 'hreflang="x-default"']) assert.ok(page.includes('<link rel="alternate" ' + h));
  assert.ok(page.includes('id="theme-controller"') && page.includes('prefers-color-scheme'));
  assert.ok(/<meta property="og:image" content="https:\/\/[^"]+\/og\.png">/.test(page));
  assert.ok(!script.includes('setItem'), 'die Sprachweiche schreibt nichts');
});
test('landing: jede Seite merkt sich nur den manuellen Klick auf den Sprachlink', () => {
  const de = fs.readFileSync(path.join(ROOT, 'docs', 'de', 'index.html'), 'utf8');
  const m = de.match(/<script>(document\.addEventListener\('click'[\s\S]*?)<\/script>/);
  assert.ok(m, 'Merkskript fehlt');
  let saved = null, handler = null;
  const link = { hreflang: 'en' };
  const document = { addEventListener(k, fn) { handler = fn; } };
  vm.runInNewContext(m[1], { document, localStorage: { setItem(k, v) { saved = [k, v]; } } });
  handler({ target: { closest: (sel) => (sel === '.tb-lang a' ? link : null) } });
  assert.deepEqual(saved, ['farbsprache.language', 'en']);
  saved = null;
  handler({ target: { closest: () => null } });
  assert.equal(saved, null);
});
