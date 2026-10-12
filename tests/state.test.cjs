'use strict';
// URL-Zustand (Spezifikation 2.3, 7.9): je Aufgabe Rundlauf URL → Zustand → URL, Sprachlink mit allen
// Parametern, c schlägt p, ungültige Werte fallen weg, farbsprache.color wird nie automatisch angewandt,
// gesperrter Speicher wirft nicht. Die Aufgaben kommen aus den gebauten Seiten (#task-data).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { ROOT } = require('./helpers.cjs');

const REQUIRE = process.env.FARBSPRACHE_REQUIRE_BUILD === '1';
const SITES = [path.join(ROOT, 'docs'), path.join(ROOT, 'tests', 'out', 'fixtures', 'docs')];

function pages() {
  const out = [];
  for (const dir of SITES) {
    const base = path.join(dir, 'de');
    if (!fs.existsSync(base)) continue;
    for (const seg of fs.readdirSync(base)) {
      const f = path.join(base, seg, 'index.html');
      if (fs.existsSync(f) && fs.readFileSync(f, 'utf8').includes('id="task-data"')) out.push(f);
    }
  }
  return out;
}
function load(file) {
  const html = fs.readFileSync(file, 'utf8');
  const data = JSON.parse(html.match(/<script type="application\/json" id="task-data">([\s\S]*?)<\/script>/)[1].replace(/<\\\//g, '</'));
  const ctx = {};
  vm.createContext(ctx);
  const re = /<script src="([^"?]+)\?v=[^"]*" defer><\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (/\/ui\//.test(m[1])) continue;
    const f = path.resolve(path.dirname(file), m[1]);
    vm.runInContext(fs.readFileSync(f, 'utf8'), ctx, { filename: f });
  }
  return { data, S: ctx.FS.site, C: ctx.FS.color, gen: ctx.FS.gen[data.task.id] || ctx.FS.gen[data.gen] };
}
const plain = (x) => JSON.parse(JSON.stringify(x));

// Gültige Nicht-Standardwerte je Steuerelement (für den Rundlauf)
function samples(task, S) {
  const base = S.state.base(task, task.presets[0].id);
  const out = [];
  for (const ctl of task.controls) {
    const cand = [];
    if (ctl.type === 'chips') {
      const vals = new Set(ctl.values || []);
      for (const cs of Object.values(ctl.cases || {})) for (const v of cs.values || []) vals.add(v);
      cand.push(...vals);
    } else if (ctl.type === 'toggle') cand.push(true, false);
    else if (ctl.type === 'stepper') {
      const lo = Math.min(ctl.min, ...Object.values(ctl.cases || {}).map((c) => c.min ?? ctl.min));
      const hi = Math.max(ctl.max, ...Object.values(ctl.cases || {}).map((c) => c.max ?? ctl.max));
      for (let v = lo; v <= hi; v += ctl.step || 1) cand.push(v);
    } else if (ctl.type === 'color') cand.push('#123456', '#E63946');
    else if (ctl.type === 'colors') cand.push(['#123456', '#FEDCBA'], ['#000000', '#FFFFFF', '#E63946']);
    else if (ctl.type === 'text') cand.push('Text mit Leerzeichen, Komma & Zeichen');
    for (const v of cand) if (JSON.stringify(v) !== JSON.stringify(base[ctl.id])) out.push([ctl.id, v]);
  }
  return out;
}

test('Aufgabenseiten liegen vor', (t) => {
  if (!pages().length) { if (REQUIRE) assert.fail('keine gebaute Aufgabenseite – erst python3 build.py --fixtures'); t.skip('nicht gebaut'); }
});

for (const file of pages()) {
  const rel = path.relative(ROOT, file);
  const { data, S, C, gen } = load(file);
  const task = data.task;
  const sp = S.state.seedParam(task);

  test(`Rundlauf URL → Zustand → URL: ${rel}`, () => {
    let n = 0, clean = 0;
    const presets = [null].concat(task.presets.map((p) => p.id));
    for (const p of presets) {
      for (const c of [null, '#E63946']) {
        for (const [id, v] of [[null, null]].concat(samples(task, S))) {
          const st = { c, p, o: {}, t: {} };
          if (id) st.o[id] = v;
          const q = S.state.write(task, st);
          const back = S.state.read(task, q);
          // preset_control ohne c: Ein Wert, den die Startpalette nicht hat, wählt seine Startpalette (2.3, wie beim Klick).
          // Das Ergebnis ist genau bekannt: p der Startpalette dieses Werts, der Wert selbst fällt als Standard weg.
          const pc = task.preset_control, to = pc && !c && id === pc ? task.presets.find((x) => x.options[pc] === v) : null;
          if (to && task.presets.find((x) => x.id === (p || task.presets[0].id)).options[pc] !== v) {
            assert.equal(back.dirty, true, `${q}: Umschalten bereinigt die URL`);
            assert.equal(S.state.write(task, back.state), S.state.write(task, { c: null, p: to.id, o: {}, t: {} }), `${q}: Startpalette ${to.id}`);
            clean++;
            n++;
            continue;
          }
          // kanonisch: Werte, die der Startpalette entsprechen oder ungültig sind, fallen weg
          const again = S.state.write(task, back.state);
          assert.equal(S.state.write(task, S.state.read(task, again).state), again, `instabil: ${q}`);
          if (!back.dirty) {
            clean++;
            assert.equal(again, q, `Rundlauf ${q}`);
            assert.deepEqual(plain(back.state), plain(st), `Zustand ${q}`);
          }
          n++;
        }
      }
    }
    for (const tg of task.pattern_toggles || []) {
      for (const v of tg.values) {
        if (v === tg.default) continue;
        const st = { c: null, p: null, o: {}, t: { [tg.id]: v } };
        const q = S.state.write(task, st);
        assert.deepEqual(plain(S.state.read(task, q).state), plain(st), `Muster-Schalter ${q}`);
        n++;
      }
    }
    assert.ok(n > task.presets.length, 'zu wenige Fälle');
    // Bereinigt werden nur Werte, die der gewählten Startpalette entsprechen; die meisten Fälle sind kanonisch
    assert.ok(clean >= n / 2, `nur ${clean} von ${n} Fällen kanonisch`);
  });

  if (task.controls.some((c) => c.type === 'colors')) {
    test(`Farbliste f steht kommagetrennt in der URL, ohne %2C (2.3, T-19): ${rel}`, () => {
      const ctl = task.controls.find((c) => c.type === 'colors');
      const q = S.state.write(task, { c: null, p: null, o: { [ctl.id]: ['#1B3A76', '#F6F3ED', '#D13B2F'] }, t: {} });
      assert.equal(q, ctl.id + '=1B3A76,F6F3ED,D13B2F');
      assert.deepEqual(plain(S.state.read(task, q).state.o[ctl.id]), ['#1B3A76', '#F6F3ED', '#D13B2F']);
      assert.deepEqual(plain(S.state.read(task, ctl.id + '=1B3A76%2CF6F3ED').state.o[ctl.id]), ['#1B3A76', '#F6F3ED'], 'alte Links gelten weiter');
    });
  }

  test(`Ungültige Werte fallen weg, ohne Fehlermeldung: ${rel}`, () => {
    const q = `${sp}=nichtfarbe&p=gibtsnicht&zz=1&${task.controls.map((c) => c.id + '=%%%').join('&')}`;
    const r = S.state.read(task, q);
    assert.equal(r.dirty, true);
    assert.equal(r.state.c, null);
    assert.equal(r.state.p, null);
    assert.deepEqual(plain(r.state.o), {});
    assert.equal(S.state.write(task, r.state), '');
    // Nicht dekodierbare Teile fallen weg und die URL wird bereinigt (T-13), gültige Teile bleiben
    for (const bad of [`${sp}=%ZZ`, '%ZZ=1', `${sp}=%E0%A4%A`]) {
      const b = S.state.read(task, bad + '&p=' + task.presets[task.presets.length - 1].id);
      assert.equal(b.dirty, true, bad);
      assert.equal(S.state.write(task, b.state), task.presets.length > 1 ? 'p=' + task.presets[task.presets.length - 1].id : '', bad);
    }
    // Doppelte Parameter: der erste zählt, die URL wird bereinigt
    const d = S.state.read(task, `${sp}=E63946&${sp}=000000`);
    assert.equal(d.state.c, '#E63946');
    assert.equal(d.dirty, true);
  });

  test(`c schlägt p, Zurücksetzen kehrt zu p zurück: ${rel}`, () => {
    const second = task.presets[1].id;
    const r = S.state.read(task, `${sp}=E63946&p=${second}`);
    assert.equal(r.state.c, '#E63946');
    assert.equal(r.state.p, second);
    assert.equal(S.state.isCustom(task, r.state), true);
    const out = S.compute(data, r.state, gen, data.lang);
    assert.equal(out.custom, true);
    if (out.palette) {
      assert.equal(out.palette.preset, null, 'mit eigener Farbe ist keine Startpalette gewählt');
      assert.equal(out.palette.input.seed, '#E63946');
    }
    // „Zurücksetzen“ entfernt c: es bleibt die gewählte Startpalette, fertig aus dem Build
    const reset = { c: null, p: second, o: {}, t: {} };
    const shown = S.compute(data, reset, gen, data.lang);
    assert.equal(shown.custom, false);
    assert.equal(shown.palette, data.palettes[second]);
    // ohne p: die erste Startpalette
    assert.equal(S.compute(data, { c: null, p: null, o: {}, t: {} }, gen, data.lang).palette, data.palettes[data.first]);
  });

  test(`Sprachlink trägt alle Parameter, Weiter-Links nur c: ${rel}`, () => {
    const st = { c: '#E63946', p: task.presets[1].id, o: {}, t: {} };
    for (const [id, v] of samples(task, S).slice(0, 3)) st.o[id] = v;
    const q = S.state.write(task, st);
    const href = S.langHref('../../en/x/', q, '#kopieren');
    assert.equal(href, '../../en/x/?' + q + '#kopieren');
    for (const part of q.split('&')) assert.ok(href.includes(part), part);
    assert.equal(S.carryHref('../status/', '#E63946'), '../status/?c=E63946');
    assert.equal(S.carryHref('../status/', null), '../status/');
  });

  test(`farbsprache.color wird nie automatisch angewandt, gesperrter Speicher wirft nicht: ${rel}`, () => {
    const mem = new Map([['farbsprache.color', '#E63946']]);
    let writes = 0;
    const win = { localStorage: { getItem: (k) => (mem.has(k) ? mem.get(k) : null), setItem: (k, v) => { writes++; mem.set(k, v); }, removeItem: (k) => mem.delete(k) } };
    const store = S.storage(win);
    const r = S.state.read(task, '');
    assert.equal(r.state.c, null, 'ohne c in der URL bleibt die Farbe leer');
    assert.equal(S.suggestion(store, r.state.c), '#E63946', 'nur als Vorschlag');
    assert.equal(S.suggestion(store, '#000000'), null, 'mit eigener Farbe kein Vorschlag');
    assert.equal(S.compute(data, r.state, gen, data.lang).custom, false);
    assert.equal(writes, 0);
    const blocked = { get localStorage() { throw new Error('blocked'); } };
    const bs = S.storage(blocked);
    assert.doesNotThrow(() => { bs.get('farbsprache.color'); bs.set('farbsprache.color', '#000000'); });
    assert.equal(bs.get('x'), null);
    assert.equal(S.suggestion(bs, null), null);
    const throwing = { localStorage: { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); }, removeItem() { throw new Error('x'); } } };
    assert.equal(S.storage(throwing).set('a', 'b'), false);
  });

  // Eigenes ist nie die Startpalette (5.0, 5.4): preset null, Name „{Startpalette}, angepasst“ bei geänderten Optionen,
  // „Eigene Farbe“ mit c, „Eigene Farben“ mit einem colors-Steuerelement; der Link im Export trägt kein erzwungenes p.
  test(`Eigene Zustände: Name, preset null und Link ohne Startpalette: ${rel}`, () => {
    const pr = task.presets[1] || task.presets[0];
    const cases = [[{ c: '#E63946', p: pr.id, o: {}, t: {} }, (l) => data.custom_names[l]]];
    for (const [id, v] of samples(task, S)) {
      const ctl = task.controls.find((x) => x.id === id);
      if (id === 'm' || ctl.view || id === task.seed_control || id === task.preset_control) continue;
      const st = { c: null, p: pr.id, o: { [id]: v }, t: {} };
      // Mit Namenshaken (gen.displayName, nach Z geändert) steht statt der Startpalette, was die Palette zeigt
      cases.push([st, ctl.type === 'colors' ? (l) => data.custom_names_colors[l] : (l, pal) => data.adjusted_names[l].replace('{palette}',
        data.name_text ? gen.displayName(pal, data.name_text[l], l) : pr['name_' + l])]);
    }
    let adjusted = 0;
    for (const [st0, name] of cases) {
      const st = S.state.read(task, S.state.write(task, st0)).state;
      if (!S.state.isCustom(task, st)) continue; // Wert entspricht der Startpalette oder gilt dort nicht
      const out = S.compute(data, st, gen, data.lang);
      if (out.error) continue;
      assert.equal(out.palette.preset, null, `${S.state.write(task, st)}: preset`);
      for (const l of ['de', 'en']) assert.equal(out.palette['name_' + l], name(l, out.palette), `${S.state.write(task, st)}: Name ${l}`);
      const ectx = S.render.exportCtx(data, out.palette, st, true);
      assert.equal(ectx.name, name(data.lang, out.palette));
      const wantP = st.p && !S.state.colorsSet(task, st);
      assert.equal(/[?&]p=/.test(ectx.url), !!wantP, `Link ${ectx.url}`);
      if (!st.c) adjusted++;
    }
    assert.ok(adjusted > 0, 'kein eigener Zustand ohne c ließ sich rechnen');
  });

  if (sp !== 'c') {
    test(`c gilt als Ersatz für den seed_param ${sp} (Weiter-Links und Kacheln tragen c): ${rel}`, () => {
      const r = S.state.read(task, 'c=E63946');
      assert.equal(r.state.c, '#E63946');
      assert.equal(r.dirty, true, 'die URL schreibt danach den seed_param');
      assert.equal(S.state.write(task, r.state), sp + '=E63946');
      assert.equal(S.state.read(task, `c=000000&${sp}=E63946`).state.c, '#E63946', 'der seed_param geht vor');
      assert.equal(S.state.read(task, 'c=nichtfarbe').state.c, null);
    });
  }

  if (task.preset_control) {
    test(`preset_control ${task.preset_control}: Optionen, die die neue Startpalette nicht festlegt, bleiben: ${rel}`, () => {
      const pc = task.preset_control;
      let kept = 0;
      for (const from of task.presets) {
        for (const to of task.presets) {
          if (to === from) continue;
          const st = { c: null, p: from.id, o: {}, t: {} };
          for (const [id, v] of samples(task, S)) if (id !== pc && !(id in st.o)) st.o[id] = v;
          const start = S.state.read(task, S.state.write(task, st)).state;
          const before = plain(start.o);
          S.state.option(task, start, pc, to.options[pc], data.first);
          assert.equal(start.p, to.id);
          assert.ok(!(pc in start.o));
          for (const k of Object.keys(start.o)) {
            assert.ok(!(k in to.options), `${k} legt ${to.id} selbst fest`);
            assert.deepEqual(plain(start.o[k]), before[k], `${k} unverändert übernommen`);
            kept++;
          }
          // was nicht festgelegt, gültig und kein Standard der neuen Startpalette ist, bleibt
          const again = S.state.read(task, S.state.write(task, { c: null, p: to.id, o: Object.fromEntries(Object.entries(before).filter(([k]) => !(k in to.options))), t: {} })).state;
          assert.deepEqual(plain(start.o), plain(again.o), `${from.id} → ${to.id}`);
        }
      }
      assert.ok(kept > 0, 'keine Option blieb erhalten');
    });
  }

  test(`Eigene Farbe rechnet über den Generator, Ergebnis wie das Palettenobjekt verlangt: ${rel}`, () => {
    // Eine Farbe darf für eine Aufgabe unlösbar sein (SolveError, etwa Weiß auf #E63946 beim Schleier);
    // dann zeigt die Seite die Meldung solve.<key>. Mindestens eine dieser Farben muss rechnen.
    let ok = 0;
    for (const c of ['#E63946', '#11697A', '#000000', '#FFFFFF']) {
      const out = S.compute(data, { c, p: null, o: {}, t: {} }, gen, data.lang);
      if (out.error) {
        assert.notEqual(out.error, 'error', `${c}: der Generator bricht ohne SolveError ab`);
        assert.ok(('solve.' + out.error) in data.frame || ('solve.' + out.error) in data.text, `Text solve.${out.error} fehlt`);
        continue;
      }
      ok++;
      const pal = out.palette;
      for (const k of ['task', 'preset', 'input', 'name_de', 'name_en', 'modes', 'roles', 'pairs', 'decorative', 'distinct', 'changes', 'findings', 'usage', 'extra']) {
        assert.ok(k in pal, 'Feld ' + k);
      }
      assert.equal(pal.name_de, data.custom_names.de);
      for (const p of pal.pairs) assert.ok(Math.abs(C.contrast(pal.roles[p.mode][p.fg], pal.roles[p.mode][p.bg]) - p.ratio) < 1e-12);
    }
    assert.ok(ok > 0, 'keine der Testfarben ließ sich rechnen');
  });
}
