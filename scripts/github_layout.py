"""Compose theme-aware PNGs and a small, transparent animated portrait block."""
from PIL import Image, ImageColor, ImageSequence, GifImagePlugin
import hashlib, json
from themes import THEMES, TRANSPARENT
from intro_panel import PORTRAIT_AT, PORTRAIT_SIZE

ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'


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


def animated_intro(assets, theme, palette, background):
    """Animate the portrait inside one compact, theme-aware introduction."""
    frames, durations = [], []
    shared_palette = None
    with Image.open(assets / 'andre-ascii.gif') as original:
        for source in ImageSequence.Iterator(original):
            frame = background.copy()
            frame.alpha_composite(transparent_portrait(source, palette['portrait']), PORTRAIT_AT)
            if shared_palette is None:
                frame.save(assets / f'profile-intro-{theme}.png')
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
    with (assets / f'profile-intro-{theme}.gif').open('wb') as output:
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
            portrait = frame.crop(PORTRAIT_AT + (PORTRAIT_AT[0] + PORTRAIT_SIZE[0], PORTRAIT_AT[1] + PORTRAIT_SIZE[1]))
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
    return '<img src="' + image_url(root, stem + '.png') + '" height="22" alt="' + alt + '" />'


def build_github_layout(root, font):
    assets = root / 'assets'
    for theme, palette in THEMES.items():
        panels = []
        for name in ['intro', 'status', 'activity', 'stack']:
            if name == 'intro':
                panel = Image.open(assets / f'intro-background-{theme}.png').convert('RGBA')
                panel.alpha_composite(transparent_portrait(assets / 'andre-ascii.png', palette['portrait']), PORTRAIT_AT)
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
        animated_intro(assets, theme, palette,
                       Image.open(assets / f'intro-background-{theme}.png').convert('RGBA'))

    alt = ('Status do GitHub: repositórios públicos, estrelas, commits, pull requests, issues e seguidores; '
           'composição de código dos repositórios; total de contribuições desde a criação da conta, sequência atual e maior sequência.')
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    username = content['user']['login']
    intro = '<p align="center">' + themed_picture(root, 'profile-intro',
             'André Mello — Consultoria e Data & Analytics. Governança de portfólio. '
             'Dados para decisões executivas. PMO, automação e controle físico-financeiro. '
             'Engenheiro Civil, MSc. em Administração. '
             'Retrato ASCII animado.', animated=True) + '</p>'
    links = ('<p align="center"><a href="https://www.linkedin.com/in/aamello/">'
             + badge_img(root, 'badge-linkedin', 'LinkedIn — André Mello') + '</a> '
             '<a href="https://github.com/' + username + '?tab=repositories">'
             + badge_img(root, 'badge-github', 'GitHub — explorar meus repositórios') + '</a> '
             '<a href="mailto:andremello@outlook.com">'
             + badge_img(root, 'badge-email', 'E-mail — andremello@outlook.com') + '</a></p>')
    status = '<p align="center">' + themed_picture(root, 'status', alt) + '</p>'
    snake = '<p align="center">' + themed_picture(root, 'contribution-snake',
             'Cobrinha animada percorrendo as contribuições públicas reais de André Mello.', animated=True) + '</p>'
    tools = '<p align="center">' + themed_picture(root, 'stack',
             'Tecnologias e ferramentas: Power BI, Python, Excel, Alteryx, SAP, PowerPoint; '
             'HTML, CSS, JavaScript e Lua; GitHub e experiência anterior em MySQL.') + '</p>'
    top = '\n\n'.join([intro, links, status, snake, tools])
    readme = preview_body = top
    (root / 'README.md').write_text(readme, encoding='utf-8')
    preview_html = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>André Mello — prévia adaptativa</title><style>'
                    ':root{color-scheme:light dark}body{margin:0;background:light-dark(#f6f8fa,#010409);font:14px/1.5 system-ui}'
                    'main{max-width:900px;background:light-dark(#fff,#0d1117);border:1px solid light-dark(#d1d9e0,#3d444d);'
                    'border-radius:6px;padding:24px;margin:24px auto}p{margin:0 0 16px}img{max-width:100%;height:auto;vertical-align:middle}'
                    'img[height="22"]{height:22px;width:auto}'
                    '@media(max-width:600px){main{padding:12px;margin:8px}}</style><main>'
                    + preview_body.replace(ASSET_HOST, './assets/') + '</main></html>')
    (root / 'previa.html').write_text(preview_html, encoding='utf-8')
    print('Transparent, animated profile built for light and dark GitHub themes.')
