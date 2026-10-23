"""Compose theme-aware PNGs and a small, transparent animated portrait block."""
from PIL import Image, ImageColor, ImageSequence, GifImagePlugin
import hashlib, json
from projects_section import projects_markdown, projects_html
from themes import THEMES, TRANSPARENT
from branding import portrait_corners

ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'
ABOUT_H = 372                      # compact "Sobre mim" row
PORTRAIT_AT, PORTRAIT_SIZE = (70, 0), (290, 364)
TEXT_AT = 420


def image_url(root, name):
    version = hashlib.sha256((root / 'assets' / name).read_bytes()).hexdigest()[:12]
    return ASSET_HOST + name + '?v=' + version


def transparent_portrait(source, color):
    original = (source if isinstance(source, Image.Image) else Image.open(source)).convert('RGB')
    # Recover glyph opacity from the original uniform terminal background.
    # Recoloring the glyphs avoids dark halos on light pages.
    alpha = original.convert('L').point(lambda value: max(0, min(255, round((value - 19) * 1.9))))
    face = alpha.crop((55, 72, 375, 480)).resize((232, 296), Image.Resampling.LANCZOS)
    alpha = Image.new('L', PORTRAIT_SIZE)
    alpha.paste(face, (29, 34))
    portrait = Image.new('RGBA', PORTRAIT_SIZE, ImageColor.getrgb(color) + (0,))
    portrait.putalpha(alpha)
    return portrait


def animated_about(assets, theme, palette, about):
    """Animate only the portrait row; keep the large remainder lossless PNG."""
    frames, durations = [], []
    shared_palette = None
    with Image.open(assets / 'andre-ascii.gif') as original:
        for source in ImageSequence.Iterator(original):
            frame = Image.new('RGBA', (1200, ABOUT_H), TRANSPARENT)
            frame.alpha_composite(transparent_portrait(source, palette['portrait']), PORTRAIT_AT)
            frame.alpha_composite(about, (TEXT_AT, 0))
            portrait_corners(frame, palette)
            if shared_palette is None:
                frame.save(assets / f'profile-about-{theme}.png')
            # GIF has binary transparency. Matte only the antialiased glyph edges,
            # leaving all empty space transparent over GitHub's own background.
            matte = Image.new('RGBA', frame.size, palette['matte'])
            matte.alpha_composite(frame)
            rgb = matte.convert('RGB')
            if shared_palette is None:
                shared_palette = rgb.quantize(colors=32, dither=Image.Dither.NONE)
            indexed = rgb.quantize(palette=shared_palette, dither=Image.Dither.NONE)
            indexed.paste(255, mask=frame.getchannel('A').point(lambda alpha: 255 if alpha == 0 else 0))
            indexed.info['transparency'] = 255
            duration = source.info.get('duration', 100)
            if frames and indexed.tobytes() == frames[-1].tobytes():
                durations[-1] += duration
            else:
                frames.append(indexed)
                durations.append(duration)
    # Write the fixed text once, then send only the small portrait rectangle.
    # A transparent clearing frame removes the initial portrait without erasing
    # the text. Each later portrait clears its own rectangle before the next one.
    with (assets / f'profile-about-{theme}.gif').open('wb') as output:
        header, _ = GifImagePlugin.getheader(frames[0], info={
            'loop': 0, 'transparency': 255, 'background': 255, 'optimize': False})
        output.writelines(header)
        output.writelines(GifImagePlugin.getdata(frames[0], duration=durations[0],
                                                disposal=1, transparency=255))
        clear = Image.new('P', PORTRAIT_SIZE, 255)
        clear.putpalette(frames[0].getpalette())
        output.writelines(GifImagePlugin.getdata(clear, offset=PORTRAIT_AT, duration=10,
                                                disposal=2, transparency=255))
        for frame, duration in zip(frames[1:], durations[1:]):
            portrait = frame.crop(PORTRAIT_AT + (PORTRAIT_AT[0] + PORTRAIT_SIZE[0], PORTRAIT_SIZE[1]))
            output.writelines(GifImagePlugin.getdata(portrait, offset=PORTRAIT_AT,
                                                    duration=duration, disposal=2, transparency=255))
        output.write(b';')


def themed_picture(root, stem, alt, animated=False, width='100%'):
    sources = []
    extension = 'gif' if animated else 'png'
    for theme in ['dark', 'light']:
        sources.append(f'<source media="(prefers-color-scheme: {theme})" srcset="'
                       + image_url(root, f'{stem}-{theme}.{extension}') + '" />')
    return ('<picture>' + ''.join(sources) + '<img src="'
            + image_url(root, f'{stem}-light.{extension}')
            + '" width="' + width + '" align="top" alt="' + alt + '" /></picture>')


def badge_img(root, stem, alt):
    return '<img src="' + image_url(root, stem + '.png') + '" height="28" alt="' + alt + '" />'


