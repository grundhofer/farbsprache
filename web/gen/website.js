/* Generator der Aufgabe Website oder App (FS.gen.website). Spiegel von tools/gen/website.py.
   Aufgabe Website oder App (Neutraltöne, Akzent, Akzent als Text, Diagrammfarben) und Aufgabe Statusfarben
   (Statusfarben in festen Bändern, optimiert auf den größten kleinsten Abstand, mit Vergleich „unoptimiert“).
   web/gen/status.js nutzt neutrals, statusColors, statusFindings und conflict. */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.website = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }

  var KINDS3 = ['normal', 'deutan', 'protan'];
  var STATUS = [['danger', 27.0], ['warning', 70.0], ['success', 150.0], ['info', 250.0]];
  var STATUS_C = { light: 0.15, dark: 0.13 };
  var STATUS_SURF = { light: [0.965, 0.025], dark: [0.27, 0.04] };
  var BAND = { light: [0.42, 9], dark: [0.62, 13] };
  var STATUS_DIR = { light: -1, dark: 1 };
  var MODES = ['light', 'dark'];
  var CHARTS = 5;
  // Start der Suche für die Linkfarbe, wenn die eigene Farbe jenseits der Flächen liegt
  var TEXT_L0 = { '-1': 0.80, '1': 0.40 };
  // Reserve über der Schwelle: gedämpfter Text 4,95 statt 4,5, kräftiger Rahmen 3,3 statt 3, als Literal
  var TEXT_T = 4.95, LINE_T = 3.3;
  // Buntheit des Akzents im dunklen Modus
  var DARK_C = 0.85;

  // Tönung t der Neutraltöne
  function tint(cs, tone) {
    if (tone === 'neutral') { return 0; }
    if (tone === 'strong') { return Math.min(Math.max(0.25 * cs, 0.010), 0.030); }
    return Math.min(Math.max(0.1 * cs, 0.004), 0.012);
  }
  // Seed → [L, C, h, t, h_roh]; unbunt (powerless): h = 0, Tönung 0, h_roh null
  function seedLch(seed, tone) {
    var lch = C().hexToOklch(seed), h = lch[2];
    if (h === null || h !== h) { return [lch[0], lch[1], 0, 0, null]; }
    return [lch[0], lch[1], h, tint(lch[1], tone), h];
  }
  function neutrals(h, t) {
    var c = C(), lt, dk;
    lt = { bg: c.oklchToHex(0.985, 0.4 * t, h), surface: '#FFFFFF', 'surface-2': c.oklchToHex(0.955, 0.6 * t, h),
      text: c.oklchToHex(0.24, 1.6 * t, h), border: c.oklchToHex(0.88, t, h) };
    lt['text-muted'] = c.solveL(1.4 * t, h, [lt.bg, lt.surface, lt['surface-2']], TEXT_T, -1, 0.60).hex;
    lt['border-strong'] = c.solveL(1.4 * t, h, [lt.bg, lt.surface], LINE_T, -1, 0.72).hex;
    dk = { bg: c.oklchToHex(0.19, t, h), surface: c.oklchToHex(0.23, t, h), 'surface-2': c.oklchToHex(0.27, t, h),
      text: c.oklchToHex(0.94, 0.6 * t, h), border: c.oklchToHex(0.34, t, h) };
    dk['text-muted'] = c.solveL(t, h, [dk.bg, dk.surface, dk['surface-2']], TEXT_T, 1, 0.60).hex;
    dk['border-strong'] = c.solveL(t, h, [dk.bg, dk.surface], LINE_T, 1, 0.45).hex;
    return { light: lt, dark: dk };
  }

  // ---------- Akzent
  // labels = [[Schrift, Richtung]]: −1 helle Schrift (Akzent dunkler), +1 dunkle Schrift (heller)
  function accentFill(cand, L, cc, h, labels, mode, changes) {
    var c = C(), best = null, i, r, pick = null, err = null, res, step;
    for (i = 0; i < labels.length; i++) {
      r = c.contrast(labels[i][0], cand);
      if (r >= 4.5 && (best === null || r > best[1])) { best = [labels[i][0], r]; }
    }
    if (best !== null) { return [cand, best[0], true]; }
    for (i = 0; i < labels.length; i++) {
      try {
        res = c.solveL(cc, h, [labels[i][0]], 4.5, labels[i][1], L);
      } catch (e) {
        if (!e || !e.key) { throw e; }
        err = err || e;
        continue;
      }
      step = Math.abs(res.L - L);
      if (pick === null || step < pick[1] || (step === pick[1] && res.ratio > pick[2].ratio)) { pick = [labels[i][0], step, res, labels[i][1]]; }
    }
    if (pick === null) { throw err; }
    changes.push({ role: 'accent', mode: mode, from: cand, to: pick[2].hex, key: pick[3] < 0 ? 'accent-darker' : 'accent-lighter',
      values: { before: c.contrast(pick[0], cand), after: pick[2].ratio } });
    return [pick[2].hex, pick[0], false];
  }
  // Akzent als Text: solveL ab L; liegt die eigene Farbe jenseits der Flächen (mixed-sides), ab TEXT_L0
  function textAccent(cc, h, against, d, L) {
    try {
      return C().solveL(cc, h, against, 4.5, d, L);
    } catch (e) {
      if (!e || e.key !== 'mixed-sides') { throw e; }
      return C().solveL(cc, h, against, 4.5, d, TEXT_L0[String(d)]);
    }
  }
  function accents(seed, L, cs, h, roles, changes) {
    var c = C(), lt = roles.light, dk = roles.dark, kept = {}, a, at, cand;
    a = accentFill(seed, L, cs, h, [['#FFFFFF', -1], [lt.text, 1]], 'light', changes);
    lt.accent = a[0]; lt['on-accent'] = a[1]; kept.light = a[2];
    at = textAccent(cs, h, [lt.bg, lt.surface], -1, L);
    lt['accent-text'] = at.hex;
    if (at.hex !== seed) {
      changes.push({ role: 'accent-text', mode: 'light', from: seed, to: at.hex, key: 'accent-text-darker',
        values: { before: Math.min(c.contrast(seed, lt.bg), c.contrast(seed, lt.surface)), after: at.ratio } });
    }
    cand = c.oklchToHex(L, DARK_C * cs, h);
    a = accentFill(cand, L, DARK_C * cs, h, [[dk.text, -1], [dk.bg, 1]], 'dark', changes);
    dk.accent = a[0]; dk['on-accent'] = a[1]; kept.dark = a[2];
    // Dunkel geht die Linkfarbe vom dunklen Kandidaten aus; weicht sie ab, sagt das ein Hinweis wie hell
    at = textAccent(DARK_C * cs, h, [dk.bg, dk.surface], 1, L);
    dk['accent-text'] = at.hex;
    if (at.hex !== cand) {
      changes.push({ role: 'accent-text', mode: 'dark', from: cand, to: at.hex, key: 'accent-text-lighter',
        values: { before: Math.min(c.contrast(cand, dk.bg), c.contrast(cand, dk.surface)), after: at.ratio } });
    }
    return kept;
  }
  function okabe(ctx) {
    var cols = ctx.datasets['okabe-ito'].schemes[0].colors, out = [], i;
    for (i = 0; i < cols.length; i++) { if (cols[i].name !== 'black') { out.push(cols[i].hex); } }
    return out;
  }
  // Export-Option „Diagrammfarben einschließen“: Linkfarbe zuerst, dann Okabe-Ito mit ≥ 3:1 auf bg
  function charts(roles, ctx) {
    var c = C(), ok = okabe(ctx), j, i, r, pool, picked;
    for (j = 0; j < MODES.length; j++) {
      r = roles[MODES[j]];
      pool = [r['accent-text']];
      for (i = 0; i < ok.length; i++) { if (c.contrast(ok[i], r.bg) >= 3.0) { pool.push(ok[i]); } }
      picked = c.pickDistinct(pool, CHARTS, KINDS3, r['accent-text'], null);
      for (i = 0; i < picked.length; i++) { r['chart-' + (i + 1)] = picked[i]; }
    }
  }

  // ---------- Statusfarben
  function statusSurface(mode, hue) { return C().oklchToHex(STATUS_SURF[mode][0], STATUS_SURF[mode][1], hue); }
  // Kombination mit dem größten kleinsten Abstand; lexikographisch, Ersatz nur bei mehr als 1e-12 besser
  function bestCombo(cands, dist) {
    var best = -1, pick = null, a, b, cc, d, m1, m2, m3;
    var d01 = dist[0], d02 = dist[1], d03 = dist[2], d12 = dist[3], d13 = dist[4], d23 = dist[5];
    for (a = 0; a < cands[0].length; a++) {
      for (b = 0; b < cands[1].length; b++) {
        m1 = d01[a][b];
        if (m1 <= best + 1e-12) { continue; }
        for (cc = 0; cc < cands[2].length; cc++) {
          m2 = Math.min(m1, d02[a][cc], d12[b][cc]);
          if (m2 <= best + 1e-12) { continue; }
          for (d = 0; d < cands[3].length; d++) {
            m3 = Math.min(m2, d03[a][d], d13[b][d], d23[cc][d]);
            if (m3 > best + 1e-12) { best = m3; pick = [a, b, cc, d]; }
          }
        }
      }
    }
    return pick;
  }
  function worst(x, y) {
    var c = C();
    return Math.min(c.distance(x, y, 'normal'), c.distance(x, y, 'deutan'), c.distance(x, y, 'protan'));
  }
  function statusColors(roles, findings) {
    var c = C(), distinct = [], j, k, i, mode, r, cc, lo, steps, sd, cands, raw, surf, against, ok, hx, b;
    var idx = [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]], dist, pick, cols, md, mr, row, x, y, missing;
    for (j = 0; j < MODES.length; j++) {
      mode = MODES[j]; r = roles[mode];
      cc = STATUS_C[mode]; lo = BAND[mode][0]; steps = BAND[mode][1]; sd = STATUS_DIR[mode];
      cands = []; raw = [];
      for (k = 0; k < STATUS.length; k++) {
        surf = statusSurface(mode, STATUS[k][1]);
        r[STATUS[k][0] + '-subtle'] = surf;
        against = [r.bg, r.surface, surf];
        raw.push(c.solveL(cc, STATUS[k][1], against, 4.5, sd, 0.60).hex);
        ok = [];
        for (i = 0; i < steps; i++) {
          hx = c.oklchToHex(lo + i * 0.02, cc, STATUS[k][1]);
          if (ok.indexOf(hx) >= 0) { continue; }
          for (b = 0; b < against.length; b++) { if (c.contrast(hx, against[b]) < 4.5) { break; } }
          if (b === against.length) { ok.push(hx); }
        }
        cands.push(ok);
      }
      // Fehlt einem Status jeder Kandidat, gilt der Wert ohne Optimierung (ein Hinweis je Modus)
      missing = [];
      for (k = 0; k < STATUS.length; k++) { if (!cands[k].length) { missing.push(STATUS[k][0]); cands[k] = [raw[k]]; } }
      if (missing.length) { findings.push({ id: 'status-fallback', mode: mode, severity: 'note', values: { status: missing } }); }
      dist = [];
      for (k = 0; k < idx.length; k++) {
        row = [];
        for (x = 0; x < cands[idx[k][0]].length; x++) {
          row.push([]);
          for (y = 0; y < cands[idx[k][1]].length; y++) { row[x].push(worst(cands[idx[k][0]][x], cands[idx[k][1]][y])); }
        }
        dist.push(row);
      }
      pick = bestCombo(cands, dist);
      cols = [];
      for (k = 0; k < STATUS.length; k++) { cols.push(cands[k][pick[k]]); r[STATUS[k][0]] = cols[k]; }
      md = c.minDistance(cols, KINDS3); mr = c.minDistance(raw, KINDS3);
      distinct.push({ id: 'status', mode: mode, value: md.value, a: STATUS[md.i][0], b: STATUS[md.j][0], kind: md.kind,
        compare: { id: 'status-unoptimized', value: mr.value, a: mr.a, b: mr.b, kind: mr.kind } });
    }
    return distinct;
  }
  // Hinweis je Modus, wenn die Statusfarben näher liegen als der Vergleichswert Okabe-Ito
  function statusFindings(distinct, ctx, findings) {
    var ref = C().referenceValues(ctx.comparisons, ctx.datasets)['okabe-ito-7'].value, i, d;
    for (i = 0; i < distinct.length; i++) {
      d = distinct[i];
      if (d.id === 'status' && d.value < ref) {
        findings.push({ id: 'status-close', mode: d.mode, severity: 'note', values: { value: d.value } });
      }
    }
  }
  // Konfliktregel: Akzent weniger als 30° von 27° entfernt und C > 0,1
  function conflict(cs, h, findings) {
    if (h === null || h !== h || cs <= 0.1) { return; }
    var dh = Math.abs(h - 27.0) % 360;
    if (Math.min(dh, 360 - dh) < 30) { findings.push({ id: 'accent-error-conflict', mode: null, severity: 'note', values: { hue: h, chroma: cs } }); }
  }

  // ---------- Aufgabe
  function build(task, inp, ctx) {
    var c = C(), o = inp.options, seed = inp.seed, s = seedLch(seed, o.tone), L = s[0], cs = s[1], h = s[2], t = s[3], h0 = s[4];
    var roles = neutrals(h, t), changes = [], findings = [], kept, distinct, ev, j, k, r, v, rid, win, summary = [], mode, ids, lightLabel;
    kept = accents(seed, L, cs, h, roles, changes);
    distinct = statusColors(roles, findings);
    charts(roles, ctx);
    ev = c.evaluate(task, roles, 'skip');
    // Schwachstellen
    ids = ['accent-text'];
    for (k = 0; k < STATUS.length; k++) { ids.push(STATUS[k][0]); }
    for (j = 0; j < MODES.length; j++) {
      r = roles[MODES[j]];
      for (k = 0; k < ids.length; k++) {
        rid = ids[k];
        v = c.contrast(r[rid], r['surface-2']);
        if (v < 4.5) {
          findings.push({ id: rid === 'accent-text' ? 'unsafe-surface' : 'unsafe-surface-' + rid, mode: MODES[j], severity: 'note', values: { ratio: v } });
        }
      }
    }
    for (k = 0; k < ev.advisory.length; k++) {
      if (!ev.advisory[k].pass) {
        findings.push({ id: ev.advisory[k].finding, mode: ev.advisory[k].mode, severity: 'note', values: { ratio: ev.advisory[k].ratio } });
      }
    }
    for (j = 0; j < MODES.length; j++) {
      r = roles[MODES[j]];
      v = c.contrast(r['accent-text'], r.text);
      if (v < 3.0) {
        win = c.linkWindow(r.text, [r.bg, r.surface]);
        findings.push({ id: win.empty ? 'link-window-empty' : 'link-underline', mode: MODES[j], severity: 'note',
          values: { ratio: v } });
      }
    }
    statusFindings(distinct, ctx, findings);
    conflict(cs, h0, findings);
    for (j = 0; j < MODES.length; j++) {
      mode = MODES[j];
      if (kept[mode]) {
        lightLabel = roles[mode]['on-accent'] === (mode === 'light' ? '#FFFFFF' : roles[mode].text);
        summary.push('sum.' + mode + '.' + (lightLabel ? 'keep-light' : 'keep-dark'));
      }
    }
    var dsRoles = [];
    for (k = 0; k < CHARTS; k++) { dsRoles.push('chart-' + (k + 1)); }
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: roles, pairs: ev.pairs, decorative: ev.decorative,
      distinct: distinct, changes: changes, findings: findings, usage: {},
      extra: { datasets: { 'okabe-ito': dsRoles }, summary: summary } };
  }

  // ---------- Exporte
  function copyObj(o) { var r = {}, k; for (k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) { r[k] = o[k]; } } return r; }
  // Vorlage weak.status oder why.status mit dem engsten Statuspaar des Modus (aus palette.distinct);
  // {kind_l} ist die Sichtweise mit kleinem Anfangsbuchstaben für die Satzmitte
  function statusTemplate(palette, text, mode, key) {
    var d = null, i, hx = palette.roles[mode], kind;
    for (i = 0; i < palette.distinct.length; i++) { if (palette.distinct[i].id === 'status' && palette.distinct[i].mode === mode) { d = palette.distinct[i]; break; } }
    kind = text['cvd.' + d.kind];
    return text[key].split('{kind_l}').join(kind.slice(0, 1).toLowerCase() + kind.slice(1)).split('{kind}').join(kind)
      .split('{a}').join(text['st.' + d.a]).split('{b}').join(text['st.' + d.b])
      .split('{pair_dist}').join('{dist:' + hx[d.a] + '/' + hx[d.b] + '/' + d.kind + '}');
  }
  // Hinweis status-close je Modus mit dem engsten Paar (Prompt), Token {status_why} der Begründung,
  // ohne Hinweis hell der Satz why.status_plain
  function statusCtx(palette, ctx) {
    var text = copyObj(ctx.text), fs = [], i, f, key, light = false, why = [], p, c, inp = palette.input || {}, tone = (inp.options || {}).tone;
    // Idee je Tönung: ohne Tönung (neutral oder unbunte Farbe) und kräftig mit eigenem Text, sonst agent.idea
    if (tone && inp.seed) {
      key = seedLch(inp.seed, tone)[3] === 0 ? 'neutral' : tone;
      if (Object.prototype.hasOwnProperty.call(text, 'agent.idea.' + key)) { text['agent.idea'] = text['agent.idea.' + key]; }
    }
    for (i = 0; i < palette.findings.length; i++) {
      f = palette.findings[i];
      if (f.id === 'status-close') {
        if (f.mode === 'light') { light = true; }
        key = 'status-close-' + f.mode;
        text['finding.' + key] = statusTemplate(palette, text, f.mode, 'weak.status');
        f = copyObj(f); f.id = key;
      }
      fs.push(f);
    }
    for (i = 0; i < text.rationale.length; i++) {
      if (text.rationale[i] === '{status_why}') {
        if (light) { why.push(statusTemplate(palette, text, 'light', 'why.status')); }
        else if (Object.prototype.hasOwnProperty.call(text, 'why.status_plain')) { why.push(text['why.status_plain']); }
      } else { why.push(text.rationale[i]); }
    }
    text.rationale = why;
    p = copyObj(palette); p.findings = fs;
    c = copyObj(ctx); c.text = text;
    return [p, c];
  }
  function agent(palette, task, ctx, lang, opts) { var pc = statusCtx(palette, ctx); return chartsCss(X().agent(pc[0], task, pc[1], lang, opts), palette, ctx, lang, opts); }
  function rationale(palette, task, ctx, lang, opts) { var pc = statusCtx(palette, ctx); return X().rationale(pc[0], task, pc[1], lang, opts); }

  // Hinweis, wenn in einem Modus weniger als fünf Diagrammfarben 3:1 erreichen: in jedem Export mit Diagrammfarben
  function chartsFew(palette, ctx, lang, mode, opts) {
    var n = 0, k;
    if (!(opts || {}).charts) { return null; }
    for (k in palette.roles[mode]) { if (Object.prototype.hasOwnProperty.call(palette.roles[mode], k) && k.indexOf('chart-') === 0) { n++; } }
    return n < CHARTS ? ctx.text[n === 1 ? 'css.charts_few_1' : 'css.charts_few'].split('{n}').join(C().fmtCount(n, lang)) : null;
  }
  // Kommentar nach der letzten Zeile mit --chart- je Block (:root, dann je @media ein Modus)
  function chartsCss(text, palette, ctx, lang, opts) {
    var lines = text.split('\n'), i, block = 0, last = {}, b, ind, note, order = [];
    for (i = 0; i < lines.length; i++) {
      if (lines[i].indexOf('@media') === 0) { block++; }
      if (lines[i].replace(/^\s+/, '').indexOf('--chart-') === 0) { if (!Object.prototype.hasOwnProperty.call(last, block)) { order.push(block); } last[block] = i; }
    }
    for (i = order.length - 1; i >= 0; i--) {
      b = order[i];
      note = chartsFew(palette, ctx, lang, palette.modes[b], opts);
      if (note) {
        ind = lines[last[b]].slice(0, lines[last[b]].length - lines[last[b]].replace(/^\s+/, '').length);
        lines.splice(last[b] + 1, 0, ind + '/* ' + X().commentSafe(note) + ' */');
      }
    }
    return lines.join('\n');
  }
  function css(palette, task, ctx, lang, opts) { return chartsCss(X().css(palette, task, ctx, lang, opts), palette, ctx, lang, opts); }
  function tailwind(palette, task, ctx, lang, opts) { return chartsCss(X().tailwind(palette, task, ctx, lang, opts), palette, ctx, lang, opts); }
  // Hex-Liste: Hinweis als eigene Zeile nach der letzten Diagrammfarbe des Modus
  function hexList(palette, task, ctx, lang, opts) {
    var parts = X().hex(palette, task, ctx, lang, opts).split('\n\n'), i, k, rows, at, note;
    for (i = 0; i < palette.modes.length; i++) {
      note = chartsFew(palette, ctx, lang, palette.modes[i], opts);
      rows = parts[i].split('\n'); at = -1;
      for (k = 0; k < rows.length; k++) { if (rows[k].indexOf('chart-') === 0) { at = k; } }
      if (note && at >= 0) { rows.splice(at + 1, 0, note); parts[i] = rows.join('\n'); }
    }
    return parts.join('\n\n');
  }
  // Design-Tokens: Hinweis als Feld note unter $extensions, je Modus eine Datei
  function dtcg(palette, task, ctx, lang, opts) {
    var out = X().dtcg(palette, task, ctx, lang, opts), i, t, j, note;
    for (i = 0; i < out.length; i++) {
      note = chartsFew(palette, ctx, lang, palette.modes[i], opts);
      if (note) {
        t = out[i].text; j = t.indexOf('\n', t.indexOf('      "standard": ')) + 1;
        out[i].text = t.slice(0, j) + '      "note": ' + JSON.stringify(note) + ',\n' + t.slice(j);
      }
    }
    return out;
  }

  return { build: build, exports: { css: css, tailwind: tailwind, hex: hexList, dtcg: dtcg, agent: agent, rationale: rationale },
    tint: tint, seedLch: seedLch, neutrals: neutrals, statusColors: statusColors, statusFindings: statusFindings,
    conflict: conflict, agent: agent, rationale: rationale, STATUS: STATUS };
}));
