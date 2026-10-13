#!/usr/bin/env python3
"""Baut das Social-Preview-Bild og.png (1280x640) mit lokalem Chrome (headless).

    python3 tools/og.py          # schreibt og.html und rendert daraus og.png

Seitenstil Swiss wie die Website: Schwarz-Weiß, Rot nur als Marke. Rechts eine geprüfte Farbreihe
(Okabe-Ito aus data/datasets/okabe-ito.json) mit dem Kontrast jeder Farbe zu Weiß. Jede Zahl kommt aus
den Formatierern in tools/color.py, die Zähler aus build.py. og.png liegt im Repo, weil der CI-Runner keinen
Browser hat; build.py kopiert es nach docs/. Ändern sich die Zahlen, neu rendern.
"""
import html, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from tools import color as C  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Dieselben mitgelieferten Schriften wie die Website (web/fonts/, OFL 1.1), relativ zu og.html im Projektordner;
# kein Abruf von Google Fonts
FONT_FACES = "".join(f'@font-face{{font-family:"{fam}";font-weight:{w};src:url(web/fonts/{f}) format("woff2")}}'
                     for fam, w, f in (("Inter", 400, "inter-400.woff2"), ("Inter", 500, "inter-500.woff2"),
                                       ("Inter", 700, "inter-700.woff2"), ("IBM Plex Mono", 400, "IBMPlexMono-Regular-Latin1.woff2"),
                                       ("IBM Plex Mono", 500, "IBMPlexMono-Medium-Latin1.woff2")))


def page(site):
    lang = "de"
    home = site.copy[lang]["home"]
    names = [t["name_" + lang] for t in site.tasks]
    ds = site.datasets["okabe-ito"]
    cols = [c for c in ds["schemes"][0]["colors"] if c["name"] != "black"]
    rows = []
    for c in cols:
        r = C.contrast(c["hex"], "#FFFFFF")
        mark = "4,5:1" if r >= 4.5 else "3:1" if r >= 3 else None
        rows.append(f'<div class="sw"><i style="background:{c["hex"]}"></i><code>{c["hex"]}</code>'
                    f'<b>{C.fmt_ratio(r, lang)}</b><span>{"erfüllt " + mark if mark else "unter 3:1"}</span></div>')
    facts = [(len(site.order), "Aufgaben"), (len(C.KINDS), "Sichtweisen"), (len(site.sources), "Quellen")]
    if site.counts["presets"]:
        facts[1] = (site.counts["presets"], "Startpaletten")
    tasks = f'<div class="ucs">{html.escape(", ".join(names))}.</div>' if names else ""
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<style>
{FONT_FACES}
html,body{{margin:0;width:1280px;height:640px;overflow:hidden;background:#FFFFFF;color:#0B0B0B;font-family:Inter,Helvetica,Arial,sans-serif}}
.wrap{{display:grid;grid-template-columns:560px 1fr;height:640px}}
.txt{{padding:44px 40px 40px 52px;display:flex;flex-direction:column;justify-content:space-between;border-right:1px solid #0B0B0B}}
.brand{{display:flex;align-items:center;gap:10px;font:700 15px Inter,sans-serif;letter-spacing:.06em;text-transform:uppercase}}
.brand svg{{width:24px;height:24px}}
.eb{{font:500 13px Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;margin-top:40px}}
h1{{font:700 52px/0.98 Inter,sans-serif;letter-spacing:-.045em;margin:14px 0 0}}
h1 em{{font-style:normal;font-weight:400;color:#5E5E5E}}
.lead{{font:500 19px/1.4 Inter,sans-serif;margin-top:22px}}
.ucs{{font:400 15px/1.5 Inter,sans-serif;color:#3A3A3A;margin-top:10px}}
.facts{{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #0B0B0B}}
.facts div{{padding:12px 10px 0 0}}
.facts b{{display:block;font:700 32px/1.1 Inter,sans-serif;letter-spacing:-.02em}}
.facts span{{display:block;font:500 10.5px Inter,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#5E5E5E;margin-top:3px}}
.grid{{padding:44px 52px 40px 40px;display:flex;flex-direction:column;justify-content:space-between}}
.cap{{font:500 12px Inter,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#5E5E5E;border-top:3px solid #0B0B0B;padding-top:10px}}
.sws{{display:grid;gap:0}}
.sw{{display:grid;grid-template-columns:56px 110px 110px 1fr;align-items:center;gap:16px;border-bottom:1px solid #DADADA;height:58px}}
.sw i{{display:block;width:56px;height:40px}}
.sw code{{font:500 15px 'IBM Plex Mono',monospace}}
.sw b{{font:700 22px Inter,sans-serif;letter-spacing:-.01em;font-variant-numeric:tabular-nums}}
.sw span{{font:500 12px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#3A3A3A}}
.note{{font:400 13px Inter,sans-serif;color:#5E5E5E}}
</style></head><body><div class="wrap">
<div class="txt"><div><div class="brand">{build.LOGO.replace("var(--accent)", "#C8050F").replace("var(--surface)", "#FFFFFF")}Farbsprache</div>
<div class="eb">{html.escape(home["eyebrow"])}</div>
<h1>{home["h1"]}</h1>
<div class="lead">{html.escape(home["trust_h"])}.</div>{tasks}</div>
<div class="facts">{"".join(f'<div><b>{C.fmt_count(n, lang)}</b><span>{html.escape(t)}</span></div>' for n, t in facts)}</div></div>
<div class="grid"><div class="cap">Okabe-Ito auf Weiß · Kontrast nach WCAG 2.2, abgeschnitten</div>
<div class="sws">{"".join(rows)}</div>
<div class="note">Farben nach Masataka Okabe und Kei Ito, Color Universal Design (2002)</div></div>
</div></body></html>"""


def main():
    site = build.Site([ROOT], ROOT / "tests" / "out" / "unused", build.build_date(None), allow_missing=True)
    try:
        site.prepare()
    except build.BuildError as e:
        sys.exit("\n".join("  FEHLER " + p for p in e.errors))
    out = ROOT / "og.html"
    out.write_text(page(site), encoding="utf-8")
    png = ROOT / "og.png"
    tmp = ROOT / "tests" / "out" / "og-profile"
    if png.exists():
        png.unlink()
    # Chrome beendet sich im Headless-Modus auf macOS nicht immer; das Bild ist trotzdem fertig.
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
                        f"--user-data-dir={tmp}", "--blink-settings=preferredColorScheme=1",
                        f"--screenshot={png}", "--window-size=1280,640", out.as_uri()],
                       check=False, capture_output=True, timeout=40)
    except subprocess.TimeoutExpired:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    if not png.exists() or png.stat().st_size < 1000:
        sys.exit("og.png wurde nicht geschrieben (Chrome-Pfad prüfen)")
    print(f"  og.png geschrieben ({png.stat().st_size} Bytes)")


if __name__ == "__main__":
    main()
