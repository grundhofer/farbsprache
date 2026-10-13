'use strict';
// Laufzeit der gebauten Seiten im kleinen DOM (tests/dom.cjs): Zustand aus der URL, Klicks und Eingaben wie im Browser,
// mit den ausgelieferten Skripten. Belegt das Verhalten des Rahmens, das kein reiner Test sieht:
// Meldung beim ersten Lauf mit unlösbarem Zustand (auch nach dem Sprachwechsel), Hinweis und Fehler unter dem Farbfeld,
// Leeren der eigenen Farben, gedrückte Chips bei f, Optionen beim Wechsel der Startpalette (preset_control), c als Ersatz
// für seed_param, Namen, Dateinamen und Links eigener Zustände. Dazu je Aufgabenseite ein Lauf ohne Ausnahme.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { ROOT, load, jload } = require('./helpers.cjs');
const { open, parse, Document } = require('./dom.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const DOCS = path.join(ROOT, 'docs');
const file = (rel) => path.join(DOCS, rel, 'index.html');
const built = fs.existsSync(file('de/website'));
const text = (html) => parse(new Document(), html).map((n) => n.textContent).join('');
function tasks() {
  const out = [];
  for (const lang of ['de', 'en']) {
    if (!fs.existsSync(path.join(DOCS, lang))) continue;
    for (const seg of fs.readdirSync(path.join(DOCS, lang))) {
      const f = path.join(DOCS, lang, seg, 'index.html');
      if (fs.existsSync(f) && fs.readFileSync(f, 'utf8').includes('id="task-data"')) out.push(lang + '/' + seg);
    }
  }
  return out;
}
// Link der Seite (relativ) → [Seite, Query]
function follow(from, href) {
  const u = new URL(href, 'https://x/' + from + '/');
  return [u.pathname.replace(/^\/|\/$/g, ''), u.search.slice(1)];
}
// Schreibzugriffe auf eine Eigenschaft eines Elements zählen (innerHTML, textContent)
function spy(el, prop) {
  let proto = el, desc;
  while (proto && !(desc = Object.getOwnPropertyDescriptor(proto, prop))) proto = Object.getPrototypeOf(proto);
  const log = [];
  Object.defineProperty(el, prop, { configurable: true, get() { return desc.get.call(this); }, set(v) { log.push(String(v)); desc.set.call(this, v); } });
  return log;
}
const i18n = (p) => JSON.parse(p.$('#i18n').textContent);
const shown = (el) => !!el && !el.hidden;
const pressed = (p, sel) => p.$$(sel).filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.getAttribute('data-val') || b.getAttribute('data-preset'));

test('Gebaute Seiten liegen vor', (t) => {
  if (!built) { if (REQUIRE) assert.fail('docs/ fehlt – erst python3 build.py'); t.skip('docs/ fehlt'); }
});

