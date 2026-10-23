"""An editorial introduction with an engineering drawing around the portrait."""
from PIL import Image, ImageDraw, ImageColor
from themes import TRANSPARENT
from branding import TYPE, MARGIN
from profile_i18n import DEFAULT, tr

INTRO_H = 304
PORTRAIT_AT = (910, 8)
PORTRAIT_SIZE = (230, 288)


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
    text(96, 108, 'DADOS · AUTOMAÇÃO · ENGENHARIA', TYPE['meta'], palette['brand'], True)
    text(MARGIN, 157, 'Dados e automação na prática.', TYPE['hero'], palette['brand'], True)
    text(MARGIN, 213, 'Projetos de análise de dados, integrações e engenharia.', TYPE['body'], palette['muted'])
    line([(MARGIN, 270), (740, 270)], palette['line'])
    line([(MARGIN,270),(112,270)],palette['brand'],3)
    line([(112,270),(156,270)],palette['highlight'],3)

    # The gridded portrait is an illustration, not a fabricated performance chart.
    panel = [(906, 10), (1170, 10), (1170, 270), (1142, 298), (878, 298), (878, 38)]
    d.polygon([(x*s, y*s) for x, y in panel], fill=palette['surface'])
    faint = ImageColor.getrgb(palette['line']) + (110,)
    grid = Image.new('RGBA', image.size, TRANSPARENT)
    gd = ImageDraw.Draw(grid)
    for x in range(898, 1170, 24):
        gd.line((x*s, 28*s, x*s, 280*s), fill=faint, width=s)
    for y in range(28, 281, 24):
        gd.line((896*s, y*s, 1152*s, y*s), fill=faint, width=s)
    image.alpha_composite(grid)
    d = ImageDraw.Draw(image)
    # Abstract routing nodes connect the portrait to the technical identity.
    line([(770,98),(824,98),(852,70),(878,70)],palette['brand_line'])
    line([(820,130),(850,130),(878,102)],palette['brand_line'])
    for x,y in [(770,98),(820,130),(1170,100)]:
        d.ellipse(((x-4)*s,(y-4)*s,(x+4)*s,(y+4)*s),fill=palette['highlight'])
    line(panel + [panel[0]], palette['brand_line'])
    line([(878, 90), (878, 38), (906, 10), (996, 10)], palette['brand'], 2)
    line([(1080, 298), (1142, 298), (1170, 270), (1170, 212)], palette['brand'], 2)

    # A small isometric data module anchors the drawing at the left margin.
    line([(833, 246), (857, 232), (881, 246), (857, 260), (833, 246),
          (833, 274), (857, 288), (881, 274), (881, 246)], palette['brand'], 2)
    line([(857, 260), (857, 288)], palette['brand'], 2)
    line([(833, 260), (857, 274), (881, 260)], palette['brand_line'])
    line([(857, 232), (857, 204), (878, 183)], palette['brand_line'])
    for x, y in [(857, 204)]:
        d.ellipse(((x-3)*s, (y-3)*s, (x+3)*s, (y+3)*s), fill=palette['brand'])
    return image.resize((1200, INTRO_H), Image.Resampling.LANCZOS)
