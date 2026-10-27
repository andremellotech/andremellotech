"""A compact technical stack with one neutral badge system."""
from PIL import Image, ImageDraw, ImageChops
from themes import TRANSPARENT
from branding import TYPE, MARGIN, section_heading
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 568


def _product(root, label, kind, font, palette):
    """One pill, font, icon box and padding for every tool, drawn at 2x."""
    scale = 2
    face = font(TYPE['body'] * scale, True)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    width = round(probe.textlength(label, font=face) / scale) + 64
    image = Image.new('RGBA', (width * scale, 48 * scale), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, width*2 - 2, 94), radius=47,
                           fill=palette['matte'], outline=palette['brand_line'], width=2)
    def rect(box, fill, radius=0, outline=None, width=1):
        draw.rounded_rectangle(tuple(v*2 for v in box), radius=radius*2,
                               fill=fill, outline=outline, width=width*2)
    def polygon(points, fill):
        draw.polygon([(x*2,y*2) for x,y in points], fill=fill)
    def line(points, fill, width=2):
        draw.line([(x*2,y*2) for x,y in points], fill=fill, width=width*2, joint='curve')
    def symbol(value, x, y, size, color='white'):
        draw.text((x*2,y*2), value, font=font(size*2, True), fill=color, anchor='mm')
    if kind == 'automate':
        polygon([(13,13),(26,13),(39,24),(26,35),(13,35),(26,24)], '#0066ff')
        polygon([(13,13),(23,13),(34,24),(23,35),(13,35),(25,24)], '#75b6ff')
    elif kind == 'oracle':
        rect((12,16,40,32), None, 8, '#e5484d', 3)
    elif kind == 'powerbi':
        for x,y,color in [(14,25,'#f4d867'),(23,18,'#e7be2c'),(32,10,'#cda418')]:
            rect((x,y,x+7,37), color, 2)
    elif kind == 'python':
        rect((17,10,36,26), '#3776ab', 5)
        rect((12,17,24,32), '#3776ab', 4)
        rect((17,23,36,38), '#ffd343', 5)
        rect((29,16,41,31), '#ffd343', 4)
        rect((21,13,23,15), 'white', 1)
        rect((30,33,32,35), '#3776ab', 1)
    elif kind in ['excel','powerpoint']:
        color, pale, letter = ('#107c41','#21a366','X') if kind=='excel' else ('#c43e1c','#e98262','P')
        rect((20,11,39,37), pale, 3)
        line([(24,20),(36,20)], color, 1)
        line([(24,28),(36,28)], color, 1)
        rect((12,16,30,34), color, 2)
        symbol(letter,21,25,16)
    elif kind == 'alteryx':
        color = '#0085b2' if palette['name']=='light' else '#4dc1e7'
        # The small wordmark retains the existing local brand artwork.
        source = Image.open(root/'assets/badges/alteryx.webp').convert('RGBA').crop((10,9,43,27))
        alpha = source.convert('L').point(lambda v:max(0,min(255,round((v-125)*255/130))))
        mark = Image.new('RGBA',source.size,color)
        mark.putalpha(alpha)
        mark = mark.resize((60,33),Image.Resampling.LANCZOS)
        image.alpha_composite(mark,(20,31))
    elif kind == 'sap':
        polygon([(11,14),(42,14),(31,34),(11,34)], '#008bc9')
        symbol('SAP',24,24,9)
    elif kind in ['html','css']:
        color, number = ('#e34f26','5') if kind=='html' else ('#1572b6','3')
        polygon([(14,10),(39,10),(36,35),(26,39),(17,35)], color)
        symbol(number,26,24,20)
    elif kind == 'javascript':
        rect((12,11,40,38), '#f7df1e', 3)
        symbol('JS',27,27,15,'#24292f')
    elif kind == 'lua':
        color = '#000080' if palette['name']=='light' else '#a7a7ff'
        rect((13,14,36,37), color, 12)
        rect((31,10,40,19), color, 5)
        rect((26,18,32,24), palette['matte'], 3)
    elif kind == 'git':
        polygon([(26,8),(42,24),(26,40),(10,24)], '#f05032')
        line([(21,15),(32,26)], 'white', 2)
        line([(24,18),(24,32)], 'white', 2)
        for x,y in [(21,15),(32,26),(24,32)]:
            rect((x-2,y-2,x+2,y+2), 'white', 2)
    elif kind == 'github':
        source = Image.open(root/'assets/badges/GitHub.webp').convert('RGBA').crop((15,7,37,29))
        alpha = source.convert('L').point(lambda v:max(0,min(255,round((v-32)*255/223))))
        alpha = ImageChops.multiply(alpha,source.getchannel('A')).resize((52,52),Image.Resampling.LANCZOS)
        mark = Image.new('RGBA',alpha.size,palette['text'])
        mark.putalpha(alpha)
        image.alpha_composite(mark,(26,22))
    elif kind == 'mysql':
        color = '#00758f' if palette['name']=='light' else '#7cc3d4'
        line([(13,14),(22,17),(29,23),(31,30),(39,35),(32,34),(28,28),(23,27),(20,22),(16,20),(13,14)],color)
        line([(24,20),(24,14),(28,23)],color,1)
    else:
        raise ValueError('Unknown tool icon: '+kind)
    draw.text((50*2,24*2), label, font=face, fill=palette['text'], anchor='lm')
    return image.resize((width,48),Image.Resampling.LANCZOS)


def render_technology(root, font, palette, locale=DEFAULT):
    image = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    section_heading(draw, palette, font, tr(locale, 'Tecnologias e ferramentas'), 12)
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

    def products(items):
        return [_product(root,label,kind,font,palette) for label,kind in items]
    card((MARGIN, 72, 1176, 206), 'Dados, sistemas e automação')
    core = products([('Power BI','powerbi'),('Python','python'),('Excel','excel'),('Alteryx','alteryx'),
                     ('Power Automate','automate'),('Oracle Cloud','oracle')])
    badges(core, 44, 124, 1156)

    card((MARGIN, 230, 588, 422), 'Sistemas e colaboração')
    badges(products([('SAP','sap'),('PowerPoint','powerpoint')]),44,286,568)
    badges(products([('Git','git'),('GitHub','github')]),44,346,568)

    card((612, 230, 1176, 422), 'Linguagens · conhecimentos')
    badges(products([('HTML','html'),('CSS','css'),('JavaScript','javascript'),('Lua','lua')]),632,286,1156)

    card((MARGIN, 446, 1176, 550), 'Banco de dados · experiência anterior')
    database = _product(root,'MySQL','mysql',font,palette)
    image.alpha_composite(database, (44, 492))
    text((44+database.width+24, 503), 'MySQL em servidores de Tibia e GTA V / FiveM.',
              font=font(TYPE['body']), fill=palette['muted'])
    image.save(root/'assets'/f'{localized("stack", locale)}-{palette["name"]}.png')