def build_github_layout(root, font):
    assets = root / 'assets'
    for theme, palette in THEMES.items():
        panels = []
        for name in ['hero', 'about-pair', 'status', 'activity', 'stack']:
            if name == 'about-pair':
                panel = Image.new('RGBA', (1200, ABOUT_H), TRANSPARENT)
                panel.alpha_composite(transparent_portrait(assets / 'andre-ascii.png', palette['portrait']), PORTRAIT_AT)
                panel.alpha_composite(Image.open(assets / f'about-{theme}.png'), (TEXT_AT, 0))
                portrait_corners(panel, palette)
            else:
                panel = Image.open(assets / f'{name}-{theme}.png').convert('RGBA')
            panels.append(panel)
        height = sum(panel.height for panel in panels) + 28 * len(panels)
        main = Image.new('RGBA', (1200, height), TRANSPARENT)
        y = 0
        for panel in panels:
            main.alpha_composite(panel, (0, y))
            y += panel.height + 28
        main.save(assets / f'profile-card-{theme}.png')
        preview = Image.new('RGBA', main.size, palette['matte'])
        preview.alpha_composite(main)
        preview.convert('RGB').save(root / ('PREVIA.png' if theme == 'light' else 'PREVIA-ESCURO.png'))
        # Adjoining slices keep the alignment while the portrait alone is animated.
        about_y = panels[0].height + 28
        body_y = about_y + panels[1].height + 28
        main.crop((0, 0, 1200, panels[0].height)).save(assets / f'profile-header-{theme}.png')
        main.crop((0, body_y, 1200, height)).save(assets / f'profile-body-{theme}.png')
        animated_about(assets, theme, palette, Image.open(assets / f'about-{theme}.png').convert('RGBA'))

    alt = ('Status do GitHub: repositórios públicos, estrelas, commits, pull requests, issues e seguidores; '
           'linguagens mais usadas; contribuições no período, sequência atual e maior sequência. '
           'Calendário de contribuições atualizado automaticamente. '
           'Ferramentas: Power BI, Python, Excel, Alteryx, SAP e PowerPoint; conhecimentos em HTML, CSS, '
           'JavaScript e Lua; GitHub; experiência anterior em MySQL nos servidores de Tibia e GTA V / FiveM. '
           'Office 365 com Excel e PowerPoint.')
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    username = content['user']['login']
    banner = '<p align="center">' + themed_picture(root, 'profile-header',
             'André Mello — Data & Analytics. Consultoria, tecnologia e engenharia.') + '</p>'
    links = ('<p align="center"><a href="https://www.linkedin.com/in/aamello/">'
             + badge_img(root, 'badge-linkedin', 'LinkedIn — André Mello') + '</a> '
             '<a href="https://github.com/' + username + '?tab=repositories">'
             + badge_img(root, 'badge-github', 'GitHub — explorar meus repositórios') + '</a></p>')
    about = '<p align="center">' + themed_picture(root, 'profile-about',
            'Sobre mim — retrato ASCII animado de André Mello. Dados, tecnologia e visão de negócio.', animated=True) + '</p>'
    body = '<p align="center">' + themed_picture(root, 'profile-body', alt) + '</p>'
    project_table = projects_markdown(content, username)
    projects_head = ('<p align="center">' + themed_picture(root, 'section-projects', 'Projetos em destaque') + '</p>') if project_table else ''
    top = banner + '\n' + links + '\n\n' + about + '\n\n' + body
    readme = top + '\n\n' + projects_head + '\n\n' + project_table
    preview_body = top + projects_head + projects_html(content, username)
    (root / 'README.md').write_text(readme, encoding='utf-8')
    preview_html = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>André Mello — prévia adaptativa</title><style>'
                    ':root{color-scheme:light dark}body{margin:0;background:light-dark(#f6f8fa,#010409);font:14px/1.5 system-ui}'
                    'main{max-width:900px;background:light-dark(#fff,#0d1117);border:1px solid light-dark(#d1d9e0,#3d444d);'
                    'border-radius:6px;padding:24px;margin:24px auto}p{margin:0 0 16px}img{max-width:100%;height:auto;vertical-align:middle}'
                    'img[height="28"]{height:28px;width:auto}'
                    'table{border-collapse:collapse;width:100%;margin:8px 0 20px}th,td{border:1px solid light-dark(#d1d9e0,#3d444d);padding:6px 13px;vertical-align:top}th{background:light-dark(#f6f8fa,#151b23)}'
                    '@media(max-width:600px){main{padding:12px;margin:8px}}</style><main>'
                    + preview_body.replace(ASSET_HOST, './assets/') + '</main></html>')
    (root / 'previa.html').write_text(preview_html, encoding='utf-8')
    print('Transparent, animated profile built for light and dark GitHub themes.')
