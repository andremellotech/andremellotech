"""Compose transparent PNGs and let GitHub select text colors for its theme."""
from PIL import Image, ImageDraw, ImageColor
import hashlib
from themes import THEMES, TRANSPARENT

ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'


def image_url(root, name):
    version = hashlib.sha256((root / 'assets' / name).read_bytes()).hexdigest()[:12]
    return ASSET_HOST + name + '?v=' + version


def transparent_portrait(path, color):
    original = Image.open(path).convert('RGB')
    # Recover glyph opacity from the original uniform terminal background.
    # Recoloring the glyphs avoids dark halos on light pages.
    alpha = original.convert('L').point(lambda value: max(0, min(255, round((value - 19) * 1.9))))
    portrait = Image.new('RGBA', original.size, ImageColor.getrgb(color) + (0,))
    portrait.putalpha(alpha)
    return portrait


def build_github_layout(root, font):
    assets = root / 'assets'
    for theme, palette in THEMES.items():
        panels = []
        for name in ['hero', 'about-pair', 'expertise', 'stack', 'activity']:
            if name == 'about-pair':
                panel = Image.new('RGBA', (1200, 550), TRANSPARENT)
                panel.alpha_composite(transparent_portrait(assets / 'andre-ascii.png', palette['portrait']), (84, 0))
                panel.alpha_composite(Image.open(assets / f'about-{theme}.png'), (532, 0))
            else:
                panel = Image.open(assets / f'{name}-{theme}.png').convert('RGBA')
            panels.append(panel)
        height = sum(panel.height for panel in panels) + 28 * len(panels) + 102
        main = Image.new('RGBA', (1200, height), TRANSPARENT)
        y = 0
        for panel in panels:
            main.alpha_composite(panel, (0, y))
            y += panel.height + 28
        draw = ImageDraw.Draw(main)
        for offset, text, size, bold, color in [
            (12, 'Contato & Projetos', 22, True, palette['text']),
            (54, 'Conheça meu trabalho e vamos conversar.', 19, False, palette['muted']),
        ]:
            face = font(size, bold)
            draw.text(((1200 - draw.textlength(text, font=face)) / 2, y + offset), text, font=face, fill=color)
        main.save(assets / f'profile-card-{theme}.png')

    footer = Image.new('RGBA', (1200, 84), TRANSPARENT)
    for stem, side in [('link-linkedin', 0), ('link-github', 1)]:
        half = Image.new('RGBA', (600, 84), TRANSPARENT)
        badge = Image.open(assets / f'{stem}.png').convert('RGBA')
        badge = badge.resize((round(badge.width / 2), 42), Image.Resampling.LANCZOS)
        x = 600 - badge.width - 8 if side == 0 else 8
        half.alpha_composite(badge, (x, 12))
        half.save(assets / ('footer-linkedin.png' if side == 0 else 'footer-github.png'))
        footer.alpha_composite(half, (600 * side, 0))

    for theme, background in [('light', '#ffffff'), ('dark', '#0d1117')]:
        preview = Image.new('RGBA', (1200, height + 84), background)
        preview.alpha_composite(Image.open(assets / f'profile-card-{theme}.png'))
        preview.alpha_composite(footer, (0, height))
        preview.convert('RGB').save(root / ('PREVIA.png' if theme == 'light' else 'PREVIA-ESCURO.png'))

    alt = ('André Mello — Dados, tecnologia e visão de negócio. Performance e Analytics; '
           'Engineering e Automation; Financial Modeling. Ferramentas: Power BI, Python, Excel, '
           'Alteryx, SAP e PowerPoint; conhecimentos em HTML, CSS, JavaScript e Lua; GitHub; '
           'experiência anterior em MySQL nos servidores de Tibia e GTA V / FiveM. '
           'Office 365 com Excel e PowerPoint. Atividade pública e calendário de contribuições atualizados automaticamente.')
    # No spaces between inline images: the contact halves keep their exact widths.
    readme = ('<p align="center"><picture>'
              '<source media="(prefers-color-scheme: dark)" srcset="' + image_url(root, 'profile-card-dark.png') + '" />'
              '<source media="(prefers-color-scheme: light)" srcset="' + image_url(root, 'profile-card-light.png') + '" />'
              '<img src="' + image_url(root, 'profile-card-light.png') + '" width="100%" align="top" alt="' + alt + '" />'
              '</picture><a href="https://www.linkedin.com/in/aamello/"><img src="' + image_url(root, 'footer-linkedin.png') + '" '
              'width="50%" align="top" alt="LinkedIn — André Mello" /></a>'
              '<a href="https://github.com/andremellotech?tab=repositories"><img src="' + image_url(root, 'footer-github.png') + '" '
              'width="50%" align="top" alt="GitHub — explorar meus repositórios" /></a></p>\n')
    (root / 'README.md').write_text(readme, encoding='utf-8')
    preview_html = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>André Mello — prévia adaptativa</title><style>'
                    ':root{color-scheme:light dark}body{margin:0;background:light-dark(#f6f8fa,#010409);font:14px/1.5 system-ui}'
                    'main{max-width:900px;background:light-dark(#fff,#0d1117);border:1px solid light-dark(#d1d9e0,#3d444d);'
                    'border-radius:6px;padding:24px;margin:24px auto}p{margin:0}img{max-width:100%;height:auto;vertical-align:top}'
                    '@media(max-width:600px){main{padding:12px;margin:8px}}</style><main>'
                    + readme.replace(ASSET_HOST, './assets/') + '</main></html>')
    (root / 'previa.html').write_text(preview_html, encoding='utf-8')
    print('Transparent profile built for light and dark GitHub themes.')
