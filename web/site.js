/* Farbsprache – Seitenverhalten (ES5-IIFE wie Bildsprache, ohne Abhängigkeiten).
   Oben die reinen Teile (FS.site: Zustand, Renderer, Rechnen), ohne DOM und in Node testbar.
   Die Renderer sind Spiegel von pages/task.py; tests/export.test.cjs vergleicht beide Byte für Byte.
   Unten die DOM-Anbindung; jedes Modul prüft zuerst, ob seine Elemente existieren. */
(function (root) {
  'use strict';
  var FS = root.FS = root.FS || {};
  function C() { return FS.color; }
  function X() { return FS.export; }
  function has(o, k) { return o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k); }
  function esc(s) { return C().esc(s); }
  function copyObj(o) { var r = {}, k; for (k in o) { if (has(o, k)) { r[k] = o[k]; } } return r; }

  // ---------- Hilfen (Spiegel von pages/task.py)
  function fill(tmpl, values) {
    return tmpl.replace(/\{([a-z_]+)\}/g, function (m, k) { return has(values, k) ? values[k] : m; });
  }
  function label(R, key) {
    if (has(R.tc, key)) { return R.tc[key]; }
    if (has(R.T, key)) { return R.T[key]; }
    throw new Error('Text fehlt: ' + key);
  }
  // Zählform aus dem Rahmen: key_1 für genau eins, sonst key („1 Paar“, „2 Paare“)
  function plural(R, key, n) { return n === 1 && has(R.T, key + '_1') ? R.T[key + '_1'] : R.T[key]; }
  // Name mitten im englischen Satz in Sentence case („on background“); Abkürzungen wie CSS bleiben, Deutsch bleibt
  function inSentence(name, lang) { return lang === 'en' && /^[A-Z][a-z]/.test(name) ? name.charAt(0).toLowerCase() + name.slice(1) : name; }
  // Markdown-Codespannen `x` als <code>, je Wort eines (Umbruch nur an Leerzeichen); Exporte behalten die Backticks
  function codeSpans(html) {
    return html.replace(/`([^`<>]+)`/g, function (m, s) {
      var parts = s.split(' '), out = [], i;
      for (i = 0; i < parts.length; i++) { if (parts[i]) { out.push('<code>' + parts[i] + '</code>'); } }
      return out.join(' ');
    });
  }
  function roleIndex(task) { var o = {}, i; for (i = 0; i < task.roles.length; i++) { o[task.roles[i].id] = task.roles[i]; } return o; }
  function numTag(R, tmpl, roles, mode) {
    var ctx = { refs: R.refs };
    if (roles) { ctx.roles = roles; ctx.mode = mode; }
    return C().renderText(tmpl, ctx, R.lang, { escape: false }).html;
  }
  function crTag(R, a, b) { return numTag(R, '{cr:' + a + '/' + b + '}'); }
  function modeHead(R, pal, mode) { return pal.modes.length > 1 ? '<h3 class="mode-h">' + esc(R.T['label.' + mode]) + '</h3>' : ''; }
  function modePrefix(R, pal, mode) { return mode && pal.modes.length > 1 ? esc(R.T['label.' + mode]) + ': ' : ''; }
  function renderCopy(R, tmpl, pal, mode, extra) {
    return codeSpans(C().renderText(tmpl, X().rctx(pal, mode || null, extra || null, { refs: R.refs, date: R.date }), R.lang, { escape: false }).html);
  }
  var COPY_ICON = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">' +
    '<path d="M5 1h9v11H5z M2 4h2v1H3v9h8v-1h1v2H2z" fill="currentColor"/></svg>';

  // ---------- Block C
  function strips(R, pal) {
    var out = [], i, j, mode, r, cells;
    for (i = 0; i < pal.modes.length; i++) {
      mode = pal.modes[i]; cells = '';
      for (j = 0; j < R.task.roles.length; j++) {
        r = R.task.roles[j];
        if (r.core && has(pal.roles[mode], r.id)) { cells += '<span style="background:' + pal.roles[mode][r.id] + '"></span>'; }
      }
      out.push('<div class="strip" data-mode="' + mode + '" aria-hidden="true">' + cells + '</div>');
    }
    return out.join('');
  }
  function notes(R, pal, error) {
    var out = [], i, ch, text, ext;
    var chs = pal.changes || [];
    for (i = 0; i < chs.length; i++) {
      ch = chs[i]; ext = { from: ch.from, to: ch.to };
      text = renderCopy(R, label(R, 'change.' + ch.key), pal, ch.mode, ext);
      out.push('<div class="note" role="note"><p>' + modePrefix(R, pal, ch.mode) + text + '</p></div>');
    }
    if (error) {
      // eigener Schlüssel einer SolveError: Text solve.<key> der Aufgabe, sonst des Rahmens, sonst allgemein
      out.push('<div class="note" role="alert"><p>' + (has(R.tc, 'solve.' + error) ? R.tc['solve.' + error] : has(R.T, 'solve.' + error) ? R.T['solve.' + error] : R.T['solve.error']) + '</p></div>');
    }
    return out.join('');
  }
  // Kurzergebnis unter dem Farbstreifen aus palette.extra.summary (Textschlüssel der Aufgabe)
  function summary(R, pal) {
    var keys = (pal.extra || {}).summary || [], out = '', i;
    if (typeof keys === 'string') { keys = [keys]; }
    for (i = 0; i < keys.length; i++) { out += '<p class="pal-sum">' + renderCopy(R, label(R, keys[i]), pal) + '</p>'; }
    return out;
  }
  // Paare, dann dekorative Paare, dann Hinweispaare (palette.advisory): je Rolle der erste Treffer
  function badge(R, pal, mode, rid) {
    var names = roleIndex(R.task), i, j, p, hx = pal.roles[mode], L = [pal.pairs, pal.decorative, pal.advisory];
    for (j = 0; j < L.length; j++) {
      for (i = 0; i < (L[j] || []).length; i++) {
        p = L[j][i];
        if (p.mode === mode && p.fg === rid) {
          return '<span class="badge">' + fill(R.T[j === 1 ? 'badge.decor' : j ? 'badge.adv' : p.pass ? 'badge.pass' : 'badge.fail'], {
            ratio: crTag(R, hx[p.fg], hx[p.bg]), bg: esc(inSentence(names[p.bg]['name_' + R.lang], R.lang)), min: j ? '' : X().fmtThreshold(p.min, R.lang) }) + '</span>';
        }
      }
    }
    return '';
  }
  function roleRow(R, pal, mode, r) {
    var hx = pal.roles[mode][r.id], lang = R.lang;
    var use = ((pal.usage || {})[mode] || {})[r.id];
    var useHtml = use ? '<span class="use">' + esc(R.T['usage.' + use]) + '</span>' : '';
    var aria = esc(fill(R.T.copy_hex_l, { name: r['name_' + lang], value: hx }));
    return '<li class="role"><span class="swatch" style="background:' + hx + '"></span>' +
      '<span class="role-t"><b>' + esc(r['name_' + lang]) + '</b> <small>' + esc(r['use_' + lang]) + '</small></span>' +
      '<code class="hex">' + hx + '</code>' + badge(R, pal, mode, r.id) + useHtml +
      '<button type="button" class="btn icon" data-copy="' + hx + '" aria-label="' + aria + '">' + COPY_ICON + '</button></li>';
  }
  function roles(R, pal) {
    var out = [], i, j, mode, rs, core, rest, more, r;
    for (i = 0; i < pal.modes.length; i++) {
      mode = pal.modes[i]; rs = []; core = ''; rest = [];
      for (j = 0; j < R.task.roles.length; j++) { r = R.task.roles[j]; if (has(pal.roles[mode], r.id)) { rs.push(r); } }
      for (j = 0; j < rs.length; j++) { if (rs[j].core) { core += roleRow(R, pal, mode, rs[j]); } else { rest.push(rs[j]); } }
      more = '';
      if (rest.length) {
        more = '<details class="more-roles"><summary>' + esc(fill(R.T.more_roles, { n: C().fmtCount(rest.length, R.lang) })) + '</summary><ul class="roles">';
        for (j = 0; j < rest.length; j++) { more += roleRow(R, pal, mode, rest[j]); }
        more += '</ul></details>';
      }
      out.push('<div class="pal-mode" data-mode="' + mode + '">' + modeHead(R, pal, mode) + '<ul class="roles">' + core + '</ul>' + more + '</div>');
    }
    return out.join('');
  }

  // ---------- Block F
  function calcLine(R, a, b) {
    var lang = R.lang, ya = C().relLum(a), yb = C().relLum(b), hi = ya >= yb ? ya : yb, lo = ya >= yb ? yb : ya;
    return fill(R.T.calc, { a: a, ya: C().fmtLum(ya, lang), b: b, yb: C().fmtLum(yb, lang), hi: C().fmtLum(hi, lang),
      lo: C().fmtLum(lo, lang), k: X().fixed(5, 2, lang), r: crTag(R, a, b) });
  }
  // Zusatz je geprüftem Paar aus palette.extra.pair_note, Pseudo-Rollen pair-fg und pair-bg
  function pairNote(R, pal, mode, a, b) {
    var key = (pal.extra || {}).pair_note;
    return key ? '<small class="pair-note">' + renderCopy(R, label(R, key), pal, mode, { 'pair-fg': a, 'pair-bg': b }) + '</small>' : '';
  }
  function compareName(R, cid) {
    if (has(R.tc, 'compare.' + cid)) { return R.tc['compare.' + cid]; }
    for (var i = 0; i < R.comparisons.length; i++) { if (R.comparisons[i].id === cid) { return R.comparisons[i]['name_' + R.lang]; } }
    return label(R, 'compare.' + cid);
  }
  function pairLabel(R, p) {
    var names = roleIndex(R.task);
    return fill(R.T.pair, { fg: '<b>' + esc(names[p.fg]['name_' + R.lang]) + '</b>', bg: '<b>' + esc(names[p.bg]['name_' + R.lang]) + '</b>' });
  }
  function checkSum(R, pal) {
    var ps = pal.pairs || [], k = 0, i;
    for (i = 0; i < ps.length; i++) { if (ps[i].pass) { k++; } }
    var words = { pairs: plural(R, 'chk.pairs', ps.length), pass: plural(R, 'chk.pass', k) };
    return C().renderText(fill(R.T['chk.summary'], words), { counts: { n: ps.length, k: k } }, R.lang, { escape: false }).html;
  }
  function check(R, pal) {
    var T = R.T, lang = R.lang, out = [], i, j, k, mode, hx, rows, p, a, b, table, dec, decHtml, ps = pal.pairs || [], DEC = ['decorative', 'advisory'];
    var hd = pal.modes.length > 1 ? 'h4' : 'h3';
    for (i = 0; i < pal.modes.length; i++) {
      mode = pal.modes[i]; hx = pal.roles[mode]; rows = [];
      for (j = 0; j < ps.length; j++) {
        p = ps[j];
        if (p.mode !== mode) { continue; }
        a = hx[p.fg]; b = hx[p.bg];
        rows.push('<tr class="' + (p.pass ? 'ok' : 'bad') + '"><td data-label="' + esc(T['th.pair']) + '">' + pairLabel(R, p) + ' ' +
          '<code>' + esc(p.fg) + '/' + esc(p.bg) + '</code></td>' +
          '<td data-label="' + esc(T['th.ratio']) + '">' + crTag(R, a, b) + pairNote(R, pal, mode, a, b) + '</td>' +
          '<td data-label="' + esc(T['th.min']) + '">' + X().fmtThreshold(p.min, lang) + ' ' +
          '<small>' + esc(fill(T.crit, { c: p.criterion })) + '</small></td>' +
          '<td data-label="' + esc(T['th.res']) + '"><span class="res">' + (p.pass ? T['res.pass'] : T['res.fail']) + '</span>' +
          '<details class="calc"><summary>' + esc(T.calc_l) + '</summary><p>' + calcLine(R, a, b) + '</p></details></td></tr>');
      }
      table = '';
      if (rows.length) {
        table = '<table class="report"><thead><tr><th scope="col">' + esc(T['th.pair']) + '</th><th scope="col">' + esc(T['th.ratio']) + '</th>' +
          '<th scope="col">' + esc(T['th.min']) + '</th><th scope="col">' + esc(T['th.res']) + '</th></tr></thead>' +
          '<tbody>' + rows.join('') + '</tbody></table>';
      }
      // „Nur dekorativ“ und „Nur als Hinweis“ (palette.advisory): Paare mit Wert, ohne Schwelle im Ergebnis; ohne Modus h3
      decHtml = '';
      for (k = 0; k < DEC.length; k++) {
        dec = [];
        for (j = 0; j < (pal[DEC[k]] || []).length; j++) { if (pal[DEC[k]][j].mode === mode) { dec.push(pal[DEC[k]][j]); } }
        if (dec.length) {
          decHtml += '<' + hd + '>' + esc(T[k ? 'adv_h' : 'decor_h']) + '</' + hd + '><ul class="plain">';
          for (j = 0; j < dec.length; j++) { decHtml += '<li>' + pairLabel(R, dec[j]) + ': ' + crTag(R, hx[dec[j].fg], hx[dec[j].bg]) + '</li>'; }
          decHtml += '</ul>';
        }
      }
      out.push('<div class="chk-mode" data-mode="' + mode + '">' + modeHead(R, pal, mode) + table + decHtml + '</div>');
    }
    var dist = pal.distinct || [];
    if (dist.length) {
      var names = roleIndex(R.task), items = [], d, line, c, val, refs = [];
      for (i = 0; i < dist.length; i++) {
        d = dist[i]; hx = pal.roles[d.mode];
        line = fill(T.distinct, { label: esc(label(R, 'distinct.' + d.id)),
          value: numTag(R, '{dist:' + hx[d.a] + '/' + hx[d.b] + '/' + d.kind + '}'),
          a: esc(inSentence(names[d.a]['name_' + lang], lang)), b: esc(inSentence(names[d.b]['name_' + lang], lang)), kind: esc(T['kind.' + d.kind]) });
        c = d.compare;
        if (c) {
          val = c.a && c.b && c.kind ? numTag(R, '{dist:' + c.a + '/' + c.b + '/' + c.kind + '}') : numTag(R, '{ref:' + c.id + '}');
          line += ' ' + fill(T['distinct.compare'], { name: esc(compareName(R, c.id)), value: val });
        }
        items.push('<li>' + modePrefix(R, pal, d.mode) + line + '</li>');
      }
      for (i = 0; i < R.comparisons.length; i++) {
        refs.push(esc(R.comparisons[i]['name_' + lang]) + ' ' + numTag(R, '{ref:' + R.comparisons[i].id + '}'));
      }
      out.push('<h3>' + esc(T.distinct_h) + '</h3><ul class="plain">' + items.join('') + '</ul>' +
        '<p class="muted">' + fill(T['distinct.refs'], { list: refs.join(' · ') }) + '</p>');
    }
    var fs = pal.findings || [];
    if (fs.length) {
      var fi = '';
      for (i = 0; i < fs.length; i++) {
        fi += '<li>' + modePrefix(R, pal, fs[i].mode) + renderCopy(R, label(R, 'finding.' + fs[i].id), pal, fs[i].mode || null) + '</li>';
      }
      out.push('<h3>' + esc(T.findings_h) + '</h3><ul class="plain">' + fi + '</ul>');
    }
    out.push('<h3>' + esc(T.not_checked_h) + '</h3><p>' + esc((R.task['not_checked_' + lang] || []).join(', ')) + '</p>');
    return out.join('');
  }

  // ---------- Block G
  function levelTags(R, obj) {
    var T = R.T, tags = ['<span class="tag-level">' + esc(T['level.' + obj.level]) + '</span>'];
    if (obj.strength) { tags.push('<span class="tag-sub">' + esc(T['strength.' + obj.strength]) + '</span>'); }
    if (obj.myth) { tags.push('<span class="tag-sub">' + esc(T.myth) + '</span>'); }
    if (obj.own) { tags.push('<span class="tag-sub">' + esc(T.own) + '</span>'); }
    return tags.join(' ');
  }
  function sourceLinks(R, obj) {
    var T = R.T, lang = R.lang, srcs = R.sources, inf = obj.informative || [], norm = obj.normative || [], first = norm.slice(), i, id, s, acc, parts = [];
    for (i = 0; i < (obj.sources || []).length; i++) {
      id = obj.sources[i];
      if (norm.indexOf(id) < 0 && inf.indexOf(id) < 0) { first.push(id); }
    }
    var all = first.concat(inf);
    for (i = 0; i < all.length; i++) {
      s = srcs[all[i]];
      if (!s) { continue; }
      acc = T['access.' + s.access];
      if (inf.indexOf(all[i]) >= 0) { acc = T.informative + ', ' + acc; }
      parts.push('<a href="' + esc(s.url) + '" rel="noopener"' + (s.short_lang && s.short_lang !== lang ? ' lang="' + esc(s.short_lang) + '"' : '') + '>' +
        esc(s['short_' + lang] || s.title) + '</a> <small>(' + esc(acc) + ')</small>');
    }
    return parts.length ? '<p class="src">' + esc(T.src_l) + ' ' + parts.join(' · ') + '</p>' : '';
  }
  function rules(R, pal) {
    var items = [], i, r, text;
    for (i = 0; i < R.rules.length; i++) {
      r = R.rules[i];
      if (!X().showIf(r.show_if || null, pal)) { continue; }
      text = codeSpans(C().renderText(r['text_' + R.lang], X().rctx(pal, null, null, { refs: R.refs, date: R.date }), R.lang, { escape: true }).html);
      items.push('<li class="rule" id="regel-' + esc(r.id) + '" data-rule="' + esc(r.id) + '"><div class="rule-h">' + levelTags(R, r) + '</div>' +
        '<p>' + text + '</p>' + sourceLinks(R, r) + '</li>');
    }
    return { n: items.length, html: '<ul class="rules">' + items.join('') + '</ul>' };
  }
  function rulesSum(R, n) { return C().renderText(R.T['rules.summary'], { counts: { n: n } }, R.lang, { escape: false }).html; }

  // ---------- Block D und E
  function demoVars(R, pal, mode, gen, toggles, sim) {
    var r = copyObj(pal.roles[mode]), k, v, out = '';
    if (gen && gen.viewVars) { v = gen.viewVars(pal, mode, toggles || {}); for (k in v) { if (has(v, k)) { r[k] = v[k]; } } }
    // view_vars dürfen auch Nicht-Farben liefern (etwa eine Deckkraft); simuliert werden nur Hex-Werte
    for (k in r) { if (has(r, k)) { out += '--d-' + k + ':' + (sim && sim !== 'normal' && /^#[0-9A-Fa-f]{6}$/.test(r[k]) ? C().simHex(r[k], sim) : r[k]) + ';'; } }
    return out;
  }
  function exportNote(R, pal, fmt) {
    var note = R.tc['fmt.' + fmt + '.note'] || R.T['fmt.' + fmt + '.note'];
    return note ? renderCopy(R, note, pal) : '';
  }
  function exportBlocks(R, task, pal, fmt, bl) {
    var T = R.T, out = [], i, b, pid, fname;
    for (i = 0; i < bl.length; i++) {
      b = bl[i]; pid = 'exp-' + fmt + '-' + i;
      fname = X().filename(task.id, pal.preset, fmt, b.suffix, formats(task), b.ext);
      out.push('<div class="exp-block">' + (b.label ? '<p class="exp-label">' + esc(b.label) + '</p>' : '') +
        '<pre class="code" id="' + pid + '" tabindex="0"' + (b.lang ? ' lang="' + b.lang + '"' : '') + '><code>' + esc(b.text) + '</code></pre>' +
        '<div class="exp-act"><button type="button" class="btn primary" data-copy-from="#' + pid + '">' + esc(T.copy) + '</button>' +
        '<button type="button" class="btn js-only" data-download="#' + pid + '" data-filename="' + esc(fname) + '" data-mime="' + X().mime(fmt, b.ext) + '">' + esc(T.download) + '</button>' +
        '<button type="button" class="btn js-only" data-wrap="#' + pid + '" aria-pressed="false">' + esc(T.wrap) + '</button></div>' +
        (b.note ? '<p class="exp-bnote">' + renderCopy(R, b.note, pal) + '</p>' : '') + '</div>');
    }
    return out.join('');
  }
  function formats(task) { return task.exports.visible.concat(task.exports.more || []); }

  // ---------- Zustand (2.3): c, p und Optionen in sprachneutralen Query-Parametern
  function seedParam(task) { return task.seed_param || 'c'; }
  function control(task, id) { for (var i = 0; i < task.controls.length; i++) { if (task.controls[i].id === id) { return task.controls[i]; } } return null; }
  function preset(task, id) { for (var i = 0; i < task.presets.length; i++) { if (task.presets[i].id === id) { return task.presets[i]; } } return null; }
  function isView(ctl) { return ctl.id === 'm' || ctl.view === true; }
  function caseOf(ctl, opts) { return ctl.by && ctl.cases ? ctl.cases[String(opts[ctl.by])] || null : null; }
  function field(ctl, opts, name) { var cs = caseOf(ctl, opts); return cs && has(cs, name) ? cs[name] : ctl[name]; }
  function normValue(ctl, v) {
    var p, i, out;
    if (ctl.type === 'color') { p = v ? C().parse(String(v), false) : null; return p ? p.hex : null; }
    if (ctl.type === 'colors') {
      if (!v) { return null; }
      out = [];
      for (i = 0; i < v.length; i++) { p = C().parse(String(v[i]), false); if (!p) { return null; } out.push(p.hex); }
      return out;
    }
    return v;
  }
  function baseOptions(task, pid) {
    var o = {}, i, ctl, pr = preset(task, pid), po = (pr && pr.options) || {}, cs, k;
    for (i = 0; i < task.controls.length; i++) { o[task.controls[i].id] = task.controls[i]['default']; }
    for (k in po) { if (has(po, k)) { o[k] = po[k]; } }
    for (i = 0; i < task.controls.length; i++) {
      ctl = task.controls[i]; cs = caseOf(ctl, o);
      if (cs && has(cs, 'default') && !has(po, ctl.id)) { o[ctl.id] = cs['default']; }
    }
    for (i = 0; i < task.controls.length; i++) { ctl = task.controls[i]; o[ctl.id] = normValue(ctl, o[ctl.id]); }
    return o;
  }
  function valid(ctl, v, opts) {
    var vals, lo, hi, st, i;
    if (ctl.type === 'chips') { vals = field(ctl, opts, 'values') || []; return vals.indexOf(v) >= 0; }
    if (ctl.type === 'toggle') { return v === true || v === false; }
    if (ctl.type === 'stepper') {
      lo = field(ctl, opts, 'min'); hi = field(ctl, opts, 'max'); st = field(ctl, opts, 'step') || 1;
      return typeof v === 'number' && v % 1 === 0 && v >= lo && v <= hi && (v - lo) % st === 0;
    }
    if (ctl.type === 'color') { return typeof v === 'string' && /^#[0-9A-F]{6}$/.test(v); }
    if (ctl.type === 'colors') {
      if (!v || v.length < 1 || v.length > (ctl.max || 4)) { return false; }
      for (i = 0; i < v.length; i++) { if (!/^#[0-9A-F]{6}$/.test(v[i])) { return false; } }
      return true;
    }
    if (ctl.type === 'text') { return typeof v === 'string' && v.length <= 200; }
    return false;
  }
  function decodeValue(ctl, s) {
    var p, parts, out, i;
    if (ctl.type === 'toggle') { return s === '1' ? true : s === '0' ? false : undefined; }
    if (ctl.type === 'stepper') { return /^-?[0-9]+$/.test(s) ? parseInt(s, 10) : undefined; }
    if (ctl.type === 'color') { p = C().parse(s); return p && p.alpha === 1 ? p.hex : undefined; }
    if (ctl.type === 'colors') {
      parts = s.split(','); out = [];
      for (i = 0; i < parts.length; i++) { p = C().parse(parts[i]); if (!p || p.alpha !== 1) { return undefined; } out.push(p.hex); }
      return out;
    }
    return s;
  }
  function encodeValue(ctl, v) {
    if (ctl.type === 'toggle') { return '1'; }
    if (ctl.type === 'stepper') { return String(v); }
    if (ctl.type === 'color') { return v.slice(1); }
    if (ctl.type === 'colors') { var out = [], i; for (i = 0; i < v.length; i++) { out.push(v[i].slice(1)); } return out.join(','); }
    return String(v);
  }
  function same(a, b) {
    if (a === b) { return true; }
    if (a && b && typeof a === 'object' && typeof b === 'object' && a.length === b.length) {
      for (var i = 0; i < a.length; i++) { if (a[i] !== b[i]) { return false; } }
      return true;
    }
    return false;
  }
  function parseQuery(search) {
    var out = [], parts = String(search || '').replace(/^\?/, '').split('&'), i, eq, k, v;
    for (i = 0; i < parts.length; i++) {
      if (!parts[i]) { continue; }
      eq = parts[i].indexOf('=');
      k = eq < 0 ? parts[i] : parts[i].slice(0, eq); v = eq < 0 ? '' : parts[i].slice(eq + 1);
      try { k = decodeURIComponent(k.replace(/\+/g, ' ')); v = decodeURIComponent(v.replace(/\+/g, ' ')); } catch (e) { out.bad = true; continue; }
      out.push([k, v]);
    }
    return out;
  }
  // URL → Zustand. Ungültiges fällt weg; dirty sagt, ob die URL bereinigt werden muss.
  function readState(task, search) {
    var q = parseQuery(search), st = { c: null, p: null, o: {}, t: {} }, seen = {}, dirty = !!q.bad, i, k, v, ctl, p, j, tg, alt = null;
    for (i = 0; i < q.length; i++) {
      k = q[i][0]; v = q[i][1];
      if (has(seen, k)) { dirty = true; continue; }
      seen[k] = true;
      if (k === seedParam(task)) { p = C().parse(v); if (p && p.alpha === 1) { st.c = p.hex; } else { dirty = true; } continue; }
      // Weiter-Links und Kacheln tragen c (2.3); mit eigenem seed_param (etwa sc) gilt c als Ersatz, die URL schreibt seed_param
      if (k === 'c') { p = C().parse(v); if (p && p.alpha === 1) { alt = p.hex; } dirty = true; continue; }
      if (k === 'p') { if (preset(task, v)) { st.p = v; } else { dirty = true; } continue; }
      ctl = control(task, k);
      if (ctl) { st.o[k] = decodeValue(ctl, v); continue; }
      tg = null;
      for (j = 0; j < (task.pattern_toggles || []).length; j++) { if (task.pattern_toggles[j].id === k) { tg = task.pattern_toggles[j]; } }
      if (tg && tg.values.indexOf(v) >= 0 && v !== tg['default']) { st.t[k] = v; continue; }
      dirty = true;
    }
    if (!st.c && alt) { st.c = alt; }
    // preset_control ohne c: Der Wert wählt seine Startpalette, wie beim Klick (2.3); er selbst fällt dann als Standard weg
    k = task.preset_control;
    if (k && !st.c && has(st.o, k) && preset(task, st.p || task.presets[0].id).options[k] !== st.o[k]) {
      for (j = 0; j < task.presets.length; j++) { if (task.presets[j].options[k] === st.o[k]) { st.p = task.presets[j].id; dirty = true; break; } }
    }
    // Vorschläge aus der eigenen Farbe (seed_control) gelten nur zusammen mit c
    if (task.seed_control && !st.c && has(st.o, task.seed_control)) { delete st.o[task.seed_control]; dirty = true; }
    // Optionen gegen die Basis der Startpalette prüfen; Standardwerte stehen nicht in der URL.
    var base = baseOptions(task, st.p || task.presets[0].id), eff = copyObj(base);
    for (k in st.o) { if (has(st.o, k)) { eff[k] = st.o[k]; } }
    for (i = 0; i < task.controls.length; i++) {
      ctl = task.controls[i];
      if (!has(st.o, ctl.id)) { continue; }
      if (st.o[ctl.id] === undefined || !valid(ctl, st.o[ctl.id], eff) || same(st.o[ctl.id], base[ctl.id])) {
        dirty = true;
        delete st.o[ctl.id];
        eff[ctl.id] = base[ctl.id];
      }
    }
    return { state: st, dirty: dirty };
  }
  // Zustand → Query (ohne „?“), feste Reihenfolge: Farbe, p, Steuerelemente, Muster-Schalter
  function writeState(task, st, forceP) {
    var out = [], i, ctl, tg;
    if (st.c) { out.push(seedParam(task) + '=' + st.c.slice(1)); }
    if (st.p || forceP) { out.push('p=' + encodeURIComponent(st.p || forceP)); }
    for (i = 0; i < task.controls.length; i++) {
      ctl = task.controls[i];
      if (has(st.o, ctl.id)) {
        if (ctl.type === 'toggle' && st.o[ctl.id] !== true) { out.push(ctl.id + '=0'); continue; }
        // Komma bleibt lesbar (f ist eine kommagetrennte Hex-Liste, 2.3)
        out.push(ctl.id + '=' + encodeURIComponent(encodeValue(ctl, st.o[ctl.id])).replace(/%2C/g, ','));
      }
    }
    for (i = 0; i < (task.pattern_toggles || []).length; i++) {
      tg = task.pattern_toggles[i];
      if (has(st.t || {}, tg.id)) { out.push(tg.id + '=' + encodeURIComponent(st.t[tg.id])); }
    }
    return out.join('&');
  }
  function effectiveOptions(task, st) {
    var pid = st.p || task.presets[0].id, eff = baseOptions(task, pid), k, i, ctl;
    for (k in st.o) { if (has(st.o, k)) { eff[k] = st.o[k]; } }
    var base = baseOptions(task, pid), cs;
    for (i = 0; i < task.controls.length; i++) {
      ctl = task.controls[i];
      if (valid(ctl, eff[ctl.id], eff)) { continue; }
      cs = caseOf(ctl, eff);
      eff[ctl.id] = cs && has(cs, 'default') ? cs['default'] : base[ctl.id];
    }
    return eff;
  }
  function isCustom(task, st) {
    if (st.c) { return true; }
    for (var k in st.o) { if (has(st.o, k) && control(task, k) && !isView(control(task, k))) { return true; } }
    return false;
  }
  // Ein gesetztes Steuerelement vom Typ colors liefert die Farben selbst und geht vor c und p (2.3: f vor c vor p)
  function colorsSet(task, st) {
    for (var i = 0; i < task.controls.length; i++) { if (task.controls[i].type === 'colors' && st.o[task.controls[i].id]) { return true; } }
    return false;
  }
  // Name eines eigenen Zustands: eigene Farben (colors), eigene Farbe (c), sonst „{Startpalette}, angepasst“. Hat der
  // Generator gen.displayName, steht statt der Startpalette, was die Palette zeigt (nach Z geändert, 5.0)
  function customNames(data, st, pal, gen) {
    var task = data.task, pr = preset(task, st.p || data.first), an = data.adjusted_names, nt = data.name_text, out = {}, l;
    if (colorsSet(task, st)) { return data.custom_names_colors; }
    if (st.c) { return data.custom_names; }
    for (l in an) { if (has(an, l)) { out[l] = fill(an[l], { palette: nt && gen.displayName ? gen.displayName(pal, nt[l], l) : pr['name_' + l] }); } }
    return out;
  }
  // Gedrückter Startpaletten-Chip: keiner, solange c oder ein colors-Steuerelement gilt (2.3)
  function pressedPreset(task, st, first) { return st.c || colorsSet(task, st) ? null : (st.p || first); }
  // Option setzen (ändert st). Mit preset_control und ohne c wählt der Wert die Startpalette. Optionen, die sie nicht
  // selbst in options festlegt und die für sie gültig sind, bleiben stehen, wie mit c (etwa bg, pr, mark bei charts).
  function setOptionState(task, st, id, v, first) {
    var base = baseOptions(task, st.p || first), i, np, nb, eff, keep, k, ctl;
    if (same(v, base[id])) { delete st.o[id]; } else { st.o[id] = v; }
    if (task.preset_control === id && !st.c) {
      for (i = 0; i < task.presets.length; i++) {
        np = task.presets[i];
        if (np.options[id] !== v) { continue; }
        nb = baseOptions(task, np.id); eff = copyObj(nb); keep = {};
        for (k in st.o) { if (has(st.o, k) && k !== id && control(task, k) && (isView(control(task, k)) || !has(np.options, k))) { eff[k] = st.o[k]; } }
        for (k in eff) {
          ctl = control(task, k);
          if (has(st.o, k) && k !== id && ctl && (isView(ctl) || !has(np.options, k)) && valid(ctl, st.o[k], eff) && !same(st.o[k], nb[k])) { keep[k] = st.o[k]; }
        }
        st.p = np.id; st.o = keep;
        break;
      }
      if (same(v, baseOptions(task, st.p || first)[id])) { delete st.o[id]; }
    }
    return st;
  }
  function makeInput(task, st) {
    var pr = preset(task, st.p || task.presets[0].id), i, cols = null;
    if (pr.colors) {
      cols = [];
      for (i = 0; i < pr.colors.length; i++) { cols.push({ value: C().parse(pr.colors[i].value, false).hex, role: pr.colors[i].role || null }); }
    }
    return { seed: st.c || (pr.seed ? C().parse(pr.seed, false).hex : null), colors: cols, options: effectiveOptions(task, st) };
  }
  function framePalette(task, pr, inp, pal, names) {
    pal.task = task.id;
    pal.preset = pr ? pr.id : null;
    pal.input = inp;
    pal.name_de = pr ? pr.name_de : names.de;
    pal.name_en = pr ? pr.name_en : names.en;
    return pal;
  }
  // Palette zum Zustand: Startpaletten kommen fertig aus dem Build, nur Eigenes wird gerechnet (9.13).
  function compute(data, st, gen, lang) {
    var task = data.task, pid = st.p || data.first;
    if (!isCustom(task, st)) { return { palette: data.palettes[pid], error: null, custom: false }; }
    var inp = makeInput(task, st);
    try {
      var pal = gen.build(task, inp, { datasets: data.datasets, comparisons: data.comparisons, lang: lang || null, data: data.data || {} });
      // Eigenes ist nie die Startpalette: preset null (Dateiname „eigen“, Quelle ohne Startpalette), Name nach customNames
      framePalette(task, null, inp, pal, customNames(data, st, pal, gen));
      return { palette: pal, error: null, custom: true };
    } catch (e) {
      return { palette: null, error: e && e.key ? e.key : 'error', custom: true };
    }
  }
  function today() {
    var d = new Date(), m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
  }
  function makeR(data) {
    return { lang: data.lang, T: data.frame, tc: data.text, task: data.task, refs: data.refs, date: data.date,
      sources: data.sources, rules: data.rules, comparisons: (data.comparisons || {}).comparisons || [] };
  }
  function exportCtx(data, pal, st, custom) {
    var vis = [], i;
    for (i = 0; i < data.rules.length; i++) { if (X().showIf(data.rules[i].show_if || null, pal)) { vis.push(data.rules[i]); } }
    // Startpaletten tragen p; Eigenes nur seinen Zustand. Unter einem colors-Steuerelement fällt p weg, wenn es nichts ändert.
    var task = data.task, p = st.p;
    if (p && colorsSet(task, st) && JSON.stringify(baseOptions(task, p)) === JSON.stringify(baseOptions(task, data.first))) { p = null; }
    var q = writeState(task, { c: st.c, p: p, o: st.o, t: {} }, custom ? null : (st.p || data.first));
    return { date: custom ? today() : data.date, url: data.url + (q ? '?' + q : ''), name: pal['name_' + data.lang],
      task_name: data.task['name_' + data.lang], core: data.core, text: data.text, rules: vis, sources: data.sources,
      refs: data.refs, datasets: data.datasets, data: data.data || {} };
  }
  function renderAll(data, pal, st, gen, opts) {
    var R = makeR(data), custom = isCustom(data.task, st), ectx = exportCtx(data, pal, st, custom), ex = {}, f, i, fm = formats(data.task), r = rules(R, pal);
    for (i = 0; i < fm.length; i++) {
      f = fm[i];
      ex[f] = { blocks: exportBlocks(R, data.task, pal, f, X().render(f, pal, data.task, ectx, data.lang, opts.exp || {}, gen)), note: exportNote(R, pal, f) };
    }
    return { strip: strips(R, pal), sum: summary(R, pal), notes: notes(R, pal, opts.error || null), roles: roles(R, pal), chkSum: checkSum(R, pal),
      chk: check(R, pal), rulesSum: rulesSum(R, r.n), rules: r.html, exports: ex };
  }

  // Sprachlink: Zwillingsseite plus kompletter Zustand und Sprungziel (2.3)
  function langHref(base, q, hash) { return base + (q ? '?' + q : '') + (hash || ''); }
  // „Weiter“-Links und Kacheln tragen nur die eigene Farbe (2.3)
  function carryHref(base, hex, param) { return base + (hex ? '?' + (param || 'c') + '=' + hex.slice(1) : ''); }
  // localStorage nur über diesen Umweg: gesperrter Speicher wirft nie (2.3, 11)
  function storage(win) {
    return {
      get: function (key) { try { return win.localStorage.getItem(key); } catch (e) { return null; } },
      set: function (key, value) {
        try { if (value === null) { win.localStorage.removeItem(key); } else { win.localStorage.setItem(key, value); } return true; } catch (e) { return false; }
      }
    };
  }
  // Die gespeicherte Farbe ist nur ein Vorschlag (Chip „Zuletzt genutzt“) und wird nie angewandt (9.14).
  function suggestion(store, stateC) {
    if (stateC) { return null; }
    var saved = store.get('farbsprache.color'), p = saved ? C().parse(saved, false) : null;
    return p && p.alpha === 1 ? p.hex : null;
  }

  FS.site = {
    fill: fill, label: label, langHref: langHref, carryHref: carryHref, storage: storage, suggestion: suggestion,
    render: { strips: strips, summary: summary, notes: notes, roles: roles, check: check, checkSum: checkSum, rules: rules, rulesSum: rulesSum,
      demoVars: demoVars, exportBlocks: exportBlocks, exportNote: exportNote, makeR: makeR, exportCtx: exportCtx, all: renderAll },
    state: { parse: parseQuery, read: readState, write: writeState, base: baseOptions, effective: effectiveOptions,
      isCustom: isCustom, input: makeInput, seedParam: seedParam, colorsSet: colorsSet, pressed: pressedPreset, option: setOptionState },
    framePalette: framePalette, compute: compute
  };

  // ---------- DOM-Anbindung
  if (typeof document === 'undefined' || !document.getElementById) { return; }
  var doc = document, win = root;
  var T = {};
  try { T = JSON.parse(doc.getElementById('i18n').textContent); } catch (e) { /* Seiten ohne Texte */ }
  function t(key) { return T[key] || key; }
  var status = doc.getElementById('status');
  function announce(text) {
    if (!status) { return; }
    status.textContent = '';
    setTimeout(function () { status.textContent = text; }, 30);
  }
  var LS = storage(win);
  function store(key, value) { LS.set(key, value); }
  function closest(el, sel) { return el && el.closest ? el.closest(sel) : null; }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  /* ---------- Kopieren und Speichern (Kette aus Designsprache) ---------- */
  function flash(button, ok, msg) {
    announce(msg);
    if (!button) { return; }
    var old = button.getAttribute('data-label') || button.innerHTML;
    button.setAttribute('data-label', old);
    if (!button.querySelector('svg')) { button.textContent = ok ? t('copied') : t('copyFailed'); }
    button.setAttribute('data-copied', '');
    setTimeout(function () { button.innerHTML = old; button.removeAttribute('data-copied'); }, 1600);
  }
  function selectPre(source) {
    if (!source || !win.getSelection) { return false; }
    var range = doc.createRange(); range.selectNodeContents(source);
    var sel = win.getSelection(); sel.removeAllRanges(); sel.addRange(range);
    return true;
  }
  function fallback(text) {
    var ta = doc.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0'; ta.style.top = '0';
    doc.body.appendChild(ta); ta.focus(); ta.select();
    var ok = false;
    try { ok = doc.activeElement === ta && doc.execCommand('copy'); } catch (e) { ok = false; }
    doc.body.removeChild(ta);
    return ok;
  }
  function copyText(text, button, source) {
    function done(ok) {
      if (!ok && source && selectPre(source)) { flash(button, false, t('selected')); return; }
      if (button) { try { button.focus({ preventScroll: true }); } catch (e) { /* alt */ } }
      flash(button, ok, ok ? t('copied') : t('copyFailed'));
    }
    if (win.navigator.clipboard && win.isSecureContext) {
      win.navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallback(text)); });
    } else { done(fallback(text)); }
  }
  function download(name, text, mime) {
    try {
      var blob = new win.Blob([text], { type: mime + ';charset=utf-8' }), url = win.URL.createObjectURL(blob), a = doc.createElement('a');
      a.href = url; a.download = name; doc.body.appendChild(a); a.click(); doc.body.removeChild(a);
      setTimeout(function () { win.URL.revokeObjectURL(url); }, 1000);
      announce(t('saved'));
    } catch (e) { announce(t('copyFailed')); }
  }
  doc.addEventListener('click', function (ev) {
    var b = closest(ev.target, '[data-copy],[data-copy-from],[data-download],[data-wrap]'), src;
    if (!b) { return; }
    if (b.hasAttribute('data-copy')) { copyText(b.getAttribute('data-copy'), b, null); return; }
    src = doc.querySelector(b.getAttribute('data-copy-from') || b.getAttribute('data-download') || b.getAttribute('data-wrap'));
    if (!src) { return; }
    if (b.hasAttribute('data-copy-from')) { copyText(src.textContent, b, src); }
    else if (b.hasAttribute('data-download')) { download(b.getAttribute('data-filename'), src.textContent, b.getAttribute('data-mime')); }
    else {
      var on = !src.classList.contains('wrap');
      src.classList.toggle('wrap', on); b.setAttribute('aria-pressed', String(on));
    }
  });

  /* ---------- Farbfeld (Startseite und Aufgabenseiten) ---------- */
  function colorField(onChange) {
    var input = doc.getElementById('seed');
    if (!input) { return null; }
    var pick = doc.getElementById('seed-pick'), err = doc.getElementById('seed-err'), note = doc.getElementById('seed-note');
    var reset = doc.querySelector('[data-seed-reset]'), last = doc.querySelector('[data-last]');
    function show(hex) {
      if (!last) { return; }
      var sug = suggestion(LS, hex);
      if (!sug) { last.hidden = true; return; }
      last.innerHTML = esc(t('lastUsed')).replace('{swatch}', '<span class="sw" style="background:' + sug + '"></span>').replace('{value}', '<code>' + sug + '</code>');
      last.setAttribute('data-hex', sug);
      last.hidden = false;
    }
    function read(fromPicker, quiet, debounced) {
      var s = input.value, p = s.replace(/\s/g, '') ? C().parse(s) : null, key = s.replace(/\s/g, '') ? C().parseError(s) : null;
      note.hidden = true;
      if (!s.replace(/\s/g, '')) { input.removeAttribute('aria-invalid'); err.textContent = ''; onChange(null, fromPicker, debounced); show(null); return; }
      if (!p) {
        input.setAttribute('aria-invalid', 'true');
        err.textContent = key === 'transparent' ? t('errTransparent') : t('errUnknown');
        return;
      }
      input.removeAttribute('aria-invalid'); err.textContent = '';
      var hex = p.alpha < 1 ? C().composite(p.hex, p.alpha, '#FFFFFF') : p.hex;
      if (p.alpha < 1) { note.textContent = t('alphaNote'); note.hidden = false; }
      else if (p.out_of_gamut) {
        note.textContent = fill(t('gamutNote'), { value: hex, d: C().fmtDist(p.mapped_distance || 0, doc.documentElement.lang === 'de' ? 'de' : 'en') });
        note.hidden = false;
      }
      if (pick && !fromPicker) { pick.value = hex.toLowerCase(); }
      if (!quiet) { store('farbsprache.color', hex); }
      onChange(hex, fromPicker, debounced);
      show(hex);
    }
    var timer;
    // Beim Tippen gilt eine Farbe nach 120 ms, wenn sie fertig aussieht. Kurzformen (#E63) und Unbekanntes warten auf
    // eine Pause von 800 ms oder das Verlassen des Felds; bis dahin steht kein Fehler da (nach Z geändert, 3.0)
    input.addEventListener('input', function () {
      var s = input.value.replace(/\s/g, ''), ok = !s || (C().parse(input.value) && !/^#?[0-9A-Fa-f]{3,4}$/.test(s));
      clearTimeout(timer);
      if (!ok) { input.removeAttribute('aria-invalid'); err.textContent = ''; }
      timer = setTimeout(function () { read(false, false, true); }, ok ? 120 : 800);
    });
    input.addEventListener('change', function () { clearTimeout(timer); read(false); });
    if (pick) { pick.addEventListener('input', function () { input.value = pick.value.toUpperCase(); read(true); }); }
    if (reset) { reset.addEventListener('click', function () { input.value = ''; read(false); }); }
    if (last) { last.addEventListener('click', function () { input.value = last.getAttribute('data-hex'); read(false); }); }
    // set (Startpalette gewählt, Feld geleert oder Farbe aus der URL) nimmt alte Hinweise und Fehler mit
    return { set: function (hex) { input.value = hex || ''; note.hidden = true; err.textContent = ''; input.removeAttribute('aria-invalid'); if (hex && pick) { pick.value = hex.toLowerCase(); } show(hex); }, show: show,
      // Farbe aus der URL übernehmen, ohne sie als eingegebene Farbe zu speichern (2.3)
      apply: function () { read(false, true); } };
  }

  /* ---------- Sprachlink und mitgenommene Farbe ---------- */
  function syncLangLink(query) {
    var link = doc.querySelector('.tb-lang a');
    if (!link) { return; }
    if (!link.getAttribute('data-base')) { link.setAttribute('data-base', link.getAttribute('href')); }
    link.setAttribute('href', langHref(link.getAttribute('data-base'), query, win.location.hash));
  }
  function carry(hex, param) {
    each(doc.querySelectorAll('[data-carry]'), function (a) {
      if (!a.getAttribute('data-base')) { a.setAttribute('data-base', a.getAttribute('href')); }
      a.setAttribute('href', carryHref(a.getAttribute('data-base'), hex, param));
    });
  }
  function replaceUrl(query) {
    try { win.history.replaceState(null, '', win.location.pathname + (query ? '?' + query : '') + win.location.hash); } catch (e) { /* file:// */ }
  }

  /* ---------- Startseite ---------- */
  var homeData = doc.getElementById('home-data');
  if (homeData) {
    var H = JSON.parse(homeData.textContent), lang0 = doc.documentElement.lang;
    var swatch = doc.getElementById('seed-swatch'), line = doc.getElementById('seed-line');
    var box = doc.querySelector('[data-home]'), said = null;
    var homeField = colorField(function (hex) {
      var c = hex || H.start;
      if (hex) { box.setAttribute('data-has-color', ''); } else { box.removeAttribute('data-has-color'); }
      swatch.style.background = c;
      var html = C().renderText(H.line, { roles: { 'default': { c: c } }, mode: 'default' }, lang0, { escape: false }).html;
      var key = C().contrast(c, '#FFFFFF') >= 4.5 ? 'use_white' : C().contrast(c, '#000000') >= 4.5 ? 'use_dark' : 'use_none';
      line.innerHTML = html + ' ' + H[key];
      carry(hex, 'c');
      syncLangLink(hex ? 'c=' + hex.slice(1) : '');
      replaceUrl(hex ? 'c=' + hex.slice(1) : '');
      if (hex && hex !== said) { announce(t('carried')); }
      said = hex;
    });
    var cq = readState({ controls: [], presets: [{ id: '_' }], pattern_toggles: [] }, win.location.search);
    if (homeField) {
      homeField.set(cq.state.c);
      if (cq.state.c) { homeField.apply(); }
      if (cq.dirty) { replaceUrl(cq.state.c ? 'c=' + cq.state.c.slice(1) : ''); }
    }
  }

  /* ---------- Aufgabenseite ---------- */
  var dataEl = doc.getElementById('task-data');
  if (!dataEl) { return; }
  var D = JSON.parse(dataEl.textContent);
  var task = D.task, lang = D.lang, gen = (FS.gen || {})[task.id] || (FS.gen || {})[D.gen];
  // ui/<aufgabe>.js lädt nach site.js (defer); der Haken wird deshalb erst beim Start gesucht
  function uiHook() { return (FS.ui || {})[task.id] || null; }
  var init = readState(task, win.location.search), st = init.state, sim = 'normal', expOpts = {}, toggles = {}, current = null, lastError = null;
  var wrapState = {};
  each(task.exports.options || [], function (o) { expOpts[o.id] = !!o['default']; });
  each(task.pattern_toggles || [], function (tg) { toggles[tg.id] = has(st.t, tg.id) ? st.t[tg.id] : tg['default']; });
  var taskRoot = doc.getElementById('task');

  function setHtml(id, html) { var el = doc.getElementById(id); if (el) { el.innerHTML = html; } }
  function query() { return writeState(task, st); }
  function syncUrl() { var q = query(); replaceUrl(q); syncLangLink(q); carry(st.c, 'c'); }

  function pressControls() {
    var eff = effectiveOptions(task, st), own = colorsSet(task, st);
    each(doc.querySelectorAll('[data-ctl]'), function (el) {
      var id = el.getAttribute('data-ctl'), ctl = control(task, id), v = eff[id], type = el.getAttribute('data-type');
      if (!ctl) { return; }
      if (type === 'chips') {
        var vals = field(ctl, eff, 'values') || [];
        each(el.querySelectorAll('[data-val]'), function (b) {
          var val = b.getAttribute('data-val');
          // Gelten eigene Farben (colors), ist auch kein Vorschlag aus der eigenen Farbe gewählt (2.3: f vor c vor p)
          b.setAttribute('aria-pressed', String(val === v && !(own && id === task.seed_control)));
          b.hidden = vals.indexOf(val) < 0;
        });
      } else if (type === 'toggle') { el.querySelector('button').setAttribute('aria-pressed', String(!!v)); }
      else if (type === 'stepper') {
        var inp = el.querySelector('input');
        inp.min = field(ctl, eff, 'min'); inp.max = field(ctl, eff, 'max'); inp.step = field(ctl, eff, 'step') || 1;
        if (doc.activeElement !== inp) { inp.value = v; }
      } else if (type === 'color') {
        var tx = el.querySelector('input[type="text"]'), pk = el.querySelector('input[type="color"]');
        if (doc.activeElement !== tx) { tx.value = v || ''; }
        if (pk) { if (v) { pk.value = v.toLowerCase(); pk.removeAttribute('data-empty'); } else { pk.setAttribute('data-empty', ''); } }
      } else if (type === 'colors') {
        each(el.querySelectorAll('input'), function (inp2, i) { if (doc.activeElement !== inp2) { inp2.value = v && v[i] ? v[i] : ''; } });
      } else if (type === 'text') { var it = el.querySelector('input'); if (doc.activeElement !== it) { it.value = v || ''; } }
    });
    var seedCtl = doc.querySelector('[data-seed-ctl]'), presetBox = doc.querySelector('.ctl-presets');
    if (seedCtl) { seedCtl.hidden = !st.c; if (presetBox) { presetBox.hidden = !!st.c; } }
    var shown = pressedPreset(task, st, D.first);
    each(doc.querySelectorAll('[data-preset]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-preset') === shown)); });
    if (taskRoot) { taskRoot.setAttribute('data-view', eff.m || 'all'); }
    each(doc.querySelectorAll('[data-toggle]'), function (el) {
      var id = el.getAttribute('data-toggle');
      each(el.querySelectorAll('[data-val]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-val') === toggles[id])); });
    });
    each(doc.querySelectorAll('[data-opt]'), function (b) { b.setAttribute('aria-pressed', String(!!expOpts[b.getAttribute('data-opt')])); });
    each(doc.querySelectorAll('[data-sim]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-sim') === sim)); });
  }
  function paintDemos() {
    if (!current) { return; }
    each(doc.querySelectorAll('[data-demo]'), function (el) {
      var mode = el.getAttribute('data-demo'), k;
      if (!current.roles[mode]) { return; }
      el.setAttribute('style', demoVars(makeR(D), current, mode, gen, toggles, sim));
      for (k in toggles) { if (has(toggles, k)) { el.setAttribute('data-' + k, toggles[k]); } }
    });
  }
  var lastNotes = null;
  // Zeile neben dem Hauptknopf und in der Kopierleiste: angepasste Werte einer eigenen Palette oder keine Lösung. Im
  // Fehlerzustand verbirgt site.css alles, was kopiert werden könnte (#task[data-error]); die Palette darunter ist nur
  // zum Vergleich da (nach Z geändert, 3.0 C)
  function palMsg(error) {
    var R = makeR(D), n = (current.changes || []).length, msg = error ? R.T['pal_msg.err'] : isCustom(task, st) && n ? fill(plural(R, 'pal_msg.chg', n), { n: C().fmtCount(n, lang) }) : '';
    each(doc.querySelectorAll('[data-pal-msg]'), function (a) { a.textContent = msg; a.hidden = !msg; });
    each(doc.querySelectorAll('.pal-cmp, .exp-err'), function (el) { el.hidden = !error; });
    var cmp = doc.querySelector('.pal-cmp');
    // Eigenes trägt keinen Startpalettennamen; die Farbe dazu sagt, welche Eingabe die Vergleichspalette ergab
    if (cmp) { cmp.textContent = fill(R.T['pal_msg.cmp'], { name: current['name_' + lang] + (!current.preset && current.input && current.input.seed ? ', ' + current.input.seed : '') }); }
    if (taskRoot) { if (error) { taskRoot.setAttribute('data-error', ''); } else { taskRoot.removeAttribute('data-error'); } }
    barVisible();
  }
  function paint(pal, error) {
    if (pal) { current = pal; }
    // Erster Lauf mit unlösbarem Zustand: Startpalette des Zustands zeigen, damit die Meldung solve.<key> erscheint
    if (!current) { current = D.palettes[st.p || D.first]; }
    var out = renderAll(D, current, st, gen, { exp: expOpts, error: error });
    setHtml('pal-strip', out.strip); setHtml('bar-strip', out.strip); setHtml('pal-sum', out.sum); setHtml('pal-roles', out.roles);
    if (out.notes !== lastNotes) { setHtml('pal-notes', out.notes); lastNotes = out.notes; }
    setHtml('chk-sum', out.chkSum); setHtml('chk', out.chk); setHtml('rules-sum', out.rulesSum); setHtml('rules', out.rules);
    each(formats(task), function (f) {
      setHtml('exp-' + f, out.exports[f].blocks); setHtml('exp-' + f + '-note', out.exports[f].note);
      each(doc.querySelectorAll('#exp-' + f + ' pre'), function (pre) {
        if (wrapState[pre.id]) { pre.classList.add('wrap'); var b = doc.querySelector('[data-wrap="#' + pre.id + '"]'); if (b) { b.setAttribute('aria-pressed', 'true'); } }
      });
    });
    paintDemos();
    palMsg(error);
    var ui = uiHook();
    if (ui && ui.render) { try { ui.render(current, st, api); } catch (e) { /* UI-Fehler bleiben lokal */ } }
  }
  var pending = null;
  function recompute(now) {
    clearTimeout(pending);
    function run() {
      var r = compute(D, st, gen, lang);
      lastError = r.error;
      paint(r.palette, r.error);
      if (r.custom && !r.error) {
        var n = (r.palette.changes || []).length;
        announce(n === 0 ? t('recomputed0') : n === 1 ? t('recomputed1') : fill(t('recomputed'), { n: String(n) }));
      }
    }
    if (now === true) { run(); return; }
    // 'frame': Die Eingabe war schon entprellt (Farbfeld), es zählt nur der nächste Frame (3.0)
    if (now) { (win.requestAnimationFrame || setTimeout)(run); return; }
    pending = setTimeout(function () { (win.requestAnimationFrame || setTimeout)(run); }, 120);
  }
  function changed(viewOnly) { pressControls(); syncUrl(); if (viewOnly) { paint(null, lastError); } else { recompute(false); } }
  function setOption(id, v) {
    var ctl = control(task, id);
    if (!ctl) { return; }
    setOptionState(task, st, id, v, D.first);
    changed(isView(ctl));
  }
  // Ungültige Farbe in einem Steuerelement: aria-invalid am Feld und Text in der Fehlerzeile (WCAG 3.3.1)
  function invalid(box, inp, on) {
    if (inp) { if (on) { inp.setAttribute('aria-invalid', 'true'); } else { inp.removeAttribute('aria-invalid'); } }
    var er = box.querySelector('.err');
    if (er) { er.textContent = on ? t('errUnknown') : ''; }
  }
  function keepView(o) { var r = {}, k; for (k in o) { if (has(o, k) && control(task, k) && isView(control(task, k))) { r[k] = o[k]; } } return r; }

  // Steuerelemente
  each(doc.querySelectorAll('[data-ctl]'), function (el) {
    var id = el.getAttribute('data-ctl'), type = el.getAttribute('data-type'), ctl = control(task, id);
    if (type === 'chips') {
      el.addEventListener('click', function (ev) { var b = closest(ev.target, '[data-val]'); if (b) { setOption(id, b.getAttribute('data-val')); } });
    } else if (type === 'toggle') {
      el.querySelector('button').addEventListener('click', function () { setOption(id, !effectiveOptions(task, st)[id]); });
    } else if (type === 'stepper') {
      var inp = el.querySelector('input');
      el.addEventListener('click', function (ev) {
        var b = closest(ev.target, '[data-step]'); if (!b) { return; }
        var eff = effectiveOptions(task, st), stp = field(ctl, eff, 'step') || 1, v = eff[id] + parseInt(b.getAttribute('data-step'), 10) * stp;
        if (valid(ctl, v, eff)) { setOption(id, v); }
      });
      inp.addEventListener('change', function () {
        var v = parseInt(inp.value, 10), eff = effectiveOptions(task, st);
        if (valid(ctl, v, eff)) { setOption(id, v); } else { inp.value = eff[id]; }
      });
    } else if (type === 'color') {
      var tx = el.querySelector('input[type="text"]'), pk = el.querySelector('input[type="color"]');
      tx.addEventListener('change', function () {
        if (!tx.value.replace(/\s/g, '')) { invalid(el, tx, false); setOption(id, baseOptions(task, st.p || D.first)[id]); return; }
        var p = C().parse(tx.value), ok = !!p && p.alpha === 1;
        invalid(el, tx, !ok);
        if (ok) { setOption(id, p.hex); }
      });
      tx.addEventListener('input', function () { invalid(el, tx, false); });
      if (pk) { pk.addEventListener('input', function () { setOption(id, pk.value.toUpperCase()); }); }
    } else if (type === 'colors') {
      el.addEventListener('change', function () {
        var vals = [], ok = true;
        each(el.querySelectorAll('input'), function (i2) {
          var p = i2.value.replace(/\s/g, '') ? C().parse(i2.value) : null, bad = !!i2.value.replace(/\s/g, '') && !(p && p.alpha === 1);
          if (bad) { ok = false; } else if (p) { vals.push(p.hex); }
          invalid(el, i2, bad);
        });
        // ein ungültiges Feld setzt die Fehlerzeile auch dann, wenn ein anderes gültig ist
        if (!ok) { invalid(el, null, true); }
        // alle Felder leer: zurück zum Standard (f fällt aus der URL)
        if (ok) { setOption(id, vals.length ? vals : baseOptions(task, st.p || D.first)[id]); }
      });
    } else if (type === 'text') {
      var ti = el.querySelector('input');
      ti.addEventListener('input', function () { if (valid(ctl, ti.value)) { setOption(id, ti.value); } });
    }
  });
  // Startpaletten: nur anzeigen, nicht rechnen
  each(doc.querySelectorAll('[data-preset]'), function (b) {
    b.addEventListener('click', function () {
      st.p = b.getAttribute('data-preset'); st.c = null; st.o = keepView(st.o);
      if (field_) { field_.set(null); }
      pressControls(); syncUrl(); recompute(true);
      announce(fill(t('presetShown'), { name: b.textContent }));
    });
  });
  // Simulation, Muster-Schalter, Export-Optionen, Reiter der Ansicht
  each(doc.querySelectorAll('[data-sim]'), function (b) {
    b.addEventListener('click', function () { sim = b.getAttribute('data-sim'); pressControls(); paintDemos(); });
  });
  each(doc.querySelectorAll('[data-toggle]'), function (el) {
    el.addEventListener('click', function (ev) {
      var b = closest(ev.target, '[data-val]'), id = el.getAttribute('data-toggle'), tg;
      if (!b) { return; }
      toggles[id] = b.getAttribute('data-val');
      each(task.pattern_toggles, function (x) { if (x.id === id) { tg = x; } });
      if (toggles[id] === tg['default']) { delete st.t[id]; } else { st.t[id] = toggles[id]; }
      pressControls(); syncUrl(); paintDemos();
    });
  });
  each(doc.querySelectorAll('[data-opt]'), function (b) {
    b.addEventListener('click', function () { var id = b.getAttribute('data-opt'); expOpts[id] = !expOpts[id]; pressControls(); paint(null, lastError); });
  });
  each(doc.querySelectorAll('[data-demo-tab]'), function (b) {
    b.addEventListener('click', function () {
      var box = doc.getElementById('demos');
      box.setAttribute('data-tab', b.getAttribute('data-demo-tab'));
      each(doc.querySelectorAll('[data-demo-tab]'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
    });
  });
  // Reiter der Exporte (Pfeiltasten wie eine Tabliste)
  var tabs = doc.querySelectorAll('[role="tab"][data-tab]');
  function selectTab(tab, focus) {
    each(tabs, function (x) {
      var on = x === tab;
      x.setAttribute('aria-selected', String(on));
      if (on) { x.removeAttribute('tabindex'); } else { x.setAttribute('tabindex', '-1'); }
      var panel = doc.getElementById(x.getAttribute('aria-controls'));
      if (panel) { panel.classList.toggle('on', on); }
    });
    if (focus) { tab.focus(); }
  }
  each(tabs, function (tab, i) {
    tab.addEventListener('click', function () { selectTab(tab, false); });
    tab.addEventListener('keydown', function (ev) {
      var d = ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0;
      if (!d) { return; }
      ev.preventDefault();
      selectTab(tabs[(i + d + tabs.length) % tabs.length], true);
    });
  });
  // Wrap-Zustand merken, wenn Exporte neu gerendert werden
  doc.addEventListener('click', function (ev) {
    var b = closest(ev.target, '[data-wrap]');
    if (b) { wrapState[b.getAttribute('data-wrap').slice(1)] = b.getAttribute('aria-pressed') === 'true'; }
  });

  // Kopierleiste: weg bei offener Tastatur und solange „Kopieren“ zu sehen ist; ab 1000 px auch, solange die Zeile mit dem
  // Hauptknopf (im Fehlerzustand mit der Meldung) ganz zu sehen ist (nach Z geändert, 3.0). Ist sie da, hält
  // scroll-padding-bottom den Fokus über ihr (WCAG 2.4.11).
  var copybar = doc.getElementById('copybar'), copySec = doc.getElementById('kopieren'), mainBtn = doc.querySelector('.pal-act');
  // mainSeen beginnt wahr: ohne IntersectionObserver bleibt die Leiste ab 1000 px weg, mit ihm blitzt sie beim Laden nicht auf
  var typing = false, inView = false, mainSeen = true;
  function barVisible() {
    if (!copybar) { return; }
    var wide = win.matchMedia ? win.matchMedia('(min-width:1000px)').matches : false;
    copybar.hidden = typing || inView || (wide && mainSeen);
    doc.documentElement.style.setProperty('scroll-padding-bottom', copybar.hidden ? '0px' : copybar.offsetHeight + 'px');
  }
  if (copybar) {
    doc.addEventListener('focusin', function (ev) { var el = ev.target; typing = !!(el && el.tagName === 'INPUT' && /^(text|number|search)$/.test(el.type)) || !!(el && el.tagName === 'TEXTAREA'); barVisible(); });
    doc.addEventListener('focusout', function () { typing = false; setTimeout(barVisible, 50); });
    if (win.IntersectionObserver && copySec) {
      new win.IntersectionObserver(function (entries) { inView = entries[0].isIntersecting; barVisible(); }).observe(copySec);
      if (mainBtn) { new win.IntersectionObserver(function (entries) { mainSeen = entries[0].intersectionRatio > 0.99; barVisible(); }, { threshold: [0, 1] }).observe(mainBtn); }
    }
    win.addEventListener('resize', barVisible);
    barVisible();
  }

  // API für die UI-Haken der Pakete (FS.ui[<aufgabe>])
  var api = {
    lang: lang, task: task, data: D,
    slot: function (name) { return doc.querySelector('[data-slot="' + name + '"]'); },
    state: function () { return st; }, palette: function () { return current; },
    set: setOption, recompute: function () { recompute(true); }, announce: announce
  };

  // Farbfeld anbinden und ersten Zustand anzeigen. Die gespeicherte Farbe erscheint nur als Vorschlag.
  var field_ = colorField(function (hex, fromPicker, debounced) {
    if (hex === st.c) { return; }
    st.c = hex;
    if (!hex && task.seed_control) { delete st.o[task.seed_control]; }
    // Ohne c wählt der Wert von preset_control wieder seine Startpalette (2.3 „Zurücksetzen“), wie beim Wechsel
    if (!hex && task.preset_control && has(st.o, task.preset_control)) { setOptionState(task, st, task.preset_control, st.o[task.preset_control], D.first); }
    pressControls(); syncUrl(); recompute(debounced ? 'frame' : false);
  });
  if (field_) { field_.set(st.c); }
  if (init.dirty) { replaceUrl(query()); }
  pressControls(); syncLangLink(query()); carry(st.c, 'c');
  function start() {
    var ui = uiHook();
    if (ui && ui.init) { try { ui.init(api); } catch (e) { /* UI-Fehler bleiben lokal */ } }
    if (isCustom(task, st) || st.p || JSON.stringify(st.t) !== '{}') { recompute(true); }
    else { current = D.palettes[D.first]; paintDemos(); if (ui && ui.render) { try { ui.render(current, st, api); } catch (e) { /* UI-Fehler bleiben lokal */ } } }
  }
  if (doc.readyState === 'complete') { start(); } else { doc.addEventListener('DOMContentLoaded', start); }
}(typeof globalThis !== 'undefined' ? globalThis : this));
