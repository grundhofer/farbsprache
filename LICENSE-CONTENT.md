# Lizenz der Inhalte / Content license

Der Code steht unter MIT (`LICENSE`): `build.py`, `pages/`, `patterns/`, `tools/`, `tests/`, `web/` und `.github/`, ohne
die Texte in `web/copy/`, die README-Vorlagen `web/readme.*.md` und die Schriften in `web/fonts/`. Für alles andere gilt
diese Datei. / The code is licensed under MIT (`LICENSE`): `build.py`, `pages/`, `patterns/`, `tools/`, `tests/`, `web/`
and `.github/`, except the texts in `web/copy/`, the README templates `web/readme.*.md` and the fonts in `web/fonts/`.
Everything else is covered by this file.

## Texte / Texts: CC BY 4.0

**Creative Commons Namensnennung 4.0 International (CC BY 4.0)** gilt für die redaktionellen Texte dieses
Repositorys: die Fließtexte der Website in `web/copy/`, die Texte der Regeln, Erklärt-Einträge und Quellen in
`data/rules/`, `data/explain/` und `data/sources/`, die Namen, Beschreibungen und Hinweise (Felder `*_de`, `*_en`) in
`data/tasks/`, `data/models.json`, `data/check.json` und `data/comparisons.json`, die README-Vorlagen
`web/readme.*.md` mit den daraus erzeugten `README.md` und `README.de.md`, `CONTRIBUTING.md` sowie das Vorschaubild
`og.png`. Ausgenommen sind wörtliche Zitate aus Quellen (in Anführungszeichen, in deutschen Texten zusätzlich mit
`[en]…[/en]` bzw. `[de]…[/de]` ausgezeichnet, oder im Feld `quote`) und zitierte oder zusammengefasste Normtexte wie die
Erfolgskriterien der WCAG. Sie gehören ihren Urhebern und stehen hier mit Quellenangabe und Link; für die WCAG gilt die
W3C Document License (Vermerk unten).

Applies to the editorial texts in this repository: the site prose in `web/copy/`, the texts of rules,
explained entries and sources in `data/rules/`, `data/explain/` and `data/sources/`, the names, descriptions and notes
(fields `*_de`, `*_en`) in `data/tasks/`, `data/models.json`, `data/check.json` and `data/comparisons.json`, the README
templates `web/readme.*.md` with the generated `README.md` and `README.de.md`, `CONTRIBUTING.md` and the preview
image `og.png`. Excluded are verbatim quotes from sources (in quotation marks, in German texts also marked
`[en]…[/en]` or `[de]…[/de]`, or in the field `quote`) and quoted or summarized standard texts such as the WCAG success
criteria. They belong to their authors and appear here with their source and a link; the WCAG success criteria fall
under the W3C Document License (notice below).

Empfohlene Namensnennung / Suggested attribution:

> Farbsprache von Sebastian Grundhöfer, CC BY 4.0
> https://github.com/grundhofer/farbsprache

Lizenztext / License text: https://creativecommons.org/licenses/by/4.0/legalcode.de ·
https://creativecommons.org/licenses/by/4.0/legalcode

## Werte und Exporte / Values and exports: CC0 1.0

Eigene Startwerte (die Eingaben der Startpaletten), eigene Daten (Eingaben, Schwellen, Vokabular und Muster in
`data/tasks/`, `data/check.json`, `data/colornames.json`, `data/comparisons.json`, `data/models.json`, die übrigen Felder
in `data/rules/`, `data/explain/` und `data/sources/` (IDs, Schwellen, Reihenfolgen, Verweise, URLs, Datumsangaben) sowie die
eigenen Testvektoren in `data/testvectors.json`), alle berechneten Werte (Hex-Werte, Kontraste, Abstände, Deckkräfte) und alle
Exporte zum Kopieren (CSS, Tailwind, Design-Tokens, Hex-Listen, Prompts, Begründungen) stellt Farbsprache unter
**CC0 1.0 Universal** gemeinfrei. Für kopierten Code brauchst du keine Namensnennung.

Own starter values (the inputs of the starter palettes), own data (inputs, thresholds, vocabulary and patterns in
`data/tasks/`, `data/check.json`, `data/colornames.json`, `data/comparisons.json`, `data/models.json`, the other fields
in `data/rules/`, `data/explain/` and `data/sources/` (IDs, thresholds, orders, references, URLs, dates) and the own
test vectors in `data/testvectors.json`), all calculated values (hex values, contrasts, distances, opacities) and all exports
to copy (CSS, Tailwind, design tokens, hex lists, prompts, rationales) are dedicated to the public domain under
**CC0 1.0 Universal**. Copied code needs no attribution.

