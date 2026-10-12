/* Palette prüfen: DOM-Anbindung (Spezifikation 3.8, 4.9). Rechnen und Rendern übernimmt FS.check (web/check.js);
   hier stehen nur Eingabe, Zustand in der URL (f, r, bgi), Knöpfe und Live-Region. Kopieren, Speichern und
   Umbrechen erledigt site.js über data-copy, data-copy-from, data-download und data-wrap. */
(function (root) {
  'use strict';
  var doc = root.document;
  if (!doc || !doc.getElementById) { return; }
  var dataEl = doc.getElementById('check-data');
  var input = doc.getElementById('chk-input');
  var out = doc.getElementById('chk-out');
  var exp = doc.getElementById('chk-exp');
  if (!dataEl || !input || !out || !exp || !root.FS || !root.FS.check) { return; }
  var D = JSON.parse(dataEl.textContent);
  var CK = root.FS.check, C = root.FS.color;
  var countEl = doc.getElementById('chk-count'), runBtn = doc.getElementById('chk-run'), statusEl = doc.getElementById('status');
  var staticOut = out.innerHTML, staticExp = exp.innerHTML;
  var st = { roles: null, confirmed: false, bgi: null }, model = null, prevText = null, changed = [], newKeys = [], timer = null, lastText = null;

  function fill(tmpl, values) { return tmpl.replace(/\{([a-z_]+)\}/g, function (m, k) { return Object.prototype.hasOwnProperty.call(values, k) ? values[k] : m; }); }
  function announce(text) {
    if (!statusEl) { return; }
    statusEl.textContent = '';
    setTimeout(function () { statusEl.textContent = text; }, 30);
  }
  function today() {
    var d = new Date(), m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
  }
  function ctxR(url) {
    return { lang: D.lang, T: D.T, F: D.F, refs: D.refs, cfg: D.cfg, rules: D.rules, sources: D.sources,
      comparisons: D.comparisons, paths: D.paths, url: url, date: today() };
  }
  function replaceUrl(q) {
    try { root.history.replaceState(null, '', root.location.pathname + (q ? '?' + q : '') + root.location.hash); } catch (e) { /* file:// */ }
  }
  function syncLang(q) {
    var a = doc.querySelector('.tb-lang a');
    if (!a) { return; }
    if (!a.getAttribute('data-base')) { a.setAttribute('data-base', a.getAttribute('href')); }
    a.setAttribute('href', a.getAttribute('data-base') + (q ? '?' + q : '') + (root.location.hash || ''));
  }
  function setCount(n) {
    if (!countEl) { return; }
    countEl.textContent = n === null ? '' : n === 0 ? D.T['in.count0'] : n === 1 ? D.T['in.count1'] : fill(D.T['in.count'], { n: C.fmtCount(n, D.lang) });
  }
  function keysOf(m) {
    var k = [], i, j;
    if (!m) { return k; }
    for (i = 0; i < m.ctxs.length; i++) { for (j = 0; j < m.ctxs[i].findings.length; j++) { k.push(m.ctxs[i].findings[j].key); } }
    return k;
  }
  function showCtx(ctx) {
    var have = out.querySelector('.chk-ctx[data-ctx="' + ctx + '"]') ? ctx : 'light';
    out.setAttribute('data-show', have);
    Array.prototype.forEach.call(out.querySelectorAll('[data-ctxpick]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-ctxpick') === have)); });
  }
  function nFindings(m) { return keysOf(m).length; }
  // Nach dem Neurendern steht der Fokus wieder an einem passenden Bedienelement statt am Seitenanfang
  function refocus(sel) { var el = sel ? out.querySelector(sel) : null; if (el && el.focus) { el.focus(); } }

  // Neu rechnen. keep: Rollen, Bestätigung und Hintergrund behalten (Übernehmen, Rückgängig, Menüs).
  // applied: {hex, ctx} der übernommenen Farbe; „Rückgängig“ steht dann an genau dieser Farbe, auch wenn sie mit
  // einer anderen zusammenfällt und sich die Reihenfolge verschiebt.
  function compute(keep, prevKeys, applied) {
    var text = input.value;
    lastText = text;
    if (!keep) { st = { roles: null, confirmed: false, bgi: null }; changed = []; newKeys = []; prevText = null; }
    if (!text.replace(/[ \t\r\n\f]/g, '')) {
      model = null; out.innerHTML = staticOut; exp.innerHTML = staticExp; setCount(null);
      replaceUrl(''); syncLang(''); showCtx('light');
      return;
    }
    var sc = CK.scan(text, D.cfg);
    if (st.roles && st.roles.length !== sc.colors.length) { st.roles = null; st.confirmed = false; }
    if (st.bgi !== null && st.bgi >= sc.colors.length) { st.bgi = null; }
    model = CK.analyze(sc, D.cfg, D.refs, { roles: st.roles, confirmed: st.confirmed, bgi: st.bgi });
    if (applied) {
      changed = [];
      for (var g = 0; g < model.colors.length; g++) {
        if (model.colors[g].ctx === applied.ctx && model.colors[g].hex === applied.hex && model.colors[g].alpha === 1) { changed = [g]; break; }
      }
    }
    if (prevKeys) {
      var now = keysOf(model), i;
      newKeys = [];
      for (i = 0; i < now.length; i++) { if (prevKeys.indexOf(now[i]) < 0) { newKeys.push(now[i]); } }
    }
    var q = CK.query(model, st.bgi), R = ctxR(D.url + (q ? '?' + q : '')), show = out.getAttribute('data-show') || 'light';
    out.innerHTML = CK.render(model, R, { new_keys: newKeys, changed: changed });
    exp.innerHTML = CK.exportHtml(model, R);
    setCount(sc.colors.length);
    replaceUrl(q); syncLang(q); showCtx(show);
  }
  function rolesNow() {
    var r = [], i;
    for (i = 0; i < model.colors.length; i++) { r.push(model.colors[i].role || null); }
    return r;
  }
  function firstNewText() {
    var i, j, f;
    for (i = 0; i < model.ctxs.length; i++) {
      for (j = 0; j < model.ctxs[i].findings.length; j++) {
        f = model.ctxs[i].findings[j];
        if (newKeys.indexOf(f.key) >= 0) { return CK.plain(CK.findingMessage(ctxR(D.url), model, f)); }
      }
    }
    return null;
  }

  // Eingabe: entprellt wie die Aufgabenseiten (120 ms); jede Tastatureingabe setzt Rollen und Hintergrund zurück
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { (root.requestAnimationFrame || setTimeout)(function () { compute(false); }); }, 120);
  });
  if (runBtn) {
    runBtn.addEventListener('click', function () {
      // Rollen und Hintergrund nur behalten, wenn der Text seit der letzten Rechnung gleich ist
      clearTimeout(timer); compute(input.value === lastText);
      if (model) { var nf = nFindings(model); announce(fill(D.T[nf === 1 ? 'live.done_1' : 'live.done'], { n: C.fmtCount(nf, D.lang) })); }
    });
  }

  out.addEventListener('click', function (ev) {
    var b = ev.target.closest ? ev.target.closest('[data-bgi],[data-confirm],[data-apply],[data-undo],[data-ctxpick],[data-mxpick]') : null;
    if (!b || !out.contains(b)) { return; }
    if (b.hasAttribute('data-ctxpick')) { showCtx(b.getAttribute('data-ctxpick')); return; }
    if (b.hasAttribute('data-mxpick')) {
      var box = b.closest('.chk-mx'), g = b.getAttribute('data-mxpick');
      Array.prototype.forEach.call(box.querySelectorAll('[data-mxpick]'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      Array.prototype.forEach.call(box.querySelectorAll('[data-mxlist]'), function (l) { l.classList.toggle('on', l.getAttribute('data-mxlist') === g); });
      return;
    }
    if (!model) {
      // Beispiel: erst übernehmen, dann wie eigene Eingabe behandeln
      input.value = D.cfg.example;
      compute(false);
      if (!model) { return; }
    }
    if (b.hasAttribute('data-bgi')) { st.bgi = parseInt(b.getAttribute('data-bgi'), 10); compute(true); refocus('[data-bgi="' + st.bgi + '"]'); return; }
    if (b.hasAttribute('data-confirm')) {
      st.roles = rolesNow(); st.confirmed = true; compute(true); announce(D.T['live.confirmed']);
      refocus('.rl-sel');
      return;
    }
    if (b.hasAttribute('data-apply')) {
      var gi = parseInt(b.getAttribute('data-apply'), 10), to = b.getAttribute('data-to'), c = model.colors[gi];
      if (!c || !/^#[0-9A-F]{6}$/.test(to)) { return; }
      var prevKeys = keysOf(model), text = input.value, spans = c.spans.slice().sort(function (p, q) { return q[0] - p[0]; }), k;
      prevText = text;
      for (k = 0; k < spans.length; k++) { text = text.slice(0, spans[k][0]) + to + text.slice(spans[k][1]); }
      input.value = text;
      compute(true, prevKeys, { hex: to, ctx: c.ctx });
      refocus('[data-undo]');
      var msg = firstNewText();
      announce(msg ? fill(D.T['live.new'], { text: msg }) : D.T['live.applied']);
      return;
    }
    if (b.hasAttribute('data-undo') && prevText !== null) {
      var ug = changed.length ? changed[0] : -1;
      input.value = prevText; prevText = null; changed = []; newKeys = [];
      compute(true); announce(D.T['live.undone']);
      refocus(out.querySelector('[data-apply="' + ug + '"]') ? '[data-apply="' + ug + '"]' : '.chk-bar [data-copy]');
    }
  });
  out.addEventListener('change', function (ev) {
    var sel = ev.target;
    if (!sel || !sel.classList || !sel.classList.contains('rl-sel') || !model) { return; }
    var r = st.roles || rolesNow(), g = parseInt(sel.getAttribute('data-role'), 10);
    r = r.slice(); r[g] = sel.value === '-' ? null : sel.value;
    st.roles = r;
    compute(true);
    var again = out.querySelector('select[data-role="' + g + '"]');
    if (again) { again.focus(); }
  });

  // Reiter der Exporte (die Exporte werden neu gerendert, deshalb über Delegation)
  function selectTab(tab, focus) {
    Array.prototype.forEach.call(exp.querySelectorAll('[role="tab"]'), function (x) {
      var on = x === tab;
      x.setAttribute('aria-selected', String(on));
      if (on) { x.removeAttribute('tabindex'); } else { x.setAttribute('tabindex', '-1'); }
      var panel = doc.getElementById(x.getAttribute('aria-controls'));
      if (panel) { panel.classList.toggle('on', on); }
    });
    if (focus) { tab.focus(); }
  }
  exp.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target.closest('[role="tab"]') : null;
    if (t && exp.contains(t)) { selectTab(t, false); }
  });
  exp.addEventListener('keydown', function (ev) {
    var t = ev.target, tabs, i, d;
    if (!t || t.getAttribute('role') !== 'tab') { return; }
    d = ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0;
    if (!d) { return; }
    ev.preventDefault();
    tabs = Array.prototype.slice.call(exp.querySelectorAll('[role="tab"]'));
    i = tabs.indexOf(t);
    selectTab(tabs[(i + d + tabs.length) % tabs.length], true);
  });

  // Erster Zustand aus der URL (f, r, bgi); ohne f bleibt das statische Beispiel stehen
  var rq = CK.readQuery(root.location.search, D.cfg);
  if (rq.f) {
    input.value = CK.stateText(rq.f, rq.r);
    var sr = CK.stateRoles(rq.r);
    st.roles = sr.roles; st.confirmed = sr.confirmed;
    st.bgi = rq.bgi;
    compute(true);
  } else if (rq.dirty) {
    replaceUrl('');
  }
}(typeof globalThis !== 'undefined' ? globalThis : this));
