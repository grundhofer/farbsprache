/* Generator der Aufgabe Präsentation (FS.gen.slides). Spiegel von tools/gen/slides.py (Bauspezifikation 4.5, 5.7).
   build(task, inp, ctx) -> Palettenobjekt (6.14), viewVars für die Ansicht „Beamer“, exports hex und rationale. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.slides = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  var LIGHT_T = 7.7, LINE_T = 3.3;
  var DARK_C = 0.85;  // Buntheit des Akzents im dunklen Modus, wie DARK_C in web/gen/website.js
  var OFFICE = ['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink'];
  var CHARTS = ['chart-1', 'chart-2', 'chart-3', 'chart-4'];

  function tint(cs) { return Math.min(Math.max(0.1 * cs, 0.004), 0.012); }
  // solve_l mit Startwert L0; bei mixed-sides startet die Suche bei L 0,5 (wie tools/gen/slides.py)
  function solve(c, h, against, target, direction, l0) {
    try { return C().solveL(c, h, against, target, direction, l0); } catch (e) {
      if (!(e instanceof C().SolveError) || e.key !== 'mixed-sides') { throw e; }
      return C().solveL(c, h, against, target, direction, 0.5);
    }
  }
  function okabeColors(ctx) {
    var ds = ctx.datasets['okabe-ito'], i, s = null, out = [];
    for (i = 0; i < ds.schemes.length; i++) { if (ds.schemes[i].id === 'okabe-ito') { s = ds.schemes[i]; break; } }
    for (i = 0; i < s.colors.length; i++) { if (s.colors[i].name !== 'black') { out.push(s.colors[i].hex); } }
    return out;
  }
  function office(r) {
    var extra = [], i, rids, out = [];
    for (i = 0; i < CHARTS.length; i++) { if (has(r, CHARTS[i]) && r[CHARTS[i]] !== r.accent && extra.length < 3) { extra.push(CHARTS[i]); } }
    while (extra.length < 3) { extra.push('text-2'); }
    rids = ['text', 'slide', 'text-2', 'slide-2', 'accent'].concat(extra, ['text-2', 'line', 'accent-text', 'text-2']);
    for (i = 0; i < OFFICE.length; i++) { out.push({ slot: OFFICE[i], role: rids[i] }); }
    return out;
  }

  function build(task, inp, ctx) {
    var o = inp.options, seed = inp.seed, bg = o.bg, room = o.room, pr = !!o.pr;
    var lch = C().hexToOklch(seed), ls = lch[0], cs = lch[1], h = lch[2], t;
    if (h === null || h !== h) { h = 0; t = 0; } else { t = tint(cs); }
    var r = {}, changes = [], findings = [], surf, ca, cand, key = null, i;
    if (bg === 'dark') {
      r.slide = C().oklchToHex(0.20, t, h);
      r['slide-2'] = C().oklchToHex(0.25, t, h);
      surf = [r.slide, r['slide-2']];
      r.text = solve(0.6 * t, h, surf, LIGHT_T, 1, 0.94).hex;
      r['text-2'] = solve(t, h, surf, 7.0, 1, 0.80).hex;
      r.line = solve(t, h, [r.slide], LINE_T, 1, 0.45).hex;
      ca = DARK_C * cs;
      cand = C().oklchToHex(ls, ca, h);
      if (C().contrast(cand, r.slide) >= 3.0) { r.accent = cand; key = 'accent-dark'; }
      else { r.accent = solve(ca, h, [r.slide], 3.0, 1, ls).hex; key = 'accent-lighter'; }
      r['accent-text'] = solve(ca, h, surf, 7.0, 1, ls).hex;
    } else {
      r.slide = C().oklchToHex(0.985, 0.4 * t, h);
      r['slide-2'] = C().oklchToHex(0.95, 0.6 * t, h);
      surf = [r.slide, r['slide-2']];
      r.text = solve(1.6 * t, h, surf, LIGHT_T, -1, 0.24).hex;
      r['text-2'] = solve(1.4 * t, h, surf, 7.0, -1, 0.45).hex;
      r.line = solve(1.4 * t, h, [r.slide], LINE_T, -1, 0.70).hex;
      if (C().contrast(seed, r.slide) >= 3.0) { r.accent = seed; key = null; }
      else { r.accent = solve(cs, h, [r.slide], 3.0, -1, ls).hex; key = 'accent-darker'; }
      r['accent-text'] = solve(cs, h, surf, 7.0, -1, ls).hex;
    }
    if (r.accent !== seed) {
      changes.push({ role: 'accent', mode: 'default', from: seed, to: r.accent, key: key || 'accent-darker',
        values: { before: C().contrast(seed, r.slide), after: C().contrast(r.accent, r.slide) } });
    }
    if (r['accent-text'] !== seed) {
      // auf dunklem Grund geht die Textvariante vom Akzent mit 0,85-facher Chroma aus; der Hinweis sagt das
      changes.push({ role: 'accent-text', mode: 'default', from: seed, to: r['accent-text'], key: bg === 'dark' ? 'accent-text-dark' : 'accent-text',
        values: { before: C().contrast(seed, r.slide), after: C().contrast(r['accent-text'], r['slide-2']) } });
    }
    var okabe = okabeColors(ctx), pool = [r.accent], kinds = C().WORST_KINDS.slice();
    for (i = 0; i < okabe.length; i++) { if (C().contrast(okabe[i], r.slide) >= 3.0) { pool.push(okabe[i]); } }
    if (pr) { kinds.push('gray'); }
    var picked = C().pickDistinct(pool, 4, kinds, r.accent, r.slide);
    for (i = 0; i < picked.length; i++) { r[CHARTS[i]] = picked[i]; }
    var roles = { 'default': r };
    var ev = C().evaluate(task, roles, 'skip');
    if (bg === 'dark') { findings.push({ id: 'dark-slide', mode: null, severity: 'note', values: {} }); }
    if (room === 'bright') {
      findings.push({ id: 'bright-room', mode: null, severity: 'note', values: { projected: C().projectedContrast(r.text, r.slide, room) } });
    }
    if (picked.length < 4) { findings.push({ id: 'few-chart-colors', mode: null, severity: 'note', values: { count: picked.length } }); }
    var distinct = [], charts = [], md, mg;
    for (i = 0; i < CHARTS.length; i++) { if (has(r, CHARTS[i])) { charts.push(r[CHARTS[i]]); } }
    if (charts.length >= 2) {
      md = C().minDistance(charts, ['normal', 'deutan', 'protan']);
      distinct.push({ id: 'chart', mode: 'default', value: md.value, a: CHARTS[md.i], b: CHARTS[md.j], kind: md.kind, compare: { id: 'okabe-ito-7' } });
      if (pr) {
        mg = C().minDistance(charts, ['gray']);
        distinct.push({ id: 'chart-gray', mode: 'default', value: mg.value, a: CHARTS[mg.i], b: CHARTS[mg.j], kind: 'gray' });
      }
    }
    var usage = { 'default': {} }, urs = ['accent'].concat(CHARTS), k;
    for (i = 0; i < urs.length; i++) {
      if (has(r, urs[i])) {
        k = C().contrast(r[urs[i]], r.slide);
        usage['default'][urs[i]] = k >= 4.5 ? 'text' : k >= 3.0 ? 'lines' : 'area';
      }
    }
    var inOkabe = [];
    for (i = 0; i < CHARTS.length; i++) { if (has(r, CHARTS[i]) && okabe.indexOf(r[CHARTS[i]]) >= 0) { inOkabe.push(CHARTS[i]); } }
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: roles, pairs: ev.pairs, decorative: ev.decorative,
      distinct: distinct, changes: changes, findings: findings, usage: usage,
      extra: { datasets: { 'okabe-ito': inOkabe }, summary: ['summary.' + room], pair_note: 'pair.' + room, office: office(r) } };
  }

  // Muster-Schalter „Beamer“: jede Farbe nach dem Beamer-Modell (4.1.14) beim gewählten Raumlicht; die
  // Modellbeschriftung bleibt in den Bildschirmfarben (cap-text auf cap-bg), damit sie auch im hellen Raum lesbar ist
  function viewVars(palette, mode, toggles) {
    var out = {}, k, room, roles = palette.roles[mode];
    if (toggles.view !== 'projector') { return out; }
    room = palette.input.options.room;
    for (k in roles) { if (has(roles, k)) { out[k] = C().projectorHex(roles[k], room); } }
    out['cap-text'] = roles.text; out['cap-bg'] = roles.slide;
    return out;
  }

  // ---------- Exporte
  function menuNote(task, ctx, lang) {
    var tx = ctx.text, out = ['<b>' + C().esc(tx['menu.h']) + '</b>'], ps = task.menu_paths || [], i, m, line;
    for (i = 0; i < ps.length; i++) {
      m = ps[i];
      line = '<b>' + C().esc(m.app) + ':</b> ' + C().esc(m['text_' + lang]);
      if (m.checked) { line += ' <small>' + tx['menu.checked'].split('{date}').join(C().esc(m.checked)).split('{url}').join(C().esc(m.url)) + '</small>'; }
      out.push(line);
    }
    return out.join('<br>');
  }
  function hex(palette, task, ctx, lang, opts) {
    var tx = ctx.text, roles = palette.roles['default'], byId = {}, rows = palette.extra.office, labels = [], width = 0, lines, i;
    for (i = 0; i < task.roles.length; i++) { byId[task.roles[i].id] = task.roles[i]; }
    for (i = 0; i < rows.length; i++) { labels.push(tx['office.' + rows[i].slot]); width = Math.max(width, labels[i].length); }
    width += 2;
    lines = [X().header(ctx), tx['office.intro']];
    if (palette.input.options.bg === 'dark') { lines.push(tx['office.dark']); }
    lines.push('');
    for (i = 0; i < rows.length; i++) { lines.push(X().pad(labels[i], width) + roles[rows[i].role] + '  ' + X().cssName(byId[rows[i].role])); }
    lines.push('');
    lines = lines.concat(X().notices(palette, ctx, task, opts));
    lines.push(X().presub(ctx.core.link, ctx));
    return [{ label: null, text: lines.join('\n'), suffix: '', lang: null, note: menuNote(task, ctx, lang) }];
  }
  function rationale(palette, task, ctx, lang, opts) {
    var tx = ctx.text, o = palette.input.options, rc = X().rctx(palette, null, null, ctx), parts = [], list_ = tx.rationale, i, e;
    parts.push(X().plain(X().presub(tx['rationale.bg.' + o.bg], ctx), rc, lang));
    for (i = 0; i < list_.length; i++) {
      e = list_[i];
      if (e !== null && typeof e === 'object') {
        if (!X().showIf(e.show_if || null, palette)) { continue; }
        e = e.text;
      }
      parts.push(X().plain(X().presub(e, ctx), rc, lang));
    }
    if (o.pr) { parts.push(X().plain(X().presub(tx['rationale.pr'], ctx), rc, lang)); }
    parts.push(X().plain(X().presub(tx['rationale.proj.' + o.room], ctx), rc, lang));
    parts.push(X().presub(ctx.core.rationale_end, ctx));
    return parts.concat(X().notices(palette, ctx, task, opts)).join(' ');
  }

  return { build: build, viewVars: viewVars, exports: { hex: hex, rationale: rationale } };
}));
