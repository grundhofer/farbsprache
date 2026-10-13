/* DOM-Haken der Aufgabe KI-Bild (FS.ui['ai-image']): Rollen an den vier Feldern „Eigene Farben“, Werte der drei
   Vorschläge aus der eigenen Farbe (kleinster Abstand normal, Rot-Grün, Graustufen) und der
   Hinweis auf feste Anteile 80 · 20 bei zwei Farben. Lücken in „Eigene Farben“ meldet der Haken, statt Felder nachrücken zu
   lassen (jedes Feld hat seine Rolle). Eigene Farben (f) gehen vor Vorschlag und Startpalette:
   Solange f gilt, drückt der Rahmen keinen Chip dieser beiden Reihen; wer einen Vorschlag wählt, verlässt f.
   Gerechnet wird mit FS.gen['ai-image'] und FS.color, ohne Startpaletten neu zu rechnen. Alle eingesetzten Werte sind
   Zahlen oder geprüfte Hex-Werte. */
(function (root) {
  'use strict';
  root.FS = root.FS || {}; root.FS.ui = root.FS.ui || {};
  var ROLES = ['dominant', 'secondary', 'accent', 'background'], KINDS = ['calm', 'contrast', 'signal'];
  function txt(api, k) { var t = api.data.text || {}; return Object.prototype.hasOwnProperty.call(t, k) ? t[k] : ''; }
  function fill(t, v) { return t.replace(/\{([a-z]+)\}/g, function (m, k) { return Object.prototype.hasOwnProperty.call(v, k) ? v[k] : m; }); }
  function fields() { return document.querySelectorAll('[data-ctl="f"] input'); }
  root.FS.ui['ai-image'] = {
    init: function (api) {
      var slot = api.slot('bar'), C = root.FS.color, i, inp = fields();
      if (!slot) { return; }
      slot.innerHTML = '<div class="ai-sug" hidden><p class="ctl-label">' + C.esc(txt(api, 'ui.sug_h')) + '</p><ul class="plain"></ul>' +
        '<p class="hint">' + C.esc(txt(api, 'ui.sug_note')) + '</p></div><p class="hint ai-two" hidden>' + C.esc(txt(api, 'ui.w_two')) + '</p>';
      for (i = 0; i < inp.length && i < ROLES.length; i++) { inp[i].setAttribute('aria-label', txt(api, 'ui.f_' + ROLES[i])); }
      // Jedes Feld behält seine Rolle: Bleibt ein Feld vor einem gefüllten leer, rücken die Farben nicht nach.
      // Die Seite meldet die Lücke und hält die Änderung an, bevor der Rahmen f setzt (Fangphase vor seinem Handler).
      var box = document.querySelector('[data-ctl="f"]'), err;
      if (box) {
        // dieselbe Fehlerzeile wie für ungültige Farben (Rahmen, pages/task.py)
        err = box.querySelector('.err');
        if (!err) { err = document.createElement('p'); err.setAttribute('class', 'err'); err.setAttribute('aria-live', 'polite'); box.appendChild(err); }
        box.addEventListener('change', function (ev) {
          var fs = fields(), last = -1, gap = false, j;
          for (j = 0; j < fs.length; j++) { if (fs[j].value.replace(/\s/g, '')) { last = j; } }
          for (j = 0; j < fs.length; j++) {
            if (j < last && !fs[j].value.replace(/\s/g, '')) { gap = true; fs[j].setAttribute('aria-invalid', 'true'); } else { fs[j].removeAttribute('aria-invalid'); }
          }
          err.textContent = gap ? txt(api, 'ui.f_gap') : '';
          if (gap) { ev.stopPropagation(); }
        }, true);
      }
      // Ein Vorschlag gilt erst ohne eigene Farben: Die Wahl eines Vorschlags hebt f auf
      var sc = document.querySelectorAll('[data-ctl="s"] button');
      for (i = 0; i < sc.length; i++) {
        sc[i].addEventListener('click', function () { var st = api.state(); if (st.o && st.o.f) { api.set('f', null); } });
      }
    },
    render: function (palette, state, api) {
      var slot = api.slot('bar'), gen = (root.FS.gen || {})['ai-image'], C = root.FS.color, lang = api.lang;
      if (!slot || !gen || !palette) { return; }
      var box = slot.querySelector('.ai-sug'), two = slot.querySelector('.ai-two'), r = palette.roles['default'] || {}, rows = '', i, v, main = 0;
      if (!box || !two) { return; }
      if (state.c) {
        for (i = 0; i < KINDS.length; i++) {
          v = gen.suggestValues(state.c, KINDS[i]);
          rows += '<li>' + C.esc(fill(txt(api, 'ui.sug_row'), { name: txt(api, 'ctl.s.' + KINDS[i]), n: C.fmtDist(v.normal, lang),
            rg: C.fmtDist(v.redgreen, lang), g: C.fmtDist(v.gray, lang) })) + '</li>';
        }
        box.querySelector('ul').innerHTML = rows;
      }
      box.hidden = !state.c;
      for (i = 0; i < ROLES.length; i++) { if (ROLES[i] !== 'background' && Object.prototype.hasOwnProperty.call(r, ROLES[i])) { main++; } }
      two.hidden = main !== 2;
      slot.hidden = box.hidden && two.hidden;
      var inp = fields();
      for (i = 0; i < inp.length && i < ROLES.length; i++) { inp[i].setAttribute('placeholder', r[ROLES[i]] || ''); }
    }
  };
}(typeof globalThis !== 'undefined' ? globalThis : this));
