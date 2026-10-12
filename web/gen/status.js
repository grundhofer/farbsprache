/* Generator der Aufgabe Statusfarben (FS.gen.status). Spiegel von tools/gen/status.py.
   T2 nach Spezifikation 4.3 auf den Neutraltönen von T1 (4.2); nutzt FS.gen.website (gen_deps).
   Eigenes Format: HTML-Snippet mit vier Meldungen, Icon und Wort (5.8). */
(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  root.FS = root.FS || {}; root.FS.gen = root.FS.gen || {}; root.FS.gen.status = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  function C() { return root.FS.color; }
  function X() { return root.FS.export; }
  function W() { return root.FS.gen.website; }

  var ICONS = {
    danger: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    warning: '<path d="M12 3 2 20h20Z"/><path d="M12 9v5"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/>',
    success: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><circle cx="12" cy="7.5" r="1" fill="currentColor" stroke="none"/>'
  };

  function build(task, inp, ctx) {
    var w = W(), s = w.seedLch(inp.seed, inp.options.tone), base = w.neutrals(s[2], s[3]), roles = {}, modes = ['light', 'dark'], i, k, keys = ['bg', 'surface', 'text'];
    for (i = 0; i < modes.length; i++) {
      roles[modes[i]] = {};
      for (k = 0; k < keys.length; k++) { roles[modes[i]][keys[k]] = base[modes[i]][keys[k]]; }
    }
    var findings = [], distinct = w.statusColors(roles, findings), ev = C().evaluate(task, roles, 'skip');
    w.statusFindings(distinct, ctx, findings);
    w.conflict(s[1], s[4], findings);
    return { task: task.id, preset: null, input: inp, name_de: null, name_en: null,
      modes: task.modes.slice(), roles: roles, pairs: ev.pairs, decorative: ev.decorative,
      distinct: distinct, changes: [], findings: findings, usage: {}, extra: { summary: ['sum.gray'] } };
  }

  // HTML-Snippet (5.8): vier Meldungen mit Icon und Wort, dazu die Regeln .msg-<status>
  function html(palette, task, ctx, lang, opts) {
    var T = ctx.text, x = X(), head, out, i, st = W().STATUS, sid;
    head = [x.header(ctx), T['html.needs']].concat(x.notices(palette, ctx, task, opts), [x.presub(ctx.core.link, ctx)]);
    out = ['<!-- ' + head[0]];
    for (i = 1; i < head.length; i++) { out.push('     ' + head[i]); }
    out[out.length - 1] += ' -->';
    out.push('<style>', '.msg{display:flex;gap:.5em;align-items:flex-start;padding:.75em 1em;margin:0 0 .5em}',
      '.msg svg{flex:none;width:1.25em;height:1.25em;margin-top:.1em}', '.msg p{margin:0}');
    for (i = 0; i < st.length; i++) {
      sid = st[i][0];
      out.push('.msg-' + sid + '{color:var(--' + sid + ');background:var(--' + sid + '-subtle);border-left:4px solid var(--' + sid + ')}');
    }
    out.push('</style>');
    for (i = 0; i < st.length; i++) {
      sid = st[i][0];
      out.push('<div class="msg msg-' + sid + '" role="' + (sid === 'danger' ? 'alert' : 'status') + '">');
      out.push('  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
        'stroke-linejoin="round" aria-hidden="true">' + ICONS[sid] + '</svg>');
      out.push('  <p><strong>' + C().esc(T['html.word.' + sid]) + '</strong> ' + C().esc(T['html.text.' + sid]) + '</p>');
      out.push('</div>');
    }
    return out.join('\n');
  }

  return { build: build, exports: { html: html,
    agent: function (p, t, c, l, o) { return W().agent(p, t, c, l, o); },
    rationale: function (p, t, c, l, o) { return W().rationale(p, t, c, l, o); } } };
}));
