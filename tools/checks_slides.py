"""Prüfung der Aufgaben Präsentation und Text auf Bild: check(D, warn) -> [Meldungen].

Prüft, was die generischen Prüfungen nicht kennen: Die Menüwege in data/tasks/slides.json (menu_paths) nennen
eine Quelle aus data/sources/*.json, ihre url ist genau die url dieser Quelle, und checked ist ein gültiges
ISO-Datum (Pflichtfeld laut tools/checks.py; ist ein Weg nicht belegbar, steht dort ein allgemeiner Satz).
"""
import datetime, re

ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
APPS = ("PowerPoint", "Keynote", "Google Slides")


def check(D, warn):
    errs = []
    t = (D.get("tasks") or {}).get("slides")
    if not t:
        return errs
    paths = t.get("menu_paths") or []
    apps = [m.get("app") for m in paths]
    if sorted(apps) != sorted(APPS):
        errs.append(f"Aufgabe slides menu_paths: erwartet genau {', '.join(APPS)}, gefunden {', '.join(map(str, apps))}")
    for m in paths:
        c = f"Aufgabe slides menu_paths {m.get('app')}"
        src = (D.get("sources") or {}).get(m.get("source"))
        if src is None:
            errs.append(f"{c}: Quelle {m.get('source')} gibt es nicht (data/sources/*.json)")
        elif m.get("url") != src.get("url"):
            errs.append(f"{c}: url passt nicht zur Quelle {m.get('source')} ({src.get('url')})")
        ch = m.get("checked")
        if ch is not None:
            if not isinstance(ch, str) or not ISO.fullmatch(ch):
                errs.append(f"{c}: checked muss ein ISO-Datum JJJJ-MM-TT sein")
            else:
                try:
                    datetime.date.fromisoformat(ch)
                except ValueError:
                    errs.append(f"{c}: checked {ch} ist kein gültiges Datum")
    return errs
