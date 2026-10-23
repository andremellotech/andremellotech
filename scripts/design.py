"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
from themes import THEMES, TRANSPARENT
from activity_panel import render_activity
from status_panel import render_status
from badges import render_badge
from intro_panel import render_intro
from contribution_snake import render_snake
import json
from github_layout import build_github_layout
from branding import section_heading

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'


def font(size, bold=False, mono=False):
    base = Path('C:/Windows/Fonts') if os.name == 'nt' else Path('/usr/share/fonts/truetype/dejavu')
    if os.name == 'nt':
        name = 'consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf'
    else:
        name = 'DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(str(base / name), size)


BADGE_GROUPS = [
    ('Dados & Automação', [('powerbi', 'Power BI'), ('python', 'Python'), ('excel', 'Excel'), ('alteryx', 'Alteryx')]),
    ('Negócios & Apresentações', [('sap', 'SAP'), ('powerpoint', 'PowerPoint')]),
    ('Linguagens · Conhecimentos', [('HTML2', 'HTML'), ('CSS2', 'CSS'), ('JavaScript2', 'JavaScript'), ('Lua2', 'Lua')]),
    ('Versionamento & Projetos', [('GitHub', 'GitHub')]),
    ('Bancos de dados · Experiência anterior', [('MySQL', 'MySQL')]),
]


def render_theme(name, palette):
    def canvas(w, h):
        image = Image.new('RGBA', (w, h), TRANSPARENT)
        return image, ImageDraw.Draw(image)

    def txt(draw, x, y, value, size=22, color=None, bold=False):
        draw.text((x, y), value, font=font(size, bold), fill=color or palette['text'])

    def save(image, stem):
        image.save(A / f'{stem}-{name}.png')

    save(render_intro(font, palette), 'intro-background')

    im, d = canvas(1200, 500)
    section_heading(d, palette, font, 'Tecnologias & ferramentas', 12)
    for group, (heading, items) in enumerate(BADGE_GROUPS):
        if group == 4:
            left, y, right = 30, 378, 1170
            heading = 'Banco de dados'
        else:
            left, y, right = (30 if group % 2 == 0 else 612), 60 + (group // 2) * 158, (588 if group % 2 == 0 else 1170)
        color = palette['accent']
        d.rounded_rectangle((left, y, right, y + (104 if group == 4 else 140)),
                            radius=12, fill=palette['surface'], outline=palette['line'])
        txt(d, left + 20, y + 17, heading, 20, color, True)
        x = left + 20
        for stem, label in items:
            badge = Image.open(A / 'badges' / f'{stem}.webp').convert('RGBA')
            if name == 'light':
                # White labels need an opaque base instead of blending into the page.
                # Derive the capsule edge from its alpha so the exterior stays transparent.
                mask = badge.getchannel('A').point(lambda alpha: min(255, round(alpha * 2.5)))
                base = Image.new('RGBA', badge.size, '#0d1117')
                base.putalpha(mask)
                base.alpha_composite(badge)
                badge = base
            badge = badge.resize((round(badge.width * 1.2), 43), Image.Resampling.LANCZOS)
            im.alpha_composite(badge, (x, y + 55))
            x += badge.width + 6
        if group == 1:
            txt(d, left + 20, y + 111, 'Office 365 com Excel e PowerPoint.', 15, palette['muted'])
        if group == 4:
            label = 'EXPERIÊNCIA ANTERIOR'
            txt(d, 1150 - d.textlength(label, font=font(13)), y + 22, label, 13, palette['muted'])
            txt(d, 220, y + 65, 'MySQL nos servidores de Tibia e GTA V / FiveM.', 17, palette['muted'])
    save(im, 'stack')
    render_status(ROOT, font, palette)
    render_activity(ROOT, font, palette)
    render_snake(ROOT, palette)


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
    for name, palette in THEMES.items():
        render_theme(name, palette)
    render_badges()
    build_github_layout(ROOT, font)
