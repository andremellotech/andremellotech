"""Restrained visual signatures shared by the profile's themed panels."""
from PIL import ImageDraw


def section_heading(draw, palette, font, number, title, y=16):
    draw.rounded_rectangle((30, y, 55, y + 23), radius=4, outline=palette['line'])
    draw.text((35, y + 3), number, font=font(12, mono=True), fill=palette['brand'])
    draw.text((70, y + 2), title, font=font(15, True), fill=palette['accent'])


def monogram(draw, palette, font, x=30, y=25):
    draw.rounded_rectangle((x, y, x + 64, y + 64), radius=10, outline=palette['brand_line'], width=2)
    word, face = 'AM', font(24, True)
    draw.text((x + (64 - draw.textlength(word, font=face)) / 2, y + 15), word, font=face, fill=palette['brand'])
    draw.line((x + 19, y + 55, x + 45, y + 55), fill=palette['brand'], width=2)


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
    for x, y, dx, dy in [(74, 40, 1, 1), (524, 40, -1, 1),
                          (74, 512, 1, -1), (524, 512, -1, -1)]:
        draw.line((x, y + dy * 24, x, y, x + dx * 24, y), fill=palette['brand_line'], width=2)
    draw.ellipse((71, 37, 77, 43), fill=palette['brand'])
