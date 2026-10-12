/* Generator der Aufgabe Text auf Bild (FS.gen['image-text']). Spiegel von tools/gen/image_text.py
   (Bauspezifikation 4.7, 4.1.15, 5.8). build(task, inp, ctx) -> Palettenobjekt (6.14), viewVars für Deckkraft und
   Referenzflächen, exports scrim, values und agent (nur Hex-Werte). */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen['image-text'] = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  // Feste Referenzflächen des Musters (wie REF in tools/gen/image_text.py)
  var REF = { 'ref-white': '#FFFFFF', 'ref-black': '#000000', 'ref-sky': '#DCEAF4', 'ref-sand': '#EFE3C8',
    'ref-leaf': '#5E7F3A', 'ref-stone': '#8A8F96', 'ref-night': '#141B2D', 'ref-dusk': '#3A3F55',
    'ref-light': '#FFD98A', 'ref-red': '#C2413B', 'ref-blue': '#2F6FB0' };
  var HEXD = '0123456789ABCDEF';

  function targetOf(o) { return parseFloat(o.tg); }

  function build(task, inp, ctx) {
    var o = inp.options, text = o.tc, sc = inp.seed, target = targetOf(o), i, k;
    var res = C().scrimAlpha(text, sc, target);
    if (res === null) { throw new (C().SolveError)('scrim-unreachable', { target: target, best: C().contrast(text, sc) }); }
    var roles = { 'default': { text: text, scrim: sc, 'worst-pixel': res.worst, composite: res.mix_hex } };
    var t2 = {}, pairs = [];
    for (k in task) { if (has(task, k)) { t2[k] = task[k]; } }
    for (i = 0; i < task.pairs.length; i++) {
      var p = {};
      for (k in task.pairs[i]) { if (has(task.pairs[i], k)) { p[k] = task.pairs[i][k]; } }
      p.min = target; pairs.push(p);
    }
    t2.pairs = pairs;
    var ev = C().evaluate(t2, roles, 'skip');
    var worst = res.worst === '#FFFFFF' ? 'white' : 'black', tkey = target === 3 ? '3' : '4.5';
    // Es zählt der kleinere Kontrast (4.7); die Seite zeigt den 8-Bit-Wert und sagt, ob er der kleinere ist
    // Gleichstand innerhalb der Rechengenauigkeit (1e-9) gilt als 8 Bit, wie in Python
    var low = res.ratio_at_percent_8bit <= res.ratio_at_percent + 1e-9 ? '8bit' : 'float';
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: roles, pairs: ev.pairs, decorative: ev.decorative,
      distinct: [], changes: [], findings: [], usage: {},
      extra: { summary: ['summary.alpha.' + tkey, 'summary.low.' + low, 'summary.worst.' + worst],
        scrim: { alpha: res.alpha, percent: res.percent, ratio: res.ratio_at_percent, ratio_8bit: res.ratio_at_percent_8bit, target: target } } };
  }

  // Deckkraft als Zahl (--d-alpha) und die festen Farben der Referenzflächen
  function viewVars(palette, mode, toggles) {
    var out = {}, k;
    for (k in REF) { if (has(REF, k)) { out[k] = REF[k]; } }
    out.alpha = X().dec(palette.extra.scrim.percent, 2);
    return out;
  }

  // ---------- Exporte
  function alpha(pct) { return X().dec(pct, 2); }
  function ch(hx, i) { return parseInt(hx.slice(i, i + 2), 16); }
  function rgb(hx, a) { return 'rgb(' + ch(hx, 1) + ' ' + ch(hx, 3) + ' ' + ch(hx, 5) + ' / ' + a + ')'; }
  function rgba(hx, a) { return 'rgba(' + ch(hx, 1) + ', ' + ch(hx, 3) + ', ' + ch(hx, 5) + ', ' + a + ')'; }
  // Hex mit Alpha, aufgerundet (nie weniger deckend als die Mindestdeckkraft)
  function hex8(hx, pct) { var n = Math.floor((pct * 255 + 99) / 100); return hx + HEXD.charAt(Math.floor(n / 16)) + HEXD.charAt(n % 16); }
  function words(palette, ctx, lang) {
    var r = palette.roles['default'], s = palette.extra.scrim;
    return { tx: ctx.text, r: r, s: s, pct: C().fmtPctUp(s.percent / 100, lang), target: X().fmtThreshold(s.target, lang),
      worst: r['worst-pixel'] === '#FFFFFF' ? 'white' : 'black', tkey: s.target === 3 ? '3' : '4.5' };
  }
  function fill(t, values) {
    var k;
    for (k in values) { if (has(values, k)) { t = t.split('{' + k + '}').join(values[k]); } }
    return t;
  }
  function scrimCss(palette, task, ctx, lang, opts) {
    var w = words(palette, ctx, lang), r = w.r, tx = w.tx, a = alpha(w.s.percent), i;
    var vals = { text: r.text, sc: r.scrim, target: w.target, pct: w.pct, pixel: r['worst-pixel'] };
    var head = [X().header(ctx), fill(tx['css.line'], vals), fill(tx['css.worst.' + w.worst], vals), tx['css.text'], X().presub(ctx.core.link, ctx)];
    var lines = ['/* ' + X().commentSafe(head[0])];
    for (i = 1; i < head.length; i++) { lines.push('   ' + X().commentSafe(head[i])); }
    lines[lines.length - 1] += ' */';
    lines = lines.concat(['.hero {', '  background:',
      '    linear-gradient(to top, ' + rgb(r.scrim, a) + ' 0%, ' + rgb(r.scrim, a) + ' 40%, ' + rgb(r.scrim, '0') + ' 70%),',
      '    url("' + tx['css.image'] + '") center / cover;',
      '  color: ' + r.text + ';', '}']);
    return lines.join('\n');
  }
  function values(palette, task, ctx, lang, opts) {
    var w = words(palette, ctx, lang), r = w.r, s = w.s, tx = w.tx, low = Math.min(s.ratio, s.ratio_8bit), i, width = 0;
    var rows = [['val.text', r.text], ['val.scrim', r.scrim],
      ['val.target', w.target + ' ' + tx['val.target.' + w.tkey]],
      ['val.alpha', w.pct + ' (alpha ' + alpha(s.percent) + ')'],
      ['val.worst', r['worst-pixel'] + ' ' + tx['val.worst.' + w.worst]],
      ['val.mix', r.composite],
      ['val.ratio', fill(tx['val.ratio.v'], { f: C().fmtRatio(s.ratio, lang, s.target), q: C().fmtRatio(s.ratio_8bit, lang, s.target),
        m: C().fmtRatio(low, lang, s.target) })],
      ['val.area', tx['val.area.v']]];
    for (i = 0; i < rows.length; i++) { width = Math.max(width, tx[rows[i][0]].length); }
    width += 2;
    var lines = [X().header(ctx)];
    for (i = 0; i < rows.length; i++) { lines.push(X().pad(tx[rows[i][0]], width) + rows[i][1]); }
    lines = lines.concat(['', X().presub(ctx.core.link, ctx)]);
    return lines.join('\n');
  }
  function agent(palette, task, ctx, lang, opts) {
    var w = words(palette, ctx, lang), r = w.r, s = w.s, tx = w.tx, core = ctx.core, a = alpha(s.percent);
    var rc = X().rctx(palette, null, null, ctx), i, rules = ctx.rules || [];
    var vals = { text: r.text, sc: r.scrim, target: w.target, pct: w.pct, pixel: r['worst-pixel'], alpha: a, mix: r.composite,
      hex8: hex8(r.scrim, s.percent), hex0: r.scrim + '00', rgba: rgba(r.scrim, a), rgba0: rgba(r.scrim, '0'),
      ratio: C().fmtRatio(Math.min(s.ratio, s.ratio_8bit), lang, s.target) };
    var out = [tx['agent.intro'], '', '# ' + X().presub(tx['agent.title'], ctx), '', core.h_idea, fill(tx['agent.idea.' + w.worst], vals), '', tx['agent.h_values']];
    for (i = 0; i < tx['agent.values'].length; i++) { out.push('- ' + fill(tx['agent.values'][i], vals)); }
    out = out.concat(['', tx['agent.h_build']]);
    for (i = 0; i < tx['agent.build'].length; i++) { out.push('- ' + fill(tx['agent.build'][i], vals)); }
    out = out.concat(['', core.h_rules]);
    for (i = 0; i < rules.length; i++) {
      out.push('- ' + X().plain(X().presub(rules[i]['text_' + lang], ctx), rc, lang) + ' ' + X().levelNote(rules[i], ctx, lang));
    }
    out = out.concat(['', core.h_avoid]);
    for (i = 0; i < tx['agent.avoid'].length; i++) { out.push('- ' + X().plain(X().presub(tx['agent.avoid'][i], ctx), rc, lang)); }
    out = out.concat(['', core.h_check]);
    for (i = 0; i < tx['agent.checks'].length; i++) { out.push('- ' + X().plain(X().presub(tx['agent.checks'][i], ctx), rc, lang)); }
    out = out.concat(['', core.h_tip, X().plain(X().presub(tx['agent.tip'], ctx), rc, lang), '', '---']);
    out.push(X().presub(core[palette.preset === null || palette.preset === undefined ? 'agent_source_custom' : 'agent_source'], ctx));
    return out.join('\n');
  }

  return { build: build, viewVars: viewVars, exports: { scrim: scrimCss, values: values, agent: agent } };
}));
