/* Generator der Testaufgabe (FS.gen.fixture). Spiegel von tests/fixtures/tools/gen/fixture.py.
   Vertrag: build(task, inp, ctx) -> Palettenobjekt. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.fixture = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  var C = root.FS.color;

  function neutrals(h, t) {
    var light = { bg: C.oklchToHex(0.985, 0.4 * t, h), surface: '#FFFFFF', text: C.oklchToHex(0.24, 1.6 * t, h), border: C.oklchToHex(0.88, t, h) };
    light['text-muted'] = C.solveL(1.4 * t, h, [light.bg, light.surface], 4.95, -1, 0.60).hex;
    var dark = { bg: C.oklchToHex(0.19, t, h), surface: C.oklchToHex(0.23, t, h), text: C.oklchToHex(0.94, 0.6 * t, h), border: C.oklchToHex(0.34, t, h) };
    dark['text-muted'] = C.solveL(t, h, [dark.bg, dark.surface], 4.95, 1, 0.60).hex;
    return [light, dark];
  }

  function accent(cand, L, Cc, h, labels, mode, changes) {
    var best = -1, label = null, i, r;
    for (i = 0; i < labels.length; i++) {
      r = C.contrast(labels[i], cand);
      if (r > best) { best = r; label = labels[i]; }
    }
    if (best >= 4.5) { return [cand, label]; }
    var lightLabel = C.relLum(labels[0]) >= C.relLum(labels[1]) ? labels[0] : labels[1];
    var res = C.solveL(Cc, h, [lightLabel], 4.5, -1, L);
    changes.push({ role: 'accent', mode: mode, from: cand, to: res.hex, key: 'accent-darker',
      values: { before: C.contrast(lightLabel, cand), after: res.ratio } });
    return [res.hex, lightLabel];
  }

  function build(task, inp, ctx) {
    var o = inp.options, lch = C.hexToOklch(inp.seed), L = lch[0], Cs = lch[1], h = lch[2];
    if (h !== h || h === null) { h = 0; }
    var t = o.tone === 'neutral' ? 0 : Math.min(Math.max(0.1 * Cs, 0.004), 0.012);
    var n = neutrals(h, t), light = n[0], dark = n[1], changes = [], findings = [], a, i, mode, r;
    a = accent(inp.seed, L, Cs, h, [o.tc, light.text], 'light', changes);
    light.accent = a[0]; light['on-accent'] = a[1];
    light['accent-text'] = C.solveL(Cs, h, [light.bg, light.surface], 4.5, -1, L).hex;
    var cand = C.oklchToHex(L, 0.85 * Cs, h);
    a = accent(cand, L, 0.85 * Cs, h, [dark.text, dark.bg], 'dark', changes);
    dark.accent = a[0]; dark['on-accent'] = a[1];
    dark['accent-text'] = C.solveL(0.85 * Cs, h, [dark.bg, dark.surface], 4.5, 1, L).hex;
    var raw = { light: [], dark: [] }, hue;
    for (i = 0; i < o.k; i++) {
      hue = (h + i * 120) % 360;
      light['step-' + (i + 1)] = C.solveL(Cs, hue, [light.bg], 3.3, -1, 0.62).hex;
      dark['step-' + (i + 1)] = C.solveL(0.85 * Cs, hue, [dark.bg], 3.3, 1, 0.62).hex;
      raw.light.push(C.oklchToHex(0.62, Cs, hue));
      raw.dark.push(C.oklchToHex(0.62, 0.85 * Cs, hue));
    }
    var okabe = [], cols = ctx.datasets['okabe-ito'].schemes[0].colors;
    for (i = 0; i < cols.length; i++) { if (cols[i].name !== 'black') { okabe.push(cols[i].hex); } }
    var pairs = [['light', light], ['dark', dark]], j, pool;
    for (j = 0; j < 2; j++) {
      pool = [];
      for (i = 0; i < okabe.length; i++) { if (C.contrast(okabe[i], pairs[j][1].bg) >= 3.0) { pool.push(okabe[i]); } }
      pairs[j][1]['chart-1'] = C.pickDistinct(pool, 1, C.WORST_KINDS, null, pairs[j][1].bg)[0];
    }
    var roles = { light: light, dark: dark };
    var ev = C.evaluate(task, roles, 'skip');
    for (i = 0; i < ev.advisory.length; i++) {
      if (!ev.advisory[i].pass) {
        findings.push({ id: ev.advisory[i].finding, mode: ev.advisory[i].mode, severity: 'note', values: { ratio: ev.advisory[i].ratio } });
      }
    }
    var modes = ['light', 'dark'];
    for (j = 0; j < 2; j++) {
      mode = modes[j];
      r = C.contrast(roles[mode]['accent-text'], roles[mode].text);
      if (r < 3.0) { findings.push({ id: 'link-low', mode: mode, severity: 'note', values: { ratio: r } }); }
    }
    var distinct = [];
    if (o.k >= 2) {
      var kinds = ['normal', 'deutan', 'protan'].concat(o.pr ? ['gray'] : []), steps, md, rw;
      for (j = 0; j < 2; j++) {
        mode = modes[j];
        steps = [];
        for (i = 0; i < o.k; i++) { steps.push(roles[mode]['step-' + (i + 1)]); }
        md = C.minDistance(steps, kinds);
        rw = C.minDistance(raw[mode], kinds);
        distinct.push({ id: 'steps', mode: mode, value: md.value, a: 'step-' + (md.i + 1), b: 'step-' + (md.j + 1), kind: md.kind,
          compare: { id: 'steps-raw', value: rw.value, a: rw.a, b: rw.b, kind: rw.kind } });
      }
    }
    var md2;
    for (j = 0; j < 2; j++) {
      mode = modes[j];
      md2 = C.minDistance([roles[mode]['chart-1'], roles[mode]['accent-text']], ['normal', 'deutan', 'protan']);
      distinct.push({ id: 'chart', mode: mode, value: md2.value, a: 'chart-1', b: 'accent-text', kind: md2.kind, compare: { id: 'okabe-ito-7' } });
    }
    var usage = {}, rid;
    for (j = 0; j < 2; j++) {
      mode = modes[j];
      usage[mode] = {};
      for (i = 0; i < o.k; i++) {
        rid = 'step-' + (i + 1);
        r = C.contrast(roles[mode][rid], roles[mode].bg);
        usage[mode][rid] = r >= 4.5 ? 'text' : r >= 3.0 ? 'lines' : 'area';
      }
    }
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: roles, pairs: ev.pairs, decorative: ev.decorative,
      distinct: distinct, changes: changes, findings: findings, usage: usage,
      extra: { datasets: { 'okabe-ito': ['chart-1'] }, summary: ['summary.text'], pair_note: 'pair.note' } };
  }

  function viewVars(palette, mode, toggles) {
    var r = palette.roles[mode];
    if (toggles.view === 'inverted') { return { bg: r.text, text: r.bg }; }
    return {};
  }

  function list(palette, task, ctx, lang) {
    var out = [], i, k, roles;
    for (i = 0; i < palette.modes.length; i++) {
      out.push(ctx.core['label.' + palette.modes[i]]);
      roles = palette.roles[palette.modes[i]];
      for (k in roles) { if (Object.prototype.hasOwnProperty.call(roles, k)) { out.push(k + ': ' + roles[k]); } }
      out.push('');
    }
    out.push(ctx.core.link.split('{url}').join(ctx.url));
    return [{ label: null, text: out.join('\n'), suffix: '', lang: null, note: ctx.text['list.bnote'] }];
  }

  return { build: build, viewVars: viewVars, exports: { list: list } };
}));
