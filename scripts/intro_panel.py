"""An editorial introduction with an engineering drawing around the portrait."""
from PIL import Image, ImageDraw, ImageColor
from themes import TRANSPARENT
from branding import TYPE, MARGIN
from profile_i18n import DEFAULT, tr

INTRO_H = 400
PORTRAIT_AT = (850, 18)
PORTRAIT_SIZE = (290, 364)


def render_intro(font, palette, scale=2, locale=DEFAULT):
    s = scale
    image = Image.new('RGBA', (1200*s, INTRO_H*s), TRANSPARENT)
    d = ImageDraw.Draw(image)

    def text(x, y, value, size, color, bold=False, mono=False, raw=False):
        d.text((x*s, y*s), value if raw else tr(locale, value), font=font(size*s, bold, mono), fill=color)

    def line(points, color, width=1):
        d.line([(x*s, y*s) for x, y in points], fill=color, width=width*s, joint='curve')

    # Type, whitespace and one blue accent carry the identity across both themes.
    text(MARGIN, 18, '@ANDREMELLOTECH', TYPE['meta'], palette['muted'], mono=True, raw=True)
    text(MARGIN-2, 49, 'André Mello', TYPE['name'], palette['text'], True, raw=True)
    line([(MARGIN, 120), (80, 120)], palette['brand'], 3)
    text(96, 108, 'CONSULTORIA · ENGENHARIA · DADOS', TYPE['meta'], palette['brand'], True)
    text(MARGIN, 156, 'Engenharia, dados e governança.', TYPE['hero'], palette['text'], True)
    text(MARGIN, 198, 'Da estratégia à execução.', TYPE['hero'], palette['text'], True)
    text(MARGIN, 253, 'Portfólio, PMO e automação com foco em resultados.', TYPE['card'], palette['muted'])
    text(MARGIN, 297, 'Consultor na KPMG Brasil · Mais de 6 anos de experiência', TYPE['body'], palette['accent'])
    text(MARGIN, 337, 'Engenheiro Civil · Mestre em Administração', TYPE['body'], palette['muted'])
    line([(MARGIN, 380), (740, 380)], palette['line'])

    # The gridded portrait is an illustration, not a fabricated performance chart.
    panel = [(836, 20), (1170, 20), (1170, 348), (1142, 376), (808, 376), (808, 48)]
    d.polygon([(x*s, y*s) for x, y in panel], fill=palette['surface'])
    faint = ImageColor.getrgb(palette['line']) + (110,)
    grid = Image.new('RGBA', image.size, TRANSPARENT)
    gd = ImageDraw.Draw(grid)
    for x in range(830, 1170, 24):
        gd.line((x*s, 40*s, x*s, 352*s), fill=faint, width=s)
    for y in range(40, 353, 24):
        gd.line((828*s, y*s, 1152*s, y*s), fill=faint, width=s)
    image.alpha_composite(grid)
    d = ImageDraw.Draw(image)
    line(panel + [panel[0]], palette['brand_line'])
    line([(808, 100), (808, 48), (836, 20), (926, 20)], palette['brand'], 2)
    line([(1080, 376), (1142, 376), (1170, 348), (1170, 290)], palette['brand'], 2)

    # A small isometric data module anchors the drawing at the left margin.
    line([(763, 314), (787, 300), (811, 314), (787, 328), (763, 314),
          (763, 342), (787, 356), (811, 342), (811, 314)], palette['brand'], 2)
    line([(787, 328), (787, 356)], palette['brand'], 2)
    line([(763, 328), (787, 342), (811, 328)], palette['brand_line'])
    line([(787, 300), (787, 272), (808, 251)], palette['brand_line'])
    for x, y in [(787, 272), (1170, 130)]:
        d.ellipse(((x-3)*s, (y-3)*s, (x+3)*s, (y+3)*s), fill=palette['brand'])
    return image.resize((1200, INTRO_H), Image.Resampling.LANCZOS)
