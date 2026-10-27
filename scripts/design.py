"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import ImageFont
import os
from themes import THEMES
from status_panel import render_status
from badges import render_badge
from intro_panel import render_intro
from technology_panel import render_technology
from contribution_city import render_city
import json
from github_layout import build_github_layout
from language_buttons import render_language_buttons
from profile_i18n import DEFAULT, LOCALES, localized

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'


def font(size, bold=False, mono=False):
    base = Path('C:/Windows/Fonts') if os.name == 'nt' else Path('/usr/share/fonts/truetype/dejavu')
    if os.name == 'nt':
        name = 'consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf'
    else:
        name = 'DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(str(base / name), size)


def render_theme(name, palette, locale=DEFAULT):
    render_intro(font, palette, locale=locale).save(A / f'{localized("intro-background",locale)}-{name}.png')
    render_technology(ROOT, font, palette, locale)
    render_status(ROOT, font, palette, locale)
    render_city(ROOT, font, palette, locale)


def render_badges():
    """Compact contact badges drawn locally and hosted with the profile."""
    content = json.loads((ROOT / 'data/github-content.json').read_text(encoding='utf-8'))
    navy = '#17324d'
    for stem, label, value, left, right, icon in [
            ('badge-linkedin', '', 'André Mello', '#0a66c2', navy, 'linkedin'),
            ('badge-github', '', '@' + content['user']['login'], '#24292f', navy, 'github'),
            ('badge-email', '', 'andremello@outlook.com', '#0078d4', navy, 'email')]:
        render_badge(A / f'{stem}.png', font, label, value, left, right, icon, A)


if __name__ == '__main__':
    A.mkdir(exist_ok=True)
    for locale in LOCALES:
        for name, palette in THEMES.items():
            render_theme(name, palette, locale)
    render_badges()
    render_language_buttons(A, font)
    for locale in LOCALES:
        build_github_layout(ROOT, font, locale)
