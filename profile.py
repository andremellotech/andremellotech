#!/usr/bin/env python3
"""Perfil mínimo — mesmos renderizadores, dados e URLs, em cinco arquivos.

Instalar: pip install 'pillow>=11,<13' 'requests>=2.32.3,<3' 'beautifulsoup4>=4.12.3,<5'
Executar: python profile.py init; python profile.py test
Prévia local com dados salvos: python profile.py render; python profile.py prepare
Atualizar dados: calendar, repositories, history (nessa ordem), render, prepare, changes.
O workflow publica Pages antes de save. Saídas locais ficam em work/profile/.
init é idempotente; init --reset reinicia uma execução local explicitamente.
notify-template exporta o exemplo original para avisos após pushes em outros repos.

SOURCE_FILES contém código Python e testes legíveis, sem reescrever os módulos.
Somente quatro imagens de entrada usam base64. profile-state.json guarda os três
snapshots completos, inclusive o histórico e seus caches anuais de contribuições.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys

DATASETS = ('contributions', 'contributions-history', 'github-content')
README_FILES = ('README.md', 'README.en-US.md')
ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'
ROOT = Path(__file__).resolve().parent

SOURCE_FILES = {

    # ===== scripts/activity_panel.py =====
    'scripts/activity_panel.py': '''"""Draw real contribution counts and their calendar as one profile panel."""
from pathlib import Path
from datetime import date,timedelta
import json
from PIL import Image,ImageDraw
from fetch_contributions import derive_stats
from themes import THEMES, TRANSPARENT
from branding import section_heading
from profile_i18n import DEFAULT, tr, localized

def contribution_summary(content,calendar):
    days=calendar['days']
    stats=derive_stats(days,date.fromisoformat(calendar['as_of']))
    return dict(stats,repositories=content['user']['public_repos'],
                active_days=sum(d['count']>0 for d in days),as_of=calendar['as_of'])

def week_grid(days):
    ordered=sorted(days,key=lambda d:d['date'])
    first=date.fromisoformat(ordered[0]['date'])
    sunday=first-timedelta(days=(first.weekday()+1)%7)
    return [dict(d,column=(date.fromisoformat(d['date'])-sunday).days//7,
                 row=(date.fromisoformat(d['date']).weekday()+1)%7) for d in ordered]

def render_activity(root,font,palette=None,locale=DEFAULT):
    palette=palette or THEMES['dark']
    colors=palette['calendar']
    white,muted,accent=palette['text'],palette['muted'],palette['accent']
    content=json.loads((root/'data/github-content.json').read_text(encoding='utf-8'))
    calendar=json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    summary=contribution_summary(content,calendar)
    cells=week_grid(calendar['days'])
    im=Image.new('RGBA',(1200,316),TRANSPARENT);d=ImageDraw.Draw(im)
    def text(x,y,value,size=18,color=None,bold=False):d.text((x,y),str(value),font=font(size,bold),fill=color or white)
    section_heading(d,palette,font,tr(locale,'Atividade e contribuições'),12)
    d.rounded_rectangle((12,60,1188,304),radius=12,fill=palette['matte'],outline=palette['line'])
    columns=max(c['column'] for c in cells)+1;step=19;size=16
    x0=(1200-(columns*step-3))//2;y0=115
    months=(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'] if locale==DEFAULT
            else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    prev=None;starts=[]
    for c in cells:
        day=date.fromisoformat(c['date']);key=day.strftime('%Y-%m')
        if key!=prev:
            label=months[day.month-1]
            starts.append((x0+c['column']*step,label));prev=key
        x=x0+c['column']*step;y=y0+c['row']*step
        d.rounded_rectangle((x,y,x+size-1,y+size-1),radius=3,fill=colors[c['level']])
    for row,label in [(1,'Seg'),(3,'Qua'),(5,'Sex')]:text(x0-42,y0+row*step,tr(locale,label),12,muted)
    for index,(x,label) in enumerate(starts):
        if index+1<len(starts) and starts[index+1][0]-x<35:continue
        text(x,83,label,13,muted)
    text(929,275,tr(locale,'Menos'),12,muted)
    for i,color in enumerate(colors):d.rounded_rectangle((976+i*20,277,991+i*20,292),radius=3,fill=color)
    text(1085,275,tr(locale,'Mais'),12,muted)
    im.save(root/'assets'/(localized('activity',locale)+'-'+palette['name']+'.png'))
    return summary
''',

    # ===== scripts/badges.py =====
    'scripts/badges.py': '''"""Two-tone, shields-style badges drawn locally (no external badge service)."""
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
''',

    # ===== scripts/branding.py =====
    'scripts/branding.py': '''"""A restrained AM signature and a single navy visual language."""
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
''',

    # ===== scripts/contribution_city.py =====
    'scripts/contribution_city.py': '''"""Render a full year of real GitHub activity as a locally hosted isometric city."""
from datetime import date, timedelta
import json
from PIL import Image, ImageDraw, ImageColor, ImageChops, GifImagePlugin
from branding import TYPE, section_heading
from themes import TRANSPARENT
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 918
FRAME_COUNT = 31
FRAME_DURATION = 100
CYCLE_DURATION = 10_000
PALETTE_COLORS = 128


def build_city_model(calendar):
    try:
        end = date.fromisoformat(calendar['as_of'])
        source = calendar['days']
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('The contribution city requires a dated calendar') from error
    if not isinstance(source, list):
        raise ValueError('The contribution city requires daily records')
    try:
        anniversary = end.replace(year=end.year-1)
    except ValueError:
        anniversary = end.replace(year=end.year-1, day=28)
    start = anniversary + timedelta(days=1)
    selected = {}
    levels = {}
    for item in source:
        try:
            day = date.fromisoformat(item['date'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid contribution date') from error
        if not start <= day <= end:
            continue
        count = item.get('count')
        if day in selected or type(count) is not int or count < 0:
            raise ValueError('Duplicate or invalid contribution day')
        level=item.get('level')
        if type(level) is not int or not 0<=level<=4 or (count==0)!=(level==0):
            raise ValueError('Invalid GitHub contribution color level')
        selected[day] = count
        levels[day] = level
    expected = [start+timedelta(days=i) for i in range((end-start).days+1)]
    if set(selected) != set(expected):
        raise ValueError('The contribution city requires a complete year of daily data')
    peak = max(selected.values())
    sunday = start-timedelta(days=(start.weekday()+1) % 7)
    days = [dict(date=day.isoformat(), count=selected[day], level=levels[day], week=(day-sunday).days//7,
                 row=(day.weekday()+1) % 7, height=110*selected[day]/(peak or 1)) for day in expected]
    return dict(start=start.isoformat(), end=end.isoformat(), days=days,
                total=sum(selected.values()), active_days=sum(v > 0 for v in selected.values()), peak=peak)


def _span(model, locale):
    months = (['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'] if locale == DEFAULT
              else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    first, last = date.fromisoformat(model['start']), date.fromisoformat(model['end'])
    def label(day):
        if locale == DEFAULT:
            return f'{day.day} {months[day.month-1]} {day.year}'
        return f'{months[day.month-1]} {day.day}, {day.year}'
    return label(first)+' — '+label(last)


def _shade(color, factor):
    return tuple(max(0, min(255, round(v*factor))) for v in ImageColor.getrgb(color))


def growth_height(height, progress):
    """The reference's three-second rise, with no overshoot or invented days."""
    if height<=0:
        return 0
    progress=max(0,min(1,progress))
    initial=min(2.6,height)
    return initial+(height-initial)*progress


def _city_geometry(model):
    """A fixed floor and fixed camera throughout the construction animation."""
    cells=[]
    for item in model['days']:
        x=(item['week']-item['row'])*12
        y=(item['week']+item['row'])*7.2
        points=[(x,y),(x+11.5,y+6.9),(x,y+13.8),(x-11.5,y+6.9)]
        cells.append(dict(item,x=x,y=y,points=points,depth=y+6.9))
    return sorted(cells,key=lambda c:(c['depth'],c['week']))


def _city_bounds(model):
    points=[(x,y-h) for cell in _city_geometry(model)
            for x,y in cell['points'] for h in [0,cell['height']]]
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)


def _city_scene(root, font, palette, model, locale, progress=1, foundation=None):
    scale=3
    width,height=1112,540
    image=foundation.copy() if foundation is not None else Image.new('RGBA',(width*scale,height*scale),TRANSPARENT)
    draw=ImageDraw.Draw(image)
    def text(x,y,value,size=18,bold=False,color=None,mono=False):
        draw.text((round(x*scale),round(y*scale)),str(value),
                  font=font(size*scale,bold,mono),fill=color or palette['muted'])
    if foundation is None:
        text(34,40,tr(locale,'CIDADE DE CONTRIBUIÇÕES'),14,True,palette['accent'],mono=True)
        text(34,72,model['total'],TYPE['name'],True,palette['text'])
        text(34,126,tr(locale,'contribuições nos'))
        text(34,153,tr(locale,'últimos 12 meses'))
        text(34,206,str(model['active_days'])+' '+tr(locale,'dias ativos'),TYPE['meta'],True)
        text(34,237,tr(locale,'Pico diário')+': '+str(model['peak']),TYPE['meta'])
        text(34,472,'@'+profile_username(root),16,mono=True)
        text(34,505,_span(model,locale),16)

    cells=_city_geometry(model)
    left,top,right,bottom=_city_bounds(model)
    box=(298,26,1072,498)
    zoom=min((box[2]-box[0])/(right-left),(box[3]-box[1])/(bottom-top or 1))
    ox=(box[0]+box[2]-(left+right)*zoom)/2
    oy=(box[1]+box[3]-(top+bottom)*zoom)/2
    def project(x,y):
        return round((ox+x*zoom)*scale),round((oy+y*zoom)*scale)
    def polygon(points,fill,outline=None):
        draw.polygon([project(x,y) for x,y in points],fill=fill,outline=outline,width=scale)
    ground_mask=Image.new('L',image.size)
    ground_draw=ImageDraw.Draw(ground_mask)
    for cell in cells:
        if foundation is None:
            polygon(cell['points'],palette['calendar'][0],palette['line'])
        ground_draw.polygon([project(x,y) for x,y in cell['points']],fill=255)
    if progress is None:
        return image
    shadow=Image.new('RGBA',image.size,TRANSPARENT)
    sd=ImageDraw.Draw(shadow)
    for cell in cells:
        h=growth_height(cell['height'],progress)
        if h>0:
            points=cell['points'];reach=h*.18
            sd.polygon([project(x,y) for x,y in [points[3],points[1],
                       (points[1][0]+reach,points[1][1]+10),
                       (points[3][0]+reach,points[3][1]+10)]],
                       fill=(22,55,35,20) if palette['name']=='light' else (0,0,0,36))
    shadow.putalpha(ImageChops.multiply(shadow.getchannel('A'),ground_mask))
    image.alpha_composite(shadow)
    draw=ImageDraw.Draw(image)
    for cell in cells:
        h=growth_height(cell['height'],progress)
        if h==0:
            continue
        points=cell['points']
        roof=[(x,y-h) for x,y in points]
        color=palette['calendar'][cell['level']]
        polygon([points[3],points[2],roof[2],roof[3]],_shade(color,.68))
        polygon([points[2],points[1],roof[1],roof[2]],_shade(color,.86))
        polygon(roof,color)
    return image.resize((width,height),Image.Resampling.LANCZOS)


def profile_username(root):
    content=json.loads((root/'data/github-content.json').read_text(encoding='utf-8'))
    return content['user']['login']


def _color_mask(rgb, color):
    red,green,blue=ImageChops.difference(rgb,Image.new('RGB',rgb.size,color)).split()
    return ImageChops.lighter(ImageChops.lighter(red,green),blue).point(lambda value:255 if value==0 else 0)


def _write_animation(path, frames, matte, palette_source, exact_colors):
    """Repeat a three-second construction and a seven-second completed city."""
    background=Image.new('RGBA',palette_source.size,matte)
    background.alpha_composite(palette_source)
    shared=background.convert('RGB').quantize(colors=PALETTE_COLORS,dither=Image.Dither.NONE)
    colors=shared.getpalette()
    pinned={}
    for color in [matte,*exact_colors]:
        rgb=ImageColor.getrgb(color)
        if rgb in pinned:
            continue
        index=min((i for i in range(PALETTE_COLORS) if i not in pinned.values()),
                  key=lambda i:sum((colors[3*i+j]-rgb[j])**2 for j in range(3)))
        colors[3*index:3*index+3]=rgb
        pinned[rgb]=index
    shared.putpalette(colors)
    previous=None
    surface=ImageColor.getrgb(matte)
    region=(340,354,1176,906)
    with path.open('wb') as output:
        for frame_index,frame in enumerate(frames):
            duration=(CYCLE_DURATION-(FRAME_COUNT-1)*FRAME_DURATION
                      if frame_index==FRAME_COUNT-1 else FRAME_DURATION)
            background=Image.new('RGBA',frame.size,matte)
            background.alpha_composite(frame)
            rgb=background.convert('RGB')
            indexed=rgb.quantize(palette=shared,dither=Image.Dither.NONE)
            indexed.paste(pinned[surface],mask=_color_mask(rgb,surface))
            # Exact flat roof colors survive Pillow's approximate palette lookup.
            city_rgb=rgb.crop(region)
            for color,index in pinned.items():
                if color!=surface:
                    indexed.paste(index,region[:2],_color_mask(city_rgb,color))
            indexed.paste(255,mask=frame.getchannel('A').point(lambda a:255 if a==0 else 0))
            if previous is None:
                chunks,_=GifImagePlugin.getheader(indexed,info={'loop':0,'transparency':255,'background':255})
                output.writelines(chunks)
                output.writelines(GifImagePlugin.getdata(indexed,duration=duration,disposal=1,transparency=255))
            else:
                area=ImageChops.difference(indexed,previous).getbbox()
                if area:
                    output.writelines(GifImagePlugin.getdata(indexed.crop(area),offset=area[:2],
                                                            duration=duration,disposal=1,transparency=255))
                else:
                    output.writelines(GifImagePlugin.getdata(indexed.crop((40,80,41,81)),offset=(40,80),
                                                            duration=duration,disposal=1,transparency=255))
            previous=indexed
        output.write(b';')


def render_city(root, font, palette, locale=DEFAULT):
    calendar=json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    model=build_city_model(calendar)
    base=Image.new('RGBA',(1200,HEIGHT),TRANSPARENT)
    draw=ImageDraw.Draw(base)
    section_heading(draw,palette,font,tr(locale,'Atividade e contribuições'),12)
    draw.rounded_rectangle((24,76,1176,906),radius=12,fill=palette['matte'],outline=palette['line'])
    with Image.open(root/'assets'/f'{localized("streak",locale)}-{palette["name"]}.png') as streak:
        if streak.size!=(1200,272):
            raise ValueError('The activity card requires a complete contribution summary')
        base.alpha_composite(streak.convert('RGBA'),(0,76))
    draw.line((44,340,1156,340),fill=palette['line'])
    foundation=_city_scene(root,font,palette,model,locale,progress=None)
    final=base.copy()
    final.alpha_composite(_city_scene(root,font,palette,model,locale,progress=1,foundation=foundation),(44,354))
    stem=root/'assets'/f'{localized("activity",locale)}-{palette["name"]}'
    # A static preview should show the complete data, not the start of the reveal.
    final.save(stem.with_suffix('.png'))
    def frames():
        for index in range(FRAME_COUNT):
            if index==FRAME_COUNT-1:
                yield final
            else:
                frame=base.copy()
                frame.alpha_composite(_city_scene(root,font,palette,model,locale,
                                      progress=index/(FRAME_COUNT-1),foundation=foundation),(44,354))
                yield frame
    _write_animation(stem.with_suffix('.gif'),frames(),palette['matte'],final,palette['calendar'])
    return model
''',

    # ===== scripts/design.py =====
    'scripts/design.py': '''"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import ImageFont
import os
from themes import THEMES
from status_panel import render_status
from badges import render_badge
from intro_panel import render_intro
from technology_panel import render_technology
from contribution_city import render_city
import json
from github_layout import build_github_layout
from language_buttons import render_language_buttons
from profile_i18n import DEFAULT, LOCALES, localized

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'


def font(size, bold=False, mono=False):
    base = Path('C:/Windows/Fonts') if os.name == 'nt' else Path('/usr/share/fonts/truetype/dejavu')
    if os.name == 'nt':
        name = 'consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf'
    else:
        name = 'DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(str(base / name), size)


def render_theme(name, palette, locale=DEFAULT):
    render_intro(font, palette, locale=locale).save(A / f'{localized("intro-background",locale)}-{name}.png')
    render_technology(ROOT, font, palette, locale)
    render_status(ROOT, font, palette, locale)
    render_city(ROOT, font, palette, locale)


def render_badges():
    """Compact contact badges drawn locally and hosted with the profile."""
    content = json.loads((ROOT / 'data/github-content.json').read_text(encoding='utf-8'))
    navy = '#17324d'
    for stem, label, value, left, right, icon in [
            ('badge-linkedin', '', 'André Mello', '#0a66c2', navy, 'linkedin'),
            ('badge-github', '', '@' + content['user']['login'], '#24292f', navy, 'github'),
            ('badge-email', '', 'andremello@outlook.com', '#0078d4', navy, 'email')]:
        render_badge(A / f'{stem}.png', font, label, value, left, right, icon, A)


if __name__ == '__main__':
    A.mkdir(exist_ok=True)
    for locale in LOCALES:
        for name, palette in THEMES.items():
            render_theme(name, palette, locale)
    render_badges()
    render_language_buttons(A, font)
    for locale in LOCALES:
        build_github_layout(ROOT, font, locale)
''',

    # ===== scripts/fetch_contributions.py =====
    'scripts/fetch_contributions.py': '''"""Fetch public contributions. Never overwrite a valid snapshot on failure."""
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from github_http import github_session

ROOT = Path(__file__).resolve().parents[1]

def parse_contributions(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    tips = {t.get('for'): t.get_text(' ', strip=True) for t in soup.select('tool-tip[for]')}
    days, seen = [], set()
    for cell in soup.select('[data-date][data-level]'):
        day = cell['data-date']
        date.fromisoformat(day)
        if day in seen: raise ValueError('Duplicate contribution date')
        seen.add(day)
        level = int(cell['data-level'])
        if not 0 <= level <= 4: raise ValueError('Invalid contribution level')
        raw = cell.get('data-count')
        if raw is None:
            tip = tips.get(cell.get('id'), '')
            if re.match(r'No contributions\\b', tip): raw = '0'
            else:
                match = re.match(r'([\\d,]+) contributions?\\b', tip)
                if not match: raise ValueError(f'Missing count for {day}')
                raw = match.group(1).replace(',', '')
        count = int(raw)
        if count < 0: raise ValueError('Negative contribution count')
        days.append({'date':day,'count':count,'level':level})
    if not days: raise ValueError('No contribution days found')
    return sorted(days, key=lambda d: d['date'])

def derive_stats(days: list[dict], today: date) -> dict:
    days = sorted((d for d in days if date.fromisoformat(d['date']) <= today), key=lambda d:d['date'])
    if not days: raise ValueError('No past contribution days')
    counts = {date.fromisoformat(d['date']):d['count'] for d in days}
    current, cursor = 0, today
    if counts.get(cursor, 0) == 0: cursor -= timedelta(days=1)
    current_end = cursor
    while counts.get(cursor,0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    current_range = ({'start':(cursor+timedelta(days=1)).isoformat(), 'end':current_end.isoformat()}
                     if current else None)
    run = longest = 0
    longest_range = None
    previous = None
    monthly = defaultdict(int)
    for d in days:
        day = date.fromisoformat(d['date'])
        if previous is not None and day != previous + timedelta(days=1): run = 0
        run = run + 1 if d['count'] > 0 else 0
        if run > longest:
            longest = run
            longest_range = {'start':(day-timedelta(days=run-1)).isoformat(), 'end':day.isoformat()}
        monthly[d['date'][:7]] += d['count']
        previous = day
    best = max(days, key=lambda d:d['count'])
    return {'total':sum(d['count'] for d in days), 'current_streak':current,
            'longest_streak':longest,'best_day':{'date':best['date'],'count':best['count']},
            'monthly_totals':dict(monthly),
            'first_contribution':next((d['date'] for d in days if d['count'] > 0), None),
            'current_streak_range':current_range, 'longest_streak_range':longest_range}

def validate_calendar(days: list[dict], today: date) -> None:
    dates = sorted(date.fromisoformat(d['date']) for d in days)
    if len(dates) < 350: raise ValueError('Incomplete calendar; keeping previous snapshot')
    if dates[-1] < today - timedelta(days=1): raise ValueError('Stale calendar')
    if any(b != a + timedelta(days=1) for a,b in zip(dates,dates[1:])):
        raise ValueError('Calendar has missing or duplicate days')

def main():
    profile = json.loads((ROOT / 'profile.json').read_text(encoding='utf-8-sig'))
    username = profile['username']
    if not re.fullmatch(r'[A-Za-z0-9-]+', username): raise ValueError('Invalid username')
    with github_session() as session:
        response = session.get(f'https://github.com/users/{username}/contributions', timeout=30)
    response.raise_for_status()
    today = datetime.now(timezone.utc).date()
    days = [d for d in parse_contributions(response.text) if date.fromisoformat(d['date']) <= today]
    validate_calendar(days,today)
    data = {'username':username,'as_of':today.isoformat(),'days':days,'stats':derive_stats(days,today)}
    target = ROOT / 'data/contributions.json'
    target.parent.mkdir(exist_ok=True)
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\\n',encoding='utf-8')
    os.replace(temp,target)
    print(f"Fetched {len(days)} days: {data['stats']['total']} contributions")

if __name__ == '__main__': main()
''',

    # ===== scripts/fetch_github_content.py =====
    'scripts/fetch_github_content.py': '''"""Collect public GitHub data; optional Actions token avoids anonymous limits."""
import json
import os
import re
from urllib.parse import urlencode
import requests
from datetime import datetime, timezone
from pathlib import Path
from github_http import github_session
ROOT=Path(__file__).resolve().parents[1]

def normalize_content(user:dict,repos:list,languages:dict)->dict:
    if not user.get('login') or not user.get('created_at'):
        raise ValueError('Incomplete GitHub user response')
    fields=['login','name','bio','public_repos','followers','following','created_at','html_url']
    public=[]
    for repo in repos:
        if repo.get('private'): continue
        if not repo.get('name') or not repo.get('html_url','').startswith('https://github.com/'):
            raise ValueError('Invalid repository response')
        entry={k:repo.get(k) for k in ['name','description','html_url','language','fork','stargazers_count','forks_count','pushed_at']}
        # Generated artwork changes this timestamp; it is not a new project update.
        if repo['name'].lower()==user['login'].lower():entry['pushed_at']=None
        public.append(entry)
    public.sort(key=lambda r:(r.get('pushed_at') or '',r['name']),reverse=True)
    totals={}
    for repo in public[:6]:
        for lang,count in languages.get(repo['name'],{}).items():
            if not isinstance(count,int) or count<0: raise ValueError('Invalid language byte count')
            totals[lang]=totals.get(lang,0)+count
    return {'user':{key:user.get(key) for key in fields},'repositories':public,
            'languages':dict(sorted(totals.items(),key=lambda item:item[1],reverse=True)),
            'languages_scope':'Até seis repositórios públicos atualizados mais recentemente'}

def collect_stats(get,username,repos):
    """Public authored totals; unavailable/incomplete searches stay unavailable."""
    stats={'stars':sum(r.get('stargazers_count') or 0 for r in repos)}
    for key,kind,query in [('pull_requests','issues',f'author:{username} type:pr is:public'),
                           ('issues','issues',f'author:{username} type:issue is:public'),
                           ('commits','commits',f'author:{username} is:public')]:
        try:
            result=get(f'https://api.github.com/search/{kind}?'+urlencode({'q':query,'per_page':1})).json()
            total=result['total_count']
            stats[key]=total if type(total) is int and total>=0 and not result.get('incomplete_results',False) else None
        except (requests.RequestException,ValueError,KeyError,TypeError) as error:
            print(f'Aviso: contagem {key} indisponível ({type(error).__name__})')
            stats[key]=None
    return stats

def main():
    username=json.loads((ROOT/'profile.json').read_text(encoding='utf-8-sig'))['username']
    if not re.fullmatch(r'[A-Za-z0-9-]+',username): raise ValueError('Invalid username')
    session=github_session()
    session.headers.update({'Accept':'application/vnd.github+json','User-Agent':'andremellotech-profile','X-GitHub-Api-Version':'2022-11-28'})
    token=os.getenv('GITHUB_TOKEN')
    if token: session.headers['Authorization']=f'Bearer {token}'
    def get(url):
        response=session.get(url,timeout=30)
        response.raise_for_status()
        return response
    user=get(f'https://api.github.com/users/{username}').json()
    url=f'https://api.github.com/users/{username}/repos?per_page=100&sort=pushed'
    repos=[]
    while url:
        response=get(url)
        batch=response.json()
        if not isinstance(batch,list): raise ValueError('Invalid repository list')
        repos.extend(batch)
        url=response.links.get('next',{}).get('url')
    langs={}
    for repo in [r for r in repos if r.get('name','').lower()!=username.lower()][:6]:
        langs[repo['name']]=get(f'https://api.github.com/repos/{username}/{repo["name"]}/languages').json()
    data=normalize_content(user,repos,langs)
    data['stats']=collect_stats(get,username,data['repositories'])
    data['as_of']=datetime.now(timezone.utc).date().isoformat()
    temp=ROOT/'data/github-content.tmp'
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
    os.replace(temp,ROOT/'data/github-content.json')
    print(f'Fetched {len(data["repositories"])} public repositories; {len(data["languages"])} detected languages')

if __name__=='__main__': main()
''',

    # ===== scripts/fetch_streak_history.py =====
    'scripts/fetch_streak_history.py': '''"""Collect complete public history directly from GitHub, with daily historical caching."""
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
from fetch_contributions import parse_contributions, derive_stats
from github_http import github_session

ROOT = Path(__file__).resolve().parents[1]


def collect_history(get_days, created, today, cache):
    years, all_days = {}, []
    for year in range(created.year, today.year + 1):
        start, end = max(created, date(year, 1, 1)), min(today, date(year, 12, 31))
        cached = cache.get('years', {}).get(str(year), {})
        days = (cached['days'] if year < today.year and cached.get('checked_on') == today.isoformat()
                else get_days(year))
        days = sorted((d for d in days if start.isoformat() <= d['date'] <= end.isoformat()), key=lambda d:d['date'])
        actual = [date.fromisoformat(d['date']) for d in days]
        if (len(set(actual)) != len(actual) or len(actual) != (end-start).days+1
                or not actual or actual[0] != start or actual[-1] != end
                or any(d['count'] < 0 for d in days)):
            raise ValueError(f'Incomplete or invalid contribution history for {year}')
        years[str(year)] = {'checked_on':today.isoformat(), 'days':days}
        all_days.extend(days)
    return {'as_of':today.isoformat(), 'days':all_days, 'years':years, 'stats':derive_stats(all_days, today)}


def main():
    profile = json.loads((ROOT/'data/github-content.json').read_text(encoding='utf-8'))['user']
    username = profile['login']
    created = date.fromisoformat(profile['created_at'][:10])
    today = datetime.now(timezone.utc).date()
    target = ROOT/'data/contributions-history.json'
    cache = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    if cache.get('username') != username:
        cache = {}
    with github_session() as session:
        def get_days(year):
            response = session.get(f'https://github.com/users/{username}/contributions',
                                   params={'from':f'{year}-01-01','to':f'{year}-12-31'}, timeout=30)
            response.raise_for_status()
            return parse_contributions(response.text)
        result = collect_history(get_days, created, today, cache)
    result['username'] = username
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\\n', encoding='utf-8')
    os.replace(temp, target)
    print(f"Public history collected: {result['stats']['total']} contributions since {created.year}")


if __name__ == '__main__':
    main()
''',

    # ===== scripts/github_http.py =====
    'scripts/github_http.py': '''"""Retry temporary read failures while keeping permanent errors visible."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def github_session(backoff_factor=2):
    retry = Retry(total=3, connect=3, read=3, status=3,
                  backoff_factor=backoff_factor,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(['GET']),
                  respect_retry_after_header=True)
    session = requests.Session()
    session.headers.update({'User-Agent': 'andremellotech-profile',
                            'Cache-Control': 'no-cache'})
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    return session
''',

    # ===== scripts/github_layout.py =====
    'scripts/github_layout.py': '''"""Compose theme-aware PNGs and a small, transparent animated portrait block."""
from PIL import Image, ImageColor, ImageSequence, GifImagePlugin
import hashlib, json
from html import escape
from themes import THEMES, TRANSPARENT
from intro_panel import PORTRAIT_AT, PORTRAIT_SIZE
from profile_i18n import (DEFAULT, tr, localized, readme_name, preview_name, preview_image,
                          INTRO_ALT, TECHNOLOGY_ALT, STATUS_ALT, ACTIVITY_ALT)

ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'


def image_url(root, name):
    version = hashlib.sha256((root / 'assets' / name).read_bytes()).hexdigest()[:12]
    return ASSET_HOST + name + '?v=' + version


def transparent_portrait(source, color):
    original = (source if isinstance(source, Image.Image) else Image.open(source)).convert('RGB')
    # Recover glyph opacity from the original uniform terminal background.
    # Recoloring the glyphs avoids dark halos on light pages.
    alpha = original.convert('L').point(lambda value: max(0, min(255, round((value - 19) * 1.9))))
    face_size = (round(PORTRAIT_SIZE[0]*.8), round(PORTRAIT_SIZE[1]*.813))
    face = alpha.crop((55, 72, 375, 480)).resize(face_size, Image.Resampling.LANCZOS)
    alpha = Image.new('L', PORTRAIT_SIZE)
    alpha.paste(face, (round(PORTRAIT_SIZE[0]*.1), round(PORTRAIT_SIZE[1]*.093)))
    portrait = Image.new('RGBA', PORTRAIT_SIZE, ImageColor.getrgb(color) + (0,))
    portrait.putalpha(alpha)
    return portrait


def animated_intro(assets, theme, palette, background, locale=DEFAULT):
    """Animate the portrait inside one compact, theme-aware introduction."""
    frames, durations = [], []
    shared_palette = None
    with Image.open(assets / 'andre-ascii.gif') as original:
        for source in ImageSequence.Iterator(original):
            frame = background.copy()
            frame.alpha_composite(transparent_portrait(source, palette['portrait']), PORTRAIT_AT)
            if shared_palette is None:
                frame.save(assets / f'{localized("profile-intro",locale)}-{theme}.png')
            # GIF has binary transparency. Matte only the antialiased glyph edges,
            # leaving all empty space transparent over GitHub's own background.
            matte = Image.new('RGBA', frame.size, palette['matte'])
            matte.alpha_composite(frame)
            rgb = matte.convert('RGB')
            if shared_palette is None:
                shared_palette = rgb.quantize(colors=32, dither=Image.Dither.NONE)
            indexed = rgb.quantize(palette=shared_palette, dither=Image.Dither.NONE)
            indexed.paste(255, mask=frame.getchannel('A').point(lambda alpha: 255 if alpha == 0 else 0))
            indexed.info['transparency'] = 255
            duration = source.info.get('duration', 100)
            if frames and indexed.tobytes() == frames[-1].tobytes():
                durations[-1] += duration
            else:
                frames.append(indexed)
                durations.append(duration)
    # Write the fixed text once, then send only the small portrait rectangle.
    # A transparent clearing frame removes the initial portrait without erasing
    # the text. Each later portrait clears its own rectangle before the next one.
    with (assets / f'{localized("profile-intro",locale)}-{theme}.gif').open('wb') as output:
        header, _ = GifImagePlugin.getheader(frames[0], info={
            'loop': 0, 'transparency': 255, 'background': 255, 'optimize': False})
        output.writelines(header)
        output.writelines(GifImagePlugin.getdata(frames[0], duration=durations[0],
                                                disposal=1, transparency=255))
        clear = Image.new('P', PORTRAIT_SIZE, 255)
        clear.putpalette(frames[0].getpalette())
        output.writelines(GifImagePlugin.getdata(clear, offset=PORTRAIT_AT, duration=10,
                                                disposal=2, transparency=255))
        for frame, duration in zip(frames[1:], durations[1:]):
            portrait = frame.crop(PORTRAIT_AT + (PORTRAIT_AT[0] + PORTRAIT_SIZE[0], PORTRAIT_AT[1] + PORTRAIT_SIZE[1]))
            output.writelines(GifImagePlugin.getdata(portrait, offset=PORTRAIT_AT,
                                                    duration=duration, disposal=2, transparency=255))
        output.write(b';')


def themed_picture(root, stem, alt, animated=False, width='100%'):
    sources = []
    extension = 'gif' if animated else 'png'
    for theme in ['dark', 'light']:
        sources.append(f'<source media="(prefers-color-scheme: {theme})" srcset="'
                       + image_url(root, f'{stem}-{theme}.{extension}') + '" />')
    return ('<picture>' + ''.join(sources) + '<img src="'
            + image_url(root, f'{stem}-light.{extension}')
            + '" width="' + width + '" align="top" alt="' + escape(alt, quote=True) + '" /></picture>')


def badge_img(root, stem, alt):
    return '<img src="' + image_url(root, stem + '.png') + '" height="22" alt="' + alt + '" />'


def build_github_layout(root, font, locale=DEFAULT):
    assets = root / 'assets'
    for theme, palette in THEMES.items():
        panels = []
        for name in ['intro', 'status', 'activity', 'stack']:
            if name == 'intro':
                panel = Image.open(assets / f'{localized("intro-background",locale)}-{theme}.png').convert('RGBA')
                panel.alpha_composite(transparent_portrait(assets / 'andre-ascii.png', palette['portrait']), PORTRAIT_AT)
            else:
                panel = Image.open(assets / f'{localized(name,locale)}-{theme}.png').convert('RGBA')
            panels.append(panel)
        height = sum(panel.height for panel in panels) + 28 * len(panels)
        main = Image.new('RGBA', (1200, height), TRANSPARENT)
        y = 0
        for panel in panels:
            main.alpha_composite(panel, (0, y))
            y += panel.height + 28
        main.save(assets / f'{localized("profile-card",locale)}-{theme}.png')
        preview = Image.new('RGBA', main.size, palette['matte'])
        preview.alpha_composite(main)
        preview.convert('RGB').save(root / preview_image(theme, locale))
        animated_intro(assets, theme, palette,
                       Image.open(assets / f'{localized("intro-background",locale)}-{theme}.png').convert('RGBA'), locale)

    alt = STATUS_ALT[locale]
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    alt += ' ' + tr(locale, 'Linguagens por bytes em até seis repositórios públicos recentes: ') + ', '.join(content.get('languages', {})) + '.'
    username = content['user']['login']
    language_links = ('<p align="right"><a href="https://github.com/' + username + '" title="Português (Brasil)">'
             '<img src="' + image_url(root, 'language-pt-BR.png') + '" height="24" alt="Português (Brasil)" /></a> '
             '<a href="https://github.com/' + username + '/' + username + '/blob/main/README.en-US.md" title="English (US)">'
             '<img src="' + image_url(root, 'language-en-US.png') + '" height="24" alt="English (US)" /></a></p>')
    intro = '<p align="center">' + themed_picture(root, localized('profile-intro',locale), INTRO_ALT[locale], animated=True) + '</p>'
    links = ('<p align="center"><a href="https://www.linkedin.com/in/aamello/">'
             + badge_img(root, 'badge-linkedin', tr(locale, 'LinkedIn — André Mello')) + '</a> '
             '<a href="https://github.com/' + username + '?tab=repositories">'
             + badge_img(root, 'badge-github', tr(locale, 'GitHub — explorar meus repositórios')) + '</a> '
             '<a href="mailto:andremello@outlook.com">'
             + badge_img(root, 'badge-email', tr(locale, 'E-mail — andremello@outlook.com')) + '</a></p>')
    status = '<p align="center">' + themed_picture(root, localized('status',locale), alt) + '</p>'
    activity = '<p align="center">' + themed_picture(root, localized('activity',locale),
             ACTIVITY_ALT[locale], animated=True) + '</p>'
    tools = '<p align="center">' + themed_picture(root, localized('stack',locale), TECHNOLOGY_ALT[locale]) + '</p>'
    top = '\\n\\n'.join([language_links, intro, links, status, activity, tools])
    readme = preview_body = top
    (root / readme_name(locale)).write_text(readme, encoding='utf-8')
    preview_html = ('<!doctype html><html lang="' + locale + '"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>André Mello — ' + ('prévia adaptativa' if locale==DEFAULT else 'adaptive preview') + '</title><style>'
                    ':root{color-scheme:light dark}body{margin:0;background:light-dark(#f6f8fa,#010409);font:14px/1.5 system-ui}'
                    'main{max-width:900px;background:light-dark(#fff,#0d1117);border:1px solid light-dark(#d1d9e0,#3d444d);'
                    'border-radius:6px;padding:24px;margin:24px auto}p{margin:0 0 16px}img{max-width:100%;height:auto;vertical-align:middle}'
                    'img[height="22"]{height:22px;width:auto}'
                    'img[height="24"]{height:24px;width:auto}'
                    '@media(max-width:600px){main{padding:12px;margin:8px}}</style><main>'
                    + preview_body.replace(ASSET_HOST, './assets/') + '</main></html>')
    (root / preview_name(locale)).write_text(preview_html, encoding='utf-8')
    print('Transparent, animated profile built for light and dark GitHub themes.')
''',

    # ===== scripts/intro_panel.py =====
    'scripts/intro_panel.py': '''"""An editorial introduction with an engineering drawing around the portrait."""
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
    text(MARGIN, 157, 'Dados e automação na prática.', TYPE['hero'], palette['text'], True)
    text(MARGIN, 213, 'Projetos de análise de dados, integrações e engenharia.', TYPE['body'], palette['muted'])
    line([(MARGIN, 270), (740, 270)], palette['line'])

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
    line(panel + [panel[0]], palette['brand_line'])
    line([(878, 90), (878, 38), (906, 10), (996, 10)], palette['brand'], 2)
    line([(1080, 298), (1142, 298), (1170, 270), (1170, 212)], palette['brand'], 2)

    # A small isometric data module anchors the drawing at the left margin.
    line([(833, 246), (857, 232), (881, 246), (857, 260), (833, 246),
          (833, 274), (857, 288), (881, 274), (881, 246)], palette['brand'], 2)
    line([(857, 260), (857, 288)], palette['brand'], 2)
    line([(833, 260), (857, 274), (881, 260)], palette['brand_line'])
    line([(857, 232), (857, 204), (878, 183)], palette['brand_line'])
    for x, y in [(857, 204), (1170, 100)]:
        d.ellipse(((x-3)*s, (y-3)*s, (x+3)*s, (y+3)*s), fill=palette['brand'])
    return image.resize((1200, INTRO_H), Image.Resampling.LANCZOS)
''',

    # ===== scripts/language_buttons.py =====
    'scripts/language_buttons.py': '''"""Small locally drawn language buttons, with no external badge dependency."""
from PIL import Image, ImageDraw
from themes import TRANSPARENT


def render_language_buttons(assets, font):
    for locale, label in [('pt-BR', 'Português'), ('en-US', 'English')]:
        face = font(22, True)
        probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        width = round(probe.textlength(label, font=face)) + 74
        image = Image.new('RGBA', (width, 48), TRANSPARENT)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0,0,width-1,47), radius=10, fill='#17324d', outline='#a6b7c8')
        if locale == 'pt-BR':
            draw.rectangle((12,12,44,35), fill='#18864b')
            draw.polygon([(28,14),(42,24),(28,33),(14,24)], fill='#ffcf40')
            draw.ellipse((22,18,34,30), fill='#2055a2')
            draw.line((23,22,33,26), fill='white', width=2)
        else:
            draw.rectangle((12,12,44,35), fill='white')
            for y in range(12,36,4):
                draw.rectangle((12,y,44,min(y+1,35)), fill='#d64b55')
            draw.rectangle((12,12,27,24), fill='#244b7d')
            for x in [15,20,25]:
                for y in [15,19,23]:
                    draw.point((x,y), fill='white')
        draw.text((56,10), label, font=face, fill='white')
        image.save(assets/f'language-{locale}.png')
''',

    # ===== scripts/prepare_pages.py =====
    'scripts/prepare_pages.py': '''"""Stage only the public profile images and preview for GitHub Pages."""
from pathlib import Path
import shutil
from profile_i18n import DEFAULT, LOCALES, localized, preview_name

ROOT=Path(__file__).resolve().parents[1]
def prepare(root=ROOT):
    dest=root/'work/pages'
    (dest/'assets').mkdir(parents=True,exist_ok=True)
    images = []
    images.extend(f'badge-{stem}.png' for stem in ['linkedin','github','email'])
    images.extend(f'language-{locale}.png' for locale in LOCALES)
    for locale in LOCALES:
        for theme in ['light', 'dark']:
            images.append(f'{localized("profile-card",locale)}-{theme}.png')
            images.extend(f'{localized(stem,locale)}-{theme}.{extension}' for stem, extension in
                          [('profile-intro', 'png'), ('profile-intro', 'gif'), ('status', 'png'),
                           ('activity', 'gif'), ('stack', 'png')])
    for name in images:
        shutil.copy2(root/'assets'/name,dest/'assets'/name)
    shutil.copy2(root/'previa.html',dest/'index.html')
    (dest/'en-US').mkdir(exist_ok=True)
    english = (root/preview_name('en-US')).read_text(encoding='utf-8').replace('./assets/', '../assets/')
    (dest/'en-US/index.html').write_text(english, encoding='utf-8')
    (dest/'.nojekyll').write_text('')
    return dest
if __name__=='__main__':print('Public images staged:',prepare())
''',

    # ===== scripts/professional_panel.py =====
    'scripts/professional_panel.py': '''"""Professional experience and results supplied by André, separate from GitHub data."""
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import MARGIN, TYPE, section_heading, domain_icon, wrapped_text
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 512
RESULTS = [
    ('R$ 660 mi', 'Portfólio de ativos', 'sob governança'),
    ('+25%', 'Eficiência operacional', 'com dados e automação'),
    ('240 h/ano', 'Retrabalho eliminado', 'por meio de automação'),
    ('Até 80', 'Liderança de equipes', 'multifuncionais'),
]
PILLARS = [
    ('Governança e PMO', 'Portfólio, indicadores executivos e acompanhamento físico-financeiro.'),
    ('Engenharia e contratos', 'Ativos físicos, terceiros e contratos com CAPEX de até R$ 125 milhões.'),
    ('Dados e automação', 'Painéis executivos e integração de dados com Power BI, SAP e Power Automate.'),
]
ALT = ('Atuação e resultados informados por André: governança de R$ 660 milhões em ativos físicos; '
       'aumento de 25% na eficiência operacional; eliminação de 240 horas anuais de retrabalho; '
       'liderança de equipes com até 80 profissionais. Governança de portfólio e PMO, engenharia '
       'e contratos com CAPEX de até R$ 125 milhões, análise de dados e automação.')


def render_professional(root, font, palette, locale=DEFAULT):
    image = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    section_heading(draw, palette, font, tr(locale, 'Atuação e resultados'), 12)
    draw.text((MARGIN, 70), tr(locale, 'Engenharia e visão de negócio para transformar informação em ação.'),
              font=font(TYPE['body']), fill=palette['muted'])
    for index, (value, title, detail) in enumerate(RESULTS):
        value, title, detail = (tr(locale, item) for item in (value, title, detail))
        left = MARGIN + index * 294
        draw.rounded_rectangle((left, 112, left + 270, 260), radius=12,
                               fill=palette['surface'], outline=palette['line'])
        draw.line((left + 20, 132, left + 56, 132), fill=palette['brand'], width=3)
        draw.text((left + 20, 143), value, font=font(TYPE['number'], True), fill=palette['text'])
        draw.text((left + 20, 199), title, font=font(TYPE['meta'], True), fill=palette['accent'])
        draw.text((left + 20, 226), detail, font=font(TYPE['meta']), fill=palette['muted'])
    for index, (title, description) in enumerate(PILLARS):
        title, description = tr(locale, title), tr(locale, description)
        left = MARGIN + index * 392
        draw.rounded_rectangle((left, 284, left + 368, 496), radius=12,
                               fill=palette['matte'], outline=palette['line'])
        domain_icon(draw, palette, index, left + 20, 306)
        draw.text((left + 60, 305), title, font=font(TYPE['card'], True), fill=palette['accent'])
        used = wrapped_text(draw, (left + 20, 354), description, font(TYPE['body']),
                            palette['muted'], width=328)
        if used > 116:
            raise ValueError('Professional description exceeds its card: ' + title)
    image.save(root/'assets'/f'{localized("professional", locale)}-{palette["name"]}.png')
''',

    # ===== scripts/profile_i18n.py =====
    'scripts/profile_i18n.py': '''"""Two complete profile editions built from the same data and layout."""
DEFAULT = 'pt-BR'
LOCALES = (DEFAULT, 'en-US')

EN = {
    'CIDADE DE CONTRIBUIÇÕES': 'CONTRIBUTION CITY',
    'contribuições nos': 'contributions in the',
    'últimos 12 meses': 'last 12 months',
    'Últimos 12 meses': 'Last 12 months',
    'contribuições em 12 meses': 'contributions in 12 months',
    'dias ativos': 'active days',
    'Pico diário': 'Daily peak',
    'Cada bloco representa um dia.': 'Each block represents one day.',
    'Altura proporcional às contribuições.': 'Height is proportional to contributions.',
    'Contribuições em 3D': 'Contributions in 3D',
    'DADOS · AUTOMAÇÃO · ENGENHARIA': 'DATA · AUTOMATION · ENGINEERING',
    'Dados e automação na prática.': 'Data and automation in practice.',
    'Projetos de análise de dados, integrações e engenharia.': 'Data analytics, integration and engineering projects.',
    'Tecnologias e ferramentas': 'Technology and tools',
    'Microsoft 365 · produtividade e colaboração': 'Microsoft 365 · productivity and collaboration',
    'Engenharia e geoprocessamento': 'Engineering and geospatial tools',
    'Desenvolvimento e versionamento': 'Development and version control',
    'Sistemas e colaboração': 'Systems and collaboration',
    'Linguagens · conhecimentos': 'Languages · working knowledge',
    'CONSULTORIA · ENGENHARIA · DADOS': 'CONSULTING · ENGINEERING · DATA',
    'Engenharia, dados e governança.': 'Engineering, data and governance.',
    'Da estratégia à execução.': 'From strategy to execution.',
    'Portfólio, PMO e automação com foco em resultados.': 'Portfolio governance, PMO and automation.',
    'Consultor na KPMG Brasil · Mais de 6 anos de experiência': 'Consultant at KPMG Brasil · 6+ years of experience',
    'Engenheiro Civil · Mestre em Administração': 'Civil Engineer · MSc in Administration',
    'Atuação e resultados': 'Experience and results',
    'Engenharia e visão de negócio para transformar informação em ação.': 'Engineering rigor and business insight to turn information into action.',
    'R$ 660 mi': 'BRL 660M',
    'Portfólio de ativos': 'Asset portfolio',
    'sob governança': 'under governance',
    '+25%': '+25%',
    'Eficiência operacional': 'Efficiency gain',
    'com dados e automação': 'data and automation',
    '240 h/ano': '240 h/year',
    'Retrabalho eliminado': 'Rework eliminated',
    'por meio de automação': 'through automation',
    'Até 80': 'Up to 80',
    'Liderança de equipes': 'Team leadership',
    'multifuncionais': 'across functions',
    'Governança e PMO': 'Governance and PMO',
    'Portfólio, indicadores executivos e acompanhamento físico-financeiro.': 'Portfolio oversight, executive KPIs and physical and financial progress.',
    'Engenharia e contratos': 'Engineering contracts',
    'Ativos físicos, terceiros e contratos com CAPEX de até R$ 125 milhões.': 'Physical assets, vendors and contracts with CAPEX up to BRL 125 million.',
    'Dados e automação': 'Data and automation',
    'Painéis executivos e integração de dados com Power BI, SAP e Power Automate.': 'Executive dashboards and data integration with Power BI, SAP and Power Automate.',
    'Tecnologias e formação': 'Technology and education',
    'Dados, sistemas e automação': 'Data, systems and automation',
    'Análise, integração de dados e automação de rotinas.': 'Analytics, data integration and workflow automation.',
    'Sistemas e comunicação': 'Systems and communication',
    'Office 365, apresentações executivas': 'Office 365, executive presentations',
    'e organização de informações.': 'and information management.',
    'Linguagens e versionamento': 'Languages and version control',
    'Banco de dados · experiência anterior': 'Databases · previous experience',
    'MySQL em servidores de Tibia e GTA V / FiveM.': 'MySQL for Tibia and GTA V / FiveM servers.',
    'Formação em evolução': 'Continuing education',
    'Engenharia Elétrica · São Judas Tadeu (em curso)': 'Electrical Engineering · São Judas Tadeu (in progress)',
    'Engenharia de Segurança do Trabalho · UFPR (em curso)': 'Occupational Safety Engineering · UFPR (in progress)',
    'Pós-graduação em Construção Civil · FAVENI': 'Postgraduate studies in Civil Construction · FAVENI',
    'Pesquisa e reconhecimento': 'Research and recognition',
    'Ex-bolsista FAPESP e CAPES': 'Former FAPESP and CAPES scholarship holder',
    'Artigo na Brazilian Administration Review': 'Article in Brazilian Administration Review',
    'Destaque profissional KPMG · FY25': 'KPMG Professional Distinction · FY25',
    'Destaque REIAd · 2023 e 2024': 'REIAd recognition · 2023 and 2024',
    'Presença no GitHub': 'GitHub presence',
    'Atividade pública': 'Public activity',
    'Repositórios públicos': 'Public repositories',
    'Estrelas recebidas': 'Stars received',
    'Alterações registradas': 'Recorded commits',
    'Propostas de alteração': 'Pull requests',
    'Ocorrências criadas': 'Issues opened',
    'Seguidores': 'Followers',
    'Linguagens nos repositórios': 'Repository languages',
    'Distribuição por bytes de código': 'Distribution by code bytes',
    'Contribuições totais': 'Total contributions',
    'Maior sequência': 'Longest streak',
    'Sequência atual': 'Current streak',
    'Atividade e contribuições': 'Activity and contributions',
    'Menos': 'Less', 'Mais': 'More', 'Seg': 'Mon', 'Qua': 'Wed', 'Sex': 'Fri', 'Outras': 'Other',
    'LinkedIn — André Mello': 'LinkedIn — André Mello',
    'GitHub — explorar meus repositórios': 'GitHub — explore my repositories',
    'E-mail — andremello@outlook.com': 'Email — andremello@outlook.com',
    'Linguagens por bytes em até seis repositórios públicos recentes: ': 'Languages by bytes across up to six recent public repositories: ',
}


def validate(locale):
    if locale not in LOCALES:
        raise ValueError('Unsupported profile locale: ' + locale)
    return locale


def tr(locale, text):
    validate(locale)
    return text if locale == DEFAULT else EN[text]


def localized(stem, locale=DEFAULT):
    validate(locale)
    return stem if locale == DEFAULT else stem + '-' + locale


def readme_name(locale=DEFAULT):
    return 'README.md' if validate(locale) == DEFAULT else 'README.en-US.md'


def preview_name(locale=DEFAULT):
    return 'previa.html' if validate(locale) == DEFAULT else 'preview.en-US.html'


def preview_image(theme, locale=DEFAULT):
    validate(locale)
    return ('PREVIA.png' if theme == 'light' else 'PREVIA-ESCURO.png') if locale == DEFAULT else f'PREVIEW-en-US-{theme}.png'


INTRO_ALT = {
    DEFAULT: 'André Mello — Dados, automação e engenharia. Dados e automação na prática. '
             'Projetos de análise de dados, integrações e engenharia. Retrato ASCII animado.',
    'en-US': 'André Mello — Data, automation and engineering. Data and automation in practice. '
             'Data analytics, integration and engineering projects. Animated ASCII portrait.',
}
PROFESSIONAL_ALT = {
    DEFAULT: 'Atuação e resultados informados por André: governança de R$ 660 milhões em ativos físicos; aumento de 25% na eficiência operacional; '
             'eliminação de 240 horas anuais de retrabalho; liderança de equipes com até 80 profissionais. Governança de portfólio e PMO, '
             'engenharia e contratos com CAPEX de até R$ 125 milhões, análise de dados e automação.',
    'en-US': 'Experience and results reported by André: governance of BRL 660 million in physical assets; a 25% increase in operational efficiency; '
             '240 annual hours of rework eliminated; leadership of cross-functional teams of up to 80 professionals. Portfolio governance and PMO, '
             'engineering and contracts with CAPEX up to BRL 125 million, data analytics and automation.',
}
TECHNOLOGY_ALT = {
    DEFAULT: 'Tecnologias e ferramentas: Power BI, Python, Alteryx, Power Automate, Power Apps, Oracle Cloud e SAP; '
             'Microsoft 365: Word, Excel, PowerPoint, Outlook, OneNote, Teams, OneDrive, SharePoint, Access, '
             'Forms, Lists, Planner, To Do, Loop, Whiteboard, Bookings, Stream, Sway, Visio, Project e Copilot; '
             'engenharia e geoprocessamento: AutoCAD, Revit, QGIS e Google Earth; '
             'desenvolvimento e versionamento: Visual Studio, Git e GitHub; conhecimentos de HTML, CSS, JavaScript e Lua; '
             'experiência anterior em MySQL para servidores de Tibia e GTA V / FiveM.',
    'en-US': 'Technology and tools: Power BI, Python, Alteryx, Power Automate, Power Apps, Oracle Cloud and SAP; '
             'Microsoft 365: Word, Excel, PowerPoint, Outlook, OneNote, Teams, OneDrive, SharePoint, Access, '
             'Forms, Lists, Planner, To Do, Loop, Whiteboard, Bookings, Stream, Sway, Visio, Project and Copilot; '
             'engineering and geospatial tools: AutoCAD, Revit, QGIS and Google Earth; '
             'development and version control: Visual Studio, Git and GitHub; working knowledge of HTML, CSS, JavaScript and Lua; '
             'previous MySQL experience with Tibia and GTA V / FiveM servers.',
}
STATUS_ALT = {
    DEFAULT: 'Presença no GitHub: repositórios públicos, estrelas, registros de alterações, propostas de alteração, ocorrências e seguidores; '
             'composição de código dos repositórios.',
    'en-US': 'GitHub presence: public repositories, stars, commits, pull requests, issues and followers; repository code composition.',
}
ACTIVITY_ALT = {
    DEFAULT: 'Atividade e contribuições: contribuições totais desde a criação da conta, sequência atual e maior sequência, '
             'com suas datas. A cidade 3D mostra o ano inteiro, nos últimos 12 meses: a base fica parada e os prédios sobem durante três segundos; a cidade completa permanece visível por sete segundos e o ciclo se repete a cada dez segundos. '
             'Cada bloco representa um dia, com as cores dos níveis de contribuição do GitHub; a altura final é proporcional às contribuições públicas reais de André Mello. Fundo integrado ao tema.',
    'en-US': 'Activity and contributions: total contributions since account creation, current streak and longest streak, '
             'with their date ranges. The 3D city shows a complete year, covering the last 12 months: the floor stays fixed while buildings rise for three seconds; the completed city remains visible for seven seconds and the cycle repeats every ten seconds. '
             'Each block represents one day using GitHub contribution-level colors; final height is proportional to André Mello’s actual public contributions. The background matches the theme.',
}
''',

    # ===== scripts/projects_section.py =====
    'scripts/projects_section.py': '''"""Native project links: public metadata, no repository screenshots."""
from html import escape
import re

MAX_PROJECTS = 3
TITLES = {'financial-performance-analytics': 'Performance financeira',
          'finance-close-automation': 'Automação de fechamento',
          'sap-project-financial-control-tower': 'Controle financeiro de projetos SAP',
          'sap-procurement-control-tower': 'Controle de compras SAP',
          'mello-charts-desktop': 'Mello Charts para PowerPoint'}


def _escape(value):
    text = escape(' '.join(str(value).split()), quote=False)
    return re.sub(r'([\\\\`*_\\[\\]|])', r'\\\\\\1', text)


def featured(content, username):
    repos = [r for r in content['repositories']
             if not r.get('fork') and not r.get('private') and r.get('description')
             and r.get('name', '').lower() != username.lower()
             and re.fullmatch(r'[A-Za-z0-9_.-]+', r.get('name', ''))
             and r.get('html_url') == f'https://github.com/{username}/{r["name"]}']
    return sorted(repos, key=lambda r: r.get('pushed_at') or '', reverse=True)[:MAX_PROJECTS]


def _title(repo):
    return TITLES.get(repo['name'], repo['name'].replace('-', ' ').replace('_', ' ').capitalize())


def projects_markdown(content, username):
    projects = featured(content, username)
    if not projects:
        return ''
    rows = ['| Projeto | Aplicação |', '|:--|:--|']
    for repo in projects:
        rows.append(f'| **[{_escape(_title(repo))}]({repo["html_url"]})** | {_escape(repo["description"])} |')
    return '\\n'.join(rows) + '\\n'


def projects_html(content, username):
    projects = featured(content, username)
    if not projects:
        return ''
    head = '<tr><th align="left">Projeto</th><th align="left">Aplicação</th></tr>'
    body = ''.join('<tr><td><b><a href="' + escape(r['html_url']) + '">' + escape(_title(r))
                   + '</a></b></td><td>' + escape(' '.join(r['description'].split())) + '</td></tr>'
                   for r in projects)
    return '<table>' + head + body + '</table>'
''',

    # ===== scripts/run_summary.py =====
    'scripts/run_summary.py': '''"""Report each consultation in Actions without adding notices to the profile."""
from datetime import datetime, timezone
from pathlib import Path
import json, os

ROOT = Path(__file__).resolve().parents[1]


def main():
    changed = os.getenv('PROFILE_CHANGED')
    status = os.getenv('PROFILE_RUN_STATUS', 'unknown')
    labels = {'success': 'concluída', 'failure': 'falhou', 'cancelled': 'cancelada',
              'skipped': 'dispensada'}
    lines = ['## Atualização do perfil', '',
             '- Consulta: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
             '- Disparo: ' + os.getenv('PROFILE_EVENT', 'local'),
             '- Resultado: ' + labels.get(status, status),
             '- Coleta do calendário: ' + labels.get(os.getenv('PROFILE_CALENDAR_STATUS'), 'não executada'),
             '- Publicação das imagens: ' + labels.get(os.getenv('PROFILE_DEPLOY_STATUS'), 'não executada')]
    calendar = ROOT / 'data/contributions.json'
    if calendar.exists():
        data = json.loads(calendar.read_text(encoding='utf-8'))
        lines.extend(['- Data dos dados disponíveis: ' + data['as_of'],
                      '- Contribuições no período: ' + str(data['stats']['total'])])
    if changed == 'false' and status == 'success':
        lines.extend(['', 'Dados consultados com sucesso, sem alterações no painel. '
                      'Nenhum novo commit foi necessário.'])
    elif changed == 'true' and status == 'success':
        lines.extend(['', 'Dados e arte atualizados. As imagens foram publicadas antes dos links do README.'])
    elif status != 'success':
        lines.extend(['', 'Consulte a etapa que falhou nos logs. O último painel válido permanece disponível.'])
    lines.extend(['', 'Agendamento: a cada 5 minutos; o disparo pode atrasar no GitHub Actions.'])
    summary = '\\n'.join(lines) + '\\n'
    destination = os.getenv('GITHUB_STEP_SUMMARY')
    if destination:
        with open(destination, 'a', encoding='utf-8') as file:
            file.write(summary)
    print(summary)


if __name__ == '__main__':
    main()
''',

    # ===== scripts/status_panel.py =====
    'scripts/status_panel.py': '''"""GitHub status cards: public numbers, language mix and streaks."""
import json
import math
from datetime import date
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import TYPE, section_heading, metric_icon
from fetch_contributions import derive_stats
from profile_i18n import DEFAULT, tr, localized

# Language colors come directly from the local GitHub Linguist snapshot.
# They stay identical in both themes and both locales; only the card adapts.

HEIGHT = 344
STREAK_TOP = 356
STREAK_HEIGHT = 272


def _icon(draw, kind, x, y, color):
    if kind == 'repos':
        metric_icon(draw, x, y, 0, color)
    elif kind == 'stars':
        points = []
        for i in range(10):
            radius = 13 if i % 2 == 0 else 5.5
            angle = -math.pi / 2 + i * math.pi / 5
            points.append((x + 13 + radius * math.cos(angle), y + 14 + radius * math.sin(angle)))
        draw.polygon(points, outline=color, width=2)
    elif kind == 'commits':
        draw.ellipse((x + 8, y + 7, x + 18, y + 17), outline=color, width=2)
        draw.line((x, y + 12, x + 8, y + 12), fill=color, width=2)
        draw.line((x + 18, y + 12, x + 26, y + 12), fill=color, width=2)
    elif kind == 'prs':
        for cx, cy in [(x + 5, y + 4), (x + 5, y + 21), (x + 21, y + 21)]:
            draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=color, width=2)
        draw.line((x + 5, y + 8, x + 5, y + 17), fill=color, width=2)
        draw.line((x + 21, y + 17, x + 21, y + 6, x + 15, y + 6), fill=color, width=2)
        draw.line((x + 18, y + 3, x + 15, y + 6, x + 18, y + 9), fill=color, width=2)
    elif kind == 'issues':
        draw.ellipse((x + 1, y + 1, x + 25, y + 25), outline=color, width=2)
        draw.ellipse((x + 10, y + 10, x + 16, y + 16), fill=color)
    else:  # followers
        draw.ellipse((x + 8, y + 1, x + 18, y + 11), outline=color, width=2)
        draw.arc((x + 2, y + 13, x + 24, y + 35), 180, 360, fill=color, width=2)


def _ring(image, center, radius, ratio, track, color, width=8):
    scale = 4
    size = (radius + width) * 2 * scale
    layer = Image.new('RGBA', (size, size), TRANSPARENT)
    d = ImageDraw.Draw(layer)
    box = (width * scale, width * scale, size - width * scale, size - width * scale)
    d.arc(box, 0, 360, fill=track, width=width * scale)
    if ratio > 0:
        d.arc(box, -90, -90 + 360 * min(1, ratio), fill=color, width=width * scale)
    layer = layer.resize((size // scale, size // scale), Image.Resampling.LANCZOS)
    image.alpha_composite(layer, (center[0] - layer.width // 2, center[1] - layer.height // 2))


def _fmt(value, locale=DEFAULT):
    if value is None:
        return '—'
    return f'{value:,}'.replace(',', '.') if locale == DEFAULT else f'{value:,}'


def language_legend(rows, total, measure, locale=DEFAULT):
    """Reserve the share column and keep readable type for long language names."""
    entries = []
    for index, (name, value) in enumerate(rows):
        share = f'{value / (total or 1) * 100:.1f}%'
        if locale == DEFAULT:
            share = share.replace('.', ',')
        available = 1156 - 762 - 18 - 12 - measure(share)
        label = tr(locale, name) if name == 'Outras' else name
        if measure(label) > available:
            while label and measure(label.rstrip() + '…') > available:
                label = label[:-1]
            label = label.rstrip() + '…'
        entries.append(dict(x=762, y=188 + index*23, right=1156,
                            name=label, source=name, share=share))
    return entries


def streak_date_labels(summary, as_of, locale=DEFAULT):
    months = (['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'] if locale == DEFAULT
              else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    def day_label(value):
        value = date.fromisoformat(value)
        if locale == DEFAULT:
            return f'{value.day} {months[value.month-1]}' + (f' {value.year}' if value.year != as_of.year else '')
        return f'{months[value.month-1]} {value.day}' + (f', {value.year}' if value.year != as_of.year else '')
    def interval(value):
        if not value:
            return '—'
        start, end = day_label(value['start']), day_label(value['end'])
        return start if start == end else start + ' — ' + end
    first = summary.get('first_contribution')
    return {'total':day_label(first)+(' — atual' if locale == DEFAULT else ' — present') if first else '—',
            'current':interval(summary.get('current_streak_range')),
            'longest':interval(summary.get('longest_streak_range'))}


def _flame(image, cx, y, color, background, scale=1):
    # Curved flame geometry follows the reference widget's src/card.php icon.
    # Rasterized here so the profile does not depend on an external SVG service.
    s, k = 4, 1200/495 * scale
    width, height = math.ceil(27*k), math.ceil(25*k)
    layer = Image.new('RGBA', (width*s, height*s), TRANSPARENT)
    draw = ImageDraw.Draw(layer)
    def contour(start, segments):
        points, current = [start], start
        for controls in segments:
            if len(controls) == 2:
                current = controls
                points.append(current)
                continue
            x0,y0 = current
            x1,y1,x2,y2,x3,y3 = controls
            for step in range(1,25):
                t = step/24
                points.append(((1-t)**3*x0+3*(1-t)**2*t*x1+3*(1-t)*t*t*x2+t**3*x3,
                               (1-t)**3*y0+3*(1-t)**2*t*y1+3*(1-t)*t*t*y2+t**3*y3))
            current = x3,y3
        return [((x+12)*k*s,(y+1)*k*s) for x,y in points]
    outer = contour((1.5,.67), [(1.5,.67,2.24,3.32,2.24,5.47),
                    (2.24,7.53,.89,9.2,-1.17,9.2),(-3.23,9.2,-4.79,7.53,-4.79,5.47),
                    (-4.76,5.11),(-6.78,7.51,-8,10.62,-8,13.99),
                    (-8,18.41,-4.42,22,0,22),(4.42,22,8,18.41,8,13.99),
                    (8,8.6,5.41,3.79,1.5,.67)])
    inner = contour((-.29,19), [(-2.07,19,-3.51,17.6,-3.51,15.86),
                    (-3.51,14.24,-2.46,13.1,-.7,12.74),(1.07,12.38,2.9,11.53,3.92,10.16),
                    (4.31,11.45,4.51,12.81,4.51,14.2),(4.51,16.85,2.36,19,-.29,19)])
    draw.polygon(outer, fill=color)
    draw.polygon(inner, fill=background)
    image.alpha_composite(layer.resize((width,height), Image.Resampling.LANCZOS), (cx-round(12*k),y))


def render_status(root, font, palette, locale=DEFAULT):
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    history = json.loads((root/'data/contributions-history.json').read_text(encoding='utf-8'))
    summary = derive_stats(history['days'], date.fromisoformat(history['as_of']))
    dates = streak_date_labels(summary, date.fromisoformat(history['as_of']), locale)
    stats = content.get('stats', {})
    text, muted, accent, brand = palette['text'], palette['muted'], palette['accent'], palette['brand']
    blue = palette['brand']
    fire = '#fb8c00'
    # Render the unchanged metrics once, then hand their transparent layer to
    # the animated activity card. The public status image contains only repos/languages.
    im = Image.new('RGBA', (1200, STREAK_TOP + STREAK_HEIGHT), TRANSPARENT)
    d = ImageDraw.Draw(im)
    section_heading(d, palette, font, tr(locale, 'Presença no GitHub'), 12)
    card = dict(radius=12, fill=palette['matte'], outline=palette['line'])

    d.rounded_rectangle((24, 76, 718, 332), **card)
    d.text((44, 92), tr(locale, 'Atividade pública'), font=font(TYPE['card'], True), fill=blue)
    tiles = [('repos', 'Repositórios públicos', content['user']['public_repos']),
             ('stars', 'Estrelas recebidas', stats.get('stars')),
             ('commits', 'Alterações registradas', stats.get('commits')),
             ('prs', 'Propostas de alteração', stats.get('pull_requests')),
             ('issues', 'Ocorrências criadas', stats.get('issues')),
             ('followers', 'Seguidores', content['user']['followers'])]
    for i, (kind, label, value) in enumerate(tiles):
        x, y = 44 + (i % 2) * 338, 140 + (i // 2) * 64
        _icon(d, kind, x, y + 6, blue)
        d.text((x + 40, y), tr(locale, label), font=font(TYPE['meta']), fill=muted)
        d.text((x + 40, y + 22), _fmt(value, locale), font=font(30, True), fill=text)

    d.rounded_rectangle((742, 76, 1176, 332), **card)
    d.text((762, 92), tr(locale, 'Linguagens nos repositórios'), font=font(TYPE['card'], True), fill=blue)
    d.text((762, 128), tr(locale, 'Distribuição por bytes de código'), font=font(TYPE['meta']), fill=muted)
    languages = content.get('languages', {})
    total = sum(languages.values()) or 1
    rows = list(languages.items())[:5]
    others = sum(size for _, size in list(languages.items())[5:])
    if others:
        rows.append(('Outras', others))
    language_colors = json.loads((root/'data/language-colors.json').read_text(encoding='utf-8'))['colors']
    rail = Image.new('RGBA', (394, 14), TRANSPARENT)
    rd = ImageDraw.Draw(rail)
    consumed = 0
    for name, size in rows:
        start = round(394*consumed/total)
        consumed += size
        end = round(394*consumed/total)
        if end > start:
            rd.rectangle((start,0,end-1,13), fill=language_colors.get(name, palette['muted']))
            if start:
                rd.line((start,0,start,13), fill=palette['matte'])
    mask = Image.new('L', rail.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,393,13), radius=7, fill=255)
    rail.putalpha(mask)
    im.alpha_composite(rail, (762,168))
    legend_face = font(TYPE['meta'])
    measure = lambda value: d.textlength(value, font=legend_face)
    for item in language_legend(rows, total, measure, locale):
        x, y = item['x'], item['y']
        color = language_colors.get(item['source'],palette['muted'])
        dot = Image.new('RGBA', (36,36), TRANSPARENT)
        ImageDraw.Draw(dot).ellipse((1,1,34,34), fill=color)
        im.alpha_composite(dot.resize((12,12),Image.Resampling.LANCZOS),(x,y+4))
        d.text((x+18, y), item['name'], font=legend_face, fill=text)
        d.text((item['right'] - measure(item['share']), y), item['share'], font=legend_face, fill=muted)

    d.line((408, 388, 408, 596), fill=palette['line'])
    d.line((792, 388, 792, 596), fill=palette['line'])
    columns = [(216, _fmt(summary['total'], locale), 'Contribuições totais', dates['total']),
               (984, _fmt(summary['longest_streak'], locale), 'Maior sequência', dates['longest'])]
    for cx, value, label, span in columns:
        d.text((cx,467), value, font=font(TYPE['number'],True), fill=text, anchor='ms')
        d.text((cx,510), tr(locale, label), font=font(TYPE['card']), fill=text, anchor='ms')
        # A range crossing two old years is wider; fit it inside its own column.
        size = TYPE['meta']
        while size > 16 and d.textlength(span, font=font(size)) > 352:
            size -= 1
        d.text((cx,549), span, font=font(size), fill=muted, anchor='ms')
    _ring(im, (600,445), 56, 1, palette['line'], fire, 7)
    d.ellipse((581,360,619,414), fill=palette['matte'])
    _flame(im, 600, 367, fire, palette['matte'], scale=.60)
    d.text((600,463), str(summary['current_streak']), font=font(TYPE['number'],True), fill=text, anchor='ms')
    d.text((600,546), tr(locale, 'Sequência atual'), font=font(TYPE['card'],True), fill=fire, anchor='ms')
    size = TYPE['meta']
    while size > 16 and d.textlength(dates['current'], font=font(size)) > 352:
        size -= 1
    d.text((600,583), dates['current'], font=font(size), fill=muted, anchor='ms')
    im.crop((0,0,1200,HEIGHT)).save(root/'assets'/f'{localized("status",locale)}-{palette["name"]}.png')
    im.crop((0,STREAK_TOP,1200,STREAK_TOP+STREAK_HEIGHT)).save(
        root/'assets'/f'{localized("streak",locale)}-{palette["name"]}.png')
    return summary
''',

    # ===== scripts/technology_panel.py =====
    'scripts/technology_panel.py': '''"""A compact technical stack with one neutral badge system."""
from PIL import Image, ImageDraw, ImageChops
from themes import TRANSPARENT
from branding import TYPE, MARGIN, section_heading, wrapped_text
from profile_i18n import DEFAULT, tr, localized

MICROSOFT_365 = [
    ('Word', 'word'), ('Excel', 'excel'), ('PowerPoint', 'powerpoint'),
    ('Outlook', 'outlook'), ('OneNote', 'onenote'), ('Teams', 'teams'), ('Copilot', 'copilot'),
    ('OneDrive', 'onedrive'), ('SharePoint', 'sharepoint'), ('Access', 'access'),
    ('Forms', 'forms'), ('Lists', 'lists'), ('Planner', 'planner'),
    ('To Do', 'todo'), ('Loop', 'loop'), ('Whiteboard', 'whiteboard'),
    ('Bookings', 'bookings'), ('Stream', 'stream'), ('Sway', 'sway'),
    ('Visio', 'visio'), ('Project', 'project'),
]


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
    elif kind in ['excel', 'powerpoint', 'word', 'onenote', 'access', 'visio', 'project']:
        color, pale, letter = {
            'excel': ('#107c41', '#21a366', 'X'),
            'powerpoint': ('#c43e1c', '#e98262', 'P'),
            'word': ('#185abd', '#41a5ee', 'W'),
            'onenote': ('#7719aa', '#b46add', 'N'),
            'access': ('#a4373a', '#d26b6f', 'A'),
            'visio': ('#3955a3', '#7899e3', 'V'),
            'project': ('#217346', '#46a86b', 'P'),
        }[kind]
        rect((20,11,39,37), pale, 3)
        line([(24,20),(36,20)], color, 1)
        line([(24,28),(36,28)], color, 1)
        rect((12,16,30,34), color, 2)
        symbol(letter,21,25,16)
    elif kind == 'outlook':
        rect((21, 12, 40, 36), '#28a8ea', 3)
        polygon([(21, 24), (31, 31), (41, 24), (41, 37), (21, 37)], '#0078d4')
        rect((11, 17, 29, 35), '#106ebe', 2)
        symbol('O', 20, 26, 15)
    elif kind == 'teams':
        rect((28, 10, 36, 18), '#7b83eb', 4)
        rect((25, 20, 41, 35), '#7b83eb', 5)
        rect((10, 17, 29, 36), '#5059c9', 2)
        symbol('T', 19, 27, 15)
    elif kind == 'onedrive':
        for box, color in [((12, 21, 28, 36), '#0364b8'), ((20, 13, 38, 34), '#0078d4'),
                           ((28, 22, 42, 36), '#28a8ea')]:
            rect(box, color, 12)
        rect((18, 27, 38, 36), '#0078d4', 3)
    elif kind == 'sharepoint':
        rect((22, 10, 42, 30), '#038387', 12)
        rect((26, 22, 41, 38), '#37c6d0', 9)
        rect((10, 17, 29, 36), '#007c80', 2)
        symbol('S', 20, 27, 15)
    elif kind == 'forms':
        rect((21, 11, 40, 37), '#37c6d0', 3)
        for y in (18, 25, 32):
            line([(31, y), (36, y)], '#008272', 2)
        rect((10, 17, 28, 35), '#008272', 2)
        symbol('F', 19, 26, 15)
    elif kind == 'lists':
        for y, color in [(12, '#d767bc'), (22, '#b74e9c'), (32, '#7b3f95')]:
            rect((12, y, 20, y + 6), color, 2)
            rect((23, y, 40, y + 6), color, 2)
    elif kind == 'planner':
        rect((13, 11, 40, 38), '#107c41', 5)
        rect((18, 19, 23, 33), '#7fd68d', 1)
        rect((27, 15, 34, 26), '#b9eabd', 1)
    elif kind == 'todo':
        line([(12, 25), (22, 35), (40, 15)], '#2564cf', 5)
        line([(12, 25), (17, 30)], '#65a2fa', 5)
    elif kind == 'loop':
        rect((12, 11, 39, 37), '#8b5cf6', 12)
        rect((20, 17, 33, 31), palette['matte'], 7)
        rect((30, 27, 41, 38), '#bca1ff', 6)
    elif kind == 'whiteboard':
        rect((12, 12, 40, 37), None, 4, '#0875d1', 2)
        line([(18, 29), (25, 20), (31, 26), (36, 19)], '#0875d1', 2)
    elif kind == 'bookings':
        rect((13, 12, 40, 37), '#008575', 4)
        line([(17, 18), (36, 18)], '#99e0d5', 2)
        symbol('B', 26, 28, 17)
    elif kind == 'stream':
        polygon([(14, 11), (40, 24), (14, 38)], '#c43b73')
        polygon([(23, 19), (32, 24), (23, 29)], 'white')
    elif kind == 'sway':
        rect((22, 12, 40, 37), '#37af8c', 3)
        rect((11, 17, 29, 35), '#008272', 2)
        symbol('S', 20, 26, 15)
    elif kind == 'copilot':
        for box, color in [((12, 12, 29, 29), '#6554c0'), ((23, 12, 40, 29), '#29a8c7'),
                           ((23, 22, 40, 38), '#e6a63e'), ((12, 22, 29, 38), '#c35da2')]:
            rect(box, color, 7)
        rect((22, 20, 30, 30), palette['matte'], 3)
    elif kind == 'powerapps':
        polygon([(12, 24), (25, 11), (39, 24), (25, 37)], '#742774')
        polygon([(19, 24), (29, 14), (40, 24), (29, 34)], '#c886ca')
    elif kind == 'autocad':
        polygon([(25, 9), (41, 38), (31, 34), (25, 20), (19, 34), (10, 38)], '#d32f42')
        line([(20, 29), (31, 29)], '#f5808a', 3)
    elif kind == 'revit':
        polygon([(13, 11), (33, 11), (41, 18), (34, 25), (41, 38), (29, 38),
                 (22, 26), (22, 38), (13, 38)], '#1866af')
        rect((22, 17, 30, 22), palette['matte'], 1)
    elif kind == 'qgis':
        rect((12, 10, 40, 38), '#589632', 14)
        rect((19, 17, 33, 31), palette['matte'], 7)
        polygon([(25, 24), (38, 25), (42, 39), (29, 33)], '#eeb246')
    elif kind == 'googleearth':
        rect((12, 10, 40, 38), '#4285f4', 14)
        line([(14, 20), (23, 17), (37, 24)], '#c2dcff', 3)
        line([(13, 28), (22, 25), (38, 32)], '#8bb9fa', 3)
        line([(17, 35), (26, 33), (34, 36)], '#c2dcff', 2)
    elif kind == 'visualstudio':
        polygon([(12, 19), (19, 13), (29, 20), (39, 10), (42, 12), (42, 37),
                 (38, 39), (29, 29), (19, 36), (12, 30), (21, 24)], '#9b5de5')
        polygon([(31, 22), (37, 17), (37, 32), (31, 27)], palette['matte'])
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
    # Measure the real font before allocating cards, including Linux CI fonts.
    # Every product uses the same 48px pill; card height follows wrapped rows.
    measure = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    groups = []
    def group(title, items, x, y, width, note=None):
        placements, px, py = [], 20, 56
        for item in items:
            if item is None:
                px, py = 20, py + 60
                continue
            label, kind = item
            badge = _product(root, label, kind, font, palette)
            if badge.width > width - 40:
                raise ValueError('Tool label is wider than its card: ' + label)
            if px + badge.width > width - 20:
                px, py = 20, py + 60
            placements.append((badge, px, py))
            px += badge.width + 10
        height = py + 48 + 20
        if measure.textlength(tr(locale, title), font=font(TYPE['card'], True)) > width - 40:
            raise ValueError('Tool heading is wider than its card: ' + title)
        if note:
            # Measure the translated note with the same helper used for drawing.
            note_y = py + 48 + 12
            note_height = wrapped_text(measure, (0, 0), tr(locale, note),
                                       font(TYPE['body']), 'white', width - 40)
            height = note_y + note_height + 20
        groups.append((x, y, width, height, title, placements, note, py + 60))
        return height

    y = 72
    y += group('Dados, sistemas e automação', [
        ('Power BI', 'powerbi'), ('Python', 'python'), ('Alteryx', 'alteryx'), ('SAP', 'sap'), None,
        ('Power Automate', 'automate'), ('Power Apps', 'powerapps'),
        ('Oracle Cloud', 'oracle')], MARGIN, y, 1152) + 24
    y += group('Microsoft 365 · produtividade e colaboração', MICROSOFT_365,
               MARGIN, y, 1152) + 24
    engineering = group('Engenharia e geoprocessamento', [
        ('AutoCAD', 'autocad'), ('Revit', 'revit'), ('QGIS', 'qgis'),
        ('Google Earth', 'googleearth')], MARGIN, y, 564)
    development = group('Desenvolvimento e versionamento', [
        ('Visual Studio', 'visualstudio'), ('Git', 'git'), ('GitHub', 'github')], 612, y, 564)
    # Sibling cards share their baseline even if one has an extra wrapped row.
    row_height = max(engineering, development)
    groups[-2] = groups[-2][:3] + (row_height,) + groups[-2][4:]
    groups[-1] = groups[-1][:3] + (row_height,) + groups[-1][4:]
    y += row_height + 24
    languages = group('Linguagens · conhecimentos', [
        ('HTML', 'html'), ('CSS', 'css'), ('JavaScript', 'javascript'), ('Lua', 'lua')],
        MARGIN, y, 564)
    database = group('Banco de dados · experiência anterior', [('MySQL', 'mysql')],
                     612, y, 564, 'MySQL em servidores de Tibia e GTA V / FiveM.')
    row_height = max(languages, database)
    groups[-2] = groups[-2][:3] + (row_height,) + groups[-2][4:]
    groups[-1] = groups[-1][:3] + (row_height,) + groups[-1][4:]

    image = Image.new('RGBA', (1200, y + row_height + 18), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    section_heading(draw, palette, font, tr(locale, 'Tecnologias e ferramentas'), 12)
    for x, y, width, height, title, placements, note, note_y in groups:
        draw.rounded_rectangle((x, y, x + width, y + height), radius=12,
                               fill=palette['surface'], outline=palette['line'])
        draw.text((x + 20, y + 17), tr(locale, title),
                  font=font(TYPE['card'], True), fill=palette['accent'])
        for badge, px, py in placements:
            image.alpha_composite(badge, (x + px, y + py))
        if note:
            wrapped_text(draw, (x + 20, y + note_y), tr(locale, note),
                         font(TYPE['body']), palette['muted'], width - 40)
    image.save(root/'assets'/f'{localized("stack", locale)}-{palette["name"]}.png')
''',

    # ===== scripts/themes.py =====
    'scripts/themes.py': '''"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#1f2328', muted='#59636e',
                  accent='#273c50', line='#d1d9e0', portrait='#294b70', matte='#ffffff',
                  brand='#294b70', brand_line='#a6b7c8', surface='#f6f8fa',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#f0f6fc', muted='#9198a1',
                 accent='#d0dae5', line='#30363d', portrait='#a7bdd3', matte='#0d1117',
                 brand='#a7c3df', brand_line='#52677d', surface='#151b23',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
''',

    # ===== tests/test_activity_updates.py =====
    'tests/test_activity_updates.py': '''from pathlib import Path
import sys,unittest,importlib.util,json,tempfile
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fetch_github_content import normalize_content

class ActivityUpdates(unittest.TestCase):
    def test_profile_generated_commits_do_not_cause_endless_updates(self):
        user={'login':'andremellotech','created_at':'2021-04-07'}
        repo={'name':'andremellotech','html_url':'https://github.com/andremellotech/andremellotech','pushed_at':'2026-10-17T10:00:00Z'}
        first=normalize_content(user,[repo],{})
        second=normalize_content(user,[dict(repo,pushed_at='2026-10-17T11:00:00Z')],{})
        self.assertEqual(first,second,'The updater must not react to its own generated commit timestamp')
    def test_actual_project_changes_are_still_detected(self):
        user={'login':'andremellotech','created_at':'2021-04-07'}
        repo={'name':'project','html_url':'https://github.com/andremellotech/project','pushed_at':'2026-10-17T10:00:00Z'}
        self.assertNotEqual(normalize_content(user,[repo],{}),normalize_content(user,[dict(repo,pushed_at='2026-10-17T11:00:00Z')],{}))
    def test_unified_panel_uses_calendar_data(self):
        spec=importlib.util.find_spec('activity_panel')
        self.assertIsNotNone(spec,'Unified contribution panel is missing')
        from activity_panel import contribution_summary,week_grid
        days=[{'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'count':c,'level':min(c,4)} for i,c in enumerate([0,3,2,0,1])]
        summary=contribution_summary({'user':{'public_repos':7}},{'as_of':'2026-01-05','days':days})
        self.assertEqual(summary['total'],6)
        self.assertEqual(summary['active_days'],3)
        self.assertEqual(summary['repositories'],7)
        self.assertEqual(summary['current_streak'],1)
        self.assertEqual(summary['longest_streak'],2)
        cells=week_grid(days)
        self.assertEqual(cells[0]['row'],4) # Thursday, with Sunday at row zero.
        self.assertEqual(cells[-1]['column'],1)
        self.assertEqual(sum(c['count'] for c in cells),6)

if __name__=='__main__':unittest.main()

''',

    # ===== tests/test_contribution_city.py =====
    'tests/test_contribution_city.py': '''"""The annual city must include every real day without decorative activity."""
from datetime import date, timedelta
import copy, importlib, importlib.util, sys, unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class ContributionCity(unittest.TestCase):
    def model(self,calendar):
        self.assertIsNotNone(importlib.util.find_spec('contribution_city'),
                             'The annual contribution city renderer is required')
        return importlib.import_module('contribution_city').build_city_model(calendar)

    def calendar(self):
        start=date(2025,10,26)
        counts={'2025-10-27':9000,'2025-10-28':2,'2026-09-28':4,'2026-10-27':3,'2026-10-28':8000}
        return {'as_of':'2026-10-27','days':[{'date':(start+timedelta(days=i)).isoformat(),
                  'count':counts.get((start+timedelta(days=i)).isoformat(),0),
                  'level':min(4,counts.get((start+timedelta(days=i)).isoformat(),0))} for i in range(368)]}

    def test_full_year_includes_older_activity_but_excludes_padding_and_future(self):
        model=self.model(self.calendar())
        self.assertEqual((model['start'],model['end']),('2025-10-28','2026-10-27'))
        self.assertEqual(len(model['days']),365)
        self.assertEqual((model['total'],model['active_days'],model['peak']),(9,3,4))

    def test_annual_window_preserves_leap_day(self):
        start=date(2023,3,2); end=date(2024,3,1)
        calendar={'as_of':end.isoformat(),'days':[{'date':(start+timedelta(days=i)).isoformat(),'count':0,'level':0}
                  for i in range((end-start).days+1)]}
        calendar['days'][-2]['count']=7
        calendar['days'][-2]['level']=4
        model=self.model(calendar)
        self.assertEqual((model['start'],model['end']),('2023-03-02','2024-03-01'))
        self.assertEqual(len(model['days']),366)
        self.assertEqual(model['total'],7)

    def test_building_heights_follow_actual_counts_and_zero_days_have_no_tower(self):
        model=self.model(self.calendar())
        rows={item['date']:item for item in model['days']}
        self.assertEqual(rows['2026-10-01']['height'],0)
        self.assertGreater(rows['2026-09-28']['height'],0)
        self.assertAlmostEqual(rows['2026-10-27']['height']/rows['2025-10-28']['height'],1.5)

    def test_incomplete_duplicate_or_invalid_daily_data_stops_rendering(self):
        baseline=self.calendar()
        for change in ['missing','duplicate','negative','fractional']:
            calendar=copy.deepcopy(baseline)
            chosen=next(item for item in calendar['days'] if item['date']=='2026-10-15')
            if change=='missing': calendar['days'].remove(chosen)
            elif change=='duplicate': calendar['days'].append(chosen.copy())
            elif change=='negative': chosen['count']=-1
            else: chosen['count']=.5
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.model(calendar)

    def test_empty_activity_has_no_invented_buildings_or_statistics(self):
        calendar=self.calendar()
        for item in calendar['days']: item.update(count=0,level=0)
        model=self.model(calendar)
        self.assertEqual((model['total'],model['active_days'],model['peak']),(0,0,0))
        self.assertTrue(all(item['height']==0 for item in model['days']))

    def test_original_github_color_levels_are_preserved_and_validated(self):
        model=self.model(self.calendar())
        self.assertIn('level',model['days'][0],'Keep the actual GitHub intensity for each day')
        self.assertEqual(model['days'][0]['level'],2)
        for invalid in [None,True,-1,5]:
            calendar=self.calendar();calendar['days'][2]['level']=invalid
            with self.subTest(level=invalid),self.assertRaises(ValueError):self.model(calendar)

    def test_buildings_grow_to_real_height_without_moving_the_floor(self):
        city=importlib.import_module('contribution_city')
        self.assertTrue(callable(getattr(city,'growth_height',None)),
                        'The reference grows buildings instead of rotating the camera')
        for height in [0,.2,5,110]:
            steps=[city.growth_height(height,i/30) for i in range(31)]
            self.assertEqual(steps[-1],height)
            self.assertTrue(all(0<=a<=b<=height for a,b in zip(steps,steps[1:])))
        self.assertLess(city.growth_height(110,0),city.growth_height(110,1))


if __name__=='__main__': unittest.main()
''',

    # ===== tests/test_github_http.py =====
    'tests/test_github_http.py': '''"""Verify transient GitHub failures are retried using a real local HTTP server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import importlib.util, sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class GithubHttp(unittest.TestCase):
    def request_with_statuses(self, statuses):
        self.assertIsNotNone(importlib.util.find_spec('github_http'),
                             'GitHub requests need transient-failure recovery')
        from github_http import github_session
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                index = min(len(calls), len(statuses) - 1)
                calls.append(self.path)
                self.send_response(statuses[index])
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with github_session(backoff_factor=0) as session:
                response = session.get(f'http://127.0.0.1:{server.server_port}/public-data', timeout=2)
            return response, calls
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_transient_error_recovers_without_manual_rerun(self):
        response, calls = self.request_with_statuses([503, 502, 200])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 3)

    def test_permanent_error_does_not_loop(self):
        response, calls = self.request_with_statuses([404])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
''',

    # ===== tests/test_language_legend.py =====
    'tests/test_language_legend.py': '''"""Keep changing GitHub language names legible without colliding with shares."""
from pathlib import Path
import sys, unittest
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import status_panel
from design import font


class LanguageLegend(unittest.TestCase):
    def layout(self, rows):
        draw = ImageDraw.Draw(Image.new('RGBA', (1200, 640)))
        measure = lambda value: draw.textlength(value, font=font(18))
        layout = getattr(status_panel, 'language_legend', None)
        self.assertIsNotNone(layout, 'Language labels must reserve room for their percentages')
        result = layout(rows, sum(value for _, value in rows), measure)
        for item in result:
            self.assertGreaterEqual(item['x'], 762)
            self.assertLessEqual(item['right'], 1156)
            self.assertLessEqual(item['x'] + 18 + measure(item['name']) + 12,
                                 item['right'] - measure(item['share']))
            self.assertGreaterEqual(item['y'], 184)
            self.assertLessEqual(item['y'] + 24, 332)
        return result

    def test_long_names_do_not_overlap_shares(self):
        rows = [('Jupyter Notebook', 50), ('Visual Basic .NET', 20), ('HTML', 10),
                ('Python', 10), ('JavaScript', 5), ('Outras', 5)]
        result = self.layout(rows)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0]['name'], rows[0][0])
        self.assertEqual(result[0]['share'], '50,0%')

    def test_an_exceptionally_long_name_is_abbreviated_without_shrinking_type(self):
        result = self.layout([('Uma linguagem com um nome excepcionalmente longo ' * 4, 1)])
        self.assertTrue(result[0]['name'].endswith('…'))
        self.assertEqual(result[0]['share'], '100,0%')

    def test_an_empty_language_mix_has_no_invented_entries(self):
        self.assertEqual(self.layout([]), [])
''',

    # ===== tests/test_projects_section.py =====
    'tests/test_projects_section.py': '''from pathlib import Path
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from projects_section import featured, projects_markdown, projects_html


class ProjectsSection(unittest.TestCase):
    def test_only_public_owned_described_projects_are_shown(self):
        repos = [
            dict(name='novo', description='A | B', html_url='https://github.com/u/novo', pushed_at='2026-10-22'),
            dict(name='privado', description='Private', private=True, html_url='https://github.com/u/privado'),
            dict(name='estrangeiro', description='Wrong owner', html_url='https://github.com/other/estrangeiro'),
            dict(name='copia', description='Fork', fork=True, html_url='https://github.com/u/copia'),
            dict(name='u', description='Profile', html_url='https://github.com/u/u'),
            dict(name='sem', description=None, html_url='https://github.com/u/sem'),
            dict(name='antigo', description='Old', html_url='https://github.com/u/antigo'),
        ]
        self.assertEqual([r['name'] for r in featured({'repositories': repos}, 'u')], ['novo', 'antigo'])

    def test_escapes_html_and_markdown_in_descriptions(self):
        content = {'repositories': [dict(name='demo', html_url='https://github.com/u/demo',
                                        description='A | B <img src=x> [clicar](https://evil.test)')]}
        markdown = projects_markdown(content, 'u')
        self.assertIn('A \\\\| B', markdown)
        self.assertIn('&lt;img src=x&gt;', markdown)
        self.assertIn('\\\\[clicar\\\\]', markdown)
        self.assertNotIn('<img', projects_html(content, 'u'))
''',

    # ===== tests/test_public_stats.py =====
    'tests/test_public_stats.py': '''from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import sys, unittest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_github_content


class PublicStats(unittest.TestCase):
    def test_counts_only_public_authored_activity(self):
        collect = getattr(fetch_github_content, 'collect_stats', None)
        self.assertTrue(callable(collect), 'The profile needs a public statistics collector')
        def get(url):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)['q'][0]
            if 'author:andre' not in query or 'is:public' not in query:
                raise ValueError('Query may include private or unrelated activity')
            total = 13 if parsed.path == '/search/commits' else 5 if 'type:pr' in query else 2
            return SimpleNamespace(json=lambda: {'total_count': total, 'incomplete_results': False})
        self.assertEqual(collect(get, 'andre', [{'stargazers_count': 3}, {'stargazers_count': 7}]),
                         {'stars': 10, 'commits': 13, 'pull_requests': 5, 'issues': 2})

    def test_unavailable_or_incomplete_results_are_not_reported_as_current_totals(self):
        collect = getattr(fetch_github_content, 'collect_stats', None)
        self.assertTrue(callable(collect))
        for body in [None, {'total_count': 50, 'incomplete_results': True},
                     {'total_count': True, 'incomplete_results': False},
                     {'total_count': -1, 'incomplete_results': False}]:
            with self.subTest(body=body):
                def get(url):
                    if body is None:
                        raise requests.HTTPError('Temporary search failure')
                    return SimpleNamespace(json=lambda: body)
                self.assertEqual(collect(get, 'andre', []),
                                 {'stars': 0, 'commits': None, 'pull_requests': None, 'issues': None})
''',

    # ===== tests/test_streak_dates.py =====
    'tests/test_streak_dates.py': '''"""Display real intervals in the date format shown in the reference cards."""
from pathlib import Path
from datetime import date
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import status_panel


class StreakDates(unittest.TestCase):
    def test_english_us_uses_the_same_real_ranges_with_english_dates(self):
        summary = {'first_contribution':'2022-03-25',
                   'current_streak_range':{'start':'2026-10-19','end':'2026-10-22'},
                   'longest_streak_range':{'start':'2023-01-09','end':'2023-01-14'}}
        self.assertEqual(status_panel.streak_date_labels(summary, date(2026,10,22), locale='en-US'),
                         {'total':'Mar 25, 2022 — present','current':'Oct 19 — Oct 22',
                          'longest':'Jan 9, 2023 — Jan 14, 2023'})

    def test_reference_format_keeps_past_years_and_hides_redundant_current_year(self):
        formatter = getattr(status_panel, 'streak_date_labels', None)
        self.assertIsNotNone(formatter, 'The cards need actual contribution date labels')
        summary = {'first_contribution':'2022-03-25',
                   'current_streak_range':{'start':'2026-10-19','end':'2026-10-22'},
                   'longest_streak_range':{'start':'2023-01-09','end':'2023-01-14'}}
        self.assertEqual(formatter(summary, date(2026,10,22)),
                         {'total':'25 mar 2022 — atual','current':'19 out — 22 out',
                          'longest':'9 jan 2023 — 14 jan 2023'})

    def test_single_day_and_missing_ranges_are_not_fabricated(self):
        formatter = getattr(status_panel, 'streak_date_labels', None)
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter({'first_contribution':None, 'current_streak_range':None,
                                    'longest_streak_range':{'start':'2026-10-19','end':'2026-10-19'}}, date(2026,10,22)),
                         {'total':'—','current':'—','longest':'19 out'})
''',

    # ===== tests/test_streak_history.py =====
    'tests/test_streak_history.py': '''"""All-time streaks cross calendar years and do not accept incomplete snapshots."""
from pathlib import Path
from datetime import date
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class StreakHistory(unittest.TestCase):
    def test_complete_history_and_daily_cache_preserve_a_streak_across_years(self):
        from fetch_streak_history import collect_history
        from fetch_contributions import derive_stats
        previous = [{'date':'2025-12-30','count':1,'level':1}, {'date':'2025-12-31','count':1,'level':1}]
        cache = {'years':{'2025':{'checked_on':'2026-01-02','days':previous}}}
        calls = []
        def get_days(year):
            calls.append(year)
            self.assertEqual(year, 2026)
            return [{'date':'2026-01-01','count':5,'level':4}, {'date':'2026-01-02','count':0,'level':0}]
        result = collect_history(get_days, date(2025,12,30), date(2026,1,2), cache)
        self.assertEqual(calls, [2026])
        stats = derive_stats(result['days'], date(2026,1,2))
        self.assertEqual(stats['total'], 7)
        self.assertEqual(stats['current_streak'], 3)
        self.assertEqual(stats['longest_streak'], 3)
        self.assertEqual(stats.get('first_contribution'), '2025-12-30')
        self.assertEqual(stats.get('current_streak_range'), {'start':'2025-12-30','end':'2026-01-01'})
        self.assertEqual(stats.get('longest_streak_range'), {'start':'2025-12-30','end':'2026-01-01'})

    def test_equal_longest_runs_keep_first_range_and_current_run_stays_separate(self):
        from fetch_contributions import derive_stats
        days = [{'date':day,'count':1,'level':1} for day in
                ['2024-01-01','2024-01-02','2025-12-31','2026-01-01']]
        stats = derive_stats(days, date(2026,1,2))
        self.assertEqual(stats.get('first_contribution'), '2024-01-01')
        self.assertEqual(stats.get('longest_streak_range'), {'start':'2024-01-01','end':'2024-01-02'})
        self.assertEqual(stats.get('current_streak_range'), {'start':'2025-12-31','end':'2026-01-01'})

    def test_no_activity_has_no_invented_intervals(self):
        from fetch_contributions import derive_stats
        stats = derive_stats([{'date':'2026-01-01','count':0,'level':0},
                              {'date':'2026-01-02','count':3,'level':1}], date(2026,1,1))
        self.assertEqual(stats['total'], 0)
        self.assertIn('first_contribution', stats)
        self.assertIn('current_streak_range', stats)
        self.assertIn('longest_streak_range', stats)
        self.assertIsNone(stats.get('first_contribution'))
        self.assertIsNone(stats.get('current_streak_range'))
        self.assertIsNone(stats.get('longest_streak_range'))

    def test_incomplete_historical_year_is_rejected(self):
        from fetch_streak_history import collect_history
        with self.assertRaises(ValueError):
            collect_history(lambda year:[{'date':'2025-12-31','count':1,'level':1}],
                            date(2025,12,30), date(2026,1,2), {})
''',

    # ===== tests/test_theme_rendering.py =====
    'tests/test_theme_rendering.py': '''"""Exercise the shipped generator and the exact files deployed to Pages."""
from pathlib import Path
from html.parser import HTMLParser
import shutil, subprocess, sys, tempfile, unittest
from PIL import Image, ImageSequence
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ThemeRendering(unittest.TestCase):
    def test_profile_preserves_contacts_and_theme_assets_without_project_showcase(self):
        scratch = ROOT / 'work/theme-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'data', root / 'data')
            shutil.copytree(ROOT / 'assets/badges', root / 'assets/badges')
            for name in ['andre-ascii.png', 'andre-ascii.gif']:
                shutil.copy2(ROOT / 'assets' / name, root / 'assets' / name)
            calendar = json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
            # A controlled annual calendar makes animation/weight checks independent
            # of André's future activity. Production still renders the real data.
            for day in calendar['days']:day.update(count=0,level=0)
            for day,count,level in zip(calendar['days'][-4:],[1,3,8,21],[1,2,3,4]):
                day.update(count=count,level=level)
            (root/'data/contributions.json').write_text(json.dumps(calendar),encoding='utf-8')
            (root/'data/contributions-history.json').write_text(json.dumps(calendar), encoding='utf-8')
            subprocess.run([sys.executable, str(root / 'scripts/design.py')], check=True, capture_output=True)
            parsed = Elements((root / 'README.md').read_text(encoding='utf-8'))
            sources = [attrs for tag, attrs in parsed.tags if tag == 'source']
            self.assertTrue(any('prefers-color-scheme: dark' in s.get('media', '') for s in sources),
                            'The GitHub theme must choose the matching text colors')
            links = [attrs['href'] for tag, attrs in parsed.tags if tag == 'a']
            language_urls = ['https://github.com/andremellotech',
                             'https://github.com/andremellotech/andremellotech/blob/main/README.en-US.md']
            self.assertEqual(links[:2], language_urls, 'Both language buttons must work on GitHub')
            self.assertEqual(links[2:], ['https://www.linkedin.com/in/aamello/',
                                         'https://github.com/andremellotech?tab=repositories',
                                         'mailto:andremello@outlook.com'],
                             'All three contact buttons must keep the correct destinations')
            readme_text = (root / 'README.md').read_text(encoding='utf-8')
            self.assertNotIn('| Projeto | Aplicação |', readme_text)
            self.assertNotIn('Projetos em destaque', readme_text)
            self.assertNotIn('<table', (root/'previa.html').read_text(encoding='utf-8'))
            self.assertFalse(any('profile-project' in (a.get('src', '') + a.get('srcset', ''))
                                 for _, a in parsed.tags), 'Do not show repository image cards')
            self.assertFalse(any(tag == 'details' for tag, _ in parsed.tags))
            # The profile leads with live GitHub activity, not a duplicate resume.
            panels = [a['src'] for tag, a in parsed.tags if tag == 'img' and a.get('width') == '100%']
            self.assertEqual([url.split('/')[-1].split('-light.')[0] for url in panels],
                             ['profile-intro', 'status', 'activity', 'stack'])
            for resume_text in ['KPMG', '660 milhões', 'UFPR', 'Mestre em Administração', 'FAPESP']:
                self.assertNotIn(resume_text, readme_text, 'Career details belong on LinkedIn')
            for english in ['Total Contributions', 'Current Streak', 'Longest Streak', 'Present', 'Data & Analytics', 'MSc.']:
                self.assertNotIn(english, readme_text)
            portrait_sources = [s for s in sources if 'profile-intro-' in s.get('srcset', '')]
            self.assertEqual(len(portrait_sources), 2, 'A single animated introduction adapts to both themes')
            self.assertTrue(all('.gif?' in s['srcset'] for s in portrait_sources),
                            'The requested animation must remain selected on this reduced-motion computer')
            for theme in ['light', 'dark']:
                animation = root / f'assets/profile-intro-{theme}.gif'
                self.assertTrue(animation.exists(), 'The portrait must animate on the profile itself')
                with Image.open(animation) as gif:
                    self.assertGreater(gif.n_frames, 1)
                    self.assertEqual(gif.info.get('loop'), 0, 'The animation must repeat')
                    first = gif.convert('RGBA')
                    self.assertEqual(first.getpixel((0, 0))[3], 0, 'No rectangular background')
                    portraits, text = set(), set()
                    for frame in ImageSequence.Iterator(gif):
                        rgba = frame.convert('RGBA')
                        portraits.add(hashlib.sha256(rgba.crop((850, 18, 1140, 382)).tobytes()).hexdigest())
                        text.add(hashlib.sha256(rgba.crop((0, 0, 740, rgba.height)).tobytes()).hexdigest())
                    self.assertGreater(len(portraits), 1, 'The portrait must move')
                    self.assertEqual(len(text), 1, 'Text must stay stable')
                    gif.seek(0)
                    duration = sum(frame.info.get('duration', 100) for frame in ImageSequence.Iterator(gif))
                with Image.open(root / 'assets/andre-ascii.gif') as original:
                    source_duration = sum(frame.info.get('duration', 100) for frame in ImageSequence.Iterator(original))
                self.assertAlmostEqual(duration, source_duration, delta=20, msg='Preserve the original animation pace')
                self.assertLess(animation.stat().st_size, 1_000_000, 'Keep the corporate proxy payload below 1 MB')
                self.assertTrue(any(f'profile-intro-{theme}.gif' in s.get('srcset', '') for s in sources))
                with Image.open(root / f'assets/activity-{theme}.png') as city:
                    self.assertEqual(city.size,(1200,918),'One card contains metrics and the full annual Aurora city')
                    self.assertEqual(city.mode,'RGBA')
                    self.assertEqual(city.getpixel((0,0))[3],0)
                self.assertLess((root / f'assets/activity-{theme}.png').stat().st_size, 1_000_000)
                city_animation = root / f'assets/activity-{theme}.gif'
                self.assertTrue(city_animation.exists(),'The annual city must animate on the profile itself')
                with Image.open(city_animation) as gif:
                    self.assertEqual(gif.size,(1200,918))
                    self.assertGreaterEqual(gif.n_frames,24,'The city needs a smooth visible animation')
                    self.assertEqual(gif.info.get('loop'),0,'The city must restart without reloading the profile')
                    durations=[frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
                    self.assertEqual(sum(durations),10000,'A complete construction cycle must last ten seconds')
                    self.assertEqual(sum(durations[:-1]),3000,'Keep the three-second construction pace')
                    self.assertEqual(durations[-1],7000,'Keep the completed city visible for seven seconds')
                    gif.seek(0)
                    titles,labels,city_frames,floor_frames=set(),set(),set(),set()
                    for frame in ImageSequence.Iterator(gif):
                        rgba=frame.convert('RGBA')
                        self.assertEqual(rgba.getpixel((0,0))[3],0)
                        self.assertEqual(rgba.getpixel((70,370))[:3],
                                         (255,255,255) if theme=='light' else (13,17,23),
                                         'The city backdrop must match the rest of the profile')
                        titles.add(hashlib.sha256(rgba.crop((0,0,1200,354)).tobytes()).hexdigest())
                        labels.add(hashlib.sha256(rgba.crop((44,354,330,918)).tobytes()).hexdigest())
                        city_frames.add(hashlib.sha256(rgba.crop((340,354,1176,906)).tobytes()).hexdigest())
                        floor_frames.add(hashlib.sha256(rgba.crop((390,430,490,460)).tobytes()).hexdigest())
                    self.assertEqual(len(titles),1,'Contribution numbers and heading cannot move or flicker')
                    self.assertEqual(len(labels),1,'The city summary must stay fixed')
                    self.assertGreater(len(city_frames),12,'The city itself must visibly move')
                    self.assertEqual(len(floor_frames),1,'The annual floor must not rotate or wobble')
                    github_colors=(['#aceebb','#4ac26b','#2da44e','#116329'] if theme=='light'
                                   else ['#033a16','#196c2e','#2ea043','#56d364'])
                    final_image=rgba.crop((340,354,1176,906)).convert('RGB')
                    final_colors={color for _,color in final_image.getcolors(maxcolors=final_image.width*final_image.height)}
                    for color in github_colors:
                        self.assertIn(tuple(bytes.fromhex(color[1:])),final_colors,'Keep each GitHub level exact')
                self.assertLess(city_animation.stat().st_size,1_000_000,'Keep the corporate payload below 1 MB')
                self.assertTrue(any(f'activity-{theme}.gif' in s.get('srcset', '') for s in sources))
            self.assertNotIn('contribution-snake',readme_text)
            self.assertNotIn('cobrinha',readme_text)
            self.assertIn('últimos 12 meses',readme_text)
            images = []
            for theme in ['light', 'dark']:
                path = root / f'assets/profile-card-{theme}.png'
                self.assertTrue(path.exists(), f'Missing {theme} profile image')
                with Image.open(path) as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.getpixel((0, 0))[3], 0, 'Page background must remain visible')
                    with Image.open(root/f'assets/intro-background-{theme}.png') as intro:
                        self.assertEqual(intro.size, (1200, 304), 'Keep the introduction compact')
                        self.assertEqual(im.getpixel((600, intro.height+14))[3], 0,
                                         'Section spacing must stay transparent')
                    images.append(im.copy())
            self.assertEqual(images[0].size, images[1].size)
            self.assertNotEqual(images[0].tobytes(), images[1].tobytes(), 'Text must adapt to the selected theme')
            badge_images = [attrs['src'] for tag, attrs in parsed.tags if tag == 'img' and attrs.get('height') == '22']
            self.assertEqual(len(badge_images), 3, 'Three contact badges without duplicated statistics')
            for name in ['badge-linkedin.png', 'badge-github.png', 'badge-email.png']:
                with Image.open(root / 'assets' / name) as im:
                    self.assertEqual(im.height, 56, 'Contact source images stay sharp at the compact display height')
                    self.assertEqual(im.getpixel((0, 0))[3], 0, 'Rounded corners stay transparent')
            with Image.open(root / 'assets/status-light.png') as im:
                self.assertEqual(im.size, (1200, 344),'Streaks belong to the activity card, without duplication')
            self.assertIn('Atividade e contribuições: contribuições totais',readme_text)
            self.assertNotIn('composição de código dos repositórios; total de contribuições',readme_text)
            for theme in ['light', 'dark']:
                with Image.open(root / f'assets/stack-{theme}.png') as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.width, 1200)
                    self.assertLessEqual(im.height, 1100, 'The expanded stack stays compact and excludes the academic resume')
                    self.assertEqual(im.getpixel((0, 0))[3], 0)
            subprocess.run([sys.executable, str(root / 'scripts/prepare_pages.py')], check=True, capture_output=True)
            english = Elements((root/'README.en-US.md').read_text(encoding='utf-8'))
            self.assertEqual([a['href'] for tag, a in english.tags if tag == 'a'], links,
                             'English must return to the Portuguese profile and keep contact links')
            english_panels = [a['src'] for tag, a in english.tags if tag == 'img' and a.get('width') == '100%']
            self.assertEqual(len(english_panels), 4)
            self.assertTrue(all('-en-US-' in url for url in english_panels),
                            'English needs translated pictures, not only an English heading')
            english_readme = (root/'README.en-US.md').read_text(encoding='utf-8')
            self.assertIn('Data and automation in practice.', english_readme)
            self.assertNotIn('Experience and results', english_readme)
            self.assertNotIn('KPMG', english_readme)
            self.assertNotIn('Tecnologias e formação', english_readme)
            for theme in ['light', 'dark']:
                for stem in ['profile-intro','activity']:
                    with Image.open(root/f'assets/{stem}-en-US-{theme}.gif') as gif:
                        self.assertGreater(gif.n_frames, 1)
                        self.assertEqual(gif.info.get('loop'),0)
                        self.assertEqual(gif.convert('RGBA').getpixel((0,0))[3], 0)
                        if stem=='activity':
                            durations=[frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
                            self.assertEqual(sum(durations),10000)
                            self.assertEqual(durations[-1],7000)
                with Image.open(root/f'assets/activity-en-US-{theme}.png') as city:
                    self.assertEqual(city.size,(1200,918))
                self.assertIn('last 12 months',english_readme)
                with Image.open(root/f'assets/status-{theme}.png') as pt, Image.open(root/f'assets/status-en-US-{theme}.png') as en:
                    self.assertEqual(pt.size, en.size, 'Both languages keep the same proportions')
                    self.assertNotEqual(pt.tobytes(), en.tobytes(), 'The card text must actually be translated')
            self.assertTrue((root/'work/pages/en-US/index.html').exists())
            for tag, attrs in parsed.tags + english.tags:
                url = attrs.get('src') or attrs.get('srcset')
                if url:
                    self.assertTrue(url.startswith('https://andremellotech.github.io/andremellotech/assets/'))
                    name = url.split('/')[-1].split('?')[0]
                    self.assertTrue((root / 'work/pages/assets' / name).exists(), f'{name} must deploy before the README')


if __name__ == '__main__':
    unittest.main()
''',

    # ===== scripts/requirements.txt =====
    'scripts/requirements.txt': '''pillow>=11,<13
requests>=2.32.3,<3
beautifulsoup4>=4.12.3,<5
''',

    # ===== templates/notify-profile.yml =====
    'templates/notify-profile.yml': '''# Copie este arquivo para .github/workflows/notify-profile.yml em cada repositório
# que deve atualizar o perfil quando receber um push.
# Requer o segredo PROFILE_DISPATCH_TOKEN (veja COMO-USAR.md, "Atualização por evento").
name: Avisar o perfil
on:
  push:
    branches: [main]      # ajuste se a branch padrão tiver outro nome
  workflow_dispatch:
permissions: {}
jobs:
  notify:
    runs-on: ubuntu-24.04
    timeout-minutes: 2
    steps:
      - name: Disparar a atualização do perfil
        env:
          TOKEN: ${{ secrets.PROFILE_DISPATCH_TOKEN }}
          SOURCE_REPO: ${{ github.repository }}
        run: |
          if [ "$SOURCE_REPO" = "andremellotech/andremellotech" ]; then
            echo "O próprio perfil já atualiza por push."
            exit 0
          fi
          if [ -z "$TOKEN" ]; then
            echo "::warning::Segredo PROFILE_DISPATCH_TOKEN ausente; o perfil será atualizado pelo agendamento."
            exit 0
          fi
          curl -fsS --retry 2 --retry-delay 5 --retry-max-time 60 --connect-timeout 10 --max-time 20 -X POST \\
            -H "Accept: application/vnd.github+json" \\
            -H "Authorization: Bearer $TOKEN" \\
            -H "X-GitHub-Api-Version: 2022-11-28" \\
            https://api.github.com/repos/andremellotech/andremellotech/dispatches \\
            -d "{\\"event_type\\":\\"repo-updated\\",\\"client_payload\\":{\\"repo\\":\\"$SOURCE_REPO\\"}}"
''',

    # ===== profile.json =====
    'profile.json': '''{
  "username": "andremellotech",
  "name": "André Mello",
  "focus": [
    "Performance & Analytics",
    "Engineering & Automation",
    "Financial Modeling"
  ],
  "stack": [
    "Power BI",
    "Python",
    "Excel",
    "Alteryx",
    "SAP",
    "PowerPoint",
    "HTML",
    "GitHub"
  ],
  "source": "https://api.github.com/users/andremellotech",
  "productivity_suite": "Office 365",
  "language_knowledge": ["HTML", "CSS", "JavaScript", "Lua"],
  "previous_experience": {
    "MySQL": "Desenvolvimento de servidores de Tibia e GTA V / FiveM"
  }
}
''',

    # ===== data/language-colors.json =====
    'data/language-colors.json': '''{
  "source": "https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml",
  "retrieved_on": "2026-10-23",
  "colors": {
    "1C Enterprise": "#814CCC",
    "2-Dimensional Array": "#38761D",
    "4D": "#004289",
    "ABAP": "#E8274B",
    "ABAP CDS": "#555e25",
    "AGS Script": "#B9D9FF",
    "AIDL": "#34EB6B",
    "AL": "#3AA2B5",
    "ALGOL": "#D1E0DB",
    "AMPL": "#E6EFBB",
    "ANTLR": "#9DC3FF",
    "API Blueprint": "#2ACCA8",
    "APL": "#5A8164",
    "ASP.NET": "#9400ff",
    "ATS": "#1ac620",
    "ActionScript": "#882B0F",
    "Ada": "#02f88c",
    "Adblock Filter List": "#800000",
    "Adobe Font Metrics": "#fa0f00",
    "Agda": "#315665",
    "Aiken": "#640ff8",
    "Aleo": "#154BF9",
    "Alloy": "#64C800",
    "Alpine Abuild": "#0D597F",
    "Altium Designer": "#A89663",
    "AngelScript": "#C7D7DC",
    "Answer Set Programming": "#A9CC29",
    "Ant Build System": "#A9157E",
    "Antlers": "#ff269e",
    "ApacheConf": "#d12127",
    "Apex": "#1797c0",
    "Apollo Guidance Computer": "#0B3D91",
    "AppleScript": "#101F1F",
    "Arc": "#aa2afe",
    "ArkTS": "#0080ff",
    "AsciiDoc": "#73a0c5",
    "AspectJ": "#a957b0",
    "Assembly": "#6E4C13",
    "Astro": "#ff5a03",
    "Asymptote": "#ff0000",
    "Augeas": "#9CC134",
    "AutoHotkey": "#6594b9",
    "AutoIt": "#1C3552",
    "Avro IDL": "#0040FF",
    "Awk": "#c30e9b",
    "B": "#da7666",
    "B (Formal Method)": "#8aa8c5",
    "B4X": "#00e4ff",
    "BAML": "#a855f7",
    "BASIC": "#ff0000",
    "BBCode": "#CAFF42",
    "BIRD2": "#b6d7e4",
    "BQN": "#2b7067",
    "Ballerina": "#FF5000",
    "Batchfile": "#C1F12E",
    "Beef": "#a52f4e",
    "Berry": "#15A13C",
    "BibTeX": "#778899",
    "Bicep": "#519aba",
    "Bikeshed": "#5562ac",
    "Bison": "#6A463F",
    "BitBake": "#00bce4",
    "Blade": "#f7523f",
    "BlitzBasic": "#00FFAE",
    "BlitzMax": "#cd6400",
    "Blueprint": "#3584E4",
    "Bluespec": "#12223c",
    "Bluespec BH": "#12223c",
    "Boo": "#d4bec1",
    "Boogie": "#c80fa0",
    "Brainfuck": "#2F2530",
    "BrighterScript": "#66AABB",
    "Brightscript": "#662D91",
    "Browserslist": "#ffd539",
    "Bru": "#F4AA41",
    "BuildStream": "#006bff",
    "C": "#555555",
    "C#": "#7355dd",
    "C++": "#f34b7d",
    "C3": "#2563eb",
    "CAP CDS": "#0092d1",
    "CLIPS": "#00A300",
    "CMake": "#DA3434",
    "COLLADA": "#F1A42B",
    "CQL": "#006091",
    "CSON": "#244776",
    "CSS": "#663399",
    "CSV": "#237346",
    "CUE": "#5886E1",
    "CWeb": "#00007a",
    "Cabal Config": "#483465",
    "Caddyfile": "#22b638",
    "Cadence": "#00ef8b",
    "Cairo": "#ff4a48",
    "Cairo Zero": "#ff4a48",
    "CameLIGO": "#3be133",
    "Cangjie": "#00868B",
    "Cap'n Proto": "#c42727",
    "Carbon": "#222222",
    "Ceylon": "#dfa535",
    "Chapel": "#8dc63f",
    "ChucK": "#3f8000",
    "Circom": "#707575",
    "Cirru": "#ccccff",
    "Clarion": "#db901e",
    "Clarity": "#5546ff",
    "Classic ASP": "#6a40fd",
    "Clean": "#3F85AF",
    "Click": "#E4E6F3",
    "Clojure": "#db5855",
    "Closure Templates": "#0d948f",
    "Cloud Firestore Security Rules": "#FFA000",
    "Clue": "#0009b5",
    "CodeQL": "#140f46",
    "CoffeeScript": "#244776",
    "ColdFusion": "#ed2cd6",
    "ColdFusion CFC": "#ed2cd6",
    "Common Lisp": "#3fb68b",
    "Common Workflow Language": "#B5314C",
    "Component Pascal": "#B0CE4E",
    "Cooklang": "#E15A29",
    "Crystal": "#000100",
    "Csound": "#1a1a1a",
    "Csound Document": "#1a1a1a",
    "Csound Score": "#1a1a1a",
    "Cuda": "#3A4E3A",
    "Curry": "#531242",
    "Cylc": "#00b3fd",
    "Cypher": "#34c0eb",
    "Cython": "#fedf5b",
    "D": "#ba595e",
    "D2": "#526ee8",
    "DM": "#447265",
    "Dafny": "#FFEC25",
    "Darcs Patch": "#8eff23",
    "Dart": "#00B4AB",
    "Daslang": "#d3d3d3",
    "DataWeave": "#003a52",
    "Debian Package Control File": "#D70751",
    "DenizenScript": "#FBEE96",
    "Dhall": "#dfafff",
    "DirectX 3D File": "#aace60",
    "Dockerfile": "#384d54",
    "Dogescript": "#cca760",
    "Dotenv": "#e5d559",
    "Dune": "#89421e",
    "Dylan": "#6c616e",
    "E": "#ccce35",
    "ECL": "#8a1267",
    "ECLiPSe": "#001d9d",
    "EJS": "#a91e50",
    "EQ": "#a78649",
    "Earthly": "#2af0ff",
    "Easybuild": "#069406",
    "Ecere Projects": "#913960",
    "Ecmarkup": "#eb8131",
    "Edge": "#0dffe0",
    "EdgeQL": "#31A7FF",
    "EditorConfig": "#fff1f2",
    "Eiffel": "#4d6977",
    "Elixir": "#8847B9",
    "Elm": "#60B5CC",
    "Elvish": "#55BB55",
    "Elvish Transcript": "#55BB55",
    "Emacs Lisp": "#c065db",
    "EmberScript": "#FFF4F3",
    "Erlang": "#B83998",
    "Euphoria": "#FF790B",
    "F#": "#b845fc",
    "F*": "#572e30",
    "FIGlet Font": "#FFDDBB",
    "FIRRTL": "#2f632f",
    "FLUX": "#88ccff",
    "FPP": "#d37327",
    "Factor": "#636746",
    "Fancy": "#7b9db4",
    "Fantom": "#14253c",
    "Faust": "#c37240",
    "Fennel": "#fff3d7",
    "Filebench WML": "#F6B900",
    "FlatBuffers": "#ed284a",
    "Flix": "#d44a45",
    "Fluent": "#ffcc33",
    "Forth": "#341708",
    "Fortran": "#4d41b1",
    "Fortran Free Form": "#4d41b1",
    "FreeBASIC": "#141AC9",
    "FreeMarker": "#0050b2",
    "Frege": "#00cafe",
    "Futhark": "#5f021f",
    "G-code": "#D08CF2",
    "GAML": "#FFC766",
    "GAMS": "#f49a22",
    "GAP": "#0000cc",
    "GCC Machine Description": "#FFCFAB",
    "GDScript": "#355570",
    "GDShader": "#478CBF",
    "GEDCOM": "#003058",
    "GLSL": "#5686a5",
    "GSC": "#FF6800",
    "Game Maker Language": "#71b417",
    "Gemfile.lock": "#701516",
    "Gemini": "#ff6900",
    "Genero 4gl": "#63408e",
    "Genero per": "#d8df39",
    "Genie": "#fb855d",
    "Genshi": "#951531",
    "Gentoo Ebuild": "#9400ff",
    "Gentoo Eclass": "#9400ff",
    "Gerber Image": "#d20b00",
    "Gherkin": "#5B2063",
    "Git Attributes": "#F44D27",
    "Git Commit": "#F44D27",
    "Git Config": "#F44D27",
    "Git Revision List": "#F44D27",
    "Gleam": "#ffaff3",
    "Glimmer JS": "#F5835F",
    "Glimmer TS": "#3178c6",
    "Glyph": "#c1ac7f",
    "Gno": "#226c57",
    "Gnuplot": "#f0a9f0",
    "Go": "#00ADD8",
    "Go Checksums": "#00ADD8",
    "Go Module": "#00ADD8",
    "Go Template": "#00ADD8",
    "Go Workspace": "#00ADD8",
    "Godot Resource": "#355570",
    "Golo": "#88562A",
    "Gosu": "#82937f",
    "Grace": "#615f8b",
    "Gradle": "#02303a",
    "Gradle Kotlin DSL": "#02303a",
    "Grammatical Framework": "#ff0000",
    "GraphQL": "#e10098",
    "Graphviz (DOT)": "#2596be",
    "Groovy": "#4298b8",
    "Groovy Server Pages": "#4298b8",
    "GtkRC": "#7fe719",
    "HAProxy": "#106da9",
    "HCL": "#844FBA",
    "HIP": "#4F3A4F",
    "HLSL": "#aace60",
    "HOCON": "#9ff8ee",
    "HTML": "#e34c26",
    "HTML+ECR": "#2e1052",
    "HTML+EEX": "#6e4a7e",
    "HTML+ERB": "#701516",
    "HTML+PHP": "#4f5d95",
    "HTML+Razor": "#512be4",
    "HTTP": "#005C9C",
    "HXML": "#f68712",
    "Hack": "#878787",
    "Haml": "#ece2a9",
    "Handlebars": "#f7931e",
    "Harbour": "#0e60e3",
    "Hare": "#9d7424",
    "Haskell": "#5e5086",
    "Haxe": "#df7900",
    "HiveQL": "#dce200",
    "HolyC": "#ffefaf",
    "Hosts File": "#308888",
    "Hurl": "#FF0288",
    "Hy": "#7790B2",
    "IDL": "#a3522f",
    "IGOR Pro": "#0000cc",
    "IL Assembly": "#512BD4",
    "INI": "#d1dbe0",
    "ISPC": "#2D68B1",
    "Idris": "#b30000",
    "Ignore List": "#000000",
    "ImHex Pattern Language": "#3a6be0",
    "ImageJ Macro": "#99AAFF",
    "Imba": "#16cec6",
    "Inno Setup": "#264b99",
    "Io": "#a9188d",
    "Ioke": "#078193",
    "Isabelle": "#FEFE00",
    "Isabelle ROOT": "#FEFE00",
    "J": "#9EEDFF",
    "JAR Manifest": "#b07219",
    "JASS": "#FF0303",
    "JCL": "#d90e09",
    "JFlex": "#DBCA00",
    "JSON": "#292929",
    "JSON with Comments": "#292929",
    "JSON5": "#267CB9",
    "JSONLD": "#0c479c",
    "JSONiq": "#40d47e",
    "Jac": "#FC792D",
    "Jai": "#ab8b4b",
    "Janet": "#0886a5",
    "Jasmin": "#d03600",
    "Java": "#b07219",
    "Java Properties": "#2A6277",
    "Java Server Pages": "#2A6277",
    "Java Template Engine": "#2A6277",
    "JavaScript": "#f1e05a",
    "JavaScript+ERB": "#f1e05a",
    "Jest Snapshot": "#15c213",
    "JetBrains MPS": "#21D789",
    "Jinja": "#a52a22",
    "Jison": "#56b3cb",
    "Jison Lex": "#56b3cb",
    "Jolie": "#843179",
    "Jsonnet": "#0064bd",
    "Julia": "#a270ba",
    "Julia REPL": "#a270ba",
    "Jupyter Notebook": "#DA5B0B",
    "Just": "#384d54",
    "KCL": "#7ABABF",
    "KDL": "#ffb3b3",
    "KFramework": "#4195c5",
    "KRL": "#28430A",
    "Kaitai Struct": "#773b37",
    "KakouneScript": "#6f8042",
    "KerboScript": "#41adf0",
    "KiCad Layout": "#2f4aab",
    "KiCad Legacy Layout": "#2f4aab",
    "KiCad Schematic": "#2f4aab",
    "KoLmafia ASH": "#B9D9B9",
    "Koka": "#215166",
    "Kotlin": "#A97BFF",
    "LFE": "#4C3023",
    "LLVM": "#185619",
    "LLVM TableGen": "#6E8B3D",
    "LOLCODE": "#cc9900",
    "LSL": "#3d9970",
    "LabVIEW": "#fede06",
    "Lambdapi": "#8027a3",
    "Langium": "#2c8c87",
    "Lark": "#2980B9",
    "Lasso": "#999999",
    "Latte": "#f2a542",
    "Leo": "#C4FFC2",
    "Less": "#1d365d",
    "Lex": "#DBCA00",
    "LigoLANG": "#0e74ff",
    "LilyPond": "#9ccc7c",
    "Liquid": "#67b8de",
    "Liquidsoap": "#990066",
    "Literate Agda": "#315665",
    "Literate CoffeeScript": "#244776",
    "Literate Haskell": "#5e5086",
    "LiveCode Script": "#0c5ba5",
    "LiveScript": "#499886",
    "Lobster": "#f95428",
    "Logtalk": "#295b9a",
    "LookML": "#652B81",
    "Lua": "#000080",
    "Luau": "#00A2FF",
    "M3U": "#179C7D",
    "MATLAB": "#e16737",
    "MAXScript": "#00a6a6",
    "MDX": "#fcb32c",
    "MLIR": "#5EC8DB",
    "MQL4": "#62A8D6",
    "MQL5": "#4A76B8",
    "MTML": "#b7e1f4",
    "Macaulay2": "#d8ffff",
    "Makefile": "#427819",
    "Mako": "#7e858d",
    "Markdown": "#083fa1",
    "Marko": "#42bff2",
    "Mask": "#f97732",
    "Mathematical Programming System": "#0530ad",
    "Max": "#c4a79c",
    "MeTTa": "#6a5acd",
    "Mercury": "#ff2b2b",
    "Mermaid": "#ff3670",
    "Meson": "#007800",
    "Metal": "#8f14e9",
    "MiniScript": "#4B4A56",
    "MiniYAML": "#ff1111",
    "MiniZinc": "#06a9e6",
    "Mint": "#02b046",
    "Mirah": "#c7a938",
    "Modelica": "#de1d31",
    "Modula-2": "#10253f",
    "Modula-3": "#223388",
    "Mojo": "#ff4c1f",
    "Monkey C": "#8D6747",
    "MoonBit": "#b92381",
    "MoonScript": "#ff4585",
    "Motoko": "#fbb03b",
    "Motorola 68K Assembly": "#005daa",
    "Move": "#4a137a",
    "Mustache": "#724b3b",
    "NCL": "#28431f",
    "NMODL": "#00356B",
    "NPM Config": "#cb3837",
    "NWScript": "#111522",
    "Nasal": "#1d2c4e",
    "Nearley": "#990000",
    "Nemerle": "#3d3c6e",
    "NetLinx": "#0aa0ff",
    "NetLinx+ERB": "#747faa",
    "NetLogo": "#ff6375",
    "NewLisp": "#87AED7",
    "Nextflow": "#3ac486",
    "Nginx": "#009639",
    "Nickel": "#E0C3FC",
    "Nim": "#ffc200",
    "Nit": "#009917",
    "Nix": "#7e7eff",
    "Noir": "#2f1f49",
    "Nu": "#c9df40",
    "NumPy": "#9C8AF9",
    "Nunjucks": "#3d8137",
    "Nushell": "#4E9906",
    "OASv2-json": "#85ea2d",
    "OASv2-yaml": "#85ea2d",
    "OASv3-json": "#85ea2d",
    "OASv3-yaml": "#85ea2d",
    "OCaml": "#ef7a08",
    "OMNeT++ MSG": "#a0e0a0",
    "OMNeT++ NED": "#08607c",
    "ObjectScript": "#424893",
    "Objective-C": "#438eff",
    "Objective-C++": "#6866fb",
    "Objective-J": "#ff0c5a",
    "Odin": "#60AFFE",
    "Omgrofl": "#cabbff",
    "Opal": "#f7ede0",
    "Open Policy Agent": "#7d9199",
    "OpenAPI Specification v2": "#85ea2d",
    "OpenAPI Specification v3": "#85ea2d",
    "OpenCL": "#ed2e2d",
    "OpenEdge ABL": "#5ce600",
    "OpenQASM": "#AA70FF",
    "OpenSCAD": "#e5cd45",
    "Option List": "#476732",
    "Org": "#77aa99",
    "OverPy": "#78b355",
    "OverpassQL": "#cce2aa",
    "Oxygene": "#cdd0e3",
    "Oz": "#fab738",
    "P4": "#7055b5",
    "PDDL": "#0d00ff",
    "PEG.js": "#234d6b",
    "PHP": "#4F5D95",
    "PLSQL": "#dad8d8",
    "PLpgSQL": "#336790",
    "POV-Ray SDL": "#6bac65",
    "Pact": "#F7A8B8",
    "Pan": "#cc0000",
    "Papyrus": "#6600cc",
    "Parrot": "#f3ca0a",
    "Pascal": "#E3F171",
    "Pawn": "#dbb284",
    "Pep8": "#C76F5B",
    "Perl": "#0298c3",
    "PicoLisp": "#6067af",
    "PigLatin": "#fcd7de",
    "Pike": "#005390",
    "Pip Requirements": "#FFD343",
    "Pkl": "#6b9543",
    "PlantUML": "#fbbd16",
    "PogoScript": "#d80074",
    "Polar": "#ae81ff",
    "Portugol": "#f8bd00",
    "PostCSS": "#dc3a0c",
    "PostScript": "#da291c",
    "Power Query": "#d38e0d",
    "PowerBuilder": "#8f0f8d",
    "PowerShell": "#012456",
    "Praat": "#c8506d",
    "Prisma": "#0c344b",
    "Pro*C": "#bb8368",
    "Processing": "#0096D8",
    "Procfile": "#3B2F63",
    "Prolog": "#74283c",
    "Promela": "#de0000",
    "Propeller Spin": "#7fa2a7",
    "Pug": "#a86454",
    "Puppet": "#302B6D",
    "PureBasic": "#5a6986",
    "PureScript": "#1D222D",
    "Pyret": "#ee1e10",
    "Python": "#3572A5",
    "Python console": "#3572A5",
    "Python traceback": "#3572A5",
    "Q#": "#fed659",
    "QML": "#44a51c",
    "Qt Script": "#00b841",
    "Quake": "#882233",
    "QuakeC": "#975777",
    "Quartus Simulation IP": "#58C42E",
    "QuickBASIC": "#008080",
    "Quint": "#9d6ce5",
    "R": "#198CE7",
    "RAML": "#77d9fb",
    "RAScript": "#2C97FA",
    "RBS": "#701516",
    "RDoc": "#701516",
    "REXX": "#d90e09",
    "RMarkdown": "#198ce7",
    "RON": "#a62c00",
    "ROS Interface": "#22314e",
    "RPGLE": "#2BDE21",
    "RUNOFF": "#665a4e",
    "Racket": "#3c5caa",
    "Ragel": "#9d5200",
    "Raku": "#0000fb",
    "Rascal": "#fffaa0",
    "ReScript": "#ed5051",
    "Reason": "#ff5847",
    "ReasonLIGO": "#ff5847",
    "Rebol": "#358a5b",
    "Record Jar": "#0673ba",
    "Red": "#f50000",
    "Redscript": "#f44336",
    "Regular Expression": "#009a00",
    "Ren'Py": "#ff7f7f",
    "Rez": "#FFDAB3",
    "Rhai": "#FBA63B",
    "Ring": "#2D54CB",
    "Riot": "#A71E49",
    "RobotFramework": "#00c0b5",
    "Roc": "#7c38f5",
    "Rocq Prover": "#d0b68c",
    "Roff": "#ecdebe",
    "Roff Manpage": "#ecdebe",
    "Rouge": "#cc0088",
    "RouterOS Script": "#DE3941",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "SAS": "#B34936",
    "SCSS": "#c6538c",
    "SIP": "#4E8D83",
    "SPARQL": "#0C4597",
    "SQF": "#3F3F3F",
    "SQL": "#e38c00",
    "SQLPL": "#e38c00",
    "SRecode Template": "#348a34",
    "STL": "#373b5e",
    "SVG": "#ff9900",
    "Sail": "#259dd5",
    "Salt": "#57bcad",
    "Sass": "#a53b70",
    "Scala": "#c22d40",
    "Scaml": "#bd181a",
    "Scenic": "#fdc700",
    "Scheme": "#1e4aec",
    "Scilab": "#ca0f21",
    "Self": "#0579aa",
    "ShaderLab": "#222c37",
    "Shell": "#89e051",
    "ShellCheck Config": "#cecfcb",
    "Shen": "#120F14",
    "Simple File Verification": "#C9BFED",
    "Singularity": "#64E6AD",
    "Slang": "#1fbec9",
    "Slash": "#007eff",
    "Slice": "#003fa2",
    "Slim": "#2b2b2b",
    "Slint": "#2379F4",
    "SmPL": "#c94949",
    "Smalltalk": "#596706",
    "Smarty": "#f0c040",
    "Smithy": "#c44536",
    "Snakemake": "#419179",
    "Solidity": "#AA6746",
    "SourcePawn": "#f69e1d",
    "SpiceDB Schema": "#a5318a",
    "Squirrel": "#800000",
    "Stan": "#b2011d",
    "Standard ML": "#dc566d",
    "Starlark": "#76d275",
    "Stata": "#1a5f91",
    "StringTemplate": "#3fb34f",
    "Stylus": "#ff6347",
    "SubRip Text": "#9e0101",
    "SugarSS": "#2fcc9f",
    "SuperCollider": "#46390b",
    "SurrealQL": "#ff00a0",
    "Survex data": "#ffcc99",
    "Svelte": "#ff3e00",
    "Sway": "#00F58C",
    "Sweave": "#198ce7",
    "Swift": "#F05138",
    "SystemVerilog": "#DAE1C2",
    "TI Program": "#A0AA87",
    "TL-Verilog": "#C40023",
    "TLA": "#4b0079",
    "TMDL": "#f0c913",
    "TOML": "#9c4221",
    "TSQL": "#e38c00",
    "TSV": "#237346",
    "TSX": "#3178c6",
    "TXL": "#0178b8",
    "Tact": "#48b5ff",
    "Talon": "#333333",
    "Tcl": "#e4cc98",
    "TeX": "#3D6117",
    "Teal": "#00B1BC",
    "Terra": "#00004c",
    "Terraform Template": "#7b42bb",
    "TextGrid": "#c8506d",
    "TextMate Properties": "#df66e4",
    "Textile": "#ffe7ac",
    "Thrift": "#D12127",
    "Toit": "#c2c9fb",
    "Tolk": "#30A1F5",
    "Tor Config": "#59316b",
    "Tree-sitter Query": "#8ea64c",
    "Turing": "#cf142b",
    "Twig": "#c1d026",
    "TypeScript": "#3178c6",
    "TypeSpec": "#4A3665",
    "Typst": "#239dad",
    "Unified Parallel C": "#4e3617",
    "Unity3D Asset": "#222c37",
    "Uno": "#9933cc",
    "UnrealScript": "#a54c4d",
    "Untyped Plutus Core": "#36adbd",
    "UrWeb": "#ccccee",
    "V": "#4f87c4",
    "VBA": "#867db1",
    "VBScript": "#15dcdc",
    "VCL": "#148AA8",
    "VHDL": "#adb2cb",
    "Vala": "#a56de2",
    "Valve Data Format": "#f26025",
    "Velocity Template Language": "#507cff",
    "Vento": "#ff0080",
    "Verilog": "#b2b7f8",
    "Verse": "#518ef8",
    "Vespa Schema Definition": "#61D790",
    "Vim Help File": "#199f4b",
    "Vim Snippet": "#199f4b",
    "Vim script": "#199f4b",
    "Visual Basic .NET": "#945db7",
    "Visual Basic 6.0": "#2c6353",
    "Volt": "#1F1F1F",
    "Vue": "#41b883",
    "Vyper": "#9F4CF2",
    "WDL": "#42f1f4",
    "WGSL": "#1a5e9a",
    "Web Ontology Language": "#5b70bd",
    "WebAssembly": "#04133b",
    "WebAssembly Interface Type": "#6250e7",
    "Whiley": "#d5c397",
    "Wikitext": "#fc5757",
    "Windows Registry Entries": "#52d5ff",
    "Witcher Script": "#ff0000",
    "Wolfram Language": "#dd1100",
    "Wollok": "#a23738",
    "World of Warcraft Addon Data": "#f7e43f",
    "Wren": "#383838",
    "X10": "#4B6BEF",
    "XC": "#99DA07",
    "XML": "#0060ac",
    "XML Property List": "#0060ac",
    "XQuery": "#5232e7",
    "XSLT": "#EB8CEB",
    "Xmake": "#22a079",
    "Xojo": "#81bd41",
    "Xonsh": "#285EEF",
    "Xtend": "#24255d",
    "YAML": "#cb171e",
    "YARA": "#220000",
    "YASnippet": "#32AB90",
    "Yacc": "#4B6C4B",
    "Yul": "#794932",
    "ZAP": "#0d665e",
    "ZIL": "#dc75e5",
    "ZenScript": "#00BCD1",
    "Zephir": "#118f9e",
    "Zig": "#ec915c",
    "Zimpl": "#d67711",
    "Zmodel": "#ff7100",
    "crontab": "#ead7ac",
    "eC": "#913960",
    "fish": "#4aae47",
    "hoon": "#00b171",
    "iCalendar": "#ec564c",
    "jq": "#c7254e",
    "kvlang": "#1da6e0",
    "mIRC Script": "#3d57c3",
    "mcfunction": "#E22837",
    "mdsvex": "#5f9ea0",
    "mupad": "#244963",
    "nanorc": "#2d004d",
    "nesC": "#94B0C7",
    "ooc": "#b0b77e",
    "pkg-config": "#2b5e82",
    "q": "#0040cd",
    "reStructuredText": "#141414",
    "sed": "#64b970",
    "templ": "#66D0DD",
    "ucode": "#00b8d4",
    "vCard": "#ee2647",
    "wisp": "#7582D1",
    "xBase": "#403a40"
  }
}
''',

    # ===== tests/test_minimal_bundle.py =====
    'tests/test_minimal_bundle.py': '''"""Black-box CLI regression tests for the five-file profile bundle.

Set PROFILE_BUNDLE_ROOT to a clean source bundle. Each test copies only its five
tracked files into a disposable directory; Git and network access are unnecessary.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


DEFAULT_BUNDLE = Path(__file__).resolve().parents[3]
BUNDLE_FILES = ('profile.py', 'profile-state.json', 'README.md', 'README.en-US.md',
                '.github/workflows/update-profile-art.yml')
DATASETS = ('contributions', 'contributions-history', 'github-content')
ASSET_HOST = 'https://andremellotech.github.io/andremellotech/assets/'
TEMPLATE_SHA256 = '6b02d932894a6074045c18a61b59212eb16a3362a67f3da718ae76e04b8ce3ef'


class MinimalBundleContracts(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ.get('PROFILE_BUNDLE_ROOT', str(DEFAULT_BUNDLE)))
        for name in BUNDLE_FILES:
            self.assertTrue((source / name).is_file(), f'Missing five-file bundle member: {source / name}')
        scratch = source / 'work/bundle-contract-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='case-', dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in BUNDLE_FILES:
            source_file = source / name
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target)
        self.runtime = self.root / 'work/profile'
        self.output = self.root / 'github-output.txt'

    def cli(self, command, success=True, **environment):
        env = os.environ.copy()
        env.update({'PYTHONIOENCODING': 'utf-8', 'GITHUB_OUTPUT': str(self.output)})
        env.update({key: str(value) for key, value in environment.items()})
        result = subprocess.run([sys.executable, str(self.root / 'profile.py'), command],
                                cwd=self.root, env=env, text=True, encoding='utf-8',
                                capture_output=True, timeout=45)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + '\\n' + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, 'Command unexpectedly succeeded: ' + command)
        return result

    def state(self):
        return json.loads((self.root / 'profile-state.json').read_text(encoding='utf-8'))

    def tracked_snapshot(self):
        return {name: (self.root / name).read_bytes() for name in BUNDLE_FILES}

    def runtime_data(self, name):
        return json.loads((self.runtime / 'data' / (name + '.json')).read_text(encoding='utf-8'))

    def write_collector(self, command, dataset, field, value, fail=False):
        filename = {'calendar': 'fetch_contributions.py',
                    'repositories': 'fetch_github_content.py',
                    'history': 'fetch_streak_history.py'}[command]
        source = ("from pathlib import Path\\nimport json\\n"
                  "root = Path(__file__).resolve().parents[1]\\n"
                  f"target = root / 'data/{dataset}.json'\\n"
                  "data = json.loads(target.read_text(encoding='utf-8'))\\n"
                  f"data[{field!r}] = {value!r}\\n"
                  "target.write_text(json.dumps(data), encoding='utf-8')\\n")
        if fail:
            source += "raise SystemExit(23)\\n"
        (self.runtime / 'scripts' / filename).write_text(source, encoding='utf-8')

    def fake_publication(self):
        """Supply public output through the existing prepare CLI, without rendering."""
        for locale in ('', '.en-US'):
            filename = 'README.md' if not locale else 'README.en-US.md'
            markup = '<p><img src="' + ASSET_HOST + 'probe.png?v=fixture" alt="probe"></p>\\n'
            (self.runtime / filename).write_text(markup, encoding='utf-8')
        (self.runtime / 'assets/probe.png').write_bytes(b'fixture-public-image-v1')
        (self.runtime / 'previa.html').write_text('<img src="./assets/probe.png">', encoding='utf-8')
        (self.runtime / 'preview.en-US.html').write_text('<img src="./assets/probe.png">', encoding='utf-8')
        for name in ('PREVIA.png', 'PREVIA-ESCURO.png',
                     'PREVIEW-en-US-light.png', 'PREVIEW-en-US-dark.png'):
            (self.runtime / name).write_bytes(b'fixture-static-preview-v1')
        source = \'\'\'from pathlib import Path
import shutil
root = Path(__file__).resolve().parents[1]
dest = root / 'work/pages'
(dest / 'assets').mkdir(parents=True, exist_ok=True)
(dest / 'en-US').mkdir(exist_ok=True)
shutil.copy2(root / 'assets/probe.png', dest / 'assets/probe.png')
shutil.copy2(root / 'previa.html', dest / 'index.html')
english = (root / 'preview.en-US.html').read_text(encoding='utf-8')
(dest / 'en-US/index.html').write_text(english.replace('./assets/', '../assets/'), encoding='utf-8')
(dest / '.nojekyll').write_text('')
\'\'\'
        (self.runtime / 'scripts/prepare_pages.py').write_text(source, encoding='utf-8')
        self.cli('prepare')

    def changes(self):
        self.output.write_text('', encoding='utf-8')
        self.cli('changes')
        lines = self.output.read_text(encoding='utf-8').splitlines()
        changed = [line.split('=', 1)[1] for line in lines if line.startswith('changed=')]
        self.assertTrue(changed, 'changes must expose changed via GITHUB_OUTPUT')
        self.assertIn(changed[-1], ('true', 'false'))
        return changed[-1]

    def publish_baseline(self):
        self.cli('init')
        self.fake_publication()
        self.assertEqual(self.changes(), 'true')
        self.cli('save')

    def test_init_roundtrips_all_persistent_data_and_is_idempotent(self):
        state = self.state()
        before = self.tracked_snapshot()
        self.cli('init')
        for name in DATASETS:
            self.assertEqual(self.runtime_data(name), state['data'][name])
        for name in ('assets/andre-ascii.png', 'assets/andre-ascii.gif',
                     'assets/badges/GitHub.webp', 'assets/badges/alteryx.webp',
                     'data/language-colors.json', 'profile.json'):
            self.assertTrue((self.runtime / name).is_file(), name)
        target = self.runtime / 'data/contributions.json'
        data = self.runtime_data('contributions')
        data['contract_sentinel'] = 'preserve-existing-runtime'
        target.write_text(json.dumps(data), encoding='utf-8')
        self.cli('init')
        self.assertEqual(self.runtime_data('contributions')['contract_sentinel'],
                         'preserve-existing-runtime')
        self.assertEqual(self.tracked_snapshot(), before)

    def test_commands_require_initialization(self):
        before = self.tracked_snapshot()
        for command in ('calendar', 'repositories', 'history', 'render', 'prepare', 'changes', 'save'):
            with self.subTest(command=command):
                self.cli(command, success=False)
        self.assertEqual(self.tracked_snapshot(), before)

    def test_separate_collectors_preserve_previous_runtime_updates(self):
        self.cli('init')
        self.write_collector('calendar', 'contributions', 'contract_calendar', 'first-pass')
        self.cli('calendar')
        self.write_collector('repositories', 'github-content', 'contract_repositories', 'second-pass')
        self.cli('repositories')
        self.write_collector('history', 'contributions-history', 'contract_history', 'third-pass')
        self.cli('history')
        self.assertEqual(self.runtime_data('contributions')['contract_calendar'], 'first-pass')
        self.assertEqual(self.runtime_data('github-content')['contract_repositories'], 'second-pass')
        self.assertEqual(self.runtime_data('contributions-history')['contract_history'], 'third-pass')
        self.fake_publication()
        self.assertEqual(self.runtime_data('contributions')['contract_calendar'], 'first-pass')
        self.assertEqual(self.changes(), 'true')
        self.cli('save')
        self.assertEqual(self.state()['data']['contributions']['contract_calendar'], 'first-pass')
        self.assertEqual(self.state()['data']['github-content']['contract_repositories'], 'second-pass')
        self.assertEqual(self.state()['data']['contributions-history']['contract_history'], 'third-pass')

    def test_failed_collector_leaves_tracked_state_and_readmes_unchanged(self):
        self.cli('init')
        before = self.tracked_snapshot()
        self.write_collector('calendar', 'contributions', 'failed_attempt', True, fail=True)
        self.cli('calendar', success=False)
        self.assertEqual(self.tracked_snapshot(), before)

    def test_changes_save_then_no_changes(self):
        self.publish_baseline()
        state = self.state()
        self.assertEqual(state['version'], 1)
        self.assertTrue(state['published_sha256'])
        self.assertTrue(all(len(value) == 64 for value in state['published_sha256'].values()))
        for name in ('README.md', 'README.en-US.md'):
            self.assertEqual((self.root / name).read_bytes(), (self.runtime / name).read_bytes())
        before = self.tracked_snapshot()
        self.assertEqual(self.changes(), 'false')
        self.cli('save')
        self.assertEqual(self.tracked_snapshot(), before)
        self.assertEqual({str(path.relative_to(self.root)).replace('\\\\', '/')
                          for path in self.root.rglob('*') if path.is_file()
                          and 'work' not in path.relative_to(self.root).parts
                          and path != self.output}, set(BUNDLE_FILES))

    def test_history_only_change_is_persisted(self):
        self.publish_baseline()
        before_readmes = {name: (self.root / name).read_bytes() for name in ('README.md', 'README.en-US.md')}
        self.write_collector('history', 'contributions-history', 'contract_cache', 'new-history')
        self.cli('history')
        self.assertEqual(self.changes(), 'true')
        self.cli('save')
        self.assertEqual(self.state()['data']['contributions-history']['contract_cache'], 'new-history')
        self.assertEqual({name: (self.root / name).read_bytes() for name in before_readmes}, before_readmes)

    def test_asset_change_is_detected_without_data_or_readme_changes(self):
        self.publish_baseline()
        (self.runtime / 'assets/probe.png').write_bytes(b'fixture-public-image-v2')
        self.cli('prepare')
        self.assertEqual(self.changes(), 'true')
        self.cli('save')
        self.assertEqual(self.changes(), 'false')

    def test_preview_change_is_detected_without_data_or_readme_changes(self):
        self.publish_baseline()
        (self.runtime / 'previa.html').write_text('<p>updated preview</p><img src="./assets/probe.png">', encoding='utf-8')
        self.cli('prepare')
        self.assertEqual(self.changes(), 'true')
        self.cli('save')
        self.assertEqual(self.changes(), 'false')

    def test_save_without_prepared_pending_change_fails(self):
        self.cli('init')
        before = self.tracked_snapshot()
        self.cli('save', success=False)
        self.assertEqual(self.tracked_snapshot(), before)

    def test_summary_succeeds_before_initialization(self):
        before = self.tracked_snapshot()
        self.cli('summary', PROFILE_RUN_STATUS='failure')
        self.assertEqual(self.tracked_snapshot(), before)

    def test_notify_template_matches_original_yaml(self):
        result = self.cli('notify-template')
        normalized = result.stdout.replace('\\r\\n', '\\n').strip().encode('utf-8')
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), TEMPLATE_SHA256)


if __name__ == '__main__':
    unittest.main(verbosity=2)
''',
}

BINARY_INPUTS = {
    'assets/andre-ascii.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAa4AAAImCAIAAACEnPnlAADgf0lEQVR42uz9fXQbR3onjFaPrG5J7KJNNGKi2yYAmkBjRAIiSFA0v8wPjSUoouBzZWpHke7O'
        '2JPx2CeTzCbZ5CR7zm7uO/vu3s1Nzia7OffN5mTuZM/MzV57lTfK5Kw+XkujWBQlSrJl8MMkpSE+bACU0Q0Pu2GrC5JQkKz7xyP1YEiJ+rCszFj1OzoSBBbq'
        '109V4WFVPV8cdjyFABxC1+EvBgYGhi8ybii6Kn33JftH3HUOMT3IwMDwCAAUHXedQ4iDdx6zVSRTggwMDI+YQrxuK8AvIe6mVmRgYGB4JA/LiENf4q5z19mx'
        'mIGB4RHeG3LXuS+x60EGBgamD7/EFCEDAwOzonyJjQIDAwMDU4UMDAwMN5xpbo0nVj/2bwKNwy4nQuj1Bf2P5z/4uZ/WrPo3/8I5vBEjhF4f/eSP/8+f/tyH'
        'xcfK/3f5as8TCKHVPzb4/5FnY83AwPALi1XC2trb/ezfNzd9+5mnn1j92BOrH3vO+cQTq1cf/cj82U//5ZPfHnY8UbPqiZpVz7Wse0JcdXSqZP+0/OtP0R1P'
        'XhdXXRdXXduAkfjYY+9e/OUdplBH90f5C/f0kccdUt/zsUvkYsm66G5SezdvT85NL2+zZu268uXLK/ByiCtZFxFCa9auC3f1K+5nSuTiko9s++pL0Lm7SUUc'
        'Kl++XK80PBNoWf7M9yGIjWCke9MLX134ILHCA98Txd20/Ersqx8k5u5mrOqVBhE/DmPFwPAgVeF/j7SsWfWzE/STAv9X7/9s4f7333l6Df8zl8QnH3/srw79'
        'TFFe+TfPIP5nn71et5r/x49+kQdizdp1zw5G65Wn87kP3E3qk0qD4m78SLuwZu26cNdzX27dOBs/7W5SG55RH3c4zZ/q7iY1GOm++LFRrzQ8qTRIT7rE2tpP'
        'ikYw0u1uUvO5D8qXL1+7Vnls9epPisYnReNJpWHh/QR8pTt6v8JxCHGo9/nt7mfUNWvXfZS/AB3+VLtw9WoFXtMrl2V3o+NJFzzVs0PR6bdPfPKxAbwdvV9x'
        'P6Ne/NhQW8LoOlp4P/G4Q9oU+2q90rBm7bqrVyv+lvCTcsNPtQs1tbVr1q5bs3YdPCrHIX9Laz73AULI3xK+RC5evVq54/i4m9Q1a9eVr1xeeD+5Qvs1a9c1'
        'BloW3k+4m1R/S2sNfrx6rMqXL/tbws8Emq9dvfpMoKXn+e1r1qyDoahXGkD8mtrajt6vrFm7Dj5YI9aCaNVjVc3obwmvb+24+LFRg2sV9zOKu9H8aeFuJGJg'
        'QHd5V8hx9//fX0a/7fj4WwhxoO8uFo16peFxh7Qp9i9m42d+mr+AEOro+8pPtQvwhWx4Ro2Pv9XR+5WGZ1SEkPsZteEZNdTRDcqio+8rt2PpfX77+NEDHX1f'
        'KV++PBs/PRs/PfPu6ccdEnS4KfYvHndIHX1fGT964MqVSwih8uXLnxRNd5MKn+19frvdibtJ/cQ0Zt49DT/9xDQW3k9Ah6CV4uNvRfo2PV4nwR941MfrpE+K'
        'ZqijGyG0Zu1aYe3a5U9YrzS4m9THHZL95kf5Cw3PqE/KT1+5fGmFMYz0bZqNn4YtZPLctL+lFcSJj7/1ldhXEUIdfZtm42eCke6Zd09fLBrjRw/k0onH66Rg'
        'pHt24nSkbxNCaPzoAfcz6uMOKZdOwEL6xDTssVq2V+0aP3rgE9OA/35SNP0treyLzfAgVeF/S//cr9//X07/uZ8eNH/up6OfVP+X/9HP7QFX/9j4BR+IhmfU'
        'SN+mJ5Wn4b+F/MKVK5dAg9hf/kJ+oZBf+Kf9f/ek8rT7GTXSt+kjbQEhlJybArVVWyf5W1p9La3w/i0BR7xCfuHxup8pmsfrJOhw4f3E43VScm4Kvv8IoY+0'
        'hfKVS3AAvHLl0idFo3z5Mmyvlp+4q1HIL9xSbc28e7p85ZKwZh28tpWIfcxc+CDha2n1N4erf3Tl8qXZ+OmPtAvbvvrSyiMJn/qkaHxiGp8UjcfrpOonyb2f'
        'uHL50j/t/7sln5qNn/7ENMZ/fMDfHO7dvP1J5enq8Vn5F9iLL/2GvyVsj1Xt3X2QgeFuVeEfz3/wV+9fyF2+krt85Y/nM0vMJn/8dz/9q0Nm7qeV3E8rf/x/'
        'Lv7x3/2c2YT/H3n+Hz/6UoF+qUCF/6H94ptNHq+ThDVr16xdt+T93PuJTbF/0dCk/tyb6cQnRWO5c3oKdNN19EnRgFNhMNL9uEOCnWbv89thn9X7/HZQEHCg'
        'hisz6PCTovFR/oK/Jdz7/Hb4elermHqlAaEbZ+En5afhgUMd3bV1EuwWU3PT0OES5Rvp3RSMdMPr3ue3+5vDyXNTCKEXX/oN6LNagebSifEfH1iirfwt4WCk'
        'u15pWK5/t331JdiWhjq64RIAxrP3+e1r1qyDTV/v89sL+YVbjq3758f28ToJXUfC2nXQIYwb6FZbtHqlYfdr/xpuGxoa1Y/NRfZNZviM4H6WpIvhFxtfiX11'
        '/OgB2KD92mv/+n/+9Z/3bt6emptermLQ52Y7Wn4+vV2D3s3bx398gM0aA/oCmE0YfqGgLXzgb2m9dvVqybr4U+1CuKt/4f0EWD8eDu5o7a1uwHHok6LBZo2B'
        '7QoZGBgYEIs2YWBgYGCqkIGBgYGpQgYGBgamChkYGBiYKmRgYGD4pcJj+PE6NgoMDAxsV8jAwMDwyO8KrU+KbBQYGBjYrpCBgYGBqUIGBgYGpgrZEDAwMDAw'
        'VcjAwMDAVCEDAwMDU4UMDAwMTBUyMDAwMFXIwMDAwFQhAwMDA1OFDAwMDEwVMjAwMDBVyMDAwMBUIQMDAwNThQwMDAxMFTIwMDAwVcjAwMDAVCEDAwMDU4UM'
        'DAwMTBUyMDAwMFXIwMDAwFQhAwMDA1OFDAwMDEwVMjAwMDBVyMDAwMBUIQMDAwNThQwMDAxMFTIwMDAwVcjAwMDAVCEDAwMDU4UMDAwMTBUyMDAwMFXIwMDA'
        'wFQhAwMDA1OFDAwMDEwVMjAwMDBVyMDAwMBUIQMDAwNThQwMDAxMFTIwMDAwVcjAwMDAVCEDAwMDU4UMDAwMTBUyMDAwMFXIwMDAwFQhAwMDA1OFDAwMDEwV'
        'MjAwMDBVyMDAwMBUIQMDAwNThQwMDAxMFTIwMDAwVcjAwMDAVCEDAwMDU4UMDAwMTBUyMDAwMFXIwMDAwFQhAwMDA1OFDAwMDEwVMjAwMDBVyMDAwMBUIQMD'
        'AwNThQwMDAxMFTIwMDAwVcjAwMDAVCEDAwMDU4UMDAwMTBUyMDAwMFXIwMDAwFQhAwMDA1OFDAwMDEwVMjAwMDBVyMDAwMBUIQMDAwNThQwMDAxMFTL8gsCl'
        'KGwQGJgqZGBAIsagE+HFCs1WbsDA8M+Fx9gQMHxG6Pn8kk2iyyWXCLGI5XLJuq5hEdeIYiqZAG1ILIsNGgPbFTJ8YeHzBe64K3S5ZITQ1uEYO1Yz/EKBw46n'
        '2CgwMDCwXSEDAwMDU4UMDA8Lff1DL73yavV5eWTXHr8aEDH2q4F76ircHoHDeLg9ck+k8E5f/1B1VyO79jB7DlOFDAz3hq3DMYSQS1Fa2yOgSsLtEZeiVL/w'
        'qwF44VIUvxqwNRfgz//ye9W6j1hWMjF/T88wNREH88vURLz6qewXtyN1KUq9LNfL8siuPVuHY3YDYlnw/Aih1vYIXGXafTIwVcjA8LPNFCgOYhF4h7vHHk6O'
        'Hfvh97+HEPqrv/iz6HCMWNa+va/fqxK8Heynsl/ckjTcFvGpaolY4ydGa0Qsy8rURHzf3terP8It65MBMbMJAwO66SUDfjP2i/tGuD2SSiYerFfNHR8PSOFg'
        'rufz4PRjbypX7pOBqUIGBgaGLz5WCWtr2SgwrAC/GjANAyE0smtPsWjYWzmXosiyIknO2I6RS4TwguDzqy5Z0TWtele1sk91uD2y5CN33PrJskIpbQ6Gqj8Y'
        'bo+E2zt8aoDjuOaWDQ5J8vm/7JAkjGvh4at7CLd1CIJgv//SK69isVYQBF4QmAc4U4UMDLcGqAwR4+cGhkxjEePa2I6Rgq6F2yINHm9B1+ocThHjVDIxtHmL'
        'S1YuEbLn69+gtBxu74gOxziEfGqgd2BweiK+dTjW2t5xfm5mZNceSXLSCm1t63BITklyDm3ekk4mdn/tG+H2jkJBG/nqnnB7RzqViO3YKUlOQRCWkMIHi0Xj'
        '5Vde43mhaBrrg8HxE8fd7sYm1c8hrk6SWkIbdC3f2z/k8XpTycRLr7w6PRFHCG3dHpuajIfbOoBUkpx1kjQ1Gf/Wt78Tbo9MT8Z3f/1laGl/xH7BwFQhwyMN'
        'Suk7Z07pmkYplSSnKNZu7O52SNI7b5+WJMmnBupdCi/wGNe+eXC/Q5LqZaVCKbHI2bdP67rm86sFXWttj7zxtz/wqwGEuJNjx8JtHf5AoKDl33n7lNvTeIkQ'
        '01ws6Hld0yq0XNDzgiBAyyWk7ycT4UgHxvidM6eIZTV4vFOT8eZgqK29o7d/EHEonUhuHY4d+/ERnhcKer5JVdPJxKbN0RKxctkMfMo0DSDleUHE2OcPmIZh'
        'GkZB1/r6B0vEwrh2Y1fPR7omSc6NXT3pVIJtGBGLQWZgAMiyUi/LJ8feSKXmEULEsqYm48QiU5Pv+vwqnEDrZfnwoQNYxAghPZ/v6x8iFtHz+emJ+MiuPfv2'
        'vl4jin39Q6nUfEHPa1oePqhpeVvX2NaMJr/a1z9U0PPVpLYpg1hWa3tkeiLu86v79r7h86tT8XhBz1vEOjk2Cp1Ht8XSiSSxrB/+zfeqbSBAahEL6XlCLqaS'
        'CVlWoHO75fIXDIiZTRgYGBjYAZkBPeLGEzBHEEI2bY6KGK9g6xAxdjidCKHOrl5BECTJ2dyygVaoz6+G2zt0Xevs6m0OhnRdg656+4euVqgkOZeYOG73GIIg'
        'uD3e6q5SyURf/5AgCJTSJaQIIV4QKKW2DcdOJgYPGduxs1g0RIxlWens6kklE+B6TQhxOJ3VhhS/GqCUUkrR7a064bYO0zTsNuH2yN0bhRiYKmR4YArL7fHq'
        'mhZuj4DxdGTXnvNzMwgh+8XW4VgqmfCrgdupHrsloLU94pIVnucbPN6iaWzs6qlQWi8rgsCH2ztIiVRrCtMwXIoC9geHw8lxqMHjrZcVEWO3x+v2eguaPvJr'
        'uxey2QavpzkYKmh6Z3dPOpHoGxg8OTa6aXPUpwbsx6OUrg+GanEtLwjRbTFB4Ne3hESM62XF7fWmk4ndX395IZullL7w4s7pyXh0OFbvUqpJBV7oHRhoDoYK'
        'utb73KDb4y0Wjei27T6/KknOvoEhdJ1zKbLPr36kaRvaIhVKt25/IZfJdnb3pJKJnbv2LGQzkuQcej5aLBq5TGaJHoSxcilKk1/lOM7nC/QODBz78RF7eJke'
        'ZKqQAf2zWHvhu6drGqg5W6nBi3B7pHdg8CNd29AWqZeVhVymORhCHIcQag6GCCGU0mo9iBD6w3/378PtHT/8m+91dneLYi1CyCFJRdMo6FqDx7uQy4BLDaW0'
        't39QEHhCiCjihWyms7vHIUnnZ2f7BgfTyYRDkohFSoRITmcqOR9u79A1zR8I1Ijiu2+frpdlSXLqWr5eVopFY+OzPfWywiH00jdfk5zOBo/njb/9ga5pnd3d'
        'RdNoDobSyUS9rLywY+f42Gg4EmnyqetDoRIhPlWtJgW3G47jFrIZsLSYxqJLVgqaVi/LlJbPvn2au85VKN39tZdNcxEhDqHrDkkSBOGtHx/O5TK5TGbo+ei+'
        'va/f0mYCY9XXPziya0+JWG8dPZxOJRBCvf2DMLwrbCEZELsrZECfW0CIzxc4OXYMjBJ6Pg9mCtgMvnlwP2jDqYk4xNje0hRgf2TJfhMh1ORXEULEIoRc1HWt'
        '97nBw4f2V3sa2lEc8NMSsaYm49Ft29OJZL0sFzQNISRiUdfyLlmxg9tSqXlI74oQcsnKmwf3L3k8EeNwW0cqNd/73GBB00QsIoRqRIwQKmgaIReb/IESsXQt'
        'Dy9sUjChQFcggp1QFjInTk3E/WqgRhRb2yPpRLLqjC/CcIHs9S5lavJdW9Llw3vLIgfM0sJUIcMXFmvXrVu1alWlTMu0fJctVwv8qlWPffJx8fEn6q5du3rl'
        '8uUaEV+5dOlLj61atWrVlcuXr169iu6lcgCxrMefqKO0XKF0zdq1lTK99um16j6rSe9etOrHo7R8+dIlNt3sgMzwy7cfXNnrTcSYFwReEDq7ek3TcDidPr+q'
        'a9ry68Uln9q0OUpKBCJJMK4t6Dql9Nq1a8v7bw6GMK4Fw4VDkpzOXxEE4fEnngi3R7KZ95uDofXNLbls5svNLXV1devWrSuVSj6/WlMjLr+yhF2Vx9vo9njh'
        'qcLtEcRxlFKwS9SINcFga+aD95uDoV958smaGrGmpubxJ56wH49SWr5y5XbxKm6PF+w/uq45nM6+/kFd15p8Pock5T/8cH1zy9o1a4EazC+maTQHQz7/l03T'
        '8Hgb7biUvv4hhyTpmgbDSymttpO4FMXnV2FM2EmZqUIG9Llmi8llM339Q7u//vL5uVkRY1BwqCqhFsdxnV09v/a1l1yyIklOw1xsCYaa/IGiaUSHY7RcafB4'
        'm4Ohomls7OpOJxOdXb20QiFplSAIQ5u3iCKu0IpDkhySBBkNlqOzq7ezuwch5HA44cTqkJy9A4Pn52YbPN7nBoZy2Uy9rPj8AUEQmlSV5wWHw0lpeWNX9yVC'
        '3B4v4jhbm//hH33XJcu0fIPUpwYIsXz+wPqWkK7nO7t63B5vQc9Hh2Mc4hDiWtvbm4MbiEVo5YaudDid4bYOMFuDMgW11drW0aSqBU1rDoY0LQ9DkctmOrt6'
        'KrTC88LGrp6iaaxvCQmC0ODxEmINbd7SEtxwfm42Orzd4XCmUok/+Lff7e0fFDEu6Pkmf8Dj9cLw+vyBV7/9nfETx4G0uSUEkp6bnWFrlalChs8RoLNy2cz5'
        'uVliWaZhgOkDLJhuj5cQ69zsjE8N8Lxw9szp3oHBEiH1sswLPIe4cKSjoOU7u3s4jnN7G5tbQhVK3zp6GPRgdDj21tEjlXJFxHj8xOjGru4SISLG0W0vcBxa'
        'YhvNZTM8L9RJkkuRXbLCC/z+f9zn9nhNw7iQy9bL8vvJpIhxhdKpybjLpVQo5QU+HOlobgnlstkGj/f83IwdePeT2dl3zpxOJefhgWtE3BLasJrn3V6viHFz'
        'KESIJYq13/r2dw4fPNCk+qcn4nWSVDRMh8NZL8vpZCK2Y2T/j/YRy/L5vyyKOJfNNAdDhFjHjh4Jt0cKmhbdHpMkJ/RZIqQ5GKKUchxySJIo1sqK8r9+tA9a'
        'jp843uDxLGSzuWxGEASEECHWQjaDEOf2enmBLxECw3vs6JF0MpFKJID0raOHff5AhVIYNFlRbveLhIGpQobPuCschG8XsSxwnYPTLsSQEUKagyFSIiVC0snE'
        'udmZvoFBhFBB00C/6JpWNExiWQUtXy7T83MzxCJuT6NpGrlsBmOcy2ZELDokJxZrF7IZEeOTY6PTk/ElORdg/8XzvNt74zzLC7zAr1nIZkSxFqHrHOIoLRNi'
        'iRi7ZGUhm2lS1RIhQHru3IzAC6RkjY+NTk/GQaeDQjcNAxToap5PJ5Jw0tQ1rWgaPC9cyGV1TXNI0vvJpGkYDR7v9FS8QstuT2PRMB2ShDgO3IDOz80AtYgx'
        'hzgRY0EQtHyeUioIQrlMKS1TSh2SVNA0j7cxlZh3OJxFw4Tda4VSSsuiWFsnSUXTEAShQinPC5RSXuDfm5yA4UXoxm8IhyQ1eLxXK5QQq0lVDx88MD0ZZ3oQ'
        'MbMJA/qFcTy0iAXmVNNYLFNquxA7HE7TXPzsYbaSJNWItXfTlYjxXZLC1WFx0ahzSmCZdXsaaaVcXDTcXq9pLBp38s1eDrenESGUy34AY2J3hRC6y+e/e0kZ'
        'EMtizYD+OQq0Q8GQ5fU6kol58PBIJuYN40bGLWhJK+Ul7SFfv92bS1FWqNhpNytTancF7yzp6katZEUhliUIfDXX7Vrq+TwW8WqB1/P5epcMKkzP58u0DIKg'
        'e7EvwZ9c9oM6yYFulnIGJVumtExpLvuBHZRyy+cHgKQwhjAy9jP/rNipothDx+qdsl0hw8PY7iUT8yLGTX4VMiYQi4yfGB356m6E0F/+1z9rbY8UdA38/uDv'
        'epdc0DWXS3bJik8NaPl8iVgnx0ab/Go6mYhuix0+tL+vfxAhpGv5voGhVGIeITQ1Ge99bqBECEKo3qWcOjFqEaveJduk6eR8iRDwQDw5NhrdFoNuw20dIhbT'
        'yUS9SyHkoktWiEUKer66JUKomtQlK+lkosmv6lpe17VwWwScEMNtkda2CELoh//9e5D0oboqAAzFcv8b0FM9/QPEIiVi2aQ+v1oqkal4vHdgIJVIjJ8Y7X1u'
        'AL4dIhbB2XBq8t2+/sEaER8+tD/c1mH7GNqD+dKvv/rD//69ka/u1jVt/MQoQqjeJfv8gRKxakQsYhFIbV9FBnZXyIAeoAPNyFf3FAoasSwI83r1N//V/h/t'
        'SyUTWKwlllUsGm53IziCnH37NKV099e+MbJrT0HP9/YPjo8d7+zqETGObovt/9Hfu73e9yYnwu0RdB2VSmTT5i0Oh9PjbSyXqSCADZQrl8uS5PSpatE06l0K'
        'QujcuZmdu/b8ZG72nTOngFRyOju7e1bzPELc1uHY+dnZjd3dbo/XIUkIcU2qGtuxcyGbiW6LOZzS+mAo3NYBLjvpZKI5GKom9amBGhE3B0MlQqLDMZesSE7n'
        '0OYtgiDksh+YpnF+bnbnr+2ZmoyD6RyuKWEowu2R6LYXCgXtW7/xnc6unhKx1reETo6NTk/EO7u735ucGNq8ZdPm6PjY6PiJ43UOafzEaNEweF4o6Nqm56MO'
        'yfn/+av/d7g98pO52b6BwehwzO31EmI9293bpKqdz/b4/AG41gRtW9DyhJCzZ077/IGFXCa6bfv42PHpibhLfopY1v5/3Aek5r0f5BmYKmS4LUZ27VnIZUzD'
        'sL+NQ89Hz8/NNHi8DodUuUodDmffwKAoYsnpLGj5omHWu+QvcdxbRw9zHDo5Nrp1OEav0KJpiBgTYpWsEtz0j5847vZ4ZVnBuJZYlk9VdU3zeBvBPtAS2kCI'
        'RSn9ydxscyhEaTmdTCxkMy/u2p1OJYDUpSiQ4RVjzPP8QjYrOZ1gSCmaBkLce5NxMMJOT0zwAp9KJtxe71Q87pAkjuOqSVOJeYckEWKVCMG49tiPD9dJ0vnZ'
        '2VwmG45EHJLz7JnTlmWF2zoWchlRxBVKTcOAlAq6psHgfKRr5+dmc9lMuD3CIQTZrRs8XpeiTMXjFVpxe7wVSjd2dZesktvr4a5zlFLTNCTJ6ZAkWq7UYPH8'
        '7Cyl5XQieR2hs2dOvTc58dbRw6iqYp+uacSyYjt2IoQEXmgOhugVumaN0ORXw+0RDnFAyvK/sgMywy8inn66oU5yFo3FCxcWlvxoYNPz+Q8XzMXFJjWQX1hY'
        '3uC2R/VAYM2adfkLOeVpN0IolUx0dnWbhgEv8h8uXC5dAtK1NevWrFmXSiZ8fvXKlUvJ+fklpNCgaCzWSc41a9fOvjcdam29fOnyzPTkZ5c91NoGpHds2dnd'
        'A6Sd3T1F07ibjzAwVcjAwMCAWBZrBvTZ7b/RbbH3JuOalpdlpdoCAJkUql8Afut3f1/L5xFCPlUdP368SfUjhAqaBsYKhBCkmC4RUiOK0eHYX/7XP6uug44Q'
        'am2PQK4EqPwL+Q7gdb0sQ6YDl6zUiPi9yXiNKIpiLSEXb1xZyordEiFUIhbYTw4f2g+k0eFYKjFfI2JZUVKJ+anJuM8XsE0o1Wkabke6b+/rYPRYoWhyX/8Q'
        'Qujk2LElFTttswm6fYV7YpEm1Y9xLZiGINHDckmXVAp1KUrvc4PvTcarnwrY4WEKer7epVRndlghqnrJY7sUBYv4QRWJZkDsrvCXDrwg+PyBgq7pWn7JLbvt'
        '2Gy/gOSDRdOol5V9e1/nEIcQOnb0iNvT+JO5WcShjV3dDkmSJGc40kEsUjSN9cHQ+bnZoee3+PxqsWj29g+6ZOXwoQNN/sCxo0d6BwY6u3sWspnW9ggv8JCP'
        'q0bEnd09xCI+VTUNs7O7pzUS4Xm+b2CoORiitOzxNo7s2n1ubhYhVKEUIW78xGhnVw+Q6ppWJ0n79r7O84JpLvr8AV7gewcGW9sjLll2e70IXV+ZtESsTZuj'
        'CKHW9g7IA/bqb/4rSsu6pv3vf/KfL+SyvCCApJcI2f0vX4aCJBDMZ0tqF+SDQRvZtcfj9ZISiQ7HeIFPJ5KEWMQi587NNAeDx/7piNvdWC0pz/PPDQwB6W/9'
        '7u8XTQOMM+fmZm0929oe2fnVPRziRCw2h0Iv7tqTTs73Dgw6HM6vbInmchmE0PpgCIJbXLJiP97VSmX3v3yZEIvjOJ9fRRyn5/PMxoKYX+GjDGJZ+/a+vmSj'
        'Eb7pdres8Q2nFllR+vqH6mW5SfWD/8qLu3b7fAHYHiKEtHw+lZpPJub/5D98l1gWQhxCHBYxxrUY17pcsqwoI7t2+9RAQdN6BwZFjDGuDbd1+NSArCipRMKn'
        'qrBfq5fl8eOjGNcWNA3+WNZFi5ASsfr6B4lFRCy+9M1XbVLY7m0djolYjA7HoAdiWePHR0uEEMu6I6lLVizroq7lRSyCH4+Wz8OLf9j7Rk//AL6ZsAshhLil'
        't0BL3oJBGz8xWiPi3udukIK/SzgSCbdFEEI7d+1ZImk6kbRJLeuiRSxiWT/8/s/VPOEQQhwSsQgb5MMH99+Q9MToyePHep8bvMXT2Y/HLf8RA7srZPj5M5SI'
        '8S2T39l+bbYalWXFjifRtDwEk8Ap7JY9wI/sZr3PDaaS81CPKZWcv0TIMz71/VSiRhSvIwTlNzUtn04mRnbtnpqIgwcinCVranA6nSCWBU58dqJA21EZHq/e'
        'pVy/fj2dTthdRbfFViaFbRf8HW6PQASbz69OTcTD7RFd1+DhgRrdnQ8m5FWcukmaTibgsaHalF8NNPnVakmnJ2647EC2xxVOry5FCbdF4PgPkhLL8vnVVJLV'
        'zGOqkIGBgQExswnDvQCOwyVC6l0KZEte8lOwVJwcO7ZyD3C0RAjZeaEhCzScc9PJedvikUrNu1yyKNbCC4QQ5O6HaBA7xgPiQ8C52u6hXpZPjR3f0BaBIyoE'
        'ZtjnUOgctodgoICuEEJTk/G7JEUIEXKx2oIBjeGDkPh6iV0FbBrjJ0Z7nxuslnT5oL30yquQ7/p2ki4xm8BFRLWkS4bX7mpJ4u5qSSFpdnWS7eVbSyxiMJ1t'
        'aIvs2/v6ElsZA2JmE/QFrc300iuvTk/EXYrS2tbhkJypVGLT5ug7Z07ZqatGdu2WZaWga+uDwZ/MzUqSM7ZjxD4/wn1ca3vHQi4ztHkLVPBoUtXxE8f7+gej'
        'wzEOoQqlDV7PsaNHIG9gOplwybJpLgJj3+Agv1pwe70c4ppDoesIQf4YXuD7BoZymWzvwACltMHr8Xgb04nE+mDw8KEDbk+jiPHZt09LkmSai83BEELIpwam'
        'J+Ot7e3Hjh7Z8/VvNAdDkMJLxHjP115OJxOt7ZFwewQh7m5Iz8/N9A0MvXlo/wsv7nR7G93exjpJ4nnhW9/+zkI2A3Sd3T0+NfDOmVMwjD6/2hLacG5uxu3x'
        'VkuKOG5k1+5LhIDRQ9c0WVbqJKmgaw5JuqWkwLiaFzq7u33+wPRUfImkDkmqHt6FbLbB4xUxlhWFEMs0Fwmx4PmHno+CpCVC6iRpajIOJbE+0rXYjhEOIYxr'
        'YU7DbZEGj7egaw6H5PZ6pyfirGIUU4Vf2BtAh9MJybVM0+AFYdPmaIlYLtdT/kCgoOWnJuLvnDkFSfQKel7XtAqlTar6zpnTzcFQg8f7zpnTkuQUxVpIUKpr'
        'Wmt7x769r0OGaoxr3zp6pDkYamvvMA2DWOTs26dFsZbnBSzWihh7vI1QVqkltGF64t2W0IYSIeG2SKlEGjxeSM48tDlqFz/yeBsrlJbLVHI6wYAAXXEc8qkB'
        'WqZgF3bJiktWKpSCKwzkBITk+zwvIIQqFWoaBsa152dnPN7GuyE9Pzfb2h4ReMEhOVOJ+QaPd3xs1O31trSExseOD23Zcn529jpCBS3PcdzGrp6PdO3c7Mw7'
        'Z04Ry2oOhqol5Xn+8KEDupb3q4H1LaFi0RDFWhHj3/yd39P1/C0lxRinEvMVSsdPHH+2u+etHx/2qYFqSZcMbzjSAb+cCloeMi2+8/bp5mAo3N4BkkJ7EWOf'
        'PwDp1E6OjcqyImJ8bm4G5nRjd7dDkqYn46lEYkmMCuQuY98gdlf4xVGF4bYO8IODO3jbBgIno+VX7CO79kCyA03L9/UPppOJnv6BfXvfqC601PvcIBymbhxO'
        'kwlw7oPDI5Q0gvf7+gd1LT81EYcT33uTcYtY0W3bT40dt4gFF//QGI7qBT2PEIJkDRaxsIjtkkk+X4CQi9AnnHzBpIsQqhFFXdcQQljE0AmkYygRsqEtcpek'
        'QFcjik3+AIwAfNbO1IAQgiex801UG4WqJT05dmzrcCydTED2CoSQLCvAeDtJ4YhtS5dOJmD8l0hqD6+daQLe7OsfKuh5TcuH2zqaVD9ICuKkkglZVhBCmpYf'
        '2bX71NhxhBDM6QqWLpCCfYOYKmRgYGBgB+RfwqvAWx5noOoIeAKH2zt0XbtjJSC7ltDy9z3exluy2Mdw+OymzVGO45pbNkB1YCjJ1BwM6bq2aXMUPOyaWzYI'
        'gsALAhQJ8XgbIcHB1uGYiDFUR6puaT8/dJVKJmxSewSaWzbAKb665YMl7esfEgQBJBIEAcoz3Q0plHv3+dXe/qGrFUophQZLSOFCsKBrCCGH0yliLMsK9ACp'
        'tnlB8Hgbq0lFjH3+LwuCAB/HuHbo+ejVCpUk5x0lDbd3kBKRZcUuKXXLmUUIsQJSbFeIfrkSatW75EuEwAkITK4iFg8fOgAVexFCYHA8OXZseca9vv7Bk2Oj'
        'L7/yGkLoB9//65Fdu9OJ5MmxY8vr8MJnR3btKWhaKjUPrs7jx4+HIxGIfgNSKFIMRlUI1EsnkuFIZCoeB49ohBC4HEMeQ58amIrH7f/WiLi6ZPD0RDw6HBs/'
        'fhz+C4lO/2HvG01+dWoyDq7F8KN0Itk7MGBHBz4o0nAkcvjg/uhw7JYtVya94Q596MDOXXtSiXkYk+Wkdlzg4UP7YSKm4nEoqyKKtfbwLiGdnoiDzznY2etd'
        'SjgS+cH3/xp80VeQFFy+Dx/aP7JrNzweHJarF1J0OPb3e19n1ZbZrhD9chUhGdm1R3I662X5h9//nmkYgsCLYm1zMEgsUiKkSfWfn5t558wpl6JsfLYHtifN'
        'wRAhhFhWKpngBaHJr4L9oaBp75w5hRA6PzezxIdmfUtoIZeRZYUXeF3XRBEvZDO8wK/m+fcmJ6A6UoWWK7TS4PVUKDXNxXB7h65p/kCgRhQ7u3oIsXxqAPYs'
        '4baIbcFwSJIgCMSyIDAO/m4OhtLJRL2svLBj5/jYaDgSAZvAQjZTNI0Gj/dj04huj6WTCYckgaSS05lKzj9Y0iafuj4UKhHiU1WHJJ2fne0bHLwb0hIhBU2v'
        'UCqKtYRYNSLmONTg9SwnhZYch9weLxiCIMDR7fVC6ZX3JieWSLqQzYJN/NjRI2BDX8hl6mV50+boHSVNJxMtoQ3EssAdanoi7vE2SpKzuSUEC+nNg/vPzc0w'
        '+wnbFf4Sbw99voDtx2e7nk1Nvhtu6yDkIgQzLInM9/kCYGBBCEG0f0HPJxPzW4djS0L94bNbh2NgTwBjArqZtj7cHgHvPLA8IITA587ekdl5EJYkaFiyM4Ly'
        'ngVNg3dqbsa9EXKxmhTMID39A+lEcomT3YMlbfIHoAd4MTUZh732HUnB7gFmE13XYANrU1STghkEjCq2YcciFswmDC+4KNqk4DYIgwCfTaXmsYib/Krd5naS'
        'Qu4M+Ht5JojlK4oZUpgq/KXH40/UXbt29Z8lJOuxxx6rEfGVS5e+9NiqVatWXbl8eTXPr1q1yo7VI5YFj3fl8uUaEVNaRgitWrWqUqarBd5uAHvVNWvXVsq0'
        'TMvLb7VWrXrsk4+L1V09WNJrn16r7hNa3iXpLcfklqToLrwCqklX+MgdJV0+jAzsgPwFMZ5IklOSnHCvTyu0r39Q1zWPt/HixU+W3ItDCaT723JCVxCRomsa'
        '1EF3yQrGtZLk7OzqAVJeEHx+9dPr1xsa3OvWrSuVSj6/WlMjlkoleDARY2jc5PM5JKmmRnyyvn7tmrWy8pQgCI8/8YTPH9D1fHMwlP3g/auVyqeffkopvXbt'
        'WvVpHUgJsVrD7aZp1Ig1bo83/+GHbrdHefrpC7lcczC0nJSUyMbOLtM0nmny1dXVVZMSYsHRskasCQZbMx+83xwM/cqTT+Y//HBjZ/fjTzz+cbEYbuu4fOUS'
        'pfQuSR1OJ7yAbDH5Dz9c39yyds3agq43B0PXPr3W3LIBJEUct2SmwFrCCwLM6RJSXdNs/3kYDbDJVA/v9eufIoSuXLlSvnLlaqVytVLhBWHVY6s6u3qhEgPi'
        'uHBbRy6bsSeXORiyXeEv31kYDrMQNGZf1UPpIsjfBzYQnxr4oz/4PWip69pL33x1/Phx8ICrPv/aKflux/jnf/k9hNCRQ/vhnAWX+k3+AELIp6r/sPeNDW0R'
        'WVH+fu/r4CsXHY7pWr6gaXAog/MpBHvViDiVnPf5A3COa1L9hZvRDjUihs+WCPnB9/8aMixUPxWEiI3s2gOkkNcA+kwn5yHmDIwV8N8lpKDHU4mEfVC1SZv8'
        'AXiq6s9WS1oiFgwvQuieSG1JIaDQPnG7ZKW1PQKS/u//rz9DCP1//+av7ayRX//mazDg903q86s1WPxvf/Hn4JuJEIpui+l63iUrQBrdFoPPtrZ1IIT+9P/5'
        'Xbg86esf6h0YOHxwPxyiWUwe2xWiX9g44ta2joVcpndgoGSVTo4dWx8MFg2zORTyqYFzszMXctl6Wf7YNN85c3p6Mi7LiihiCJBIpxK5bIZSCh42LkWBYJKh'
        'zVv2/2jfjRBjjkMIgV1l0+Zob/8QxrWmubiQzXi8jblMtkn1+9QAz/O8wO//x30twQ26lgdSl0sRscghrqBpCHEVSnmBD0c6mltCLuVGfIjb64W0ehDukk4m'
        'IB7u5NjocwNDuWxm/MTxBo/nY9Ns8qtvHT0MNaduBgju+UjXpibjbo/XNIzegcESIfWyzAs8h7hwpKOg5Tu7eziOc3sbl5Omk4mCposYj58Y3djVXU3a2d0j'
        'YtwcCoH951vf/s7hgweqJZWVp3xqIJfJbuzuvidSW1KHJIlirawo5TJtCW1YzfP7/u6NBo+nQikh1kI2cyGXjf3fdobbO6an4qKI35uM+9TA/ZFC3foSIUXD'
        'oLQ8NREPt3dAnb/Dhw40eDxuT6OIRVGsdXu90xPvLmQzZ8+chgVmmsaFbPbc7Ax46tyNMxYDU4UPFRADq2va1QrVtTyHEM8L4H3W4PESy8IYm4aJ0HUOcUXT'
        '0LU8sSzTMIY2b4HYWIjGQwht2hyFzE4QfyrLikt+KpfNQFEhSqmuaZTSVDIxPRnPZTN2xFiJEIck5TJZKM8k8GtSyXlRrAVSnhcgN2rRMAt6HnRcuUzPz80I'
        'gqDl85RSQRDKZUppmVLqkCTISwhF3KErh8NZoZTScr2sCAKfSiSmJ+NQWQlj/M6ZU51dvQvZDHyNwRZRIqRGxLqmFQ2TWFZBy9+StGgalJYdkhOLtQvZTDUp'
        'pRSkLpoGzwsXclld06olNQ0DY6xr2r2SVksKFabALpxOJEFSQixBECqUvnPmFEgqYswhbiGXqRHx/ZG+n0qkk4l0MpHLZpqDIRHjgq6dn5t958ypcFtH5ebz'
        '8Lyw/x/3SZKzQikkKEMIUUrhdCwIgkOSTNNgGcDYAfmXCW5PI62Ui4vG53cvLvCC2+s1jUWEUI1Ya5qLy78kfjVgGot2MXVQN6a56HA4EUK57AeQcLC4aEBX'
        'xme4k4KuIIWiaSyWKbXvvG5JuoKjnG1Dt4dxiaQOh9N+/55Il3cFlo27manqh3lQki7pnDkPIpbF+guGXPYDLGIwStqaws7PWv3innSN/UG/GijTskWs1YJg'
        'GAatlKE3vxqAF+D/rGl5h+QE5QL38dAyl/2gTnIghJKJ+XqXXKZlaCliDC3RivZTW2FBSyBNJm7kGUsm5g3DsGsHE8sSBB4hJAi8aS66FMVuCR+sJoV39Hy+'
        '3iUjhExzEYt4uaT28MLz25IuJ72dpHZXej5vz1TrbbKIg8j3TXo7w1f1TIGkMLP3sTYY2K4Q/bNnW2jyq9MTcTuPnu3xd3JsNLothtB1hFCJEAj7n5qMv/TN'
        'Vw8f3D81EV8ebQJtRr66ByG07+9ehxj+ZGK+tT1S0LWdu/ZY1kWIYDl8aL+dLtA20SCEgLRELKj9ZFdZIuSiS1Z8agDiHOyWCCG7K13L9w0MQQmkNw/uB9Lq'
        'lAegOF565dWCpulaHoSyuxo/MVrvkqcn4hA48d7kRHXOAnCyw7j25PFjuq7Vu2QOoehwLJVIQMVkO+cCpBGEfII1Ir4/SW3S20kKV3VLSCE14RIXThHjl195'
        'DUxhK5BWJ2FcTgopEff93eugN0d27YFIFYQQkIKkf/hH34VIGDu4yF4VIsYwvOxLx+4Kf7GsJdFtL0xPxl/9zX8FJo49X//G1GTc51e//du/z3GoRsRbh2Pn'
        'Z2fD7RGH5Dz8fx0oGoaIsa5rJYvkchm4N4QNwshX9xQKWmzHyOGDB3hB2PT8FsShj3St3qWkkvObNkfTqQSxrKmJuNvTiBDnUuRnu3t3f+0b52ZnRIybgyG3'
        't3E1zyPEAenG7m63x+uQJIS4JlWN7di5kM1Et8X2/+jv3V7ve5MTQ5u3bNocTScTzcGQw+H0eBvLZSoIwrnZGYS4crncEgoBqcfbCHWUKKW8IBDLwmLtuXMz'
        'Pn+gs7unmtTt8aLrqFg0+voHRYxrRCwIQnRbzOGU1gdD4baOv/yLP6t3KefPzUa3bX8/mTw3O1MiFs8LPC80+dXmYAjK5rlkRXI6hzZvcXu9hFj3J6lNKmJ8'
        'S0l9aqBGxEtIo8MxSsuyrPjUgH1bB1JDUM0KpLEdI7cjLRpmczCIODQ+NvrSN1/jOHTs6JFwe+Qnc7N9A4PR4Zgtqa7l04kksayFXAZauj2NDod0fm6mr38Q'
        'XUcLuQz79jFV+AsEXdOmJ+MIoQaP1+GQFnKZMi2H2zqOHT3CcejNg/u/siXK8/xCNgtpCj82DYfD2eD1fKRpUxPvVl/qEcsCKwSUiCuahkNyIg6dm5vd2NUN'
        'heXWtwQvEdLbPyhi0eNthLR9oojPnjntDwRMY5HSMsa1GGMglZxO0zCgN4Q42HYRYpWskkOSGjxel6JMxeMOSeI4jliWT1V1TfN4G8Eo0RLakMtkgRQhxPM8'
        'IYQXBJ8vkMtmctkMsazW9g6ErleTmuZic3BDhZZ5XiCEFDSNF3hCrOmJCV7gIVFVhdLW9sj0RHxjV3dB11yup9xeD88LIhYhPA7j2mM/PlwnSednZyktpxPJ'
        '+5PUJnV7vbeUNJWYd0jSctJ0MnFybNTWg2C40DXNNAx7Tu+VlOMQIQRxaHoiPj0Zt/1AablSg8VqSYumQSntGxj8SNfeOnpY1zRBEOockiw/BcN7qUSYjyE7'
        'IP8yIdTahhBKJROXL5UeeOed3T1F0zAXF5Wn3fkLOYfTuWbNuvyFnPK0G0g7u7pNw4AX+Q8XLpcu1UnOorF44cKC/XhXrlxKzs8PbHo+/+GCubjYpAbyCwt2'
        'gztfXAYCS0iXSPr00w1AurZm3Zo161YYCuiqaCzWSc41a9fOvjcdam29fOnyzPTkfUtqk/r86i0lhQa3JL3jnN4raXJ+foWprJZ0hZYMTBUyMDAwIFbmCf2y'
        '2E+qj72QEGFJ4D2qsquA8cEO1LdbIoTstAUuWakRMZTcrC5+ZBczggiHErHqZRlyPUEu6+hwLJWYh5JDCCHIKW3f8VcnL1hCaqef2rf3dTAEIYQgDzPkm7JJ'
        'Ibl0vSzv2/sGkNomoCWVmNDt42dGdu25J0ltUkiZVT289yrpCqTQVfXTwvMDywqkNt2NyJNEsndgAOxCG9oi1aQwa2DAuaWkhw/tX+Ia9Vu/+/v2nDap/h9+'
        '/3vsS8fuCn8hsHU4lkomfut3f5/nBdM0otu284LAcRzUG3F7vM2hkGkYre0RyenMZTObNkd9aiCXy7z0668SYk1PTjT5A8eOHukdGOjs7lnIZlrbI7zAQ+6m'
        'GhF3dvcQi/hU1TTMzu6e1kiE5/m+gaHmYIjSssfbOLJr97m5WYQQ3CeOnxjt7OoJRzqIRXRNq5OkC7msS5abQ6EXd+1JJ+d7BwZb2yMuWXZ7vQhdvyVpiVgO'
        'STr2T0d8fnXT5ihchrq9XoFfA7WQbNLegUGMayktS5ITSCHTKiFk56/tAUmh0BIvCOtbQmD08Hi9uq7t/vrLWKyFdFX3JKlNCrWi7OFdzQsch+5J0tuR8jzP'
        '84KIcbFovPzKa0XT4AVhY1e3Q5LuSHp+drZGxMeOHvnYNBs83v0/2schjuMQpeUlku7/x31N/sD+H+2LDsduKaksK1u3v5DLZfr6B31qQNc1dJ2rkyTIGOaQ'
        'pOmJOAQjLXcmdSlKk18taNrtGiDmV8jw2QEeEvYW4+/3vt47MAC3EFxVs96BQfj1LmJsWRddsmJZFy3rIkIIcYhDyOWSZUWBwOSCpvUODEIi5XBbh08NyIqS'
        'SiR8qgrbhHpZHj8+inEtRIMUNM2yLlqElIgFmzURi5C9VcvnU6l52Lm8uGv3jS3Gwf31skwsa/z4aIkQYlm3IwWhdu7aAw+sa3lZUTCuFbG4hBQeDNJhAam9'
        'OwZJsYjRdQ6yV/lUtUSs8ROjNSKWZeXU2PFwJNLaHrlXSW3SJcMrK8q9SroCqU9VfapKLMuyLkJ9EogtuSMpsQjMab1LIRYZ2bWnXpZrRPyH/+67S0hvzv6e'
        '20maTiZOHj8W3bZ9ajIOeTBhTrcOx06OHbO3hLdTc9zNEi7sC8vuCtHnmnzBfrH8MGgf/VLJ+XQy0dc/qGn56Ym4na+pOi2NiHHvc4Op5Pz0RBw+comQZ3zq'
        '+6lEjSheRwjqQ2paPp1MjOzaPTURTycT0W0xONbV1OB0OkEsi1gWBDZAkAb4AELKPDgqXr9+PZ1O2F1Ft8VuSQplp/xqQNPy8LS2r+8SUp8vYJGLhaokicsz'
        'U9mlrMAh0aUoLpc8ddMHEyF0r5LapDBo9vDCZ+9J0tuRQl1WGNLq5yeWBV2tQFo9YvAC/na55HqXUk1qN4hu2367OfX5VaiaAIMGcwoPtmQp3jFFGPvaMlXI'
        'wMDAwMwmD3QzWL33sfcLPr8qirWQrdolK3YK5eogBPgbskJVV86EBNfwWfu2HsIV7HALiJqAWAX7Xh8a2x9cOfUxQsjnu7ELq86qDbf49mehVGZ1fMgKpC5Z'
        'OTk2CoLYsRmQfKzafnK78pWQBXoFSWGsXLICpUKg+mg16ZLhhbgXu6sHMrxw+C1oGkSDfEZSe0xGdu0ZPzG6ZCFVnyogd9mbB/ff7sCxdThWTWqPP1Skqm6/'
        'ZNEyMLMJ+izpZ2RZISWyc9ee5mCoaBqxHSNwMmrweDmEWtsjPC9869vfWchmEEL1suKQpPETx93uxibVzyGuTpJaQht0TRMxBsMCQqi1PRJujyDE9Q0O8qsF'
        't9cLV/LXEYL8MbzA9w0M5TLZ3oEBSimYLNw3/9RJEs8Lz3b31EmSS1YuEbLn698omsZy59uRXbt9fnUhm3FIkmkutrZ1OCRn3+Dg+Nhok6oePnhgZNeezu7u'
        '6Yl4a3sH+BuvDwZ/Mjfb5FdvSWpLGtsxUtA0nxrgeWFjV0+xaKxvCbWENuhaPtze0drecX5uJpfN3Ain2bX7EiHNLRuGNm9JJxOS5KyTpIKuOSTplpKmE4n1'
        'weDhQwfcnkYRY1GsdUhSNSnkLrSHt0bEYOvY87WX08nEAxlen6ouZDOmudgcDCGEPgspQtzQ5i2yrOi69tzAkGksumQluu0FjkOpRAJm7aVXXvX5A5LkBEl9'
        'aqCzu8enBt45c2pk157zczMQwcJxXIPHW02KMd66/QVIfVS9AESMv/Xt74TbI9OT8diOnUvK4zBVyHDXlUn8qq5pHEJNqppOJho8HkrL75w5LUlOUazd2N0N'
        'GejSyYTb621pCY2PHR/asmV8bNQlK23tHb39g4hD6URy63Ds2I+P2KU7y2VaoRTj2vOzMx5vY4mQcFukVCINHq9DknRNG9octUsC2cm4JKdTy+cxxqnEfIPH'
        'Oz426vZ6IS88xrW6ls9lM3ZoGiHE4XT6/Coh5NnuXkEQ3nn7dJM/0BLaMD3xbktoQ4mQXDYjirXNwdD4idG29o5cLnP2zClIBdYcDDV4vAhxtyS1JeUFwSFJ'
        'FUrfPLRflhVRrAVJeV5o8Hre+NsfoKrSV4cPHdC1vGkabk/jJUJAg/zm7/yerudvKWmJEJ4XsFjLccinBrYMx86eOV1NumR4/YEA3IhVKtQ0jAcyvFCopHdg'
        '0CUrLln5LKQlQhaymSZVPXvm9DtnTumahjiuRCxd1+yLvIKuPdvdU4PFgqYPbdkCAUUFLZ9KJorFG/ncSIk4HBLk17BJ3zp6hJapS5arI2QQQrwgOBxO0zCm'
        'J+LQA/tes7vC+8fIrj3p5DyUZEIIYRH39A/s2/uGbUzofW4QnN3scksQbCCKtVD9BxpYxCKWZecCgOpL8H5023Y4A8IdvF1aCCoNIYTA9AFdpZPz9meTiflw'
        'ewQOyFDvaflJ2X7sZGK+r3+oXpaB1OWSwbwIuQPsQxYYTOzz4HLS6vwFUDsJIQTpIeDiHy4NmvyB6mql9um7yR8YPzFqV1y6naRYxPCQuq75fAE4L1eTwkfs'
        '4QXHQDjq2sWtPuPwIoTsofiMpJqWhyTVK1xlbB2O3YzpzEPxLBAfEqSfHDsmYhxu6wC6alKgs6uGomWpjGDqpybfZdqQqUIGBgYGdkC+rwMylBmCDAXLU6j7'
        '1QAkWI8Ox8A34u7TrNt1fOBFdFvsaoVKknPo+WixaMDld2dXTyqZ2DocEzGGVP7gFtfcsgEuHMPtHSLGvf1D8Fl4n1LqcDpv+TB9/UPNwZCua0u6AlKfX4Wu'
        'oD7RCqS6rnV29TYHQ6lkoq9/CEg7u3oFQYDHcEhSuL2D4zh4/+GQ0gr1+VUYE5//y9BgSVe8INhzejfDe/ekdsvlki4hhZa0QlfYoNnLYwmpfQ8Ybo8AKcwy'
        'ZHaA2lJLZt+vBkBS9o1mu0J0r6m3XLIyNRkH26KIRZ8amIrHpybfbfKrlwiBI8/UZBwK6doxWPv2vj6yaw9YG+EoBOZFMCm2tkf27X2jr39Q1/KpZAKctMdP'
        'jEa3bYfwrHAkAoV+RCxCOsISsYA6HIlAhkE7JA54pyfi0eEYZK+DGsTTE3EIufv7va9jEa8TRfCAs8PvmlS/TQfZ9xBCNSIWsXj40IGdu/ZApjyE0Mqk48eP'
        'Q5vDB/dHh2PLW0JUGXR1S9KbsWUPkhTS//UODExPxGHuiEWqSWGmbJa7Gd67Jx0/fvyWki4hJRaBmk2QsbGgazBTBV2DDK+QlRIhlErMp5OJatJ9e1/fOhyz'
        'Sz/DMEKFLLCz14hidDj2D3vfACOyXw3AQiIWscjFS1WWfbYrZLgDMK5t8HglSYpui5mmUTTMNw/tTyXnPd7GV37jO5LTeW5upskfqNCy2+stmkaJkIKmcxwC'
        '6zAv8DzPF01jaiIuSc4Gj/dj09jY1f3D73+PUuqSn1ofDC7kss9292CMwYxY0LSFXKZeliXJWTTMCqW7v/ayfa8PoWnEsiBcDP5uDobSyUS9rJiGASnzCrpW'
        '53C6vd63fnzk3NyMaRh7vv6NoeejP5mb5XlhfTC4kM1QWg63d+ia5g8EakSxs6sH7MVAKoq1hFg1IuY41OD1rED6wo6d42Oj4UikyaeuD4VKhPhU1SFJ52dn'
        '+wYH08nEQjZToZUGr6dCqWku3pK0oOkPltQhScQiJUIWslkw2hYNMxyJ2KQ+NQC7s3Bb5C6H9+5JJaczlZxfLuly0oKeHz9xPJVI9PUPQvx1Z3fP0PPRErFG'
        'du0Jt3cUNK0Gi5SWRYyHNkerSR2S1DswyCGEEFcipEn1n5+beefMKShnyvPCybHR6cm4ruXB6Le+JSRiESFOxDi2Y6fkdL5z5hT7jrNd4Z3NI/v2vu5SlHBb'
        'RNfyUL/x5NjokoOMS1HgynxDW6SgaXDvDtfYYE+ATd/4iVGEEFyZV6czAAMFXGbbZgEwa9SIIlR3hEqS1fsOO/i/yR+w62TWiHj8xCiYYuCi3ecLLHfig8t4'
        '+Dg4PMJ/wa8QrAFgSdB1rfe5QdhErEAKrnbwPngmwgt7t2IbEKAS5t2QQp+fhdTOgwBmDXC4qya159SOmLzj8N49qYhF2590ZdIVCrpWH00QQstJ9XwefgR7'
        '/KnJd8NtHXaajyV1We0UEndJylQhA7q/iKXPNaTp8Sfqrl27euXy5RoRg8fMqlWrKmUK9TeIZT3+RB2l5cuXLt1lh4899liNiK9cuvSlx1atWrXqyuXLq3l+'
        '1apVy58fWq5AWqF0zdq1lTK99um16j6h5apVj33ycfGfhRQGze587bp1S0jtKbvL4b17UujqlpIuIb37BbNk9Cplalehuvuu7pWUHZAf6ctBqLcJd9UIoU2b'
        'o7qu+fyqaRrV189ujxfjWtMwRIwhw/sS0wR0BZ59+s2q6kt+xAsCePxhXCtJTklyQioXIHU4nX39g7quNfl8DknKf/jh+uaWtWvWFnS9ORi69uk1SikcuGrE'
        'mmCwNZfNwOWm3TmlFF7wgtDZ1WuaBtDlP/zQ7fYoTz99IZdrDoZqakRZeco0jeZgCHEckDYHQy5ZuSNp5oP3m4OhX3nyyfyHH27s7H78icc/LhbDbR2Xr1yi'
        'lLaG21cgLZVKwGVLCqQ1NeKT9fVAygvCqsdW2cNbvnLF+Su/cvGTTyil165d+/TTT8tXrly7du1qpQLvUErLV65AS7uWNMa1pVKJWNann34KLcGYAC9Wr16N'
        'ELpy5Ur5ypWrlUowtEEQhMefeIIQ614lrRFr3B7vCpKKGIO1BOZU17RwewQSF8EaAKuIaRrwt8fbyAuCiPHFTz5ZQooQgjbWxU+q155LUWRZcXu8LlkhhFTP'
        '6ZKWDGxXeIfcCuH2yNe/+RpC6Mih/ZqWl2XlzYP7q2Pd+/qH4Nyka/notpiu53/4/e+F2yPVbmLVOQiqPbxGdu3ZuWv37/7Way/9+qsIIV3Pw8kL7BXTE3GX'
        'rABpjYhTyXmfP2DnvEsn5+2DkquqAZw94fAFx7He/kF4/p7+gXQyUdA0u09oCQc6+4MY1yJIq/Pc4P2RNqn+6Yk4tLRLL61MWv1U1aRNqh9e2MMLRgBwJOwd'
        'GPyjP/i9O6YesBNEwrn1zYP7+/qHCnpe0/Lhtg47Ek7XtZd+/dUaLP63v/hzny9gF5MCqT9vSauHt5r0uYGhGlFMJRLjJ0b/4N9+FyE0PjZqt6wmxTdj/qoj'
        '+WAh9Q0MVc8pXhbzx8B2hbcFnB0gBd5P5mZ7BwYlyZnLZKF8B+wHJck5NfFu78BgiRARY6iUxnFcbMdIOpUY+eqecHtHoaCZxo1dpF0KEgI/pifi6WRC17TO'
        'rh6E0A//5ntuT2OF0v0/2hdujxQ0Lbo9JknO1Tzv9npLhDQHQ5TSEiEuRRbFWllRTMMIRzqggYhxcyhEiCWKtd/69ncOHzzQpPqLpkEsAl7BPC+cPXManrZe'
        'lnmB5xAXjnQUtHxndw/HcW5vY3NL6L/86X9q8qsul+JTVZuU45BDkoC0XKYtoQ0rkPrUAM/zvMDLylM+NZDLZDd2d69M6lKU5ZJyHEonExAPZw8vpWVRrIUQ'
        'mgvZLKV06PmoIPAQryYrCuwo7bgaXdOiw7H9P9qXSiZ8/kCFUpf81NTku7qW37Q5+tbRw8SyevuHBEFIJRNQ2unsmdOt7ZEKLU9NxmEiOrt7Pm9J7eH9Xzdn'
        'H0hNwzh75pQgCFAjZSGbQYhze73LSU1zURRrRRHDmQBx3Nkzp6Crt44eqZ5T01xcHwzScgXCHxmYKrz1DsLn/7K9RCTJKWKcTiZcsqLl8wU9b59wTcMwDcOv'
        'BuBonE4mzs/NvnPmlGkYGOOpifj0ZByKNC2hgNpAoBzhxUe6dn5uFmNMiNWkqhxCHOLA9Kzl85RSQRDKZUppmVLqUuTCzWpECKHVPJ9OJOGIp2ta0TR4XriQ'
        'y+qaBiHPHOIWcpmiaaSTiXOzM30DN2wRJUJqRKxrWtEwiWUVtHy5TM/PzUAZNn8gAJFnQOqQJJu0QunKpLlMFmpCwVDomub2elcmvaWkQFrQtOrhRRzn9nhN'
        '04C6gJTSqxV6bnYGqmulkgl7eIllwWTJsgIOfTC8Z98+fcNPU6x1expN07hESIPHm04mPtK1dDJBiMUh5JIVGAqeFx6OpDcqTP086XuTcYfDWSdJRdMQBKFC'
        'KfxoOen05ATP8w0e7/m5GV3TiGWF2yOwkJbM6YVc1jQMaMm+8uyAfG9wexoRQrnsB/8spJBwsLhouL1e01hECNWItaa5CEfv4qJR55Qg0Yjb00grZbulsSwL'
        'A3QF6RRNY7FMqV1vwOFwmuairbvvm9Ru6XA47fdXJnU4nLeU1PjFKOFm53H5/CS1u6rOOXjL5DGSJN2O9I6C2LPPvtGIZbG+V/jVgIhxLvvBZ9SDIsYuRYH1'
        'vfxH4EZjN7BJ6yQHQiiZmK93yWVa1rS8Q3IahkErZUh6ikW8WuD1fB4ccU1zEYu4TMsWsVYLwvI+oSu4XXJITmJZej4PWT9z2Q/ge9jaHvkspHbLXPYDaLmc'
        '1C75Igg8qAZbUj2fL9NyMjF/l3oQhg6Gt9rMZQ/1Lcf8nqDn86A+ctkPqh+vTClISitlYll1TumeJL3l8NozZQ/vkuWxwvBWD0X1pNuCwPAu1/IMbFd4B1eY'
        'cHsEgkNOjo1CcH71pqm6NtMKqYMh8Vy9SwlHIqnEvN0VhJSMnzhuZzwGFz/IlAfX4SfHRiEE5fCh/XbKBrg1q05/YGepqxGx3RLcAO2bdeiqRKyTY6Phtg74'
        'UfWXpLU9AknGPm/SFSR1yTJCaN/fvVGdtm/lXczy8YcXy61V8MKlKGCnmp6Mt7ZFpifjU5Pxepc8fTOHtkWs3ucGYGp6nxsoEXK72bfntEbEPlU9fHA/ZE5c'
        'Iml1PsR7mlPIh3iXw/vyK69dv349nUwsSS4JLUFSEGS6yqZ3x+Fld4WPKMBfASEEzhwuWRnavCXc1lGhFF1H6WQCnFSgYtHUZNznV7/927/vkpXpybgsK3B7'
        '6PZ4Ecf5/Cq07OzqeefMqVw20+Dx/mRu1ucPOBzS+bmZF3bsdEhODqEaETepamzHzoVsJrot5nBK64OhcFsH5KFLJxPNwZDD4YREXoIg+NRAjYjhjj86HHPJ'
        'iuR0Dm3e4vZ6CbGe7e7d/bVv2Im53N7G1TyPELd1OHZ+dnZjd7fb44VYlCZVrXM4w5GOqcm4LCsbn+2ZnozHdox83qS3k3R8bNThcFJKpyfj9vjbw7uygWv5'
        'C9tFBv7rUpQ/+LffdcnKR7q2mucXctkaUTRN4+zbp6Pbtr+fTEIoDhQM2fR81CE5SxbxqWrRNDZ2dY+PHSeWtXU45lMDqWQCWp6bnYE5PTk26lPV6cmJ6HBs'
        'uaSxHSP3N6fR4djdD+/ZM6cWshkR4waPVxCE6uGFNGhn3z4d2zFy+OABhJAtCHMtZKrw1nA4nS6XbJoQuIYQ4niBTyUTZ98+7fZ4v8RxPM8jhEzTuP4p+sqW'
        '6P/60T6OQ5B1CuLbJcnJ8zwhRBQxtNzY1Q3X8IIgdHb3TE/G6xySLD9FKTVNo0Ip1KUDOy8h1vTEBJC6vd6peNwhSRzHEcvyqapuX65LEkSqYVx77MeH6yTp'
        '/OwspeV0InkdIVHEZ8+c9gcCprFIaRnjWowxz/ML2azkdJqGwQt80TSgGJ5hLP7q8Asnx0b51Xy4veMhkN5O0gqteBq9giBMTcRh/Kcm4vbwfnaXAOiqs6un'
        'ORgqaFpzMOSQnNOT8ZJlbezqTicTMKfn5mZEEZumwXGIUgpBinV1UuUqnZqIQwqDMi2H2zoEgYc55XmhaJjrW0KQHOGOkn4ew1uhFcgISSmtUFpN6lMDIKnL'
        'pfACX9C0VDKxJBfDS6+8On37RGHsgPzIXxQGAmvWrEslE5cvlT4nirXrajq7uvMfLlwuXaqTnEVjcW3NOiD1+dUrVy4l5+cHNj2f/3DBXFxsUgP5hQVoUDQW'
        '6yTnmrVrZ9+bDrW2Xr50eWZ6srO7p2ga5uKi8rQ7fyHncDrXrFmXv5BTnnYjhFLJRGdXt2kY8CL/4UJyfqlnWai17fMmXUHSX/YFM7Dp+buU9IEP78z0JDzD'
        '0083LCH9/FYvU4UMDAwMiJV5Qo9IkuolMfMiFlvbI6lEAjJFL2lfIhZCCC6tIckCfAqCDSDPc70sT0/EIfjBjva3r9XrXYp93V4d0m8/gB3MD8EedsJkuw4R'
        'XJYvJ00nkhC5YWelXm4vglzTPf0DkFEK3YzYh1B/uMu/J9LbSWoHeCwfXvvxlkTsoM/HRLak+NEKlpklFZdsF5nbNY4Ox1KJ+anJuM8XeDhz6lcDS0htuuWT'
        '/hCGl90Voi9AXkJd06By0/TkRJM/cOzokd6Bgc7unvOzswvZLMehd86c+sM/+u5H+o2KHxjXplKJJn9g/4/2DT0fdXu9Ar8GKgSN7Np9bm4WIdQ7MAixK1Di'
        'xzSM1vaI5HSu5gWOQ82h0Iu79qST870Dg63tEZcsu71ehK53dvcsZDOt7RFe4CFVVI2IO7t7iEV8qmoaZmd3T2skwvN838BQczBEafmWpD+Zm23weA8fOrD7'
        '6y9jsTaXzUC0jJ31kxcEnz9Q0LWFbLbB493/o31Dm7c4JOkSIZs2R93exjrHjQpHd096O0kbPB4wiRw+dGDJ8NIKbfKrBU3Tb6gMDMNrfg4OhpRS6NY2hYGt'
        'Rte01vYI3OVtHY6BbQFawqBRSqPbtvOCUPj5iHJQ7ju/uuedt0/TMjXNRZ8/wAv8w5nTqYl3eV6oJj0/O1sj4mNHj2zaHHXJT0EMePXw2lHwEKCNOA5ilhHH'
        'PYLmFOZXeGvs2/v61ETc5ZJlRRnZtdunBgqaVi/L9bJcI+KRXXsOH9z/4q7dP9sL3Gi5R1YUjGtFLML3xCKkRG6ULqmXZZes9A4Mwq93EWPLuigryo18pQf3'
        '18sysazx46NwzQ+kvQODECwRbuvwqQFZUVKJhE9VocN6WR4/PopxLQRmFDTNsi4uJ613KcQi0W2xU2PHw5HIcm8yYln79r6eTMxDy5Fde+B9i1haPq/l8+nk'
        '/L2S3k7SdCKJcS3GtcuHFyHEfea5s4uB3P+10c+GhdyuCffzXPCCu/lhEYvR4RiMFcwppMz6POb08KEDMKdLSIlFYHjhzLFENLuWabXj4c9la2+PsLtChp8t'
        'CMinBHHs0xNxEWM4HPn8KpTaWdLS/nUK580aUaypwel0wucLWORiQdegK8gjrWl5cOWDA9T169fT6US4LaJp+XQyEd0WA9KRXXtSyflLhDzjU99PJWpE8TpC'
        '8EFoObJr99REHD5yS1Lb1xeqL61wKrQFQTe9i2+4LrvkeyW9naTJxDz0D8NVPbwPMJXGw+nKrwZgMKtbgnSyrDzMOdW0/BJS+A0H3trh9sgtXWduJyCs80fK'
        '5ZCpQgYGBgZmNrn9IQtusqEASHXy4XQiKWIRMinZgQFg9EAI2bfdcPoAEwEEIdiVM+0gBMiq1ORX7cgNhBCUPbE/C4VDXTfzg8GvetsmA/1AiiebFE6aBU07'
        'OXasOirmljGtSyS1bRrVMRL24y2X1CUrUEDDDm4VMV4iKWSBXp4VyqUoSyT9BdmGgFVBxNjnV6vNC1AB9Z7u0WB4YRJXGF44U1fP6e0Wkp0We4kxBPKop5Pz'
        'dl70JQupmtSeCFvSvv5B2LAzswnDz6/g7S+cn5ultNw3MPTmof1QAP7wwQOyrNRJ0rGjR3z+QIVWIDqid2CAUgp2EvfNP3WSxPPCt779nYVsBiEU2zFS0DSf'
        'GoA8dxzi6iSpJbShRsRQB33P115OJxOt7ZFwewQhrm9wsFKmTapasqwSIZ3dPefmZr717e+E2yMCL0BVoPNzM/B4WKxdHwxOT0709g+CcWMhmzHNRcRxL+zY'
        '6VMDUIGPQyiVTIAzLUTF6Jq2RFIw+4DF4zpCkCOLF/i+gaFcJrtc0tU8TywiYjw1Ef+t3/19YIdLMVvSCqUNXs9bPz6ydTjW2t5xfm4GWq5vCTkkZ7Wk0W0v'
        'QGYzSHG2QpDJ5wqwKkA2GnTTQ+D83Iydb+1eF9LGZ3tAUn61cMvhrZMkhyT9ZG4Woeut7ZFjR4+88OLOWy6kelmBnEN2XcDmlg0bu3oWchm3x1uhFRj/6oW0'
        'hBQhbmjzFllWUskECOjxNq4PBheyWdMwHllfa6YKb9yMOJxOYlm2XRXSbSGOaw6Gwu0duWzGJSs+f6BomOCEwfOCS5F5XrBzH0lOp5bPY4xTifkGj3d8bNTt'
        '9ba0hMbHjg9t2cILgkOSKpT29g8iDqUTya3DsWM/PuIPBGCXUalQ0zAwrj0/O+PxNpYIWc3zGNe+8/bpXCbzzplTvCA4HE7TMBaymc7ungql5+dmW9sjAmRt'
        '4oVnu3vOnjnl9nohuLh3YLCg5VfzQkHLgwXg7NunoShlOpUwDQPScS+RNNwWKZVIg8cLqZWHNkft4kceb+NySUuEVCj1qQGeF1LJefigTw1USwqPJ0nOBq/n'
        'jb/9AULIIUm8wC9kMy2hDdWSlogFmdAqtAwvIA3aw8xAc0tlVywa97QZtJOHw/AKAg+S3m54C5rmkKQGj/f9ZHJjV4/ACw7JecuFND426pKVtvaOOkl6429/'
        'YBrG0OYtb/ztD4hlNQdD/kCgXKYVSqsX0hLSEiEL2UyT+rNgZNMwpifiEDa6sasnnUrIslLtYMDuCh8hVRhu61he9QYORHbRHLviUokQeN9OagDh+hax4JAC'
        '9YzABcwOsIcyRlD7CVraTmRw6rQLIb03GYdiTxB8tiQLC/SAELKIZdeBsojl8wXqZRmCvTQt39c/CEckXdeqrSV2VoJqXzlb0ibVD6ddMHFA0aUSITbpEkmh'
        'HJXPF5iafHdk125Ivr1E0upiVU3+wL69r8PWo8kfuJ2kqKom0dTkuw/Ht2OFHFZ9/UP3VBTJvpewN5UgaXTb9lsOb/WUwXA1+QO3XEgulwxRK6mbFhXo9vCh'
        'A3BzAvkdqhfSElJNy0Md2lsO+COboIGpQgYGBoZH+4AM52KE0KbNUY7jmls2NAdDHMdBhZ3mYEjXtU2bo+AC1tyyQRAEXhDCbR2CIAw9H71aoXb6k+prclIi'
        '4Koabu/QdQ26SiUTff1DgiBA54IgSJKzuWUDrVA4tNotbVK4CQKfXo+30T6t+NVAc8sGOOzAQWzT5mg1afVn4bEppSCp/bT2Ca6vf2gFSaHAEGSa2DocEzGG'
        '4lPVLasfDAZkiaSdXT0cx0HtKng8n//L1R+8myMq+qKkv7zX4b3vheSSn3JIEsa19uzzggALya8GYFJgIdmkhJDqlcZU4aMCj7fxhR07U8lEkz8Aqd6b/AFI'
        'gI4QavB6moOhgqZDJICIRYckuWSFUtra3i45nQihc7MzL73yKhZraYX29Q+SEmltj7hcSiqV6O0fTCcTu7/+8kI2Syl94cWd05Px6HCs3qVwHGrweOtlRcTY'
        '7fG6vd6Cpo/82u6FbLaaNJ1I9A0Mguk59uLIsR8fgavMGlFs8HiLpoFxbXR4uyQ562W5mjQ6HFvIZiCSobW93TQMQRBAUjuCYvfXX24OhmRZATPI7STduj1W'
        'I+IKpVu3v5DLZDu7e+pdSoXSelmB5xcx9qkByPj0rW9/x+FwSpKzoOerJeV5oUlVz83N9vYPFjR9aPMWyIxvmkZsx05B4G3rxPJ6gV8kJWgaRnPLhnsa3npZ'
        'gcvf+1hIwLKQzYbbI30DQ+g651PV2IsjF7LZDW2RCqXrg0GeF4qmsbGrB0jhxpDtCh85mIZxbm4GbrVFsbZCyxVaafB6KpSa5mK4vUPXNH8gUCOKnV09hFg+'
        'NQC/yReyWUKsGhF7vN50MvHOmVMixk3+QIWWC5rWEtpQ55CKplEvKy/s2Dk+NhqORJp86vpQqESIT1UdknR+drZvcDCdTDgkiVikRIjkdKaS89Wk7759ul6W'
        'Jcn55sH9Z8+c5gWht3+wXlbOvn36ZhU37FMD6UQS7A82qWlAkjGuoGt1Dqfb633rx0dA0nB7pHdg8CNd29jVw3FcLpMl5OIKkobbIrbZxCFJgiAQywIlC3/D'
        'zRTcwU9Pxqcn4kObtwxtjlZLWtDzoljbHAyCpAvZLJgyZVk5dvRILpuxS199UfWgS1E2PttztUJf+uar9zS8zcFQOpm4v4V05NAB+D1UL8uUls++fXpqIn72'
        'zOne/kERiwhx5+dm3F4veNgA3ZLMXUwVokch2wLUuIHvnktWKrRCabloGnUOJ/yqBNuoaRjpRNI0jaJpTE/EEYeKpnHu3Iyua26P99jRI25PI5xW3B7vhVy2'
        'Qqmu5aFEGc8LUxPxEiGp5DwhBAot0TJdyGbOnZtxOKSCpvP8jVBWQixIV2eT6nr+I02jtAx1iyilxaKxkMtIknMhmxUxnpqMT0/Gz83OYFxbTTp+YnR6Ii7L'
        'CqXl8+dmuetcLpuxC0uViHVudiadSpybm3E4nJSWV5A0nUwUNL1ESNEwi4ZJiFWhtKDpUF+taJgLuQzP86JYe35uBih8/sASSUURQzY9kLSg56cm45IkwYaX'
        'lIhpGHbpK/QFLaBYLBq5TEbE+J6GF37Z3N9CKprGQjbL88JCNlPQtFQiAQtekpxFw7QbiBjbpPb23KUo4baOR6okHjOb3AKPPfZYjYivXLr0pcdWrVq16srl'
        'y6t5ftWqVXZE2t0YNB9/oo7ScoXSNWvXVsr02qfXqvuslOlqgV+16rFPPi4+/kTdtWtXr1y+vIT06tWr9/rkQHr50qUHKGn141FaRgjZz3/LoVjSZ6VMy7Rs'
        'P961a1cf5czJa9etu9fhve+FZA/7LddJ9UTAU1XPFNsVokc5J41thbhy5Yrb7VGefvpCLkcp/fTTT69WKrBnWW4nWeJK1tnVa5pGczBULl8JBlszH7zfHAz9'
        'ypNP5j/8cGNn9+NPPP5xsRhu67h85RKltDXcbppGjVjj9njzH35okzYHQzU1otvjhXQphBAwcdi2DvsFVLxFCAFvjVgTDLbCA8B9OS8I0HKJtQSSkSwnLZVK'
        'ff2Duq6JGHd29ei61uTzOSQp/+GH65tb1q5ZW9B1Sum1a9duNxSffvrpEkmhQ4+3Mf/hhS/w1u9u4tnthcQLAiyn9c0tS4a3ORi69uk1SikcomFO77iQaIVu'
        '7OzKZTNPOBzGT3967dq16pW5aXNU12/su0WMe5/rN00DIQTrxJ5TxFK3okfVggzxRhvaIjt37f7d33rNLgBELAI+euAcV13O6Za53sLtkei2mK7nXbJSIuQH'
        '3/9rcN2ClHwQdwGedCVi2WV6NC0vywrE8EFI343cLcn51vYIxrUIob/f+/of/NvvIoSOHNrf2hapweKpseOtbRF4TjvPXSo57/MH4LMjv7anoGmpxLyu5b/+'
        'zdcQQv+Pf/N7IOmLX92NEBofOw6xestJC5pmPxX0CccuaN/kDxw+tD/c1nFLX7++/iE7aKxa0hoRy4ryg+//9SO7H3QpykvffHX8+HHbOfHP//J7MKd2LkIY'
        '3urchdVzeseFFG6PQFf79r5uL1FYtFuHYzCnbx7cD5XLXty1O5VIQLAmeHqyDIaP4q4w3B6JbntBVpSNXd379r5hGsb5uZl0MqFrWmdXD0KooGu8wHd29+h5'
        'rUn1L2SzkuTc+GxPsWj4/Gp0ODY9Gbd3N7Av8/kDULTs8KEDDR6P29MoYlEUa7/17e8cPnigSfX71ADP87zAy8pTPjVwbnamd2CwREi9LEOB8HCko6DlO7t7'
        'OI5zexubW0L/5U//U5NfLVkWQlw6OQ+xIiVCjv3TEYhWLuhaONKxmufdXq+IcXMoRIglirWEWOdnZ+sk6UIuy/PCe5NxW1JwwYVbeQ5xy0ldiiJJTuizREhz'
        'MEQp5TjkkCRRrJUVJZVMQFH2vv7B3v4hjkN2tNzGru6SVaqXZbfXa0uay2TfTyXqZflj05Qk56MWw2DfFaZTiVw2s2lzFAYN5hRiLquHt1ymLaENy+f0dgsp'
        'l8lu7O4uEZJOJiq0wnGI47jYjpESsRDH9T43eLVCYy+OSJIzl8lC/OVbR49UyhUR4wqtNHi8sqIUTSO2Y+QjXXtkzcePqCrUNW16Mp5KJi4RYnvGwbX9R7p2'
        'fm6W5wVKKbGs8ROjFUodDufUxLtXKzSXyeiahjE+NzsDvl3wQWJZHMedn5t958wpKI/nkKSCpvG8cCGX1TXNIUm5TJZSygu8aRgYY9Mw3V4vJE2oUFojYl3T'
        'ioZJLKug5ctlen5uxuFwFg0TuioRcm525mPTTCcTuUwGntMhSat5HiLbIGAWnFTOz81QWnZ7vaZhlAhZyGUWslmQ9PzcLEQcc4i7JakgCFo+D9q5XKaUlulN'
        'caAaEYSXuFxPvXX08PRkHAZzejJOLItDCL7b1ZLqmobQdQ5xRdNIJuZX/rLZt/X28H6RtCGlNJVMwKBhXFsipESIiHH18FYoveWc3m4h6ZoGC+n9ZBKh62CW'
        'oZSeHBsllnW1QpOJ+ZbgBi2fL+j5qYk4xjiXzYhYdEhOEWNZUVKJ+XfOnMIYv3PmFDsgM9wiWRsUSr/vTtyeRlopFxcNt9drGosIoRqx1jQXHQ6n/T6EefnV'
        'gGkslim10x06HE7TXLwjOzgkFxeNOqcEWWeA9G4Cp25HCj6VuewHEIW2/Pnv+FSSJC2R9FG+jF8ZAi8sGV4wpyyf07tZSCssRZjT280UKwGKHvEs1i5FgZUH'
        'EaMuRYEXsARvuT7sBrbSdCkKqCS/GoDeWtsjCCHTXMQiLtOyRazVgmAYBq2URYxz2Q+wiFcLfDIxX++S4aLHITntTJzEsgSBRzcTxFe/EDG2HxWugaArPZ+H'
        'roAUmoFCv93j3Y5UEHjTXHQpCjxemZahZZlSeP4l4i9NuqUohmHksh8Qy8plP9Dz+Wo9CI/0yP5+XT5oZVpOJuYNw7CXx+3m9G4WEqwNu3+YDpei5LIf1EmO'
        '6nUODeyZYnrw0d0VLkk+/Ju/83vgcAe5Bk6Ojd5uV2j7QMALuHoDN2M7dyGk9qsR8eFD+6EBhHDYl9wnx0aj22IlYp0cG7VzOkA6BqjpA2ns7JYIIbsruFOH'
        'rm5H+od/9N1UYp5YBOL574m0XpYxrj15/BhYSGzSvoGhVGIeIfTmwf2t7ZGCrvl8gXAk8oPv//Vv/vbvIYT+4e/egNR7hFzs7R9ECP3lf/0ze9BgYPv6B+tl'
        '+Yff/96jljxZxPgP/t3/9t/+4s8RQt/+7X/9p//x39tLq/qX65I5nZp8t69/8C4X0suvvHb9+nVYvbKsIIR6+geIRaD6GLT0+dVSifz93tejvxpDCO37u9cf'
        'tVTV7K5w+SHuxuU9rMjzc7M+f+Ds26eLhiFinMtmwONkuecHvOlSlG/9xnc6u3oO/18HRLG2XC5LTmd0OOaSFcnpHNq8xe31EmI92927+2vfODc7A9EUkN0P'
        'IW7rcOz87OzG7m63xwthIU2qGtuxcyGbiW6LOZzS+mAo3NYBPhDpZKI5GHI4nB5vY7lMBUHwqYEaETcHQyVCbkmqa/l0IkksS3I6O7t77on0L//iz+pdStE0'
        'Ort7qknPzc4gxJXL5ZZQKJ1KQIV1XcvTChVF0TSNJlVFiBMxFgQBgurAyoQ4LrZj5PDBA7wgVCil5Qqt0D/4t991yQrkJSwUNBFjeAHeP1+8fQrUhCKEIIQW'
        'shlIjwY/2vP1b0xNxt3uxia/umROo8Oxu19IZ8+cWshmYPXu/LU9U5Px8eOjnd3d701ODG3esmlzdHxsdPzE8TqHtJDL9PUPIg6N3/yVz/TgI6cKtw7HOI4z'
        'DWPo+ShEmwBiO3bC1QlCXIPX87Fput2NpHTbu0JiWTcMFw7JIUktoQ2QavDYjw/XSdL52VlKy+lE8jpCoojPnjntDwRMY5HSMsa1GGOe5xeyWcnpNA2DF/ii'
        'aSDEQXItQqzpiQle4FPJhNvrnYrHHZIE1dd8qqrfvFx3SBJEFNySFC7O+wYGXYpiGov3RCrLSoXS6PZY0TSrSeGqviW0IZfJrm8JXiIkmZiH4IStwzGH5OQ4'
        'Lp1I+AOBXCbrafQWtLyua6KICSEul+JwSKUSyWUyuWwG1Oi+va8TywJ7i/3C4XT6fIEvntkEDCAg6ZK4mtWr+a9siaaS86D1bjend1xIEM8Dq1fT8r86/ALP'
        'C5AD0aUoU/F4hVbcHm+F0tb2iK5piEPTE/Hotlj1F4EdkBk+K0KtbWvWrp19bzrU2nr50uWZ6cnO7p6iaZiLi8rT7vyFnMPpXLNmXf5CTnnajRBKJROdXd2m'
        'YcCL/IcLl0uX6iRn0VhcW7NuzZp1kJPuypVLyfn5gU3P5z9cMBcXm9RAfmEBGhSNxTrJeUvS5PzNLISBwL2SXr5Ugs8uIb1wYeGO1hKQ1HiEHTLu/8YmEFh5'
        'Tu+4kGamJ1dYnLCQ2DgzVcjAwMCAWJmnOx+c4b7fdrhfcq/vVwNw8Q9u+u9Nxje0RaoDAxBCcD+tazfLgcqKHUiAEIJExPWyPD0RF8VaEYtwCw7hGQghSGRt'
        'WzPqZblwoyy6aBfktatNAamdBDsciUCpYujq5NgxKMs7NRkPt0UeCCnICABJfWpAy+cRQj5VHT9+PJWa/4zuR48y+vqH7HUCc2qXebrvhbSkDpS9zhFCU5Pv'
        '3mUoPbsrfFTWn9vTSCs0OhyTnE4oYOKSFULIt37jO3Bxsz4YKhESbo/UiLiga6ZhchyitCwIQo2IIcGfT1X3/+O+Jn9g/4/2RYdjfQNDzcEQpWWPt3Fk1+5z'
        'c7MIod6BQYxrwbe5ORQyDaO1PSI5nat5geNQcyj04q496eR878Bga3vEJcturxeh653dPQvZTGt7hBd4SKNUTWoaZmd3T2sk8g9736iXlWNHj2zs6hExvlqh'
        'kJ3J7fF6vI0PhLRELIckHfunIwu5DEgKCcH27X2dQxxCKJfNRLdtB/sA+16t8EvXJT8FQeKw0pqDIcRxpmk0B4PH/umI290Ic8rz/GdcSA6H8ytborlcJrot'
        '5vF6SYlEh2O8wBcNs7W93edXF3LZRzYkHDG/wmrUyzLU6xAxtqwbv1Rv3hwg7sa/CHZAsqJYxKqX5RoR/+G/+y68k0okoMCYyyXLijKyaw/GtQVNgz8IIYuQ'
        'ErlRcaJell2y0jswCL/egVRWFPjv4YP762WZWNb48VH4je1TAwVN6x0YhJzG4baOJaT1slwvy+PHR+tdiqwoW4djPlWFH8mKIiuKiMW7Jy0RsgIp7CZ27tpj'
        'SwqksJ1pUv3RbTEEmSEQgj3pLX2YwHck3B4Bb6TbtfxCKkF4AUuuaotN7Nc7d+2x57R6IVnWxftZSCdGTx4/1vvc4PiJ0RoR9z53Y04hWeHNpc3A7goRgu8k'
        '1I3VtPwKNQ/tIsI3/JZdcr1LeT+VqBHF6wgVdM12Noxu2z41EU/fLMFTI4o1NTidTvh8AYtcLOha73ODqeR8+iZpQdeg+E69S7l+/Xo6nQi3RTQtDz2kkvPT'
        'E/GRXXtSyflLhDzjU6tJ7ZbV3o5wSoUHfoCkUP8XQlBst0p0054uy0p1CV3bbRPdxivTvn+4XUv0xXVlhSVnH07tkYThbfKrMBEju3Z/xoVELAuqQcGKnbo5'
        'p9OPdtoFpgoZGBgYEDObLN0M2lmMYPcEhTchXiKVml/igu9XA/UuZfn74faIHapR71IQQvZtN0JIFGtTqXmXS3bJCmRsRgjZMR5wNV5NCvlmoGKn/VnoBw5W'
        '1S2rSSHF0+dK+tAqcD6yGNm1Z/zEKBRNvaeF1PTzidTsLadLUXy+QEHP2ya+KbYfRMxsgpYmp4Hrm+hwjEOoTpJaQhtqRAyJVZqDwXBbR7i9Y3oybkcLbNoc'
        'fefMqdiOnc3B0Pm5mZdeeVWWlYKurQ8GfzI32+RXG7wej7fRffNPnSTxvPCtb39nIZtBCMV2jBQ0zacGIOUch7glpHu+9nI6mWhtj4TbIwhxfYOD/GrB7fXC'
        '7fh1hJpUtUQIL/B9A0O5TLZ3YAAqNHm8jelEYn0wOD050ds/+DmROhzOjV09kuR0SFJ02wsch3RNs+siMKB7j3+HHDzh9ggk2X1uYMg0Ft0e770upAqlDV7P'
        'saNHfP5AhVZSyfmRXXskyZnLZrZuj01Nxiu03KSqhw8eGNm1B1YvG3+mCn8OsJ7Ovn16z9dePvbjI/5AAH6dFk0jnZwv6Hk7ibRpGO+cOUUp7ezufuNvfwDm'
        'lCZVfefM6eZgqMHjRYiTnE4tn8cYpxLzDR7v+Nio2+ttaQmNjx0f2rKFFwSHJFUo7e0fRBxKJ5Jbh2PVpJUKhZCV87MzHm9jiZBwW6RUIg0eL9T5HNoctUsC'
        'ebyNFUrLZQqkJUJ4Xni2u+fsmVOfE6mIcUHTTo4dQxxXIpaua1CvA+4NHU4n2zOie83ZVaHEsgghhFjEst45c0rXtNb2jntdSJRSnhewWCti7A8EHJJUNMyT'
        'Y8cope+cOUUsyyUroljbHAyJWITV+4UvssruCtG93mQjhJKJ+ZFde2x/LshZvcIv8+i27T/8/vdGdu2BZAealrcPLBaxep8bhPc3tEXABcwOsJ+ajMPxp6Dn'
        'oWU1KRx27A9axIpu235q7LhFLLgOrxFFhFCJEOgBIQSujhaxsIgtYvl8Aci8/XmQJhPz4JVm52FGCPX1D50cO+ZSFCziR8T6gR5cggafX52aiIMlyr542Toc'
        'u9eFhEUM0wQGwJNjoz6/Koq19kxB5mqEEMzvD7//vSWkDMxswsDAwMBcrPuHoGx2uL2D47jmlg3NwRDHcSvUclpS1IlSunU4JmJMCNm0OQp+W5Av2u3xhts7'
        'dF3r7OptDoZSyQSkGKCUdnb1CoIgSc7mlg20Qn1+tbqlrmtLuuIFASr+eLyNnV09qWTiYZLaQ9HXP/RIVYP851qTMI/3OqcOSYJlTCmF9Bns/Mt2hUsByUrT'
        'VZa1cFtE1/KiWBvdvv1P/sN3o9tiIhYPHzrQ+9xgiVjLI5Zsv7Bwe6S1PbJv7xsvv/IaQgjSAkLc25LoNBGL0xPx6HBs/PhxhFA4Ejl8cH90OHbLlulEsndg'
        'YPz48SbVjxBKJ5LhSGQqHoewKoissll8amAqHn84pBCTB9cI7NvycFRhk+qHpXivcwoxkW8e3P8f/vTPxo+Pvnlwv+3MOLJrz769r7PhRY94tMlL33ztpW++'
        'Bvks4cYaFlAqNZ9KzIfbOtLJeWIRl0suaFq9LNtpfkWMIS7CrwY2tEVcitLaHvnh97+HELKsi5Z1UdfyoEfQzVhdEYslYvlUtaBpTf5AX/8QLN8mn/r1V16F'
        '11C9LByJQHsI5CgRYmdRDUciNaI4smt3vSy3tkei22L1stzkU0Us1ojYsi4+NFKE0Ia2yIa2yCObffohY2ryXZes+HyBe53TdHLeXr1/8h++++bB/S5F2dAW'
        'gQtxpgcf9QMyeHscPrT/8KH9dvI7XhDAD0bghYVsVhTxjYSitFw0jTqHcyGXCbd10Aq1yz+ZhlEsGno+j8Vat6cxlZwv6Fo6mXC5nioaJiFWhdKCppvmoijW'
        'Fg2zaBoIIZ4XpibiJUJSyXlCSDqZODc7Q8t0IZs5d27G4ZAKms7zN4J2CbEg6rlCqWkY6UTSNI2iaUxPxBEHRu1EQdNLhBQN86GRnhwbLejaQi5jstRbD2Wt'
        'NgdD6WSC5wWeF+5pTqtXr52WuFg0cpmM3Xl1FS2wX7NhZ2aTB4PHHnusRsSUlhFCq1atqpTpaoGHVfj4E3WUliuUrlm7tlKm1z69ViPiK5cufemxVXbLVase'
        '++Tj4uNP1F27dvXK5cvVDa5cvrya51etWmVHuUGfdsuHRspmGf3z1UK5pzllg8YOyOguKzqF2yNQ7aivfyh8s3ASrLnwzYJK1SVy4H34CFgq7D9bh2MuRQlu'
        'aG185pmnn264fOmSz69ClTLIxb923dpIx7NXr171+dX1weDVq1dDG8Lrg8FVq1aF2zqgZWhDGFr6/OrVq1effPLJ9cEgdNX4TNOqVav6+geBDl40PvMMtLxv'
        '0r7+wWvXrvrVwO1IA19eD1KH2zqWl7ViQA/Lx+uOcxr48npZVqDyJywkl6LAMrZX75IgeoZHfVe4dTjWOzB4+MCBcCQChg4IVyoRq6d/IJ1MEIvs3LX7d3/r'
        'NTv47KVffxUhND52nJCLcCOjaXlZVrZsiyGExsdGfaqaSiQKmmYbGew0gqnkvM8fQAilk/PwWQgMmJ6IA6ldpgf6rBExtEwnknA9Z3/QbgB9VsdXQVf3Sloj'
        'YllR/n7v6+C2tpwU41qE0N/vff2lb76qa/l9e99gG0P0cENCwUJSL8srzylCyKeq/7D3DcjgYC8kl6y0tkUQQn/yH78LaS/6+od6BwZ++Dff0/N5O+SU4VF0'
        'pkklExey2amJd3leqJMklyK7ZIUXeAjSOHvm9LGjR9LJRCqRiA7H9v9on4ixy6UgDpWIFY50NLeEXIoiSU6oxp1Ozh8+dEDgBZ4Xxk+MbuzqBv/VcKRjNc+7'
        'vV4R4+ZQiBBLFGu/9e3vHD54oEn1+9QAz/O8wMvKUz41cG52pndgsERIvSxD/fVwpKOg5Tu7eziOc3sbbVLos0RIczBEKS0R4lJkUayVFcU0jHsizWWy76cS'
        '9bLscikiFjnELSf9L3/6n5r8asmy0skEBHWxW0L0cENCP9K1qYl3X3hxZOU53f+P+9wer2kY9kLiBZ5DXL0sE4sQQgoFrfe5wasVOjXxbjqVAD0YHY5NT8aZ'
        'n82j61doGoZLUXied3u9GNdCqaP3JifgBtqOSpZlRcQ4lUhAtjhe4Mtlen5uRhAELZ8v6PkSISVCdD3P87xDcmKxFsqMIYRW8zxEQUFNn6Jp8LxwIZfVNc0h'
        'SaBGeYE3DQNjbBomHG0KmlahtEbEuqYVDZNYVkHLV5OCoiyXKaVlSqlLkQs3iz3dK6muaQhd5xDH8wIkZF1O6nA4i4YJZaQQ4kQRuz2NX6SKS78UaxWSV688'
        'pwK/ZiGbEcVaeyGVCKkR8bF/OsIhrmga52ZnrlYoONPA1l7XNIzxudmZL1gVLXZARvdb+VOqEWtNc/GORz8RY4fDaZqLDocTIZTLfrByQsPiogE3d3o+7/Y0'
        '0kq5uGi4vV7TWEQIAanD4bTfh+AnvxowjcUypXYlxiWkECa1vCtQwfdEahdovx0pOw7/4txurzyn1ZWUqxcSK7OFmNnkLmEYRi77AawkMInARfXyq2ViWYLA'
        'gz66pR6Eu2q4kcEiXi3wej5f75IRQqa5iEVcpmWLWKsFwTAMWimLGOeyH0DLZGIeWmpa3iHdSGcAiskmrZMcCCFoWaZlaGl3dR+k6KbD+XJSe0z+uYxaK2gE'
        '9EAts78UPpJ3nFN79doLCdY28wBlu8K7+hpACuWRr+5GCKWTiZNjo9FtMZcs65o2fmIUIVTvkqcn4qAca0QRUvudHBuF3AfwcWJZI1/dA355dnUnCJW3kwDW'
        'iPjwof2QqcEO2wBrCZCWiHVybDTc1mFXWbK9nSFLoN0SIWR3BXYS6OoBkp4cG5VlBTJUV0v60CL2gQv0lE0qYvyHf/Tdff/z9amJeGt7BOJe4PFEjKtnKpmY'
        'b22PFHTNfn67wXKvoF/w1Nm2rWNq8t2+/sG7nNOXX3nt+vXr6WRiajIe/dUYQuiHf/PXLO0Cuyu89Qr71m98x+cPpFMJt7vRNA2eF7YOx87Pzh4+tN/nDyzk'
        'MtFt28fHjlNK93z9G1OTcZ8/MLR5S7ito0Ipuo7SycRL33xtZNeen8zNbuzqRhz64d98zyU/VS6XJaczOhxzyYrkdA5t3gLlvZ/t7t39tW+cm50RMW4Ohtze'
        'xtU8jxAHpBu7u90er0OSEOKaVDW2Y+dCNhPdFnM4pfXBEDhSbNocTScTzcGQw+H0eBvLZSoIgk8N1Ii4ORgqEfKgSJuDofNzs7lMZtPmaLWk01Pxh7NVBBZe'
        'EHhBIJa1dTjmUwO5bEYU8flzs7KsrG8JQvJ6eLyXX3ntJ3OzpmHATMmysr4ldH5uJtzW4XBI5+dmoGXlKv3Wb3yns6vnI11ze7wuWdE17Rf8jkyWFdMwXnhx'
        'Z3Q4dvdzevbMKbi2LhHS4PFCfZuiaeQyGZeijHx1T6GgsduPR10V+tVAc8uGc7MzH+naW0cP+/yqPxAoaHmPt5Hn+YVsFs6MAi80B0P0Cl3IZcq0/KvDL+Qy'
        'WV7gU8nE2bdPuz3eL3HcW0cPcxw6NzfjkJxQCsohSS2hDZD179iPD9dJ0vnZWUrL6UTyOkKiiM+eOe0PBExjkdIyxrUYYyCVnE6w3hRNAyHuvck4bDOnJyaA'
        '1O31TsXjDkniOI5Ylk9V9ZsGEzBrlAh5UKRHDh1o8qscx+VymWpJP2/Hi5deebW61IbD6fT5ArlsJpVMpJIJSun5uRliWZLkvH4dhds7zr59urOr51KJQCHW'
        '8bHRMi2H2zpSqQSl5c6unvdTiTqHJMtPmeZic3DDR7p2fm72/NyspuUdkmTbx36RARk31geD9zSnFVrheaHB66HliqfRS2n5vcmJG3OayUxPxpkeZAfk2yLU'
        '2oYQSiUTly+Vbq1DA4E1a9at0KC6qzVr186+Nx1qbb186fLM9GRnd0/RNMzFReVpd/5CzuF0rlmzLn8hpzztBtLOrm7TMOBF/sOFy6VLdZKzaCyurVkHpD6/'
        'euXKpeT8/MCm5/MfLpiLi01qIL+wAA2KxmKd5HxQpBcuLLAvwy+WQuzuuac5nZmeZIPGVCEDAwMDYmWe0D1Vd4I8SMQiy9N1LLlQh+pO9bIMISXpRNLO6QIp'
        'YexgDzs1tF2dBwwg0BIhBImI62V5eiIuilCLFkHci11Qqd6l2NaMelmG2BK75QMkrZdlWVFSiXm4d08n5+/mIHy7QAW/GujpH4CEPWhZoma7zm8yMW+bOCA+'
        'DCIo7KddYXgRQmCe8qkBLZ+HQAs7vZjdCbFIOjm/8vC+eXA/ZHmpTseNHlbOanRfsVIrz6mdUw7kWl6MjIHdFaJbVneiFepyKeMnRvv6B31qQNc1Smm4PVJ9'
        'of7nf/m991OJDW2RcCTi9noP/OgfGjzeY0ePxHaM8ALvkCRwUe7s7iEW8amqaZid3T2tkQjP830DQ83BEKVlj7dxZNfuc3OzCKHegUGMayktQwUl0zBa2yOS'
        '07maFzgONYdCL+7ak07O9w4MtrZHXLLs9noRut7Z3bOQzbS2Rx4s6fTEu6ZhmuZiLptpDoaKpoE4zudXwfl863AslUzcbvTgy5lKJvxqwO3xIo4TeKHB452e'
        'iP/vf/KfL+SyvCC8/MpruVyms6snHOkgFokOb18fDKVTiRd27PSpgVwu09s/6JKVw4cONPkDx44e+dg0Vx7e/f+4r8kf2P+jfUXTqJeVfXtf5xCHEDp29Ijb'
        '0/iTudlcLgNz6vMHVh5egRfqJEnE+GqFwvM/hEs0cJa+11tUcPhvUtU7zWmHIPAuWXFIUnMoVOeQvvXt77yfSlBK1wdDJUJYbAlTheh2FromVe3rHzx86IBL'
        'Vtwer65rbk9jdYrm91OJ6HAsnUi4vV5KqWmYPC/s/LU9vCBUaKW5JcRxHMY4l8n4VBXWuk9Vx4+PyspTEJGykM04JGed5HxvMr7p+SghlkOSeF7wqQER44Vs'
        'xqcGdC0vOZ2reV4QhKmJODQ4e+Y0RBq4FKWgaeuDoXsiXc3z9fJTK5OWrJKIxd6BwRKxjh09omuaiLEoYgizc8lPrZytGhpIkpPneUJILpMB00fRNDZ2dU9P'
        'xIll9fYPlggpl+n0VFwUsWkYH5tGvSxTWv5I05qDGwRBMI3FltCGJr9Ky5WVh7eg5VtCG6Cclj8Q4HmhXpZdiuz2NJaINbR5S8kiLkWG320rDy/o1oVspmga'
        '8PywZXuw5hS/GpAkp2kY4fYI+XllBL9IXIqyMmk6mdjY1S2KtUXTWHlOHZL0fjLpcDgbvB5BEE6Njb779unocGxqIi5JUnUecgZ2V3gL70JwuXK5ZLsgcvWx'
        'ItwegaI5mpYHJzXIW9X73GAqOX+JkGd86vupRI0oXkeooGvhtgi0HNm1e2oink4motticICtqcHpdMLnC1jkYkHXoIf0zc7hs3Aovn79ejqdsLuKboulkvPT'
        'E/GRXXseLCk46Mmyckv3uju63d3O3zDcHoFKeD6/mkomwKEPvAXBXWbJC3tU7TdvN7zVn0I3nW/AERKiLDQtD3O6oS2y8vBCP9XPv8SZ8cGm2Fo+VjC8dySF'
        '4lmalr/jnBLLgkJO4FAJ9w92NWQGpgoZGBgYEDOboFtuW2zzAkJoSQ0Tl6JA6irYDyKEpibjdtoul0tGCNl38E1+1Y7xgPiQepeCELItGNAYPgjhHHaNUIjx'
        'AHMH/DK3u3popEv2fS5F8fkC1YVP7ax5G9oi6eS8HdZyH6S2uQB2bYWbp0L4yOcqqSjWQk4z26C0nPQB+k7CEtq393WIF/T5Aksktc1BkB5thUqzsCusLse6'
        'RFJ79S4hZTYTdld45zPL0OYtLlkpaFqTqo6fOE4sCxKd9/UPbezqWchl3B4v1BhDCLW2R8LtEYS4vsFBfrXg9nrhovo6Qk2qWiKEF/i+gaFcJts7MEApbfB6'
        'PN5G980/dZLE88K3vv2dhWwGIRTbMVLQNChC36T6OcTVSVJLaEONiHleEDHe87WX08nEwyHVtXxv/5DH600lE7aT89btsanJeLitA4Zi56/t8amB9I1zLudw'
        'OCml90fqkp+CPsPtEYck/WRu1iXLprnY2tbhkJyfs6SaiLEgCOlk4nakre0dzcHQ+bmZl775Wri9Y3oyDqviPtaYz6+2hDacm5uJ7Rjx+VW4yKsmHR8bbVLV'
        'wwcPyLJSJ0knx0ZHdu25wX5zIoCdWBYY8dyeRhFjUawFF3FbUp4XNnb1FIuGyyVXk6aTid1ff3maJSVELB3Ditc3GNeCeXTnrj0IIYg7blL9+/a+rt/w0gjc'
        '9N4g0xNxWVEKmtbXP4hxbWt7BBwaevuH6mUZKi6FIxFIjoRxLfh5pBLzNaI4PREXsYhFkVikd2BQxBhiWkZ27YYdSl//4FQ8Lt9MN5BOJR4aqSjWppPz9bIs'
        'YuySlXB7hFjW//Ff/rOez4tY3Lf3dWJZWj6v5fOalq8RcZPqr5fl+yaF4SWW9ebB/T/8/vegz76BoXRy/vOW9IaGUgM1onhLUnBXAreq6cl3pyfftVfFPSWD'
        'gE301ET8//gv/xmWGca1uq4tIQUXn5Fde2CLunU4BuwuRYGJqGaH20aocfj1V15dIunU5LslYvl8gSWk9pyyJOTsrvDOB2SI5QAfw5Njx1yKEt22/fChA8Sy'
        '7KwHJUI2tEXem4xXH1LgDr5GFEFt1buUgp63cwRYxIIjtv3Z6qQJU5NxLGL4CLS0HQPhAAhH14dACpfxBU0D2ZfYEKLbYocP7ff5VYQQmEHss+f9kSKEotu2'
        '2wmxwW7Q1z9UL8uft6SQYKKvf1DX8jDdS0g1LS9iHN22vdovElIhQCj0LSvBolsV7ax2VAQdikW8RFKXSy4RAmk+akQR1mGTPwDaECaiuiuwrvh8ATjmV0sK'
        'dxeHD+23zSP2AfmWXTEwVcjAwMDA7gpv8ztcEITmlg0OSXLJCsa1zS0bqssh9vUPNQdDuq5t2hwVMYYGgiDwghBu6zBNw+NthLB5KP9ECFnS0u3xhts7dF3r'
        '7OptDoZSyQSQUko7u3oFQZAkJ5D6/Gp1y4dA6pCkcHsHx3GUUofTaecus9O4wn7E4228ZRIXcEe/4/DapJRSXhCqvdvsBIUPbXhFjH3+L0ODeyUNt3eQEvH5'
        '1ehwDDx7lnvqiRjzguDxNlYPr9vjBVJ4E+PaoeejVytUkpxDz0eLRUPEWJaValK43IQMPQ6nEyFkTxCsyeXe7y5FgWQ2TJ2xXSG6+1KzcF9T0PPR4dhUPB7d'
        'vv1P/sN3ISdgQdPgOAbGSgjqSieS4UhkKh63yzlB9XQtn4dLnKl43P4vXDLe/G6I0xNxKNkDBbwPH9wfHY7dsmU6kewdGLAjyR4CKYSy2fkQx0+MRrdtRwid'
        'Gju+oS0yfmI03BbpHRj8oz/4PbiZAvfG6uPY7RwS+/qHYHhtUpDi8KEDkGEU/B/hAUCuhzO80xNxyPd3r6Twkfcm4z39AxCvCQsJDNy6lhfFWqggVs0L0sFn'
        'RSzWy/KpseP1LiUcifzg+389smu3PdrVpIcP7u/pH4CKTlCbCeYlnUja4tgXOE1+dWoyzkzGbFd4z/B4vW8dPTy0ecvQ5miJkJMnRh0OSeDX9A0OppMJSmmT'
        'X62XlRIhhFwMt3fomuYPBGpEsbOrhxDLpwZg+xBui5jmIkIcQtcdkiQIArEsCBeDv6Gwd72svLBj5/jYaDgSafKp60OhEiE+VXVI0vnZWSB1SBKxSIkQyelM'
        'JecfDulCNlOhlQavp0JpS2gDxtg0FsG27pCk/T/aRywrlUycPXOaUvqH/+7fh9s7Dh/af35uZoW4BRHj3v5BQeDXB4MwvDapx9soCMK5uZnf/O3fh0Rbz3b3'
        'YIxzmWw4Enk4w7uQzYJ5umiY90qaTiZaQhvSyQQtVzgOgUkaEqmtbwnBU63m+fcmJ6LbY/bwNodCJ0+M9g0MXUfo2NEjzcEQzwsLuUy9LEuSs6DpFUp3f+3l'
        'JaRg5EknkifHjkE9puZgCCHk8TbqmhaORHKZbJ0kFU2jQmmDx/uxabD9INsV3s+52C77Cb9XYQ/YpPrByQvu+H2+AOR2trcM1e5gth2wet+Bbgb/N/kDdkVQ'
        '2CMUNK2aFF5MTcaj27ZD4U077QJkH3gIpLZ9ZvzEKFzAw42+rmtgeQCjwR3TMYzs2gP3/T5fwLbAjOzas4QU3cxQv8TeCqmYH87wwuSC5+a9ktqGDlgt4Pao'
        'a3nwPwV7Dgj40iuvVg+vbegAi1O9S0ml5rGIbbMJeBdWk8JwLQl8shNtEHKxmhR6/kXOyM1U4S80HnvssRoRX7l0ya55JGK8atVjn3xcXNLgS4+tWrVq1ZXL'
        'l1fz/KpVq6qjxB5/ou7atatXLl+uETGlZYTQqlWrKmUK9UOgAaXlCqVr1q6tlOm1T69V9wktgbS6q4dG+hCG1ya1x3kJ1q5b99CG19bs90F6u+e/5db4Xod3'
        'CenlS5duN6og6d0/DAM7IN8Bn376aZ3D8cnHH4fbIxjXSpKTEKs13E4rtK9/UNe1JxwOR51DefrpC7lcczBUUyOWSiX4kYhxZ1ePrmtNPp9DkvIffri+uWXt'
        'mrUFXW8Ohq59eo1SCgeu1nD7RwW9we3Rtfy1a9ds0quVCqX02rVrlNLylSsixr3P9eeymQdCWiPWBIOtmQ/ebw6GfuXJJ/Mffrixs/vxJx7/uFgMt3VcvnLJ'
        'NIz1zS2faybnTz/9dAkpSOHxNoKVBoKF3R7v5yoppbQ13G6axvXrn4KhA2w1H5vmyqQ1NeKT9fVACjO1XN81B0MY14KJxiFJhJDOrl5aoTapw+mEbAsgqa5p'
        'sNjAaKPrmsPpBPYlkkIGB8RxCKHOrl7oKtzWYUsKKxZyPYCBxb61EDGG4b2j4YuB7QpvWNx+83d+b9//fL3JH/Cp6j/sfaPJr2paPtwegSMS5Ly7kUQvOQ8H'
        'KE3Ly7JSI+JUct7nD9g58tLJeft05rrZ4LmBoRpRTCUS+/a+DqdyXdeAdGoiDidNOFf+LFvfZyb1+QPVnwXf5umJOLSE2kA1It65a/fv/tZrn8ddO6RjgOuF'
        'JaSyooCtwKcG9v3P1x+CpAghTctjsba3fwDqZN0wEI0dJ+TiCqRNqh9e3M6jsK9/CIwk9pl9CSn0CY8Hh/QHKynGtWDz6ekfSCcThw8d8PkCqdR8dNt2nxr4'
        'oz/4vSWZR5iaY7vC22J6Mp5KJBZymZbgBl3L9w4MlghJJxOCIFQorZcVjkOd3T0cx7m9jc0tIZeiSJJzNc+7vd4SIc3BEKW0RIhLkUWxVlYU0zDCkQ5oIGJs'
        'GsbZM6cEQSAlsrGru2SVctkMkPrVQGzHyEe6NvT8lv0/2pfLZjxe7wMhbQ6FCLFEsfZb3/7O4YMHmlS/Tw3wPM8LvKw85VMDuUz28KH96WQilUh8HqNKCDEN'
        'Y2NXj9vrrSZ9P5Wol+WPTfOdM6enJ+Mu11MiFu8oKcchhySBpOUybQltuCdJN3Z3Q6o+CKN8b3KizuEkhFQq5XCkYwXSdDIBkX8ixtFtL3AcgmSOuqZBZN7Z'
        'd07RMq2TJJciu2RlOWm9LPMCzyEuHOkoaPkHK+n0RLxOkoqGyQs8pHTr7R8ES1c6mYAaJrCvJJbF0nMxVXhbswmtUNMw4FdlZ1dvKjkvirVurxch9H4ySWlZ'
        'xNghSQVNJ5ZV0PLlMj0/NyMIgpbPU0oFQSiXKaVlSqlLkQs36y4hhFbzfDqRpJRSSt+bjDsczjpJqtByQdN4Xkgl54HUNAyM8TtnTmGxFnzNHhSprmlF0+B5'
        '4UIuq2uaQ5JymSyllBd4INU1LZfNwOk43B7x+b+8cl7Ce0VzMIQ4zu3xLiFF6DqHuKJp6FqeWJbb00gpvaOkDkmyJa1Qeq+Swpyeffv0+8nE+bnZZGIe49qi'
        'afACf0fSgqaJGJ8cG52ejOuaRiwLBm16Mj49GRcx5nne7fVCptvlpAVNg2BBXdOKhvlgJX0/mTQNo8Hj/cncbDqZODc7AwsJcZy9sOGZmXZjB2R0H4k2q8vF'
        'QrQTLCaHw2maiw6HEyGUy34ALYuLhtvrNY1FhFCNWGuai3D1Xlw06pzS/WUHeSCkbk8jrZSXt3Q4nPD+Q7h0lyRpZdKHI6nb671lCWAR45VJjbu+XFsuqU3q'
        'VwOmsVim9IFLarC7P8TSMXyegMhNOwYe/ogY00pZxFgQeNNcdClKMjFf75LLtKxpeYfkNAwDGuj5PBbxaoHX8/lb6kER49vF9sP7xLL0fB54TXORWFYu+0Eu'
        '+wFC6G5IwXvZNBexiMu0bBFrtSDYLXPZD/R8/vPWg+AiU00Kj4cQal2WHQB0hCDwoBrqJMeDkhRaQle3LLi8Mundp/ZYgRS6AiX4YCW95fPA8IoYwwi7FAUW'
        'lV8N2Fly2Xec7Qrv8O1NJuZ/83d+T9e08ROj9rHiN3/n9w4f3N/aHiEWKRGrXpYxrj15/FiTP3D40H47ZYNLVuC+3E4K8ObB/bdL8nyX74sY/8G/+9/+21/8'
        'ebgt0toWmZ6M14h4ZVI7tV91SwhygJZvHtzf2h4p6NrnGpkAgtgZlRFCEM0CYS0vv/La9evX08kEJFwARznw0bNbgn3js0i6hDTc1lEvuxBC4yeOR381Buln'
        'ljzeEtISIbfcTqKfLzxS0DQ75GM5qV2uq7rO1L1KOjX5bl//4BJJU6n5epcMUwkDvnU4tpy0eninJuPf/u1//af/8d+zUzO7K1zhjOM0DeP83KzPH6jQ8u6v'
        'vdzZ1XMhlzUNM5fLjB8f7ezufm9y4p0zp+tdStE0Ort7HA6nx9tYLlNBECCjV3MwVCIkOhxzyQrG+OvffK2g55c7rNxuIdp7h+ZgyCUrpmkUNI0Q0uRXTdNY'
        'yGbuSCo5nUObt7i9XkKsZ7t7d3/tG+dmZ6BDt7dxNc/7/IGzb5+G66fPbzBBkHB7R2d3z2qeR4jbOhw7Pzu7sbvb7fGePXNqIZsRMW7weAVBiG6LOZzS+mAo'
        '3NYhYrxpczSdTDQHQ59R0iWkRcP0qaqI8YVstsHjRQhxHBravGUFUkrLhJCVtQYWa8+dm/H5A7eU1CFJCHFNqhrbsXMhm4ntGLk/SaPDseWSuj1eh+Q8Pzez'
        'aXP06998jeNQa3tkOWn18I6fGF3IZliRE6YKVwJEwsd27EQIVWjl3bdPwxV7LpuBAHiHJDV4vJLkrFAa3R4rmiaxLJ+q6jfvuR2SRIhVIgTj2mM/PnxybJTj'
        '0MmxUb8aaG7ZcEu7hJ2ksxq8IEBuTrBsEMt64cWdDslZ0HTJ6VyZtE6Szs/OUlpOJ5LXERJFfPbMaX8gYBqLlJYxrk0nEvUu+UscRymN7dh5f3lJ7xKt7R0I'
        'Xce4FmPM8/xCNis5naZhVGiF54UGr4dSWqGUEGt6YgLC19xe71Q87pAkjuM+o6RLSCFEhBBS0LXmUIjSckHTVyZ95+3Tvc8NrjxEsDxuJykv8EXTQIh7bzKO'
        'EHqwkp4aG7WI1dnVs/9H+zgOvXlwf1ukY2XSs2dO6ZrG9CA7ID9IDGx6Pv/hgrm42KQG8gsLa2vWrVmzrmgs1knONWvXzr43fflS6eGThlpbL1+6PDM92dnd'
        'UzQNc3FRedqdv5BzOJ1r1qzLX8g9zLt2fyAApMrTboRQKpno7Oo2DWNmehIaPP10Q53kLBqLIAjk7Lty5VJyfv6zS3o70iWPtwLphQsLn1FSeJH/cOFy6dID'
        'l3T5VA5sen5l0s9jTTJVyMDAwIBYmSf0RTWeIIRuGdbe1z+EloXoI4TsYH4IDICM8OjujI+3q7q5POcwGB/D7REw10BmaTtUw06CbRc/sosZQYPDh/aH2zoQ'
        'Qg8zlXFf/1CT6icWgfiZ6rwGtgGh3qXYd/zVCSluN7x3lBQyWtfL8vRE/L5J72OUYHkAy0OTFDJ4I4R6+gcOHzqwc9ceyA8mK0oqMT81Gff5AtWkd7842V0h'
        'etQC76LbYpA40+dXEcft/trL64OhdCoxsmv3JUJMw/jzv/ze+6kELwjrW0Iixi5F7uzuWchmWtsjvMBD7qYaEXd290CJ8enJ+PpgqPTzxb+XezxwHGcaS7Mq'
        '2eXD7YtFqBruVwO9/QPFoimK2CE508nECy/udHsbpyfjTap67J+OuN2Nnd09rZEIz/N9A0PNwRClZY+3cWTX7nNzswghWVYavB6HJD3Moj+0Ql0uZfzEqM8f'
        'aA6FTMNobY9ITudqXuA41BwKvbhrTzo53zsw2Noeccmy2+tF6PrKw2sa5sqS9g4MgrM61Iq6D9KFbAbCe+8+aNelKBu7uh2SdN+k9yEpQpxLkc/NzQq80ODx'
        'ppMJCH3Zt/d1nhdMc9HnD/ACX016IZt1e7wQf8JUHlOFP4MsKyLGqWSCFwRRxIQQUcSmYSzkMv//9t41uI0ry/M82bIyJTMvXUJii8iURYAmkLBIQAIJiubL'
        'fKgtUyEK7pbpKFnq9qO2bFe3ez0zNY+q2Iqe3emY3Z2Y2Znt3YiZ3tnamoiq7Y1y1Gyoq7tlOSyX25JYkiw/wIf5MhOgCwBtZEKhTJSdF5R4QVn74UooFvWw'
        'LFGyRJ1fKKQUmMzHvYmT995zzv+cNs0n9+47MXT047TRP5AQRbEhEp3LZmLxloJpbo5ERUkqs3JDY1QQBEJILpMJ6joAvH/qHUVRru2kU1VtqWtSJqS1rTOX'
        'zSiKFwCWfgN96kb+eY2qzeUyacOYnhwXJanGp1HXTaeNYEhvam65ABDU9RPHjqraxhLlqnyZtaJYo278cCS5/bH+seFhnsnARZIvF0CGFS8dIwhEJvW63tXd'
        'G9TDMiFz2UxQD1tmXvF614qiJEmjw0mPovCkMV5oyadp125exti175RSlx/zhk/q2E6Juss64kvvdJM/UDBNXn3pS08qE+JRvDd5pwf/7sCJY0d5Pbyx4SR1'
        'Xa6E6A8EuAW8KKm95E6nJydEUfxStziuFW7E9JKKTBMXFODBcdxw8KjXwb3706kZruScTs3MU/pQUP84bVTJ8gWAG47Xu1qkIY92vEYwNhd34SoSsyljcO++'
        '0eEkV4fmM6yqKjI7a/Aocb7/1c61ssNt/mXjl7elKZ5OzcymjK7uXtPMFy4p99X4tAsXLszOGrGmOL/+/l2JazdvZc+r3WkwGHbp5wXL7Hy098ZO+pUGzpU7'
        '5c3LD3V77vSK+TOVB1hVtctPihYQTSGCIAig2+Sqr/RgMFwpY1LRRq6oWFdevDsHErxyRTo94/Op3GVRyRzg+QD9uxInfnX0ZgZcfAR6Pa/unQOJparFXP5r'
        '6RL7UqcKr+359Q69K+kWXNiZNxpPFwGA0ZGkz6deo3n5njxrghecWXan/Bd9qnZ86GilQulXPenoTSykcr2123mnl0uH8UIrlUNVnDNY9hPXCr+czp6euWyW'
        'S/kLIJQZ2xTwv/3LNwf37mtqbpmaHH/pz/4RX4Tu6ul74/WDfY/11wYCfHX8AgAXcRIl0ePxxuLxgpm/GTFUHv7q07TBb+2PNbeMjSSXPuXTk+NcG6pQMOtD'
        'YUpdSmliz1OK4qX0c3553J1SG6jbcHG9TJ/LZhznjGWaVwznvtVvmudf+G7RsSvNu0FRGqNbqmQiipJMyP5nnp9NGVub47HmOIDQ1dsrrpWu2LxdPX25TLaz'
        'p4cxting9wfqai/94Xf64suvzGUzAJDYM1gwzaAe5op+X+mkN7OEyvu9oXHLbbvToB7eufuJomM7ts071x8IbAr457LZTf6ATIiqaZS6vPf584NmDk3hlWGM'
        'jQ0nHdv+3vd/CAJwQSS+8KxqG/kwQZaJKInptNEQicaaW2JN8VKJbvIHPIpimWbfjn5enadg5Q/8/NWVEoUuswWesRfSw3zxfrHMHNsWBOCfjw0neXICgHB8'
        '6Agh1Vub45IoeRRv2pjZ5A+cGDpaGwjwShqdPb0l6saaW05b5u2UMg6G9Fw2MzUxXmnenQOJI798MxQO85Fvucwc2yakenpi3B+oK1F6teYFuOAP1JUZW1hg'
        'itdr5vOEkKV32tgYPTF0rO/xx3muTpmxzu7er3RSx7Z5Yc+b6cTbeaeObY8NfzA1MR7Sw9vaOk5bpihKoijF4i38pAUzXyWTxuiW906d5M8PmjlcK4QvDQrj'
        'k+JK5Z2l9XrGhpMlSk0zH2tqqddDJ4eOVQrrVMkyAJQovUUVdioBhpdXVqrMlPmsil95fSg8m5rhpYV4xJlp5ru6e6+hDXFLqSws8ObtfLS3Ei7HJ4CVQkgf'
        'jiRd6vbv2n3F5uU1lQCgPqTzwkadj/YuvdOl+gWjI0leo+orndQ08zfvVag8SLfhTrn+gmXmuRA6FwRbKm8BALwE6/GhI1d7fhA0hQiCIDhBhqtmgIiSxCvv'
        'CILAqxHxOAleG0hVtYbGLZIkiZLEywz5A3VcyqGru29ltaB/R2TU6+XXwOf1seY4XRLF3dXdJ0lSrT9ASDW/vFp/INbcIhPS2d13p02OfJrGm7fWHwiGHpYk'
        'idc8kgmpXP/lzbtzICETQildtie/U8syW9s6GyJR3hH8mK1tnZIkKYq3oXELK7NgSF+2J+/TWxFiwjU4Lj+pZZkreKdfelJUXsBR4Y1M5d44dPC5F14CgEqd'
        'oIqi3IlfHe3ftRsAZo0UT5YCAOrSWDxu5vM8X+prnIDwFLfDr7/W+WhvJTVwbDjZP5DgrpI3Dh3kpYq/3ubl2Wnp9Ezno70l6nJ5wcrfsXicFy26vHmDeng0'
        'maz8lxc+XnanJ44dA4BYPH740MH+gcQV95w1Up09PSeOHeO1QbjQ6U9//KOVapyQHu7o7jk5dGzLpTrLy07KH6EVuVP+6xWpxNGR5NLe5w+qaeb584wGDlDF'
        '+jqf4K3N8ZAeJqSakGrLMgumWaOqwZCuapqqaTzuoWCag3v31ajq1uZ4/65EjarWB3WZyEuf15UdDMaa49eWHY41x32aNjryASHVPOG0RN2grhdMsz4UThtG'
        'japWycSnaV+jHaw0L6Wf16gqdV3evOn0TFAP16gqtwVVsny15nXdz7kdgUu5usvulBvZWDxeH9SffeElvs2Lw8Xicb4/T+AtUcoFTX2qxvsUAFaqcTq6e376'
        '4x+ljJmrnXQF75S6tPLgVcmEyGTZSWtU9bnvfPe573wXrRtOkL8cHmTg2HaJulMT47lcZmpynLquIMAGj3d6amIum5lNGY5jl1w3nTYAoOjYY8NJEKDo2LMp'
        'o2BaJUrfO3USboGD+0vV5bigYUMkmstmuAOxaDtFxwYAUZRO/Oro2HBSVTUuxXj7wymWNa9P1TyKt2CZZcY2eLxltvDeu+8oisILJM0aKcexr9i8Rdsp2g6l'
        'bpmxgmk5zhlZrl56p6PDyRKl6dQMpZTXPGILbC6bmZoa93iUgmmJosStHqUuVwMcHUnyPqWuu1KxJgXLjDW1sDK72knLjK3UnU5NjquqVrBMl7rKxRRmeelJ'
        'j7z15sFfHDj8+kG0bjhBXnnW33//mjVreB4bz3B64Bsbzp9fvENSmpZeFWMLZ+fn76JWPXf27FpRvGLznjt7tkomjC0AwJo1a8oLjFdKqdxpmbF169eXF9j5'
        'L85XyeTc/Pzv3bemsueaNfd99pvi0kOdm5+/pQVeZEKueFJ+VStyp5df/7KTYpodjgrhBhbyVVVzbJu7TURJ2r6j37JM7jOpCGQRUl0qlbq6ey3LlAlpbeuw'
        'LLM+GPQoCqW0IRJdqbjCa+S6XpvKGnyVXBWJbM1lM7fOMwArVTzeNBfLZcbYF198wTf4iJhvLJw7x3+0uaHxk1yO73D+/PmlOyyWy1988QX//Isvvlg4d+78'
        '+fNL91w4dw4A1q5dKxPy+Wef8R1u6YO0fUd/NvOxP1D3xYUvav2B/Kef1tb6tQcf/CSXa4hEq6rkqz1I+U8/3dzQuH7d+oJlNUSi5784zxhb2qeZX3/cEIn+'
        'N9/8JpfPURQvd5cpipdSd2us2XFs9/PP0GGCphBurBaHKEnUdb/3/R+2tnV4FK8oSsFQeC6Xee6/fSnWFBdAYGxhW1u7onhNM98YidaHwrlsprWtg8vTCwI4'
        'jr1SFofXD6CUch9oQ+OWxJ7B2fQVcvK425pr2ziO3b8rYVn51raOWn+gYOX7BxKD39rf2d07Nprs6u691YI0NzQbuSgYdTW9HG7KZUK+/+d/4VGU2ZTB24Qb'
        'fe4t5XWclzYaKzOZEG5BPF4v3zOxZ5BHPt+GB2lrc8ujPX3clVF07P6BBFsob/IHGiLRomNf40Ha1tZRdOzNjVF/IECpGwyFNzdGl/WpAAKAsLW5uSGyhbp0'
        'kz/Q2dM7PTkRa47bzhm/v46X1caYajSFN16ZiKevHvy7A4qilBm7mCIqQIm6sXhLQ2PUp2mK4l0rirWBQInShkiUMVaiFOBC2rhZQ8Pz6sZGkg2RKKUuK7Nt'
        'be1z2ezo8AezaeOKAdKszKjrerzeWn/AceztOx6XCWmIRil1eYX7seEP5rKZ90+9c2eGVlSMO788XqeJUrrvmW/HmlvmS3TbIx21/sD05PhsaubwodcSe546'
        '8aujlpkf3Lvv4C8OUNft7O4TBEinjL4dj5fcEi2529raT5tmbW1djarOpozEnkG+52zKGBtJ8gH+rdPs44ddLLMaVfX5NJnIAgixeEvBzLe2dwiCUBuou9qD'
        'JAjgURRZrlY1bWGBNUa38B2W9umLL79y+NBr3AO+QVGKtnPiV0dr/QHHtjt7ekuU8uVFWSa3KLQLTeE9wWnLnJ6ccGxbFEWZkIJlMsYKpilK4sICm54clyTJ'
        'zOcZY5IkLSwwxhYYYz5NPTF07OYNzdhIkucdy4T4VC2dMsqMeTxeXkto2WBQkiTHtnmiGF9v8vk28mmjZZpFxxZF6eDfHuB1qdIpY/uO/jtnVBhrjvOhXOUT'
        'fnkVTxFvCse2F8usYJnWpeTuxTILhsKszIQLQq2/znHseUo3+QPTk+MCgChKuWymzFitPzA1NV5mC7X+uqLteBQFBMGxLw7bua8JLnl1bsUN1voDAgiiKHFB'
        'Vss0i7ZDXbdg5q/xIHFNSV7sqczYWlHkyaBL+/STXNYyTY+ifJxKOba9yR8gcvVcNsPffAAwNjIsiiJvE/xGo9sEVj7I2eN1nDMejxcActlfc6HD4hm7NhBw'
        '7DP2nTEZ4THYVj5f669j5YXbn2mHwGWBRI59ZoGxyorttR8kAKiSqx3nDH+9Fc/YG7zK0j69xiO3THwTAYwrhJsqWRlfZly4y0KSRP7sblA8AJAyZmp86gJb'
        'MM28R/HeHtfwl2Ll8zU+lV/nsury3Eoit/OdxJ+TpTbrSx8k27ZZeYHrBBOZrJXESp86zhkikwW24FJ3rSQtM4L8CeHl4bH9cVR4UxaQSwcfHzoaa2pJp2dq'
        'fGrBMrk2HM9vrw/pAFBJQTn8+kG+tsgj/m/dC9mnaS//43/67/6nv/jS5a2u7j4ueDc6kqzxqWPDycpg5GuRY7iXpxHc8Pk0jchkS1Ocp45wYYVrPEg+VZtN'
        'GUvVJbgaZld3b5VMKnvyGlKdl5QZ+aF8qmqZ5k2KZiL39Frh4N7977/7DmMssWew1h+Yy2Y6u3tPDB1rbeuQCenflfB4lc2RaKypRSZk+47+2ZTREIl6PF5/'
        'oG5hgUmStDkSGfzWfp+qLRUZXMHv1Vw2c416KVzisFAwt+/o79vxOGMLTc0tH01OiJL04p++EgyFubsAn3K4jfpvvLMG9+6by2aPDx31qRup6ypeb9+Ox6/x'
        'IAX1cJVMGiLREqX9Awmfqileb/9AojYQoNR9pL1z3zPfnpoYlwmRJEkUJcexRVHaOZCYnpg4/PpBHvaAfY2m8AZRFG+NT/09QagN1Dm2XXTsWHMLO8eKji0T'
        'Qqk7NjwsSmI6ZdQGAqPJpEdRBEGgrhvUda4bePBvD5Soe5P5W7HmuE/VLNPcOZCgpd/W4qGuW1F1vWJMDHVdbuw2RyLTExOzKWN6cuLJvfsOHzp42jLffusw'
        'Pt9f2/CwivTvTpy2zPqQHmuOz6ZS136Q0saMR1F4agoh1Ud+eXiDokxPTDC2MGukLgDIMnn/1DuhcDiXyfrrAgUz7w/UiaI4l83ytR1JlDyKwh8kbH+cIN8g'
        'Pdsfc2x7fGyE//fBBzdtULxF+8z6qvvXrbs/nTKCIf3cufnUzEzP9sfyn845Z87U6+H83Nwnn8zdCdff2t5xdv5s5fqRO41QOHztB4k/aUX7zAbFu279+okP'
        'x6Jbt/I+bW3vKDq2c+aM9mBt/pNcZQkyurUJANIp4+x8CVsYTSGCIAhOkG+NcKEoSUtV8Gr9dZIktbZ1CILQ2tbhUzfW+uu2tXX4AwGZkFhzy9bmlrlchmsL'
        'wtcduEevWZYegTvJ3Uxd97kXXiJy9TXioncOJHzqRl4AYJn7OLFnsGCZqqpV1igRNIVww4J66ZTBH0fHsft37Q6G9GAoLAjQ2dMridIGReEZYFUyodTt7OkV'
        'JdFzURGEtLZ3UJcGdf3IL9/8Gu1gSA/X+gMgCGnDwK/EnfykyYRsjkRLlG6ORJ/61n6eYlS0HVZm/bsSi2VWEWrd9+zzqqrJhNTruj9Qt0FRBvfu+ySXFSWp'
        'f1eiWLQlUdrkD8ymjFwmg50OGFcIN5svRQHg5NCxWDyuqhqAACBwWT3qulUyCeo6V9ZUNc2nalxeONbUwj9JG0ZQ17/G6+dhGVcTNOTfQHzKv95x+qUIG8o/'
        'ESp/CwAAP/3xj44PHSEyAbjgUteyTMvM9+9KHPj5qzWqysvSuu7nBdP8m5+/2tHdQ2RSoi513ZQx89Mf/wgDaADXCldqksIL5QDA0vrCFy5cmJ01uJhSJX7V'
        'yucH9+5Pp2bmKX0oqH+cNqpk+QJAwTK/rifyamGDfPJFXTekh29RLSrkK3XQl3YED0V0qevzqbyEE5GJaeb7dyU+HEmmjJlYc5yXecL0EjSFCIIgt4T7sAmW'
        'TWfSKYO6Lq+vaFmmz6fKcjXXWOcFLQGAp6Dw8ps8MeD40JHKyBFWzoejqhqO6fCZBACs4QnoNrmdVJT0d+5+YnpyYtsjHR7F29Xbe2LoaL2uHz702hNPPnUB'
        'oF7XS5SKktjV05fLZDt7ek5b5hN7nhJFcQVlYBi7WLKOq3gVCiamE9yDdHb3eRRvsWhj76MphNuhQPO7oTDvnTrp2LYkiY3RLSVKc9mMT9Weenq/TIhlmn07'
        '+h3nDIAAcMEfqOMShx7Fm8tkb4VanCBAwcp/acETZKWKrIb08B0igCoT8mhPHyHkvVMn/YE6RfGiMitOkG8twWD48rltfSh8+NBBvpJ9cujY2HCSp83PpmYA'
        'oERpjU8rWHkAcKk7OpK8RSvZODm61fh8KpeEAQDqujU+zTTzd8IojLru4UMH+UbKxaUSQLcJgiAIYFzhHRQb0dXdJxMS0sM8ZG/nQILHjvGNWzRL4uE+CKyc'
        'I2LFS1fzxwN7CnCtcFUavvqQXk2qFcXb91h/sWjHmuKMsZ27E1UyKTO2c/cTuUy2tb2jxqeVGatRtenJ8auVLrphtu/oTzw5eEsLFcE95hwDgJAe3uQPcIUY'
        '3mUhPawoXsbY5ki0mlQ7tl3pymvXAODK+3wau+JreV3dfdvaOqYnxwf37lcUL5YuQVP4NdDV3Tu4d7/i9QLAwV8cCIb0wb37HceONcUrbhOPokiSRF2XZ+MJ'
        'gtC34/Erlqm7YdIp4/1T76DPZGXZ/+y3+x7rL1FXJqSzp3c2bWx7pKNG1QSA577zXcXrLTp2347HT1umY9tfY8GQhkj04C8OAIA/EEDhNcC1wttuBPvS6ZmK'
        'GySkh7mHpKO7p3Dx/U+XzI/kisLw6HAy1hxfKUfH4N79S8UQl10VcjN9umzKzBM8lkWGVrpyWUfc7tQ9ufr40JGu7j7+gGFXoimEO0ex/YFvbDh/fvHc2bNV'
        'MmFsAQDWrFlTXmALbAFbCUEA3Sar1QJWipR3dffKhNQ99FAwpC8uLtY99NCDD246Oz8fDOkbvIpMCPerYKPBXe4tqfhAKtWUEMC1wnucfc8+P/it/R5F8fm0'
        'XDbT2tZRZmVRlLa1dRQde3Nj1B8IUOoGQ+HNjVHLyre2dWA52jtvCrS8HvwyB1dID4uStLSgAv+vY9vLIvAr1eVjzXHuMOEbvLb9ikvqc3GNru6+y1ULETSF'
        't5VgSJ/LZuayuVg8XqK0IRJljJUo9WmqLFermubYdizeslYUawMBmRDGWGtbB2bLwZ0lyObyAX5DJMoFbi3LZIxV8hod216mgbrULP7OoSh1bNunaYN795+2'
        'TEXxJvYMnrZMy8xfbnBvfjC7tallLpfp7OkpuSX0IKMphNsstMkrLvEoCp5dN5fL1AbqFhYYYwuMMZ+mFi7V6AGAtaI4a6T4d+nDkeTbbx3GgnNwRxalq6Qw'
        'bt/Rn04ZYyNJ3lMNkSgrM64sPXZN70RDJAqCYOXzPCXOsW2+wd+aKztws0xzscwsMy8AiKKEphDdJncEXCqueMauDQQc+wwAVMnVjnOGryUVz9gbvMrK6tMg'
        'CALoNrnTSBkzVj6/wBZSxoxt27Zts/ICl3clMlkriVY+X+NTMUUE7oDw+Ot/vfH9l3UZ95LBlUIIfJrGj1/ZQHCCDKved8wnU0vVSmRC9j3z7VhziyCAAEJD'
        'Y1QmxHFsXgRqLpfp6u7d3BgdHUm2tnWyMlNVzbHtO0fv5B5BlKSlC39LhWdESeLx84SQvsceb4q3TE2Ot7Z1MLYQDD28ra29IRIdG04u85bsHEhsa2ufTRmt'
        'bR2yXM0ruDc0Rlc2uejyJ3BzJFowTZ+m8QcJexZNIdz+8It9zzxPCEmnjKX6SKIkbX/scRCgaDv1IZ1/JfoHEj5VU7zevh2P1wYClLqPtHdWEZnIF1eRUGEJ'
        'bu+a4LL8HP5W276jv+jYuUxma3Pccez3331nbCS5waMoilIlE0mSRElsaIx6FO+JoaPLvSUlKlwQtjbHRVHi7pfaQN1aUSxYZjCkr7jDhPPSn/0jnm3S1d3L'
        'HyQEJ8i3m9Hh5N/811ffOHQQALY0Xcy35yoM6ZRBqUvp5zKRLTMPACVKDx866Lqfnzh2NG3MzBopM58fG07WqCqPaONHQG41z73w0rL3GW//YDAsEzKbMupD'
        'ekgPB/VwUA8DQKwpXqLuk3v3A0BQD1tmPp0ylg30+DGtfP740BGZyAXTVDXNMvOu+zkht3YwYebznY/2AkDlQUIA3SZ3GqFweN26+4v2mQ2Kd9369RMfjkW3'
        'bj07f3Z8bKS1vaPo2KkZ1Ji7O1AUpV4P5+fmPvlk7kv31B6szX+S83i969bdn/8kZ+NgH00hgiAIoIr1vRNDUx/SZ1NGpejS4N79JepWyRc9jB+OJKtkWZar'
        'Kf2cf+JTNS7ZUKOqfIf6kF6jqgd+/mowpJcorRzqhutzchfnqgzcuQFJi2W/EmuO9w8k/tP//h9iTS31euinP/7RUmWNGlXlIhqzRqqzpydtGB+OJLc0xXkx'
        'L5+q8Z4tURcA+ALINfp0bDgpy9V8qYSfdKUWDUN6+Mm9+04cO4YyHIBuE/haAzKCIZ2Q6vqQXiWTgmUm9gwSuZoLc1XJpERdj6Ic+Yc3a2vrWts7tsbjoih2'
        '9fQ1RKKMLfgDdYN7901NTgBAZ08vIdWMLSiKNxZvoS6VJKnWH6CUVr5p15VFKwgyIc+/8N1cLuPYq7b0TyVKeWtzXBAEANgciZYorXhCeNdYpslFBh3brvwK'
        'T6cjpHpzJPr+qXd8quZRlLHh5P/2n370cdrY0hSPxeO1gcBrv/ibTf7AwV8cEEAQBGBsgfdpa3sHdWlQ1w/+7YH6UPjgLw70DySu3acCCA3RqGPbBcvkJ10p'
        'RTXHtgUQAGBqYrxyp/jFRFMItz+SRpZJmbHW9g5CyOhI8rRpdvX0blAUVdtICMllsh5FaWpuuQAQ1PUTx46q2sYSpSVK57IZj+LdoHg/HEluf6yfUtejKKIo'
        'FUxzYYGNjSYlURJF0XHs6//aEFLNGOO13ncOPHEv+BNVVeNJcoqi8Lbq6u7LZTMyIQIIjm0ripebjN++wNSNuWzGse0TQ0cZY7lshqeOfJw2+gcSs4bBBSgd'
        '2xFFqSESlQkRRemll18plSghJJfJBHUdAApmvjG6ZZM/oHi9lT5dK4o16sZlfRrUwzIhc9nMe6dO8pOuoNna1tbh01RV1YqOvexOEcC1wq8lXtfK5yshuA8F'
        '9Y/TBi8GxKfPppmfTRmDe/eNDidnU0b/rgSfNVdVkdlZIxgMu/TzgnVx5HJjk51KxG8wpPN6zfdmX1j5/DUWB/gOVyty3dXdy3tKJoS6buVvn0+t8Wkfp40q'
        'Wb4AwHuK/6h/1+5r92nno73p1Mzskh6piLmtiCgclsNGU4ggCALoNrmDZspXfDPHmuOVpXRKP1/qNgEAWa5Op2d8PtWnaseHjnZ19wLAbMqo8WmVnUuU1od0'
        '6tJ0eoYXn7wH3/+V5uXt+cahg3wYTl23q7t3afMeHzpy/YPHzkd7l0pP7xxIWGbessxgMFyw8tfTzst0rXlYHxcqv2Kf1ofCBdPk9WC3NMVXRPi6clL8GgKu'
        'FcIdkLrA12gqgk79uxINkegnuezmSOSjyQmAC109fW+8fvCJJ5+qDdTVBuo2KIooSi++/MpcNgMAiT2DBdMM6mHq0no9JICwQVEao1uqZMJTF2r9gRpVq1G1'
        'YtEe3LtvntKGxi3b2jrmcpnEnqcaIlFe6KchEuWfKIpXkqS+x/oXy+xuXz+qNC8h1a3tHVOT4y++/EqsOS6JEnVpZ0/P9OQ4b96GSLSzu28ul9n37PPBULhY'
        'tAe/tT/W3DI2kqxUYuK6MsGQ3hjdMjU57g/U1foDlmnu3P3E9OSEY9s7dydGR5Jd3b2d3X2CAJ3dfbx5K507uHefAEBIdd9jjxOZyITwk25r6/Ao3oZIVJKk'
        'K/ZpmbFNAf/bv3yzta2D+2q6uvu42g18dW0kfnn1obBH8RaLNqocoSm8o9Q/oWDlLdOMNcdf/eufMMYaItFN/sDHqdTW5rgkSh7FmzZmNvkDJ4aO1gYCjY3R'
        'E0PH+h5/XJQkj6KUGevs7gUBZo3UzoHEkV++GQqHK494UNc9iiIAHH79NcvM8/o+jLHW9vZX//onAMA3/IE6AOH40JG+x/oPv37w+h3QcEdGKS21445tv3fq'
        'pChJHo/Xse25bKa1vaPM2PTkBG/eel3nzV6wzEfaO947dbLMFniPcGMR0sPb2jpOW+bUxPh7p07y9Dvub+FqWnyDuq4gCI5zxrLMhkiENy/v3LRhqKomE+JR'
        'FFXbmMtkN0cir/71T0RJerSnjxDC3WVX7FPGmChKiuJ9+63D3FfDyowPKr9qBjq/vBKlsXgLVwDDOl+4Vgh3ZuBbfSj84UjSNPNd3b2jI0kikypZrg+FZ1Mz'
        'JUq3NMV53BmflMWa4nwfXi7KpW7no72VaEQ+X6tMx3YOJGZThmnm+3clDr9+kK/c//THP+InPfDzn+0cSFCXjo58wBfy7945dVd33xXnvNw9xdsKAFzq8uZN'
        'pwzeJnxmynMilx1qmdvEp2lEJtdoIp+m8eatzNYH9+47OXTM5UGF+bxMCD+pqmoAcI0+5Re5NGiU+2q4BvX1z+4vbwp0m6ApRBAEwQnyHTyz45OvnQMJmZBg'
        '6GEeMk1IdUPjFr4da26xLLO1rbMhEk2njK7uPkmSGGOtbZ2SJCmKt6FxCyuzYEhfuqdlmdt39MuEUEo9Xi9fSoMvczv4A3WrIOJMJoTrYoX0cGtbRzpl8Obl'
        'ZUOWiW4tm2J/6Qy0Uofkll6/KEker7eru1cQBN7XvPfhhnTUUZULTSHc+QXF4YJQ669jjLW2d1imubW5eWxkeNsjHTIhNapWGwjMpox9zz4/l80yxp548qmx'
        'kWT/QKLGpwkCbPIHalSNe0tqA4GCaQ0+vW8um90U8DdEogXTam3vkGXS1dMHF4Srabj7NK2ru5eWqGPbd+kXpuLr4Ibsez/4Yaw5LoBQH9LLjO3c/UQuk+XC'
        'Fv0DuxXFW7EpIT3MnSGVG69s8GPKhCT2PDU9OV7ZcwXtYKw5Tki1KEn1Ib2aVDu2zVNc9j37fEMkWnJd3rkejxcANgX885T2PdYvSeL1X0NnT6/Pp42OJCtu'
        'H/zSoSm8E5maHE+nZjyKsjkSkSTpjdcPPtLeyRaYT1OLjt0Qic6mjBpVe2LPUyeGjsbi8fqgvjkaLVHKfSPTExNdvb2zKcOjKNSlJUoVrzedmok1t1imGQqH'
        'q2QZABhbeP/dd67mOpQJqQ+Fy2zh7v2eVOzglqZ4sWjLMnFs26epoiQCCAAXeI4jAAT18KyR4oNobgGvdtf8mIwxvnGNPeEm8gId2+bir4rXW3Tsvh2Pn7bM'
        'hsgWSZLee/cdSZQaolFKXcc5E2tuWStKh18/+JXKkggAjdEtBdNMGTNoB9EUwp0c/wEAwdDDRduh1BVFMZfNiKIkilLRdniOlChKo8PJEqXp1AyldDZlTE2M'
        'swU2l81MTY17PErBtHgqHgBQ6lLqligtM+bY9qyRmstmCqaZNgyfpsWaWi7/IvFB5Se57N07h+IjOMe2i0XbyuclSSw6dsktFW2nRGnRdnjzjo4kx0aSUxPj'
        '1HW5Xbhamywt6clnxJVs5cuHonAT3h5WZqPDycOvH+SO6RJ1pybGc7nM1OQ4dV1BAB4mVXTsEqVH3nqTj98rhcOuPTXmOdSWmS8zJkrS1e4UAXSb3CHcd999'
        'VTJhbOHs/PyyjKsHvrGBsYUyY+vWry8vsPNfnK+Sybn5+d+7b82aNWvKC2ytJK5Zc99nvyk+8I0N588vnjt7dukO586eXVxcvGcbdmmbLG3eu/HxODc/v8AW'
        '8MsCqGK9illcXDx/fnHNmjW/XUVqauHjkfX3r4+3PLK4uBgM6ZsjkcXFxeiW2OZIZM2aNbGmFl4YL7olJhOy/v71wZC+uLj4zW9+c3MkcnZ+PhjS6x6qjzXH'
        'ZUKuIVzs0zQeaRHSw5cXJLqr+ew3Req6i4uLn/2muMwOXrGskkxIV3ff0jaBq6RtwIo6SfhJl56CJ0dzb4/3m9/kfcqvCjWocYIMq7v4SWtbx4mho3w6tu/Z'
        '5xsjW95+682+x/oLVr5/ICGAACD07Xh8LpupD4VVVZvLZRoao7X+gO2caYxE60PhomP3DyTYQnmTP9AQiRYde1tbe0h/ONbc8t7V1wqp64qSRF3Xse1lBYnu'
        '6ibls1oulFAxOtzt3tC4Zd+zz09PTiy7WcYYT+qotAmvPfI7q2w3XXukMtfmammObS/LJLFM0+P1Kop3kz8QDIXLbMHj8W7yBx5p76hR1cJ1uG74nfKY8Nvg'
        '8kbQFN4sPElrbDQZa4oDwGnLTOwZPG2Z7737zia/v9ZfJxNZlqtffPmVw4deq9dDQT0siqIoiaq2MaiHpybGO3t6S5TWqCpjTJKkWLylYOZb2zsEQagN1DU0'
        'Rv/y3/0v9SG9dGl17GrWcNnG3W4H+wcSs2mj89HeWn9gscwSf/iUqmmbG6MnfnXUMvO5bIbbQX+gjqtgVeSwljUFY2yZ7bv5JqKuyxXDKKV8ffbyY/I3k6J4'
        'BQFqVE0QoLW9429+/uomf6BgmpTShkiULhFeXIbH6631BxzHVlUtsWdwNm1gvh2awjuasZHk2EiSuu5py5yenEgZMzw7KtbUUmbMoygF0xRF6ZNc1jJNj6Lk'
        'MlnGmCiJjm0TQhzbqQ0EAKBgmmXGqmRimWbRdqjrFsz8wgKbnhz3eLxF2/EoCi3R1bpwXvEh8A3LNAkho8PJxTIrWGbKmBkbSaZTxmKZBUPhyriP5yxzY3SN'
        'QKLKCC4Yenhp6y07acUDwwM/lx7tv/veP+eikDyv2adpPK6lIRK9xhhTJkQmco2qyUQumBZ1XUpdAQSZkKmJccs0rxEoerHOsm/j6PAHvCnwuwboNrmrqfXX'
        'sfJC8YxdGwg49hkAqJKrHeeMx+OtfO5Sl2sgOvaZBcYqU0KPx+s4Z3A4AKtA+pcQbr6xNQDdJnCPZaHw78AGxWPl8xu8SsqYsW3btm1WXpAJyWV/TWSyVhJT'
        'xkyNTwUA08x7lIsrffybI0kiXJKzxyaFm1DbvQ1n4X9kQi4/I3VdK59fagf5ntg7OEGGeyELZXMkoijeru5en6rN5TJ/9o//WVd3L1dwamiMBvXw1OR4/66E'
        'PxAYG0m2tnUGdb3o2A2NW0RRDIbCPnVjibqx5nhQD4+NJBN7nprLZVaNV+R2csVEvRW0sw2RqABCQ2O0PhTeOZAomHlKKa/B4vF6VVVjjO175ttcQyykh0VJ'
        'svL5L+3Krc3x0tUXExE0hXDH+k8EAUAQBr+1v1Aw3zt1stZf9/6773ycMmpU7TeOvVYUHcfmy+drRRFA2DmQmJ6Y2NbeXusPeBQFQKjX9cSep+aymf5dCY9X'
        '2RyJxppaZEK27+g/MXTUcWzuFcXWhq8SA3/rrIlMCNdn43366l//JKjrYyPDiT2Dhw+9JkpSYs/gXDYLAgRDYQBQNa3o2LlM5mreG+7vJqRaUbybGyOzKQNN'
        'IZpCuOv8J5ZpUtflXpTEnqdkIhOZiKIUCodrVLU2UOdRvNSlABcIqSaEiKI4l80qXq9j26IkFh0bQPhwJMlzTsaGh0VJTKeM2kBgNJksszItucFgGPMN4Cq5'
        'GYIgLPV1cBcH3FAOyTK3SeVQfCOkhxsat+SymVhTCy259aEw71OeYrS5McoY83iUUonCF9C/OzE2kmyKtzC28OHIcH1IX3adywawXPoQAC5cgFhzy03mwyCA'
        'bpM7k1A4vG7d/flPctqDtQCQThmtbe2ObfON/KdzZ0vzGxRv0T6zvur+devuT6eMYEg/d24+NYNCdXd6n9ooHoOmEEEQBLDME3I1P/KTe/edOHasXg8BQME0'
        'jw8d5Tl5vFyRTGQAoC7l/wWAgpWv8WkykXnNIJ6cAAAykZdqNSNwh8WEjw4nr1YF7PqP0NXdV6OqALAilaEQwLVCuDNWr947dVIAAQCOvPVmrb/uo8kJEGBb'
        'W7tHUQQQGqJRx7a3NscVr3etKAkCNESjT+7dP5ua6ezp3doc96lqbSAAcKG1vWN6YsKjKL5LldGxee8oeCJQpUzVjR+hzBoikSP/8CY6xwDjCuGurc7BI8X6'
        'dyXgYjQZBYAaVa3XQ/27EiXqPrl3XzAY5sPDzp5e/v6XCXHdz1VN4/89fOhgjapS1z1x7Cj3Mwb1cME0+U+Rr4VKn8KlGBouqRBrjl9n3CIXaOAvyC/d+am9'
        '+y8/KYKjwrsDdqn2ZqlEL2a/lhkAzKaM3zhOOm2MDidPW2Y6NTOXy6ZThiyT40NHx0aSAkA6Zbz/7jtEJu+fegdAcM7YR/7hTZ+qjQ4nD7/+miyT0eEPjrz1'
        'JldgxiHh7afSp0u7m7ouz7q7rh655DW+hvuY8/6pd4qO7dj25SdFAN0mCIIggG4TWI0elRqfxr0llH5eorQ+pFOXptMzXORmdCTp86myXJ1Oz/h8F2fHPlVD'
        '5wms3gTBpdVKEZwgw2p1MnIBvudf+C5jCx6Pt14PCSBsUJTG6BYu+y4Tsv+Z52dTxtbmeKw5DiB09faKa6XaQEAAoWCZre0dXCIFgdWl1/Diy6/EmuNjI0lc'
        'AEFTuArHfRUdPcbYtrYOSRLThuFRlBpV2zmQAAFmjdTOgcSRX74ZCof5wlC5zBzbJqR6emLcH6grURpripdK1LHt906dRDsIqzRL2uPxOrY9NpzkcrC4Soim'
        'cPXAc7O4jh5jbC6XyWUzPk3b2hw/8g9vFkzzg3ffsaw8AHycNiwzX2blj9MGdanjnJmenNjkD5wcOjo6kpSJfPStN6cmx3G8AKs3UZorM/KyfGgHAd0mCIIg'
        'OCq8J2bNDY1beLa/TIgoSdt39AuCoCjeWn8g1txiWWZrW2dDJGpZ5vYd/TIhhFRXfgUbEFZ69VYmhOtlcccFDr3RFKIpvCVsbY77VK1EaWLPU4riLVF3a3Oz'
        'Y9vB0MM7dydkmVTJpF7XpyYnOrt7C6Y1+PS+uWx2U8DfEIkWTKu1vYO6VCayR1GCejioh3ltX+QGXkJchX/nQMKyTMZYJUWET0ivN0IQVjglifdppTYL9hSa'
        'wtXJD/78L2LNLR9NTsiEvP3WYcZYrb+uNhAoM7ZWFD8cGabUleXqhkiEurREqeL1plMzseYWyzRD4XCVLLe2dfAi8ZaZr1G1uVwGRy43AF+GA4D0nSQCKBNS'
        'o2rFor3tkQ7sXDSFqxNePOjw6wcPv37QsW2futGjKJIkpdOGcEGYmhqfTRm5TManamVWFkWJyy5Q6nLDV2bMse1ZI+U4dtGxR0eSskwkSZqaQAE7uGLiI88A'
        'qRRvgqtU7Kzs+aWHug2X7VM1SZJGh5PFoj2Xy+CoENBtgjzwjQ3nzy+eO3u2Sibn5ud/7741a9asOXf27FpRXLNmDXoVEQRHhbC6w2t58Y0NHk+tP5D/9NPa'
        'Wr/24IOf5HINkWhVlVwqlbq6e7k7xXFsf6AOxw43Wc2dkGrGmMfr5RIJ23f0V5q3IRKNNbfQEgUAUZJ41/AQUfhdfws2JppCZCX53vd/2NrWIYCwuTFadOz+'
        'gQRbKG/yBxoi0aJjb2trVxSvaeYbI1FeBeW9U+/gchLckL84GHq41h+o13VRlERRfPkf//PO7t4yY0ubl4sGyTIRAPY983xrW0eJuok9gwIIlVIK3O98M73A'
        'fTg8lBoNK5rCe/QL2b/rCVXTZEL6dz0hXCoAVHRsUZQkSYrFWwpmvrW9QxCE2kBdQ2PUp2mK4s1lstOT47xgHo4Kb4D+gcTBXxxIp4xgKFxmrGCZjC18NDnR'
        '2dO7tHkLlunYjkzIJ7ns5sYoABz4+aunLXN0+IOdA4nO7j5BgJvXB2po3LLJH5ieHG+IRPsHEphvh6YQ7kGNz7GRZDpl8A3LNE9b5vTkBGMLkiRVycQyzaLt'
        'UNctmPmFBTY9OS5JkpnPFyyeqC/IMqn112GY4VdFVTUepEmpW6/rc9msTMhsyvCp2tLm9amq45zxKN502vg4ZUxPTvB8IQBIpwzeZXDTzjRWZpIo0ZKbNgxC'
        'CLrCAN0myO/mLJ9ZYIzXgwcAj8frOGc8Hi8A5LK/xia6FdT667B5EUAV6zuHlDFj2zY3gtwaSpIIAJIkOs4ZnguxtTnOjSY2F9yQCtbSDU4u++uKHeRelMq2'
        'T9OuU6QawQkyclNfTm74+IZP01RVEyXJ51ODobBP3Viibqw5vjkSeaS907HPdHb3vf/uO61tnZaVx9ga+Oqe+qWvGbhU0H3nQGJw735CiEzIvmefHxtJerze'
        '+pDeGIn6VM2naumUUekpWInsIwGFZ9AUIrAk4+rZ73xXEKCzu29w7/6Cle/s7p3LZhsaozIh/bsSHq+yORKNNbX8p//jP9T4tKJjt7Z3eDzegpVPG5h795Wp'
        'WB++EWuO73vmeUJIlSw7jv3+u+9QSksutax8Ys/giaFjUxPjPnXjwsJCYzTKe4p7usZGkpVsuRtYA9n2SMfYSNIfqKt4kLFr0BTeozz3wktjw8l0yhAEeOPQ'
        'wbGRpCDA8aGjchXp350YG07KhFDqjg0Pi5KYThmqqpUZ69+dKDoOdd0yK1eiOhC4Cf/Vact879TJJ558yqN4x0aSVj6fy2YYY7HmuLhWUryKR1Eao1t+9v/8'
        'hPcU93QBQDplfFU7uHMgQUvUsW1xrRhrbilYpiiKlGL1EkC3CXJlHnxw0wbFW7TPrK+6f926+9Mp4+x8if+oZ/tj+U/nUjMz2EoIgqYQQRAEJ8hwDy3zJ/Y8'
        'tVj+bUD1zoGET91Y66/DCfLKtvNtyGWMNcd9qoZZJWgKka/2tQFBYIwFQ+GCZba2dfjUjazM+gcSoiTOZTOEVKO2HaycmP6yluRmi1LaEIkSUn3z7SwT0rfj'
        'cZ+qzaaMzZFoiVLMLQGMK0Tg+tyd1HUP/PxnKWMGAApWPhgM82QJWcaXFqyUEx9ufdh8SL/YcYRUA4CA7Q64VojA9cYbLquHG2uOp1NG/65EOjUzNpzEJlop'
        'O8XfNLd09s1fbJUNbHY0hQiCIIBrhQjcvFDzKhNi2DmQkAmxTBOFqhDAtULkOonF4zWqWuPTYs3xWHN8FdxRUA+XKAWA0VU66x/cu5+vSD73wkv4AKMpRODm'
        'V7VizfEaVQUAmcj1oXB9KLxUO+Cuux2uKPEf//LfL1utu3VKEzIhvMV8mras6W7dSWdTMzWqKhPiU7XV8fZa9dyHTXAnUyXL6ZRx4tjR2ZRhmvllSbVwF2rw'
        'XONO4ZbpFQJAyp3x+dT07zbdrTtpfSg8a6So6/70v/xomSsMAXSbIAiC4AQZgRteeFodCnp8rhrSw13dfXxy+lXvi/86n9vy2W5lknu12W5lz5u57OucSvs0'
        'rau7TyYk1hznriGcHQN6kJGVoiESbYhEThw7Orh3f0MkesVqv3d+KuH05Pi+Z59viERFURIlURQlVmb9u3YHQ/o8pX2P9ReL9pfO/SspIo5t88yNilf9au71'
        'yp6wcnkpVyPW1NLZ0zM9OdHZ3VswLZ+qvXfqJD7AaAqRlUFRvGXGfOpGn6a++tc/gbswxW16clwmZPuOfkEQ/v4XB7bv6L8AUGYLPlUrmKZHUQ7+4gBXseXl'
        '2y83pg2RKL3jE9dy2cxs2vD5VFmu5i5yTBtHU4isGJIkMbZQdGy2UPYoyl0UiMdrG/G0GW4mpibHRUmamhxXFCWdNkqum04bJUobGrc4ju3YNr+7ru4+VmaV'
        'QSJj7PqrzfGT+jQt1tRyRUtUuaple1ZOWtnh8vnv1Y4JS1InfapWZmUAGB35AJOOAd0mCHLP8sA3Npw/v4j5djgqROAWLbqJknSXDjT4BNmyTI/Xq6oa17Xn'
        'G5RS/qPWtk7HsZdqZ93+dBQ+GV960pAeZoxdu9l514iS1NrWycpsW2tbLpvxeL1oDdEUIrCymncgCC/+6St9Ox6fnpq4G79g/kDdJn8gGAqX2YLH493kDzzS'
        '3lGjqgXTbIhETTPfGIlua2+v9QfeO/VOa1unJEmiJH3/z//Coyhjw8llNjGkhxsatyydq1Z26Oruu/Yc9mrFm0J6WOTZjZdqj/BDObbNjdrlJ4VLeYRPP/Oc'
        'T9UUxWs7Z7q6ewGEYCj8/qmTXHgNDSKaQmQF6OzukyQpnTIaItESpUd++SbcbYo7wZA+NTHuDwTKjNWomiBAa3vH3/z81U3+QME0+3cnFMWby2SnJ8cFEMqM'
        'bW1uZgvlqYnxuWzm8KHXQno4sWfwtGW2tnV0dvcJAtT6A2+/ddinaYPf2h9rbikUzMG9+09bpmPbfL3vah4Yn6Z1Ptq7VBkXlrh3OL9do7y0Xsn/bm3rWHpS'
        'QYD+XU+omgYAoii9f+qdzp7eEqWzKaPMyoIAtEQt00R9STSFyMqwWGab/IHZlHHaMmdTxl331aKua5mmTIgoijIhHkUpmBZ1XUpdAQSZEEmSzHy+YPGsDEGW'
        'yVw2s8kfmJ4c57bMsW1CyHunTqZTxthI0jLNrc0tkiSmDWNsJDk2kqSuy3cAgK7u3nTK4Ce9vOKSlc8vlhnPe1nmNmmIRJf6aiqHgt8W8Pydk/LyT+mUIQjC'
        'bMqYmhjv6ukFgI9TKYALNar2G8f2qSqOCgHdJggCVwm05iK1/JNafx0AVAq0w92cM+5SFzPtALNNkFttRG6dgsBtHSTmL9a256kgueyvNyieSun0pXd6tXQU'
        'vhv/6dIduObC9WSwXK7O8KVSrEt7oaLysDSnJWXM1PjUpRoQCI4KkZW0gPUhfTZldHX3Wma+ROmtFmG+1bcz+K39ADA28kGJ0vqQDgDHh47270oAwOHXD3Z1'
        '9wKAZeZ5VZD6kP7GoYNbm+MFy6SuWx/SBYD+XYl0yjjxq6Oxpjh1KaWfd178LTOo64cPHbyG/Bcfky6TDa9c1YH/+rOLCg7GDN+hq7svFo//5Mf/l0xIjU9V'
        'Va1GValLT/zq6OC39gHAbMrg11+i7vGho7GmFpnINar60x//CJ9ewLVCZKXY9+zzhw+91trWuUFReLj1XSp3unMgEdTDjmMHQ2EAEATo2/F4rKmFx9nMpoyG'
        'SNTj8foDdQsLTJKkoB6ukklDJEoImU0b1HW7unvhArz/7junLbNG1RoiEbi02iiKkuPYB37+s6Cuj40MLw3TCerhdMp47jvfFQTwqdq+Z54nhPD1RLjkoGdl'
        '1tXdCwKctswan5ZOzWzf0f/sd74rCDCXy1hm3nHs/c9++6PJifdOnSRyNXXdYtGura1zHFsUpZ0DiemJCe4Bn8tmCpbJFsqYaoKmEFlJgqGwKImKooii5A/U'
        'vffuO/27EnO5zN0SYFjJQU6njHTKkAlpircwtlAwLVES0ymjNhAYTSY9iiIIAnXdoK5bpukP1KWNGY+iUOoWTGtzY2Se0lwu09rWIQjg8XhD4fD2xx4/8tYv'
        'Q+FwLpP11wUKZt6nbizazubGaMEyRVF0HHtqYpy7PrijwzLN05a5NDXYp2oAQCmVZQICTE1ObGtrLzN2fOioIMAbhw7yHBjGWNGxn9y7bzZteDzerp5eWSaK'
        '11sw8/5AnSiKc9ms4vU6tl107KmJcbSDOEFG4NZkIiv1ejg/N/fJJ3Or445C4fC6dfenU0YwpJ87N5+amenZ/lj+0znnzBl+p+ur7l+37v6ifeZqt6woivZg'
        'bf6TnP21etWjW5sAIJ0yWtvaHdseHxvBxxVNIYIgCKCKNQK3ri7o4N79JeqOjiR9PnV1VAXp6u5bMo+WAYC6FABqVLVEXe45qZLJhyPJKlmW5WpKP6/Mait7'
        'AsCHI8n6kF6jqmPDSVmurhyK0s8vbyjuNuFVR2aNFP/w+NARri1oWWasKV4lEwAoUZc7cK7zpG8cOnjb6osigGuF9xpbm+NPfWu/AIIgQJVMymzhbreDPB1N'
        'JmRzY1QmxKepre0dc9nM1ua4KIkeRSk6dpVMWts7qEuDuu7YTmt7x9Z4XBTFrp6+hkiUsQV/oG5w776pyQkA6OzpJaSasQUBhIZo1LHtrc1xxevNZTP9A4l5'
        'ShljDZEoz1/se+zxxXJ5Lpvd5A8c/MWBvh2PexRlntLtO/prA3UbPIooSkFdP/i3B+pD4YO/ONA/kLjuk7ZIkkgprVhPBDCuEFmxVQwAEKBeDwX1sKppXAgP'
        '7v7owlhTPKjrJeoG9XDBNDt7emVCCKmONbXwO00bRlDX+SisRlVPHDtKSHXBNPkf1/3cpbREXR58U6OqPlXr7Om9VBWLuO7nslx9cujYk3v3Xd6iNT6NunRw'
        '737+kUtdM5838/nZ1Aw/qc+nqpo2uHf/VzmpvDp6B9cKEbiTMxkeCuofp41VMPPi830eh8wn/unUzNhwkm/MU8rvtEqWLwAULDPWFDfN/GzKGNy7b3Q4OZsy'
        '+ncl+Ky5qorMzhrBYNilnxcss/PR3nRqhsdgmmb+oo6DZV6eAcJFGSqB0FY+zwOzfT6Vn5Tba5mQ/l27r/Ok1HVjzfFKmA6CphBBEATQbYLALQpRpi4dHflg'
        'tQ46eLTzbMrY0hSfTc1wDwZ1acHK1/h49N/nlZ1luTqdnvH5VJ+qHR86ymessymjxqdR+jn3schydY2qzqZmKh4P/iuV3+XHAYCCla8P6dSl6fTMdZ6Ue3UA'
        'YHQkGWuKHx86ioNBQLcJckunk7GmFkmSPIoiSqIoiv0DibFV4UGG3xXZJ6S6tb3j+NBRVdUABI/Hyxjr7OlhjG0K+P2ButpLfzYoiihKL778ylw2AwCJPYMF'
        '0wzqYerSej0kgLBBURqjW7gijiRJsynDp6qOc2ZrU4tH8Xb19oprpdpAgHs8LgDU63qJUlESu3r6cpns9Zy0RtU8inLiV8cAoD4U5nmB+LgCuk2QW4SVz6fT'
        'Mx3dPTWqWiUTn6r5VG11VJWsqEt8OJIEgJQx8x//8t9T162SSb0eqlHVWDxeorRKJoRUm/k8AKSNmSpZHhtOykQmskxdyv0tXKBhcO8+PgDs6u4dTV58WwT1'
        'cJUsV8mkq6dvNjWjalrBNLu6ewmp3toc5x6Pzu4+3ryu+/l1nnQ2NQMAT+3db+XzB37+MxSkAVwrROAWJ64FQ3qJ0ipZ5loMS3UE4C6PKzw+dIRPjSsRQtyh'
        'UZnwAgBXo3Cp2/lo72xqpkTplqY4D+uzzDyfR4+OJIlManxawcrzPT8cSbrU5YeyzPzocLKru69GVfnn/bt2nxw65lI31hSfTRlVsgwAJUr5Ea7npD6fylNl'
        'RlfXCB1NIYIgCOBaIQJ3kf9EJoRS6vF6K5JTsLr8J5TSStWkZTcoE7Lv2ed5vEtrW2dDJJpOGV3dfZIkMcZ4XRRF8TY0bmFlFgzpseYWXkOqIRK1LHP7jn4e'
        'wNjQuIVXUIk1tfDyUq1tHemUUWnepXt6FKV/IMFPWhHCCOlh1OtHU4jA7U878alaKPQwY6y1vSOdMp7au38um1l930auBCNK0uDT+wpmHgShf1dCkkSfqsWa'
        'W0RR9Kmaz6fNUyrLhDH2xJNPjY0k+wcSNT5NEGCTP1CjajIhtf5AbSBQMK3Bp/fNZbObAv6GSLRgWjyPRSayR1F8qsYY27k7USWTMmM7dz+Ry2Rb2ztqfBqv'
        'xHLxUIEAAPh8Go9/VBRvbjW2PJpC5C7gB3/+F7HmlvffPbk5EpEk6e1fHs7lMrlMZrXeL2NsNm2kDWNw775X//onlmkSUr3JH5iemhAuCIIA+555fnpyIhaP'
        '1wf1zdFoidKgrnsUZXpioqu3dzZleBSFurREqeL1plMzseYWyzRD4XCVLLe2dVDqBvUwHxLGmuKOcwZAALjgURRJkqjr8hRA/neJ0oJpCQJwl/Tbbx3GBxJN'
        'IfL1cPj1g4dfPxgMPVy0HUrdpVkNPBhl9d0yv8HZlMFnyoyxWn9genJcEEAUJWmdZJlmOjVDKeWFltgCm8tmpqbGPR6lYFqiKBVMEwAodSl1S5SWGXNse9ZI'
        'OY5ddOyx4SQIUHTs2ZRRMK0SpUXb4c1bZqxgWo5zRpari7Yzl8uUqCuKUtGxRVHyKMpdKqCLALpNVgf33XdflUwYWzg7P49NsW79+vICO//F+SqZnJuf/737'
        '1qxZs6a8wNZK4po19332m+ID39hw/vziubNnl+5w7uzZtaK4Zs2aSu4ddd2lezK2AACVQ1WMMgIYV4jcIaxbv77uoYe4HeRpvF3dfTIhqyPSEK5f2wZgcXEx'
        'GNIX2MLi4uJnvykusIWz8/PUdRfYAnXduoceAoDPflOkrru4uLj+/vV8B5mQxcVFvie3cXxj/f3r+TE/+03x7Px85VAAwKsO4LOHE2QE7qgVNF5aN9Yc3/fM'
        '87WBQEMk2hjZ8vZbbzLGeFDeqm8EnkbCGOOO5qW1DWLNccs0B/fuf+nlV0786lgwpAdDDzuO/eLLr/hUrVi0n/vOSwIIjmPzSbeqatxx/IN/+a98qnpRwcE0'
        'ZUJa2zodx+7flbCsfGtbR7FoX7HMPIKmEIGvcQUt1tzCM3YPv/7aJr//N45T6w9sbWq5i8qe3OwrAYAxxhiLNcf7dz2hapogCIk9g6ct8/jQ0dmUkTaM/oHE'
        'wV8c4B6Y6clxx7Zn00Yum+nq7n37rcPUdRN7Bg/8/FUA+CSbfe/UOx6vl0vksjKr9Qccx96+43Fudt8/dZJSei+0LZpC5G5CEITpyYn3Tp2MNbWUGWNsYXQ4'
        'uVhmlpnv6u67PBxvdQ8Sx0aS6ZTh2DYhhFdx4sM3VdVkQizTpK7LrRjf8Kkba/11jmNL4jruA3FsmzFGXZcQcnzoKJ8R+3wbubX9cCQpSlKtP4CjQnSbIAjc'
        'm3IYAIApxoBuEwTu5vxl/mXGVf+bkcOo8anYDjhBRu6m8Ut9SC9R+r3v/7Cru3c2bex/9tuiKE1NjHu8XgwHga+e3iMIQqypZXpyfPuOfl5PGcFRIQJ3bGTJ'
        'c9/5LgA8tXf/PKUyIenUTDo1Q133+LEjXGcF53fw1RO9uQRhLB7/wb/8V1zLC8FRIXKnOw0AoOjYT+7dNzaS3L6j36N4j/zyTe4NwCa6kSG2unFzY2Se0hpV'
        'nZ6YmE0Z6DABdJsgyD1La3vH2fmz42Mj2BRoChEEQXCCjMBd70duiEQJqcbJ8vW01fd+8MMSdQmprvUHgqGHc9kMNgtgxTsE7k5HimWZAND5aO+JXx2NNcWD'
        'eng0meSV5NIpQ1U1AFgFJZVvEVzZPxaP16hqwcpXyfIViykjgB5k5A7/JgMAkUmJXtQaMPP5dHpGJjL/0VKjiSGHvy09qmnUdf/tv/5XKWOmRlVrVPXEsaPY'
        'MoBrhQjctQGGXHAlpIdd6lZChfkXfqnQ4aqpGLVS4eiVltk5kDDN/OyStkLQFCIIggC6TZBVS0gPK4qXlzqSJOle9qvw9MTKGJD7mjCWEE0hAqsyg6Kzu69Q'
        'MPt3JfyBgGWZnd29Nao2PTm+c3didCRJXXe11ga4Bs+98NJsynjx5VdizfHTlpnYMygA5LIZtIOAbhNk9Y3+AGA2ZYyNfEBddzY1U6OqMiFBXQ/qOnXd//iX'
        '/54vGn44kryn2iTWHPepmkxI2jDShpEyZgqm6VM1fGYAg2mQ1UeNT0sZM5XomfpQeNZIWfn8T//Lj5btWSXL90ib8DsdHU7yQBn+DpAJqVHVk0PH8JkBdJsg'
        'CILgBBmBe61e0rVnkasy8FAmBGUcEUC3CQKXVG0qJs+x7VhzPNbcQku0q7s3qIfTKWP/s9+GC8LdnnwmE7I5EvWpWonSxJ6nJElsiES7evrgguBRlP6BBK/u'
        'hLmJaAoRuMdDsrc90rFYZmXGNvkDc7kMANSo2lwuMzqcTKdmLo4fBeEujTf2B+pe+NNXYs0tRds58aujuWyms6eXsYX3332ns7v3pz/+EX8roB1EU4jAPV5C'
        'r1i0c5mMKEmKoliWKctEkqSpifFKgTdeKQkAdg4k7iI9Z5+mBUP61MT44dcPHn79oOPYXd29tERLrlswzbRhELm61l+Xy2bualuPALpNEARBAN0myK2gq7vv'
        '+l0KvCYc3JFuHwTBCTJy4+SymWWVobq6+zyKQiltbet0HNvj9caaWliZdXX3Dj69/8gv34QlOS23bQZNKRUlaWmZ9lhz3DLNkB7mNYsrzhB+/ZhAggCGWCPw'
        'FYteAgAvIDU28gGln48OJ32aJhNZJqR/127ubXgjn59NGXApeSNlzBwfOgq3cZVzqUQjkUn/QIKrDcpElokhy9WyfPF9PzqcjDXHtza1FKz8G4cOYhcjOCpE'
        'rpexkeTYSJJS2hCJyoRQSgHA59tYtJ1af53j2Iwx7nh1bJtvVOpkPvfCS2PDydsWFURd17FtQsh7p05KkuRRFMexRVHc5A8cHzrat+PxeUqnJsbHRpL88u7B'
        'bGsE0G2CIAgC6DZBYKWDVOBK0qdw3SKp1/gVmRD+o6/RIYPgBBlBrotl/op9zz6vqlo6ZYT0sChJALA5Ei1R6vF660N6wTR9mlYf0kuU/tk/+Wcl6lJKv//n'
        '/+P01AR1XZkQfiiuv73v2ecVxWtZ5vd+8MOibVumubU5LgjC5cfkeouObfOTUtflR6gcCrsJQVOI3EIYY9x4cZErSqkkrpuaGldVrcanTU2Mt7Z1ejzK9OR4'
        'V3cvXIC5XGZw774TQ8cAoLxQzuUyjLGCaVJKu7p7E384WKJu/64nBvfuHxtNCheEuVyGUleWyfTURFd372zaoK7Lj0Bd9/kXvvvR5IRj2/uf/fboSLJy0p0D'
        'iWe/811BgHTKWKrDiiBoCpFbPFNWNQBwHDudmqGuK0rS5sZosWiXGdvgUVR1o+OcaYhsmS/RbW0d7BybTRm5bIa6LmOM+zrSKeO0ZXKHhiDA6HAyl804ts0Y'
        'm54cp67rUzdubozMUyqK0oYNSnmRzWUzT+7dd2Lo6AJbiDW1pNMGP+nocFIQ4I1DB2VCWts60imDW2qMoUEA3SYIgiCAbhMEQRA0hciqclvzQG4EAVwrRO5e'
        'QxYM6Ze7g/2Bulp/AAQhGNK5B6YhEuULfHxP6ro8mY8HUWNLIjgqROBulE3t6u7j2yVKAUC49CPhy35X+G2CHV1mVVGIAQF0myB33XjQyud51PSNBbjwIyyL'
        'wV76CYKgKUQQBMEJMoIgCJpCBEEQNIUIgiBoChEEQdAUIgiCoClEEARBU4ggCIKmEEEQBE0hgiAImkIEQRA0hQiCIGgKEQRB0BQiCIKgKUQQBEFTiCAIgqYQ'
        'QRAETSGCIAiaQgRBEDSFCIIgaAoRBEHQFCIIgqApRBAEQVOIIAiCphBBEARNIYIgCJpCBEEQNIUIgiBoChEEQdAUIgiCoClEEARBU4ggCIKmEEEQBE0hgiAI'
        'mkIEQRA0hQiCIGgKEQRB0BQiCIKgKUQQBEFTiCAIgqYQQRAETSGCIAiaQgRBEDSFCIIgaAoRBEHQFCIIgqApRBAEQVOIIAiCphBBEARNIYIgCJpCBEEQNIUI'
        'giBoChEEQdAUIgiCoClEEARBU4ggCIKmEEEQBE0hgiAImkIEQRA0hQiCIGgKEQRB0BQiCIKgKUQQBEFTiCAIgqYQQRAETSGCIAiaQgRBEDSFCIIgaAoRBEHQ'
        'FCIIgqApRBAEQVOIIAiCphBBEARNIYIgCJpCBEGQO4T7yAMbsBUQBMFRIYIgyD0/KnQ/K2IrIAiCo0IEQRA0hQiCIGgKsQkQBEHQFCIIgqApRBAEQVOIIAiC'
        'phBBEARNIYIgCJrCa7B77N/sHvs32A4IgqYQQRAETeES1q2/PxJvf/q7//Qa+/x+4ltf6cTRlvYabdPln7/wJy9fdaT2B3+47BNCqp/+42eWffj0H/0xAPRs'
        '/31t48Zlv/7in148+It/+vLlR0MQBE3htYh3bV+3/v7k8beXfviAR6mt1/lGjbbpm9qDLV3buXWrrdc7H9v9gEcBgJau7Z2P7V63/v4HPEpL1/ZQY6xG2/SA'
        'R6n+hnLu3PyyE+kPPxzftq1n++9zW/b0H/2x/vDDABDftu2FP3lZ1TRt48aln3f39cGFC5dZzD36ww/vfuIP+P4v/MnLfOfX/u5vK/v83//nX6maxrcHnviD'
        'p//ojwmpxqcBQdAUXov05Fioces31QeXfviZY296SI+2tD+wQZHWr39ggzKRPBWJtz/gUTY9pCdPvM3HiampsfTUWLxre6ghtnDu7AMblHjX9s8ce+7XxgMb'
        'lGUn6unb/pf/67/t6dsOAN/7Fz849Pd///QfPaNt3Njcsu3H//mvAEDVtN1P/MHQ0SMv/snLu//gDy0zb5rmsvHdsSP/8L1/8YPkB+/zMeaP//NfvXjNkaZl'
        '5oeTHzz9x3+MTwOCoCm8FoX8XO5jAwSItrT/zsR53f2ReHuoIfZZ0f6saJ87O3/u3PwDG5TT+U/OnZ3nA8aWzt8PNm4FAGn9+s+K9mlz7nILWKEpvq27d3tI'
        'DwOAmf/UdT8385+qmjb8wfuVfYyZj/Kffvov/sk/UjWtuWWbHg6b+U+XHefQ3/9dauYjANDDD7/4py8bMx9d7YyqphkfzRgffaRqG/FpQBA0hdci1Bjb9JD+'
        'wAYl97Gx9PNvag++ffD/i7S0f+bYlQ9P5z8JNW7tfGx3btZYt+7+6g2eyw9YW69H4u18CFn5UNu4cejo2z/+z3/185/9v3yOfNH2fTTz9B89U1nmqzD8wfuq'
        'tvHCBTDz+WU/4nPhUPjh4Q/er+zwwp+83BTftvsP/pDPmpvi2+Lbtg1/8P73vv+D/+Ff/8+H/v5v8WlAkHsWgXg2XqeXY/yDd+BeCqYBgNe2/vf4iCAImkIE'
        'QRCcICMIgqApRBAEuVdMoQACtgKCIPcyAgi/d0G4gNYQQZB72Q5eEC78HlyAC9gYCILcy1yA+y7+C4IAaBURBLm3xoNwye5V3CYXcKaMIMi9Ni+ujP/+f0aA'
        'HRO4Kx8IAAAAAElFTkSuQmCC'
    ),
    'assets/andre-ascii.gif': (
        'R0lGODlhrgEmAoUAALTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hW'
        'Z0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh+QQEKAAAACwAAAAArgEmAgAI/wBtCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLF'
        'ixgzatzIUWONGh1DihxJsqTJkyhTqlyJ8ONAkCxjypxJs6bNmzgpwoSZs6fPn0CDCv0JkufQo0iTKl3KtKDRplCjSp1KtarVq1izat3KtavXr2DDih1LtqyM'
        'DRQobCjoYkOAAGsJzhgBAUKJsnjz6g2KNq1agm7fwiVIty6EEUxDQFxxIYWNEhUMrliRMIRjGzE8eKBMMPJjyikUFxQdMcQDzghJK1R98ILAyQlTXN5LG6Jf'
        'vwQFCyZo2PDPGBk8PB6hOPODxyEQl8iwosSIEXdDCH9810aG1xlKrKhQQfHyGI8zpP/IENx6jBXMya8IcX3Fg+6QM5yfvLzE9BHgF5Zgn/8g8MceKMecDSN4'
        'ENoC2TUnH3oC2rBddwWNwJx9HvRX24UJ3ZZWbroFwFtvEPyW2XIpXLBdDK5VUCJwKGYwwgUZJJeCcCVUd50NkVUQQ40OylfBdj0GuNwFFWQQ2XE2IJndYzpm'
        'VyN5ySkWAmoCiafdQDFUEIFCA/7oZZZJopikQJChR5mJ1pFZHUFbAkgchnAi1FdacQkU2Ft1PtbbmjlJWMFy1pVwnGs3ChrjdeQZuSSPadpAaAo8GhrCflXW'
        'GF9wFxQokJJ3AerkctfZdxCkGbhG0HKeHXQjooBGduOY1An/5EEGD9xVKJ9kVgDdk3H2WlBfedqJp0GF4YqTB0R6OiQDjeJ4qHXiFdkcd809wByMkW0XQpbZ'
        'cSuhpURGS14MISBoQwrwIZpCBEXOiqaKDI3AHWKdRVddkSmS12yplgoEIwP7WesghCkch16mlr7q68IMh3RBDOAdJ55JrI02kMINZ6yxUuQ6Np6xNIG88cgk'
        'l2zyySinrPLKLLfs8sswxyzzzDTXbPPNOOccUgs89+zzz0AHLfTQRBdt9NFIJ6300kw37fTTUEct9dRUV2311VhnrfXWXHft9ddghy222DqXbfbZaKet9tps'
        't+3223DHLffcdNdt991456333nz3/+3334AHLvjghBdu+OGIJ6744ow37vjjkEcu+eSUV2755ZhnrvnmnHfu+eeghy766KSXbvrpqKeu+uqst+7667DHLvvs'
        'tNdu++2456777rz37vvvwAcv/PDEF2/88cgnr/zyzDfv/PPQRy/99NRXb/312Gev/fbcd+/99+CHL/745Jdv/vnop6/++uy37/778Mcv//z012///fjnr//+'
        '/Pfv//8AbBgKAkg3FLzABgZMyAsOSECzGRAFICABBFFAAhAscIANLJsGUABBCYKAghaEoA0sgMEMmvCEKLyZBhwwkBdMgAQvIMFDLGgDEChkhQTRgAYGAoIJ'
        'MDCFTbEAAv9tCIIPFrGDE6zgC3BYABi+8CJCHKENlMhECU7gihZ4QQ9rSMQBRhGIP9HAAXcowiOa0YMg/CEJmJWRHdpgh0ocyBotoAASPlEgRazhAN0IRp9g'
        'sIQSoWFG/ngQC75ggCJMCCD7yEjMydAGEyghBUngAA/acCAcTEgeG0JBLV6yhhawAAk0AAJSPhKTGjilA1KZyUYC5QUMiKADUGCBF04giw6oZCzpGEoW1hKS'
        'G7ziCl+QSxTk0oWpnGUtUXBFFDAgmShYYS1jeUsbsBCW0XTAC2r5AgUogJgCYaE1XYmTbWrAm7RkwAQcwKxaLtOYxpziDjXAgCy+sIieHKUNzOn/zTUyQIs+'
        'ZCcBFKABAugQBNpUwCddOMorNlOhJFAACSK6SHLGhJKHfKAYjzjLib5xAjUEaSk72cMfDsQCyczoFGXoAHyW0opOJCNBephGjxISgRbNaeRGaUELfNIgh1zi'
        'RDcIgixqIIs+feEpETLKChpViKkU6igNeMBMcjCokaSgEH2qUoHAUJFi5GEfK1hDGYIUkgIRokcNclY8FnECPaxlUUsoQxR485YOXec5V7jKZ/4zlCvVohV7'
        'eMWWEpSea8SrMIvZzFxa4Jm5JMEt/erMiUaSrUOMpgJWqlODgECiV9SiAQVJkAIUwJqFFWUkJ+rCD97yAAQ9gAUcMAF6/352AgyQqAOSyky4FoAB4txtHScA'
        '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'
        'maYjjh7Wt6NCB3xJ3noypWamULaZeOaM9ynHwFMqsbjkR6WtRQJv0sE2gWUOHLDVllB5VlVnmTFAwAt0gukoTgq8BpdVHdk3EkWnXTiQjSU9dChcMXL6kVh7'
        'fokpRA/FJVqUTq1K2nVNYS5pFXYPsfeoo+ON1993FRG3JI8f5UoejweBxIBHDpCXk5s8BTaddSpZxKNcNwQEACH5BAUGADcALGsATQHIAAsAhbTAztavZae0'
        'wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxE'
        'TjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAj/AG8IHCjQBIoYJFSoMPHCIEIUNxK+QPGi4QuCGDNq3Mixo8ePIEOKHEly4MSLJQeSuPECxA2IAlFAJHHR5YuVMiPWTMmzp0+fMH9ulEkx6FCUIhk4'
        'sKBgAgoFCjSQsGDhxYSqGiyQ0ADCglSqVicKHUuWbMWyMVtOnaAARMuJNB04iAjRaEa3DkCgcEDRKYkJf68qZatBgdwJDgRYIACV8QG3dtFKnkyZI0ULSm/w'
        'nfvCAYm9S1duVPsXqUDEXpVCRcyAQVQGqK9acKDBwYQDEzSg0FC5N1qtBOeSlBpc4NytN3Sz1qBhwgQOKDgoQKF0quiMpDlMAElChAoRImBgpgiPgcQJESe6'
        'wxBx3bf795K7q4BPv779+/ZJRJWLlWtWryAwt5VWzTFnAX4IJriRTe2F5FJz2210IHNWfcYfA0zBhpliBxygwAEOHMCVWwqWaCJPewWlwUUHJncDYlftZ0GH'
        'MzqgFGwOKMDUh7CBQOKJQI7VYkwu6fURiUNmtBcDNxwI05MVfaZTX25ZoBeB0FlplUtBdjmWUWJR9BFMDRJ0EU43BAQAIfkEBQYANwAscQBZAb8ACQCFtMDO'
        '1q9lp7TCpK+6nKe1m6e1mKKtkJyojZmlhI+bhI6bd4qdeYOPcnuGbHaBbHWCO6p3VnB3YGl1YGl0vF9bV2h6VV1oUl1sTFRfSFZnSVBcjjw+SE9bQ0tVQUtX'
        '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'
        'hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwk'
        'LhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAj/AG8ItKDhhcCDCBMqXMiwocOHC0FYIDEBBAqC'
        'JDRoAMERhAYUEl9YmLixZEWCHz2C9KiBBMGLLTV2VClRooWLL1C0HAnCAcSfQIMGnXCDBAORGjUosOCAgVMGDiYIGLmUgQYHFiZYnTDRAogJEw5MwMpg7Eir'
        'S5s+jTo1qwMUKCaguIHCQVQLCkAI3csXKAmBfw+O1Vq2MN6eADQcOKCAAQEFGgho1PqVAQinBBgoECsgqlqtWg87SHygJ4ODL0CQUE23r+vXCjUI1CsQhciJ'
        'LknEVT3BpcWbGXX3tu31hobhDnRP5Bg8926KvkGmhk29uvXr2BF6zTk3u3eIIF68pfiY8MXb8RaMkxhPIiNIC+hFqm6p84XLG9u9Zuxp+2DghBxpxAAKDPz3'
        '3YEMvZDXbjVFlZEGBZaVFVhjKXWVAxBqMBJBElolIYV2ETWBbAwVUIBprSGoIkNz+VSUXBpK5tgBDDCmGFMjWqaAVgoQ4ECPE/g4VlNmYUWQV+k9pFGSAhG1'
        '4pOofRSXfRl+5RVXdR23pE0EcdXTSElpSNBXLQW3kUIBAQAh+QQFBgA3ACyRAJYBgAAKAIW0wM7Wr2WntMKkr7qcp7Wbp7WYoq2QnKiNmaWEj5uEjpt3ip15'
        'g49ye4ZsdoFsdYI7qndWcHdgaXVgaXS8X1tXaHpVXWhSXWxMVF9IVmdJUFyOPD5IT1tDS1VBS1c9RE48RE46RlQ6QUwyPEkyOEIrNUErMTwpLjglLDUkLDgg'
        'JS4cJC4cIiwaISwdHR4WHCYVGyUUGCIdFx8RFh8OEhwNEhwNEhsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAI/wBpsIBxo6DBgwgTKlzIsKHDhwtpvIgh'
        'MAaMiS9Y3GDxouJFGhdvvHixsePAizFGGnwBouBIDSwhypxJs6bBljdwJtR5A0VBnwlRkET4AqZBnyAUOFDAgCRQm1Cj2iSp8uaNCQBQgICpYAIKBTA1oCBh'
        '4cYBBzlFwpwAwqtOCwosoHBAou1QqXjzPgThwAIJBSTSou3p9EXZG4NJvPgKAoVcpRNEGiQRWIOFlpWf6t3M+eDhgpcTagjLs6xWDRMmkNDaubXr1wxRaJZZ'
        'GLbt2wx5LtT6QoECFAw09MRN/HZjmJ8R8r3BYHVqloGLS3ct9wWDsw7/flUwvbtr1CT64gIMCAAh+QQFBgA3ACydAKABcgALAIW0wM7Wr2WntMKkr7qcp7Wb'
        'p7WYoq2QnKiNmaWEj5uEjpt3ip15g49ye4ZsdoFsdYI7qndWcHdgaXVgaXS8X1tXaHpVXWhSXWxMVF9IVmdJUFyOPD5IT1tDS1VBS1c9RE48RE46RlQ6QUwy'
        'PEkyOEIrNUErMTwpLjglLDUkLDggJS4cJC4cIiwaISwdHR4WHCYVGyUUGCIdFx8RFh8OEhwNEhwNEhsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIvQBv'
        'CBxIsKDBgwgTKlzIsKFDgx1EPJxIsaLFiw9fgCCBsaPHjwdfKNgIQsNAEChQTEBhgYGGCSBekOAIsqbNhiJJaGBwgARKEihIWHhhYaUDEjI5xrzJtCnKgRMO'
        'WPCZ8sUNoCkFLhWIoqlXmy+sCrSw9avZs01notBAE63bhVkFamRowYHKoRMmvGDQdcLbvwUdiFRAwgEIhhx9arSrQAHBtoDRKlWg0q8FCwxNQjUZV2vkt4dv'
        'dJ354qjBgAAh+QQFBgA3ACyrAKwBWwAJAIW0wM7Wr2WntMKkr7qcp7Wbp7WYoq2QnKiNmaWEj5uEjpt3ip15g49ye4ZsdoFsdYI7qndWcHdgaXVgaXS8X1tX'
        'aHpVXWhSXWxMVF9IVmdJUFyOPD5IT1tDS1VBS1c9RE48RE46RlQ6QUwyPEkyOEIrNUErMTwpLjglLDUkLDggJS4cJC4cIiwaISwdHR4WHCYVGyUUGCIdFx8R'
        'Fh8OEhwNEhwNEhsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIwABB3BhIsCCJFwUTKlzIsKHDhw5foEC4kMQNEBZQWLBwg4EGiCBDiowIAsSLCRg9gnBw'
        '0eINFBNIkJiAAsSEFxRBoBjJs6dDEgUKaEDowAEKlgp3aqzJUWFTn1BH1iT4ImPJGxo+6ozKtavXhkNB7vwaUiBZhmMHajA5FIUGjQcKPj2bEGdBgSQEgrC4'
        'lmvRq0uR3rAo8wZFugx1klBAQoOFF1kbX3Qwl2dVnSCyhk3YVDBip4OtTrjhwOXA0QkDAgAh+QQFXwA3ACy+ALYBOgAKAIW0wM7Wr2WntMKkr7qcp7Wbp7WY'
        'oq2QnKiNmaWEj5uEjpt3ip15g49ye4ZsdoFsdYI7qndWcHdgaXVgaXS8X1tXaHpVXWhSXWxMVF9IVmdJUFyOPD5IT1tDS1VBS1c9RE48RE46RlQ6QUwyPEky'
        'OEIrNUErMTwpLjglLDUkLDggJS4cJC4cIiwaISwdHR4WHCYVGyUUGCIdFx8RFh8OEhwNEhwNEhsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIxQBR3Bg4'
        '8AXBgwhvGFSYUKFBgQ0jNnyxcKADCzdIoHgB4gUKEDc+vlDQEYHAhQIvvjgAEsTGjh8zksgoECLEgyA6akBBQsMNDRgtcLjhgOJOjigskHRQAIUGEi8mJN1Y'
        '9AaDmQx4+rRQAONNgjlRSiVhQQMIByQUDE048wZGhBomkOXAU8ENEFKlulWIMafEv4ADCx5MuLDhw4hDtk0cOKZLji9IuAzr1+VexoFf+OR592XkyR0rC/RJ'
        'MCbmhCcrEv7qcXBAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBp'
        'dLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQY'
        'Ih0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZun'
        'tZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8'
        'STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEI'
        'HEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1do'
        'elVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEW'
        'Hw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCc'
        'qI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1'
        'QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISA'
        'ACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJd'
        'bExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0S'
        'HA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSP'
        'm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCku'
        'OCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUy'
        'ADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hW'
        'Z0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eK'
        'nXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQs'
        'OCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0A'
        'FgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48'
        'PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7'
        'hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwk'
        'LhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgA'
        'hbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NL'
        'VUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1'
        'gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBoh'
        'LB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztav'
        'Zae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1E'
        'TjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zw'
        'd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYc'
        'JhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSv'
        'upyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpG'
        'VDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBp'
        'dLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQY'
        'Ih0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZun'
        'tZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8'
        'STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0I'
        'HEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1do'
        'elVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEW'
        'Hw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCc'
        'qI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1'
        'QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2A'
        'ACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJd'
        'bExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0S'
        'HA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSP'
        'm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCku'
        'OCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUy'
        'ADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hW'
        'Z0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eK'
        'nXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQs'
        'OCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0A'
        'FgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48'
        'PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7'
        'hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwk'
        'LhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgA'
        'hbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NL'
        'VUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1'
        'gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBoh'
        'LB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztav'
        'Zae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1E'
        'TjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zw'
        'd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYc'
        'JhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSv'
        'upyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpG'
        'VDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBp'
        'dLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQY'
        'Ih0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZun'
        'tZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8'
        'STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEI'
        'HEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1do'
        'elVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEW'
        'Hw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCc'
        'qI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1'
        'QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISA'
        'ACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJd'
        'bExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0S'
        'HA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSP'
        'm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCku'
        'OCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUy'
        'ADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hW'
        'Z0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eK'
        'nXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQs'
        'OCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0A'
        'FgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48'
        'PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7'
        'hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwk'
        'LhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgA'
        'hbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NL'
        'VUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1'
        'gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBoh'
        'LB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztav'
        'Zae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1E'
        'TjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zw'
        'd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYc'
        'JhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSv'
        'upyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpG'
        'VDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBp'
        'dLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQY'
        'Ih0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZun'
        'tZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8'
        'STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0I'
        'HEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1do'
        'elVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEW'
        'Hw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCc'
        'qI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1'
        'QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2A'
        'ACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJd'
        'bExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0S'
        'HA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSP'
        'm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCku'
        'OCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUy'
        'ADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hW'
        'Z0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eK'
        'nXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQs'
        'OCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0A'
        'FgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48'
        'PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7'
        'hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwk'
        'LhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgA'
        'hbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NL'
        'VUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1'
        'gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBoh'
        'LB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AACH5BAUyADcALF0AFgICAAgAhbTAztav'
        'Zae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zwd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1E'
        'TjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYcJhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAgJACEIHEiwIISAACH5BAUyADcALF0AFgICAAgAhbTAztavZae0wqSvupyntZuntZiirZCcqI2ZpYSPm4SOm3eKnXmDj3J7hmx2gWx1gjuqd1Zw'
        'd2BpdWBpdLxfW1doelVdaFJdbExUX0hWZ0lQXI48PkhPW0NLVUFLVz1ETjxETjpGVDpBTDI8STI4Qis1QSsxPCkuOCUsNSQsOCAlLhwkLhwiLBohLB0dHhYc'
        'JhUbJRQYIh0XHxEWHw4SHA0SHA0SGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgJAG0IHEiwoI2AADs='
    ),
    'assets/badges/GitHub.webp': (
        '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'
    ),
    'assets/badges/alteryx.webp': (
        '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'
        'H1qIfmT1AgA='
    ),
}


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)

def contained(root, path):
    resolved = path.resolve()
    if resolved == root.resolve() or not resolved.is_relative_to(root.resolve()):
        raise RuntimeError('Diretório de trabalho fora do local autorizado.')
    return resolved

def runtime_path():
    return contained(ROOT, ROOT / 'work/profile')

def state_data():
    state = json.loads((ROOT / 'profile-state.json').read_text(encoding='utf-8'))
    if state.get('version') != 1 or set(state.get('data', {})) != set(DATASETS):
        raise ValueError('Arquivo de estado incompatível ou incompleto.')
    if not all(isinstance(state['data'][name], dict) for name in DATASETS):
        raise ValueError('Snapshot de dados inválido.')
    return state

def init(reset=False):
    runtime = runtime_path()
    marker = runtime / '.profile-initialized'
    if runtime.exists():
        if not marker.is_file():
            raise RuntimeError('A pasta work/profile já existe sem identificação do gerador.')
        if not reset:
            print('Execução já inicializada; os dados coletados foram preservados.')
            return
        # Resolve and verify the exact owned directory before recursive deletion.
        shutil.rmtree(contained(ROOT, runtime))
    state = state_data()
    runtime.mkdir(parents=True)
    for name, text in SOURCE_FILES.items():
        target = contained(runtime, runtime / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    for name, encoded in BINARY_INPUTS.items():
        target = contained(runtime, runtime / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded, validate=True))
    for name in DATASETS:
        atomic_json(runtime / 'data' / (name + '.json'), state['data'][name])
    for name in README_FILES:
        shutil.copyfile(ROOT / name, runtime / name)
    marker.write_text('profile-runtime-v1\n', encoding='utf-8')
    # Local-only exclusion: a checkout still has exactly five versioned files.
    try:
        result = subprocess.run(['git', 'rev-parse', '--git-path', 'info/exclude'], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        excluded = Path(result.stdout.strip())
        if not excluded.is_absolute():
            excluded = ROOT / excluded
        text = excluded.read_text(encoding='utf-8') if excluded.exists() else ''
        if '/work/' not in text.splitlines():
            excluded.parent.mkdir(parents=True, exist_ok=True)
            excluded.write_text(text.rstrip() + '\n/work/\n', encoding='utf-8')
    except (OSError, subprocess.CalledProcessError):
        pass  # A downloaded five-file copy does not need Git installed.
    print('Execução inicializada:', runtime)

def require_runtime(healthy=True):
    runtime = runtime_path()
    if not (runtime / '.profile-initialized').is_file():
        raise RuntimeError('Execute primeiro: python profile.py init')
    if healthy and (runtime / '.failed').exists():
        raise RuntimeError('A execução anterior falhou. Reinicie com: python profile.py init --reset')
    return runtime

def run_module(name, arguments=()):
    runtime = require_runtime()
    environment = os.environ.copy()
    environment['PROFILE_BUNDLE_ROOT'] = str(ROOT)
    try:
        subprocess.run([sys.executable, str(runtime / 'scripts' / name), *arguments],
                       cwd=runtime, env=environment, check=True)
    except subprocess.CalledProcessError:
        (runtime / '.failed').write_text(name, encoding='utf-8')
        raise

def test():
    runtime = require_runtime()
    environment = os.environ.copy()
    environment['PROFILE_BUNDLE_ROOT'] = str(ROOT)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=runtime, env=environment, check=True)

def prepare():
    runtime = require_runtime()
    destination = runtime / 'work/pages'
    if destination.exists():
        shutil.rmtree(contained(runtime, destination))
    run_module('prepare_pages.py')
    validate_artifact(runtime)

class AssetReferences(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls = []
        self.feed(text)
    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag in ('img', 'source'):
            self.urls.extend(attributes[key] for key in ('src', 'srcset') if key in attributes)

def validate_artifact(runtime):
    pages = runtime / 'work/pages'
    for name in ('index.html', 'en-US/index.html', '.nojekyll'):
        if not (pages / name).is_file():
            raise ValueError('Arquivo público ausente: ' + name)
    for name in README_FILES:
        text = (runtime / name).read_text(encoding='utf-8')
        for url in AssetReferences(text).urls:
            if url.startswith(ASSET_HOST):
                relative = unquote(urlsplit(url).path.rsplit('/assets/', 1)[1])
                if not contained(pages, pages / 'assets' / relative).is_file():
                    raise ValueError('Imagem referenciada ausente: ' + relative)
    return pages

def proposed_state(runtime):
    pages = validate_artifact(runtime)
    return {'version': 1,
            'data': {name: json.loads((runtime / 'data' / (name + '.json')).read_text(encoding='utf-8'))
                     for name in DATASETS},
            'published_sha256': {path.relative_to(pages).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted(pages.rglob('*')) if path.is_file()}}

def changes():
    runtime = require_runtime()
    candidate = proposed_state(runtime)
    changed = candidate != state_data() or any((runtime / name).read_bytes() != (ROOT / name).read_bytes()
                                             for name in README_FILES)
    atomic_json(runtime / 'pending-profile-state.json', candidate)
    answer = 'true' if changed else 'false'
    output = os.getenv('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as stream:
            stream.write('changed=' + answer + '\n')
    print('changed=' + answer)

def save():
    runtime = require_runtime()
    pending = runtime / 'pending-profile-state.json'
    if not pending.is_file():
        raise RuntimeError('Valide a publicação com prepare e changes antes de salvar.')
    candidate = json.loads(pending.read_text(encoding='utf-8'))
    if candidate != proposed_state(runtime):
        raise RuntimeError('Os dados ou arquivos mudaram após a validação. Repita prepare e changes.')
    # Called only after Pages succeeds in the workflow. Git commits these three
    # atomic replacements together; collection/render failures cannot publish them.
    atomic_json(ROOT / 'profile-state.json', candidate)
    for name in README_FILES:
        temporary = ROOT / (name + '.tmp')
        temporary.write_bytes((runtime / name).read_bytes())
        os.replace(temporary, ROOT / name)
    print('Estado completo e os dois READMEs salvos; imagens permanecem no Pages.')

def summary():
    runtime = runtime_path()
    if not (runtime / '.profile-initialized').is_file():
        print('A execução não chegou à inicialização; o último perfil publicado foi preservado.')
        return
    try:
        subprocess.run([sys.executable, str(runtime / 'scripts/run_summary.py')], cwd=runtime, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print('Resumo indisponível; consulte a primeira etapa com falha:', type(error).__name__)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('init', 'test', 'calendar', 'repositories', 'history',
                                          'render', 'prepare', 'changes', 'save', 'summary', 'notify-template'))
    parser.add_argument('--reset', action='store_true', help='Reiniciar somente a pasta de execução local.')
    options = parser.parse_args()
    if options.reset and options.command != 'init':
        parser.error('--reset é exclusivo de init')
    commands = {'calendar': 'fetch_contributions.py', 'repositories': 'fetch_github_content.py',
                'history': 'fetch_streak_history.py', 'render': 'design.py'}
    if options.command == 'init':
        init(options.reset)
    elif options.command in commands:
        run_module(commands[options.command])
    elif options.command == 'notify-template':
        print(SOURCE_FILES['templates/notify-profile.yml'], end='')
    else:
        globals()[options.command]()

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('Erro:', error, file=sys.stderr)
        sys.exit(1)
