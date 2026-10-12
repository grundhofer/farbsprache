"""Seitentheme (System / Hell / Dunkel), unverändert übernommen aus Bildsprache (Swiss).

Das Theme betrifft nur den Seitenrahmen. Paletten, Farbfelder und Muster sind Inhalt und
behalten ihre eigenen Farben. Die Kontraste der Tokens prüft tests/test_theme.py.
"""
from pathlib import Path

PALETTES = {
    # Swiss / International Typographic Style: Schwarz und Weiß als System, Rot als einzige Signalfarbe
    'light': {
        'ground':'#FFFFFF', 'surface':'#FFFFFF', 'surface-2':'#F2F2F2',
        'ink':'#0B0B0B', 'ink-2':'#3A3A3A', 'ink-3':'#5E5E5E',
        'rule':'#B0B0B0', 'rule-soft':'#DADADA',
        'accent':'#C8050F', 'accent-ink':'#FFFFFF', 'accent-soft':'#FCE6E7', 'brass':'#0B0B0B',
        'tag-style':'#FCE6E7', 'tag-motif':'#EDEDED', 'tag-guard':'#E2E2E2',
    },
    'dark': {
        'ground':'#0B0B0B', 'surface':'#0B0B0B', 'surface-2':'#1A1A1A',
        'ink':'#FFFFFF', 'ink-2':'#D0D0D0', 'ink-3':'#A6A6A6',
        'rule':'#5C5C5C', 'rule-soft':'#2A2A2A',
        'accent':'#FF4D52', 'accent-ink':'#0B0B0B', 'accent-soft':'#3A1214', 'brass':'#FFFFFF',
        'tag-style':'#3A1214', 'tag-motif':'#232323', 'tag-guard':'#2C2C2C',
    },
}


def css():
    def values(mode):
        shadow = 'none'  # Swiss: keine Schatten, Trennung nur über Linien und Abstand
        return ''.join('--'+key+':'+value+';' for key, value in PALETTES[mode].items())+'--shadow:'+shadow+';color-scheme:'+mode+';'
    return (':root {'+values('light')+'}\n'
            '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {'+values('dark')+'} }\n'
            ':root[data-theme="dark"] {'+values('dark')+'}\n')


def script():
    return '<script id="theme-controller">\n'+(Path(__file__).parent/'theme.js').read_text(encoding='utf-8')+'\n</script>\n'


def controls(lang):
    labels = {'de': ('System', 'Hell', 'Dunkel'), 'en': ('System', 'Light', 'Dark')}[lang]
    title = {'de': 'Darstellung', 'en': 'Appearance'}[lang]
    buttons = ''.join(f'<button type="button" data-theme-choice="{mode}" aria-pressed="false">{labels[i]}</button>'
                      for i, mode in enumerate(('system', 'light', 'dark')))
    return f'<div class="theme-switch" data-theme-controls role="group" aria-label="{title}" hidden>{buttons}</div>'