https://creativecommons.org/publicdomain/zero/1.0/

Ausgenommen sind Farben aus Datensätzen Dritter. Farbsprache kann sie nicht gemeinfrei stellen, sie behalten die
Bedingungen ihres Datensatzes (unten). Enthält ein Export solche Farben, steht der Vermerk des Datensatzes im Export
selbst. Behalte ihn, wenn du die Farben weitergibst. / Colors from third-party data sets are excluded. Farbsprache cannot
dedicate them to the public domain; they keep the terms of their data set (below). If an export contains such colors,
the notice of the data set is part of the export itself. Keep it when you pass the colors on.

## Fremddaten / Third-party data

Jeder Datensatz in `data/datasets/` nennt Herkunft, Lizenz und Pflichtvermerk. Die Quellenseite der Website
zeigt sie vollständig. / Every data set in `data/datasets/` states its origin, license and required notice.
The sources page of the website shows them in full.

- **Okabe-Ito (2002):** keine formale Lizenz. Die Autoren bitten um Nennung („Masataka Okabe, Kei Ito“), Exporte
  tragen sie. CUD-Logos werden nicht verwendet. / No formal license. The authors ask to be credited, and exports carry
  the credit. The CUD logos are not used.
- **Paul Tol (bright, muted):** BSD-3-Clause für `tol_colors.py`, „Copyright (c) 2022, Paul Tol. All rights
  reserved.“ Exporte mit Tol-Farben tragen diesen Copyright-Vermerk. Gibst du die Farben als Teil von Software weiter,
  gehören nach der Lizenz auch ihre Bedingungen und der Haftungsausschluss dazu (Volltext in
  `data/licenses/BSD-3-Clause.txt` mit dem Copyright-Satz oben, auch auf der Quellenseite). Paul
  Tols Name darf nicht für eigene Produkte werben. Für die Schemata auf seiner Website nennt er keine eigene Lizenz. /
  BSD-3-Clause for `tol_colors.py`, “Copyright (c) 2022, Paul Tol. All rights reserved.” Exports with Tol colors carry
  this copyright notice. If you pass the colors on as part of software, the license also requires its conditions and
  the disclaimer (full text in `data/licenses/BSD-3-Clause.txt` with the copyright line above, also on the sources
  page). Paul Tol's name must not be used to endorse your own products. He
  states no separate license for the schemes on his website.
