"""Readable technology groups and education with the shared profile type scale."""
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import TYPE, MARGIN, section_heading
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 808


def _badge(root, stem, palette, height=48):
    badge = Image.open(root/'assets/badges'/f'{stem}.webp').convert('RGBA')
    if palette['name'] == 'light':
        mask = badge.getchannel('A').point(lambda alpha: min(255, round(alpha * 2.5)))
        base = Image.new('RGBA', badge.size, '#0d1117')
        base.putalpha(mask)
        base.alpha_composite(badge)
        badge = base
    return badge.resize((round(badge.width * height / badge.height), height), Image.Resampling.LANCZOS)


def _product(label, kind, font, palette):
    """Local vector marks for the two products added from the supplied LinkedIn."""
    face = font(TYPE['body'], True)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    width = round(probe.textlength(label, font=face)) + 70
    image = Image.new('RGBA', (width, 48), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, 47), radius=24,
                           fill=palette['surface'], outline=palette['brand_line'])
    if kind == 'automate':
        draw.polygon([(15, 13), (28, 13), (41, 24), (28, 35), (15, 35), (28, 24)], fill='#0066ff')
        draw.polygon([(15, 13), (25, 13), (36, 24), (25, 35), (15, 35), (27, 24)], fill='#75b6ff')
    else:
        draw.rounded_rectangle((13, 16, 42, 32), radius=8, outline='#e5484d', width=4)
    draw.text((52, 10), label, font=face, fill=palette['text'])
    return image


def render_technology(root, font, palette, locale=DEFAULT):
    image = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    section_heading(draw, palette, font, tr(locale, 'Tecnologias e formação'), 12)
    def text(xy, value, **kwargs):
        draw.text(xy, tr(locale, value), **kwargs)
    def card(box, title):
        draw.rounded_rectangle(box, radius=12, fill=palette['surface'], outline=palette['line'])
        text((box[0]+20, box[1]+17), title, font=font(TYPE['card'], True), fill=palette['accent'])
    def badges(items, x, y, limit):
        start = x
        for badge in items:
            if x + badge.width > limit:
                x, y = start, y + 60
            image.alpha_composite(badge, (x, y))
            x += badge.width + 10

    card((MARGIN, 72, 1176, 222), 'Dados, sistemas e automação')
    core = [_badge(root, stem, palette) for stem in ['powerbi', 'python', 'excel', 'alteryx']]
    core += [_product('Power Automate', 'automate', font, palette),
             _product('Oracle Cloud', 'oracle', font, palette)]
    badges(core, 44, 124, 1156)
    text((44, 192), 'Análise, integração de dados e automação de rotinas.',
              font=font(TYPE['meta']), fill=palette['muted'])

    card((MARGIN, 246, 588, 462), 'Sistemas e comunicação')
    badges([_badge(root, stem, palette) for stem in ['sap', 'powerpoint']], 44, 302, 568)
    text((44, 378), 'Office 365, apresentações executivas', font=font(TYPE['body']), fill=palette['muted'])
    text((44, 409), 'e organização de informações.', font=font(TYPE['body']), fill=palette['muted'])

    card((612, 246, 1176, 462), 'Linguagens e versionamento')
    badges([_badge(root, stem, palette) for stem in ['HTML2', 'CSS2', 'JavaScript2', 'Lua2', 'GitHub']],
           632, 302, 1156)

    card((MARGIN, 486, 1176, 600), 'Banco de dados · experiência anterior')
    image.alpha_composite(_badge(root, 'MySQL', palette), (44, 536))
    text((210, 547), 'MySQL em servidores de Tibia e GTA V / FiveM.',
              font=font(TYPE['body']), fill=palette['muted'])

    # Academic details are secondary to the practice and outcomes above.
    text((MARGIN, 638), 'Formação em evolução', font=font(TYPE['card'], True), fill=palette['accent'])
    text((MARGIN, 679), 'Engenharia Elétrica · São Judas Tadeu (em curso)',
              font=font(TYPE['meta']), fill=palette['muted'])
    text((MARGIN, 711), 'Engenharia de Segurança do Trabalho · UFPR (em curso)',
              font=font(TYPE['meta']), fill=palette['muted'])
    text((MARGIN, 761), 'Pós-graduação em Construção Civil · FAVENI',
              font=font(TYPE['meta']), fill=palette['muted'])
    draw.line((624, 640, 624, 790), fill=palette['line'])
    text((656, 638), 'Pesquisa e reconhecimento', font=font(TYPE['card'], True), fill=palette['accent'])
    text((656, 679), 'Ex-bolsista FAPESP e CAPES', font=font(TYPE['meta']), fill=palette['muted'])
    text((656, 711), 'Artigo na Brazilian Administration Review', font=font(TYPE['meta']), fill=palette['muted'])
    text((656, 743), 'Destaque profissional KPMG · FY25', font=font(TYPE['meta']), fill=palette['muted'])
    text((656, 775), 'Destaque REIAd · 2023 e 2024', font=font(TYPE['meta']), fill=palette['muted'])
    image.save(root/'assets'/f'{localized("stack", locale)}-{palette["name"]}.png')
