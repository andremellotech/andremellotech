"""The AM cut-corner signature, data prism and coordinated domain colors."""
from PIL import ImageDraw


def section_heading(draw, palette, font, number, title, y=16):
    draw.polygon([(35, y), (57, y), (57, y + 18), (52, y + 23), (30, y + 23), (30, y + 5)], fill='#174d82')
    draw.text((35, y + 3), number, font=font(12, mono=True), fill='white')
    draw.line((31, y + 22, 43, y + 22), fill=palette['copper'], width=2)
    draw.text((70, y + 2), title, font=font(15, True), fill=palette['accent'])


def monogram(draw, palette, font, x=30, y=25):
    draw.polygon([(x + 12, y), (x + 64, y), (x + 64, y + 52),
                  (x + 52, y + 64), (x, y + 64), (x, y + 12)], fill='#123d65')
    # A and M share a junction: the same connected geometry as the data motif.
    draw.line((x + 12, y + 45, x + 23, y + 16, x + 34, y + 45), fill='white', width=3)
    draw.line((x + 16, y + 35, x + 30, y + 35), fill='white', width=3)
    draw.line((x + 34, y + 45, x + 34, y + 16, x + 43, y + 31, x + 52, y + 16, x + 52, y + 45),
              fill='#4ed6dc', width=3)
    draw.ellipse((x + 32, y + 43, x + 36, y + 47), fill='#d5a372')
    draw.line((x + 61, y + 9, x + 61, y + 35), fill='#4ed6dc', width=3)
    draw.line((x + 13, y + 60, x + 39, y + 60), fill='#d5a372', width=3)


def chamfered_card(draw, box, fill, outline, cut=14):
    left, top, right, bottom = box
    points = [(left + cut, top), (right, top), (right, bottom - cut),
              (right - cut, bottom), (left, bottom), (left, top + cut)]
    draw.polygon(points, fill=fill, outline=outline)


def data_prism(draw, palette, x=860, y=108):
    """An architectural data mark, with no quantitative axes or invented values."""
    corners = [(0, 20), (112, -10), (270, 30), (158, 62)]
    for offset in [34, 17, 0]:
        points = [(x + dx, y + dy + offset) for dx, dy in corners]
        draw.polygon(points, fill=palette['surfaces'][0] if offset == 0 else None,
                     outline=palette['brand_line'], width=2)
    draw.line((x, y + 20, x + 112, y - 10), fill=palette['cyan'], width=3)
    draw.line((x + 112, y - 10, x + 270, y + 30), fill=palette['copper'], width=3)
    draw.line((x + 158, y + 62, x + 158, y + 96), fill=palette['brand'], width=2)
    draw.line((x + 270, y + 30, x + 270, y + 64), fill=palette['cyan'], width=2)
    draw.line((x + 57, y + 22, x + 112, y + 7, x + 209, y + 32, x + 155, y + 46, x + 57, y + 22),
              fill=palette['brand_line'], width=2)
    for dx, dy, color in [(57, 22, 'brand'), (112, 7, 'cyan'), (209, 32, 'copper')]:
        draw.ellipse((x + dx - 3, y + dy - 3, x + dx + 3, y + dy + 3), fill=palette[color])


def domain_icon(draw, palette, kind, x, y):
    color = [palette['brand'], palette['cyan'], palette['copper']][kind]
    if kind == 0:
        for dx, height in [(0, 9), (9, 17), (18, 25)]:
            draw.rounded_rectangle((x + dx, y + 25 - height, x + dx + 5, y + 25), radius=1, outline=color)
    elif kind == 1:
        draw.line((x + 3, y + 3, x + 23, y + 23), fill=color)
        draw.line((x + 3, y + 23, x + 23, y + 3), fill=color)
        for dx, dy in [(0, 0), (20, 0), (0, 20), (20, 20)]:
            draw.rectangle((x + dx, y + dy, x + dx + 6, y + dy + 6), outline=color)
    else:
        for dx, dy in [(0, 0), (7, 7), (14, 14)]:
            draw.rectangle((x + dx, y + dy, x + dx + 13, y + dy + 13), outline=color)


def portrait_corners(panel, palette):
    draw = ImageDraw.Draw(panel)
    draw.line((74, 112, 146, 40, 524, 40, 524, 440, 452, 512, 74, 512, 74, 112),
              fill=palette['brand_line'], width=2)
    draw.line((74, 166, 74, 112, 146, 40, 270, 40), fill=palette['brand'], width=3)
    draw.line((524, 186, 524, 314), fill=palette['cyan'], width=3)
    draw.line((330, 512, 452, 512), fill=palette['copper'], width=3)
    for x, y, color in [(146, 40, 'brand'), (524, 186, 'cyan'), (452, 512, 'copper')]:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=palette[color])
    for x in range(478, 511, 12):
        for y in range(64, 101, 12):
            draw.ellipse((x, y, x + 2, y + 2), fill=palette['brand_line'])
