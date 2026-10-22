"""A restrained AM signature and a single navy visual language."""
from PIL import ImageDraw


def section_heading(draw, palette, font, number, title, y=16):
    draw.polygon([(35, y), (57, y), (57, y + 18), (52, y + 23), (30, y + 23), (30, y + 5)], fill='#294b70')
    draw.text((35, y + 3), number, font=font(12, mono=True), fill='white')
    draw.text((70, y + 2), title, font=font(15, True), fill=palette['accent'])


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
