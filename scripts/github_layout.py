"""Compose theme-aware PNGs and a small, transparent animated portrait block."""
from PIL import Image, ImageDraw, ImageColor, ImageSequence, GifImagePlugin
import hashlib
from themes import THEMES, TRANSPARENT

ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'


def image_url(root, name):
    version = hashlib.sha256((root / 'assets' / name).read_bytes()).hexdigest()[:12]
    return ASSET_HOST + name + '?v=' + version


def transparent_portrait(source, color):
    original = (source if isinstance(source, Image.Image) else Image.open(source)).convert('RGB')
    # Recover glyph opacity from the original uniform terminal background.
    # Recoloring the glyphs avoids dark halos on light pages.
    alpha = original.convert('L').point(lambda value: max(0, min(255, round((value - 19) * 1.9))))
    portrait = Image.new('RGBA', original.size, ImageColor.getrgb(color) + (0,))
    portrait.putalpha(alpha)
    return portrait


def animated_about(assets, theme, palette, about):
    """Animate only the portrait row; keep the large remainder lossless PNG."""
    frames, durations = [], []
    shared_palette = None
    with Image.open(assets / 'andre-ascii.gif') as original:
        for source in ImageSequence.Iterator(original):
            frame = Image.new('RGBA', (1200, 578), TRANSPARENT)
            frame.alpha_composite(transparent_portrait(source, palette['portrait']), (84, 0))
            frame.alpha_composite(about, (532, 0))
            if shared_palette is None:
                frame.save(assets / f'profile-about-{theme}.png')
            # GIF has binary transparency. Matte only the antialiased glyph edges,
            # leaving all empty space transparent over GitHub's own background.
            matte = Image.new('RGBA', frame.size, palette['matte'])
            matte.alpha_composite(frame)
            rgb = matte.convert('RGB')
            if shared_palette is None:
                shared_palette = rgb.quantize(colors=255, dither=Image.Dither.NONE)
            indexed = rgb.quantize(palette=shared_palette, dither=Image.Dither.NONE)
            indexed.paste(255, mask=frame.getchannel('A').point(lambda alpha: 255 if alpha == 0 else 0))
            indexed.info['transparency'] = 255
            frames.append(indexed)
            durations.append(source.info.get('duration', 100))
    # Write the fixed text once, then send only the small portrait rectangle.
    # A transparent clearing frame removes the initial portrait without erasing
    # the text. Each later portrait clears its own rectangle before the next one.
    with (assets / f'profile-about-{theme}.gif').open('wb') as output:
        header, _ = GifImagePlugin.getheader(frames[0], info={
            'loop': 0, 'transparency': 255, 'background': 255, 'optimize': False})
        output.writelines(header)
        output.writelines(GifImagePlugin.getdata(frames[0], duration=durations[0],
                                                disposal=1, transparency=255))
        clear = Image.new('P', (430, 550), 255)
        clear.putpalette(frames[0].getpalette())
        output.writelines(GifImagePlugin.getdata(clear, offset=(84, 0), duration=10,
                                                disposal=2, transparency=255))
        for frame, duration in zip(frames[1:], durations[1:]):
            portrait = frame.crop((84, 0, 514, 550))
            output.writelines(GifImagePlugin.getdata(portrait, offset=(84, 0),
                                                    duration=duration, disposal=2, transparency=255))
        output.write(b';')


def themed_picture(root, stem, alt, animated=False):
    sources = []
    if animated:
        for theme in ['dark', 'light']:
            sources.append('<source media="(prefers-reduced-motion: reduce) and '
                           f'(prefers-color-scheme: {theme})" srcset="'
                           + image_url(root, f'{stem}-{theme}.png') + '" />')
    extension = 'gif' if animated else 'png'
    for theme in ['dark', 'light']:
        sources.append(f'<source media="(prefers-color-scheme: {theme})" srcset="'
                       + image_url(root, f'{stem}-{theme}.{extension}') + '" />')
    return ('<picture>' + ''.join(sources) + '<img src="'
            + image_url(root, f'{stem}-light.{extension}')
            + '" width="100%" align="top" alt="' + alt + '" /></picture>')


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
            (12, 'Contato & Projetos', 22, True, palette['accent']),
            (54, 'Conheça meu trabalho e vamos conversar.', 19, False, palette['muted']),
        ]:
            face = font(size, bold)
            draw.text(((1200 - draw.textlength(text, font=face)) / 2, y + offset), text, font=face, fill=color)
        main.save(assets / f'profile-card-{theme}.png')
        # These adjoining slices preserve the original layout and avoid quantizing
        # every text line and technology badge into a full-page GIF.
        about_y = panels[0].height + 28
        body_y = about_y + panels[1].height + 28
        main.crop((0, 0, 1200, about_y)).save(assets / f'profile-header-{theme}.png')
        main.crop((0, body_y, 1200, height)).save(assets / f'profile-body-{theme}.png')
        animated_about(assets, theme, palette, Image.open(assets / f'about-{theme}.png').convert('RGBA'))

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
    readme = ('<p align="center">'
              + themed_picture(root, 'profile-header', 'André Mello — Dados, tecnologia e visão de negócio.')
              + themed_picture(root, 'profile-about', 'Sobre mim — retrato ASCII animado de André Mello.', animated=True)
              + themed_picture(root, 'profile-body', alt)
              + '<a href="https://www.linkedin.com/in/aamello/"><img src="' + image_url(root, 'footer-linkedin.png') + '" '
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
    print('Transparent, animated profile built for light and dark GitHub themes.')
