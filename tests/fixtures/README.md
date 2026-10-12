# Testaufgabe „fixture“

Diese Dateien spiegeln die Struktur des Projekts und bilden eine vollständige Aufgabe, die nie
ausgeliefert wird. `python3 build.py --fixtures` legt sie über den Kern des Projekts und baut nach
`tests/out/fixtures/docs/`. Kern heißt: die gemeinsamen Dateien (`data/*/core.json`, `web/copy/core.py`,
Konstanten, Datensätze, Vergleichswerte). Aufgaben, Regeln, Erklärt-Einträge, Quellen, Texte und
eigene Prüfungen der Website-Aufgaben bleiben draußen, damit die Testaufgabe nie von deren Daten abhängt
(`tools/checks.py`, `_own`). Die generischen Tests (Ehrlichkeit, Exporte, Parität, Zustand,
Seitenprüfung) laufen über diese Seite und über `docs/`.

Sie zeigt, dass eine Aufgabe außer diesen Dateien nur ihre IDs in den `_order.json`-Dateien und zwei Stellen in
`build.py` braucht (`SEG`, `N_PAGES_PER_LANG`); `web/site.js`, `web/site.css` und `tools/checks.py` bleiben unverändert.
