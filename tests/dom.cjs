'use strict';
// Kleines DOM für Node, nur Standardbibliothek: parst eine gebaute Seite, führt ihre Skripte (color.js, export.js,
// gen/*.js, site.js, ui/*.js) in node:vm aus und erlaubt Klicks und Eingaben. Es kann genau das, was web/site.js und
// web/ui/*.js nutzen: Elemente, Text, Kommentare, Attribute, innerHTML, Selektoren (Typ, #id, .klasse, [attr], [attr="v"],
// Nachfahre, Kind, Liste), Ereignisse mit Capture und Bubbling, location/history, localStorage und Zeitgeber, die der
// Test selbst weiterlaufen lässt. Kein Layout, kein CSS. Grundlage für tests/page.test.cjs (Laufzeitfehler im Rahmen).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const RAW = new Set(['script', 'style']);
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
function decode(s) {
  return s.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);/g, (m, k) => {
    if (k[0] === '#') return String.fromCodePoint(k[1] === 'x' ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10));
    return Object.prototype.hasOwnProperty.call(ENT, k) ? ENT[k] : m;
  });
}
const escText = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escAttr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;');

class Node {
  constructor(doc) { this.ownerDocument = doc; this.parentNode = null; this.childNodes = []; this._ls = []; }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get firstChild() { return this.childNodes[0] || null; }
  get textContent() { return this.childNodes.map((n) => (n.nodeType === 8 ? '' : n.textContent)).join(''); }
  set textContent(v) { this._replace([new Text(this.ownerDocument, String(v))]); }
  _replace(nodes) {
    for (const n of this.childNodes) n.parentNode = null;
    this.childNodes = [];
    for (const n of nodes) this.appendChild(n);
  }
  appendChild(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.push(n); return n; }
  removeChild(n) { const i = this.childNodes.indexOf(n); if (i >= 0) { this.childNodes.splice(i, 1); n.parentNode = null; } return n; }
  addEventListener(type, fn, capture) { this._ls.push({ type, fn, capture: capture === true || !!(capture && capture.capture) }); }
  removeEventListener(type, fn) { this._ls = this._ls.filter((l) => l.type !== type || l.fn !== fn); }
  dispatchEvent(ev) {
    const chain = [];
    for (let n = this.parentNode; n; n = n.parentNode) chain.push(n);
    ev.target = this;
    const call = (node, capture) => {
      for (const l of node._ls.slice()) {
        if (l.type !== ev.type || l.capture !== capture) continue;
        ev.currentTarget = node;
        l.fn.call(node, ev);
      }
    };
    for (let i = chain.length - 1; i >= 0 && !ev._stop; i--) call(chain[i], true);
    if (!ev._stop) { call(this, true); call(this, false); }
    if (ev.bubbles) for (let i = 0; i < chain.length && !ev._stop; i++) call(chain[i], false);
    return !ev.defaultPrevented;
  }
}
class Text extends Node {
  constructor(doc, data) { super(doc); this.nodeType = 3; this.data = data; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}
class Comment extends Node {
  constructor(doc, data) { super(doc); this.nodeType = 8; this.data = data; }
}
class ClassList {
  constructor(el) { this.el = el; }
  _get() { return (this.el.getAttribute('class') || '').split(/\s+/).filter(Boolean); }
  contains(c) { return this._get().includes(c); }
  add(...cs) { const l = this._get(); for (const c of cs) if (!l.includes(c)) l.push(c); this.el.setAttribute('class', l.join(' ')); }
  remove(...cs) { this.el.setAttribute('class', this._get().filter((c) => !cs.includes(c)).join(' ')); }
  toggle(c, force) { const on = force === undefined ? !this.contains(c) : !!force; if (on) this.add(c); else this.remove(c); return on; }
}
class Element extends Node {
  constructor(doc, name, attrs) {
    super(doc); this.nodeType = 1; this.localName = name.toLowerCase(); this.tagName = this.localName.toUpperCase();
    this.attrs = new Map(attrs || []); this.classList = new ClassList(this);
    const props = {};
    this.style = { setProperty(k, v) { props[k] = v; }, getPropertyValue(k) { return props[k] || ''; } };
  }
  get nodeName() { return this.tagName; }
  getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
  setAttribute(k, v) { this.attrs.set(k, String(v)); }
  hasAttribute(k) { return this.attrs.has(k); }
  removeAttribute(k) { this.attrs.delete(k); }
  get id() { return this.getAttribute('id') || ''; }
  get lang() { return this.getAttribute('lang') || ''; }
  get className() { return this.getAttribute('class') || ''; }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(v) { if (v) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  get type() { return this.localName === 'input' ? (this.getAttribute('type') || 'text').toLowerCase() : (this.getAttribute('type') || ''); }
  get value() { if (this._value === undefined) this._value = this.localName === 'textarea' ? this.textContent : (this.getAttribute('value') || ''); return this._value; }
  set value(v) { this._value = String(v); }
  get offsetHeight() { return 0; }
  get innerHTML() { return this.childNodes.map(serialize).join(''); }
  set innerHTML(html) { this._replace(parse(this.ownerDocument, String(html), RAW.has(this.localName) ? this.localName : null)); }
  get outerHTML() { return serialize(this); }
  matches(sel) { return parseSelector(sel).some((cx) => matchComplex(this, cx)); }
  closest(sel) { const cxs = parseSelector(sel); for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (cxs.some((cx) => matchComplex(n, cx))) return n; return null; }
  querySelectorAll(sel) { return queryAll(this, sel); }
  querySelector(sel) { return queryAll(this, sel)[0] || null; }
  click() { const ev = makeEvent('click', true); this.dispatchEvent(ev); }
  focus() { const d = this.ownerDocument, old = d.activeElement; if (old === this) return; d.activeElement = this; if (old && old !== d.body) old.dispatchEvent(makeEvent('focusout', true)); this.dispatchEvent(makeEvent('focusin', true)); }
  blur() { const d = this.ownerDocument; if (d.activeElement === this) { d.activeElement = d.body; this.dispatchEvent(makeEvent('focusout', true)); } }
  select() {}
}
function makeEvent(type, bubbles) {
  return { type, bubbles: !!bubbles, defaultPrevented: false, target: null, currentTarget: null, key: undefined,
    preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this._stop = true; } };
}
function serialize(n) {
  if (n.nodeType === 3) return n.parentNode && RAW.has(n.parentNode.localName) ? n.data : escText(n.data);
  if (n.nodeType === 8) return '<!--' + n.data + '-->';
  let s = '<' + n.localName;
  for (const [k, v] of n.attrs) s += v === '' ? ' ' + k : ' ' + k + '="' + escAttr(v) + '"';
  s += '>';
  if (VOID.has(n.localName)) return s;
  return s + n.childNodes.map(serialize).join('') + '</' + n.localName + '>';
}

// ---------- HTML-Parser (wohlgeformtes HTML wie aus build.py)
function parse(doc, html, rawIn) {
  const root = new Element(doc, '#fragment');
  if (rawIn) { root.appendChild(new Text(doc, html)); return root.childNodes.slice(); }
  const stack = [root];
  const top = () => stack[stack.length - 1];
  let i = 0;
  const n = html.length;
  while (i < n) {
    const lt = html.indexOf('<', i);
    if (lt < 0) { top().appendChild(new Text(doc, decode(html.slice(i)))); break; }
    if (lt > i) top().appendChild(new Text(doc, decode(html.slice(i, lt))));
    if (html.startsWith('<!--', lt)) {
      const end = html.indexOf('-->', lt + 4);
      top().appendChild(new Comment(doc, html.slice(lt + 4, end < 0 ? n : end)));
      i = end < 0 ? n : end + 3; continue;
    }
    if (html[lt + 1] === '!' || html[lt + 1] === '?') { const end = html.indexOf('>', lt); i = end < 0 ? n : end + 1; continue; }
    if (html[lt + 1] === '/') {
      const end = html.indexOf('>', lt);
      const name = html.slice(lt + 2, end).trim().toLowerCase();
      for (let k = stack.length - 1; k > 0; k--) { if (stack[k].localName === name) { stack.length = k; break; } }
      i = end + 1; continue;
    }
    const m = /^<([a-zA-Z][a-zA-Z0-9-]*)/.exec(html.slice(lt, lt + 64));
    if (!m) { top().appendChild(new Text(doc, '<')); i = lt + 1; continue; }
    const name = m[1].toLowerCase();
    let j = lt + m[0].length;
    const attrs = [];
    let selfClose = false;
    for (;;) {
      while (j < n && /\s/.test(html[j])) j++;
      if (html[j] === '>') { j++; break; }
      if (html[j] === '/' && html[j + 1] === '>') { selfClose = true; j += 2; break; }
      const am = /^[^\s=>\/]+/.exec(html.slice(j, j + 256));
      if (!am) { j++; continue; }
      const an = am[0].toLowerCase();
      j += am[0].length;
      while (j < n && /\s/.test(html[j])) j++;
      let val = '';
      if (html[j] === '=') {
        j++;
        while (j < n && /\s/.test(html[j])) j++;
        const q = html[j];
        if (q === '"' || q === "'") { const e = html.indexOf(q, j + 1); val = html.slice(j + 1, e); j = e + 1; }
        else { const vm2 = /^[^\s>]+/.exec(html.slice(j, j + 1024)); val = vm2 ? vm2[0] : ''; j += val.length; }
      }
      attrs.push([an, decode(val)]);
    }
    const el = new Element(doc, name, attrs);
    top().appendChild(el);
    if (RAW.has(name)) {
      const end = html.toLowerCase().indexOf('</' + name, j);
      el.appendChild(new Text(doc, html.slice(j, end < 0 ? n : end)));
      i = end < 0 ? n : html.indexOf('>', end) + 1; continue;
    }
    if (!selfClose && !VOID.has(name)) stack.push(el);
    i = j;
  }
  const out = root.childNodes.slice();
  for (const c of out) c.parentNode = null;
  return out;
}

// ---------- Selektoren
function parseSelector(sel) {
  const groups = [];
  let cur = '', depth = 0, quote = null;
  for (const ch of sel) {
    if (quote) { cur += ch; if (ch === quote) quote = null; continue; }
    if (ch === '"' || ch === "'") { quote = ch; cur += ch; continue; }
    if (ch === '[') depth++;
    if (ch === ']') depth--;
    if (ch === ',' && depth === 0) { groups.push(cur); cur = ''; continue; }
    cur += ch;
  }
  groups.push(cur);
  return groups.map((g) => parseComplex(g.trim()));
}
function parseComplex(s) {
  // → [{comb, simple}] von links nach rechts; comb ist ' ' (Nachfahre) oder '>' (Kind) vor dem Teil
  const parts = [];
  let i = 0, comb = null;
  while (i < s.length) {
    if (/\s/.test(s[i]) || s[i] === '>') {
      let c = ' ';
      while (i < s.length && (/\s/.test(s[i]) || s[i] === '>')) { if (s[i] === '>') c = '>'; i++; }
      comb = c; continue;
    }
    const simple = { tag: null, id: null, classes: [], attrs: [] };
    while (i < s.length && !/\s/.test(s[i]) && s[i] !== '>') {
      const ch = s[i];
      if (ch === '#' || ch === '.') {
        const m = /^[a-zA-Z0-9_-]+/.exec(s.slice(i + 1));
        if (ch === '#') simple.id = m[0]; else simple.classes.push(m[0]);
        i += 1 + m[0].length;
      } else if (ch === '[') {
        let j = i + 1, quote = null;
        while (j < s.length && (quote || s[j] !== ']')) { if (quote) { if (s[j] === quote) quote = null; } else if (s[j] === '"' || s[j] === "'") quote = s[j]; j++; }
        const body = s.slice(i + 1, j), eq = body.indexOf('=');
        if (eq < 0) simple.attrs.push([body.trim(), null]);
        else { let v = body.slice(eq + 1).trim(); if (/^["']/.test(v)) v = v.slice(1, -1); simple.attrs.push([body.slice(0, eq).trim(), v]); }
        i = j + 1;
      } else if (ch === '*') { i++; } else {
        const m = /^[a-zA-Z][a-zA-Z0-9-]*/.exec(s.slice(i));
        if (!m) throw new Error('Selektor nicht unterstützt: ' + s);
        simple.tag = m[0].toLowerCase(); i += m[0].length;
      }
    }
    parts.push({ comb: parts.length ? comb : null, simple });
    comb = null;
  }
  return parts;
}
function matchSimple(el, s) {
  if (el.nodeType !== 1) return false;
  if (s.tag && el.localName !== s.tag) return false;
  if (s.id && el.getAttribute('id') !== s.id) return false;
  for (const c of s.classes) if (!el.classList.contains(c)) return false;
  for (const [k, v] of s.attrs) { if (!el.hasAttribute(k)) return false; if (v !== null && el.getAttribute(k) !== v) return false; }
  return true;
}
function matchComplex(el, parts, k = parts.length - 1) {
  if (!matchSimple(el, parts[k].simple)) return false;
  if (k === 0) return true;
  const comb = parts[k].comb;
  for (let p = el.parentNode; p && p.nodeType === 1; p = p.parentNode) {
    if (matchComplex(p, parts, k - 1)) return true;
    if (comb === '>') return false;
  }
  return false;
}
function queryAll(root, sel) {
  const cxs = parseSelector(sel), out = [];
  const walk = (n) => { for (const c of n.childNodes) { if (c.nodeType === 1) { if (cxs.some((cx) => matchComplex(c, cx))) out.push(c); walk(c); } } };
  walk(root);
  return out;
}

// ---------- Dokument, Fenster, Zeitgeber
class Document extends Node {
  constructor() { super(null); this.ownerDocument = this; this.nodeType = 9; this.readyState = 'loading'; this.activeElement = null; }
  get documentElement() { return this.children[0] || null; }
  get body() { return this.querySelector('body'); }
  getElementById(id) { return queryAll(this, '#' + id)[0] || null; }
  querySelectorAll(sel) { return queryAll(this, sel); }
  querySelector(sel) { return queryAll(this, sel)[0] || null; }
  createElement(name) { return new Element(this, name); }
  createTextNode(t) { return new Text(this, t); }
  createRange() { return { selectNodeContents() {} }; }
  execCommand() { return false; }
}

// open(file, query, {noUi, storage, hash}) → {win, doc, data, tick(ms), flush(), $, $$, click(sel), input(el, value, type), search()}
// Lädt die Seite wie ein Browser: erst alle Skripte (defer), dann DOMContentLoaded. ui/*.js ist dabei, außer noUi.
function open(file, query, opts) {
  opts = opts || {};
  const html = fs.readFileSync(file, 'utf8');
  const doc = new Document();
  for (const n of parse(doc, html)) doc.appendChild(n);
  doc.activeElement = doc.body;
  let now = 0, seq = 0;
  const timers = new Map();
  const store = new Map(Object.entries(opts.storage || {}));
  const seg = path.relative(path.join(path.dirname(file), '..', '..'), path.dirname(file)).split(path.sep).join('/');
  const win = {
    document: doc, navigator: {}, isSecureContext: false, console,
    location: { pathname: '/' + seg + '/', search: query ? '?' + String(query).replace(/^\?/, '') : '', hash: opts.hash || '' },
    history: { replaceState(state, title, url) { const u = String(url), q = u.indexOf('?'), h = u.indexOf('#'); win.location.search = q < 0 ? '' : u.slice(q, h < 0 ? undefined : h); win.location.hash = h < 0 ? '' : u.slice(h); } },
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) },
    matchMedia: () => ({ matches: false }),
    setTimeout: (fn, ms) => { const id = ++seq; timers.set(id, { fn, at: now + (ms || 0), id }); return id; },
    clearTimeout: (id) => { timers.delete(id); },
    requestAnimationFrame: (fn) => win.setTimeout(fn, 16),
    addEventListener() {}, removeEventListener() {}
  };
  win.window = win; win.self = win;
  vm.createContext(win);
  const re = /<script src="([^"?]+)\?v=[^"]*" defer><\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (opts.noUi && /\/ui\//.test(m[1])) continue;
    const f = path.resolve(path.dirname(file), m[1]);
    vm.runInContext(fs.readFileSync(f, 'utf8'), win, { filename: f });
  }
  doc.readyState = 'complete';
  doc.dispatchEvent(makeEvent('DOMContentLoaded', false));
  function tick(ms) {
    const until = now + ms;
    for (;;) {
      let next = null;
      for (const t of timers.values()) if (t.at <= until && (!next || t.at < next.at || (t.at === next.at && t.id < next.id))) next = t;
      if (!next) break;
      timers.delete(next.id); now = next.at; next.fn();
    }
    now = until;
  }
  const api = {
    win, doc, tick, flush() { tick(5000); },
    $: (sel) => doc.querySelector(sel), $$: (sel) => doc.querySelectorAll(sel),
    data: JSON.parse(doc.getElementById('task-data') ? doc.getElementById('task-data').textContent : 'null'),
    click(sel) { const el = typeof sel === 'string' ? doc.querySelector(sel) : sel; if (!el) throw new Error('fehlt: ' + sel); el.click(); api.flush(); return el; },
    // Wert setzen und Ereignis auslösen (change bubbelt wie im Browser, input auch)
    input(el, value, type) { el = typeof el === 'string' ? doc.querySelector(el) : el; el.value = value; el.dispatchEvent(makeEvent(type || 'change', true)); api.flush(); return el; },
    search: () => win.location.search
  };
  api.flush();
  return api;
}

module.exports = { open, parse, Document, makeEvent };
