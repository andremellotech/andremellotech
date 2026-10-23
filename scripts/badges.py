"""Two-tone, shields-style badges drawn locally (no external badge service)."""
from PIL import Image, ImageDraw, ImageChops

HEIGHT = 56  # drawn at 2x; shown at height="28"


def _text_width(draw, text, face):
    return round(draw.textlength(text, font=face))


def render_badge(path, font, label, value, label_bg, value_bg, icon=None, assets=None):
    face = font(24, True)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    icon_w = 52 if icon else 0
    compact = bool(icon and not label)
    left_w = 68 if compact else 22 + icon_w + _text_width(probe, label, face) + 22
    padding = 18 if compact else 22
    right_w = padding + _text_width(probe, value, face) + padding
    width = left_w + right_w
    badge = Image.new('RGBA', (width, HEIGHT), value_bg)
    draw = ImageDraw.Draw(badge)
    draw.rectangle((0, 0, left_w, HEIGHT), fill=label_bg)
    x = 22
    if icon == 'linkedin':
        draw.rounded_rectangle((x, 11, x + 34, 45), radius=6, fill='white')
        draw.text((x + 6, 11), 'in', font=font(25, True), fill='#0a66c2')
    elif icon == 'email':
        draw.rounded_rectangle((x, 15, x + 34, 41), radius=3, outline='white', width=3)
        draw.line((x + 2, 18, x + 17, 30, x + 32, 18), fill='white', width=3)
    elif icon == 'github':
        source = Image.open(assets / 'badges/GitHub.webp').convert('RGBA').crop((15, 7, 37, 29))
        alpha = source.convert('L').point(lambda v: max(0, min(255, round((v - 32) * 255 / 223))))
        alpha = ImageChops.multiply(alpha, source.getchannel('A')).resize((34, 34), Image.Resampling.LANCZOS)
        mark = Image.new('RGBA', alpha.size, 'white')
        mark.putalpha(alpha)
        badge.alpha_composite(mark, (x, 11))
    x += icon_w
    draw.text((x, 12), label, font=face, fill='white')
    draw.text((left_w + padding, 12), value, font=face, fill='white')
    mask = Image.new('L', badge.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, HEIGHT - 1), radius=10, fill=255)
    badge.putalpha(ImageChops.multiply(mask, badge.getchannel('A')))
    badge.save(path)
    return badge.size
