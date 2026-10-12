/* DOM-Haken der Testaufgabe (FS.ui.fixture): zeigt, wie ein Paket eigene Bedienteile in einen Slot hängt.
   init(api) einmal nach dem Laden, render(palette, state, api) nach jeder Neuberechnung. */
(function (root) {
  'use strict';
  root.FS = root.FS || {}; root.FS.ui = root.FS.ui || {};
  root.FS.ui.fixture = {
    init: function (api) {
      var slot = api.slot('palette');
      if (!slot) { return; }
      slot.hidden = false;
      slot.innerHTML = '<p class="hint" data-fixture-ui></p>';
    },
    render: function (palette, state, api) {
      var el = api.slot('palette') && api.slot('palette').querySelector('[data-fixture-ui]');
      if (!el) { return; }
      var n = 0, k;
      for (k in palette.roles.light) { if (Object.prototype.hasOwnProperty.call(palette.roles.light, k)) { n++; } }
      el.textContent = (api.lang === 'de' ? 'Rollen im hellen Modus: ' : 'Roles in light mode: ') + n;
    }
  };
}(typeof globalThis !== 'undefined' ? globalThis : this));
