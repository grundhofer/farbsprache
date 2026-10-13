'use strict';
// Lädt die reinen UMD-Module aus web/ unverändert in einen node:vm-Kontext.
// FARBSPRACHE_JS_DIR=docs/assets lädt stattdessen die ausgelieferten, kompaktierten Dateien (gleiche Pfade unter web/).
// FS_CONST entsteht wie im Build: color-constants ∪ cvd ∪ {css_names}.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.join(__dirname, '..');
const JS_DIR = process.env.FARBSPRACHE_JS_DIR ? path.resolve(ROOT, process.env.FARBSPRACHE_JS_DIR) : path.join(ROOT, 'web');

// 'web/gen/charts.js' oder 'gen/charts.js' → Datei unter JS_DIR
function js(rel) { return path.join(JS_DIR, rel.replace(/^web\//, '')); }

function jload(rel) { return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')); }

function constants() {
  const k = Object.assign({}, jload('data/color-constants.json'), jload('data/cvd.json'));
  const names = jload('data/css-names.json');
  const css = {};
  for (const n of Object.keys(names)) { if (!n.startsWith('_')) css[n] = names[n]; }
  k.css_names = css;
  return k;
}

// load(['color.js', …], {extra}) → Kontext mit FS (z. B. ctx.FS.color). extra ergänzt FS_CONST.
function load(files, extra) {
  const context = { FS_CONST: Object.assign(constants(), extra || {}) };
  vm.createContext(context);
  for (const f of files) {
    const file = js(f);
    let src = fs.readFileSync(file, 'utf8');
    // ausgelieferte color.js bringt nach der Vermerkzeile FS_CONST mit; extra kommt danach dazu
    const head = /^(?:\/\*.*\*\/\n)?var FS_CONST=.*;\n/.exec(src);
    if (head) { vm.runInContext(head[0], context); Object.assign(context.FS_CONST, extra || {}); src = src.slice(head[0].length); }
    vm.runInContext(src, context, { filename: file });
  }
  return context;
}

// Objekte aus dem vm-Kontext haben fremde Prototypen; für deepStrictEqual als JSON übernehmen (NaN → null).
function plain(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }

// snake_case (Python) → camelCase (JS), z. B. fmt_pct_up → fmtPctUp, fmt_L → fmtL
function camel(name) { return name.replace(/_([a-zA-Z0-9])/g, (_, c) => c.toUpperCase()); }

module.exports = { ROOT, jload, constants, load, plain, camel, js };
