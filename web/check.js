/* Farbsprache – Palette prüfen (FS.check): Scanner, Rollen, Befund-Engine, Reparatur, Ansicht und Exporte.
   Rein, ohne DOM. Spiegel von tools/check.py (Spezifikation 3.8, 4.9, 5.8); tests/check.test.cjs vergleicht
   beide Seiten. Jede Zahl kommt aus FS.color (Formatierer und Platzhalter). */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.check = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  function NAMES() { return root.FS_CONST.css_names; }
  function has(o, k) { return o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k); }
  function esc(s) { return C().esc(s); }
  function copyObj(o) { var r = {}, k; for (k in o) { if (has(o, k)) { r[k] = o[k]; } } return r; }

  var SEVS = ['fail', 'check', 'note'];
  var SYM = { fail: '■', check: '▲', note: '●', pass: '✓' };
  var KINDS_SIM = ['normal', 'gray', 'deutan', 'protan', 'tritan'];
  var KINDS_DIST = ['normal', 'deutan', 'protan', 'tritan', 'gray'];
  var CTXS = ['light', 'dark'];
  var COMMENT = /\/\*[\s\S]*?\*\//g;
  var WS1 = /[ \t\r\n\f]/;
  var HSLCH = /^-?[0-9]*\.?[0-9]+(deg)?[ \t]+[0-9]*\.?[0-9]+%[ \t]+[0-9]*\.?[0-9]+%$/;
  var VAR = /^var\([ \t]*--([A-Za-z0-9_-]+)[ \t]*(,[^)]*)?\)$/;
  var IDENT = /[A-Za-z0-9_-]/;
  var COPY_ICON = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">' +
    '<path d="M5 1h9v11H5z M2 4h2v1H3v9h8v-1h1v2H2z" fill="currentColor"/></svg>';

  // Trimmen per Schleife statt per Regex (bei langen Leerraumfolgen sonst quadratisch)
  function trim(s) { var a = 0, b = s.length; while (a < b && WS1.test(s.charAt(a))) { a++; } while (b > a && WS1.test(s.charAt(b - 1))) { b--; } return s.slice(a, b); }
  function identBefore(text, i) { return i > 0 && IDENT.test(text.charAt(i - 1)); }
  function identAfter(text, i) { return i < text.length && IDENT.test(text.charAt(i)); }
  function spaces(n) { var s = ''; while (s.length < n) { s += ' '; } return s; }
  function ljust(s, w) { return s.length >= w ? s : s + spaces(w - s.length); }
  function hex2(n) { var s = n.toString(16).toUpperCase(); return s.length < 2 ? '0' + s : s; }

  // ---------- Scanner (4.9)
  function blocks(text) {
    var out = [], stack = [], last = 0, i, ch, top;
    for (i = 0; i < text.length; i++) {
      ch = text.charAt(i);
      if (ch === '{') { stack.push([i, trim(text.slice(last, i))]); last = i + 1; }
      else if (ch === '}') {
        if (stack.length) { top = stack.pop(); out.push([top[0], i, top[1]]); }
        last = i + 1;
      } else if (ch === ';') { last = i + 1; }
    }
    for (i = 0; i < stack.length; i++) { out.push([stack[i][0], text.length, stack[i][1]]); }
    return out;
  }
  function ctxAt(pos, bl, dark) {
    var i, j;
    for (i = 0; i < bl.length; i++) {
      if (bl[i][0] < pos && pos < bl[i][1]) {
        for (j = 0; j < dark.length; j++) { if (dark[j].test(bl[i][2])) { return 'dark'; } }
      }
    }
    return 'light';
  }
  function parseValue(v) {
    var p = C().parse(v, false);
    if (p === null && HSLCH.test(v)) { p = C().parse('hsl(' + v + ')', false); }
    return p;
  }
  function scan(text, cfg) {
    text = typeof text === 'string' ? text : '';
    var clean = text.replace(COMMENT, function (m) { return spaces(m.length); });
    var dark = [], i, j, m, re, bl, found = [], taken = [], notes = [], decls = [], byCtx = {}, d, p, mv, ref, toks = [];
    for (i = 0; i < cfg.dark_contexts.length; i++) { dark.push(new RegExp(cfg.dark_contexts[i], 'i')); }
    bl = blocks(clean);
    re = /(^|[ \t\r\n\f{;])(--[A-Za-z0-9_-]+)[ \t\r\n\f]*:[ \t\r\n\f]*([^;{}]*)/g;
    while ((m = re.exec(clean)) !== null) {
      var start = m.index + m[1].length, end = m.index + m[0].length, vs = end - m[3].length;
      var val = trim(m[3]);
      if (/!important$/i.test(val)) { val = trim(val.slice(0, -10)); }
      decls.push({ name: m[2].slice(2), val: val, vs: vs, ve: vs + val.length, ctx: ctxAt(start, bl, dark), start: start });
      taken.push([start, end]);
    }
    for (i = 0; i < decls.length; i++) { byCtx[decls[i].ctx + '\u0000' + decls[i].name] = decls[i]; }
    for (i = 0; i < decls.length; i++) {
      d = decls[i];
      if (!d.val) { continue; }
      p = parseValue(d.val);
      if (p === null) {
        mv = VAR.exec(d.val);
        if (mv === null) { continue; }
        ref = byCtx[d.ctx + '\u0000' + mv[1]];
        p = ref && !VAR.test(ref.val || '') ? parseValue(ref.val) : null;
        if (p === null) { notes.push({ key: 'var', name: d.name, ref: mv[1] }); continue; }
      }
      found.push({ pos: d.start, p: p, raw: d.val, name: d.name, span: [d.vs, d.ve], ctx: d.ctx });
    }
    function free(s, e) {
      for (var k = 0; k < taken.length; k++) { if (s < taken[k][1] && e > taken[k][0]) { return false; } }
      return true;
    }
    re = /#[0-9A-Fa-f]{3,8}(?![0-9A-Za-z_-])/g;
    while ((m = re.exec(clean)) !== null) {
      if (!identBefore(clean, m.index) && (m.index === 0 || clean.charAt(m.index - 1) !== '&')) { toks.push([m.index, m.index + m[0].length]); }
    }
    re = /(rgba?|hsla?|oklch|oklab|color)\([^()]*\)/gi;
    while ((m = re.exec(clean)) !== null) { if (!identBefore(clean, m.index)) { toks.push([m.index, m.index + m[0].length]); } }
    re = /[A-Za-z]+/g;
    while ((m = re.exec(clean)) !== null) {
      if (has(NAMES(), m[0].toLowerCase()) && !identBefore(clean, m.index) && !identAfter(clean, m.index + m[0].length)) {
        toks.push([m.index, m.index + m[0].length]);
      }
    }
    toks.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    var lastEnd = -1;
    for (i = 0; i < toks.length; i++) {
      if (toks[i][0] < lastEnd || !free(toks[i][0], toks[i][1])) { continue; }
      p = C().parse(clean.slice(toks[i][0], toks[i][1]), false);
      if (p === null) { continue; }
      lastEnd = toks[i][1];
      found.push({ pos: toks[i][0], p: p, raw: text.slice(toks[i][0], toks[i][1]), name: null, span: [toks[i][0], toks[i][1]], ctx: ctxAt(toks[i][0], bl, dark) });
    }
    found.sort(function (a, b) { return a.pos - b.pos; });
    var colors = { light: [], dark: [] }, dropped = { light: 0, dark: 0 }, f, lst, hit;
    for (i = 0; i < found.length; i++) {
      f = found[i]; lst = colors[f.ctx]; p = f.p; hit = null;
      for (j = 0; j < lst.length; j++) { if (lst[j].hex === p.hex && lst[j].alpha === p.alpha) { hit = lst[j]; break; } }
      if (hit === null) {
        if (lst.length >= cfg.max_colors) { dropped[f.ctx] += 1; continue; }
        hit = { hex: p.hex, alpha: p.alpha, oog: !!p.out_of_gamut, md: p.mapped_distance === undefined ? null : p.mapped_distance,
          raw: f.raw, names: [], spans: [], ctx: f.ctx };
        lst.push(hit);
      }
      if (f.name && hit.names.indexOf(f.name) < 0) { hit.names.push(f.name); }
      hit.spans.push(f.span);
    }
    for (i = 0; i < CTXS.length; i++) { if (dropped[CTXS[i]]) { notes.push({ key: 'dropped', ctx: CTXS[i], n: dropped[CTXS[i]] }); } }
    return { colors: colors.light.concat(colors.dark), notes: notes };
  }

  // Name in einem Block eindeutig: der zweite „surface-b“, der dritte „surface-c“ (trifft kein Rollenmuster, anders als „text-2“)
  function uniq(nm, used) { var s = nm, k = 0; while (has(used, s)) { s = nm + '-' + 'bcdefghijklmnopqrstuvwxyz'.charAt(k++); } used[s] = 1; return s; }
  function stateText(f, r) {
    if (!r) { return f.join(' '); }
    var out = { light: [], dark: [] }, used = { light: {}, dark: {} }, i, tok, ctx, role, parts = [];
    for (i = 0; i < f.length; i++) {
      tok = i < r.length ? r[i] : '-';
      ctx = /\.d$/.test(tok) ? 'dark' : 'light';
      role = /\.d$/.test(tok) ? tok.slice(0, -2) : tok;
      out[ctx].push('  ' + (role !== '-' ? '--' + uniq(role, used[ctx]) + ': ' : '') + f[i] + ';');
    }
    if (out.light.length) { parts.push(':root {\n' + out.light.join('\n') + '\n}'); }
    if (out.dark.length) { parts.push('.dark {\n' + out.dark.join('\n') + '\n}'); }
    return parts.join('\n');
  }
  // Rollen aus r und ob sie bestätigt sind; nur „-“ heißt: r trägt allein den Kontext
  function stateRoles(r) {
    var roles = [], any = false, i, t;
    if (!r) { return { roles: null, confirmed: false }; }
    for (i = 0; i < r.length; i++) {
      t = /\.d$/.test(r[i]) ? r[i].slice(0, -2) : r[i];
      roles.push(t === '-' ? null : t);
      if (t !== '-') { any = true; }
    }
    return any ? { roles: roles, confirmed: true } : { roles: null, confirmed: false };
  }

  // ---------- Rollen
  function guessRoles(colors, cfg) {
    var rx = [], i, j, k, n, b, pre = cfg.name_prefix, best = [], out = [], g, ri, win;
    for (i = 0; i < cfg.roles.length; i++) {
      rx.push([]);
      for (j = 0; j < cfg.roles[i].patterns.length; j++) { rx[i].push(new RegExp(cfg.roles[i].patterns[j])); }
    }
    for (g = 0; g < colors.length; g++) {
      b = null;
      for (k = 0; k < colors[g].names.length; k++) {
        n = colors[g].names[k].toLowerCase();
        if (n.indexOf(pre) === 0) { n = n.slice(pre.length); }
        for (ri = 0; ri < rx.length; ri++) {
          for (j = 0; j < rx[ri].length; j++) {
            if (rx[ri][j].test(n) && (b === null || j < b[0] || (j === b[0] && ri < b[1]))) { b = [j, ri]; }
          }
        }
      }
      best.push(b); out.push(null);
    }
    for (i = 0; i < CTXS.length; i++) {
      for (ri = 0; ri < cfg.roles.length; ri++) {
        win = null;
        for (g = 0; g < colors.length; g++) {
          if (colors[g].ctx === CTXS[i] && best[g] !== null && best[g][1] === ri) {
            if (win === null || best[g][0] < best[win][0]) { win = g; }
          }
        }
        if (win !== null) { out[win] = cfg.roles[ri].id; }
      }
    }
    return out;
  }

  // ---------- Bewertung
  function roleDef(cfg, rid) { for (var i = 0; i < cfg.roles.length; i++) { if (cfg.roles[i].id === rid) { return cfg.roles[i]; } } return null; }
  function findingDef(cfg, fid) { for (var i = 0; i < cfg.findings.length; i++) { if (cfg.findings[i].id === fid) { return cfg.findings[i]; } } return null; }
  function contrastItems(m, cfg, cx) {
    var cols = m.colors, idx = cx.idx, bg = cx.bg, items = [], i, j, k, pr, fgs, ons, os, g;
    function ofRole(rid) {
      if (rid === 'bg') { return [bg]; }
      var r = [];
      for (var q = 0; q < idx.length; q++) { if (cols[idx[q]].role === rid) { r.push(idx[q]); } }
      return r;
    }
    if (cx.roles_mode) {
      for (i = 0; i < cfg.pairs.length; i++) {
        pr = cfg.pairs[i]; fgs = ofRole(pr.fg);
        for (j = 0; j < fgs.length; j++) {
          g = fgs[j];
          if (g === bg) { continue; }
          ons = [];
          for (k = 0; k < pr.on.length; k++) {
            os = ofRole(pr.on[k]);
            for (var q = 0; q < os.length; q++) { if (os[q] !== g && ons.indexOf(os[q]) < 0) { ons.push(os[q]); } }
          }
          if (ons.length) { items.push({ id: pr.finding, i: g, on: ons, min: pr.min, firm: pr.firm, cond: has(pr, 'cond') ? pr.cond : null, role: pr.fg }); }
        }
      }
    }
    for (i = 0; i < idx.length; i++) {
      g = idx[i];
      if (g === bg || (cx.roles_mode && cols[g].role !== null)) { continue; }
      items.push({ id: 'check-text', i: g, on: [bg], min: cfg.free_text_min, firm: false, cond: 'free', role: null });
      items.push({ id: 'check-nontext', i: g, on: [bg], min: cfg.free_nontext_min, firm: false, cond: 'free', role: null });
    }
    return items;
  }
  function measure(item, hexes) {
    var worst = null, wi = null, r, k;
    for (k = 0; k < item.on.length; k++) {
      r = C().contrast(hexes[item.i], hexes[item.on[k]]);
      if (worst === null || r < worst - 1e-12) { worst = r; wi = item.on[k]; }
    }
    return [worst, wi];
  }
  function values(items, hexes) { var out = [], i; for (i = 0; i < items.length; i++) { out.push(measure(items[i], hexes)[0]); } return out; }
  // schlechter: vorher erfüllt und danach verfehlt, oder schon verfehlt und der Wert sinkt weiter
  function worse(it, b, a) { return (b >= it.min && a < it.min) || (b < it.min && a < b - 1e-12); }
  function metric(fid, a, b) {
    if (fid === 'check-duplicates') { return C().distance(a, b, 'normal'); }
    if (fid === 'check-gray') { return C().grayDistance(a, b); }
    return C().worstDistance(a, b, C().WORST_KINDS);
  }
  // Vergleichswert um 1e-9 abgesenkt: Okabe-Ito liegt nie „unter“ dem eigenen Wert, auch bei Unterschieden im letzten Bit
  function target(fid, cfg, refs) { return (fid === 'check-cvd' ? refs[cfg.compare].value : C().JND_DISTANCE) - 1e-9; }
  function repairContrast(it, hexes) {
    var a = hexes[it.i], o = C().hexToOklch(a), ya = C().relLum(a), against = [], all = true, any = false, k, dir, r;
    for (k = 0; k < it.on.length; k++) {
      against.push(hexes[it.on[k]]);
      if (C().relLum(hexes[it.on[k]]) >= ya) { any = true; } else { all = false; }
    }
    dir = all ? -1 : !any ? 1 : 0;
    if (dir === 0) { return { i: it.i, from: a, to: null }; }
    try { r = C().solveL(o[1], o[2], against, it.min, dir, o[0]); } catch (e) {
      if (e instanceof C().SolveError) { return { i: it.i, from: a, to: null }; }
      throw e;
    }
    return { i: it.i, from: a, to: r.hex };
  }
  // Kandidaten der Abstands-Reparatur für eine Farbe (gleiches C und h, L im Raster), je Analyse einmal gerechnet
  function grid(orig, cfg, cache) {
    if (!has(cache, orig)) {
      var o = C().hexToOklch(orig), g = cfg.repair_grid, out = [], k;
      for (k = g.from; k <= g.to; k++) { out.push(C().oklchToHex(k / g.div, o[1], o[2])); }
      cache[orig] = out;
    }
    return cache[orig];
  }
  function repairDistance(fid, g1, g2, cfg, refs, items, hexes, members, cache) {
    var ya = C().relLum(hexes[g1]), yb = C().relLum(hexes[g2]), mv = ya > yb ? g1 : g2, other = ya > yb ? g2 : g1;
    // nur Prüfungen, an denen die verschobene Farbe beteiligt ist, können sich ändern
    var own = [], q;
    for (q = 0; q < items.length; q++) { if (items[q].i === mv || items[q].on.indexOf(mv) >= 0) { own.push(items[q]); } }
    items = own;
    var orig = hexes[mv], tgt = target(fid, cfg, refs), before = values(items, hexes), cands = grid(orig, cfg, cache);
    var near = [], i, k, cand, best = null, bestD = null, trial, after, bad, key, d;
    for (i = 0; i < members.length; i++) {
      if (members[i] !== mv && members[i] !== other) { near.push([members[i], metric(fid, orig, hexes[members[i]]) >= tgt]); }
    }
    for (k = 0; k < cands.length; k++) {
      cand = cands[k];
      bad = cand === orig;
      for (key in hexes) { if (has(hexes, key) && Number(key) !== mv && hexes[key] === cand) { bad = true; } }
      if (bad || metric(fid, cand, hexes[other]) < tgt) { continue; }
      trial = copyObj(hexes); trial[mv] = cand;
      after = values(items, trial);
      for (i = 0; i < before.length; i++) { if (worse(items[i], before[i], after[i])) { bad = true; } }
      for (i = 0; i < near.length; i++) { if (near[i][1] && metric(fid, cand, hexes[near[i][0]]) < tgt) { bad = true; } }
      if (bad) { continue; }
      d = C().distance(orig, cand, 'normal');
      if (best === null || d < bestD - 1e-12) { best = cand; bestD = d; }
    }
    return { i: mv, from: orig, to: best, other: other };
  }
  function overWhite(c) { return c.alpha >= 1 ? c.hex : C().composite(c.hex, c.alpha, '#FFFFFF'); }

  function analyze(sc, cfg, refs, state) {
    state = state || {};
    var raw = sc.colors, n = raw.length, roles = has(state, 'roles') ? state.roles : null, guessed = guessRoles(raw, cfg);
    if (roles === undefined) { roles = null; }
    var confirmed = !!state.confirmed && roles !== null, cols = [], g, c2, i, k, hn = roles !== null;
    for (g = 0; g < n; g++) {
      c2 = copyObj(raw[g]);
      if (roles !== null) { c2.role = g < roles.length ? roles[g] : null; c2.role_src = confirmed ? 'confirmed' : 'user'; }
      else { c2.role = guessed[g]; c2.role_src = 'guess'; }
      if (raw[g].names.length) { hn = true; }
      cols.push(c2);
    }
    var m = { colors: cols, ctxs: [], confirmed: confirmed, notes: (sc.notes || []).slice(), has_names: hn };
    var bgi = has(state, 'bgi') ? state.bgi : null, ci, ctx, idx, cx, bg, c, o, hexes, items, findings, passes, it, r, rec, twin;
    for (ci = 0; ci < CTXS.length; ci++) {
      ctx = CTXS[ci]; idx = [];
      for (g = 0; g < n; g++) { if (cols[g].ctx === ctx) { idx.push(g); } }
      if (!idx.length) { continue; }
      cx = { ctx: ctx, idx: idx, roles_mode: false };
      for (i = 0; i < idx.length; i++) { if (cols[idx[i]].role) { cx.roles_mode = true; } }
      bg = null;
      if (typeof bgi === 'number' && idx.indexOf(bgi) >= 0) { bg = bgi; }
      if (bg === null) { for (i = 0; i < idx.length; i++) { if (cols[idx[i]].role === 'bg') { bg = idx[i]; break; } } }
      if (bg === null) {
        for (i = 0; i < idx.length; i++) {
          var y = C().relLum(overWhite(cols[idx[i]]));
          if (bg === null || (ctx === 'dark' && y < C().relLum(overWhite(cols[bg])) - 1e-12) ||
            (ctx !== 'dark' && y > C().relLum(overWhite(cols[bg])) + 1e-12)) { bg = idx[i]; }
        }
      }
      cx.bg = bg;
      var bgEff = overWhite(cols[bg]);
      hexes = {};
      for (i = 0; i < idx.length; i++) {
        c = cols[idx[i]];
        c.eff = idx[i] === bg ? bgEff : (c.alpha >= 1 ? c.hex : C().composite(c.hex, c.alpha, bgEff));
        o = C().hexToOklch(c.eff);
        c.chroma = o[1];
        c.oklch = C().shortestOklch(c.eff);
        c.best = C().contrast(c.eff, '#FFFFFF') >= C().contrast(c.eff, '#000000') ? '#FFFFFF' : '#000000';
        hexes[idx[i]] = c.eff;
      }
      items = contrastItems(m, cfg, cx); findings = []; passes = [];
      for (k = 0; k < items.length; k++) {
        it = items[k];
        if (it.id === 'check-nontext' && it.cond === 'free') {
          twin = null;
          for (i = 0; i < items.length; i++) { if (items[i].id === 'check-text' && items[i].i === it.i && items[i].cond === 'free') { twin = items[i]; break; } }
          if (measure(twin, hexes)[0] >= twin.min) { continue; }
        }
        r = measure(it, hexes);
        rec = { id: it.id, i: it.i, j: r[1], on: it.on, min: it.min, role: it.role, cond: it.cond, firm: it.firm, value: r[0], ctx: ctx };
        if (r[0] >= it.min) { passes.push(rec); continue; }
        rec.sev = it.firm && confirmed ? 'fail' : 'check';
        rec.open = it.firm && !confirmed ? 'unconfirmed' : it.cond;
        rec.repair = repairContrast(it, hexes);
        findings.push(rec);
      }
      var members = [], dup = {}, gridCache = {}, fids = ['check-duplicates', 'check-cvd', 'check-gray'], fi, tgt, a, b, v, kind, md;
      for (i = 0; i < idx.length; i++) {
        g = idx[i];
        if (g !== bg && (!cx.roles_mode || cols[g].role === null || cfg.signal_roles.indexOf(cols[g].role) >= 0)) { members.push(g); }
      }
      cx.set = members;
      for (fi = 0; fi < fids.length; fi++) {
        tgt = target(fids[fi], cfg, refs);
        for (i = 0; i < members.length; i++) {
          for (k = i + 1; k < members.length; k++) {
            if (dup[members[i] + ',' + members[k]]) { continue; }
            a = hexes[members[i]]; b = hexes[members[k]];
            if (fids[fi] === 'check-cvd') { md = C().minDistance([a, b], C().WORST_KINDS); v = md.value; kind = md.kind; }
            else { v = metric(fids[fi], a, b); kind = fids[fi] === 'check-duplicates' ? 'normal' : 'gray'; }
            if (v >= tgt) { continue; }
            if (fids[fi] === 'check-duplicates') { dup[members[i] + ',' + members[k]] = true; }
            rec = { id: fids[fi], i: members[i], j: members[k], kind: kind, value: v, sev: 'note', ctx: ctx };
            rec.repair = repairDistance(fids[fi], members[i], members[k], cfg, refs, items, hexes, members, gridCache);
            findings.push(rec);
          }
        }
      }
      var neutral = false;
      for (i = 0; i < idx.length; i++) { if (cols[idx[i]].chroma < cfg.neutral_c_max) { neutral = true; } }
      if (idx.length >= 2 && !neutral) { findings.push({ id: 'check-neutral-missing', i: null, j: null, sev: 'note', ctx: ctx, repair: null }); }
      for (i = 0; i < idx.length; i++) {
        if (cols[idx[i]].oog) { findings.push({ id: 'check-gamut', i: idx[i], j: null, sev: 'note', ctx: ctx, repair: null }); }
        if (cols[idx[i]].alpha < 1) { findings.push({ id: 'check-alpha', i: idx[i], j: null, sev: 'note', ctx: ctx, repair: null }); }
      }
      var order = [];
      for (i = 0; i < cfg.findings.length; i++) { order.push(cfg.findings[i].id); }
      for (i = 0; i < findings.length; i++) {
        findings[i].n = i;
        findings[i].key = [ctx, findings[i].id, findings[i].i === null ? '-' : String(findings[i].i), findings[i].j === null ? '-' : String(findings[i].j)].join('|');
      }
      findings.sort(function (p, q) {
        return (SEVS.indexOf(p.sev) - SEVS.indexOf(q.sev)) || (order.indexOf(p.id) - order.indexOf(q.id)) || (p.n - q.n);
      });
      cx.findings = findings; cx.passes = passes;
      var dist = {}, ps, kk;
      for (kk = 0; kk < KINDS_DIST.length; kk++) {
        ps = [];
        for (i = 0; i < members.length; i++) {
          for (k = i + 1; k < members.length; k++) { ps.push([C().distance(hexes[members[i]], hexes[members[k]], KINDS_DIST[kk]), i, k, members[i], members[k]]); }
        }
        ps.sort(function (p, q) { return p[0] < q[0] ? -1 : p[0] > q[0] ? 1 : (p[1] - q[1]) || (p[2] - q[2]); });
        dist[KINDS_DIST[kk]] = [];
        for (i = 0; i < ps.length && i < 5; i++) { dist[KINDS_DIST[kk]].push({ a: ps[i][3], b: ps[i][4], value: ps[i][0] }); }
      }
      cx.dist = dist;
      m.ctxs.push(cx);
    }
    return m;
  }

  function query(m, bgi) {
    var cols = m.colors, f = [], r = [], i, h;
    if (!cols.length) { return ''; }
    for (i = 0; i < cols.length; i++) {
      h = cols[i].hex.slice(1);
      if (cols[i].alpha < 1) { h += hex2(C().quantize(cols[i].alpha)); }
      f.push(h);
      r.push((cols[i].role || '-') + (cols[i].ctx === 'dark' ? '.d' : ''));
    }
    var out = ['f=' + f.join(',')], dark = false;
    for (i = 0; i < cols.length; i++) { if (cols[i].ctx === 'dark') { dark = true; } }
    if (m.confirmed) { out.push('r=' + r.join(',')); } else if (dark) {
      r = [];
      for (i = 0; i < cols.length; i++) { r.push(cols[i].ctx === 'dark' ? '-.d' : '-'); }
      out.push('r=' + r.join(','));
    }
    if (typeof bgi === 'number' && bgi >= 0 && bgi < cols.length) { out.push('bgi=' + bgi); }
    return out.join('&');
  }
  function readQuery(search, cfg) {
    var f = null, r = null, bgi = null, dirty = false, seen = {}, parts = String(search || '').replace(/^\?+/, '').split('&'), i, k, v, eq, vals, x, p, ids = { '-': true }, toks, ok, j;
    for (i = 0; i < cfg.roles.length; i++) { ids[cfg.roles[i].id] = true; }
    for (i = 0; i < parts.length; i++) {
      if (!parts[i]) { continue; }
      eq = parts[i].indexOf('=');
      k = eq < 0 ? parts[i] : parts[i].slice(0, eq); v = eq < 0 ? '' : parts[i].slice(eq + 1);
      if (has(seen, k)) { dirty = true; continue; }
      seen[k] = true;
      if (k === 'f') {
        vals = []; x = v.split(',');
        for (j = 0; j < x.length; j++) {
          p = /^[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/.test(x[j]) ? C().parse('#' + x[j], false) : null;
          if (p === null) { vals = null; break; }
          vals.push('#' + x[j].toUpperCase());
        }
        if (vals && vals.length && vals.length <= 2 * cfg.max_colors) { f = vals; } else { dirty = true; }
      } else if (k === 'r') {
        toks = v.split(','); ok = true;
        for (j = 0; j < toks.length; j++) { if (!has(ids, /\.d$/.test(toks[j]) ? toks[j].slice(0, -2) : toks[j])) { ok = false; } }
        if (ok) { r = toks; } else { dirty = true; }
      } else if (k === 'bgi') {
        if (/^[0-9]{1,2}$/.test(v)) { bgi = parseInt(v, 10); } else { dirty = true; }
      } else { dirty = true; }
    }
    if (f === null && (r !== null || bgi !== null)) { r = null; bgi = null; dirty = true; }
    if (f !== null && r !== null && r.length !== f.length) { r = null; dirty = true; }
    if (f !== null && bgi !== null && bgi >= f.length) { bgi = null; dirty = true; }
    if (f !== null && r !== null) {
      // Reihenfolge wie scan: erst hell, dann dunkel; bgi wandert mit
      var order = [], moved = false, f2 = [], r2 = [];
      for (j = 0; j < r.length; j++) { if (!/\.d$/.test(r[j])) { order.push(j); } }
      for (j = 0; j < r.length; j++) { if (/\.d$/.test(r[j])) { order.push(j); } }
      for (j = 0; j < order.length; j++) { if (order[j] !== j) { moved = true; } f2.push(f[order[j]]); r2.push(r[order[j]]); }
      if (moved) { f = f2; r = r2; bgi = bgi !== null ? order.indexOf(bgi) : null; dirty = true; }
    }
    return { f: f, r: r, bgi: bgi, dirty: dirty };
  }

  // ---------- Ansicht (Spiegel von tools/check.py)
  function fill(tmpl, values) { return tmpl.replace(/\{([a-z_]+)\}/g, function (m0, k) { return has(values, k) ? values[k] : m0; }); }
  function num(R, tmpl) { return C().renderText(tmpl, { refs: R.refs }, R.lang, { escape: false }).html; }
  function cr(R, a, b) { return num(R, '{cr:' + a + '/' + b + '}'); }
  function dst(R, a, b, kind) { return num(R, '{dist:' + a + '/' + b + '/' + kind + '}'); }
  function count(R, n) { return C().renderText('{count:n}', { counts: { n: n } }, R.lang, { escape: false }).html; }
  function code(hx) { return '<code>' + hx + '</code>'; }
  function thr(x, lang) { return X().fmtThreshold(x, lang); }
  function roleName(R, rid) { var r = roleDef(R.cfg, rid); return r ? r['name_' + R.lang] : rid; }
  function plain(html) { return X().unesc(html.replace(/<[^>]*>/g, '')); }
  function effOf(cols) { var hx = {}, g; for (g = 0; g < cols.length; g++) { if (has(cols[g], 'eff')) { hx[g] = cols[g].eff; } } return hx; }

  function findingMessage(R, m, f) {
    var T = R.T, cols = m.colors, hx = effOf(cols), fid = f.id, a, b, out, c;
    if (fid === 'check-text' || fid === 'check-nontext') {
      a = hx[f.i]; b = hx[f.j];
      out = fill(T['msg.' + (fid === 'check-text' ? 'text' : 'nontext') + '.' + (f.cond === 'free' ? 'free' : 'role')], {
        a: code(a), b: code(b), ratio: cr(R, a, b), min: thr(f.min, R.lang), role: f.role ? esc(roleName(R, f.role)) : '' });
      if (f.open && f.open !== 'free') { out += ' ' + T['open.' + f.open]; }
      return out;
    }
    if (fid === 'check-duplicates' || fid === 'check-cvd' || fid === 'check-gray') {
      a = hx[f.i]; b = hx[f.j];
      return fill(T['msg.' + fid.slice(6)], { a: code(a), b: code(b), d: dst(R, a, b, f.kind), at: esc(T['at.' + f.kind]),
        okabe: num(R, '{ref:' + R.cfg.compare + '}') });
    }
    if (fid === 'check-neutral-missing') { return T['msg.neutral-missing']; }
    c = cols[f.i];
    if (fid === 'check-gamut') { return fill(T['msg.gamut'], { raw: code(esc(c.raw)), a: code(c.hex), d: C().fmtDist(c.md || 0, R.lang) }); }
    return fill(T['msg.alpha'], { raw: code(esc(c.raw)), a: code(c.eff) });
  }
  function repairText(R, m, f) {
    var T = R.T, rp = has(f, 'repair') ? f.repair : null, cols = m.colors, a, b, worst = null, k, r, o, kind;
    if (!rp) { return ''; }
    if (rp.to === null) {
      return fill(T['fix.none.' + (f.id === 'check-text' || f.id === 'check-nontext' ? 'contrast' : 'distance')],
        { link: '<a href="' + R.paths.charts + '">' + esc(T['fix.charts']) + '</a>' });
    }
    a = rp.from; b = rp.to;
    if (f.id === 'check-text' || f.id === 'check-nontext') {
      for (k = 0; k < f.on.length; k++) {
        r = C().contrast(b, cols[f.on[k]].eff);
        if (worst === null || r < worst[0] - 1e-12) { worst = [r, f.on[k]]; }
      }
      return fill(T['fix.contrast'], { to: code(b), from: code(a), ratio: cr(R, b, cols[worst[1]].eff), d: dst(R, a, b, 'normal') });
    }
    o = cols[rp.other].eff;
    kind = f.id !== 'check-cvd' ? f.kind : C().minDistance([b, o], C().WORST_KINDS).kind;
    return fill(T['fix.distance'], { to: code(b), from: code(a), dd: dst(R, b, o, kind), at: esc(T['at.' + kind]), d: dst(R, a, b, 'normal') });
  }
  function repairHtml(R, m, f) {
    var txt = repairText(R, m, f), btn = '';
    if (!txt) { return ''; }
    if (f.repair.to !== null) { btn = ' <button type="button" class="btn js-only" data-apply="' + f.repair.i + '" data-to="' + f.repair.to + '">' + esc(R.T['fix.apply']) + '</button>'; }
    return '<p class="fix">' + txt + btn + '</p>';
  }
  function ruleOf(R, fid) { var fd = findingDef(R.cfg, fid); return fd && has(R.rules, fd.rule) ? R.rules[fd.rule] : null; }
  function levelTags(R, obj) {
    var F = R.F, tags = ['<span class="tag-level">' + esc(F['level.' + obj.level]) + '</span>'];
    if (obj.strength) { tags.push('<span class="tag-sub">' + esc(F['strength.' + obj.strength]) + '</span>'); }
    if (obj.myth) { tags.push('<span class="tag-sub">' + esc(F.myth) + '</span>'); }
    if (obj.own) { tags.push('<span class="tag-sub">' + esc(F.own) + '</span>'); }
    return tags.join(' ');
  }
  function shortSrc(R, rule) {
    var norm = rule.normative || [], ids = norm.slice(), i, s, src = rule.sources || [];
    for (i = 0; i < src.length; i++) { if (norm.indexOf(src[i]) < 0) { ids.push(src[i]); } }
    for (i = 0; i < ids.length; i++) { s = R.sources[ids[i]]; if (s) { return s['short_' + R.lang] || s.title; } }
    return '';
  }
  function whyText(R, m, f) {
    var rule = ruleOf(R, f.id) || {};
    return plain(fill(R.T.why, { msg: findingMessage(R, m, f), src: esc(shortSrc(R, rule)), url: esc(R.url) }));
  }
  function findingHtml(R, m, f, newKeys) {
    var T = R.T, rule = ruleOf(R, f.id), fd = findingDef(R.cfg, f.id), head, isNew = newKeys.indexOf(f.key) >= 0, more = '';
    head = '<span class="sev">' + SYM[f.sev] + ' ' + esc(T['sev.' + f.sev]) + '</span>';
    if (rule) { head += ' ' + levelTags(R, rule) + ' <small class="f-src">' + esc(shortSrc(R, rule)) + '</small>'; }
    if (isNew) { head += ' <span class="tag-sub f-new">' + esc(T['new']) + '</span>'; }
    if (fd && fd.explain) { more = ' <a class="more-link" href="' + R.paths.explained + '#' + fd.explain + '">' + esc(R.F.more_about) + '</a>'; }
    return '<li class="finding" data-sev="' + f.sev + '" data-key="' + esc(f.key) + '"' + (isNew ? ' data-new' : '') + '>' +
      '<div class="finding-h">' + head + '</div><p>' + findingMessage(R, m, f) + '</p>' + repairHtml(R, m, f) +
      '<p class="f-links"><button type="button" class="btn" data-copy="' + esc(whyText(R, m, f)) + '">' + esc(T.why_btn) + '</button>' + more + '</p></li>';
  }
  function passHtml(R, m, p) {
    var cols = m.colors, a = cols[p.i].eff, b = cols[p.j].eff, role = p.role ? ' (' + esc(roleName(R, p.role)) + ')' : '';
    return '<li>' + SYM.pass + ' ' + fill(R.T[p.id === 'check-text' ? 'pass.text' : 'pass.nontext'], { a: code(a), b: code(b), role: role,
      ratio: cr(R, a, b), min: thr(p.min, R.lang) }) + '</li>';
  }
  function rolesBlock(R, m, cx) {
    var T = R.T, cols = m.colors, items = [], i, j, c, g, name, opts, lab, tag, parts, btn, r;
    for (i = 0; i < cx.idx.length; i++) {
      g = cx.idx[i]; c = cols[g]; parts = [];
      for (j = 0; j < c.names.length; j++) { parts.push('--' + esc(c.names[j])); }
      name = parts.length ? '<code>' + parts.join(', ') + '</code>' : code(c.hex);
      opts = '<option value="-"' + (!c.role ? ' selected' : '') + '>' + esc(T['roles.none']) + '</option>';
      for (j = 0; j < R.cfg.roles.length; j++) {
        r = R.cfg.roles[j];
        opts += '<option value="' + r.id + '"' + (c.role === r.id ? ' selected' : '') + '>' + esc(r['name_' + R.lang]) + '</option>';
      }
      lab = esc(fill(T['roles.menu_l'], { name: plain(name) }));
      tag = c.role && c.role_src !== 'confirmed' ? ' <span class="tag-sub">' + esc(T['roles.suggest']) + '</span>' : '';
      items.push('<li><span class="swatch" style="background:' + c.eff + '"></span><span class="rl-n">' + name + '</span>' +
        '<span class="rl-arrow" aria-hidden="true">→</span><select class="rl-sel" data-role="' + g + '" aria-label="' + lab + '">' + opts + '</select>' + tag + '</li>');
    }
    btn = m.confirmed ? '<p class="hint">' + esc(T['roles.confirmed']) + '</p>' :
      '<button type="button" class="btn primary js-only" data-confirm>' + esc(T['roles.confirm']) + '</button>';
    return '<section class="chk-blk"><h3>' + esc(T['roles.h']) + '</h3><p class="hint">' + esc(T['roles.intro']) + '</p>' +
      '<ul class="chk-roles">' + items.join('') + '</ul>' + btn + '</section>';
  }
  function bgBlock(R, m, cx) {
    var cols = m.colors, chips = '', i, g, lid = 'chk-bg-' + cx.ctx;
    for (i = 0; i < cx.idx.length; i++) {
      g = cx.idx[i];
      chips += '<button type="button" class="chip chk-bg" data-bgi="' + g + '" aria-pressed="' + (g === cx.bg ? 'true' : 'false') + '">' +
        '<span class="sw" style="background:' + cols[g].eff + '"></span>' + cols[g].eff + '</button>';
    }
    return '<section class="chk-blk"><h3 id="' + lid + '">' + esc(R.T['bg.h']) + '</h3><div class="chips" role="group" aria-labelledby="' + lid + '">' + chips + '</div></section>';
  }
  function barBlock(R, m, cx, changed) {
    var T = R.T, cols = m.colors, rows = [], i, g, c, bt, notes, undo, ok, note;
    for (i = 0; i < cx.idx.length; i++) {
      g = cx.idx[i]; c = cols[g];
      bt = fill(T['bar.best.' + (c.best === '#FFFFFF' ? 'white' : 'black')], { ratio: cr(R, c.best, c.eff) });
      notes = [];
      if (c.role) { notes.push(esc(roleName(R, c.role)) + (c.role_src !== 'confirmed' ? ' (' + esc(T['roles.suggest']) + ')' : '')); }
      if (g === cx.bg && c.role !== 'bg') { notes.push(esc(T['bar.isbg'])); }
      if (c.oog) { notes.push(fill(T['bar.gamut'], { d: C().fmtDist(c.md || 0, R.lang) })); }
      if (c.alpha < 1) { notes.push(fill(T['bar.alpha'], { color: code(c.hex) })); }
      undo = changed.indexOf(g) >= 0 ? ' <button type="button" class="btn" data-undo>' + esc(T['bar.undo']) + '</button>' : '';
      ok = c.oklch ? '<code class="ok">' + c.oklch + '</code>' : '';
      note = notes.length ? '<small class="bar-note">' + notes.join(' · ') + '</small>' : '';
      rows.push('<li class="bar-row"><span class="swatch" style="background:' + c.eff + '"></span>' +
        '<span class="bar-t"><code class="hex">' + c.eff + '</code> ' + ok + '<small>' + bt + '</small>' + note + '</span>' +
        '<span class="bar-act"><button type="button" class="btn icon" data-copy="' + c.eff + '" aria-label="' + esc(fill(T['bar.copy_l'], { value: c.eff })) + '">' +
        COPY_ICON + '</button>' + undo + '</span></li>');
    }
    return '<section class="chk-blk"><h3>' + esc(T['bar.h']) + '</h3><ul class="chk-bar">' + rows.join('') + '</ul></section>';
  }
  function cls(r) { return r >= 4.5 ? 't' : r >= 3 ? 'g' : 'd'; }
  function matrixBlock(R, m, cx) {
    var T = R.T, cols = m.colors, idx = cx.idx, ctx = cx.ctx, head = '', rows = [], i, j, a, b, cells, r, k, legend = [], picks = '', lists = [], li;
    if (idx.length < 2) { return ''; }
    for (i = 0; i < idx.length; i++) { head += '<th scope="col"><span class="sw" style="background:' + cols[idx[i]].eff + '"></span><code>' + cols[idx[i]].eff + '</code></th>'; }
    for (i = 0; i < idx.length; i++) {
      a = idx[i]; cells = '';
      for (j = 0; j < idx.length; j++) {
        b = idx[j];
        if (a === b) { cells += '<td class="mx-d">–</td>'; continue; }
        r = C().contrast(cols[a].eff, cols[b].eff); k = cls(r);
        cells += '<td class="mx-' + k + '">' + cr(R, cols[a].eff, cols[b].eff) + '<small>' + esc(T['mx.' + k]) + '</small></td>';
      }
      rows.push('<tr><th scope="row"><span class="sw" style="background:' + cols[a].eff + '"></span><code>' + cols[a].eff + '</code></th>' + cells + '</tr>');
    }
    for (i = 0; i < 3; i++) { k = ['t', 'g', 'd'][i]; legend.push('<span class="mx-' + k + '">' + esc(T['mx.legend.' + k]) + '</span>'); }
    for (i = 0; i < idx.length; i++) {
      picks += '<button type="button" class="chip" data-mxpick="' + idx[i] + '" aria-pressed="' + (i === 0 ? 'true' : 'false') + '">' +
        '<span class="sw" style="background:' + cols[idx[i]].eff + '"></span>' + cols[idx[i]].eff + '</button>';
    }
    for (i = 0; i < idx.length; i++) {
      a = idx[i]; li = '';
      for (j = 0; j < idx.length; j++) {
        b = idx[j];
        if (a === b) { continue; }
        r = C().contrast(cols[a].eff, cols[b].eff);
        li += '<li><span class="sw" style="background:' + cols[b].eff + '"></span><code>' + cols[b].eff + '</code> ' +
          cr(R, cols[a].eff, cols[b].eff) + ' <small class="mx-' + cls(r) + '">' + esc(T['mx.' + cls(r)]) + '</small></li>';
      }
      lists.push('<ul class="mx-list plain' + (i === 0 ? ' on' : '') + '" data-mxlist="' + a + '">' + li + '</ul>');
    }
    return '<section class="chk-blk chk-mx"><h3>' + esc(T['mx.h']) + '</h3><p class="hint">' + legend.join(' · ') + '</p>' +
      '<div class="mx-wide" role="region" tabindex="0" aria-label="' + esc(T['mx.h']) + '"><table class="mx"><thead><tr><td></td>' + head + '</tr></thead>' +
      '<tbody>' + rows.join('') + '</tbody></table></div>' +
      '<div class="mx-narrow"><span class="ctl-label" id="mx-pick-' + ctx + '">' + esc(T['mx.pick']) + '</span>' +
      '<div class="chips js-only" role="group" aria-labelledby="mx-pick-' + ctx + '">' + picks + '</div>' + lists.join('') + '</div></section>';
  }
  function simBlock(R, m, cx) {
    var rows = '', i, k, cells;
    for (k = 0; k < KINDS_SIM.length; k++) {
      cells = '';
      for (i = 0; i < cx.idx.length; i++) { cells += '<span style="background:' + C().simHex(m.colors[cx.idx[i]].eff, KINDS_SIM[k]) + '"></span>'; }
      rows += '<div class="sim-row"><span class="sim-k">' + esc(R.F['sim.' + KINDS_SIM[k]]) + '</span><div class="strip" aria-hidden="true">' + cells + '</div></div>';
    }
    return '<section class="chk-blk"><h3>' + esc(R.T['sim.h']) + '</h3>' + rows + '<p class="sim-note">' + esc(R.F.sim_note) + '</p></section>';
  }
  function refsLine(R) {
    var parts = [], i;
    for (i = 0; i < R.comparisons.length; i++) { parts.push(esc(R.comparisons[i]['name_' + R.lang]) + ' ' + num(R, '{ref:' + R.comparisons[i].id + '}')); }
    return fill(R.F['distinct.refs'], { list: parts.join(' · ') });
  }
  function distBlock(R, m, cx) {
    var T = R.T, F = R.F, cols = m.colors, out = '', k, i, d, li;
    if (cx.set.length < 2) { return '<section class="chk-blk"><h3>' + esc(T['dist.h']) + '</h3><p class="hint">' + esc(T['dist.none']) + '</p></section>'; }
    for (k = 0; k < KINDS_DIST.length; k++) {
      li = '';
      for (i = 0; i < cx.dist[KINDS_DIST[k]].length; i++) {
        d = cx.dist[KINDS_DIST[k]][i];
        li += '<li><span class="sw" style="background:' + cols[d.a].eff + '"></span><span class="sw" style="background:' + cols[d.b].eff + '"></span>' +
          '<code>' + cols[d.a].eff + '/' + cols[d.b].eff + '</code> ' + dst(R, cols[d.a].eff, cols[d.b].eff, KINDS_DIST[k]) + '</li>';
      }
      out += '<div class="dist-k"><h4>' + esc(F['sim.' + KINDS_DIST[k]]) + '</h4><ol class="plain">' + li + '</ol></div>';
    }
    return '<section class="chk-blk"><h3>' + esc(T['dist.h']) + '</h3><p class="hint">' + esc(T['dist.intro']) + '</p>' +
      '<div class="dist-grid">' + out + '</div><p class="muted">' + refsLine(R) + '</p></section>';
  }
  function findingsBlock(R, m, cx, newKeys) {
    var T = R.T, fs = cx.findings, lim = R.cfg.open_findings, body = '', i, ps = cx.passes, li = '';
    if (!fs.length) { body = '<p>' + esc(T['f.none']) + '</p>'; }
    else {
      body = '<ul class="findings">';
      for (i = 0; i < fs.length && i < lim; i++) { body += findingHtml(R, m, fs[i], newKeys); }
      body += '</ul>';
      if (fs.length > lim) {
        body += '<details class="f-more"><summary>' + fill(T[fs.length - lim === 1 ? 'f.more_1' : 'f.more'], { n: count(R, fs.length - lim) }) + '</summary><ul class="findings">';
        for (i = lim; i < fs.length; i++) { body += findingHtml(R, m, fs[i], newKeys); }
        body += '</ul></details>';
      }
    }
    if (ps.length) {
      for (i = 0; i < ps.length; i++) { li += passHtml(R, m, ps[i]); }
      body += '<details class="f-pass"><summary>' + fill(T['f.passed'], { n: count(R, ps.length) }) + '</summary><ul class="plain">' + li + '</ul></details>';
    }
    return '<section class="chk-blk chk-f"><h3>' + esc(T['f.h']) + '</h3>' + body + '</section>';
  }
  function notesHtml(R, m) {
    var T = R.T, out = '', i, n, x;
    for (i = 0; i < m.notes.length; i++) {
      n = m.notes[i]; x = null;
      if (n.key === 'var') { x = fill(T['note.var'], { name: code('--' + esc(n.name)), target: code('--' + esc(n.ref)) }); }
      else if (n.key === 'dropped') { x = fill(T[n.n === 1 ? 'note.dropped_1' : 'note.dropped'], { n: count(R, n.n), max: count(R, R.cfg.max_colors), ctx: esc(T['ctx.' + n.ctx]) }); }
      if (x !== null) { out += '<p class="note" role="note">' + x + '</p>'; }
    }
    return out;
  }
  function mostColorful(m) {
    var best = null, g;
    for (g = 0; g < m.colors.length; g++) { if (has(m.colors[g], 'chroma') && (best === null || m.colors[g].chroma > m.colors[best].chroma + 1e-12)) { best = g; } }
    return best !== null ? m.colors[best].eff : null;
  }
  function render(m, R, opts) {
    opts = opts || {};
    var T = R.T, newKeys = opts.new_keys || [], changed = opts.changed || [], out = [], i, cx, chips = '';
    if (opts.example) { out.push('<p class="note chk-example">' + fill(T.example, { colors: code(esc(R.cfg.example)) }) + '</p>'); }
    out.push(notesHtml(R, m));
    if (!m.ctxs.length) { out.push('<p class="hint">' + esc(T.empty) + '</p>'); return out.join(''); }
    out.push('<div class="pal-act"><button type="button" class="btn primary" data-copy-from="#exp-report-0">' +
      esc(fill(R.F.copy_fmt, { fmt: R.F['fmt.report.inline'] })) + '</button><a class="more-link" href="#kopieren">' + esc(R.F.all_fmts) + '</a></div>');
    if (m.ctxs.length > 1) {
      for (i = 0; i < m.ctxs.length; i++) {
        chips += '<button type="button" class="chip" data-ctxpick="' + m.ctxs[i].ctx + '" aria-pressed="' + (i === 0 ? 'true' : 'false') + '">' + esc(T['ctx.' + m.ctxs[i].ctx]) + '</button>';
      }
      out.push('<div class="chips js-only chk-ctxpick" role="group" aria-label="' + esc(T.ctx_l) + '">' + chips + '</div>');
    }
    for (i = 0; i < m.ctxs.length; i++) {
      cx = m.ctxs[i];
      out.push('<div class="chk-ctx" data-ctx="' + cx.ctx + '">' + (m.ctxs.length > 1 ? '<h2 class="ctx-h">' + esc(T['ctx.' + cx.ctx]) + '</h2>' : ''));
      if (m.has_names) { out.push(rolesBlock(R, m, cx)); }
      out.push(bgBlock(R, m, cx), barBlock(R, m, cx, changed), matrixBlock(R, m, cx), simBlock(R, m, cx), distBlock(R, m, cx), findingsBlock(R, m, cx, newKeys), '</div>');
    }
    return out.join('');
  }

  // ---------- Exporte (5.8)
  function secLines(R, m, cx, sev) {
    var out = [], i, f, line, fix;
    for (i = 0; i < cx.findings.length; i++) {
      f = cx.findings[i];
      if (f.sev !== sev) { continue; }
      line = '- ' + SYM[sev] + ' ' + plain(findingMessage(R, m, f));
      fix = repairText(R, m, f);
      if (fix) { line += '\n  ' + plain(fix); }
      out.push(line);
    }
    return out;
  }
  function report(m, R) {
    var T = R.T, lang = R.lang, out = ['# ' + T['rep.title'], '', fill(T['rep.head'], { date: R.date, url: R.url })], anyRole = false, i, j, k, cx, cols = m.colors, pre, list, lines, ps;
    for (i = 0; i < cols.length; i++) { if (cols[i].role) { anyRole = true; } }
    out.push(T['rep.roles.' + (m.confirmed ? 'confirmed' : anyRole ? 'guess' : 'none')]);
    for (i = 0; i < m.ctxs.length; i++) {
      cx = m.ctxs[i]; pre = m.ctxs.length > 1 ? T['ctx.' + cx.ctx] + ': ' : ''; list = [];
      for (j = 0; j < cx.idx.length; j++) { list.push(cols[cx.idx[j]].eff + (cols[cx.idx[j]].role ? ' (' + roleName(R, cols[cx.idx[j]].role) + ')' : '')); }
      out.push('', '## ' + pre + T['rep.colors'], list.join(', '), fill(T['rep.bg'], { color: cols[cx.bg].eff }));
      for (k = 0; k < SEVS.length; k++) {
        lines = secLines(R, m, cx, SEVS[k]);
        out.push('', '## ' + pre + T['rep.' + SEVS[k]] + ' (' + C().fmtCount(lines.length, lang) + ')');
        if (lines.length) { out = out.concat(lines); } else { out.push('- ' + T['rep.empty']); }
      }
      ps = [];
      for (j = 0; j < cx.passes.length; j++) { ps.push('- ' + plain(passHtml(R, m, cx.passes[j]))); }
      out.push('', '## ' + pre + T['rep.pass'] + ' (' + C().fmtCount(ps.length, lang) + ')');
      if (ps.length) { out = out.concat(ps); } else { out.push('- ' + T['rep.empty']); }
    }
    var refs = [];
    for (i = 0; i < R.comparisons.length; i++) { refs.push(R.comparisons[i]['name_' + lang] + ' ' + plain(num(R, '{ref:' + R.comparisons[i].id + '}'))); }
    out.push('', '---', T['rep.sim'], fill(R.F['distinct.refs'], { list: refs.join(' · ') }),
      T['rep.not_checked'] + ' ' + T.not_checked.join(', ') + '.', T['rep.license']);
    return out.join('\n');
  }
  function hexlist(m, R) {
    var T = R.T, cols = m.colors, parts = [], i, j, cx, head, names, w, rows, c, nm;
    for (i = 0; i < m.ctxs.length; i++) {
      cx = m.ctxs[i];
      head = fill(T['hex.head'], { date: R.date }) + (m.ctxs.length > 1 ? ' · ' + T['ctx.' + cx.ctx].toLowerCase() : '');
      names = []; w = 0;
      for (j = 0; j < cx.idx.length; j++) {
        c = cols[cx.idx[j]];
        nm = c.names.length ? c.names[0] : (c.role || '');
        names.push(nm); if (nm.length > w) { w = nm.length; }
      }
      w += 2; rows = [head];
      for (j = 0; j < cx.idx.length; j++) {
        c = cols[cx.idx[j]];
        rows.push((w > 2 ? ljust(names[j], w) : '') + c.eff + (c.role ? '  ' + roleName(R, c.role) : ''));
      }
      parts.push(rows.join('\n'));
    }
    return parts.join('\n\n') + '\n\n' + fill(T['hex.link'], { url: R.url });
  }
  function css(m, R) {
    var T = R.T, cols = m.colors, lines = ['/* ' + fill(T['hex.head'], { date: R.date }), '   ' + T['css.checked'], '   ' + fill(T['hex.link'], { url: R.url }) + ' */'];
    var i, j, cx, rows, c, nm, note, w, ind, bits, used;
    for (i = 0; i < m.ctxs.length; i++) {
      cx = m.ctxs[i]; rows = []; used = {};
      for (j = 0; j < cx.idx.length; j++) {
        c = cols[cx.idx[j]];
        nm = c.names.length ? c.names[0] : c.role;
        if (!nm) { continue; }
        nm = uniq(nm, used);
        bits = [];
        if (c.oklch) { bits.push(c.oklch); }
        if (c.role) { bits.push(roleName(R, c.role)); }
        rows.push([nm, c.eff, bits.join(' · ')]);
      }
      if (!rows.length) { continue; }
      w = 0;
      for (j = 0; j < rows.length; j++) { if (rows[j][0].length > w) { w = rows[j][0].length; } }
      w += 3;
      ind = cx.ctx === 'light' ? '  ' : '    ';
      if (cx.ctx === 'light') { lines.push(':root {'); } else { lines.push('@media (prefers-color-scheme: dark) {', '  :root {'); }
      for (j = 0; j < rows.length; j++) {
        lines.push(ind + ljust('--' + rows[j][0] + ':', w + 1) + rows[j][1] + ';' + (rows[j][2] ? ' /* ' + rows[j][2].replace(/\*\//g, '* /') + ' */' : ''));
      }
      lines.push(cx.ctx === 'light' ? '}' : '  }');
      if (cx.ctx !== 'light') { lines.push('}'); }
    }
    return lines.join('\n');
  }
  // CSS gibt es nur mit Rollen (5.9)
  function hasCss(m) { for (var i = 0; i < m.colors.length; i++) { if (m.colors[i].role) { return true; } } return false; }
  function exports_(m, R) {
    var out = [['report', report(m, R)], ['hex', hexlist(m, R)]];
    if (hasCss(m)) { out.push(['css', css(m, R)]); }
    return out;
  }
  function exportHtml(m, R) {
    var T = R.T, F = R.F, ex = exports_(m, R), tabs = '', panels = '', i, f, pid, hx, links = '', tasks = ['website', 'charts'];
    for (i = 0; i < ex.length; i++) {
      f = ex[i][0];
      tabs += '<button type="button" role="tab" class="tab" id="tab-' + f + '" data-tab="' + f + '" aria-controls="panel-' + f + '" ' +
        'aria-selected="' + (i === 0 ? 'true' : 'false') + '"' + (i === 0 ? '' : ' tabindex="-1"') + '>' + esc(F['fmt.' + f]) + '</button>';
    }
    for (i = 0; i < ex.length; i++) {
      f = ex[i][0]; pid = 'exp-' + f + '-0';
      panels += '<div class="tabpanel' + (i === 0 ? ' on' : '') + '" id="panel-' + f + '" role="tabpanel" aria-labelledby="tab-' + f + '">' +
        '<h3 class="panel-h">' + esc(F['fmt.' + f]) + '</h3>' +
        '<pre class="code" id="' + pid + '" tabindex="0"><code>' + esc(ex[i][1]) + '</code></pre>' +
        '<div class="exp-act"><button type="button" class="btn primary" data-copy-from="#' + pid + '">' + esc(F.copy) + '</button>' +
        '<button type="button" class="btn js-only" data-download="#' + pid + '" data-filename="' + X().filename('check', null, f) + '" data-mime="' + X().mime(f) + '">' + esc(F.download) + '</button>' +
        '<button type="button" class="btn js-only" data-wrap="#' + pid + '" aria-pressed="false">' + esc(F.wrap) + '</button></div></div>';
    }
    hx = mostColorful(m);
    if (hx) {
      links = '<h3>' + esc(T['open.h']) + '</h3><ul class="next">';
      for (i = 0; i < tasks.length; i++) {
        links += '<li><a href="' + R.paths[tasks[i]] + '?c=' + hx.slice(1) + '">' + fill(esc(T['open.' + tasks[i]]), { color: hx }) + '</a></li>';
      }
      links += '</ul>';
    }
    return '<div class="tabs" role="tablist" aria-label="' + esc(F.fmts_l) + '">' + tabs + '</div>' + panels + links;
  }

  return {
    SEVS: SEVS, scan: scan, stateText: stateText, stateRoles: stateRoles, guessRoles: guessRoles, analyze: analyze, query: query, readQuery: readQuery,
    render: render, findingMessage: findingMessage, repairText: repairText, whyText: whyText, plain: plain,
    report: report, hexlist: hexlist, css: css, hasCss: hasCss, exports: exports_, exportHtml: exportHtml, mostColorful: mostColorful
  };
}));
