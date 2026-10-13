/* DOM-Haken der Aufgabe Diagramm (FS.ui.charts).
   - blendet Anzahl bei „Eine Linie hervorheben“ aus (dort fest), Darstellung außer bei Gruppen und Familie bei Hervorhebung
   - zeigt beim Versuch, über acht Farben zu gehen, den Weg „Eine Linie hervorheben“ (Stepper bietet höchstens acht)
   - bietet bei Verlauf und Abweichung mit eigener Farbe den Knopf „Verlauf aus deiner Farbe“ an
   Texte kommen aus #task-data (COPY charts ui.*), nie aus Benutzereingaben. */
(function (root) {
  'use strict';
  root.FS = root.FS || {}; root.FS.ui = root.FS.ui || {};
  var doc = root.document;
  function ctl(id) { return doc.querySelector('[data-ctl="' + id + '"]'); }
  root.FS.ui.charts = {
    init: function (api) {
      var T = api.data.text, bar = api.slot('bar'), pal = api.slot('palette');
      if (bar) {
        bar.innerHTML = '<div class="ch-max" data-ch-max hidden><p class="hint"></p><button type="button" class="btn" data-ch-hl></button></div>';
        bar.querySelector('.hint').textContent = T['ui.max'];
        bar.querySelector('[data-ch-hl]').textContent = T['ui.max-btn'];
        bar.querySelector('[data-ch-hl]').addEventListener('click', function () {
          bar.querySelector('[data-ch-max]').hidden = true;
          api.set('t', 'hl');
        });
        bar.hidden = false;
      }
      if (pal) {
        pal.innerHTML = '<p data-ch-seed hidden><button type="button" class="btn"></button></p>';
        pal.querySelector('button').textContent = T['ui.seed-btn'];
        pal.querySelector('button').addEventListener('click', function () { api.set('fam', 'seed'); });
        pal.hidden = false;
      }
      var n = ctl('n'), inp = n ? n.querySelector('input') : null;
      function showMax() {
        var box = bar ? bar.querySelector('[data-ch-max]') : null;
        if (box && box.hidden) { box.hidden = false; api.announce(T['ui.max']); }
      }
      function isCat() { var b = doc.querySelector('[data-ctl="t"] [aria-pressed="true"]'); return !!b && b.getAttribute('data-val') === 'cat'; }
      if (n && inp) {
        // Capture-Phase: läuft vor dem Stepper des Rahmens, liest also den Wert vor dem Klick
        n.addEventListener('click', function (ev) {
          var b = ev.target && ev.target.closest ? ev.target.closest('[data-step="1"]') : null;
          if (b && isCat() && parseInt(inp.value, 10) >= 8) { showMax(); }
        }, true);
        inp.addEventListener('input', function () { if (isCat() && parseInt(inp.value, 10) > 8) { showMax(); } });
      }
    },
    render: function (palette, state, api) {
      var o = palette && palette.input ? palette.input.options : null, el, box;
      if (!o) { return; }
      el = ctl('n'); if (el) { el.hidden = o.t === 'hl'; }
      el = ctl('mark'); if (el) { el.hidden = o.t !== 'cat'; }
      el = ctl('fam'); if (el) { el.hidden = o.t === 'hl'; }
      box = api.slot('bar') && api.slot('bar').querySelector('[data-ch-max]');
      if (box && !(o.t === 'cat' && o.n >= 8)) { box.hidden = true; }
      el = api.slot('palette') && api.slot('palette').querySelector('[data-ch-seed]');
      if (el) { el.hidden = !(state.c && (o.t === 'seq' || o.t === 'div') && o.fam !== 'seed'); }
    }
  };
}(typeof globalThis !== 'undefined' ? globalThis : this));