if (built) {
  test('Jede Aufgabenseite läuft mit Startpalette, eigener Farbe und Sprachlink ohne Ausnahme', () => {
    for (const rel of tasks()) {
      for (const q of ['', 'c=E63946']) {
        const p = open(file(rel), q);
        assert.ok(p.$('#chk-sum').textContent.trim(), `${rel}?${q}: Prüfbericht leer`);
        const link = p.$('.tb-lang a').getAttribute('href');
        assert.ok(!q || link.includes('?' + p.search().slice(1)), `${rel}?${q}: Sprachlink ohne Zustand`);
        if (q) assert.deepEqual(pressed(p, '[data-preset]'), [], `${rel}: mit c ist kein Startpaletten-Chip gedrückt`);
        else if (p.$('[data-preset]')) assert.deepEqual(pressed(p, '[data-preset]'), [p.data.first], `${rel}: Startpalette 1 gedrückt`);
      }
    }
  });

  test('Erster Lauf mit unlösbarem Zustand zeigt die Meldung, auch nach dem Sprachwechsel', () => {
    const cases = [['de/text-auf-bild', 'sc=FF00FF'], ['de/text-auf-bild', 'tc=1B1B1B'], ['de/ki-bild', 'f=1B3A76']];
    for (const [rel, q] of cases) {
      let p = open(file(rel), q);
      for (let round = 0; round < 2; round++) {
        const S = p.win.FS.site, D = p.data, gen = p.win.FS.gen[D.task.id] || p.win.FS.gen[D.gen];
        const r = S.compute(D, S.state.read(D.task, '?' + q).state, gen, D.lang);
        assert.ok(r.error, `${rel}?${q}: Zustand ist lösbar, Testfall prüft nichts`);
        const msg = D.text['solve.' + r.error] || D.frame['solve.' + r.error];
        const alert = p.$('#pal-notes [role="alert"]');
        assert.ok(alert, `${D.lang}: ${rel}?${q}: Meldung fehlt beim ersten Lauf`);
        assert.equal(alert.textContent, text(msg));
        assert.equal(p.search(), '?' + q, 'Zustand bleibt in der URL');
        const [twin, tq] = follow(rel, p.$('.tb-lang a').getAttribute('href'));
        assert.equal(tq, q, 'Sprachlink trägt den Zustand');
        p = open(file(twin), tq);
      }
    }
  });

  test('Hinweis und Fehler unter dem Farbfeld verschwinden, wenn eine Startpalette gewählt oder das Feld geleert wird', () => {
    const p = open(file('de/folien'), '');
    const note = p.$('#seed-note'), err = p.$('#seed-err'), seed = p.$('#seed');
    p.input(seed, 'oklch(0.7 0.3 30)');
    assert.equal(note.hidden, false, 'Außerhalb von sRGB: Hinweis sichtbar');
    p.click('[data-preset="tinte"]');
    assert.equal(note.hidden, true, 'nach der Startpalette ausgeblendet');
    assert.equal(seed.value, '');
    p.input(seed, 'oklch(0.7 0.3 30)');
    p.click('[data-seed-reset]');
    assert.equal(note.hidden, true, 'nach Zurücksetzen ausgeblendet');
    p.input(seed, 'oklch(0.7 0.3 30)');
    p.input(seed, '', 'input');
    assert.equal(note.hidden, true, 'nach dem Leeren ausgeblendet');
    p.input(seed, 'keine Farbe');
    assert.ok(err.textContent, 'Fehler bei unbekannter Schreibweise');
    p.click('[data-preset="graphit"]');
    assert.equal(err.textContent, '', 'Fehler nach der Startpalette weg');
    assert.equal(seed.hasAttribute('aria-invalid'), false);
  });

  test('Eigene Farben (colors): leere Felder setzen f zurück, gedrückt ist dann kein Startpaletten- oder Vorschlags-Chip', () => {
    for (const noUi of [true, false]) {
      let p = open(file('de/ki-bild'), '', { noUi });
      const ins = p.$$('[data-ctl="f"] input');
      ins[0].value = '#112233';
      p.input(ins[1], '#FFEEDD');
      assert.equal(p.search(), '?f=112233,FFEEDD', 'Komma unkodiert wie auf der Prüfseite');
      assert.deepEqual(pressed(p, '[data-preset]'), [], `ui=${!noUi}: f gilt vor p`);
      ins[0].value = '';
      p.input(ins[1], '');
      assert.equal(p.search(), '', 'alle Felder leer: f fällt weg');
      assert.deepEqual(pressed(p, '[data-preset]'), [p.data.first], 'danach wieder Startpalette 1');
      p = open(file('de/ki-bild'), 'c=E63946', { noUi });
      assert.deepEqual(pressed(p, '[data-ctl="s"] [data-val]'), ['calm'], 'mit c ist der Vorschlag gedrückt');
      p = open(file('de/ki-bild'), 'c=E63946&f=112233,FFEEDD', { noUi });
      assert.deepEqual(pressed(p, '[data-ctl="s"] [data-val]'), [], `ui=${!noUi}: f gilt vor c, kein Vorschlag gedrückt`);
      assert.deepEqual(pressed(p, '[data-preset]'), []);
    }
  });

  test('Eigene Farben: Jedes Feld behält seine Rolle, eine Lücke vor einem gefüllten Feld wird gemeldet statt aufgerückt', () => {
    for (const rel of ['de/ki-bild', 'en/ai-image']) {
      const p = open(file(rel), '');
      const ins = p.$$('[data-ctl="f"] input'), err = p.$('[data-ctl="f"] .err');
      assert.ok(err, `${rel}: Fehlerzeile fehlt`);
      ins[0].value = '#1B3A76';
      p.input(ins[3], '#F6F3ED');
      assert.equal(p.search(), '', `${rel}: f bleibt ungesetzt`);
      assert.deepEqual(ins.map((i) => i.value), ['#1B3A76', '', '', '#F6F3ED'], `${rel}: kein Feld rückt nach`);
      assert.deepEqual(ins.map((i) => i.getAttribute('aria-invalid')), [null, 'true', 'true', null]);
      assert.equal(err.textContent, p.data.text['ui.f_gap']);
      ins[1].value = '#D13B2F';
      p.input(ins[2], '#E9DCC8');
      assert.equal(p.search(), '?f=1B3A76,D13B2F,E9DCC8,F6F3ED', `${rel}: alle vier Felder in ihrer Reihenfolge`);
      assert.equal(err.textContent, '');
      assert.deepEqual(ins.map((i) => i.getAttribute('aria-invalid')), [null, null, null, null]);
      const roles = p.$$('#pal-roles .role-t b').map((b) => b.textContent);
      const hexes = p.$$('#pal-roles code.hex').map((c) => c.textContent);
      assert.equal(hexes[roles.indexOf(p.data.task.roles.find((r) => r.id === 'background')['name_' + p.data.lang])], '#F6F3ED', `${rel}: Feld 4 ist der Hintergrund`);
    }
  });

  test('preset_control: Wechsel der Startpalette behält Optionen, die die neue nicht festlegt', () => {
    const p = open(file('de/diagramm'), 'p=seq-viridis&pr=1&bg=dark');
    p.click('[data-ctl="t"] [data-val="div"]');
    assert.equal(p.search(), '?p=div-blue-orange&pr=1&bg=dark');
    p.click('[data-ctl="mark"] [data-val="areas"]');
    p.click('[data-ctl="t"] [data-val="cat"]');
    assert.equal(p.search(), '?p=cat-okabe&pr=1&bg=dark&mark=areas');
    p.click('[data-ctl="t"] [data-val="seq"]');
    assert.equal(p.search(), '?p=seq-viridis&pr=1&bg=dark&mark=areas', 'n und fam legt die Startpalette fest');
    // Mit c wählt t keine Startpalette; „Zurücksetzen“ kehrt zur Startpalette dieses Werts zurück
    const q = open(file('de/diagramm'), 'c=E63946&bg=dark');
    q.click('[data-ctl="t"] [data-val="seq"]');
    assert.equal(q.search(), '?c=E63946&t=seq&bg=dark');
    q.click('[data-seed-reset]');
    assert.equal(q.search(), '?p=seq-viridis&bg=dark');
    assert.match(q.$('#exp-hex-0').textContent.split('\n')[0], /· viridis, 5 Stufen auf dunklem Grund, angepasst ·/);
  });

  test('c aus Weiter-Links und Kacheln gilt auf Seiten mit eigenem seed_param', () => {
    const home = open(file('de'), 'c=E63946');
    const tile = home.$$('[data-carry]').map((a) => a.getAttribute('href')).find((h) => h.includes('text-auf-bild'));
    const [rel, q] = follow('de', tile);
    assert.equal(q, 'c=E63946');
    const p = open(file(rel), q);
    assert.equal(p.search(), '?sc=E63946', 'die URL schreibt den seed_param');
    assert.equal(p.$('#seed').value, '#E63946');
    assert.equal(p.$('.tb-lang a').getAttribute('href').split('?')[1], 'sc=E63946');
    for (const a of p.$$('[data-carry]')) assert.ok(a.getAttribute('href').endsWith('?c=E63946'), 'Weiter-Links tragen c');
  });

  test('Eigene Zustände ohne c nennen die Startpalette nur als „angepasst“, mit f „Eigene Farben“; Dateiname eigen, Link ohne p', () => {
    // Diagramm (gen.displayName): Der Name nennt Familie, Anzahl und Hintergrund der gezeigten Farben,
    // nie die Familie einer anderen Startpalette; t ohne p wählt die Startpalette des Datentyps
    const cases = [['en/charts', 't=div&fam=cb-rdbu', 'RdBu, 5 steps on white, adjusted', 'Okabe-Ito, lines on white'],
      ['en/charts', 'p=div-blue-orange&fam=cb-rdbu&n=9', 'RdBu, 9 steps on white, adjusted', 'Blue-orange, 5 steps'],
      ['de/diagramm', 'p=seq-viridis&fam=cb-blues&n=9', 'Blues, 9 Stufen auf Weiß, angepasst', 'viridis, 5 Stufen'],
      ['de/diagramm', 'fam=tol-bright', 'Tol bright, 4 Farben, Linien auf Weiß, angepasst', 'Okabe-Ito, Linien auf Weiß'],
      ['de/diagramm', 'p=seq-viridis&bg=dark', 'viridis, 5 Stufen auf dunklem Grund, angepasst', null],
      ['de/ki-bild', 'f=112233,FFEEDD', 'Eigene Farben', 'Dunkelblau, Papier, Rot'],
      ['de/ki-bild', 'p=gruen&f=112233,FFEEDD', 'Eigene Farben', null],
      ['de/marke', 'c2=E63946', 'Tinte, angepasst', null]];
    for (const [rel, q, name, old] of cases) {
      const p = open(file(rel), q);
      const pal = p.win.FS.site.compute(p.data, p.win.FS.site.state.read(p.data.task, '?' + q).state, p.win.FS.gen[p.data.task.id], p.data.lang).palette;
      assert.equal(pal.preset, null, `${rel}?${q}: eigener Zustand ist keine Startpalette`);
      assert.equal(pal['name_' + p.data.lang], name, `${rel}?${q}: Name`);
      for (const pre of p.$$('#kopieren pre')) {
        const t = pre.textContent;
        if (old) assert.ok(!t.includes(old + ' ·') && !t.includes('„' + old + '“') && !t.includes('“' + old + '”'), `${rel}?${q}: ${pre.id} nennt die Startpalette`);
        assert.ok(!/starter palette|Startpalette/.test(t), `${rel}?${q}: ${pre.id} nennt eine Startpalette`);
        for (const m of t.match(/https:\/\/\S+/g) || []) assert.ok(!/[?&]p=/.test(m) || /[?&]p=/.test(p.search()) && !q.includes('f='), `${rel}?${q}: Link ${m}`);
      }
      assert.ok(p.$$('#kopieren pre').some((pre) => pre.textContent.includes(name)), `${rel}?${q}: kein Export nennt ${name}`);
      for (const b of p.$$('[data-download]')) assert.ok(b.getAttribute('data-filename').includes('-eigen'), b.getAttribute('data-filename'));
    }
  });

  test('preset_control: t ohne passendes p wählt die Startpalette des Datentyps, Kopiertexte nennen keine fremde Familie', () => {
    const cases = [['de/diagramm', 't=seq&fam=okabe-ito', '?p=seq-viridis', 'viridis, 5 Stufen', 'Okabe-Ito'],
      ['en/charts', 't=div', '?p=div-blue-orange', 'Blue-orange, 5 steps', 'Okabe-Ito'],
      ['de/diagramm', 'p=cat-okabe&t=hl', '?p=hl-gray', 'Grau mit Blau hervorgehoben', 'Linien auf Weiß'],
      ['en/charts', 't=div&fam=cb-rdbu', '?p=div-blue-orange&fam=cb-rdbu', 'RdBu, 5 steps on white, adjusted', 'Okabe-Ito, lines']];
    for (const [rel, q, search, name, foreign] of cases) {
      const p = open(file(rel), q);
      assert.equal(p.search(), search, `${rel}?${q}: URL`);
      assert.equal(p.$('#exp-hex-0').textContent.split('\n')[0].split(' · ')[1], name, `${rel}?${q}: Name in der Hex-Liste`);
      for (const pre of p.$$('#kopieren pre')) assert.ok(!pre.textContent.includes(foreign), `${rel}?${q}: ${pre.id} nennt ${foreign}`);
      if (p.data.task.controls.find((c) => c.id === 'n')) {
        const n = Number(p.$('#ctl-n').value), t = p.data.palettes[search.slice(3).split('&')[0]].input.options;
        assert.equal(n, t.n, `${rel}?${q}: Anzahl der Startpalette`);
      }
    }
  });

  test('Kurz erklärt: Demo context mit Farben aus demo_vars, Knopf „Brücke zeigen“ schaltet aria-pressed und data-bridge', () => {
    // Eingaben aus data/explain/*.json, Hex rechnet der Bau; hier gegengerechnet mit color.js
    const entry = ['brand', 'website', 'charts', 'slides'].map((f) => jload('data/explain/' + f + '.json').entries)
      .reduce((a, b) => a.concat(b), []).find((e) => e.id === 'context');
    const C = load(['color.js']).FS.color;
    const want = Object.keys(entry.demo_vars).map((k) => '--d-' + k + ':' + C.parse(entry.demo_vars[k], false).hex + ';').join('');
    for (const [rel, label] of [['de/erklaert', 'Brücke zeigen'], ['en/explained', 'Show bridge']]) {
      const p = open(file(rel), '', { hash: '#context' });
      const box = p.$('#context .demo-context'), btn = p.$('#context [data-bridge-toggle]');
      assert.ok(box && btn, `${rel}: Demo oder Knopf fehlt`);
      assert.equal(box.getAttribute('style'), want, `${rel}: Variablen des Musters`);
      assert.equal(btn.textContent, label);
      assert.equal(box.childNodes.filter((n) => n.nodeType === 8).length, 0, `${rel}: Kommentar des Musters ausgeliefert`);
      const state = () => [btn.getAttribute('aria-pressed'), box.getAttribute('data-bridge')];
      assert.deepEqual(state(), ['false', 'off'], `${rel}: Ausgangszustand`);
      p.click(btn);
      assert.deepEqual(state(), ['true', 'on'], `${rel}: Brücke an`);
      p.click(btn);
      assert.deepEqual(state(), ['false', 'off'], `${rel}: Brücke aus`);
    }
  });

  test('Als Datei speichern: Recraft-JSON als .json, Design-Tokens als application/design-tokens+json', () => {
    for (const [rel, q] of [['de/ki-bild', 'mdl=recraft'], ['en/ai-image', 'p=gruen&mdl=recraft&f=1B3A76,F6F3ED,D13B2F']]) {
      const p = open(file(rel), q);
      const b = p.$('[data-download="#exp-prompt-1"]');
      assert.ok(b, `${rel}?${q}: zweiter Block fehlt`);
      assert.match(b.getAttribute('data-filename'), /-controls\.json$/);
      assert.equal(b.getAttribute('data-mime'), 'application/json');
      JSON.parse(p.$('#exp-prompt-1').textContent);
    }
    const w = open(file('de/website'), 'c=E63946');
    for (const b of w.$$('[data-download^="#exp-dtcg-"]')) assert.equal(b.getAttribute('data-mime'), 'application/design-tokens+json');
  });

  test('Dateinamen einer Seite sind eindeutig, auch für eigene Farben', () => {
    for (const rel of tasks()) {
      for (const q of ['', 'c=E63946']) {
        const names = open(file(rel), q).$$('[data-download]').map((b) => b.getAttribute('data-filename'));
        assert.equal(new Set(names).size, names.length, `${rel}?${q}: ${names.join(', ')}`);
      }
    }
  });

  test('Fehlerzustand: nichts kopierbar, was nicht zur Eingabe passt; Meldung neben dem Hauptknopf und in der Kopierleiste', () => {
    const css = fs.readFileSync(path.join(DOCS, 'assets', 'site.css'), 'utf8');
    assert.match(css, /#task\[data-error\] \[data-main\], #task\[data-error\] \[data-main-bar\], #task\[data-error\] #pal-roles \[data-copy\],\n#task\[data-error\] #kopieren > :not\(h2\):not\(\.exp-err\) \{ display:none !important; \}/);
    const state = (p) => ({ err: p.$('#task').hasAttribute('data-error'), msgs: p.$$('[data-pal-msg]').map((a) => (shown(a) ? a.textContent : null)),
      cmp: shown(p.$('.pal-cmp')) ? p.$('.pal-cmp').textContent : null, exp: shown(p.$('.exp-err')) });
    // von der Startseite mit Rot auf Text auf Bild: kein Lauf ergab je eine Palette, verglichen wird mit der Startpalette
    for (const rel of ['de/text-auf-bild', 'en/text-on-image']) {
      const p = open(file(rel), 'c=E63946');
      const F = p.data.frame, s = state(p);
      assert.deepEqual(s, { err: true, msgs: [F['pal_msg.err'], F['pal_msg.err']], cmp: F['pal_msg.cmp'].replace('{name}', p.data.palettes[p.data.first]['name_' + p.data.lang]), exp: true }, rel);
      assert.equal(p.$('.exp-err').textContent, F['pal_msg.exp']);
    }
    // gültig, dann unlösbar getippt: verglichen wird mit der vorigen eigenen Palette, ihre Farbe steht dabei
    const p = open(file('de/text-auf-bild'), 'sc=333333');
    assert.equal(state(p).err, false);
    p.input('#seed', '#FF00FF');
    assert.equal(p.search(), '?sc=FF00FF');
    assert.deepEqual(state(p), { err: true, msgs: [p.data.frame['pal_msg.err'], p.data.frame['pal_msg.err']], cmp: p.data.frame['pal_msg.cmp'].replace('{name}', 'Eigene Farbe, #333333'), exp: true });
    p.input('#seed', '#333333');
    assert.deepEqual(state(p), { err: false, msgs: [null, null], cmp: null, exp: false }, 'wieder lösbar: alles zurück');
    // KI-Bild mit eigenen Farben ohne Lösung (dritter Fall)
    assert.equal(state(open(file('de/ki-bild'), 'f=1B3A76')).err, true);
  });

  test('Eigene Farbe verändert: Zeile „{n} Werte angepasst ↓“ neben dem Hauptknopf und in der Kopierleiste, Link auf die Hinweise', () => {
    for (const rel of tasks()) {
      for (const q of ['', 'c=E63946', 'c=F2A900']) {
        const p = open(file(rel), q);
        const S = p.win.FS.site, D = p.data, gen = p.win.FS.gen[D.task.id] || p.win.FS.gen[D.gen];
        const r = S.compute(D, S.state.read(D.task, '?' + q).state, gen, D.lang);
        const n = r.palette ? (r.palette.changes || []).length : 0;
        const want = r.error ? D.frame['pal_msg.err'] : q && n ? (n === 1 ? D.frame['pal_msg.chg_1'] : D.frame['pal_msg.chg'].replace('{n}', String(n))) : null;
        const msgs = p.$$('[data-pal-msg]');
        assert.equal(msgs.length, 2, rel);
        for (const a of msgs) {
          assert.equal(shown(a) ? a.textContent : null, want, `${rel}?${q}`);
          assert.equal(a.getAttribute('href'), '#pal-notes');
        }
        if (want && !r.error) assert.ok(p.$('#pal-notes .note'), `${rel}?${q}: Hinweis fehlt`);
      }
    }
  });

  test('Farbfeld: Fehler erst nach einer Pause oder beim Verlassen, Kurzformen warten, eine Entprellung', () => {
    const p = open(file('de/website'), '');
    const seed = p.$('#seed'), err = p.$('#seed-err'), strip = () => p.$('#pal-strip').innerHTML, before = strip();
    const type = (v, ms) => { seed.value = v; seed.dispatchEvent({ type: 'input', bubbles: true, preventDefault() {}, stopPropagation() {} }); p.tick(ms); };
    for (const v of ['#', '#E', '#E6', '#E63', '#E639', '#E6394']) {
      type(v, 250);
      assert.equal(err.textContent, '', `${v}: kein Fehler während des Tippens`);
      assert.equal(p.search(), '', `${v}: keine Zwischenfarbe`);
    }
    type('#E63946', 140);
    assert.equal(p.search(), '?c=E63946');
    assert.notEqual(strip(), before, 'nach 120 ms und einem Frame neu gerechnet, nicht erst nach 250 ms');
    // Unbekanntes: Fehler nach 800 ms Pause, sofort beim Verlassen
    type('keine Farbe', 500);
    assert.equal(err.textContent, '');
    p.tick(400);
    assert.equal(err.textContent, i18n(p).errUnknown);
    type('keine Farbe!', 100);
    assert.equal(err.textContent, '', 'beim Weitertippen verschwindet der Fehler');
    p.input(seed, 'keine Farbe!');
    assert.equal(err.textContent, i18n(p).errUnknown, 'change zeigt den Fehler sofort');
    // Kurzform gilt nach der Pause
    type('#E63', 900);
    assert.equal(p.search(), '?c=EE6633');
  });

  test('Live-Meldungen: #pal-notes ohne aria-live und nur bei neuem Inhalt geschrieben, je Ergebnis eine Meldung', () => {
    const p = open(file('de/website'), 'c=E63946');
    const notes = p.$('#pal-notes');
    assert.equal(notes.hasAttribute('aria-live'), false);
    const writes = spy(notes, 'innerHTML'), said = spy(p.$('#status'), 'textContent');
    p.click('[data-ctl="m"] [data-val="light"]');
    p.click('[data-ctl="m"] [data-val="both"]');
    assert.equal(writes.length, 0, 'Ansichtswechsel schreibt den unveränderten Hinweis nicht neu');
    p.input('#seed', '#E63947');
    assert.equal(writes.length, 1);
    assert.equal(said.filter((s) => s).length, 1, said.join(' | '));
    // dieselbe Farbe noch einmal (change nach input): keine zweite Rechnung, keine zweite Meldung
    p.input('#seed', '#E63947');
    assert.equal(said.filter((s) => s).length, 1);
    const home = open(file('de'), '');
    const hs = spy(home.$('#status'), 'textContent');
    home.input('#seed', '#E63946', 'input'); home.input('#seed', '#E63946');
    assert.deepEqual(hs.filter((s) => s), [i18n(home).carried], 'Startseite meldet die mitgenommene Farbe einmal');
  });

  test('Zurücksetzen lässt den Fokus am Knopf', () => {
    const p = open(file('de/website'), 'c=E63946');
    const reset = p.$('[data-seed-reset]');
    reset.focus();
    p.click(reset);
    assert.equal(p.search(), '');
    assert.ok(p.doc.activeElement === reset, 'Fokus bleibt am Knopf, nicht im Textfeld (Tastatur auf dem Handy)');
  });

  test('Farbsteuerelemente: ungültige Eingabe mit Text und aria-invalid, leerer Wähler ohne Farbe', () => {
    const k = open(file('de/ki-bild'), '');
    const ins = k.$$('[data-ctl="f"] input'), er = k.$('#ctl-f-err');
    ins[0].value = '#1B3A76';
    k.input(ins[1], 'blaugrün');
    assert.deepEqual(ins.map((i) => i.getAttribute('aria-invalid')), [null, 'true', null, null]);
    assert.equal(er.textContent, i18n(k).errUnknown);
    assert.equal(k.search(), '');
    k.input(ins[1], '#D13B2F');
    assert.equal(er.textContent, '');
    assert.equal(k.search(), '?f=1B3A76,D13B2F');
    const m = open(file('de/marke'), '');
    const tx = m.$('#ctl-c2'), pk = m.$('[data-ctl="c2"] input[type="color"]'), e2 = m.$('#ctl-c2-err');
    assert.equal(pk.hasAttribute('data-empty'), true, 'leer: Wähler ohne Farbe');
    m.input(tx, 'zz');
    assert.deepEqual([tx.getAttribute('aria-invalid'), e2.textContent], ['true', i18n(m).errUnknown]);
    m.input(tx, '#E63946');
    assert.deepEqual([tx.getAttribute('aria-invalid'), e2.textContent, pk.hasAttribute('data-empty'), pk.value], [null, '', false, '#e63946']);
    m.input(tx, '');
    assert.equal(pk.hasAttribute('data-empty'), true, 'geleert: wieder ohne Farbe');
  });

  test('Bildteile b1–b3: höchstens 200 Zeichen, längerer Text verschwindet nicht still', () => {
    const p = open(file('en/ai-image'), '');
    const b1 = p.$('#ctl-b1');
    assert.equal(b1.getAttribute('maxlength'), '200');
    p.input(b1, 'Y'.repeat(201), 'input');
    assert.equal(p.search(), '', 'über 200 Zeichen: nichts übernommen');
    p.input(b1, 'Y'.repeat(200), 'input');
    assert.equal(p.search(), '?b1=' + 'Y'.repeat(200));
    assert.ok(p.$('#exp-prompt-0').textContent.includes('Y'.repeat(200)));
  });

  test('Nicht dekodierbare URL-Teile fallen aus der Adresszeile', () => {
    assert.equal(open(file('de/website'), 'c=%ZZ&m=dark').search(), '?m=dark');
    assert.equal(open(file('de/website'), '%ZZ=1').search(), '');
    assert.equal(open(file('de'), 'c=%ZZ').search(), '');
  });

  test('Palette prüfen: Live-Meldung mit Einzahl', () => {
    for (const [rel, n1] of [['de/pruefen', 'Palette geprüft: 1 Befund.'], ['en/check', 'Palette checked: 1 finding.']]) {
      const p = open(file(rel), '');
      p.$('#chk-input').value = '#777777 #FFFFFF';
      p.click('#chk-run');
      assert.equal(p.$('#status').textContent, n1);
    }
  });
}

