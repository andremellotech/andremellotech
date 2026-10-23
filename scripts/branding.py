"""A restrained AM signature and a single navy visual language."""
from PIL import ImageDraw

MARGIN = 24
GAP = 24
TYPE = dict(name=40, hero=32, section=26, card=22, body=20, meta=18, number=36)


def section_heading(draw, palette, font, title, y=16):
    draw.text((MARGIN, y - 1), title, font=font(TYPE['section'], True), fill=palette['accent'])
    draw.line((MARGIN, y + 40, 1200 - MARGIN, y + 40), fill=palette['line'])


def wrapped_text(draw, xy, value, font, color, width, line_height=29):
    """Wrap measured words without reducing the shared body text size."""
    x, y = xy
    lines, line = [], ''
    for word in value.split():
        candidate = (line + ' ' + word).strip()
        if line and draw.textlength(candidate, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=font, fill=color)
    return len(lines) * line_height


def banner_background(image, height=224):
    """Navy gradient banner with a faint grid, a soft glow and a champagne hairline.

    Purely decorative: no data, no invented figures.
    """
    from PIL import Image, ImageFilter
    box = (12, 8, 1188, height - 8)
    bw, bh = box[2] - box[0], box[3] - box[1]
    base = Image.new('RGBA', (bw, bh))
    px = base.load()
    top, bottom = (9, 22, 38), (22, 52, 82)
    for y in range(bh):
        for x in range(bw):
            t = (x / bw) * 0.55 + (y / bh) * 0.45
            px[x, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
    glow = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((bw - 640, -260, bw + 220, 420), fill=(96, 165, 220, 46))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    grid = ImageDraw.Draw(base)
    for gx in range(0, bw, 28):
        for gy in range(0, bh, 28):
            grid.point((gx, gy), fill=(255, 255, 255, 38))
    # Rising bars: an abstract nod to analytics, without values.
    for i, bar in enumerate([34, 52, 44, 76, 62, 98, 84, 124]):
        bar = round(bar * bh / 208)
        x = bw - 330 + i * 34
        grid.rounded_rectangle((x, bh - 22 - bar, x + 18, bh - 22), radius=4,
                               fill=(120, 170, 214, 22 + i * 5))
    grid.line((bw - 340, bh - 22, bw - 40, bh - 22), fill=(190, 205, 222, 70), width=1)
    mask = Image.new('L', (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=18, fill=255)
    base.putalpha(mask)
    image.alpha_composite(base, (box[0], box[1]))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=18, outline=(255, 255, 255, 40), width=1)


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


def portrait_corners(panel, palette, box=(60, 8, 360, 364), cut=36):
    draw = ImageDraw.Draw(panel)
    x0, y0, x1, y1 = box
    draw.line((x0, y0 + cut, x0 + cut, y0, x1, y0, x1, y1 - cut, x1 - cut, y1, x0, y1, x0, y0 + cut),
              fill=palette['brand_line'], width=2)
    draw.line((x0, y0 + 80, x0, y0 + cut, x0 + cut, y0, x0 + 160, y0), fill=palette['brand'], width=2)


def render_banner(font, width=1200, height=224, scale=2):
    """Premium banner: deep navy glass, a restrained gold accent and geometric lines.

    Drawn at 2x and downsampled for smooth edges. No data or figures: the
    linework is purely decorative.
    """
    from PIL import Image, ImageFilter, ImageChops
    S = scale
    canvas = Image.new('RGBA', (width * S, height * S), (0, 0, 0, 0))
    box = (12 * S, 8 * S, (width - 12) * S, (height - 8) * S)
    bw, bh = box[2] - box[0], box[3] - box[1]

    def gradient(size, tl, tr, bl, br):
        tiny = Image.new('RGBA', (2, 2))
        tiny.putdata([tl, tr, bl, br])
        return tiny.resize(size, Image.Resampling.BILINEAR)

    layer = gradient((bw, bh), (5, 13, 26, 255), (17, 48, 84, 255), (10, 27, 47, 255), (26, 66, 108, 255))

    glow = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((bw * 0.62, -bh * 0.9, bw * 1.12, bh * 0.9), fill=(110, 175, 235, 70))
    gd.ellipse((-bw * 0.06, bh * 0.55, bw * 0.30, bh * 1.5), fill=(201, 169, 106, 26))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60 * S)))

    sheen = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).polygon([(bw * 0.38, 0), (bw * 0.52, 0), (bw * 0.30, bh), (bw * 0.16, bh)],
                                  fill=(255, 255, 255, 9))
    layer.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(6 * S)))

    dot_layer = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    dots = ImageDraw.Draw(dot_layer)
    for gx in range(14 * S, bw, 28 * S):
        for gy in range(14 * S, bh, 28 * S):
            dots.ellipse((gx - 1, gy - 1, gx + 1, gy + 1), fill=(255, 255, 255, 30))
    layer.alpha_composite(dot_layer)

    # A quiet routing motif keeps the banner visual without a decorative chart.
    routing = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    rd = ImageDraw.Draw(routing)
    ox, oy = -box[0], -box[1]
    for index in range(8):
        shift = index * 22 * S
        rd.line((810*S+shift+ox, 196*S+oy, 890*S+shift+ox, 116*S+oy,
                 1160*S+ox, 116*S-shift//2+oy), fill=(160, 198, 232, 40), width=S)
    rd.line((850*S+ox, 194*S+oy, 938*S+ox, 106*S+oy, 1150*S+ox, 106*S+oy),
            fill=(160, 198, 232, 100), width=2*S)
    layer.alpha_composite(routing)

    mask = Image.new('L', (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=22 * S, fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel('A'), mask))
    canvas.alpha_composite(layer, (box[0], box[1]))
    # Semi-transparent strokes go on an overlay: drawing them straight onto
    # the RGBA canvas would replace pixels instead of blending.
    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    o = ImageDraw.Draw(overlay)
    o.rounded_rectangle(box, radius=22 * S, outline=(255, 255, 255, 34), width=S)
    for i in range(160):                          # soft top highlight, fading to both sides
        t = 1 - abs(i - 80) / 80
        o.line((box[0] + 40 * S + round((bw - 80 * S) * i / 160), box[1] + S,
                box[0] + 40 * S + round((bw - 80 * S) * (i + 1) / 160), box[1] + S),
               fill=(255, 255, 255, round(110 * t)), width=S)
    d = ImageDraw.Draw(canvas)

    def spaced(x, y, text, face, fill, tracking):
        for ch in text:
            d.text((x, y), ch, font=face, fill=fill)
            x += d.textlength(ch, font=face) + tracking
        return x

    # --- monogram: glass chamfered tile with gold edge
    mx, my, ms = 46 * S, 62 * S, 100 * S
    cut = 22 * S
    tile = [(mx + cut, my), (mx + ms, my), (mx + ms, my + ms - cut), (mx + ms - cut, my + ms), (mx, my + ms), (mx, my + cut)]
    tile_layer = gradient((ms, ms), (34, 66, 104, 255), (20, 44, 74, 255), (16, 36, 62, 255), (11, 26, 46, 255))
    tile_mask = Image.new('L', (ms, ms), 0)
    ImageDraw.Draw(tile_mask).polygon([(x - mx, y - my) for x, y in tile], fill=255)
    tile_layer.putalpha(tile_mask)
    canvas.alpha_composite(tile_layer, (mx, my))
    o.line(tile + [tile[0]], fill=(214, 182, 118, 235), width=2 * S, joint='curve')
    k = ms / 64
    def m(px, py): return (mx + px * k, my + py * k)
    line = dict(fill='white', width=round(3.4 * S * k / 1.5), joint='curve')
    d.line([m(12, 47), m(23, 15), m(34, 47)], **line)
    d.line([m(16.5, 36), m(29.5, 36)], **line)
    d.line([m(34, 47), m(34, 15), m(43, 31), m(52, 15), m(52, 47)], **line)

    # --- typography
    tx = 176 * S
    spaced(tx, 38 * S, 'ANDREMELLOTECH', font(14 * S, True), (143, 166, 189, 255), 3.2 * S)
    d.text((tx - 3 * S, 54 * S), 'André Mello', font=font(46 * S, True), fill='white')
    for i in range(160):                          # gold hairline fading to the right
        o.line((tx + i * S * 1.4, 134 * S, tx + (i + 1) * S * 1.4, 134 * S),
               fill=(214, 182, 118, round(255 * (1 - i / 160))), width=2 * S)
    spaced(tx, 146 * S, 'DATA & ANALYTICS', font(19 * S, True), (222, 193, 130, 255), 3.4 * S)
    x = tx
    pills = []
    face = font(13 * S, True)
    for label in ('CONSULTORIA', 'TECNOLOGIA', 'ENGENHARIA'):
        wide = sum(d.textlength(c, font=face) + 1.6 * S for c in label)
        o.rounded_rectangle((x, 176 * S, x + wide + 28 * S, 202 * S), radius=13 * S,
                            fill=(255, 255, 255, 16), outline=(255, 255, 255, 70), width=S)
        pills.append((x + 14 * S, label))
        x += wide + 28 * S + 10 * S
    canvas.alpha_composite(overlay)
    for px_, label in pills:
        spaced(px_, 181 * S, label, face, (205, 219, 233, 255), 1.6 * S)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)
