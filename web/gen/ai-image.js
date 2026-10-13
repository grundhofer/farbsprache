/* Generator der Aufgabe KI-Bild (FS.gen['ai-image']). Spiegel von tools/gen/ai_image.py:
   Farbnamen aus dem festen Vokabular, Vorschläge aus einer Farbe, Palettenobjekt, Export Bildprompt.
   Vorrang f vor c vor p. Rein, ohne DOM; tests/parity.test.cjs vergleicht mit Python. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen['ai-image'] = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  var ROLES = ['dominant', 'secondary', 'accent', 'background'];
  var PARTS = ['[BACKGROUND AND LARGE SHAPES]', '[SECONDARY ELEMENTS]', '[THE FOCAL ELEMENT]'];
  var PART_NO_BG = '[LARGE SHAPES]', INK = '#16191D', PAPER = '#FFFFFF';
  function has(o, k) { return o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k); }
  function hue(h) { return h === null || h === undefined || h !== h ? null : h; }

  // ---------- Farbnamen
  function sector(h, sectors) {
    for (var i = 0; i < sectors.length; i++) { if (h < sectors[i][0]) { return sectors[i][1]; } }
    return sectors[sectors.length - 1][1];
  }
  function colorName(hx, cn) {
    var o = C().hexToOklch(hx), L = o[0], c = o[1], h = hue(o[2]), i, name, t;
    if (c < cn.neutral_c_max || h === null) {
      name = 'black';
      for (i = 0; i < cn.neutral_steps.length; i++) { if (L >= cn.neutral_steps[i][0]) { name = cn.neutral_steps[i][1]; break; } }
      t = cn.tint;
      if (h !== null && c >= t.c_min && name !== 'black') {
        if (t.warm[0] <= h && h <= t.warm[1]) { name += ' with a warm tint'; } else if (t.cool[0] <= h && h <= t.cool[1]) { name += ' with a cool tint'; }
      }
      return name;
    }
    var base = sector(h, cn.sectors), drop = false, s, lw = cn.lightness, light = null, ch = cn.chroma, chroma = null, out = [];
    if (base === 'teal|cyan') { base = L < cn.teal_cyan_l ? 'teal' : 'cyan'; }
    for (i = 0; i < cn.substitutions.length; i++) {
      s = cn.substitutions[i];
      if (s.bases.indexOf(base) >= 0 && ((has(s, 'l_below') && L < s.l_below) || (has(s, 'l_from') && L >= s.l_from))) {
        base = s.to; drop = s.drop_lightness; break;
      }
    }
    if (!drop) {
      if (L >= lw.light.l_from) {
        if (L >= lw.pale.l_from && c < lw.pale.c_below) { light = 'pale'; } else if (c < lw.light.c_below) { light = 'light'; }
      } else if (lw.deep[0] <= L && L < lw.deep[1]) { light = 'deep'; } else if (L < lw.dark[1]) { light = 'dark'; }
    }
    if (c < ch.muted_below) { chroma = 'muted'; } else if (c > ch.vivid_above) { chroma = 'vivid'; }
    if (light) { out.push(light); }
    if (chroma) { out.push(chroma); }
    out.push(base);
    return out.join(' ');
  }
  function blockNames(hexes, cn) {
    var names = [], out = [], seen = {}, i, j, n, idx, lo, hi, L, words, skip;
    for (i = 0; i < hexes.length; i++) { names.push(colorName(hexes[i], cn)); out.push(names[i]); }
    for (i = 0; i < names.length; i++) {
      n = names[i];
      if (has(seen, n)) { continue; }
      seen[n] = true; idx = [];
      for (j = 0; j < names.length; j++) { if (names[j] === n) { idx.push(j); } }
      words = n.split(' '); skip = idx.length < 2;
      for (j = 0; j < words.length; j++) { if (cn.lightness_words.indexOf(words[j]) >= 0) { skip = true; } }
      if (skip) { continue; }
      L = {}; lo = idx[0]; hi = idx[0];
      for (j = 0; j < idx.length; j++) { L[idx[j]] = C().hexToOklch(hexes[idx[j]])[0]; }
      for (j = 0; j < idx.length; j++) {
        if (L[idx[j]] < L[lo]) { lo = idx[j]; }
        if (L[idx[j]] >= L[hi]) { hi = idx[j]; }
      }
      // nur, wenn die hellste wirklich heller ist; gleiche Hex-Werte heißen immer gleich (dann greift same-names)
      if (!(L[hi] > L[lo])) { continue; }
      for (j = 0; j < idx.length; j++) {
        if (hexes[idx[j]] === hexes[hi]) { out[idx[j]] = 'lighter ' + n; } else if (hexes[idx[j]] === hexes[lo]) { out[idx[j]] = 'darker ' + n; }
      }
    }
    return out;
  }

  // ---------- Vorschläge aus einer Farbe
  function suggest(seed, kind) {
    var o = C().hexToOklch(seed), L = o[0], Cs = o[1], h = hue(o[2]), K = C(), sec, acc;
    if (h === null) { h = 0; }
    seed = K.normHex(seed);
    if (kind === 'contrast') {
      acc = K.oklchToHex(L < 0.55 ? 0.70 : 0.45, Math.min(Math.max(Cs, 0.10), 0.16), (h + 180) % 360);
      return [seed, K.oklchToHex(0.96, 0.01, h), acc];
    }
    if (kind === 'signal') { return [K.oklchToHex(0.95, 0.008, h), K.oklchToHex(0.30, 0.01, h), seed]; }
    sec = L < 0.7 ? K.oklchToHex(0.95, Math.min(0.02, Cs), h) : K.oklchToHex(0.30, Math.min(0.04, Cs), h);
    acc = L >= 0.5 ? K.oklchToHex(L - 0.25, Cs, h) : K.oklchToHex(L + 0.30, Cs, h);
    return [seed, sec, acc];
  }
  function suggestValues(seed, kind) {
    var cols = suggest(seed, kind), K = C();
    return { normal: K.minDistance(cols, ['normal']).value, redgreen: K.minDistance(cols, ['deutan', 'protan']).value,
      gray: K.minDistance(cols, ['gray']).value };
  }

  // ---------- Palette
  function colors(inp) {
    var o = inp.options, f = o.f, out = [], i, s;
    if (f && f.length) {
      if (f.length < 2) { throw new (C().SolveError)('few-colors', { n: f.length }); }
      for (i = 0; i < f.length && i < 4; i++) { out.push([ROLES[i], C().normHex(f[i])]); }
      return [out, 'f'];
    }
    if (inp.seed) {
      s = suggest(inp.seed, o.s || 'calm');
      for (i = 0; i < s.length; i++) { out.push([ROLES[i], s[i]]); }
      return [out, 'seed'];
    }
    for (i = 0; i < inp.colors.length; i++) { out.push([inp.colors[i].role, C().normHex(inp.colors[i].value)]); }
    return [out, 'preset'];
  }
  function weights(o, present) {
    var main = [], i, w, out = {};
    for (i = 0; i < present.length; i++) { if (present[i] !== 'background') { main.push(present[i]); } }
    if (main.length === 2) { out[main[0]] = 80; out[main[1]] = 20; return out; }
    w = (o.w || '60-30-10').split('-');
    for (i = 0; i < main.length; i++) { out[main[i]] = parseInt(w[i], 10); }
    return out;
  }
  function build(task, inp, ctx) {
    var K = C(), cn = ctx.data.colornames, o = inp.options, cs = colors(inp), cols = cs[0], i, r = {}, present = [], hexes = [];
    for (i = 0; i < cols.length; i++) { present.push(cols[i][0]); hexes.push(cols[i][1]); r[cols[i][0]] = cols[i][1]; }
    var roles = { 'default': r }, bn = blockNames(hexes, cn), names = {}, ys = [], dk = 0, lt = 0;
    for (i = 0; i < present.length; i++) { names[present[i]] = bn[i]; ys.push(K.relLum(hexes[i])); }
    for (i = 0; i < ys.length; i++) { if (ys[i] < ys[dk]) { dk = i; } if (ys[i] > ys[lt]) { lt = i; } }
    var lines = dk !== lt ? [{ fg: present[dk], on: [present[lt]], min: 4.5, criterion: '1.4.3', rule: 'text-contrast' }] : [];
    var t2 = {}, k;
    for (k in task) { if (has(task, k)) { t2[k] = task[k]; } }
    t2.pairs = lines;
    var ev = K.evaluate(t2, roles, 'skip'), decorative = [], d;
    for (i = 0; i < ev.decorative.length; i++) {
      d = ev.decorative[i];
      if (!(lines.length && ((d.fg === present[dk] && d.bg === present[lt]) || (d.fg === present[lt] && d.bg === present[dk])))) { decorative.push(d); }
    }
    var textOk = ev.pairs.length > 0 && ev.pairs[0].pass, findings = [], uniq = {}, nu = 0;
    if (!textOk) { findings.push({ id: 'no-text-line', mode: null, severity: 'note', values: { ratio: ev.pairs.length ? ev.pairs[0].ratio : 1.0 } }); }
    for (i = 0; i < present.length; i++) { if (!has(uniq, names[present[i]])) { uniq[names[present[i]]] = true; nu++; } }
    if (nu < present.length) { findings.push({ id: 'same-names', mode: null, severity: 'note', values: {} }); }
    var distinct = [], kinds = ['normal', 'deutan', 'protan', 'gray'], md;
    for (i = 0; i < kinds.length; i++) {
      md = K.minDistance(hexes, [kinds[i]]);
      distinct.push({ id: 'colors', mode: 'default', value: md.value, a: present[md.i], b: present[md.j], kind: kinds[i] });
    }
    var ref = has(r, 'background') ? 'background' : 'dominant', use = {}, cr;
    for (i = 0; i < present.length; i++) {
      if (present[i] === ref) { continue; }
      cr = K.contrast(hexes[i], r[ref]);
      use[present[i]] = cr >= 4.5 ? 'text' : cr >= 3.0 ? 'lines' : 'area';
    }
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null, modes: task.modes.slice(), roles: roles,
      pairs: ev.pairs, decorative: decorative, distinct: distinct, changes: [], findings: findings, usage: { 'default': use },
      extra: { names: names, weights: weights(o, present), text_pair: textOk ? [present[dk], present[lt]] : null, source: cs[1] } };
  }
  function viewVars(palette, mode, toggles) {
    var r = palette.roles['default'], ex = palette.extra, out = { paper: PAPER, ink: INK, board: has(r, 'background') ? r.background : PAPER }, i, role;
    for (i = 0; i < ROLES.length; i++) {
      role = ROLES[i];
      if (has(r, role)) {
        out['label-' + role] = "'" + ex.names[role] + ' · ' + r[role] + "'";
        out['w-' + role] = String(has(ex.weights, role) ? ex.weights[role] : 0);
        out['show-' + role] = 'flex';
      } else { out['show-' + role] = 'none'; }
    }
    return out;
  }

  // ---------- Export Bildprompt
  function fill(t, vals) { return t.replace(/\{(c|w|p|a|b)\}/g, function (m, k) { return has(vals, k) ? vals[k] : m; }); }
  function model(ctx, mid) {
    var ms = ctx.data.models.models, i;
    for (i = 0; i < ms.length; i++) { if (ms[i].id === mid) { return ms[i]; } }
    return ms[0];
  }
  function part(o, key, def) { var v = String(o[key] || '').replace(/^[ \t\n\r]+|[ \t\n\r]+$/g, ''); return v || def; }
  function promptText(palette, mdl, text) {
    var o = palette.input.options, r = palette.roles['default'], ex = palette.extra, hexed = mdl.method === 'hex-in-prompt', w = ex.weights;
    function nm(role) { return ex.names[role] + (hexed ? ' (' + r[role] + ')' : ''); }
    var bg = has(r, 'background'), p1 = part(o, 'b1', PARTS[0]);
    if (bg && p1 === PARTS[0]) { p1 = PART_NO_BG; }
    var clauses = [fill(text['pr.dominant'], { c: nm('dominant'), w: String(w.dominant), p: p1 })];
    if (has(r, 'secondary')) { clauses.push(fill(text['pr.secondary'], { c: nm('secondary'), w: String(w.secondary), p: part(o, 'b2', PARTS[1]) })); }
    if (has(r, 'accent')) { clauses.push(fill(text['pr.accent'], { c: nm('accent'), w: String(w.accent), p: part(o, 'b3', PARTS[2]) })); }
    if (bg) { clauses.push(fill(text['pr.background'], { c: nm('background') })); }
    var out = text['pr.open'] + clauses.join('; ') + '. ' + text['pr.guard'];
    if (ex.text_pair) { out += ' ' + fill(text['pr.text'], { a: nm(ex.text_pair[0]), b: nm(ex.text_pair[1]) }); }
    if (mdl.id === 'gpt-image') { out += ' ' + text['pr.gpt']; }
    return out;
  }
  function rgb(hx) { return '[' + parseInt(hx.slice(1, 3), 16) + ', ' + parseInt(hx.slice(3, 5), 16) + ', ' + parseInt(hx.slice(5, 7), 16) + ']'; }
  function recraftJson(palette) {
    var r = palette.roles['default'], w = palette.extra.weights, parts = [], i, x, out;
    for (i = 0; i < ROLES.length; i++) {
      x = ROLES[i];
      if (has(r, x) && x !== 'background') { parts.push('{"rgb": ' + rgb(r[x]) + ', "weight": ' + X().dec(w[x], 2) + '}'); }
    }
    out = '{"controls": {"colors": [' + parts.join(', ') + ']';
    if (has(r, 'background')) { out += ', "background_color": {"rgb": ' + rgb(r.background) + '}'; }
    return out + '}}';
  }
  function note(mdl, text, lang, extra) {
    var esc = C().esc, parts = [fill(text['note.model'], { c: '<b>' + esc(mdl.name) + '</b>', w: esc(mdl.vendor), p: esc(mdl.checked) }) + ' ' + esc(mdl['note_' + lang])];
    if (mdl['doc_note_' + lang]) { parts.push(esc(mdl['doc_note_' + lang])); }
    if (mdl.quote) { parts.push(fill(text['note.quote'], { c: esc(mdl.quote) })); }
    if (extra) { parts.push(esc(extra)); }
    parts.push(text['note.duty']);
    return parts.join(' ');
  }
  function prompt(palette, task, ctx, lang) {
    var text = ctx.text, mdl = model(ctx, palette.input.options.mdl), r = palette.roles['default'], hx = [], i;
    var blocks = [{ label: null, text: promptText(palette, mdl, text), suffix: '', lang: 'en', note: note(mdl, text, lang) }];
    if (mdl.method === 'palette-field') {
      for (i = 0; i < ROLES.length; i++) { if (has(r, ROLES[i])) { hx.push(r[ROLES[i]]); } }
      blocks[0].label = text['blk.prompt'];
      blocks.push({ label: text['blk.palette'], text: hx.join(' '), suffix: '-palette', lang: null, note: note(mdl, text, lang, mdl['field_note_' + lang]) });
    } else if (mdl.method === 'api-weights') {
      blocks[0].label = text['blk.prompt'];
      blocks.push({ label: text['blk.json'], text: recraftJson(palette), suffix: '-controls', lang: null, note: note(mdl, text, lang, mdl['field_note_' + lang]), ext: 'json' });
    }
    return blocks;
  }
  // Hex-Liste des Rahmens; mit eigenen Farben (f) heißt die Palette „Eigene Farben“ statt wie die Startpalette (das setzt auch der Rahmen)
  function hexList(palette, task, ctx, lang, opts) {
    var c = ctx, k;
    if (palette.extra.source === 'f') {
      c = {};
      for (k in ctx) { if (has(ctx, k)) { c[k] = ctx[k]; } }
      c.name = ctx.text['name.f'];
    }
    return X().hex(palette, task, c, lang, opts);
  }

  return { build: build, viewVars: viewVars, exports: { prompt: prompt, hex: hexList }, colorName: colorName, blockNames: blockNames,
    suggest: suggest, suggestValues: suggestValues, promptText: promptText, model: model };
}));
