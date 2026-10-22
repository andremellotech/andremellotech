"""A restrained AM signature and a single navy visual language."""
from PIL import ImageDraw


def section_heading(draw, palette, font, number, title, y=16):
    draw.polygon([(35, y), (57, y), (57, y + 18), (52, y + 23), (30, y + 23), (30, y + 5)], fill='#294b70')
    draw.text((35, y + 3), number, font=font(12, mono=True), fill='white')
    draw.text((70, y - 1), title, font=font(20, True), fill=palette['accent'])


def banner_background(image):
    """A single navy banner with a quiet routing pattern, without invented data."""
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 8, 1188, 216), radius=18, fill='#102338')
    for index in range(9):
        shift = index * 22
        draw.line((810 + shift, 196, 890 + shift, 116, 1160, 116 - shift // 2),
                  fill='#203b54', width=1)
    draw.line((850, 194, 938, 106, 1150, 106), fill='#3e5d78', width=2)
    draw.line((938, 106, 994, 50, 1150, 50), fill='#294961', width=2)
    for x, y in [(938, 106), (994, 50), (1150, 106)]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill='#718ba2')


def metric_icon(draw, x, y, kind, color):
    if kind == 0:
        draw.line((x, y + 5, x, y + 22, x + 25, y + 22, x + 25, y + 5,
                   x + 11, y + 5, x + 8, y + 1, x, y + 1, x, y + 5), fill=color, width=2)
    elif kind == 1:
        for dx in [0, 9, 18]:
            for dy in [0, 9, 18]:
                draw.rounded_rectangle((x + dx, y + dy, x + dx + 5, y + dy + 5), radius=1, outline=color)
    elif kind == 2:
        draw.rounded_rectangle((x, y + 3, x + 24, y + 24), radius=3, outline=color, width=2)
        draw.line((x, y + 9, x + 24, y + 9), fill=color, width=2)
        draw.line((x + 6, y, x + 6, y + 6), fill=color, width=2)
        draw.line((x + 18, y, x + 18, y + 6), fill=color, width=2)
    else:
        draw.line((x + 2, y + 25, x + 2, y, x + 23, y + 3, x + 20, y + 14,
                   x + 2, y + 11), fill=color, width=2)


def monogram(draw, palette, font, x=30, y=25):
    draw.polygon([(x + 12, y), (x + 64, y), (x + 64, y + 52),
                  (x + 52, y + 64), (x, y + 64), (x, y + 12)], fill='#17324d')
    # A and M share a junction, keeping the signature in one color.
    draw.line((x + 12, y + 45, x + 23, y + 16, x + 34, y + 45), fill='white', width=3)
    draw.line((x + 16, y + 35, x + 30, y + 35), fill='white', width=3)
    draw.line((x + 34, y + 45, x + 34, y + 16, x + 43, y + 31, x + 52, y + 16, x + 52, y + 45),
              fill='white', width=3)


def chamfered_card(draw, box, fill, outline, cut=14):
    left, top, right, bottom = box
    points = [(left + cut, top), (right, top), (right, bottom - cut),
              (right - cut, bottom), (left, bottom), (left, top + cut)]
    draw.polygon(points, fill=fill, outline=outline)


def domain_icon(draw, palette, kind, x, y):
    color = palette['brand']
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
    draw.line((74, 166, 74, 112, 146, 40, 270, 40), fill=palette['brand'], width=2)
