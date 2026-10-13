[Deutsch lesen → README.de.md](README.de.md)

# Farbsprache

**Choose, check and copy colors.** Every number is calculated.

Farbsprache helps you choose colors. Pick your task, such as a website, a chart or a presentation, and you immediately get a finished palette with named roles, checked contrast and code to copy. Enter your own color and the page recalculates everything and tells you what it changed and why.

**[Open the website](https://grundhofer.github.io/farbsprache/)** ·
[Deutsch](https://grundhofer.github.io/farbsprache/de/) ·
[English](https://grundhofer.github.io/farbsprache/en/)

![German start page “Wofür brauchst du Farben?” (What do you need colors for?) with the tasks and a checked row of colors.](og.png)

## What it is about

Many color tools show palettes. Farbsprache starts from the task: 7 tasks with 22 starter palettes and 287 checked color pairs. Every contrast figure is calculated when the site is built or in your browser, never by hand. The yardstick is WCAG 2.2. 44 rules carry an evidence level (standard, research, convention, unproven). Rules, explained entries, method and menu paths rest on 83 sources in total.

## Contents

- **[Tasks](https://grundhofer.github.io/farbsprache/en/):** website or app, status colors, chart or dashboard, presentation, logo and brand, text on image, AI image. Every task has a finished role palette, a fixed reference pattern, a simulation of color vision deficiency and exports to copy.
- **[Check palette](https://grundhofer.github.io/farbsprache/en/check/):** paste your own colors, see contrasts and distances, apply fixes.
- **[Method](https://grundhofer.github.io/farbsprache/en/method/):** which formulas the page uses, how it rounds, what it checks and what it does not.

## Build locally

Requires Python 3.12+ and Node 22 for the script tests. Nothing to install.

```sh
python3 build.py --fixtures
python3 tools/parity.py
FARBSPRACHE_REQUIRE_BUILD=1 python3 -m unittest discover -s tests -v
FARBSPRACHE_REQUIRE_BUILD=1 node --test tests/*.test.cjs
FARBSPRACHE_REQUIRE_BUILD=1 FARBSPRACHE_JS_DIR=docs/assets node --test tests/*.test.cjs
python3 -m http.server 8000 --directory docs
```

## Project layout

| Path | Content |
| --- | --- |
| `build.py` | Static generator: checks, starter palettes, pages, language switch, README |
| `pages/` | Start page, task page frame, check, explained, method, sources, legal notice |
| `tools/color.py`, `web/color.js` | Color core in Python and JavaScript with the same test vectors |
| `tools/export.py`, `web/export.js` | Exports: CSS, Tailwind v4, design tokens, hex list, prompt, rationale |
| `tools/gen/`, `web/gen/` | Generators per task |
| `tools/checks.py` | Data checks before the build |
| `data/` | Tasks, rules, explained entries, sources, data sets, constants, test vectors, legal notice details |
| `patterns/` | Reference patterns and mini previews |
| `web/` | Site style, site script, theme, texts |
| `tests/` | Python and Node tests, golden files, test task |
| `docs/` | Generated website; not checked in |

GitHub Actions checks everything and publishes `main` to GitHub Pages. How to contribute is in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Code, including `patterns/` and `.github/`: [MIT](LICENSE). Texts: [CC BY 4.0](LICENSE-CONTENT.md). Own data, starter values, calculated values and exports: [CC0](LICENSE-CONTENT.md). Colors from data sets such as Okabe-Ito, Paul Tol, ColorBrewer and viridis are excluded: they keep their own terms, and the notices are in the exports and on the sources page. The legal notice details in `data/legal.json` are not covered by these licenses. Fonts in `web/fonts/` (Inter, IBM Plex Mono): SIL Open Font License 1.1. The material from CSS Color 4 in the color core keeps the W3C Software and Document License. The license texts are in `data/licenses/`. [LICENSE-CONTENT.md](LICENSE-CONTENT.md) says which license applies to which folder.

Sister projects: [Bildsprache](https://github.com/grundhofer/bildsprache), image styles for AI images, and [Designsprache](https://github.com/grundhofer/designsprache), a catalog of UI design languages.

© Sebastian Grundhöfer
