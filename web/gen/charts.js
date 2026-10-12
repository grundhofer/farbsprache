/* Generator der Aufgabe Diagramm oder Dashboard (FS.gen.charts). Spiegel von tools/gen/charts.py, gleiche
   Reihenfolge der Schritte, damit Hex exakt und Zahlen bis 1e-9 gleich sind (Paritätstest).
   Vertrag nach Spezifikation 7.4: build(task, inp, ctx) -> Palettenobjekt (6.14), dazu viewVars und exports.js. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.charts = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  var C = root.FS.color;
  function X() { return root.FS.export; }
  var BG = { light: '#FFFFFF', dark: '#16191D' };
  var TEXT = { light: '#222222', dark: '#E8E8E8' };
  var GRID_L = { light: 0.90, dark: 0.30 };
  var AXIS_L0 = { light: 0.45, dark: 0.75 };
  var CONTEXT_L0 = { light: 0.70, dark: 0.45 };
  var DIRECTION = { light: -1, dark: 1 };
  var OKABE_BLUE = '#0072B2';
  var MODE = 'default';
  var DEFAULT_FAM = { cat: 'okabe-ito', seq: 'viridis', div: 'blue-orange', hl: 'gray' };
  var CAT_FAM = { 'okabe-ito': ['okabe-ito', 'okabe-ito', ['black']], 'tol-bright': ['tol', 'bright', []], 'tol-muted': ['tol', 'muted', []] };
  var CB_FAM = { 'cb-blues': 'blues', 'cb-rdbu': 'rdbu', 'cb-puor': 'puor' };
  var DIV_HUES = [255.0, 50.0];
  // Feste Daten der Kachelkarte 7 × 5 (Muster), Werte 0 bis 99, für jede Palette gleich
  var TILE = [44, 62, 64, 57, 62, 83, 99, 44, 52, 45, 45, 62, 82, 86, 37, 33, 29, 41, 63, 73, 67,
    22, 15, 21, 42, 58, 56, 50, 2, 3, 21, 41, 44, 37, 40];

  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function isNum(h) { return typeof h === 'number' && h === h; }
  function usageOf(hx, bg) { var r = C.contrast(hx, bg); return r >= 4.5 ? 'text' : r >= 3.0 ? 'lines' : 'area'; }
  function isRed(h) { return isNum(h) && ((h >= 0 && h <= 45) || h >= 345); }
  function isGreen(h) { return isNum(h) && h >= 120 && h <= 160; }
  // Rot-Grün-Ablehnung (4.4): Gegenseite h_b durch 255° ersetzen → [h_b, ersetzt]
  function redGreen(ha, hb) {
    if ((isRed(ha) && isGreen(hb)) || (isGreen(ha) && isRed(hb))) { return [255.0, true]; }
    return [hb, false];
  }
  function toContrast(seed, bg, bgk, target) {
    target = target === undefined ? 3.0 : target;
    if (C.contrast(seed, bg) >= target && (bgk === 'light' || C.relLum(seed) > C.relLum(bg))) { return seed; }
    var lch = C.hexToOklch(seed), L = lch[0], Cs = lch[1], hue = isNum(lch[2]) ? lch[2] : 0.0, L0 = L, yb, steps;
    if (bgk === 'dark') {
      yb = C.relLum(bg);
      L0 = Math.max(L, C.hexToOklch(bg)[0]);
      steps = 0;
      while (C.relLum(C.oklchToHex(L0, Cs, hue)) <= yb && steps < 20) { L0 = Math.min(1.0, L0 + 0.05); steps++; }
    }
    return C.solveL(Cs, hue, [bg], target, DIRECTION[bgk], L0).hex;
  }
  function adjacent(colors, kinds) {
    var best = null, i, k, d;
    for (i = 0; i < colors.length - 1; i++) {
      for (k = 0; k < kinds.length; k++) {
        d = C.distance(colors[i], colors[i + 1], kinds[k]);
        if (best === null || d < best.value - 1e-12) { best = { value: d, i: i, kind: kinds[k] }; }
      }
    }
    return best;
  }
  function monotone(steps, kind) {
    var ls = [], i, up = true, down = true, m;
    for (i = 0; i < steps.length; i++) { ls.push(C.hexToOklch(steps[i])[0]); }
    if (kind === 'seq') {
      for (i = 0; i < ls.length - 1; i++) { if (!(ls[i] < ls[i + 1])) { up = false; } if (!(ls[i] > ls[i + 1])) { down = false; } }
      return up || down;
    }
    m = Math.floor(ls.length / 2);
    for (i = 0; i < m; i++) { if (!(ls[i] < ls[i + 1])) { return false; } }
    for (i = m; i < ls.length - 1; i++) { if (!(ls[i] > ls[i + 1])) { return false; } }
    return true;
  }
  function scheme(ds, sid) { for (var i = 0; i < ds.schemes.length; i++) { if (ds.schemes[i].id === sid) { return ds.schemes[i]; } } return null; }

  // ---------- Datentypen
  function cat(o, seed, bg, bgk, kinds, ctx, changes, summary) {
    var f = CAT_FAM[o.fam], cols = scheme(ctx.datasets[f[0]], f[1]).colors, fam = [], pool = [], i, start = null, roles = {};
    for (i = 0; i < cols.length; i++) { if (f[2].indexOf(cols[i].name) < 0) { fam.push(cols[i].hex); } }
    var lines = o.mark === 'lines';
    for (i = 0; i < fam.length; i++) { if (!lines || C.contrast(fam[i], bg) >= 3.0) { pool.push(fam[i]); } }
    if (seed) {
      start = seed;
      if (lines) {
        start = toContrast(seed, bg, bgk);
        if (start !== seed) {
          changes.push({ role: 'series-1', mode: MODE, from: seed, to: start, key: 'series-1',
            values: { before: C.contrast(seed, bg), after: C.contrast(start, bg) } });
        }
      }
    }
    var chosen = C.pickDistinct(pool, o.n, kinds, start, bg);
    if (chosen.length < o.n) { summary.push(lines ? 'summary.pool' : 'summary.pool-areas'); }
    for (i = 0; i < chosen.length; i++) { roles['series-' + (i + 1)] = chosen[i]; }
    return [roles, chosen.length > (start ? 1 : 0) ? [f[0]] : []];
  }
  function seq(o, seed, bgk, ctx, summary) {
    var fam = o.fam, n = o.n, steps = [], used = [], i, table, cls, lch, gray, t, c;
    if (fam === 'seed' && !seed) { summary.push('summary.seed-missing'); fam = DEFAULT_FAM.seq; }
    else if (fam !== 'seed' && seed) { summary.push('summary.seed-unused'); }
    if (fam === 'viridis') {
      table = scheme(ctx.datasets.viridis, 'viridis').colors;
      for (i = 0; i < n; i++) { steps.push(table[Math.floor((2 * i * 255 + (n - 1)) / (2 * (n - 1)))].hex); }
      if (bgk === 'light') { steps.reverse(); }
      used = ['viridis'];
    } else if (fam === 'cb-blues') {
      cls = scheme(ctx.datasets.colorbrewer, 'blues').classes[String(n)];
      for (i = 0; i < cls.length; i++) { steps.push(cls[i].hex); }
      if (bgk === 'dark') { steps.reverse(); }
      used = ['colorbrewer'];
    } else {
      lch = C.hexToOklch(seed);
      gray = !isNum(lch[2]);
      if (gray) { summary.push('summary.seed-gray'); }
      for (i = 0; i < n; i++) {
        t = i / (n - 1);
        c = gray ? 0.0 : 0.02 + 0.10 * Math.sin(Math.PI * Math.min(1.0, 1.1 * t));
        steps.push(C.oklchToHex(0.96 - 0.64 * t, c, gray ? 0.0 : lch[2]));
      }
      if (bgk === 'dark') { steps.reverse(); }
    }
    return [steps, used];
  }
  function div(o, seed, ctx, changes, summary) {
    var fam = o.fam, n = o.n, steps = [], i, cls, ha = DIV_HUES[0], hb = DIV_HUES[1], hs, rg, before, u, a, hue;
    if (fam === 'seed' && !seed) { summary.push('summary.seed-missing'); fam = DEFAULT_FAM.div; }
    else if (fam !== 'seed' && seed) { summary.push('summary.seed-unused'); }
    if (has(CB_FAM, fam)) {
      cls = scheme(ctx.datasets.colorbrewer, CB_FAM[fam]).classes[String(n)];
      for (i = 0; i < cls.length; i++) { steps.push(cls[i].hex); }
      steps.reverse(); // kühle Seite zuerst: Stufe 1 = weit unter dem Mittelwert
      return [steps, ['colorbrewer']];
    }
    if (fam === 'seed') {
      hs = C.hexToOklch(seed)[2];
      if (!isNum(hs)) { summary.push('summary.seed-gray-div'); }
      else {
        ha = hs; hb = (hs + 180.0) % 360.0;
        rg = redGreen(ha, hb);
        if (rg[1]) {
          before = C.oklchToHex(0.97 - 0.55, 0.13, hb);
          hb = rg[0];
          changes.push({ role: 'step-' + n, mode: MODE, from: before, to: C.oklchToHex(0.97 - 0.55, 0.13, hb),
            key: 'red-green', values: { hue_from: (hs + 180.0) % 360.0, hue_to: hb } });
        }
      }
    }
    for (i = 0; i < n; i++) {
      u = (2 * i - (n - 1)) / (n - 1);
      a = Math.abs(u);
      hue = u < 0 ? ha : u > 0 ? hb : 0.0;
      steps.push(C.oklchToHex(0.97 - 0.55 * a, 0.13 * a, hue));
    }
    return [steps, []];
  }

  // ---------- Generator
  function build(task, inp, ctx) {
    var o = inp.options, t = o.t, bgk = o.bg, seed = inp.seed || null, bg = BG[bgk], roles = {};
    var changes = [], findings = [], summary = [], distinct = [], used = [], data = [], kinds = C.WORST_KINDS.slice(), i, k, res, steps;
    if (o.pr) { kinds.push('gray'); }
    if (t === 'cat') {
      res = cat(o, seed, bg, bgk, kinds, ctx, changes, summary);
      for (k in res[0]) { if (has(res[0], k)) { roles[k] = res[0][k]; data.push(k); } }
      used = res[1];
      summary.unshift(o.pr ? 'summary.cat-pr' : 'summary.cat');
    } else if (t === 'seq' || t === 'div') {
      res = t === 'seq' ? seq(o, seed, bgk, ctx, summary) : div(o, seed, ctx, changes, summary);
      steps = res[0]; used = res[1];
      for (i = 0; i < steps.length; i++) { roles['step-' + (i + 1)] = steps[i]; data.push('step-' + (i + 1)); }
      summary.unshift('summary.' + t + (t === 'seq' && bgk === 'dark' ? '-dark' : ''));
      if (!monotone(steps, t)) { findings.push({ id: 'not-monotone', mode: null, severity: 'note', values: {} }); }
    } else {
      var context = C.solveL(0.0, 0.0, [bg], 3.0, DIRECTION[bgk], CONTEXT_L0[bgk]).hex, hi;
      roles.highlight = OKABE_BLUE;
      used = ['okabe-ito'];
      if (seed) {
        hi = toContrast(seed, bg, bgk);
        // Fällt die eigene Farbe auf 3:1 praktisch mit dem Kontextgrau zusammen, bleibt Okabe-Blau (mit Hinweis)
        if (C.worstDistance(hi, context, C.WORST_KINDS) < C.JND_DISTANCE) {
          changes.push({ role: 'highlight', mode: MODE, from: seed, to: OKABE_BLUE, key: 'highlight-gray',
            values: { distance: C.worstDistance(hi, context, C.WORST_KINDS) } });
        } else {
          used = [];
          roles.highlight = hi;
          if (hi !== seed) {
            changes.push({ role: 'highlight', mode: MODE, from: seed, to: hi, key: 'highlight',
              values: { before: C.contrast(seed, bg), after: C.contrast(hi, bg) } });
          }
        }
      }
      roles.context = context;
      data = ['highlight', 'context'];
      summary.unshift('summary.hl');
    }
    roles.bg = bg;
    roles.text = TEXT[bgk];
    roles['text-2'] = C.solveL(0.0, 0.0, [bg], 4.5, DIRECTION[bgk], AXIS_L0[bgk]).hex;
    roles.grid = C.oklchToHex(GRID_L[bgk], 0.0, 0.0);
    var rbm = {}; rbm[MODE] = roles;

    // Paare: Linien (cat lines, hl) normativ 3:1; Flächen (cat areas, seq, div) nur als Hinweis (4.4)
    var t2 = {}, p, pairs = [], adv = (task.advisory || []).slice();
    for (k in task) { if (has(task, k)) { t2[k] = task[k]; } }
    if (t === 'cat' && o.mark === 'areas') {
      for (i = 0; i < task.pairs.length; i++) {
        p = task.pairs[i];
        if (p.fg.indexOf('series-') === 0) { adv.push({ fg: p.fg, on: p.on, min: p.min, finding: 'low-contrast' }); } else { pairs.push(p); }
      }
      t2.pairs = pairs; t2.advisory = adv;
    }
    var ev = C.evaluate(t2, rbm, 'skip'), low = null;
    for (i = 0; i < ev.advisory.length; i++) {
      if (!ev.advisory[i].pass) { low = low === null ? ev.advisory[i].ratio : Math.min(low, ev.advisory[i].ratio); }
    }
    if (low !== null) { findings.unshift({ id: 'low-contrast', mode: null, severity: 'note', values: { ratio: low } }); }

    // Abstände (4.1.8): schlechtester Fall normal, Deuteranopie, Protanopie; bei pr zusätzlich Graustufen getrennt
    var cols = [], groups, g, a, md, base;
    for (i = 0; i < data.length; i++) { cols.push(roles[data[i]]); }
    if (t === 'seq' || t === 'div') {
      groups = [['steps', C.WORST_KINDS.slice()]];
      if (o.pr) { groups.push(['steps-gray', ['gray']]); }
      for (g = 0; g < groups.length; g++) {
        a = adjacent(cols, groups[g][1]);
        if (a) { distinct.push({ id: groups[g][0], mode: MODE, value: a.value, a: data[a.i], b: data[a.i + 1], kind: a.kind }); }
      }
    } else {
      base = t === 'cat' ? 'series' : 'highlight';
      groups = [[base, C.WORST_KINDS.slice()]];
      if (o.pr) { groups.push([base + '-gray', ['gray']]); }
      for (g = 0; g < groups.length; g++) {
        md = C.minDistance(cols, groups[g][1]);
        if (md) { distinct.push({ id: groups[g][0], mode: MODE, value: md.value, a: data[md.i], b: data[md.j], kind: md.kind }); }
      }
    }
    for (i = 0; i < distinct.length; i++) {
      if (distinct[i].value < C.JND_DISTANCE) { findings.push({ id: 'near-jnd', mode: null, severity: 'note', values: {} }); break; }
    }
    var usage = {}; usage[MODE] = {};
    for (i = 0; i < data.length; i++) { usage[MODE][data[i]] = usageOf(roles[data[i]], bg); }
    // advisory: Datenfarben ohne Normpaar (Stufen, Flächen) mit Wert; der Rahmen zeigt sie in Block C und F (3.3)
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: rbm, pairs: ev.pairs, decorative: ev.decorative,
      advisory: ev.advisory, distinct: distinct, changes: changes, findings: findings, usage: usage,
      extra: { datasets: used, summary: summary } };
  }

  // ---------- Name eines eigenen Zustands ohne eigene Farbe (nach Z geändert, 5.0): Familie, Anzahl, Darstellung,
  // Hintergrund, wie die Palette sie zeigt; fam „seed“ ohne eigene Farbe fällt wie im Generator auf die Standardfamilie
  function displayName(palette, text, lang) {
    var o = palette.input.options, t = o.t, fam = o.fam === 'seed' && !palette.input.seed ? DEFAULT_FAM[t] : o.fam, r = palette.roles[MODE], n = 0, k;
    for (k in r) { if (has(r, k) && k.indexOf(t === 'cat' ? 'series-' : 'step-') === 0) { n++; } }
    return text[t === 'hl' ? 'name.hl' : t === 'cat' ? 'name.cat' + (n === 1 ? '_1' : '') : 'name.steps'].split('{fam}').join(text['name.fam.' + fam])
      .split('{n}').join(C.fmtCount(n, lang)).split('{mark}').join(text['name.mark.' + o.mark]).split('{bg}').join(text['name.bg.' + o.bg]);
  }

  // ---------- Anzeige des Musters
  function viewVars(palette, mode, toggles) {
    var o = palette.input.options, t = o.t, r = palette.roles[mode], u = (palette.usage || {})[mode] || {}, v = {}, k, n = 0, i, s;
    v.scheme = o.bg === 'dark' ? 'dark' : 'light';
    v['v-lines'] = t === 'hl' || (t === 'cat' && o.mark === 'lines') ? 'block' : 'none';
    v['v-bars'] = t === 'cat' ? 'block' : 'none';
    v['v-tiles'] = t === 'seq' || t === 'div' ? 'block' : 'none';
    v['v-cat'] = t === 'cat' ? 'flex' : 'none';
    v['v-hl'] = t === 'hl' ? 'flex' : 'none';
    v['v-seq'] = t === 'seq' ? 'flex' : 'none';
    v['v-div'] = t === 'div' ? 'flex' : 'none';
    for (k = 1; k <= 8; k++) {
      v['s' + k] = has(r, 'series-' + k) ? 'flex' : 'none';
      v['e' + k] = u['series-' + k] === 'area' ? r.text : 'transparent';
    }
    for (k in r) { if (has(r, k) && k.indexOf('step-') === 0) { n++; } }
    for (k = 1; k <= 9; k++) {
      v['t' + k] = k <= n ? 'flex' : 'none';
      v['f' + k] = u['step-' + k] === 'area' ? r.text : 'transparent';
    }
    if (n) {
      for (i = 0; i < TILE.length; i++) {
        s = Math.floor(TILE[i] * n / 100) + 1;
        v['c' + (i + 1)] = r['step-' + s];
        v['k' + (i + 1)] = v['f' + s];
      }
    }
    return v;
  }

  // ---------- JS-Array (5.8)
  function jsArray(palette, task, ctx, lang, opts) {
    var o = palette.input.options, t = o.t, r = palette.roles[MODE], text = ctx.text, rids = [], k, i, lines = [], low = [], nn, vals = [];
    var pre = { cat: 'series-', seq: 'step-', div: 'step-' };
    if (t === 'hl') { rids = ['highlight', 'context']; } else {
      for (k in r) { if (has(r, k) && k.indexOf(pre[t]) === 0) { rids.push(k); } }
      rids.sort(function (a, b) { return parseInt(a.split('-').pop(), 10) - parseInt(b.split('-').pop(), 10); });
    }
    lines.push('// ' + X().presub(text['js.head'].split('{type}').join(text['ctl.t.' + t]), ctx));
    nn = X().notices(palette, ctx, task, opts);
    for (i = 0; i < nn.length; i++) { lines.push('// ' + nn[i]); }
    lines.push('// ' + text['js.order.' + t + (t === 'cat' && o.pr ? '-pr' : '')]);
    var us = (palette.usage || {})[MODE] || {};
    for (i = 0; i < rids.length; i++) { if (us[rids[i]] === 'area') { low.push(r[rids[i]]); } }
    if (low.length) { lines.push('// ' + text['js.low'].split('{text}').join(r.text).split('{list}').join(low.join(', '))); }
    for (i = 0; i < rids.length; i++) { vals.push('"' + r[rids[i]] + '"'); }
    lines.push('const chartColors = [' + vals.join(', ') + '];');
    lines.push('// ' + X().presub(ctx.core.link, ctx));
    return lines.join('\n');
  }

  // ---------- Zweck der Datenfarben unter 3:1 (4.4): „nur Flächen mit Kontur“ statt „Linien, Punkte, Balken“
  function areaTask(palette, task, ctx, lang) {
    var u = (palette.usage || {})[MODE] || {}, t = {}, k, i, r, c, roles = [];
    for (k in task) { if (has(task, k)) { t[k] = task[k]; } }
    for (i = 0; i < task.roles.length; i++) {
      r = task.roles[i];
      if (u[r.id] === 'area' && r.id.indexOf('series-') === 0) {
        c = {};
        for (k in r) { if (has(r, k)) { c[k] = r[k]; } }
        c['use_' + lang] = ctx.text['use.area'].split('{text}').join(palette.roles[MODE].text);
        r = c;
      }
      roles.push(r);
    }
    t.roles = roles;
    return t;
  }
  function withArea(fmt) { return function (palette, task, ctx, lang, opts) { return X()[fmt](palette, areaTask(palette, task, ctx, lang), ctx, lang, opts); }; }

  return { build: build, viewVars: viewVars, displayName: displayName, redGreen: redGreen, TILE: TILE,
    exports: { js: jsArray, hex: withArea('hex'), css: withArea('css'), dtcg: withArea('dtcg'), agent: withArea('agent') } };
}));
