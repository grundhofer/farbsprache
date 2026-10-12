/* Leseseiten von P5 (Kurz erklärt, Methode, Quellen): Der Sprachlink nimmt das Sprungziel (#anker) mit, denn die
   Anker sind in beiden Sprachen gleich (2.3). Dazu der Knopf „Brücke zeigen“ im Demo context (Spezifikation 3.9):
   Er schaltet aria-pressed und data-bridge am Muster um; patterns/demo-context.html zeigt die Brücke über
   [data-bridge="on"]. Kein Blinken, keine Animation. */
(function (root) {
  'use strict';
  var doc = root.document;
  if (!doc || !doc.addEventListener) { return; }
  function syncLang() {
    var a = doc.querySelector('.tb-lang a');
    if (!a) { return; }
    if (!a.getAttribute('data-base')) { a.setAttribute('data-base', a.getAttribute('href')); }
    a.setAttribute('href', a.getAttribute('data-base') + (root.location.hash || ''));
  }
  syncLang();
  root.addEventListener('hashchange', syncLang);
  doc.addEventListener('click', function (ev) {
    var b = ev.target.closest ? ev.target.closest('[data-bridge-toggle]') : null;
    if (!b) { return; }
    var box = b.parentNode ? b.parentNode.querySelector('[data-bridge]') : null;
    var on = b.getAttribute('aria-pressed') !== 'true';
    b.setAttribute('aria-pressed', String(on));
    if (box) { box.setAttribute('data-bridge', on ? 'on' : 'off'); }
  });
}(typeof globalThis !== 'undefined' ? globalThis : this));
