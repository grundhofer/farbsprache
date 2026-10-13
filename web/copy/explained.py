"""Texte der Seite Kurz erklärt. Vertrauenswürdiges HTML (CC BY 4.0).

Die Einträge selbst stehen in data/explain/*.json. {color} setzt pages/explained.py als berechnetes Hex ein.
Texte im Muster demo-context ({{schlüssel}}) sucht die Seite zuerst unter pattern.<schlüssel> hier.
"""

COPY = {
 "de": {
  "explained": {
   "title": "Kurz erklärt – Farbsprache",
   "desc": "Die Gründe hinter den Regeln von Farbsprache. Jeder Eintrag sagt, wie gut er belegt ist, und nennt seine Quellen.",
   "h1": "Kurz erklärt",
   "lede": "Die Gründe hinter den Regeln. Jeder Eintrag sagt, wie gut er belegt ist.",
   "toc_l": "Einträge",
   "at": "Steht bei:",
   "at.none": "noch bei keiner Aufgabe",
   "demo.btn": "Brücke zeigen",
   "demo.caption": "Beide Quadrate haben dieselbe Farbe: {color}. Zeige die Brücke, dann siehst du es.",
   "empty": "Noch sind keine Einträge gebaut.",
   "legend": "Belegstufen: Norm steht so in einer verbindlichen Regel. Forschung ist durch Studien oder Fachquellen gestützt, mit Angabe, wie gut. Konvention gilt, weil es vereinbart oder üblich ist. Unbelegt heißt: keine Quelle auffindbar oder widerlegt.",
  },
 },
 "en": {
  "explained": {
   "title": "Explained briefly – Farbsprache",
   "desc": "The reasons behind the rules of Farbsprache. Each entry says how well it is backed and names its sources.",
   "h1": "Explained briefly",
   "lede": "The reasons behind the rules. Each entry says how well it is backed.",
   "toc_l": "Entries",
   "at": "Used on:",
   "at.none": "no task yet",
   "demo.btn": "Show bridge",
   "demo.caption": "Both squares have the same color: {color}. Show the bridge to see it.",
   "empty": "No entries are built yet.",
   "legend": "Evidence levels: Standard is stated like this in a binding rule. Research is backed by studies or expert sources, with a note on how well. Convention holds because it is agreed or common. Unproven means no source was found, or it was disproved.",
  },
 },
}
