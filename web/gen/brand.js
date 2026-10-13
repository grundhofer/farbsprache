/* Generator der Aufgabe Logo und Marke (FS.gen.brand). Spiegel von tools/gen/brand.py:
   Schriftfarbe, Textvarianten auf Weiß und #16191D, Graustufe, zweite Farbe, Steckbrief als Markdown.
   Die Markenfarbe selbst bleibt unverändert. Rein, ohne DOM; tests/parity.test.cjs vergleicht mit Python. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.brand = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  var WHITE = '#FFFFFF', BLACK = '#000000', DARK = '#16191D';
  function has(o, k) { return o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k); }

  // Textvariante; liegt die Fläche auf der falschen Seite, startet die Suche knapp jenseits der Fläche
  function variant(c, h, L, against, direction) {
    try { return C().solveL(c, h, [against], 4.5, direction, L); } catch (e) {
      if (!(e instanceof C().SolveError) || e.key !== 'mixed-sides') { throw e; }
      return C().solveL(c, h, [against], 4.5, direction, C().hexToOklch(against)[0] + 0.05 * direction);
    }
  }
  function build(task, inp, ctx) {
    var K = C(), seed = K.normHex(inp.seed), o = inp.options, lch = K.hexToOklch(seed), L = lch[0], c = lch[1], h = lch[2];
    if (h === null || h === undefined || h !== h) { h = 0; }
    var on = K.contrast(seed, WHITE) >= K.contrast(seed, BLACK) ? WHITE : BLACK;
    var light = variant(c, h, L, WHITE, -1), dark = variant(c, h, L, DARK, 1);
    var r = { brand: seed, 'on-brand': on, 'brand-text-light': light.hex, 'brand-text-dark': dark.hex, 'brand-gray': K.grayHex(seed),
      'bg-light': WHITE, 'bg-dark': DARK };
    var c2 = o.c2;
    if (c2) { r['brand-2'] = K.normHex(c2); }
    var roles = { 'default': r }, changes = [], list = [['brand-text-light', light, WHITE, 'text-light'], ['brand-text-dark', dark, DARK, 'text-dark']], i, x;
    for (i = 0; i < list.length; i++) {
      x = list[i];
      if (x[1].hex !== seed) {
        changes.push({ role: x[0], mode: 'default', from: seed, to: x[1].hex, key: x[3], values: { before: K.contrast(seed, x[2]), after: x[1].ratio } });
      }
    }
    var ev = K.evaluate(task, roles, 'skip'), distinct = [], findings = [], md;
    if (c2) {
      md = K.minDistance([seed, r['brand-2']], K.WORST_KINDS.slice());
      distinct.push({ id: 'brand2', mode: 'default', value: md.value, a: 'brand', b: 'brand-2', kind: md.kind, compare: { id: 'okabe-ito-7' } });
      distinct.push({ id: 'brand2-gray', mode: 'default', value: K.grayDistance(seed, r['brand-2']), a: 'brand', b: 'brand-2', kind: 'gray' });
      if (md.value < K.JND_DISTANCE) { findings.push({ id: 'brand2-close', mode: null, severity: 'note', values: { distance: md.value } }); }
    }
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null, modes: task.modes.slice(), roles: roles,
      pairs: ev.pairs, decorative: ev.decorative, distinct: distinct, changes: changes, findings: findings, usage: {},
      extra: { summary: c2 ? ['summary.c2'] : [] } };
  }
  function viewVars(palette, mode) {
    return { 'mono-ink': BLACK, 'mono-paper': WHITE, 'show-2': has(palette.roles[mode], 'brand-2') ? 'flex' : 'none' };
  }

  // ---------- Steckbrief (Markdown)
  function rgb(hx) { return 'rgb(' + parseInt(hx.slice(1, 3), 16) + ' ' + parseInt(hx.slice(3, 5), 16) + ' ' + parseInt(hx.slice(5, 7), 16) + ')'; }
  function factsheet(palette, task, ctx, lang) {
    var t = ctx.text, r = palette.roles['default'], rc = X().rctx(palette, 'default', null, ctx), ok = C().shortestOklch(r.brand);
    function p(key) { return X().plain(X().presub(t[key], ctx), rc, lang); }
    var out = [p('fs.title'), X().header(ctx), '', '## ' + t['fs.h_screen'],
      '- Hex: ' + r.brand, '- RGB: ' + rgb(r.brand), '- OKLCH: ' + (ok ? ok : t['fs.oklch_none']), '',
      '## ' + t['fs.h_on'], p('fs.on_white'), p('fs.on_black'),
      p(r['on-brand'] === '#FFFFFF' ? 'fs.on_pick_white' : 'fs.on_pick_black'),
      p(C().contrast(r['on-brand'], r.brand) >= 7 ? 'fs.aaa_ok' : 'fs.aaa_gap'), '',
      '## ' + t['fs.h_text'],
      p(r['brand-text-light'] === r.brand ? 'fs.text_light' : 'fs.text_light_changed'),
      p(r['brand-text-dark'] === r.brand ? 'fs.text_dark' : 'fs.text_dark_changed'), '',
      '## ' + t['fs.h_gray'], p('fs.gray'), '',
      '## ' + t['fs.h_mono'], p('fs.mono_black'), p('fs.mono_white'), ''];
    if (has(r, 'brand-2')) { out = out.concat(['## ' + t['fs.h_c2'], p('fs.c2_hex'), p('fs.c2_cr'), p('fs.c2_dist'), '']); }
    out = out.concat(['## ' + t['fs.h_print'], p('fs.print'), '', '## ' + t['fs.h_law'], p('fs.law'), '', '---', X().presub(ctx.core.link, ctx)]);
    return out.join('\n');
  }

  return { build: build, viewVars: viewVars, exports: { factsheet: factsheet } };
}));
