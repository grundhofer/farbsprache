/* Generische Export-Renderer von Farbsprache (FS.export): CSS, Tailwind v4, DTCG, Hex-Liste,
   Prompt für Coding-Agenten, Begründung. Rein, ohne DOM. Spiegel von tools/export.py.
   Die Ausgabe ist Byte für Byte gleich (tests/export.test.cjs). */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.export = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }

  var EXT = { css: 'css', tailwind: 'css', dtcg: 'tokens.json', hex: 'txt', agent: 'md', rationale: 'txt',
    html: 'html', js: 'js', scrim: 'css', values: 'txt', factsheet: 'md', prompt: 'txt', report: 'md', json: 'json' };
  var MIME = { css: 'text/css', json: 'application/json', md: 'text/markdown', txt: 'text/plain',
    js: 'text/javascript', html: 'text/html', 'tokens.json': 'application/design-tokens+json' };
  var NS = 'io.github.grundhofer.farbsprache';

  // ---------- Hilfen (auch vom Seitenrahmen genutzt)
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function pad(s, n) { while (s.length < n) { s += ' '; } return s; }
  function padStart(s, n, c) { while (s.length < n) { s = c + s; } return s; }
  function unesc(s) {
    return s.replace(/&(amp|lt|gt|quot|#x27);/g, function (m, k) {
      return { amp: '&', lt: '<', gt: '>', quot: '"', '#x27': "'" }[k];
    });
  }
  function presub(t, ctx) {
    return t.split('{palette}').join(ctx.name || '').split('{task}').join(ctx.task_name || '')
      .split('{date_iso}').join(ctx.date || '').split('{url}').join(ctx.url || '');
  }
  function plain(template, rc, lang) {
    var out = C().renderText(template, rc, lang, { escape: true }).html;
    return unesc(out.replace(/<[^>]*>/g, ''));
  }
  function rctx(palette, mode, extra, ctx) {
    var roles = {}, m, k;
    for (m in palette.roles) {
      if (has(palette.roles, m)) {
        roles[m] = {};
        for (k in palette.roles[m]) { if (has(palette.roles[m], k)) { roles[m][k] = palette.roles[m][k]; } }
      }
    }
    if (extra && mode) { for (k in extra) { if (has(extra, k)) { roles[mode][k] = extra[k]; } } }
    var r = { roles: roles, mode: mode || null };
    if (ctx && ctx.refs !== undefined && ctx.refs !== null) { r.refs = ctx.refs; }
    if (ctx && ctx.date) { r.date = ctx.date; }
    return r;
  }
  function fixed(n, d, lang) {
    var sep = lang === 'de' ? ',' : '.';
    var s = String(Math.abs(n));
    if (d) { s = padStart(s, d + 1, '0'); s = s.slice(0, s.length - d) + sep + s.slice(s.length - d); }
    return (n < 0 ? '-' : '') + s;
  }
  function dec(n, d) {
    var s = fixed(n, d, 'en');
    if (s.indexOf('.') >= 0) { s = s.replace(/0+$/, '').replace(/\.$/, ''); }
    return s;
  }
  function fmtThreshold(x, lang) {
    return dec(Math.floor(x * 100 + 0.5), 2).replace('.', lang === 'de' ? ',' : '.') + ':1';
  }
  function ratio2(x, lang, threshold) {
    var s = C().fmtRatio(x, lang, threshold === undefined ? null : threshold);
    return s.slice(0, s.length - 2);
  }
  function roleDefs(task, palette, mode, opts) {
    opts = opts || {};
    var have = palette.roles[mode] || {}, out = [], i, r;
    for (i = 0; i < task.roles.length; i++) {
      r = task.roles[i];
      if (has(have, r.id) && (!r.export_option || opts[r.export_option])) { out.push(r); }
    }
    return out;
  }
  function cssName(r) { return r.css_name || r.id; }
  // Rollen-ID → Exportname: Paare in Prompt und DTCG nennen dieselben Namen wie die Tokens
  function cssNames(task) { var o = {}, i; for (i = 0; i < task.roles.length; i++) { o[task.roles[i].id] = cssName(task.roles[i]); } return o; }
  function commentSafe(s) { return s.split('*/').join('* /'); }
  function modeWord(ctx, mode) { return has(ctx.core, 'mode.' + mode) ? ctx.core['mode.' + mode] : mode; }

  function showValue(cond, palette, mode) {
    var roles = palette.roles[mode] || {}, m = cond.metric, i, n, k;
    function col(x) {
      if (x === undefined || x === null) { return null; }
      if (x.charAt(0) === '#') { return C().normHex(x); }
      return has(roles, x) ? roles[x] : null;
    }
    if (m === 'finding') {
      var fs = palette.findings || [];
      for (i = 0; i < fs.length; i++) {
        if (fs[i].id === cond.a && (fs[i].mode === null || fs[i].mode === undefined || fs[i].mode === mode)) { return true; }
      }
      return false;
    }
    if (m === 'count') {
      var pre = cond.a || '';
      n = 0;
      for (k in roles) { if (has(roles, k) && k.indexOf(pre) === 0) { n++; } }
      return n;
    }
    var a = col(cond.a), b = col(cond.b);
    if (a === null || b === null) { return null; }
    if (m === 'cr') { return C().contrast(a, b); }
    if (m === 'dist') { return C().distance(a, b, cond.kind || 'normal'); }
    if (m === 'gs') { return C().grayDistance(a, b); }
    throw new Error('show_if: unbekannte Kennzahl ' + m);
  }
  function showIf(cond, palette) {
    if (!cond) { return true; }
    var modes = cond.mode ? [cond.mode] : palette.modes, i, v, op, x;
    for (i = 0; i < modes.length; i++) {
      v = showValue(cond, palette, modes[i]);
      if (v === null) { continue; }
      if (cond.metric === 'finding') { if (v) { return true; } continue; }
      op = cond.op || '>='; x = cond.value;
      if ((op === '<' && v < x) || (op === '>=' && v >= x)) { return true; }
    }
    return false;
  }
  function blocks(x) {
    if (typeof x === 'string') { return [{ label: null, text: x, suffix: '', lang: null, note: null, ext: null }]; }
    var out = [], i;
    for (i = 0; i < x.length; i++) {
      out.push({ label: x[i].label || null, text: x[i].text, suffix: x[i].suffix || '', lang: x[i].lang || null, note: x[i].note || null, ext: x[i].ext || null });
    }
    return out;
  }
  function notices(palette, ctx, task, opts) {
    var spec = (palette.extra || {}).datasets || [], ids = [], out = [], i, j, t, d, k, inc, rs, hit;
    if (Object.prototype.toString.call(spec) === '[object Array]') { ids = spec.slice(); } else {
      inc = null;
      if (task) {
        inc = {};
        for (i = 0; i < palette.modes.length; i++) { rs = roleDefs(task, palette, palette.modes[i], opts); for (j = 0; j < rs.length; j++) { inc[rs[j].id] = true; } }
      }
      for (k in spec) {
        if (!has(spec, k)) { continue; }
        hit = inc === null || !spec[k] || !spec[k].length;
        for (j = 0; !hit && j < spec[k].length; j++) { if (inc[spec[k][j]]) { hit = true; } }
        if (hit) { ids.push(k); }
      }
    }
    for (i = 0; i < ids.length; i++) {
      t = has(ctx.core, 'notice.' + ids[i]) ? ctx.core['notice.' + ids[i]] : null;
      if (t === null) {
        d = (ctx.datasets || {})[ids[i]] || {};
        t = d.required_notice || d.attribution || null;
      }
      if (t && out.indexOf(t) < 0) { out.push(t); }
    }
    return out;
  }
  function header(ctx, mode) {
    var t = presub(ctx.core[mode ? 'header_mode' : 'header'], ctx);
    return mode ? t.split('{mode}').join(modeWord(ctx, mode)) : t;
  }

  // ---------- CSS
  function cssBody(palette, task, ctx, lang, opts) {
    var modes = palette.modes, lines = [], width = 0, per = [], i, j, rs, ind, r, hx, ok, use, note;
    for (i = 0; i < modes.length; i++) {
      rs = roleDefs(task, palette, modes[i], opts);
      per.push([modes[i], rs]);
      for (j = 0; j < rs.length; j++) { width = Math.max(width, cssName(rs[j]).length + 3); }
    }
    for (i = 0; i < per.length; i++) {
      ind = i === 0 ? '  ' : '    ';
      if (i === 0) { lines.push(':root {'); } else {
        lines.push('@media (prefers-color-scheme: ' + per[i][0] + ') {');
        lines.push('  :root {');
      }
      if (per[i][0] === 'light' || per[i][0] === 'dark') { lines.push(ind + 'color-scheme: ' + per[i][0] + ';'); }
      rs = per[i][1];
      for (j = 0; j < rs.length; j++) {
        r = rs[j];
        hx = palette.roles[per[i][0]][r.id];
        ok = C().shortestOklch(hx);
        use = r['use_' + lang];
        note = ok ? ok + ' · ' + use : use;
        lines.push(ind + pad('--' + cssName(r) + ':', width + 1) + hx + '; /* ' + commentSafe(note) + ' */');
      }
      lines.push(i === 0 ? '}' : '  }');
      if (i) { lines.push('}'); }
    }
    return lines;
  }
  function css(palette, task, ctx, lang, opts, noHeader) {
    var lines = [], head, i;
    if (!noHeader) {
      head = [header(ctx), ctx.core.css_checked].concat(notices(palette, ctx, task, opts), [presub(ctx.core.link, ctx)]);
      lines.push('/* ' + commentSafe(head[0]));
      for (i = 1; i < head.length; i++) { lines.push('   ' + commentSafe(head[i])); }
      lines[lines.length - 1] += ' */';
    }
    return lines.concat(cssBody(palette, task, ctx, lang, opts)).join('\n');
  }

  // ---------- Tailwind v4
  // Rollenfamilie für die Zeilen im Tailwind-Export (Spiegel von export._stem)
  function stem(name) {
    var s = name.indexOf('on-') === 0 ? name.slice(3) : name, t;
    for (;;) { t = s.replace(/-(subtle|strong|muted|text|light|dark|[0-9]+)$/, ''); if (t === s) { return s; } s = t; }
  }
  function sameLine(prev, r) { return stem(cssName(prev)) === stem(cssName(r)) || (prev.kind === 'surface' && r.kind === 'surface'); }
  function tailwind(palette, task, ctx, lang, opts) {
    var core = ctx.core, prefix = { surface: 'bg-', text: 'text-', ui: 'border-', decor: 'border-', data: 'bg-' };
    var first = roleDefs(task, palette, palette.modes[0], opts), ex = [], i, j;
    for (i = 0; i < first.length && ex.length < 5; i++) {
      if (first[i].core) { ex.push((prefix[first[i].kind] || 'bg-') + cssName(first[i])); }
    }
    var head = [header(ctx), core.tw_line, core.tw_line2.split('{examples}').join(ex.join(', '))].concat(notices(palette, ctx, task, opts));
    head.push(presub(core.link, ctx));
    var lines = ['/* ' + commentSafe(head[0])];
    for (i = 1; i < head.length; i++) { lines.push('   ' + commentSafe(head[i])); }
    lines[lines.length - 1] += ' */';
    lines.push('@import "tailwindcss";');
    lines.push('');
    var names = [], seen = [], rs, ind, cur, last, r;
    for (i = 0; i < palette.modes.length; i++) {
      rs = roleDefs(task, palette, palette.modes[i], opts);
      seen.push({});
      ind = i === 0 ? '  ' : '    ';
      if (i === 0) { lines.push(':root {'); } else {
        lines.push('@media (prefers-color-scheme: ' + palette.modes[i] + ') {');
        lines.push('  :root {');
      }
      cur = []; last = null;
      for (j = 0; j < rs.length; j++) {
        r = rs[j];
        if (cur.length && !sameLine(last, r)) { lines.push(ind + cur.join(' ')); cur = []; }
        cur.push('--' + cssName(r) + ': ' + palette.roles[palette.modes[i]][r.id] + ';');
        last = r;
        seen[i][cssName(r)] = 1;
        if (names.indexOf(cssName(r)) < 0) { names.push(cssName(r)); }
      }
      if (cur.length) { lines.push(ind + cur.join(' ')); }
      lines.push(i === 0 ? '}' : '  }');
      if (i) { lines.push('}'); }
    }
    lines.push('');
    lines.push('@theme inline {');
    // Utilities nur für Rollen, die jeder Modus definiert
    for (i = 0; i < names.length; i++) {
      for (j = 0; j < seen.length; j++) { if (!seen[j][names[i]]) { break; } }
      if (j === seen.length) { lines.push('  --color-' + names[i] + ': var(--' + names[i] + ');'); }
    }
    lines.push('}');
    return lines.join('\n');
  }

  // ---------- Design-Tokens nach DTCG 2025.10
  function component(b) { return dec(Math.floor((2 * b * 10000 + 255) / 510), 4); }
  function js(s) { return JSON.stringify(s); }
  // Kontrast für JSON: abgeschnitten wie fmtRatio (auch die Schwellenregel), Punkt, ohne Endnullen
  function ratioJson(x, threshold) {
    var s = ratio2(x, 'en', threshold);
    return s.indexOf('.') >= 0 ? s.replace(/0+$/, '').replace(/\.$/, '') : s;
  }
  function pairObj(p, withMin, nm) {
    var s = '{"fg": ' + js(nm[p.fg]) + ', "bg": ' + js(nm[p.bg]) + ', "ratio": ' + ratioJson(p.ratio, withMin ? p.min : null);
    if (withMin) { s += ', "min": ' + dec(Math.floor(p.min * 100 + 0.5), 2) + ', "criterion": ' + js(p.criterion); }
    return s + '}';
  }
  function list(items, ind) {
    if (!items.length) { return '[]'; }
    if (items.length === 1) { return '[' + items[0] + ']'; }
    var parts = [], i;
    for (i = 0; i < items.length; i++) { parts.push(ind + '  ' + items[i]); }
    return '[\n' + parts.join(',\n') + '\n' + ind + ']';
  }
  function dtcg(palette, task, ctx, lang, opts) {
    var out = [], core = ctx.core, mi, mode, rs, desc, width, toks, i, r, hx, comp, pairs, decor, ext, ns, text, nm = cssNames(task);
    for (mi = 0; mi < palette.modes.length; mi++) {
      mode = palette.modes[mi];
      rs = roleDefs(task, palette, mode, opts);
      desc = (mode === 'light' || mode === 'dark' ? header(ctx, mode) : header(ctx)) + ' · ' + ctx.url;
      width = 0;
      for (i = 0; i < rs.length; i++) { width = Math.max(width, js(cssName(rs[i])).length + 1); }
      toks = [];
      for (i = 0; i < rs.length; i++) {
        r = rs[i]; hx = palette.roles[mode][r.id];
        comp = [component(parseInt(hx.slice(1, 3), 16)), component(parseInt(hx.slice(3, 5), 16)), component(parseInt(hx.slice(5, 7), 16))].join(', ');
        toks.push('    ' + pad(js(cssName(r)) + ':', width + 1) + '{"$type": "color", "$value": {"colorSpace": "srgb", "components": [' +
          comp + '], "alpha": 1, "hex": ' + js(hx) + '}, "$description": ' + js(r['use_' + lang]) + '}');
      }
      pairs = []; decor = [];
      for (i = 0; i < (palette.pairs || []).length; i++) { if (palette.pairs[i].mode === mode) { pairs.push(pairObj(palette.pairs[i], true, nm)); } }
      for (i = 0; i < (palette.decorative || []).length; i++) { if (palette.decorative[i].mode === mode) { decor.push(pairObj(palette.decorative[i], false, nm)); } }
      ext = ['      "standard": ' + js(core.dtcg_standard)];
      ns = notices(palette, ctx, task, opts);
      for (i = 0; i < ns.length; i++) { ext.push('      "notice": ' + js(ns[i])); }
      ext.push('      "pairs": ' + list(pairs, '      '));
      ext.push('      "decorative": ' + list(decor, '      '));
      text = '{\n  "$description": ' + js(desc) + ',\n  "color": {\n' + toks.join(',\n') + '\n  },\n' +
        '  "$extensions": {\n    ' + js(NS) + ': {\n' + ext.join(',\n') + '\n    }\n  }\n}';
      out.push({ label: palette.modes.length > 1 ? (core['label.' + mode] || null) : null, text: text,
        suffix: mode === 'light' || mode === 'dark' ? '-' + mode : '', lang: null });
    }
    return out;
  }

  // ---------- Hex-Liste
  function hexList(palette, task, ctx, lang, opts) {
    var parts = [], mi, mode, rs, width, i, rows;
    for (mi = 0; mi < palette.modes.length; mi++) {
      mode = palette.modes[mi];
      rs = roleDefs(task, palette, mode, opts);
      width = 0;
      for (i = 0; i < rs.length; i++) { width = Math.max(width, cssName(rs[i]).length); }
      width += 2;
      rows = [mode === 'light' || mode === 'dark' ? header(ctx, mode) : header(ctx)];
      for (i = 0; i < rs.length; i++) { rows.push(pad(cssName(rs[i]), width) + palette.roles[mode][rs[i].id] + '  ' + rs[i]['use_' + lang]); }
      parts.push(rows.join('\n'));
    }
    var tail = notices(palette, ctx, task, opts).concat([presub(ctx.core.link, ctx)]);
    return parts.join('\n\n') + '\n\n' + tail.join('\n');
  }

  // ---------- Prompt für Coding-Agenten
  function joinAnd(items, core) { return items.length === 1 ? items[0] : items.slice(0, -1).join(', ') + ' ' + core.and + ' ' + items[items.length - 1]; }
  // Normquellen derselben Norm zusammengefasst (Spiegel von export._norm_list): „WCAG 2.2, 2.4.7 und 1.4.11“
  function normList(shorts, core) {
    var groups = {}, order = [], out = [], i, s, cut, key;
    for (i = 0; i < shorts.length; i++) {
      s = shorts[i]; cut = s.lastIndexOf(', ');
      key = (cut >= 0 ? 'g' : 'n') + '\u0000' + (cut >= 0 ? s.slice(0, cut) : s);
      if (!has(groups, key)) { groups[key] = []; order.push(key); }
      if (cut >= 0) { groups[key].push(s.slice(cut + 2)); }
    }
    for (i = 0; i < order.length; i++) {
      out.push(order[i].charAt(0) === 'g' ? order[i].slice(2) + ', ' + joinAnd(groups[order[i]], core) : order[i].slice(2));
    }
    return out.join('; ');
  }
  function levelNote(rule, ctx, lang) {
    var core = ctx.core, srcs = ctx.sources || {}, t = core['level.' + rule.level], i, parts;
    function short(id) { var s = srcs[id] || {}; return s['short_' + lang] || s.title || id; }
    if (rule.level === 'norm') {
      parts = [];
      for (i = 0; i < (rule.normative || []).length; i++) { parts.push(short(rule.normative[i])); }
      t += ': ' + normList(parts, core);
      var inf = rule.informative || [];
      if (inf.length) {
        parts = [];
        for (i = 0; i < inf.length; i++) { parts.push(short(inf[i]) + ', ' + core.informative); }
        t += '; ' + parts.join('; ');
      }
    } else if (rule.level === 'research' && rule.strength) {
      t += ', ' + core['strength.' + rule.strength];
    }
    if (rule.own) { t += ', ' + core.own; }
    return '(' + t + ')';
  }
  function findingText(f, palette, task, ctx, lang) {
    var t = plain(presub(ctx.text['finding.' + f.id], ctx), rctx(palette, f.mode || null, null, ctx), lang);
    if (f.mode && palette.modes.length > 1) { t = ctx.core['label.' + f.mode] + ': ' + t; }
    return t;
  }
  function pairGroups(palette, task, mode) {
    var lines = {}, i, j, line, p, g, key, groups = {}, order = [], out = [];
    for (i = 0; i < (task.pairs || []).length; i++) {
      line = task.pairs[i];
      if (!has(lines, line.fg)) { lines[line.fg] = []; }
      lines[line.fg].push(line);
    }
    for (i = 0; i < (palette.pairs || []).length; i++) {
      p = palette.pairs[i];
      if (p.mode !== mode) { continue; }
      g = null;
      var ls = has(lines, p.fg) ? lines[p.fg] : [];
      for (j = 0; j < ls.length; j++) {
        if (ls[j].on.indexOf(p.bg) >= 0 && ls[j].rule === p.rule) { g = ls[j].group || null; break; }
      }
      key = (g || p.criterion) + '\u0000' + p.min;
      if (!has(groups, key)) { groups[key] = { key: g || p.criterion, min: p.min, pairs: [] }; order.push(key); }
      groups[key].pairs.push(p);
    }
    for (i = 0; i < order.length; i++) { out.push(groups[order[i]]); groups[order[i]].i = i; }
    // strengere Schwelle zuerst, sonst Reihenfolge des Schemas (Index als Gleichstandsregel, egal wie stabil sort ist)
    out.sort(function (a, b) { return b.min - a.min || a.i - b.i; });
    for (i = 0; i < out.length; i++) { delete out[i].i; }
    return out;
  }
  function groupLabel(key, ctx) {
    return ctx.text['pairs.group.' + key] || ctx.core['pairs.group.' + key] || key;
  }
  function agent(palette, task, ctx, lang, opts) {
    var core = ctx.core, text = ctx.text, out, i, j, k, mode, gs, items, decs, rules, fs, checks, src, nm = cssNames(task), L = [['decorative', 'agent_decor'], ['advisory', 'agent_adv']], d;
    out = [core.agent_intro, '', '# ' + presub(text['agent.title'], ctx), '', core.h_idea,
      plain(presub(text['agent.idea'], ctx), rctx(palette, palette.modes[0], null, ctx), lang), '',
      core.h_tokens, '```css'];
    out = out.concat(cssBody(palette, task, ctx, lang, opts));
    out = out.concat(['```', '', core.h_pairs, core.agent_pairs_intro]);
    for (i = 0; i < palette.modes.length; i++) {
      mode = palette.modes[i];
      out.push('');
      if (palette.modes.length > 1) { out.push(core['label.' + mode]); }
      gs = pairGroups(palette, task, mode);
      for (j = 0; j < gs.length; j++) {
        items = [];
        for (k = 0; k < gs[j].pairs.length; k++) {
          d = gs[j].pairs[k];
          items.push(nm[d.fg] + '/' + nm[d.bg] + ' ' + ratio2(d.ratio, lang, d.min));
        }
        out.push('- ' + core.agent_group.split('{label}').join(groupLabel(gs[j].key, ctx)).split('{min}').join(fmtThreshold(gs[j].min, lang)) + ' ' + items.join(' · '));
      }
      // Dekorative Paare und Hinweispaare (palette.advisory, etwa Datenfarben als Flächen) mit ihrem Wert
      for (k = 0; k < L.length; k++) {
        decs = [];
        for (j = 0; j < (palette[L[k][0]] || []).length; j++) {
          d = palette[L[k][0]][j];
          if (d.mode === mode) { decs.push(nm[d.fg] + '/' + nm[d.bg] + ' ' + ratio2(d.ratio, lang, d.min)); }
        }
        if (decs.length) { out.push('- ' + core[L[k][1]] + ' ' + decs.join(' · ')); }
      }
    }
    out = out.concat(['', core.agent_pairs_end, '', core.h_rules]);
    rules = ctx.rules || [];
    for (i = 0; i < rules.length; i++) {
      out.push('- ' + plain(presub(rules[i]['text_' + lang], ctx), rctx(palette, null, null, ctx), lang) + ' ' + levelNote(rules[i], ctx, lang));
    }
    out = out.concat(['', core.h_weak]);
    fs = palette.findings || [];
    if (fs.length) { for (i = 0; i < fs.length; i++) { out.push('- ' + findingText(fs[i], palette, task, ctx, lang)); } }
    else { out.push('- ' + core.agent_weak_none); }
    out = out.concat(['', core.h_avoid]);
    for (i = 0; i < text['agent.avoid'].length; i++) { out.push('- ' + plain(presub(text['agent.avoid'][i], ctx), rctx(palette, null, null, ctx), lang)); }
    out = out.concat(['', core.h_check]);
    checks = core.agent_checks_before.concat(text['agent.checks'], core.agent_checks_after);
    for (i = 0; i < checks.length; i++) { out.push('- ' + plain(presub(checks[i], ctx), rctx(palette, null, null, ctx), lang)); }
    out = out.concat(['', core.h_tip, plain(presub(text['agent.tip'], ctx), rctx(palette, null, null, ctx), lang), '', '---']);
    src = core[palette.preset === null || palette.preset === undefined ? 'agent_source_custom' : 'agent_source'];
    out.push(presub(src, ctx));
    out = out.concat(notices(palette, ctx, task, opts));
    return out.join('\n');
  }

  // ---------- Begründung
  function rationale(palette, task, ctx, lang, opts) {
    var parts = [], list_ = ctx.text.rationale, i, e;
    for (i = 0; i < list_.length; i++) {
      e = list_[i];
      if (e !== null && typeof e === 'object') {
        if (!showIf(e.show_if || null, palette)) { continue; }
        e = e.text;
      }
      parts.push(plain(presub(e, ctx), rctx(palette, null, null, ctx), lang));
    }
    parts.push(presub(ctx.core.rationale_end, ctx));
    return parts.concat(notices(palette, ctx, task, opts)).join(' ');
  }

  var RENDERERS = { css: css, tailwind: tailwind, dtcg: dtcg, hex: hexList, agent: agent, rationale: rationale };
  function renderer(fmt, gen) {
    var ex = (gen && gen.exports) || {};
    if (has(ex, fmt)) { return ex[fmt]; }
    if (has(RENDERERS, fmt)) { return RENDERERS[fmt]; }
    throw new Error('kein Renderer für das Format ' + fmt);
  }
  function render(fmt, palette, task, ctx, lang, opts, gen) {
    return blocks(renderer(fmt, gen)(palette, task, ctx, lang, opts || {}));
  }
  // Hat ein anderes Format aus fmts (alle Formate der Aufgabe) dieselbe Endung, steht das Format im Namen (Spiegel von export.filename)
  function filename(taskId, preset, fmt, suffix, fmts, xt) {
    var ext = xt || EXT[fmt] || 'txt', part = '', i;
    for (i = 0; i < (fmts || []).length; i++) { if (fmts[i] !== fmt && (EXT[fmts[i]] || 'txt') === ext) { part = '-' + fmt; } }
    return 'farbsprache-' + taskId + '-' + (preset || 'eigen') + part + (suffix || '') + '.' + ext;
  }
  function mime(fmt, xt) {
    var ext = xt || EXT[fmt] || 'txt';
    return MIME[ext] || MIME[ext.split('.').pop()] || 'text/plain';
  }

  return {
    FORMATS: ['css', 'tailwind', 'dtcg', 'hex', 'agent', 'rationale'], NS: NS,
    css: css, tailwind: tailwind, dtcg: dtcg, hex: hexList, agent: agent, rationale: rationale,
    render: render, renderer: renderer, blocks: blocks, filename: filename, mime: mime,
    unesc: unesc, presub: presub, plain: plain, rctx: rctx, fixed: fixed, dec: dec, fmtThreshold: fmtThreshold,
    ratio2: ratio2, roleDefs: roleDefs, cssName: cssName, cssNames: cssNames, showIf: showIf, levelNote: levelNote,
    header: header, notices: notices, commentSafe: commentSafe, modeWord: modeWord,
    findingText: findingText, pairGroups: pairGroups, groupLabel: groupLabel, pad: pad
  };
}));