- **ColorBrewer (Blues, RdBu, PuOr):** Apache-2.0-artige Lizenz, Copyright 2002 Cynthia Brewer, Mark Harrower und The
  Pennsylvania State University. Der Pflichtsatz steht wörtlich in jedem Export mit einer ColorBrewer-Farbe; behalte
  ihn: „This product includes color specifications and designs developed by Cynthia Brewer
  (http://colorbrewer.org/).“ „ColorBrewer“ darf nicht im Namen eines eigenen Produkts stehen. / Apache-style license,
  copyright 2002 Cynthia Brewer, Mark Harrower and The Pennsylvania State University. The required notice is part of
  every export with a ColorBrewer color, word for word; keep it. “ColorBrewer” must not appear in the name of your own
  product.
- **viridis:** CC0, gemeinfrei, ohne Pflicht. Die Autoren bitten um Nennung (Stéfan van der Walt, Nathaniel Smith,
  Eric Firing), Exporte tragen sie. / CC0, public domain, no obligation. The authors ask for credit, and exports carry
  it.
- **Simulation von Farbsehschwäche / Color vision deficiency:** Die Matrizen in `data/cvd.json` stammen aus
  libDaltonLens (Nicolas Burrus) unter der Unlicense, gemeinfrei. / The matrices in `data/cvd.json` come from
  libDaltonLens (Nicolas Burrus) under the Unlicense, public domain.
- **CSS Color 4 und WCAG 2.2 / CSS Color 4 and WCAG 2.2:** Die Farbnamen in `data/css-names.json` und die Matrizen in
  `data/color-constants.json` stammen aus CSS Color 4 (W3C Software and Document License), die Koeffizienten der
  Leuchtdichte aus WCAG 2.2 (W3C Document License). Die Farbnamen nutzt nur der Parser. Die als extern markierten
  Testvektoren in `data/testvectors.json` sind Werte aus diesen Quellen und aus Björn Ottossons Beitrag zu OKLab; jeder
  Abschnitt nennt seine Quelle. In `tools/color.py`, `web/color.js`, `data/color-constants.json` und
  `data/css-names.json` sind aus CSS Color 4 übernommen oder abgeleitet: Matrizen, sRGB-Übertragung, Umrechnung zwischen
  XYZ, OKLab und OKLCH, ΔEOK, HSL-Umrechnung, Gamut-Mapping und die Tabelle der Farbnamen. Für diese Teile gilt
  zusätzlich die W3C Software and Document License (Volltext in `data/licenses/W3C-Software-and-Document-2023.txt`, auch
  auf der Quellenseite) mit diesem Vermerk, den auch die ausgelieferte `color.js` in der ersten Zeile trägt: „This
  software includes material copied from or derived from CSS Color Module Level 4
  (https://www.w3.org/TR/2026/CRD-css-color-4-20261009/). Copyright © 2026 World Wide Web Consortium.
  https://www.w3.org/copyright/software-license-2023/“ Hinweis der Spezifikation: „Copyright © 2026 World Wide Web
  Consortium. W3C® liability, trademark and permissive document license rules apply.“ Für relative Leuchtdichte,
  Kontrast und die zitierten oder zusammengefassten Erfolgskriterien gilt die W3C Document License mit diesen Vermerken
  (der erste steht ebenfalls in der ersten Zeile von `color.js`): „Copyright © 2023 W3C®. This software or document
  includes material copied from or derived from Web Content Accessibility Guidelines (WCAG) 2.2
  (https://www.w3.org/TR/2024/REC-WCAG22-20241212/).“ „Web Content Accessibility Guidelines (WCAG) 2.2,
  https://www.w3.org/TR/2024/REC-WCAG22-20241212/, W3C Recommendation 12 December 2024. Copyright © 2020-2024 World Wide
  Web Consortium. W3C® liability, trademark and document use rules apply.
  https://www.w3.org/copyright/document-license-2023/“
  / The color names in `data/css-names.json` and the matrices in `data/color-constants.json` come from CSS Color 4 (W3C
  Software and Document License), the luminance coefficients from WCAG 2.2 (W3C Document License). Only the parser uses
  the color names. The test vectors marked as external in `data/testvectors.json` are values from these sources and from
  Björn Ottosson's post on OKLab; each section names its source. In `tools/color.py`, `web/color.js`,
  `data/color-constants.json` and `data/css-names.json`, the matrices, sRGB transfer, conversion between XYZ, OKLab and
  OKLCH, ΔEOK, HSL conversion, gamut mapping and the table of named colors are copied or derived from CSS Color 4. These
  parts also keep the W3C Software and Document License (full text in
  `data/licenses/W3C-Software-and-Document-2023.txt`, also on the sources page) with the
  CSS Color 4 notice above, which the shipped `color.js` carries in its first line, and the original notice of the
  specification. Relative luminance, contrast and the quoted or summarized success
  criteria fall under the W3C Document License with the WCAG notices above.
- **Lizenztexte / License texts:** Die Texte in `data/licenses/` stehen unverändert unter den Bedingungen ihrer
  Herausgeber. / The texts in `data/licenses/` are unchanged and keep the terms of their publishers.

## Nicht von diesen Lizenzen erfasst / Not covered

- **Schriften.** Die Seite liefert Inter und IBM Plex Mono selbst aus (`web/fonts/`), unter deren eigener Lizenz
  (SIL Open Font License 1.1, Volltexte in `data/licenses/`). Sie lädt nichts von Google Fonts. / The site ships Inter
  and IBM Plex Mono itself (`web/fonts/`) under their own license (SIL Open Font License 1.1, full texts in
  `data/licenses/`). It loads nothing from Google Fonts.
- **Impressum.** Die Anbieterangaben in `data/legal.json` (Name, Anschrift, E-Mail-Adresse, Umsatzsteuer-ID) sind
  Pflichtangaben für das Impressum und stehen unter keiner der Lizenzen oben. / The provider details in
  `data/legal.json` (name, address, email address, VAT ID) are the required details for the legal notice and are not
  covered by the licenses above.
- **Namen.** Normfarbsysteme, Marken und Produktnamen gehören ihren Inhabern und werden nur zur Beschreibung
  genannt. Farbsprache enthält keine Werte aus Pantone, RAL, HKS oder NCS. / Color standards, trademarks and
  product names belong to their owners and are named only to describe. Farbsprache contains no values from
  Pantone, RAL, HKS or NCS.
