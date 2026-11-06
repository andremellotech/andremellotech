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
from PIL import Image, ImageDraw
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
    """Use the complete published brand artwork; never redraw or recolor it."""
    scale = 2
    face = font(TYPE['body'] * scale, True)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    width = round(probe.textlength(label, font=face) / scale) + 64
    image = Image.new('RGBA', (width * scale, 48 * scale), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, width * scale - 2, 48 * scale - 2), radius=47,
                           fill=palette['matte'], outline=palette['brand_line'], width=2)
    # Only GitHub switches between vendor-supplied black and white variants.
    name = 'github-dark' if kind == 'github' and palette['name'] == 'dark' else kind
    path = root / 'assets' / 'badges' / 'official' / (name + '.png')
    with Image.open(path) as original:
        mark = original.convert('RGBA')
    # Contain the entire original canvas in the shared 32px logo box. This
    # preserves geometry, transparent clear space, colors and aspect ratio.
    mark.thumbnail((32 * scale, 32 * scale), Image.Resampling.LANCZOS)
    x = 26 * scale - mark.width // 2
    y = 24 * scale - mark.height // 2
    image.alpha_composite(mark, (x, y))
    draw.text((50 * scale, 24 * scale), label, font=face, fill=palette['text'], anchor='lm')
    return image.resize((width, 48), Image.Resampling.LANCZOS)


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

    # ===== data/tool-logo-sources.json =====
    'data/tool-logo-sources.json': '''{
  "description": "Exact publisher artwork, rasterized without tracing, cropping, stretching or recoloring. JavaScript and CSS use the original community authors' published symbols. All trademarks belong to their respective owners; nominative identification only.",
  "logos": {
    "github": {
      "filename": "github.png",
      "source_url": "https://brand.github.com/GitHub_Logos.zip",
      "source_page": "https://brand.github.com/foundations/logo",
      "archive_member": "GitHub Logos/SVG/GitHub_Invertocat_Black.svg",
      "source_sha256": "693d7abe6f899646cc2e96856723b45e95f71885a54910b2749f6decdf7e1ee1",
      "png_sha256": "2de8d69881943a36b35e981de032ad684d0a03a759c09b7131a1dce95acecf60",
      "original_size": [
        261,
        256
      ],
      "owner": "Respective product trademark owner"
    },
    "github-dark": {
      "filename": "github-dark.png",
      "source_url": "https://brand.github.com/GitHub_Logos.zip",
      "source_page": "https://brand.github.com/foundations/logo",
      "archive_member": "GitHub Logos/SVG/GitHub_Invertocat_White.svg",
      "source_sha256": "ccd84c89b1056345608fc3489357f8acc7397e49a3cdc2d418b6c8016911d47b",
      "png_sha256": "bc8d77f15a5263e5f8a37879694b7156c9ef30eb81813a2a7a578f7f2d7afbdb",
      "original_size": [
        261,
        256
      ],
      "owner": "Respective product trademark owner"
    },
    "sharepoint": {
      "filename": "sharepoint.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/SharePoint-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/sharepoint/collaboration",
      "source_sha256": "0e2713d7afa583ab45efc68a64cfe4e5a735c61a5f41f7d884c2df6130869a54",
      "png_sha256": "c0312ef34a2735adf3bbb4bb528f1bf6c120c7909a32ce6468e5d557e3ba1cd4",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "onenote": {
      "filename": "onenote.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/OneNote-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/onenote/digital-note-taking-app",
      "source_sha256": "81b19719c18dd2889f19aacc2238139d819f97653d0582a9638f107cf7a2e491",
      "png_sha256": "b9477e77a234b2b7c3635bff94349f4eaca3ea4bbce0ced373b3f2a9be1034ce",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "excel": {
      "filename": "excel.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/Excel-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/excel",
      "source_sha256": "ff01cdad545c6f1c0bff371c1f1758ad228174520c718c679bd454f6b4fcacf8",
      "png_sha256": "a2f3397fa77d3697e13bfca05f3d21ef511d0642d55ed32b1b8803eab2e437c6",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "outlook": {
      "filename": "outlook.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/Outlook-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/outlook/email-and-calendar-software-microsoft-outlook",
      "source_sha256": "d67b8bb4bb8d7afe8e71e066112452d5d681ea7991fa1ec7c37df962246b2c31",
      "png_sha256": "7c9304b16fe39b207dbd7bded24fc99386351a394b73c43917da80e1af4a45c2",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "powerpoint": {
      "filename": "powerpoint.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/PowerPoint-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/powerpoint",
      "source_sha256": "9bdf04481c14b24f419bad93903daff9884ad5a4b957a77241ddc0294ce5b423",
      "png_sha256": "5bd92cda28feff45b876b49eb3d11a0115ea381cab5d83f48fca1b6c31a4dcec",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "onedrive": {
      "filename": "onedrive.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/OneDrive-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/onedrive/online-cloud-storage",
      "source_sha256": "9f72ac359c7e03ca4723ce1a3b60f932a0bc5d2ce72dbdce365e83223142f6bc",
      "png_sha256": "a232d9506e44f945acc35c7c7a200e78d1b6554afe2e8f37c65f0ca8f92d2a27",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "word": {
      "filename": "word.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/Word-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/word",
      "source_sha256": "02bf3ae7245c5f4288e5135a31aa27c458e39ae431dc93d2d8847e5a7c123fdf",
      "png_sha256": "752076e8eaadad360b5f166a4aab4e3ef7aa6bab90dc0fe3b692834f2c715def",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "visualstudio": {
      "filename": "visualstudio.png",
      "source_url": "https://visualstudio.microsoft.com/wp-content/uploads/2019/02/BrandVisualStudioWin2019-2.svg",
      "source_page": "https://visualstudio.microsoft.com/",
      "source_sha256": "59e293462a6acb2ed52299c1bb554b25f1a784385fb5a4157f9735173152f7a2",
      "png_sha256": "3bf60a36522c3f581a5369a3c342e57ea3177be210681326a59d5c2e05075ffe",
      "original_size": [
        187,
        187
      ],
      "owner": "Respective product trademark owner"
    },
    "html": {
      "filename": "html.png",
      "source_url": "https://www.w3.org/html/logo/downloads/HTML5_Badge_128.png",
      "source_page": "https://www.w3.org/html/logo/",
      "source_sha256": "18b8cc80474535e1eaa3bbf64a7cf36b249c598fb18e9a441469b82405b3ed5b",
      "png_sha256": "7f6bff5fa168548e6bb592bbfe0ca3762cd419f1f04fde4f4135d1a784129c34",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "mysql": {
      "filename": "mysql.png",
      "source_url": "https://www.mysql.com/favicon-48x48.png",
      "source_page": "https://www.mysql.com/about/legal/logos.html",
      "source_sha256": "e013c0d393c7c6f899201fd691cf1216ad86b72861f7e66d9a1ada8f3064a0e2",
      "png_sha256": "190b9168029eefa6bdf575699948a9f417f56799d3afbda9272fee0e8a59ca72",
      "original_size": [
        48,
        48
      ],
      "owner": "Respective product trademark owner"
    },
    "css": {
      "filename": "css.png",
      "source_url": "https://raw.githubusercontent.com/CSS-Next/logo.css/HEAD/css.svg",
      "source_page": "https://github.com/CSS-Next/logo.css",
      "source_sha256": "28dceb38651b6d3d43119bae6f56dc6dd76415cfedd4a718afcd61fc7bec8ba3",
      "png_sha256": "921f5a5c28945fc985192f4d50bb4c6576811678af0fb17a9a58b6e29fa17041",
      "original_size": [
        2667,
        2667
      ],
      "owner": "Original community logo authors"
    },
    "powerbi": {
      "filename": "powerbi.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/1068058-Icon-PowerBI",
      "source_page": "https://www.microsoft.com/pt-BR/power-platform/products/power-bi/",
      "source_sha256": "45674a2ad73f337f5d524c5735f4a65d449c3942e5d79fcae7db42fa196453be",
      "png_sha256": "fa0dc5224c65d30a8d7906fa75b05ceb170d6b0c3fb887b6c6edd1f53732acc2",
      "original_size": [
        64,
        64
      ],
      "owner": "Respective product trademark owner"
    },
    "python": {
      "filename": "python.png",
      "source_url": "https://s3.dualstack.us-east-2.amazonaws.com/pythondotorg-assets/media/community/logos/python-logo-only.png",
      "source_page": "https://www.python.org/community/logos/",
      "source_sha256": "4008a934b415c152bfa513be3e9b05de4212ae41549a27f2c6c8d41b3a24a4da",
      "png_sha256": "3e761e3e7ce8d27bf9bb7e41be2d15b77eb3bacd8e90041f2f37d100ddcb2860",
      "original_size": [
        269,
        326
      ],
      "owner": "Respective product trademark owner"
    },
    "javascript": {
      "filename": "javascript.png",
      "source_url": "https://raw.githubusercontent.com/voodootikigod/logo.js/master/js.svg",
      "source_page": "https://github.com/voodootikigod/logo.js",
      "source_sha256": "a70a3d8d36ea6b0e614a04ec30d5a4fb2bf36d515492cb84050ded2b84d14393",
      "png_sha256": "a5d2924604927b1973f40d69e5de10858143359fda851b21aaccc8c49a3c1f18",
      "original_size": [
        1680,
        1680
      ],
      "owner": "Original community logo authors"
    },
    "qgis": {
      "filename": "qgis.png",
      "source_url": "https://www.qgis.org/styleguide/visual/qgis-icon128.png",
      "source_page": "https://www.qgis.org/styleguide/",
      "source_sha256": "42170afd8121d1b7e463834d69a422cadcec7e509269c39f78e9947520ff15cd",
      "png_sha256": "9f951214fa081c32ec08c1831f240205af7a00c94c855ee749cb11e6e4d59206",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "teams": {
      "filename": "teams.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/Teams-Icon-FY26",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-teams/group-chat-software",
      "source_sha256": "6a33d49f19d1be2bcdf86921935a2171e5c18c3b11abe297ca03d5f4f302ba3a",
      "png_sha256": "6986fcccb8b48d3ac7bc5b5cbb9e1350b0d11f3c095f55f48f9294c7609e7ee8",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "forms": {
      "filename": "forms.png",
      "source_url": "https://www.microsoft.com/content/dam/microsoft/bade/images/icons/en-us/m365-app-icons-fy26/Forms-Icon-FY26.svg",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/online-surveys-polls-quizzes",
      "source_sha256": "4c5e9957fc26175ed71e83c427144b6ab266f749f5b72c3fd478cdb59691355c",
      "png_sha256": "1e0c55d4d4c3f11be8f187c4ba692b6e551c491be8b98c9eaffeddc9522c3344",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "lua": {
      "filename": "lua.png",
      "source_url": "https://www.lua.org/images/lua-logo.gif",
      "source_page": "https://www.lua.org/images/",
      "source_sha256": "9c3a3208ef05e12110f9b7b491cef676e650e4ebf3d36c4414268666bcc95d8a",
      "png_sha256": "5848da199ef6f87d08a50578d00b49d3277dd5ee7c4b6e9228fe8a27a72cedb2",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "git": {
      "filename": "git.png",
      "source_url": "https://git-scm.com/images/logos/downloads/Git-Icon-1788C.svg",
      "source_page": "https://git-scm.com/community/logos",
      "source_sha256": "1080a5430edb6278dc03e4b04efc16c8bed5b943408d648ad721a28836814220",
      "png_sha256": "17129afa94ff1aa2dccd21f0e72b8233ba5c72181ff17f84f5f50bc0a0cdb7aa",
      "original_size": [
        654,
        654
      ],
      "owner": "Respective product trademark owner"
    },
    "access": {
      "key": "access",
      "filename": "access.png",
      "source_url": "https://www.microsoft.com/content/dam/microsoft/bade/images/icons/en-us/m365-app-icons-fy26/Access-Icon-FY26.svg",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/access",
      "note": "Current FY26 product asset",
      "bytes": 4090,
      "icon_kind": "access",
      "source_sha256": "524381782541b874279fcfc9ede2cadddf5c21a8eb2b9ca0f0199ba56037d5e7",
      "png_sha256": "fafcb30945836f974f61a9b707abe3359ac881504f4dd705faf43282c761ba5e",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "lists": {
      "key": "lists",
      "filename": "lists.png",
      "source_url": "https://adoption.microsoft.com/wp-content/uploads/2021/02/lists-icon.png",
      "source_page": "https://adoption.microsoft.com/en-us/microsoft-lists/",
      "note": "Exact Microsoft Adoption product icon; native 600x599 PNG",
      "icon_kind": "lists",
      "bytes": 5428,
      "dimensions": [
        600,
        599
      ],
      "source_sha256": "e2ec8032834c6faf1d77b6feea78c8f9b88f4f04da6092b78ad25154945a643a",
      "png_sha256": "857f4c7acfd0c98a47b11e37d1c30dc5d0ea4af338f6201d00dad8024e119d65",
      "original_size": [
        600,
        599
      ],
      "owner": "Respective product trademark owner"
    },
    "whiteboard": {
      "key": "whiteboard",
      "filename": "whiteboard.png",
      "source_url": "https://whiteboard.cloud.microsoft/resources/favicon.ico",
      "source_page": "https://whiteboard.cloud.microsoft/",
      "note": "Exact app-specific Whiteboard favicon, losslessly extracted 56x56 image from ICO to PNG; full artwork preserved; original also saved as whiteboard.ico",
      "icon_kind": "whiteboard",
      "bytes": 1895,
      "dimensions": [
        56,
        56
      ],
      "source_sha256": "a204c21dce5700a3a74353b281c9cfaf9fe1cb1dc5ebf949cfdcc045ea12ace3",
      "png_sha256": "09bc4d09aa26fb676efa1c7fad1c684e319adca1b270bb4ded44940c9bc2fc15",
      "original_size": [
        56,
        56
      ],
      "owner": "Respective product trademark owner"
    },
    "bookings": {
      "key": "bookings",
      "filename": "bookings.png",
      "source_url": "https://catalogartifact.azureedge.net/publicartifacts/10100100.9d34a54c-e776-490b-aa19-4ed98464d29e-4a63b91e-cd78-4510-9ffa-d17a8e122cdc/image60_BookingsIconImage.png",
      "source_page": "https://marketplace.microsoft.com/en-ph/product/office/WA200004183?tab=Overview",
      "note": "Exact official Bookings marketplace logo; publisher Microsoft Corporation",
      "icon_kind": "bookings",
      "bytes": 15034,
      "dimensions": [
        300,
        300
      ],
      "source_sha256": "ebd1dcbb832e9b41d6c1765577d8e62eb7c79a6685cfcf125f1888139f4c0835",
      "png_sha256": "caef8b1787a4b7bd0d995acbfdfa68a824bc09d27518f4d5ca48c0552f904998",
      "original_size": [
        300,
        300
      ],
      "owner": "Respective product trademark owner"
    },
    "stream": {
      "key": "stream",
      "filename": "stream.png",
      "source_url": "https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/stream_48x1.svg",
      "source_page": "https://www.microsoft.com/en-us/microsoft-365/microsoft-stream",
      "note": "Official Office UI Fabric brand asset; may predate FY26 redesign",
      "bytes": 501,
      "icon_kind": "stream",
      "source_sha256": "a158cb8c960f2044f8969d0abd229297243e22714d92aa9bb81666874aa32abc",
      "png_sha256": "4dbff17fc915d92359340c1221049b905eebfa2dd5753beb36df4cb96b45bd8c",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "sway": {
      "key": "sway",
      "filename": "sway.png",
      "source_url": "https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/sway_48x1.svg",
      "source_page": "https://sway.cloud.microsoft/",
      "note": "Official Office UI Fabric brand asset; may predate FY26 redesign",
      "bytes": 2307,
      "icon_kind": "sway",
      "source_sha256": "55801cfb79307945ba285b4e4edf6029875770f2dd38c2425b4a3a8cc15e9b43",
      "png_sha256": "b5041c0b83ada51059606411b473fb6fd7f8f5a59d5887c73878171b75c8f57e",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "visio": {
      "key": "visio",
      "filename": "visio.png",
      "source_url": "https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/visio_48x1.svg",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/visio",
      "note": "Official Office UI Fabric brand asset; may predate FY26 redesign",
      "bytes": 2062,
      "icon_kind": "visio",
      "source_sha256": "bd9227bec33e37b26aefd116dba97e3ecb9dce92073206c571f990a83ab240d0",
      "png_sha256": "17cfb3c55548256c590024104c3d1e612380284d2be06fda433203afa9935d64",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "project": {
      "key": "project",
      "filename": "project.png",
      "source_url": "https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/project_48x1.svg",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/project/microsoft-project-enterprise-plans-and-pricing",
      "note": "Official Office UI Fabric brand asset; may predate FY26 redesign",
      "bytes": 1730,
      "icon_kind": "project",
      "source_sha256": "1b4c9f741d94735e2cef138278c73fce636b736dd82ef2502865cf0e7c87e2bf",
      "png_sha256": "34400fc745ecb349cabcb5c9d4a36c35bda96abd9235f5a43b8f7a97ec87ff10",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "copilot": {
      "key": "copilot",
      "filename": "copilot.png",
      "source_url": "https://www.microsoft.com/content/dam/microsoft/bade/images/icons/en-us/m365-app-icons-fy26/Copilot-Icon-FY26.svg",
      "source_page": "https://www.microsoft.com/pt-br/copilot",
      "note": "Current FY26 product asset",
      "bytes": 2849,
      "icon_kind": "copilot",
      "source_sha256": "f16fdf8123d9dc4597561bfc62cebf5bc43262a1301d9acd470c4914e6dd1e1f",
      "png_sha256": "ca8ea1d28af8534e0b725f4acf58e3b2f09b69fbb162a3faa30e4f18df548a3b",
      "original_size": [
        1365,
        1365
      ],
      "owner": "Respective product trademark owner"
    },
    "planner": {
      "key": "planner",
      "filename": "planner.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/3381754-Pricing-Icon-Planner-20x20",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/project/microsoft-project-enterprise-plans-and-pricing",
      "note": "Official vendor-published exact artwork",
      "bytes": 4743,
      "icon_kind": "planner",
      "source_sha256": "b03976f9a4039c6bcaf59568f24d274e335a627b5e1971c7b4c707c491507e16",
      "png_sha256": "9cdd29f904303562360285ac040ea5f3f742d612d076b9b69f987fef018e97d3",
      "original_size": [
        53,
        53
      ],
      "owner": "Respective product trademark owner"
    },
    "loop": {
      "key": "loop",
      "filename": "loop.png",
      "source_url": "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/Icon_Microsoft_Loop_32x32",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/planner/microsoft-planner",
      "note": "Official vendor-published exact artwork",
      "bytes": 3679,
      "icon_kind": "loop",
      "source_sha256": "0f4dcf9d87c73118dc1b993a085053de40a433d5e5ff8b4c7fdadd4ca74d9d47",
      "png_sha256": "e2949bda38400c6119861e0c07618cbc066a2bc57bfd7119a82f49a5854e714e",
      "original_size": [
        629,
        629
      ],
      "owner": "Respective product trademark owner"
    },
    "todo": {
      "key": "todo",
      "filename": "todo.png",
      "source_url": "https://res.cdn.office.net/files/fabric-cdn-prod_20230815.002/assets/brand-icons/product/svg/todo_48x1.svg",
      "source_page": "https://www.microsoft.com/pt-br/microsoft-365/microsoft-to-do-list-app",
      "note": "Official vendor-published exact artwork",
      "bytes": 774,
      "icon_kind": "todo",
      "source_sha256": "dc1680bbac2c9edcb0a8145b2995edf8621d60135d1487a2f2b146c34c96745a",
      "png_sha256": "f1ad15c42f6709c54a43d6e88a276ebb415d25cdd2061665e8d8d37c765acc88",
      "original_size": [
        128,
        128
      ],
      "owner": "Respective product trademark owner"
    },
    "powerapps": {
      "key": "powerapps",
      "filename": "powerapps.png",
      "source_url": "https://download.microsoft.com/download/498606aa-6d27-4f13-aa5c-1401078c153b/Power-Platform-icons-scalable.zip",
      "source_page": "https://learn.microsoft.com/en-us/power-platform/guidance/icons",
      "note": "Current official Power Platform icon download package updated December 2025",
      "bytes": 4398,
      "archive_member": "Power Platform/PowerApps_scalable.svg",
      "icon_kind": "powerapps",
      "source_sha256": "c357907ad0a2d24a6d8c82b23fe4d2aaa4a4524076991f74770fc043a4cc455a",
      "png_sha256": "d94273b576a3814e9f8fd680c917b7a65cd420396324aa4b3be938cb78a412af",
      "original_size": [
        256,
        256
      ],
      "owner": "Respective product trademark owner"
    },
    "automate": {
      "key": "automate",
      "filename": "automate.png",
      "source_url": "https://download.microsoft.com/download/498606aa-6d27-4f13-aa5c-1401078c153b/Power-Platform-icons-scalable.zip",
      "source_page": "https://learn.microsoft.com/en-us/power-platform/guidance/icons",
      "note": "Current official Power Platform icon download package updated December 2025",
      "bytes": 2545,
      "archive_member": "Power Platform/PowerAutomate_scalable.svg",
      "icon_kind": "automate",
      "source_sha256": "2025db7bb3feec49d75681934b8561fb958cf11bdf0e2acf6e2b28db5c755e8d",
      "png_sha256": "cdb5dda228c4aecc604fcf7dc6c6d1026aad5b751e3fec8d703a78a7f65f98b1",
      "original_size": [
        256,
        256
      ],
      "owner": "Respective product trademark owner"
    },
    "autocad": {
      "filename": "autocad.png",
      "source_url": "https://help.autodesk.com/cloudhelp/ENU/CONNECT-User-Guide/images/AutoCAD-icon-original.png",
      "source_page": "https://help.autodesk.com/cloudhelp/ENU/CONNECT-User-Guide/files/Troubleshoot_AutoCAD.htm",
      "notes": "Unmodified official Autodesk help icon (small native raster).",
      "source_sha256": "95f3672f5e67fb74f47e9f6c3d7cd0b8bfbef65fe068287c643c8eaa2adb76e9",
      "png_sha256": "aa4f7a6cd01acc59768948ef48d942b94760f65e79378103646ce3af335d9d1c",
      "original_size": [
        48,
        44
      ],
      "owner": "Respective product trademark owner"
    },
    "revit": {
      "filename": "revit.png",
      "source_url": "https://help.autodesk.com/cloudhelp/ENU/CONNECT-User-Guide/images/Revit-icon.png",
      "source_page": "https://help.autodesk.com/cloudhelp/ENU/CONNECT-User-Guide/files/Troubleshoot_Revit.htm",
      "notes": "Unmodified official Autodesk help icon (small native raster).",
      "source_sha256": "bf06518d1d813b324625de6a7e98d232dc6dced36e2af18ea899dc9a12c0d95d",
      "png_sha256": "da4f11539e9295b187bd28f61d8ffdf68a9fc6d4bee7b6a2e35a8037a696af80",
      "original_size": [
        48,
        44
      ],
      "owner": "Respective product trademark owner"
    },
    "googleearth": {
      "filename": "googleearth.png",
      "source_url": "https://www.gstatic.com/images/branding/product/2x/earth_48dp.png",
      "source_page": "https://earth.google.com/web/",
      "notes": "Unmodified Google-hosted product icon, 96x96. An official app favicon is also saved as googleearth.ico.",
      "source_sha256": "393f41ef048e0c7da97dcb8b55cb0ff61390a5265d25e71d0173c5a160e6d850",
      "png_sha256": "9c9af1bd0af40ff350ed0fc6c8a4cd85df34ad326ce5b27333531df7ecfb26c0",
      "original_size": [
        96,
        96
      ],
      "owner": "Respective product trademark owner"
    },
    "oracle": {
      "filename": "oracle.png",
      "source_url": "https://www.oracle.com/favicon.ico",
      "source_page": "https://www.oracle.com/",
      "notes": "Official corporate favicon, unmodified ICO; may contain several sizes. Largest native ICO frame losslessly decoded to PNG; no crop, recoloring, resize or geometry change.",
      "original_filename": "oracle-favicon.ico",
      "source_sha256": "258741bdfd5fde8ef9a60cd95e6a642bab47c57f15cf9550318d69e93805b90a",
      "png_sha256": "900b79400479f0f905b87b7c2751fada095cc8f8f88a66e57688785ee60c4bc7",
      "original_size": [
        48,
        48
      ],
      "owner": "Respective product trademark owner"
    },
    "sap": {
      "filename": "sap.png",
      "source_url": "https://support.sap.com/content/dam/support/sap-logo.svg",
      "source_page": "https://support.sap.com/en/index.html",
      "notes": "Exact vendor-published gradient SAP logo. Main marketing page denied requests; public support asset succeeds.",
      "source_sha256": "4146d5df8fc04673049281dfd85569324a49e4ba68968acfbe125a126c93800a",
      "png_sha256": "5d5774f173877692c255c423691f160725e60a0126a95b18feea74924376a460",
      "original_size": [
        245,
        120
      ],
      "owner": "Respective product trademark owner"
    },
    "alteryx": {
      "filename": "alteryx.png",
      "source_url": "https://cdn-ilebkin.nitrocdn.com/JEFSMzmzwFcXftzdERHKYzgDrSDuEATd/assets/images/optimized/rev-f1b43a1/www.alteryx.com/wp-content/themes/trifacta/assets/favicon/android-icon-192x192.png",
      "source_page": "https://www.alteryx.com/",
      "notes": "Native 192x192 app/site icon linked from official homepage; downloaded from its official linked optimization CDN.",
      "source_sha256": "e0c65ca7da0ad51ec8fe292b8d4d27208e6f3440e7d580e2b499648771812468",
      "png_sha256": "f1c8150746595862ca96829931634b165aad40b8ab139fe1f9208c9d51f578f0",
      "original_size": [
        192,
        192
      ],
      "owner": "Respective product trademark owner"
    }
  },
  "attribution": {
    "Git": "Git logo by Jason Long; https://git-scm.com/community/logos",
    "CSS": "Original CSS community logo; https://github.com/CSS-Next/logo.css",
    "JavaScript": "Original community logo by Chris Williams; https://github.com/voodootikigod/logo.js",
    "Other products": "Marks belong to their respective owners; source pages and original file hashes are recorded for each asset."
  }
}
''',
}

BINARY_INPUTS = {
    'assets/badges/official/access.png': (
        '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'
        '6/8D756QQM4LRosAAAAASUVORK5CYII='
    ),
    'assets/badges/official/alteryx.png': (
        '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'
        '+iwPrv8PyDLAekDKurkAAAAASUVORK5CYII='
    ),
    'assets/badges/official/autocad.png': (
        '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'
        'tgAAAABJRU5ErkJggg=='
    ),
    'assets/badges/official/automate.png': (
        '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'
    ),
    'assets/badges/official/bookings.png': (
        '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'
    ),
    'assets/badges/official/copilot.png': (
        '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'
    ),
    'assets/badges/official/css.png': (
        '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'
    ),
    'assets/badges/official/excel.png': (
        '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'
    ),
    'assets/badges/official/forms.png': (
        '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'
        'D3vYQzEV4/8Adpg1S+CZrLIAAAAASUVORK5CYII='
    ),
    'assets/badges/official/git.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAE/ElEQVR4nO2dzYskNRTAW9a/wIvgBwqC6Ha/V7N+4Ey9'
        'VzuroKKiIjoioq5415NelGUPXvxvvCi7Cyt7dNX14lEFV9fbzFRS7cnLlrxqWRVnurvSSSWVJJDbMPPq90uqkrwkM5mMrLS7u7erCt5VBBc14Q1N+JsiuFAT'
        'vtPu7Z3wHV/UZb88dZdi+FYztkdVRfCN/IzvOKMsh9X0XsX483Hw/6lwXe0W9/uON1H4mCX4h49Zgn/4mCX4h49Zgn/4mCX4h49Zgn/4mCWsKu1kcpti/M4d'
        '/EUVwSK6d9dMoaiy2FKMB64l5MlalhB2UbknDPPOnywpmuFRzVjnb4KDIh9BTfh9Q7C97OdyT3A+1IQmS/A+zocswR98zBL8w8cswT98zBL8w8e1JdQ0LeoK'
        'Xj7YhXv+eGJ253xn9pAifE8zXMnLFhvBx7UlHFd0WTyjCPaTXjuys6oJxhK6HsF4mKQEu0vKYCxBMbyW3OvIzXo+NLqcPWYSj8y2k5HgMpmiqHjFJCZF+KH1'
        'WEKU4DqTVe+cus8krprwRScNIiQJ7tOI2Mpw0yS2mpBdxRSEhCHga+kBpwFM4pNXl8u4vEoYCr5mbBvGt01i1IyfuY7Ni4Qh4WupBF+ZxBllUmdw+LyodQkv'
        'TVKX4Au+XtS65hkmK8Ez/PbvOpfvwap8cnQSAoHf/qu+cVScq44ojVJCgPDbhou3joq1YfwgqhxziPD1EgGa8Fw0OeZQ4euVAroHH7eEkOHrtQSMWELo8PXa'
        'AkYoYQzwdS8BPSRU+KoAOtgu7j7cwZkmeFMxXBpsdDQW+Lq3gPUkHFcaguds9pAjJSxOoI8DvjYSsJmE+enpw5pA25Rw60R/d/fCkuP/8QjAzXZbUPG6zWdQ'
        'BFe7iaNcfOEbqB5MwEKC3tl6vK8AWf7QjNdsPodcMDLpbh1JSgC20ppNeoGq4CObz6EYv5Skxa/JCSinD5gJwKfsPgtcT1JAbZjkl+Gq1Wch+EVeQRdSE6DK'
        'Yst026P1V1BNcDY1ATXBWSMBjOetP4cMheSmqZQEaIYrfeF3w3WCH209g2L8+lb+Io2JGP6nyvb2nq3/fScTsTSWInCjHLOi4oxi/NMW/NGvBzV2BEidy+86'
        'Lscsrx3Jsg0Cf0wSGnsCFpXwB83wsa7wWdmJ3ZSz5xXjp4rxJy95YtmLafOPBy+AA8yKhSyhGZWADfLCoUpoRiPAws6IECU0oxBg8QLZ0CQ0wQtwcHtvKKMj'
        'xXhTTr64nixtEF/E+0MJb8y5oJWHMiymD4OB718C/L7uUSU5SS+TrOjg+5KgGG821bTsE6N8J6KE70UC4edGOdxuhhsh/MFHR2SWw9UMn7iNLYD/VTBITyjN'
        'cri2M1jBtPzBJWyfvMMkLtl+Ej38ISQ0jA+abitMAr7rb0JtmMOVJeXo3vleegLh5b5xLLZcelrPj1FCUxUv9IlBMllJwnclQTEeznnrZFA53OR6AoGWOcGy'
        'HK4syGX4LiVwV6/JRllVFk+qCh7RNHtaNk1Z3rcz3pYfej5BxzDaiVcCxAd/PBIgXvjhS4D44YcrAdKBH54ESA9+OBIgXfj+JUCG709Chu9RAuSW708CZPj+'
        'JECG708CZPj+JECG708CZPj+JECG708CZPj+JECG76rsy4l+gqvLjv//7wR6LnZLu7d3Qi7wlptGpLV3LZ7gi+7A9Yq7o0MsfwHenGHSZViqAAAAAABJRU5E'
        'rkJggg=='
    ),
    'assets/badges/official/github.png': (
        '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'
    ),
    'assets/badges/official/github-dark.png': (
        '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'
    ),
    'assets/badges/official/googleearth.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAAsSAAALEgHS3X78AAAQ6UlEQVR4nO2ceVQUZ7qHO8lMkrlnZv6+f94zkaahAU1w'
        'xmiccU2iietkiAqNLG5RY4xZ1USDiYLiEiWJezLRqPEmZkYdl2RcUEDohVX2VXaBRlm6u6qA7v7N+aq7vE3T0FXVVYBe3nOe4wYc+/m99X5dX32gUIzUSI3U'
        'SI3USA2zAvCYxWIZS9N0rJmiEi0W5hJFMcUWijZaKLqVYZhOhmHgpJOm6UaaphtomtYzDPMTwzC7aZpeZrFYnh3q1/LQ1P1OeuK9TmZPq6nn3y2m7tKmDmtr'
        'zT0rVdXagwqjFRXGHpQbe1B9rxuNbV0wdjIwWWhQFMVC07RHGIYx0TSdRlFUgsVieW6oX+ewqhIjxpYbbbur7tlzi5rtTM5dILMB0NUD2jp+5N21odLYjZYO'
        '5kEY/eEMpZ5hmCMWiyVU8f91vBS2ILqwGTn5TUB2I2CoB3R1vdGKIKvRjjut3egw07zCoCgqj6KotwA8pXjU6w7wdFET3i5oQWUu1+l1/aP1hXqgrKUH7Sbv'
        'QTjDaO7q6toE4L8Uj2LHE/H5zWgi4g3OEaPjkCGEDCckiApjN8wWz+ItFssDnEG0UhT1DoDHFY9CFTRjdEEzdHl3Ab27+Hr5A+DIbLCjsY0ZMADXIBiGyadp'
        'eoriYa1y4KlCI3blN4HhFtUBqZM3AI7Slp4+V0N/IdA0bSOLNYDfKB6mym9GSEEzSrNJ19c7SK8BrpQB5/KBH3OBU5nAd3rghMHx+9NZwD9uAz+XADeqfA8h'
        'YwByGmxoc1kbPAXgFkQJuSdRPAxV1IIF+c3oIF2fXgP7xSKH5CO3+nLYlbTe/F3rCOR6hfRXAUFfZ0ez823rQAFwMI5aoRjOC22xEVtymmBNq0L3DznA0XTP'
        '4j0GcKtvCBzHdY4rQ1srXQDsAl0H1Ld18QrAeTXYGYZJGnYLdCHwZH4zfsqqh4WMl6O3/g8pAjjk5Fsd8EupdAFw1NwTFAIZSRcAPKkYDkVuYPIbkXqtAh3f'
        'ZDi6Xq4ADjn5PgtIvSNdABm1okK4AuDpoZb/uKEBl3/KA82KT+8bwFEZAjiU5vj8S0XSBUCouy84hOtDFgKZ+al38P0pA3p6yR+EK+CQCz/mOORJEQBZY8i9'
        'gpAQGIY5R1wMegC/FCPpu0zY+sgf5AAOpgLH9UDKHd8D4II0dtBCQ/hqUOVfKMCqE3qn5AHkD1YAB1MBsv6Q+wdfAyAY6u1oN1OCQqAo6s1BkX8xB2NOZ8Hk'
        'LtoTA8n3dh9wWGAABNIAyZW+B0DIbbTBZOYXgPM+wSL7zVpaCX53JgclfOQPRQAHUx1f91qFAPn9BEAgu6l8AyDQNF0K4HeyBXAuF0fJpX7ER/FCxs9hgQFw'
        'V8LNSt8DSK8FGgQsys4QvpVF/vnbmPSdHt2eZPKVLnf3H3Th6wwgrdr3ALR1drSZBK0HVsl3UZOT8asfspAnVPJQdP9BJwdSgWM64FatOPlcAITbd22CrgKG'
        'YQoA/FqyAM7m4T1u9Egu/5Z8ARDIXbOvARCqBdwpO0fRBknkJxfit6f0qB9u8g+leZfPcb7A9wDIu6r7nYLuD5oA/N7nAM7kYrO3XU055B+WoPs5yN9dKxc+'
        '/93JEfjWlKbpT32Sn16H35zIRDMnzJNY8uLiL1rx9qkuLP2GgWY/hdeTLPjbPgv7+6VHGaw+1oVPzvbgi2S7JPIPCQyA8HU6kFrtWwCEcmO3kKugFcBvRQfw'
        'z1y86al7yd8RmWtPdrGyX9vrmb96IPowjY1nunEgZXC6/8BA6wHP8eNOU7ug/aK3RMknG0wns6B3l38gxY53TnX3K9grnztY+CWFDWe6sT/FLnv3PyAFuFzs'
        'ewDkrSnf9YCiqFxRAZzNwQRy2bJSnPL3XrEh8hAtTryLfFdeT6Kw5V89vOX7GgB5HQ9GkQj5HOSURQfP+wOapicLDuB0Jva7duXWi1ZWlhTSCfPdWH28C1/d'
        'sMsn3xkAgR1FIrvflSzycL+TVwgHBD9oOa5DJSd/+2Uru6j2kihCen/y539uwbw9jrEUf8kqSj6f7nflconvARD09Xa0etm+piiqVtBz5PNZeJ5dfNOAXf+2'
        'IYx0vhepfJg/gPx5TsifN5/tka37OR6MIh8DSHd+Djm13TnAFragMXTCgK1E/sFU2DUHaFaKHOLnu8l35cMfu2Xr/v1OyHkkX+X3CqIOKGyyosrYjfr7Xahu'
        '7UJ5Sw9yG2zkHGwC7wCOa3GFBPDu910epfkqfSD5c11Yd6oLB32VP0AAhEvF0gRwayBq2ANmv/CSTzaRvtaibdcvNhsfiWLor+vnemDNiS7Z5BPI1UWepPna'
        '/d4C0NbhHoBfeQ3gTC6eJf+pld929ZrLcoqf14/8ubsdfPBDt2wBEMgpPCJJzgAIOfUY4zWA73RYmnTdTs/vR5SU0uf1J95FPmHebgs+Od8ji3yO09nyyicY'
        '6rHcawBHUrFr7fdddm/ipGAuD/kcJMyES1b+8gUG8FUKcDZf3gC0ddjpNYC91+3Ji76kWBGDLn6PZ/lznLy2l8KeqzbJ5XMBEC4UyRdARh1OeA1gx889Oe5S'
        'ZJe+x7N4V/kcEQdofHVTHvlfOf9MDgJLLZ9dY+pwzWsA75/uKvYmSxLhIuTP3uXgze+6eMvnM3p6QcJNAcixeqkDyKhBkdcAVvydqRIkTyy7+Yt3lc8Rd94q'
        'efdzAXCcLZBOvpM2rwFEHqSaegkZRPFzeconkPVg33W7bPIJX94Evs92nK6QIoBzBajwGsBrSRTdryAZhM8dQHx/8mc5Wf4NI1o+3wAI5JHslXIB8t0DqIb9'
        'f7Nh/fIGrF4DmLvbzPCVJgVzBIh3lc+x6Z89gue+EPmunMx0HH0U0v1XK4CvtUDSDYK922sAs3ebjXOGUPwcAfIJ8/ZQ2H3VLrt8DvLx5DQ22UNKqfYcQFoN'
        '8HMpcCIT+OImJx9Ium6zeA1gzi5zlbuQwZA+R6B4lp0OyFO6/WLlCwzAnaMZjgNgp7Ic34z4jdbxNb644eCB/BvAvuu2du9XwE5zrjdRrqHMTjRj1vYOzIxv'
        'Y3/lK5uP+Nk85HO8e5o8X5a3+z3Bie6PXgEk2+54DWDWTlOqN2GvJpow+aNmjHu7BqErK3vxx1VVGL+uDtM+acGsRJMo6bMFiOcgnxN/2TZs5bMBXO3J8B5A'
        'YvtJVxG9pO22YMrHzRi7qqqPeE+Qj5u0oQmzdpp4SZ8tUv6rTshJjT1X7aLkSx1Akgc+v9bzk9cAXt3ZtsmjlJ1mTHivAc+94V08gXwcBwli2majePG7Bhbv'
        'CtnHSkq2yzr3xXQ/YesFyvtm3Jz41r/2kbPTghfeb+wlVQwvvN+AWYlm/tJ3ee96V15JNLNEHXbsFw0n+YSYI/dXeg1gxmcN/uSFu0qa9onRZ/kcf1pTg5kJ'
        'naLFz+pHvmsAhJXfMrLIFxvAriv25mkbKpVeA4iLw+OzdrSbOBHkxYSuvuOT9Gfd+OOb1ZiZ0CGLeI6ZJIRjXYM69wfq/iVHTS2KsLAnvAbArgM77l/mhEzZ'
        '1NJHoBSMJSHEd/ISL0Y+BzkwzN5ADYL8frv/qr1z+qfGFAXfmp1oXMeJeX5trSwBOEKowSvbTaLE85HPEXOERlLy0IyepBuwk2cYU7fcjeMdwPTPygLIYjlr'
        'p9n63MoqyYSPWdGX59fVsQuzHOJZdjgI309j9xX7YMvH2lPd9qnbOjF5Y6H3B/K9x1B71cz4jvuepHHwleyNiR80ihbPRz4HuY/ZdM46aKPno7NW+4sJZkzZ'
        'YixWKBTCfpzBKwnNe16Ob2sQI1Qoo1dUYtJHLYLFv8JTPMcMJ6uOdbEjSU75G/9hxfQEM6bFmzHlk5odCqH10oZS1YytrdVySh/twpgVVZj+WbvkXe8un4Oc'
        'slh/pkfy0bPvBrDmZPcD+VO3tmPKhrJxCjE1dVPTxd6SpJHdH8+uqsaMhE7hHT+A/Bn98PJ2B69/QWHzWSu7bexr92+7ZEPYFxQrnmPylia9QmyNf69sxejl'
        '5bwF+krI8kqMfauWFSdH17vL53hpuxnzPrfgrRPd2HnFLlg+eT5NDjG7ind0fycmfli0WHQAk6PvPD16aWGD3NJD3Bj/bqNPXT+Tp3hOvjuv7aOw7BsGH/zY'
        'g08vWLHjFzsbzN7rwI6f7Yg7Z2X/LeYIw75Vn+4mnmWbGZPimmpClx/y7Ru2R8dmvyvlVeBJeIgHXljfJJl4IfJfSujLi24Q4a70kc91//ryDxW+1v9EJz89'
        'eklBA19xPrOs4gET1zfzFj9U8vvr/ilxTXfHrdH6/o3apEKiMlcGLyuTXXiIB/6ysUW0+KGSP/WzdkxaX+b9IC7/wmNB0bmZgyE8xFMIm1ol6XrZ5TsDmLy5'
        'Vq+Ii5P2Z4sGL84eH7yk2NpHkI9yQzwQ7AY7jja0+NT1vsjnO/fZ7t/SavvLh8UTFHKUOiprT8jSMslEhwwg3RPjP7iLGdvlE+9r50/Z2m4fv65or0KuGjXz'
        '0lPBMTn5IcvKB0V4sAtBSx38aV0DXt5u4iXe164X0vlT4k320NVFWrU6Tt6fqKuKyAwOjs03ySk72E26O8+tqcX0re3Cu96HkTOQ/GnxZuuY1WVtoxZce0Yx'
        'GBUSbVgYFFNoFytWrPggJ+ol5OMq8eeP70k+cgSPnW0ma/DyEjyzIGWhYjBLHWnYEbykaFCEB7mId2fcO414Md4kuOulkD9xcxsCY0vgtyAtUTEUFbTYcDx4'
        'SbEssoO8iHclaHkV+y6JCBQrXoj8qVtNGPvOXfhHFUK58NYhwXv9klUYnlAvzvxXUGyxKLFBPkgnBLoxelU1Jm2+J5/8bWaM32BE4LI7UC4ugt/CtJMKhcTv'
        '94WWOuyHJ4Mi9eeDYgsHRbrag3hXAmIrEPJGNSasb8b0eJMk8qduM7Hig96ohjK6HMrIfPgtSD+vCPVxo02yCsMTwVH6E+qYfFmEq3mKd0e9rBJj327ECxtb'
        'MW2biZf46S7S//zxffbzA5ZUOsRHl8NPk4dRi9KPkcZTDLcKjNTHq6PzbEFLy0VLVguQ3p94DpUL7JWxshqhaxvw/PtNmLCxFRM333/ACx+1Ytz7zQh9uwGj'
        'V9VCFVMB/+hyFof8MijDs3tGhd1crxjOFRilfz0wMsukji2VTXqgF/Hu8nsRU+4RTrY7rPyoEigj9B2j/nZ9ruJhqMAovVodqcsLjM6XTHggD+kDihcp3y/y'
        'NvwWZuQHRN4KUjxMRWakOsrweWBkZo86tkSw7MAhFq+MKobfQgOjDE+NCx02i62ICl6aFarW6AyBUTkIjC2VVHqASPEDyifjRpMNv0Xp6aMiUgIVj0bhMdVi'
        '3YoAja4+MCoXAR6CCIiVSLpI8X6s+Bwybmr+sCBjJfk/Kx61IrupykjDugCNoVEVmYOA6GJpxYuRT26oIrLhF55R9szClGUP9bjhW6HLM3+t1ugWB4RrDQEa'
        'AwKibiMgplQW6R7FR5XAPzIP/uF60vFZfwhLDR/yO9qhKr9w/ZhAjSFRpdFVkzBUi3OhiiqAKqZUOvGs8Hz4a7JZ6apF2jylJiMuUJM+aqhf/7Cq0Utyn1Vp'
        'DBuVGt3VAI3erNLo4R+ZxYbiH5UPVXQRVFFFUEUXQxVd4kax49/IBlnkbfhrcqCMyIR/uA7KRdq7ygjtpVGLtJtVi1O9f5fKSDkqZIkhSKXRLVKGG7arNIZT'
        'ynBtmkqjr1JG6GuVEXqKlRuhsynDdbWqCF2V/6L0W8pw7XX/CP1JZbguLiBCN18dlvzfzi83UiM1UiM1UiOlGE71H3gfSHI8RPTUAAAAAElFTkSuQmCC'
    ),
    'assets/badges/official/html.png': (
        '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'
    ),
    'assets/badges/official/javascript.png': (
        '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'
    ),
    'assets/badges/official/lists.png': (
        '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'
    ),
    'assets/badges/official/loop.png': (
        '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'
        'QmCC'
    ),
    'assets/badges/official/lua.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAIAAABt+uBvAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAalklEQVR4nO1dC1Bc1fk/+wJCRqMY0STGWFNNjdrY2GjH'
        'UZPJaEdbnY6tNdpW26rjWGPVKrs8FxZIgETeEMIjL8AQYpICAYSQEEAgEHkk4ZWwCYHwygJLCLvLa3fv3f+c8+1eLnv3CRtr+/fMnc3lPs/9ne/9fecEGX5s'
        'NhuyffrH9iNAdtqPANlpPwJkp/0I0H8PQDRpZkcM/z8BojlY3Op7adpAUbReT+n1xgdQFP6HougfFkC0pc+jKEqlUg0NDXV1dd28eRMO6vX6gYGBoaGhiYkJ'
        'vV7PfQ5FUQ6+lEAz+1KaxhvTCGrUD4uCxsfH5XK5RqOBP/v6+hITE1NTUxMTE1taWuCgWq3OysratWtXTExMWVkZw3FKpZK50ZFGURggg8Egl4/u3dv04Yf5'
        'r7yS9ZvfZL777rFdu+pbW4cJdlZJ6dYCRLNGCvb7+/v379+fnJyckpIyNDQEp2ZmZpRKpVarNbuXoqipqSmFQqFUKpkn5OXlJSUlHTlypK2tzS5tAmkMDKj+'
        '9a9vvL23IyTh8SQI+SLky+OJEZIsWRL2/vv5nZ34+RYx+j4oaIo02O/v76+pqRkYGJiZmZnf09RqdU9PT2lp6cmTJ5mDDDRsjICtzp1TPPpoAkI+fH6QQBAi'
        'FIYJBDKBIEwoDBUIZHy+FCGfBx7YUVHRbTAYdDrqewVIqVSWlJTExMR0dnaCrLF2pcXxh4N2pTJFUbm5udXV1WzQ4Za2tuGVK6MQ8hWJMC48XjBCsIXADp8f'
        '4uYWhlDAnXeGnjnTy+2kiwGiSbfgd2xsLDEx8dChQz09Pey3LkSFWbv9/PnzGRkZMTExly5dYphlelq/eXMGQmKRKJzHw4jweCGmzbgPB4XCMIT81qyJVSjM'
        'pZvLAKI5/Z6ZmRkeHnZc1yywURTV0tLS3Y05RavFWi81tQEhX6EwFCEpGyCgHfY+QkECQShCkqCgU4zkcj1ABoPh8uXLBQUFOp2OOUKRZrjFjSJWDbsnarWW'
        'kA8ANAcRDkz4l88PQShwzZrYkZEJtsB2GUB6vf7EiRMRERE1NTXOshIYbDY2BzkS3gjf1tqqWLw4jEgZGRsg9jb3ON5xd5cWFXWypTVy1dD19PSkpaVdv37d'
        'QReBonAntFr8AAe+HKskrZbS6Si7z4YHFhZeQsiPz5+lERssBvuE1iRJSfWESV0BEM3qLMNKdhnKzHKlacONG1NdXWPnz1+vqrpWWNh57FjHsWPtxcXy2tq+'
        '1taha9duqlTauWDZghVOZWaeQ0gsFM4hH2u8BjsiURhCkm3bqlxJQb29vSqViq2SbfQbqA0uuXlzurS0Kyqq+k9/OvyrX6Xcd1+UmxuWAgj5EUNOgpA/QoGL'
        'F4c++GDMxo1p772Xl5R09syZfmZs4ZmWHBd85PDhNiKAzMnHBosBBUVH17qAgmjSrebm5qioKIVCYZutwEuE81qtvry869138x95JH7RIikB4gsCSiBCUj5f'
        'JhDIhEKZQBAiEIDglJJTvuQy8R13yNavT5FIypqbB+GBej2l1ern+lb4j7Nn+xEKYljMNu2AQUSkVcDBgy0LpSCadOe7774LDw+/evWqXXRgSBUKTVra2XXr'
        'diEUAATC4wWLRKEiERi1oWYWikm5yPj8YIEgVCTCwJFP9UPITyiU/vrXB/LyLmo0WjNSgtcNDKjXro1FKEAgkNllMQAIoaDly7e1tw8zKM8HINrUj1OnToF9'
        'bA0dCCkYDIaJCW1ycv3atXEI+RB0MJnw+QAB0L+UdJcrSmHw5zAIuVdGDvry+b7PP783L6+DgYYhK4PBIBaXECsxzMws5OxjgIitKHntta/MnLL5AwTNGjoU'
        'ZZTEFRXdGzbsJp6hn1AYSnCBIXVIs1gac+MRgQA7Uwj5urn5/+53OZcvj4LsYGi2o2Nk+fIIYgQa30gQN2cxIB8eL8TNLaiurtfso5wGSE+abTMHoJmY0IrF'
        'pUJhIEL+xEuU2dUjzu4gFCwSYXpESOLltS09vQG4g6ZpECIHDjQTQgNrSGqGESFDLPhEIhlCX2zbVskdckcBosltOp0uNzdXLpfboB3g3ra24eeeS0fIh7jO'
        'oWZi0sZmkXY4egdv5LPxQT4f8x2PF4SQ77vv/ntkZBIGCToYE1MrFPoTYQTuO+Zu+DX1TYqQWCwu1elo7mc5B1BZWVlCQgLELiwCBE5QdXXv/fdHAU+5lmQI'
        'Z2GLjiAuRSiIqGcZMC8hJfGzz6b39Y0DRsBreXkdq1ZFkxgQNh3A+SL34sDQ0qWRGRkNTCjWrDkEEE3u6+vri4iIGBwctIYO9CY//+Idd2B9KRIZCYctOBaM'
        'Dna7iegN9PKSLV0a7ukZTHSiBMI9IhG2ZdaujW1rG2YsDIMB26IJCXXPPbf3gQd2eHtv8/YOf+CBnc88s2f79srBQZWZNzcfCjKQ4E5XV5c1dKAfBQUXPT2x'
        '5cJWri7Z+PxQHg/bB+vXJ4eGVuTnX6yr621sHDx16mpqauOWLYfJqPgRgRKKkN/q1dEdHRgjnW7W7KZpQ3+/qrn5elPTYE/PGPMdDD/OEyCaEzk1a2B3VlX1'
        '3H47tiZcxVkmUSolcAfce29EZmbzzZsWQpF6Pd3cfP2VV7IJKclIDEzy+ONx16+rGfVP/DhzFQxsaMOOc4KCaCuJBJDKnZ3KVasiEfJ3udwhCsjvySeT5XKs'
        'yEFDabXYjNDrKTOP19+/jMgao9/w4osZk5OzsRcIzsONDgYJHAKoqqrqwoULFh1ReIdGo9u4EQdfiIxwAWcxEIP5v2ZNbE/PGPCLxc8Cdx9g+uKLbxCSEJcl'
        'HCGfrVuPsy1jblOr1UyuaT4AqVSqqKgokD5cgED0+PufQEhMgnKzXsICOYtsWJC5uQUeP44DqTMz5tkxDkwYo8lJ3TPPpBHjC3S5/5EjbRYD8oD1hQsX9u7d'
        'a0162AKINqVZcnJyLKIDrywru7J4MeMWugwdYv5jcfuHPxwyC4PaaNClgoKLxKcJBuH10ENf9vZixW8xSKLVauPj49vb2y1+o32AysvLr127Zs3JGB+fef75'
        'NMJcWPS4SGeBVQmBZH9wtRwECNr0tP7nP082GYdhCIk//hgzmsXEicFgqKysBCJymsVom246CYyfJeiAn+0CnWXmXnt5RQ4N4UyD43kQEDefflrICpiFuLuH'
        '1NX1WfsitVp95coViyrIvgyirftcKtXMmjVxCAUSI8U1fhZjWPL5oQj5r1+fYkO+WgEIf2dKSj1CElCp4NP+8Y+51iiRna1yAiCtVmstCw7kk5xcj5AfEaWY'
        'HVy7EQry37Rpj7M5EehbdvYFki8MNT0q+PbbZVVVPbYxchQguLquri4vL8+a9NFqqaeeSkXIHyI7FiMY81VejLcdMG8KSkv7jlCQMZtK4s1iUPlcUQ1f1NXV'
        'NTY25hBA0LKysioqKiDEwdUURUWd7u5BFo0Xl7AY+TPo7rujRkcnnZJBIEp8fL5ByIexWgmXBa5ataO7e4yLEdzy1VdflZeXOxoPmpiY2LlzZ39/P5eCYEj/'
        '+c8ikIJsR9QGUvMzF3m8gOJiHLd0io70evrJJ3cRU8gYyWUkUXb2eS5ATBA5MzPTTNlbBUij0dTU1HBrMOBZCoVm3bp4iISBOec62pn9k4y/71tvfW3RzLMC'
        'Db7s5MkuPh/HdlkOHQAk2bLlkDWhoVAo4uLiJiYm2Bc4HVGkCPa1tb1Eec0ROk5GTu0rexCunp7SsrIrTLDJrreo19MvvriPBBJnyzmIWsRctmLFzvHxGYs8'
        'S1HUtWvXzMqU5hFypQ0GQ3z8GfAtLEbCSdLGGJZfmPWII34I+a5blzg0hAdWp5uT4TEbOSCfkJBygo45t4JBxOcHVlbiAgdHMrq2ALLm7VLkuX/5y2G29cyK'
        'hAIoASSsFTBv2mEeaxp53+efTzdFtnAOGsoxyWb07KF7O3Z8y+MFMvqUFa6DsAnOhcTG1jjOs8ha7Dk7O3tkZMTiPXo9/Ytf4PSWKT/BjBLO3ohEssceS96w'
        'Yffq1fEQ3DSFx+cpiSCBQWJgMXl5HdPTFj6Momi5fPTtt78GswN4k/tMwPq99/KsWUMajYYpDLQF0I0bN+Lj47lBACAppXLirruiTF8++3ryGUH33Rd16RIu'
        '+SspuUy8ISd0FpdbGeiJYR3A5/tt3rwvIaHu1KmrHR0jcvmNs2f7c3JaP/igwNs7HCExS+7Mus2sHmKANm7cx06isT+8vb09PT0dtBgcMQcIzl27di0uLs6a'
        'CmttHSJ5EsYIMgpCMj5BK1dGAkAnTlyBxCbLrnGadlhGI5Md9kNI4ukpXb58+8qVkV5eoXy+PylBxIFHEzdZruggLOb/6KOJkI/lRkqhRoWdlbBMQUNDQyUl'
        'JdzqZBBA337bw+cHMZ1g+gHu5cqVkRcvYoBKS2cBsiuJWMLCmjAyiiSSrYZ0AM5MEOLCsXqoA7I9EqDIVq+OHhgwhmLNPryvr49hHcsA2W56wrfFxZ08nj+P'
        'Z/7lDECWKMjGhtO+kJ/iMh2krgSCMNOR2YS1UIgLVuBeqHow5Vot0I5ZDyF6yzU+JyYmWltbp6en7ftiVsLPlMFgOHasncfzZ48Yq4rNKRYDSSGFkheyYy44'
        'iEL0JaUwTKoe8xq4DiTh40tu94fkD6nowM6zJVOeqVCIaG8fcdA6nw8FHTvWQQDCsnNu/NgqQBZT7PCEe+/d8fLL2Zs3Z9522zaTXGM4JWjt2uRXX81Zvz6N'
        'wIdzx+RGjOmDD8a9/35eXFxddvb57OzzsbG1f/3rsfvv38EYQdyXwhuXL4/o6LAKkJ3UM5weHBwsKyvjEhEwbUmJnNgaZjreaKo6zmLgYf/5z4eJZpx6+uld'
        'TDKWnA1FSHzoEK7WKSm5vGgRHgwIPIlEgV98UQIpZuZzYOf6dc2bbx4myl4GQoC9QaXmqlVRV69acFnBLZ+YmLDlrAIocrk8Pj4eilW58J050ysQGNnBYRlk'
        'gcWEwhDGOVIoNL/8ZRI7a0SCgZL9+8+RGPMlDw+cZQY9/fHHhdAfpXLy0KGWL7+siY+vq6zsBl9kfHx6/foU06vn2IpEiwU89FAMRCm5QnpwcDArKwuiYLa0'
        '2MDAQEJCAltWsc92dird3BgBNCsyrAHELVOGHkOaeMsWHOhTKic5AGEKyszEABUXyz08pHw+1lweHqFyOX5+Z6fy8cfjyfQLPz4fS7G//e3fkAULDj5NMohm'
        'QgDw9V+3btf0NDtZNvtp3d3dDqn58fHxzMxMtVrNOYt/VarpZct2gjh0BCCbLGYZIChJQEgC0YmiIrmHB5T5BD7+ePL0NKaUf/yjAKHPhcIwUryA3yIUBjY1'
        'DZBI+XcI+bGq1owbeHYvv5xtLeLR1NSUlpbGPmIrHkRZCXZSFP3MM+nA52wx5BSLEack1C5AWVlsCsLPX7Jk+wsvZL70Utbdd0dBQSOkQMiA+cF8i5QUnEpg'
        '9KxJIcIT/D76qIjrajCF8FDn7VC4g7burH74YT5kLx0EyKIWs8diANB5BiCCMjbWTbpfTGr6fPn8gCVLZMuXR/797/+emtKZKMgsE8X4vX7p6Y2O55HmEe6g'
        'DAbDnj1NTMTX5SwGZ0EGsVnMVC6Fc4GLFgVv2pTx0UeFcXF1R4921NT0Dg6qGR89PR3P0uCyGMjp5marFTxOADQ8PNzY2Mh9EFDQ+fPXPT2x9GUHpW4di33z'
        'jVHNg1u/YcPuysqeyclZT4imaYVCnZNzASoVgYI4pixG9pFHEqambAXe7JfgMV5JdHQ0KDKutB8fn9m4ESdUGbPFBotxbX+LLLZhA1eLSb76CiiokxHSP/tZ'
        '/MAADgxNTury8y9u3Vq4efPehx6K9/AI5/N9v/0WB8N274Z05mzfTCFX8datBdYkdH9/P2RxHKIgvV6fnJxscSIckHFISAWp9JpNGVo3FPHosdAx4sUGaHR0'
        '8qmnjIYiy84OKCm5zLAYQJacjOdSqFTT77xzGCEfMsVSYsrEh1RX48zX7t1GGcQxowNKS69YA6iiouLAgQOOBu0NBsPRo0crK3Hhp5lbD2Lo7Nl+L685+Xgz'
        'Cioru4JQkLt7mEgEG64ZB18cdqDMCQAaGZncsMGYTSefiv31Zcu2Q2CguFi+aJGUeBjS6mqsp/LyLopEfkKhTCQKA0+Vz5cJhQGNjf2MmjdZIQw9+j/5ZNLw'
        '8JyYPBug9PT0M2fOOFEGrNFoJiexOc9tMAK//W02JOYtyqDCwk6EPhUK8dxZonGYX9gRgyX95psYIJo2vP56NkKfe3iEC4Uyd/dQhD776COc52PJIIxRfT2G'
        '4Ouv2wUCf3d3rOZJoX4IQv966aX9MzOQNWzg83GRJJPyBf6Sycq5wVZTHlSbn58/OopFGLvNc64GRQA6fvwSsWLN40EAUGfniL//yeDg01LpnC0o6LRMViGV'
        'nlq+PBoh8Qsv7L15E0u62treZcsiSegLF59u2XJQqZyanMSRreLiyx4eUsgCHTyIpdLY2PRrr2WbLhaLRNK33spVKo3DmZV1DqHPmJAeuGArVmyHjlkM1zuX'
        'enak0bgUjt60aQ8jDgGgVat2WnMFTTcaTz31VBpCfiKR9ORJXJ0FU9tTUxuio6tB9DQ1DcTG4rk3J05cWbQIhLT/5s174XalcjI3t+3LL2t27z7b2Ig1d0fH'
        'cEMDtqQVCnVcXM0TT6RAOSkJ14o/+6zYdojDueIF08RGdUVFBddrZb6/uLiTCA6QRFhGLFsWcfJk15Uro+3tw21tFrbW1uH29uFz564//HACiekErl4dW1PT'
        'y65FJZaEYs2aL199NXN4eCIjo8ndHbx5jNEHH+SNjEzCZfBLUXRhYeftt297441cphZNIilDyMfNDUfKvb139PZCnNDCx+p0Oq7j6RBAer0+JiYGVkPgCDbj'
        'aLzzztemOSNYGPH5wV5e25Yujbjrru1eXtvvums7s8P8uXQp3hcIGMkV4OkZsmVLbkREdUrKd5GR1W+++fWSJVisLlq0zds7YsmSbYSLsSoEd+GnP43+5JPi'
        '2NjapKSzfn4nn302TSAIQCjQzS3k7bePpKc3xMTUrl2Lpb67Ow7mx8efsUHUJ06cqKqqmmeFWX19/a5duyxeAAC1txvnjJjCVJiOmICxpX3mF1xt7KYTT50t'
        'wiVEJIMBEWRK+xmDimBMEz8DbvEB3510QMryQvxhDs+mTWkwZ9EiE2k0mpiYGGtFmPZlkFarzc3NHR7GRdnW1n7Yv78Z1CoTG2dPieDsGE/NjS7iAnAylQ5P'
        'LSFBeEb2G3PQc/MTocz1bm6hYD2ZIm14DQFw8REKWro0FAQT1/kCOAoKCrKzwb+fV4WZ3VIzOEbcV7FQiCdnmaVbmelgTAjJ2kSVuYkNW/kJ9sWmZ855jmne'
        'lW9GRoPtoqlz584NDGAEFzoVwVoD3MbHpzdu3IOQ2M0t3GR92M+FWcr/zObaHM+dcXNExBP2+fjjIhtZZkcm9DsB0MjIiDVRD8Kop+cmqYnxI5zvUMbZefhs'
        '7DM0JSUmos8bb+RMTensVtTbrrl3CCCKIJ2Xl3f06FFrwIOCuHRJ+dhjsYARm9ds0wKX1xzPwZrdyOfDQhzi117Lhlkd1jSXTqc7ffo0RE1dM1dDpVLt2LGj'
        'tbXVGkbA53L56Lp1SQhJ3NyMip87ZXR+pUN27zXNHRS/8UauWm0VHeh8SUlJamqq3a92bkLdBVK1z16aw6wBtw8Oql966QCZbmhcGcKuTFkwi0mFwjDizUo+'
        '++wbMBQtCmZAp6WlZfv27eB52eZAZxOHepVKxS5+sNQDfGZ6Wu/jU8rMhTQlGMwS7XZ4zYENQ0OMBuym3XmnLCOjiZm2aiNj3NTUBKxgN67oHEC0eXTRalQf'
        'rszP7/jJT6KJFYcDDixzZkEsZlLqOAbm5hYqEAQiJH7uuQyIpVoTuvNbhnAeNYoUFBCdO3fOhvxn5h0rlZOffFJ8220yE0w44cn6SIeWRWBdyYQHwTgMQki8'
        'YkVUbOwZyBraCMWTLs36XAuNSdt4jYEkziIjIyGcZuNNzLTapqbBt98+6umJA0Ck+hOmKs8poDFlb4K5G6OhTKWPUNTgc889kRLJCZhKxgQJbLScnJza2lrH'
        '0VnQ0hQKhSIqKsosi2TpYiPR0TSG6dNPi+69dwcpxvCFOKlQCDFGTBFQwmKas409CdZZqNkw3vjIIwlRUVXd3cZCHrs5HJqmDx48mJKSwk4rO9IWtLhJf39/'
        'c3Mzw9423sqeWXvjxmROzoXXXz/88MNxixcHkw/G6S2o+yQBEHBuA03FoMYFUO68M+yJJ5I/+KCgtPQypJhBHtsO8UCvGhoa9uzZw81B2G0LCpgZHDtoOjW7'
        'Qg604WHNqVNXk5LObt1a9MorWU8/nbJmTeyKFVH33BPl7R11331Ra9fGPfts6u9/f/Dzz0v37Gmuq+sD6wbW2GGWoHCkhzMzM9yCOUfaQhdYokknKIo6ffq0'
        'xXkLlu6ysDqoVkuNjk7196u6usYuXx6Vy0evXh0bGFDfvDk9twbDzsqiZh0bHh5m4+IU7bh4DbPy8vLw8PDGxkbHB4qijPOX7QpXuMyR9blYD6eKiooSEhIg'
        '7zDvtQldAxBtmk4UHR3NXjPHwW4By3CXenNgkck5fWAuValUycnJGRkZ7DVO59dcvEygWq3mZopu9TKB3JUIx8fHm5qaLIbSnW2uXImTmms3lpeXV1ZWuqSX'
        'thsjbi5cuGCWJV8I7dzCpUqhXbp0KTU1NS4urqkJ+0eu6jr7XqZu7vjx49HR0fn5+S55xfe32C1Flg9lqkTA2LcU2MYWtxkBgmNpeyFPuL66ujo3N3dwcNAl'
        'iHx/ANGcoVar1fv27cvOzq6vr79x48Y8xKdGo+nu7q6srDx48CDML+W+xbXtli+4TbM6TVFUT09PVVVVRkZGXV0d40A2NTU1NDTI5XL2TJvR0dHu7u6Ojo6W'
        'lhatVgvPaWxsjI+PP3LkSH19vVn891ag8x9bsp3C8wKN5pJWqy0sLNy3b19iYmJREY6xQyspKYmNjU1NTc3NzWU04+TkJEyZ/N4a+o9AQ1uORuLG/lNLjEhr'
        'DzH8b/+/GvS8OMJVuum/8j8eMfwg2/8BshLN6sa5smMAAAAASUVORK5CYII='
    ),
    'assets/badges/official/mysql.png': (
        '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'
    ),
    'assets/badges/official/onedrive.png': (
        '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'
    ),
    'assets/badges/official/onenote.png': (
        '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'
        '9C8HAAAAAElFTkSuQmCC'
    ),
    'assets/badges/official/oracle.png': (
        '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'
        'i0A+AAAAAElFTkSuQmCC'
    ),
    'assets/badges/official/outlook.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAgAElEQVR4nO2dB1SUV9uuPef854tdkTYzFBV7b6gISJOm'
        'gDVq1NhLbDEaS6x0NL333osyg4KAvSF9sMeKHQuIKIrS5n2vs/Y7M4Bo8uU//0+S7/t51rrXoIG15Ln2fT9775chDRrUV33VV33VV33VV33VV33VV33VV33V'
        'V33VV339DSvmANZv7mHBe7v5+aNdnPx0Bze/2s7N77Zx8sdkfv4lmQUbk7D+q/+d/3YVnYZd9H6+fHkvFa/vhbf3wPu74eNd8PlO+HoHfL8dft4GsYlUxG3l'
        'y40baftX/7v/5SsM/vfqVBaFplASeQDW74dX98Gbe+HdPfDhLvh0J3y5A77dDj9ug43JoE2CjXHSg3fer/hm40b+8Vd/H/+StSSN9stS2bsyFdYehPADEL0f'
        'Xt4HwgVv7YH3dsNHu+CznfDVDvhuO/y0DTYlQ1wSfPeTRPiG8ocfvm+Y/Fd/P/8yFbaX/5iXzkuL0ilbkgbLU2HVQViXAhEHIGY/vLIP3tgL7+yBD3bDJ7vg'
        'i53wzQ74YRv8kgyxSbA5ESJfL+OlyHLefteQ9s47NP+rv7+/dU3PoNeMLPTPZcKCDHghHZamwUupsOYghKVA1AHYsB9e22d0wbu7fzuKdEnw7ucGlkWW81JU'
        'OVEvV5R98qFh1l/9ff7tamwajZ7J4dXJeiqnZ8PsLJiXCc9nwJJ0WJYKKw/C2pTHo+h3B3IyfPCNgSWR5SyPKuel6ErWRFfy9tvS/qVLafJXf99/ixp5BPdR'
        'hzk17hBMzIEp2TAjC+ZkwvwMWJQOL6bBilRYfRBCU6D2QH4kinbAN9uro+iNLypZFFnGkigBoYJVMZWsiTEQFmO4FPUq/g3+p1bgWZoHHuWdoMNIIw/D04fg'
        'mRx4Vg/TsmFWFszNhIUZsPhJUbQfNuyD1/7JQF77djkLIktZFF3Oi9EVLI8WEAysXS+xLsYgR6zn85dfpkWD/0nl8StDvY9x2f8YDDsKw4/A6MMw9hBMyIHJ'
        'engkitLhjwzk2lH0yWaJOZGlzI0qZUFUKS8ICDEVrIipZKUJQth6mYgN5EVHM6LBv3u5H8PC9TifuP0KnidgyHEIOAZBR2HEERhzGMbnwCQ9TM2GmVlQeyD/'
        'XhTVHMifJsPcVx/cmxH1kNlRpcyNLmVBTBkvxJSzJKaC5esNrFpvgrBBQJCJWl/5y7zpN50a/DvWgMOMHXhEKhh0DFxPwOAT4H0c/I7B0KMQcgRGmVzwe1G0'
        'LA2Us8HvDOTXt0p3JseUXJkUWcKUyAfMiH7I7GgBoYwF68tYtL6cJesrWLa+gpXrDaxZLxG6QZwZZFatKSmaNO7sew3+XaqfHnX/bEk7IEdm4GGZQUfB9TgI'
        'F3icAJ/jUDuKqgayHmZkP3kg/1YULfri4aHR4cUlYyPuMz7iPpOiHjAl6iHTox4wO6aUuTFlLIgp5/n1FQqEpesreekRN0jMnHGVYO+cwqkTc90a/MsW/K/e'
        'aYYpfTOk285ZMv31MgMPybgckTG7wP1X8DoBvsch8BgEH4GaA/n3oqj22WBlfGVecNSds0HhdxgRUczoiPs8HXmfZyJLmBT1kCnRD5ge/ZCZ0Q95LqaM+QJC'
        'TDmLTRCWr69U3LBagIiqZIhrOj7OKYwffmpHmCf/0eBfqXqk4NRrv7Srz0GJvmkSzhky/bNkBtSC4PZPouiJA9l0NjAP5FX7pMqxH9zP9gm9VeEXVkRgeBFB'
        'kXcZHlnMqMj7jI0qYXzUAyZGlSgQpikQSpkTXcq8mDIWxpSzyOSGZesrWbG+UnHDyOATePRLwafPQUZ45dyb8cz5oAZ/+wrjf/fYY5jTY6+hpNd+iT4pEn1T'
        'JfqlSzhnyvTPlhFR5FIrijx/ayAfMrrgt84G02Mf5g4Kz7/mHlqIZ/htfMKL8IsoIjDiLkGRxQyPKmZk1D3GKBBKmBj9gGcFhJiHzIgurYoksxteWF/Bi+vF'
        'gK5kzNgzeDgfxKvvQYb0SSWwbyYj3Q6/6+m59+/phk6J5T267TBkdt9loMceA732SfQ+IGF2Qb8MGecnuMBVuMAcRccg8OjjUVR7IM85ID30eP12Tr81N+QB'
        '6woYFHoLAcEjvBCfiCJ8I+8QEFmsQAiOvMfI6HuMib7H2OgSJkSXMCn6AVOiHzI95iEzY0qZE1OmuEHMBjGgRSwFBR/Ho/9BvJxT8embhm/fNPx7pRPYI/1I'
        'UI+cfg3+LtV144l/dNIZ1nTeWlnedZuB7jsN9NhtoOdeCeGC3ikSfZ7gAjGQXf6TA1lEUeBP9w93XXOjqMfam/Rad5O+oQUMCL2FS1ghbmGFeETcxjvyDr6R'
        'd/GPusvQqGJCou4xPPoeo6Pv83T0fcZHV7thqnBDTCmzYkpNs6GM+ZGlDB6cifuAVDz6p+LTL40hfdPx651BYK8MAntmVQ7rlf32WPu0Rn9p89v/8NCzww+l'
        'ZzpuKqPL5kq6JhnotsOA4gIThN6PRJFcBWFgrShyN7ngsSg6ZDwbjNpbUdA5Mu9U+zV5dFpzna5rr9N93Q16hRbQJ+wW/cNu4RJeiGt4IYNNEHyijBACoooJ'
        'ihKRZHbDfcZFl/BMDTdMM7lBxNLomZcZNCgVd5dUPAak4+mcjne/dPz6ZuDfJ5PA3tkE9slmaO+cXP/e2X5/fufHbvw/Tp+UvN/uixKpw7cP6fhTKZ1jy+kS'
        'X0nX5GoIPfdIT4yiJw1k198YyCNzkPt+XpRqv+rKg9arr9J2TR7t116n47rrdFl3g+6hN+kZVkCf8AKcw28xMKIQ14jbuEUU4RlZhE9kEb4KhLsMiyomOKqY'
        'EdH3GFXDDRNquGHskvx7A90PVri4puI2KB33AWl4DkjH2zmDIc6Z+PbLwq9fNgFCfXPw76uXhvbWf+zZ4E+cDW3eKdK2ff8u7T4tocPXD+n4fSmdfimjc1wF'
        'XRIq6bb9yVH0pIE88DcGsogi9x0PL6pXXz6nWnkZ9aor2K26gsOaPNqsu45T6HU6hN6gc9hNuoXl0zMsn94RBfSLuMWAiNu4RBThFnGbwRFFeEXeYUjkHfyi'
        '7hIYdVdxQ4jJDSKWxGx4JqoE3xm5+r6DD5b1d09loFsag1zTcHNJZ/DADAWCT/9MhvTPxre/Hj9nPf7OOfg5CwhCmZv/lOY7vlY0ufUbhbR9twinj+7R7rMS'
        '2n/zkA4/ltF5UxmdRRQl1oii/+RAdhfz4JChrP3bNw7aLLtYqVpxCQFAteoyqtVX0Ky5iv3aPFoLCGHXaR92k07h+XQJv0mP8AJ6hRfQJ/IW/SNvMzCykEGR'
        't3GPNLrBO+oOvlF3qmZDsCmWhq28daW3f+axXl6p9PFIxdkjjQGD03BxTcd1UDqDB2XgMTAbz4E5+Ljo8emfw5ABhxgiXvvrjeqXjX/v7Cl1DsDh5ZsZrV+5'
        'Res3C2nz3l2cPr5P+y9K6PBdKR1/LqeTtpzOIooSKxUIj7igBoTfOhv02HLvuM2LuXk2L57HdtkFVMsvoXrpshHC6iuo1uahXpuH/bprOK67RtvwG7QPv0nH'
        '8Jt0jsinW0Q+PSMK6B1ZQN/IAvpHFuISeRvXyNsMjizCK6oInyijGwIiblf2m3Qio6tvSmkPn4P08k6lj1ca/TzTcB6cxkD3DFzdMnBzzcLdNRuPQXo8XXLw'
        'cjmEl4se7wE5RvXPxts5Gy/njMw6B2AfnVfsuOEmjq8V0uat27R9/w7tPr1P+68emCCU0ck8DxIrH4uiJw3kATkyzukVxfbhednWi3JlmxcuYLvkAqqlF40A'
        'Vlw2Qlh9FfWaq6jX5SnShF7DIfQ6rUOv4xRxkw4R+XSKyKdLRAHdIwoUEMIN/SILGWByg1vkbTwiixi04urpjkFpZzr5pdDF7yDdfFPpMSSN3t5p9PVKw9kj'
        'gwEeGQwcnMkg92xc3bJxd8vBwzUHj0E5CggPFz2ewhkDsvAYkMngfmnFdQ6gTUye7BB9HccN+bR+7RZt3y6i7YfFyjwQEKrmgVZAqFB2Rv9sIHf4vDDLasHZ'
        'O9YLzmH9fC62L1xAZQaw7DKq5UYA6peuol4lIBgBqEOvoQm7jn3YdRzDrtMm7AbtFBBGN3SNyKdHRAG9Im7RV4mlQvqH3nzYaXxORtuhKYZ2gSl0DEilS0Aq'
        'Xf1S6eGbRk+fdHp7Z9DPKwNnzywGeGbjMjibQR45uLrn4Oaew2DXQwx2zWHwID2DXbJxH5iFm5gT7hlynQPo+UWhbB9+BYfoGzi+XEDrN24r80BAaP/ZfeNQ'
        '/sEEQVdO1/gKuidX0mPn42eDHkll+baLzp+0mnsG6/lnsV6Yi/XC89guOo/tYuGCS6iWXlJcoH7pCuqVV5RhrFackIdm3TU0oXmow8wgbiggnMKNIDqaQHQz'
        'uaHzojN6h5D9N1qHpNA2KIV2w1LpEJhKp8BUugak0c03nR6+6fTyyaSvkHc2zt7ZDPDU4+KRwyCPQwxy1+PqJmBk4+qqx21QFq4DM3EZmEbImGPUOYDg9HLZ'
        'ft0l7CPzcIi5geMr+bR5sxCnd+/g9FEx7T8XEB7Q8YeHdP6ljK66crolmCAIJ+yT6LW3UnJ8+VqW5YyTD61mn8b6uTNYzzuH9YJcbBUAFxQX2C65iO3SS6iX'
        'X0a9/IoJgskFq6+iEU4QMyH0Gurw64rswq8pjmgdfgOniBu0FyDWXst3HJuS6RC8D4fhB3AYnkKb4IM4BaXSflgqHYem0ykgjS5+6XT3y6SXfxa9h2TRd4ie'
        'fj56nL309PfMwcVTz8DBObgM1uPinsUgtyxcBmUycFA6A11SWRJ9o+4BzL0IHd+8jkPoZewjryoQWr9a8AiEDp/fp+PXD+j0w0O6bCyji3CCgJBUSafvHuRa'
        'zTx13mr6SaxmncZ69pkqALbzTQCev4DtoovYLr6I6kXhgsuoll1BvcLkgpV5aFblVTlBQFCJSArLQxV+TZFd+HUcwq7JDrOPpNsF7bxjH7QH+5B9OITsVwC0'
        'DkmlbXAq7YLT6DAsjU6B6XQJzKJrQCbd/bPp6a+nj5+ePgqEHJyHCBA59PfU039wNgMHZzHALZP+rmn0H5SG51A9H8WV1z2AhZdg2lmZDq9fxT70Eg4mJxgh'
        '3MbpvTu0+9gE4RvjTOj8cymdfyktVS+9dNhq8gnJeupJrGacwXrmGaxnncF6zlls557Ddl4utgvOY7vQCEC1+BIqJYYuG6No2RVUy6+gWXHV5AQBIQ9VDQiq'
        '0DxUYdewXX7usl3IruP2w7ZjP2wX9sG7sRcOCNmPY8hBHEek0iYkjbYhabQLzqTDsEw6B2XRJVBP94AcegTo6emXQy+/HPr45hjd4K2nn6demQ39BmfSzz2d'
        'vm6puPpnsv77Er5KNPw5AIRmngfnjXcVCMIJjjE3aGN2gtgZfXSX9p/fo+PXJbSOyT9jNeFEodXEk9g8exrrqaexnn4Gm+lnsZ51DlsFQK4RwPzzVS5QVUG4'
        'jOpFAcEURSuq40glIJgiSYBQrblaoRmfkqEJSCq3G7oN+6HbsQ/aheKA4L04hOzDcbgRgOOoDNqEZOAUkkn7kGw6BevpPExPl6F6ugfm0D3gED39sunpq6f3'
        'ED29vbPp65VFH89M+nik0ds9leAZp3nl54d8urXyzwUw7xLMOg8jjkq0f/OGMhOMEPJp89YtnN4rou1bt0psp546az3uBNbPnMBaAXAS6ymnsZ12BpsZQudQ'
        'zc7F9rlcVAqEC9guuIBqoQnACyYXLLmMeukVRcad0RVUVSCuoFp1FdXcYyfs/eMv2QVuxS4wEQHAbpgZwG4cgvfgEHIAB9H8kWk4jMyk9chsnEZk0y4kmw4h'
        'ejoqEHLoGphDt0A9Pfz19PDT03NIFr18sujplUlPr3ScA7OZ+Xohb2+u5IP4ShOASvlPBzAlF8adhUHJDxC7I8f11xUImkXnz1k+fbjE+umjWI87hvX441hP'
        'OIn1pFPYTj6N7ZSz2Ew7i1oAmCWUi2rOeVRzL6BacAH1gkuonr+I6vlLqBZdQr34EmrFCVdQCQgmAAqEFy8Uq0ZsS9f4bpY0/luwCxAAkrAbmozdsJ0KANF8'
        'R5H/pvhxGJFO65FZOI7Kps1IPU4jcmgXolcgdBpmdELXQD1dA7Lo5pdFd98sug/JoLt3Gr7PX2D5z+XExFXyRryBDxL+SgDnYMI5GHtG3OVLYkAXW43SX7Me'
        'qcd61CGsRh/GeswxbMYdx/qZ49hO/BWbZ09hO+UMqqlnjACm56KamYtq9gXUz51HLSDMFxAuo154EbUAsOgy6sWXUQs3KHFkdILtVH2OxjeuQOOrw95/C5oA'
        '8+pPpir/g/bgqMRPCg4jDuIwPN24+kdl4jg6i9ajckwQ9LQP1tMhWE/HYXo6BWbTJSCTLv6ZdPHNoM/Thxn30T1e0BlYGWcgYnMlr26p5J34vwOAszDqDIT8'
        'KtP361vYjMnGSkAYmYPN6CNYjz2Gzfjj2Iz/FduJJ1FNOo1q8hnUU8+hmnYW1YxcNLPOo559HvVzF9E8dxH13PNo5l9Co4AwOWHRFVQvXEGz4Ey+emj8EY2f'
        'FjvfOGPz/RPQDBUrPwn7YTuwDzZHzz4cgo27H4eQVBxHpOEwIgPHkZk4jhIu0NNmVDZth+tpNzybdsHZdBiWTcfATDoGZNJpaAaeq64y+ZdKZsUaWKCtZHmc'
        'gbAtBjbEG3groZKP/wwA7T+vHOMWV0mf7yvo9mUZnT8rpePHJbT/8D7t3ivG6e27tH2riLZvFNLm9Vu0fSUfpw03cdpwg3Yx12gfk0fHqKt0irpC16jLdI+6'
        'RK/oS/SNuUifyAv0WJVLmwXnUM86j2bOBTTPXUAz9wKaeZeUSFK08KKsGZui1wzZ9EDjp0PjvxkRO5qAROPKDxSxI1b+TuyHmXLftPrtg1NwHJ6Kw3CR/xk4'
        'miGIKBqZTevh2bQJycIpOIt2wzJpH5hBj+knCPqihGdiJZ6NNTBda2Cu1sCLcQbWbK4kJr6SNxIq+XBrJV9sragbAF3D+EeXb6WEHt9JdPm6go5flNHus1La'
        'flRK6w9KcHj3HvZv3UXzxh00r97G7pVbaDbko4m5iV3Udewir+EQcRXHsCs4hl2mbegl2oVepEPoeTqHXaBb2Hl6hufSNyKXAVHn6bb8LJqZudjNvoBGxNIc'
        'ofNophy7pPHXXdQM0SIix85vM3Zi1QsJACLzzYN32G7T6hfN34998H7sQwQAEUNpOAgQI9KNAEZk4jBCvGbRengmbYIzcBqVjcsr+QTHGhillXg61sAErcSU'
        'WInZWgMvbDawaouByHgDr2418F6igc/qCkDHb6T4Lt8Z6PB1JW2/qKD1p2XYf1iK5r0HqN+5j+2bxdi8dgfrl4uwWl+IdXQ+VpH5WIdfxybsGjbr8rBdIy7T'
        'LqFedRH7VedxWHme1qvO0XbVOTqsPkvn1WfptvYMPdedoV/YWbouOY2diCUxG2acLVcH7zym9tlUqfYVzY9DI5rvZ4od/61oxMpXAOzAfugO7EzZLwDYKwAO'
        'KACUxguFCAjpihyHZyiv9sMzcAxJp9Ois7h/X4avViJQKxGilRgdKzFWa2BirIEZWgML4wws32IgLN7AhgQDbydW8kldRFDrLxnd6VsDTl9V4vh5BXaflKP6'
        'sBSb9x5g9XYJlm/eo9Wrd7F4uQiL9YW0jCrAIvwmLUOv03JtHharr2Kx6hKWL13EasUFrFfkYrPsHOqlZ9EsO4P9stO0WXaatstP0XHFKbqsPEX3Vafos/YU'
        'bWafRv101kW1jy5f7b0J9RAt6iE6NL6b0fhuQeMnVr5x9WtMq1/s++1MAOyECwSAoL0mB+zHLjjFCEIoOBX74DTsQ8RrKq0n5dDjvTu4aGUGayW8tRJ+Wolh'
        'WonhWokxWonxWompOol5cQaWbjGwLsFATEIlbyZW8lFSHTig7eeGvW2+qMT+0wpUH5dj80EZlu8+xOKtElq8fo8WrxTTfEMRzWIKaRZ+i6Zh+TRbe4Nmq/No'
        'tuoKzVdcosWyi7Rcep6WL+ZisfgslotPY/3CKWxeOIXqhZNoXvgVh8UnaLPkBO1fPEGnpSfotuJXOs/TP1B5/yKrvDeh8ok1NT/OCMAvvnr1i/gJSMYucJux'
        '+UN3YjdUABDag13QPiOEoH3YBe3HPuiAMg/sgg5gF3wAu5AUnFZfovvGSvroJAboZAbpZDy0Ej5aCf9YiSCtxEitgTGxBp7VGZiz2cDiLQZWJxiI2mrg9cRK'
        'PqgLAI6fVtzWfFKBzYflWL1fisU7D2nx1gOavXafpi8X02T9HRpHF9EoopDGYTdpvPYGjVdeo/GKKzRefpkmSy/RdMl5mi06R/NFZ2n5/ClaLjyFxYKTWM4/'
        'gdW849jOP4Z6wTHsFx6j9fPHcFp0lI5LjtHl+cMYm29a/T46BYLKdwsqv3hF6oAE1AFJaBQJCAKAyQVDdysu0Awzv+7FbtheNEH70Azbh92w/dhPyaGNuMWN'
        'gy46mR46mb5aiQFaGVedjKdOVqIoQCsRrJWUeTBBJzFzs4FFWwysTDAQkWjg1SQD79UFAPVHpZLNh2VYvldKi7cf0OzNEpq8dp9GLxfTKOYuDaNu0yi8kEbr'
        'Cmi4+jqNVl6jdeQ1pv1QSHjiHV7feYfFvxQwaMNFms4/TbO5v9J8zglazjmOxZyjtJpzFKvZR7CZcxj1c4exm3sYxwWHcVp4mI7PH8HWe6MJQiwqUwSpfDeb'
        'IGxB7WdygX+SInVgMurAbWgCt6MJ2IF66A7UgTvRBO5GPXQXGqHAXWhC9qMKv4RaK+Ogk3HSyXSMk+mqk+mpk+mnkxiolXDTSnhpJQXC0FhjFI3TSUzfIrFg'
        'i4HlCQZCEw28nGTg7eQ6AGDzfimt3jWt+jdKaPzKPRpuKKZhzF2eiiyiYfgtnlqbz1OrbzBr0x1u3DPwW/WgXOL9nYVYPXec5jOO0HLGYVrOOESrGYewmqHH'
        'eqYe9Sw99nNycJybg9P8HFReAkAstt6bsB0Si61PHLZDhMwQEkzaisovCVVAEioFxjbUAWZtRx2wQ4EiXm3nHqHld6W0igObOFDHgaNOpl0cdNTJdNPJ9NbJ'
        'OOtk4zzQyfjoZPy1shJFY3QSUzZLzIuXWJpgYG2igZgkA28m18EQtnzrAS3eLKHpa/eV5jdaX0zDqDs8FXGbp8IK+ceafFqG5nPseiV/tG7fN9Br+a+0mKKn'
        '5RQ9FpOzaDU5C6spmdhMy0Q9Iwu7mVm0npWNrddGowQEr03Yemux9dGh8olDJSAM2YLKNx6VbwIqXwFBKBGVv0niY79kVP7J2I7cg9Wr12kRR5UEBNs40Oig'
        'dZxMe51MJ51Md62szIP+WglXrYSnzuiCQJ3EKJ3Es+LNH/ESixMMrE40EJVs4I26ANDy9Xs0fe0ejTfcVVZ9w6gi/hFRxD9Cb/GPNQU0WXuTa8W/vep/q0or'
        'JDouPELLiZm0nJiBxaQMrCamY/VsOjaT01FPTcd+egY2Hj9j47kRa8+N2HgJbcJGwPAxglCkOGJLDcVj65uA7ZAEbH23KrJefJyWP1c+0nyzLE0Q7HXQRifT'
        'IU5W5oEximQlitx11bui4TqJCZslZsVLLNpq4KUkA5HJBl6rCwDNX7lLk/Wi+UVK5DwVdpt/rBXNF7Fzk7255Y81V5Jh/9mHhMcXskZXQNKx+1Qa5Mc+71JB'
        'GS0nZGAxPg2Lcam0Gp+K5YRUrCccRDUpFc3kNKwH/4iVx09YefyMtZDnL1h7bcLac5MJSCw23rpa2oyNdxw2PnHYjN+HxSd3aB4r01wr00IHLZRXuQpASx1Y'
        'xcmodKZ5ECc/EkX9lV2RpOyKhmglgnQS47ZITE+QWLDVwIokibBkA69sqwMATWPu0DjqNg3DC3kq1Bg5T63O56lVN+n/7q3HmvqwQqZPzFWaLDxHk/lnaDr3'
        'FE2fO4nTi6e58+Bxp8x89xwW49KwePogrcbsx/LpA1iNPYDtMwdQTUyh97snsPL+iVbuP2A5+EcsB/+E1WAzkF+MQEwOsfSMxUrRJqx847Bcc4YWGw3G5m+S'
        'ja8mEGYpQOLAwjQPNHHQWocyD5QoErsinazsipSBrJOVGHp6i8SUeAPzEyWWJhpYl2xgQ10AaBJZSMOwWzQMzeepNTeVxj+18gZPvXSdlAuPr/6Ad6/R+Plc'
        'miw4S5N5p5XmN519gmYzj+Gy9gy1fXA67yEWY1NpNSaFVqP2YzlyH1aj92H99D5U4/YRkAteafdoO2cnrdy+o5Xb90a5/2CE4v4jlu4/0Wrwj7Qa/LNR0w7S'
        '4sv7NN8oVWtTrY9jhUwgBASdjKXOCMFORFEcxq2pVqZX1UCWlIHsr5MYvUVicrzE3ESJJUkG1m6TiNleBwAah+bTaG0+DZXGX1ca33DFNRouz6Ok/NF2nr9V'
        '8Wjzxeqf8yvNZh2n2YyjNJ92mDPXSx/5mkqDbFz9ow8ozbccvgerEXuwHrUX2zF78c/FqHPg/M15rP1/xsL1ayxcv8HC7VssXL/Dws2kAC0W6y/T7GeJZr8Y'
        'aPZzDZn//ItEMzOEWq4QEKx0piiKAyfhAq3RBcaBbDwb+MZJjNgiMTFBYs5WA4uTJVZtMxBdFw5ovPY6jVZdp+FL12i4Ik9pfMNlV2m+4spjq/+zg8XG5puj'
        'RzTftPqbTz9C86mH+GJ3wWNfZz8x1bj6R+zFMmQ3VsG7sB6+G5uRu/E7xyPyzimlw4oDtBj4pVEuX9Ji0FdYzEuj+bdlNPupslo/mmT++CeD6b9VwzCCMMHQ'
        'yrQUUaSTlSgyuuDRgSxc4L1ZJmSLxIStEjMTJRYlGVi5XSKyLhzQaGUejUTjl12l4dIrNFp6mUYvXqZ7zLXHGrlsU8FvN3/aYVpMyWHV94+D81iSQyvz6g/e'
        'hdWwHVgH7cR6+E58z4LfE+QSfwPbERtpMWwTzd++Wd30Hypp+kMFTb+vML7W+rgaioBQWeWO6miSaaWVUMVhckZet74AAArRSURBVIEYyBhdECcrLvCMkwiK'
        'lxmXIDEjUWJhssRL2yTC6ySCVlyl0bIrNHrxEo2WCF2k0eKLuL72BAAb8x9vvil6RPNbPKtnxTeXHvu6/guyqle/aPzQ7VgP24Zt8A58z6BAeJKGnJTostdA'
        'ix9FcyuNjf6unKbfVdD02zKafltere9qyASl2Y8VT3RDy1gZa62MRivTWrhAV+0CMQvc42SGbpEYu1VmaqLE/GSJZdsNhO0w1AGApZdpvOQCjV8wadF5ReoV'
        'Fx5r5Cd7i57Y/OZTDtFisp4Wk7L4ZNvNx75OJXY/NVd/4DasA5KxGbqNIWd4RAqQWn836LCMbZyp+d8IldH06zKaflNq+rjUqJpQTCCaCQnnCDfUgNAqVsZG'
        'Cw46kwuqZoGMW5yE/xaZMVslpiRJzEuWWLpdIrROACwWDc9VhqsyYMX2cuFZJesrxYa/Rp25UW4cuErsPN58ceg6eeXBI1/zoMyA5Yg9WIbsql79ovn+idgE'
        'JuFzmirVhlFT3qeg+wEDzb4tpcmXD2tJ/F0pTb56SJOvzXDKjBCUeDLFUg0ntNwkmVwgVc0CcU/USyvhslnGL15m1FaJZxMlntsmsWS7xNq6ANBkUW5Vw5ss'
        'OKNkvLLDmXeaszcf34Z6ReVWZX5zETs1mj9o+VHkWvvQzFPFpsG7E6th242r3z8JG7+t2AYkKY0Vqgni9+R2TMY+rowmn5fQ5DOTPn9g1BdCJihfmdwhXGGa'
        'EUYIJidsFC6QsBWXdVqJdsoVBcpt6YDNMkO2SAxPkJiUJDNnm8TiHRJrdtYFgIWi6caGK/luOlgJzfg87zEAJWUSfVaIe55Hm999wSGKn3AQ812aXSt6jM23'
        'EVcJ/lvxOgleJghVekLjxd/V/JzeqQZafl1C40/uV6nJp/ergZghfF3LCT9VD2bFBbHGWdC2xkWdc5yMd7xEyFaJCckys7ZJLNousaouHCCukJvOPalku1lK'
        'xouomXWcCwVPvopIOXmPl7V5vBybx77jd5FqxZWo9F/vGpsftKM6evwSsRF3OOI+x28rnidRZAbxGIwnyPx5g4/JOMWX0uSjYhp/dI/GH9+rBmF2hBmCyQnG'
        'mSAGszGKLGMlVFoZRy3KRZ0Yxn03y3jGSwRtlRmfJDNjm8yiHRIr68IBzeefotkcY7ON+W7MeOVgNeMoTotO8KBM4j9bt+6Woxll3PVYieYHitxPwkZcnvnE'
        'Y+NjvGr2EO8bM8sMohaQx1Tjc8TX9Es30OqrezT+UIAopvHH92n8acmjEMwzQYmiiqoostgkYxsrY6eVlGEsrid6x8l4bJEYtlViXJLE9G0SC3dIvLSzLi7j'
        'njtB89mmk6yQyHdzxk8VOkTHRce4XlTxh5t/+koJjuP2GptfM/d9t2IjVr638UZTPPES75wU7yEWIKpgmBr7GJBaja/Sr8bZoPmphMYf3KXxBwLCvWoINWeC'
        'KY7M29MWSgxJqGNl2mglJYZ6xcm4x8sM3SoxNkli6jaJBTskVtSFA1qKhyezTI03NVzZ2ZgzXujZbCynZLN+U94Tc95cBXfKWfL+6aodj1WtoatEj2i+l3jY'
        'Ih43bsX9uPHtq2aZQTzijFpQzE03q+bXqAWE9++YIIg4qoZgjCKzC0yHtY0SlptMMRQrKTHUc7OMa7xMQKLMmGSZqdsl5u+UWLarDgBYzDlmaDnzCC2mHarR'
        'cGPTjQPWOGTFtXLLZ9KVq+W+z+cw/4OzvLbpCjE/XmTOmyfpOi3VuNd/YvMTH22+jxGAZlgSbuJN3CY9AqIWjD+kE+B6WKb5J8VGJ3xkmgliMH9hcoHpjFB1'
        'hSFiaKOkxJB4XiDuh7pvlhmUIOOfKDM6WWbydpm5OySW7jIY6gDAkZsW4vHhNGPTW5p2NdVNz6Dl+PSqO32LsQdp9XQKrcYcqLrdVE65w413PNWZX6v5Pqbm'
        'e21GPWQL6oBEHJ7Zg5v4rSomuf8GjCogtcGY/lz7cztsLaXRu3eMM+Hje8ahrMyCh8ZhbJ4F5hjaWGM3pJPpullmYLyMb6LMqGSZZ7dLzN0psWSXIf+/HYDV'
        '7CObLWceotU0PS2fzaLlhExlpT/a9FqNH72fVqPMjd9TY59v2u0EJj+5+Z5xyuoXP+mgCUqi/crDuIo3cQv9BognwfhdHQeXHInG7xQ96gIlhkwn5qphLBxg'
        'UHZDVrEyqliJ1mInJAAkGAGMTJaZtF1izk6JF3ZJJ/7bAdjOzPaynpUjW07XYzk5Cwvx+PCZtKqmWyhNT1Guk6saP3Kv8XRbc9UrzTdeMVQP3ITq2PESzd+C'
        '2j8B9bAk7IZvo4/uNoOOYHwn/RNAPAnGH1WLT+7Q+P27RhfUBPCNKYaUQWw8ExgPZTK2WuPD+86bZQYkyPgkygxPlpm4XWb2DomFu6TvG9RF2czJ+dpmRg6W'
        'U7KwnJROq2fSaDW2ZtP3G28zR9RovMh606qvihzzPr9W8229jQ/Xjc1PxH74djqGn2DgYXAREhBMIH4PhqI/0HzxOdZfF9P4PVMMmeeAGMTK6VgAMM0BEwAL'
        'BYCYAzIdN4NzAnibAEwQAHbKLNjDmDoB0GCO/v/azsj6WvzEgvXkDCwnpGE5/iCW4hJNiZo91VFjbnzQjupBa171SvMTsPExbTW9qweuaL4mKFlZ+R3CTii/'
        '4mzAIRQINUHUhOH6z2D8jiy//C0AJgdUXU0YAbRQbkgl5TzQYbNMvwQZr60yIckyz2yXmblTKnj+LE81qMuymZE5xHZyWpxqRtZDm4mpWI07gNVoAWEvVmLV'
        'BxmvFJTGi7ipmfXmVe8jAGzBVjTdN8HYePHz/ON3037FIXpoC+mfg1GHUCD8LognOcMExKyajVf+7ig0+0hE0J1aM6DGVtQcQeZnBbESVqYragGgb4KMZ5JM'
        'sAnA1B2GxQ3+rJp6kYZTzlIyPRcmnoHRv0LwMfA/DF6HwD0HXLLAORP6ZEDPdJMyoFcG9BYS/y0T+mRBX6Fs6CekB2eTfg/EP4PxGJAa6pVSadwFiRmgHMhM'
        'uyBzBFXtgoQDzM+Rjc+M1TqJ9ltk+iTIeCTKBCXLjN3G8bCwP/kX+wXqcXn2DBU1AfiZALjpYWAm9MuE3unQPQ16pFWD6GUGkWkCkfUHQeTUAFHbFU+C8QQo'
        'Qpqf7lfHz8e1zgEmAOLJmvkcYHSATCsdqMTN6GbonQAeW2WGJku3xm7/i/5vHYHHmDTuFOW1AbhmGwH0FY1Oh26p1RB6pP//g3B+AojarqjtjJoSMLrvraDR'
        'e2ILWvxY/DQxb0HNT8vMjyurHlXKyqPKdlsEAJnBW6WCodv5a3+3aOAh+occp6A2gAEZ0Ec0Og26HTRBeBKIjP8aiMdg/BaQw9A7zUDTj+4ao0e5HRWr/0kX'
        'ctXX0ub4MTtA/ASd02aZnvHS0QF/1cqvXYFJPOVziDeGHOJeFQDRyHTokWoE0NUE4b8MIvu346nmrKjtjk47KmgqbkKVw1fxo9fSVdtPc/yYB3CNnyPSgoX4'
        'uSGddN1Jx7wGe/+Gv8y153aauOqZNjADXf8MTvVJp6DHQaSuKdAlxQjhERBpJgi/Mx/+KIjaruiXLdM7VaJ9UjlWX9835r1yHV3j/ueRm9Aaz4nND2U2GqTm'
        'm6SbzbTS4eax0qcWGwlqkFTHW836qq/6qq/6qq/6qq/6qq/6qq/6qq/6qq/6avDvWv8PB1mC+X13p5MAAAAASUVORK5CYII='
    ),
    'assets/badges/official/planner.png': (
        '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'
        'fdzz/wHTJv7qaChzeQAAAABJRU5ErkJggg=='
    ),
    'assets/badges/official/powerapps.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAgAElEQVR4nO2dB3BUZ5a2tfXPVO2/tVtb4xnUyjkT7Bnb'
        'Y08ejyd6UM5qdbdyzmoFJIEQGSSyQCSBwMYBk5PABBGVQUKInJMCOOCx8exgm3frfN+9t2+3WlI3wmBv+VadugpAVz3vOe8557stYWHx/fX99f31lK80n7T/'
        '1LprXyjwLHiNgj6mrz2t1+/f0P2f/WtaXuhd1fxa7/Lm125Xt7zQX93w1F7/mVz5bvk++Z75M7We2jP5nvlfaz21kAd9Ld8jv1vroZ1R6F7o/aRfv+fNZp++'
        'utaZ/XVtZ3pXt3zdu6oFPctbcKemGXeWNOHWouNf31rQ2H2z6viMa7OanvjrP7NL66Z1zffM36z11D4yhK4dJJgYnvmbc9xzXEb6+v117a79a9s299W1Pupf'
        '24a+Na3orW1F74oW9Czj8G8vbsKtBY24Oe84blQdw7XZR7++OuPI5hszj4749Z/pleeRl5rnkfcg3yPfJPBaQyE88h9oPbXJj/v6/XXtqf1rWx8QeBZ1begj'
        '+Csp+5txZ2kzblc34dbCRtycfxw3q47jxpxjuD7zKK5NP4IrUw8/uDL1aLrFd/D6tzz3vPkEftAwT4x59G+a+uIA/q2/rm2+BF6IvtWtkFsPwb+9qJFn/9zj'
        'uFF5DNdnHcW1GUdxdeoRXK04jMuTDuFSWcMyWMDk13/mV65b7rQ89zxI4UGRz2IEolSY+vr9da3TBsAfznoI/uxjuEbZP+0Irk45jCvlh3Bl4iFcKm3ApZID'
        'Cyy+C1e2R3ZArnsuct3zWOgJYUSU/CEF0beuPM88v+Fev29de4AhfD3rWTbQem4YWM/VKUdwZfJhDr/sEC5OOIgLBQdxLnt/jMW3+cr1yX0u2y2nN9ctF3oh'
        'E2RQUTyGr5Jc99zeYq/iHw/2+jdXNj7Xt7at12TrmW/ceq4I1nO5rAGXSw7hUvFBXNAewPmc/R93pzVYWXxbr2yX7EU5bjngkasXAwUxTxT6ONs9G+nu6bWD'
        'vX5fXesio9azqhU9w1kPwSfrqeDWc3niIVwuacClCQ24UHgA5/MP4Gz2PpxJ27vR4tt4Zbtne2e75DzMds2BGDkUkiD6ohivktxBBaG/n+GWgRTXlK9SvFJe'
        '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'
    ),
    'assets/badges/official/powerbi.png': (
        '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'
    ),
    'assets/badges/official/powerpoint.png': (
        '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'
        'nWT8/xM71CM3Wfe6AAAAAElFTkSuQmCC'
    ),
    'assets/badges/official/project.png': (
        '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'
    ),
    'assets/badges/official/python.png': (
        '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'
    ),
    'assets/badges/official/qgis.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAAsSAAALEgHS3X78AAAgAElEQVR4nOV9B3gb15UupChlN4mjSHaSzfOzQvSOASnJ'
        'duJE2ffiQolUsa2sxCZ2sUsUO0US7FXsBQRBAARB9EZSlGSnrGPvZr84cfa9vJe2LpvYcZFsic1ykTAzZ787wNAkxQICoCR77/f9BIhy7znnP+e/d+4MAAbj'
        'Lm0KBWOrAhhbbTbG5xTP7dtmsx39nN/vBcZW+j3U+4GxlQGMLZtr8aezbQFgbEEBAhSkNRp6XfdF9j3ttvt3dE2EfbPXztzd4wrb2z8ZtqfbueuhHscu/sDU'
        'A1/vdX17p+I5xrb1xqWIUaw95me5bVEoGNsUin3LA7UFZWrXz8K+2T3BeqJ3gpXb42a297iZl3rcrF/1TjD/0DvB/GPvOOvlHjfzvR4385oP0z1u5pvUcxPM'
        'P/eOs37dO8F8vtsdZupxh9X0TITF9U/tEow+K/3ySsSqVBGf/29DxvLMU01G/H2fexfW62Ke6HUzNd1u5u97xpl4j5tF9p9ngfICG4ae5YD6JxwYvMheQP/5'
        'pUCvo58besb7etUzbBiYYkPfBIvsGWfhvS7mTI+b+WyXm1nfPb7rH7ud7PsXbIHPcFVQGrys9TrDHu0dZzZ0u8J+1j/J+ljzcw6oLrFB6Q0Y9I57gYhAwaMC'
        '6GYRNKjHF6F3fNFzvtf3TFDvQc9RffZPsmHwAhvUz3Jg6Bk29IwzX+t2sYw9E2E5iAyfaVsW5pFPOxmwTNuRRne7WGXdbuaLveOsD7Q/51LB6B1nkb1upgcF'
        '0RdM2CRQRFFkjrNwRDayQXWJTfaMM9/oHmcaO927fmiDTyZ8NJl/Kifwo8CgnEBl3eUM29PtDuvqcjHnBi6wQfUMB3onWGS3i+npcbM83d4sh9sKNwWi2828'
        '2e1m4UjClBc5lB3dTubvelzM422j3/wG8kEBiq1HbV5/7upGrWgUVNZTGdPp3oV1OcL0ygus95Em946zyW4Xi0QOo9sebxDuANgUuhdA2UR0u1AFUnMKqf4p'
        'B7rHWX/qdDJPd7p3bV9YGt+tsuRds3tLt/si+74uB7Ove5x1dfinPOgZZ+NdLhbe5WaTnzh9Z9DlD1xsssvF9vRf4JKDz3CIThfr/3Y42U/Tvvr83HLXTbLp'
        'Ksbnu+zsuA4n67LyEhd6Jzlkp4vlQYH3y3H33YVONxvvdLPwgYtc6D3PgU4H63yXg8lBvqIqpyv9TjZKctCdDscDzE4H06q8yPH0TnJQFhGdKJPudCBdwQH5'
        '0OlkE8gfRETPOPtyu5OdRQfgjkkSYh9NsOh+q511qHuC/cbgM1xv1jjZZKfX+M8UOpxsomeSQ/Rd4ECbneVAR+ReEm45oNzcRrOObs85WeVdbpYHlWiHk+2h'
        'MmY1Bz4TYBEdLpZn4BkutDtZf2hzcvegWNDJuOmN1j2FTfiFc06WsXeKg7Ke7HCxieXGtocYHbcdHArty+Fkk+0ONtEzRVX8tWYr68e+hESVsHnzAn1QNeBk'
        'fqPdyXT3X0JZwCYog5xsWArOZx8ODtE5zoXOcc6NVmtYNorN0aNUJWzZtJVOh/OBfzhnZ/964BIPZcONc47b6/S5uwxtDg7RMc7BUTU0WcPKfeHasimy06xi'
        'fq19nPOv/c/woM3JwW+Hg60ODonGanNyCOoxlxft7pWBnmvzvpfw2YhuyU0lAdnm4hDdU1xoc7AKFslR6IKv0O360jkHy953iYeCggICmwYHh2yzsz2tdg7R'
        'Ps6Bngs86JzkeoPr4BCtDvbNVgfno1vBvtFmpwIOXee50DPFAyQRyN5W1B/q10H1EXK02imSya7znBvNFuYx+rgoZOv8JitrsI/KfPaNTXPCwSFb7N5s777I'
        'g67zPGi2sd9rtXF+02zjKFtsrNQmO+uHTQ4OU6EQfiG//f6/Q4mBkNvN/qLCwL6/xc75fpuDFd9mYw+1ONi/bLaz30L9ULY7OCRFhneskKPFziHbXBzinJtz'
        'o8nC+ZEvgQM/TqCD32xhF6OManVujvEtdirwSGrI3kt86JjkzTVb2FOtDnZmk50tP7qB05FLGjC2tDiYnFY7K7vFxna2Ojkfdl+g5BNaHBwCjRkaH7gLQP22'
        'o6pzcl5vNIdxfSRsfE6gd/9abN/Z12LnfNTqoowmW1DAQgYuNKOMd3HJjkkeuj/fbOeeazWFSdEyd/k+E1phrLMFQFWs95wwYxvaxaSf6O5mf7HZzhI12zn9'
        'zXbuR2i8NheXaLJzcGRHQLCvjGY7F++a4iN//jn9pYjPb5gEOvMbNN+6r8nG/h0VHAc3cENXMb7JxiU6zyNDuR82WTn9dW7W/6QDif6gU4UbORm/WiKhfgBg'
        'gbgOB4fZaGbr29zc9zun+JQdzd7AhQ42rqfrAh8aLdwGKqYbkSLfWpbRaOP0dV/kQ5OdczPEBhItDi6B+m51cl9oMHO+j8ajAgSMLShood7oAoa338UnV5oc'
        'nB81Wjm/60BzjZ1LNNq4ZBNKjBD42GTjki0OKnE/qrNxH/F732gh+83M/93s4OBNdi652LBg0YhK3sklmx1cstHCaUKTJzXubbx0ZPE+lsJ231cabGxV2zgP'
        'Wtxc5C8RMl9tXOLcJB+aHJxfb+iEDtLfJjv3xbZxlP0hNMiKDOJBi4v3bq2Re5gaS8HYGvAkG2RbfBK+3srOaHPzPmxx8ihJarJRAQweVi7R5kZ9corQOGsS'
        'QT/ZYGeltbp56M0kMmSjWMmQBhsXR1nW7OC+XmdkeksS7vwFU/Skje7X25gHml3cuWYXDxqslCSFggSixcVDlf/XOhs3jB7zFkNozW0yPvD1Bivn9xQBNv+M'
        'aFgH9Sj4E3xkxJ8VNhYbjWPznTO+WxotSfV2ZmSjnftBk5MH9VYu2WDjQfDg3uy4KIQ6K7dx4UT/8pau8i6X6q2cvLZJAdTbeHgoBq+38shmFx8a7NwrdRbO'
        'D9AYd+sJbpvPrlozO6bRziMb7Dyyzsoj65EfgcC6AKLRwUeJ+I5i1JuAS6qA/qdUz9/ZaOe92DqBCOCuSYA/BtDGN9p5nhob58DdHPzFV+yhO7UWrqJ1XAB1'
        'Fh5eZ6V8WRH1fqLOzMXbp4TQYOdQG3ZLVnm0BtYY2dFU9lt4nhU72SgsPLx5XAA1Zu+gIdug2sRGBwatzmot3Clkf52FR2zY91tBNtj5UGvl/k3Rzb5nxcFr'
        'LbypZjcfvTgUAxKor1oL5yKSN7QOvxtOYvvTaEU4O8Jm1Vi4VxscVDKRK/lZu0HU23lQbePGfzKOLyh1o9ywOhv3hk86ggYaqMbCnVc4uPzFTn1a2lH6OMHI'
        'zWpCVWzh4SiANTQsXtRuBGYe0eRGisD96cIY9EC1Nl5RPSoRC4/cUKcroMbExVsmhVBj5VSjvj8tmb/yNrxse62V/8smtxCqzXy8xsKHIEDUOwWIwDfo1SB9'
        'kRGj2sz7edO4EGqCHcTsHaTWwn/97Oga695PQUv3rQyrLbwk5FO1hU9UW/hktYUPgUJh5uONbiFUWXi5CwMpjFx+tYX/Zr0DlRqfCI5lnqdpQggKozf7b/sl'
        'G6FsvipASVpt5r/Y4BLSJARMQLWZ52mZEqH7hoVxFGZeYp0jJAwTVD9m3t9qjQLOpzn76UZLdJWJV1BnF6AMJhVmKpMDQpWJT9Q6BFBp4v9BYeJ9mxqk0sw/'
        '13pBBFUm3s2gOqfkRwiVJu7Yqkd8n9Km0Am/VWXiz9ZY+RsmoWopyEozn6i2CUBh4D9EneutNPIvNYwLocrM8wRDAIJX59hRn4XsX94qTXxdnUsIKIDLgnoL'
        'KtdAhYmHN04K4ayRd5JRMMoNqzTz/lpjF/jV8aow8UnEaqWJ9zY6V8v4DDWFL5EqxngxjRNiqDDxPZUm5GtgqDAJiFqnCMmQilFhEsgrzHyCYsdElcfq7K3X'
        'qUOEjLOFynFAB2+KfdsCQgi3uOl5oHyMg501eoNfYRSQARNgFJDVNiFUGPm/ZJw1CZ9oOi9G/wTHqpGP10+IoMooyLxb5AfQ+eMQXCRFHxPk24Q7yo38X9U4'
        'RSiIeIU38QJCpVkAZ438GUblmCCjzi1C/wTVITKo1iWCMgv3e8FuuoGPvOmy7dKZev7vZjsefm723J4X/MPe52fO7XnxWtvueqov29HPhYAE6lQpulNu5Bvr'
        'xsVQPsb3nDWiIAaOCrMQGOVGbh0K3GJGz24Q5SYBUWlFkwr/clEIlp/gI+9m5fbvw7n/AXiX3EMOfA/I/of9AvQ/TJB9D8F0y+52mtBgSaCv0igfE9Q0TkkQ'
        'ATeCJaB8TEAyygwCfZVdCGVGAVGOHgwEYwK8yi6CsjHBb8s07PuCJuCol4DpkvseIap3wnTZzo+nG4X4bMeD+Oy5Peti5twefK59L473PgTTrbs7QiFH9FFx'
        'mZGbqXCIKJ8DjtciMMoNfK0CBS8IAsrG+DgyqszAfz7X4N1qDWb/B2gCyu79PtTeB9dKd3imy3fCTKMQ5joegrn2PTDXvndNzLbvJWfP7SURCbPnIlqDlSP6'
        'mKbUxD9ebkIJKyTLxoRkmZG6HzAY5WMhIcBTOy6GUiPf6LMXORkiAu6Fa6U7PdNlVCUsImHv+iSc20vO0pUQpBzRe2bFJv6jpWOCD8qNQig1UCRAMGCUjQm0'
        'VXYUPCERKIslYwJP9bgE3VJHwL4JaxMI2AFUJTRtgATvbdByRC8qSg2iPSVjwqvlZhGUjAmJ0jEhBANGyZhAW2ETB9VZiUHgqXZLoNQg2PQKmEa4A3JEE1Bg'
        'EO0pHhNeLTOLoHhMSJQg/4NAwAQs7UhwU+GWQJFBoKec27QK2LkEt1OOaAJK9MJHSgyC2TKTCIoNQjJoAorGBNqzNnFQbBaPCTyVTjEUGwSXTuh2fWkRCZtI'
        'wI5QytFWfyfh4lH+McpvFPxRIVlioO5TKA4AjCKDQFtuFUORQUgE0gGFUSGO+ijWC0O7DC1buwKWytHD3kB3PrgmZjsfJBHw/odhtmuPV44A/CagQC+ILzGK'
        'kM8kqoAigwiCAaNwVFBTYRdTQQyUAEReKSrJUcFbZ81s1m0loIyWIwHMtT0Ic3VymKsPXxOz9XJyrl6O32yJgKtlAtXLbMYX16ta+kCsyCCuqp6UQeGo6Eaw'
        'wS80iEhGkV6QUeGUQuGoEA+iM7LQICJKzWIoHhHuDXor4qj3ve/6S0D5Tpgu2g6zHWKY/8URmPtJNMz/NBrmf3ZwVcx5n/fAvx2BD35ziFq9rfXZA/r61QK9'
        'oK9yXAqFBuHNQm8QA0bRmAgYxaPiRytcUijQCz2FoyIIFOj9qJ/CMWFiyCrg7H2PkDX+EHAvTJ/ZDjN934H5G0kwP5cJ8+/7h7n3s3DyRja8/26ST46O3nJp'
        'PP1/iY35tYIR4QtlFgkU6oV4MPGiKmBUdI1x2sAPL/A+SBbqRWTABIyKiDKrBPL1woFAA7+cgA8r7/0+1FME3FyXgILtMN37HZi9GgVzb/4Y5i+nwfzl1PXx'
        'TirMv5vmIa5nweyVJO/qaNGHORYnU55WwCk0CK8UGcVwRi8iUNwCwRm9iPT18StGnl74wJlR4avFJjGcGQ280wJfpwV64Wv0vkmgDXzOv5y7455rJTt/clPh'
        'rYJrZTvJdQmYPgizbz4Bc5ePwfy76Si462LuCnWLEx9kwuyV5I5bSPDdIhnKHxX0lFolyGccBTKQWOWPiogSiwTyRwQqapMpXy+aKLNLIH9U6DmDGAoQBais'
        'xkR4nlZEfX9CMJeeg++9fzn1te0zZTsv3VDcC1dLd+L+ERAJs28vJWH2ytqYuZxGzlxOJT3vZ8D0lZxSNPZzS89pe68TUii25o8I+ootYsjXiwhEwhk9ldWr'
        'Il8vXoLTIyK81C6DglFhOtXzmRHRubMuGZzRC2+u19naA4mIIhNiVqikMybgMmB8QsLvs+77ykzZjkuoEq6W7CT8I2A/zL4dCXPvHIP330uHj6fT4cb0yTXx'
        '8bV08sZ0OkHMZ+HwftGpWxYT1DeCeT/4d2pE2F9kkcCZUTGeP7I0wOtiRISXWKWQqxV9l+r3tF4UX2BAT4jJfD2FjXVIM6sXE0VmKRSMif+c3cvfuTiIAZOg'
        '8Orve0U7v7qqHK1KwH6YeycS3nvzx/Dvf0qA3/w+Dl76w9r49f+PJX/7xzjyt39KIEwvJOR7baCCvmXJN8U8t2/baYoEKeX3aW/s/IpRgVGCbl9F8k85manm'
        'CE6PiN4q9D5BrPHm9TEixgtNEjg1IjyJ+g52Pljs9KpytAoBM2/thw+uHIBXXvkR1Nl/APWuKGhwHYD6dVDnPEA2jh8gmyeioXMqJs9rwyI58n03HsKpEVFf'
        'oUUKpxAJOjF5eoSKwao4pRN5Sh0yOK0XeS/Mokvs9IjoX4qtUiqAfgV6VQJEOMqKUyPCX57SybaH6tpQWEuO1iLg8gF49ZVHodQogVLT96DRfQAa3VHrklDv'
        '2k+g26bJaKLjQqxXjnyrMzopFuRIJ+wvNFPJi5/SieHUyOrIGxF5iqxSRMTpJQTkaYWKM2MSWM7iqUCgE+NIivJGRSmUscF8XH8dOZou2+m5Vn4vuT4BMsjR'
        'CqHU9LAfwffBeYCodx8gmyaiibapGEqOFCvJkWLftlydsL8A+TwiJvJ0YnLl4IuJfIMEkfButpYf7vPK21nGsISXpxN5TumpFwYHRKJBArk60ZtZfcJv+eIX'
        'kiukFYvkaLp0x8WPq6gKwK+d2U7OrEFAiVEKOTpkmxBKNkACkiNEQuN4NLRfilssR1uWy1GOVtR3hiZhREyuEBcckZSjE/1ipd2CLXla8aUzRgnkejsIioRc'
        'nZg4Y5QiEgYXBy4UDRZtGVwt2THwseJemCncjq9VASVjMsjVSuCUToJWH1Bi/C7UOaOg3hkN9dTtmiDqHFFk0+QhaHI91QLoKxAWbbkvlqNsjbj/jFEGeSMS'
        'HI2Xq1uK0wYp5GnESUtiQt85rRPHFlkxyNWKPXk6CQQFrYREt6f0EjxHLXoyVBPycjkCBWPbtbId/R+Xfh1JEDFz7SC5EgHFYzLI1nptQ4HI0aK9mIcpEvyC'
        'I4qsc0XhrRcOQ4PrcDc1NsASEqjb5/ZtQyTkm2SQo5MQOVoJ6Qs+maeXQo5W/HZWn/ArC44sfnP2MO/bOTrxH0+PoRdKiOXs+YscH7K1EgIxnjsieT1dRX9S'
        'JnQX7AJ15Rz6pl7F1qt5X+37aDAMZqajiZm/RZKLCXjllUehaEwGWb6MRLah22xEgvG7UOuM8hdkjT2KbEYkuI+0L5wrhlvlKEsr7jtt9JGgk5A5WjF+xowh'
        '+aHed0ujszNTLS47Y8UgWyf20IEMBhQJJhmStRcyBqTfCLUcKXwEoPvTet6A5/ohmHs7EkfBX4uAT+zzklDjQAGOXjX4NTQcUWSN8wCOSKh3HumiqmAVOcrS'
        'iPsRCdkjEk+2TgJZGvH1jGG+eMUY0A9kaiTMbK3k9TyDFLK97K0f5HWQ5SMhWyf5xWkV/x9C/XFVoOXopYjPz7wVOXBzNhrm3tlPTL8VSXiPAx6FQoMMMjVI'
        'eqikWIIsDdpGeZgiwW84D+BNU4ehzrG2HGVoxP25eimJkjpLI+pZc4eADkqmRlScNyqDLI2EXG5soMjSSjxUNgxL/iVFLdxBG8gIFQm+U4toO3n6b5FtH16N'
        'gvkr+/Hrl/cTr77yGBQYZJChWbBlCdBjmYiEMW8l1DiiodoRtR5IhS2KbJyiKqF9IbDL5AiRkqmRDGZpxbPpKu/Sc93kS27hfTVTK/7P3FEpyhpyucEBQyPB'
        'TyESdOIXkvsEuxZnS8hI8H33/9U3Hsv54L0DxMfvRREv/8ejROEaBHghhUytGE4bHoIq+wGodh4EBUXE6lDYo0mFIwpvnDoCdYvkiF6hLXzm+CL7ixlD0v/l'
        'l7/0C7KGxbG5YzLI1EpwZFyokKGRErlGDDI10lfTNYIHqYw4GrqfDkHzAT0nXPnr49kwd9Dzl9ceh3w9RmRovDZkrgFEUt7IniUkrAtnFN4wdQRqHU8ulqOt'
        'gV0hQu99H2V8LlMrdZ0yySFjWOLJ1KBqCBGGpXjOKAZZetl8ulpcSmcKKuF9IVol0ZWAX92f+PIrj35YZJSTaWoJ4Q3y2jg5LIbckT1QiUhw+EUCWWWPJuvP'
        'HwGF89BAlm3fV5bvAGxoO4bWKHR0nKmVvpk9IoOTGimVQaHCyWEJkTkiJbJHMUgflvxr1rDkBwtEHD0adEWgvujJ7vwvHtxfZMLmMjbgx0k0YftIUDgPQdU6'
        'JCACqhzRnsaLT0Kl7YA733aU+pRQwH4s/CaAWnIiExk+TBlGhpYEKZmukRI5Yxhkj8rm04fEo+ka6YPLMwYFEiUFPan5W9LUL3r4JvrkftFjmSPSeeRL+rCU'
        'OEkFeW2k+0iooEg4SJGwJuzRUGmPwhEJCme044Ru35eCIoEOwkmtRJVrkkO6WoL7Y/gChv1DujcgRJ5ZjipjLk0tOZ+mkh5b9ciZ+pYt4RdWxq1LPDqZ0lSS'
        'yJMa2fUMnYySo3Tv2GsiTS2GHN0eOGs7AFWOgyjAUEkFenVU2KPwhgtHoMIW7Shoe/TLgZNAz+IG9j3pask/ZxsoufD4Y3gAINPUEk+GVgZonJNaGaSppW+k'
        'qaVDqUOSp9NVEkmWTvgtv+aIFfSWltW0AUFkpl46kzGCQapa6icJEsjykVDpOAQVC8E+uCIqEBwHb9RfeArKrdHufNtDgcsR/aakAQkzTS19OWtUjgzC04dR'
        'KYceacMyIk0to/o/qcMgyyCHXHM4pGtkH6Wqpf8vTS11IVLS1FhV6pCsJk0tq/YCq0pTS5tT1KIfInv33fpV8lvobZD0YdFjJ3WyedR/qlpGpHnHXROpw1LI'
        '0u2FcluUj4SD6+KsPRpHJFQ4Dy7IUUDnRmgSEvrF0jSt7D8z9HJI8dPwIEGmqmV46rDUg+6jcbOM4ZBjDoc8e8QS5NoiyFPO3ZChx2YSBgSRq32fPy1HSSpJ'
        'ZNqw7Hq6DiNT1FIilQryGlDLIGUIHS/shTJrFFTYD8FZ28F1UW6Lxmun0MR8yNkynvzVxTZsqNHamqQUCtN0stcyRjFIHZLhyLDbBBKNlzIk9aSopTdTh2Q3'
        'liNlSPZxuhYjUWBRgFc76qQfSxoQRJ4cwWbSdXJIGZIR/tiRokbz224otUTCWfthKPeDhLP2gzdqp56CCtuRSdVL6X/vTY5PvtV3I5VAlXCiSiJJHZL+9SSq'
        'BC8J5G0kAtZC8pCMSEfSopXNnlCJD9OT9rJ5YUGOklWix9K0svl0LXYLCSmrIFmNVkgRUIJIsB2iSFgPZbZovGbqKahyPeVSTSooEuiDtY1Vgu+8KJKjFLXs'
        'tZOjSI5QVq5u8O1GslpGpGowMl0nu5mslFC/eLRoCbuiHKWqZddTtRiZNCQlkr19rIkktRTSNBFQbI6EctshKKOCvB6iccXkk1BmPfR8ie7x72w4+MvlKEUt'
        '/mbSkPTZDIMckoekePKQjPTH+CUY2hwkDcmIFA2GiIBEHwlryVFCjyQyTSufSdVikKiSEX6NoZJC6nAEFFEkHIYy68FVcGgxblZPPQ2lluh/L9FHeS9LCaTR'
        'EzPauEtWSTvT9eGQMiynHE9SycikIQxoJN9mJPmQOIQRSWoMUnVyz4kBWfaC3bfIkVdaE/ojHkvRYPMpGjkkqjBisQ+rIXEITdK7odC8H8qth5cHe0WUWg7e'
        'rLv0Yyh3HvJeGRFwo34N2zuZJCix4ydU2GVERNIQhiepZLg/DiRtMhJVGJk8jBEp2nAiQSnLWU+OEgYkkclD8uspGjmJKsFfElKGd0ORyUtCKQryWrAcxKsm'
        'noIiUzT1cydBNeTMPt9PiCdqMc4Jpew8yqBUXTiZNCjDk1QYmejNxjuGE6gShjEiGWW2EvNLjlK08plkbTicUGGEX2OokKTuhkLTfiizHoESCwr0KjAfxBWh'
        'ImD5T51QRKiwmBOD2H+kGyIgUS0nKCdUGH5CRWXkHcEJXyCTtXJP3CI5WnZ0ukiOZI8lqrH55GE5JAxS9q/X/xISSi2HKRJWhDmEFbDSz9mi+/G9/J0Jg7KS'
        'hEFsLkUXjhwnE5QyPGFQRhFxJ5AwiJGJwxiRpME8sX3SSnrndfnWBS1HMQOSyMQh+fWkYTmZMCgjbulvBcSr0AppNxQY90OJ9TAUWw7dCvNBvGIzCPA17zaw'
        'z6l4lfCBeJWsO34Q+0uKPoJM1odDgkqGe4HB7UY8qgQ1hifrwiF+EOtdNClvWUmOYnokkUka+UzSMPV6wq8xBmWQoJLDacPjUGI9ctsJoBrl2KLJLrZbcn+c'
        'Sl4cp5Q9nzwS7kkeiYATQ3LK0AQVRiQMYjjKUC/ox0OL+EEKZPwg5kkYlHuStBEQNyAdXNh1XWV1FNsveyxBLZ9PVIdDnFJOUPatAzRWgiocTo09DiWWJ6HI'
        'fJhCMYLpEF4x/vTmEnBLRfikKW5U+uVYpeyH8QOy4Tgldi1eJYdETTiZrNsNJ4bCIV4pJ+KU2M04JeaJV8rxuEE54QvchhGnlAP1fiWGoz5R4NHjiZoISNJF'
        'kAlD4YAQ148lrEDAMjnCIhNU4ddPqMPJOCXml01xSlRx4ZBneAKKLUcWSCgyHcLPjj8NBbeJAMYnE97SreRYw9574lXYj+KVWF/coPz/xCqxKwnD4ZA6tgeS'
        'R3dDojYC4tXhEDtIkeKJ8waSAnpsMRY/FzeIebwIJ1F/iboISEF96ndD7IDsZqwSeyVWiU3GKaWFMcPyXev9Zg0tR//Ug0UmDEfMnBiOgFiUKCjI60GJQdyg'
        'l4Qiy5NQaD4MhaZDePntJoBuCsbKP1lyVCH8QpwSk8UpZYkxg+H1MYOYNXYQeylWKXsrYTgcTzbsgST97gUkoorRRSwgceST5xB56PVxQ/KPYwewv8QpsRdi'
        'lbKBmAGs4PigNPq4insvNaj/W8NL5Ch+SD6PKidmwD8SYqlKDIfc0cehyPwknDEewsvGn4b8O0HAiscRin3blmUgVPQAAAEmSURBVO8OosdRoGIGJMz4Qfnu'
        'mP6If4ztkybH9EnzYgZk2ccHsZbjSkwTM4CpjitlmphBTHG8H8s63i85daxXduR4X8Qjx7ql8pg+wa6jzcyvLR/Xe5pzY78NT8sRqoTYwfDr8UPhZMwARqAA'
        'r4eYAQxiB8MhZ/QJKDQexsvcdwkBixsKCDqH6zuPG9Iv/EYygiZb3xm1gE/403L0VA8WGTccMRM/FAHHB+SemAE5vh6OD2B4jDIcz9E/fqPcdRQKxg5Snzm4'
        'Oxt8cqErna30/yv/CM4GXx94W9jK/qf+iMdihyLmE0f3wgndHvLEyB5YDwm6Pei1eMnUYSi0PVkcQrv+mzXwrY765D841ifPP9Yvzz3Wh+X5g6e7xblxqr2F'
        '2YbHw/8LaPyHCKFzpKkAAAAASUVORK5CYII='
    ),
    'assets/badges/official/revit.png': (
        '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'
    ),
    'assets/badges/official/sap.png': (
        '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'
    ),
    'assets/badges/official/sharepoint.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAgAElEQVR4nO2dd3Sd1Znu9+nqknvHYJtOgMCQQiZtMpnc'
        'de/cm8Ikk2EmFGNsjDEYbOOObLlbvXcd9d57r0flSEfn6BQ1FyC9TzIhZBKKf3ft73zHku1kEsICDPG71rM+ocUfnN9+9Oz32++WEOJ6Xa/rdb2u1/W6Xtfr'
        'el2v63W93sfyP+tcHTAzsyloZion1OMZXOCe/P5S1+RrK1yTb61yTr51g9P92xsnJn+8zuGx32T3VK23Te7aYLOtv75I76ZmZhYbZ2d3maanJvynJgmanCTE'
        'M0mYe5JFLjdLnR5WTHhY7fCw1uFhvWOSWyamuMMxxd0TM9znmOVex+yrd1k9cXf2uddcX4y/tM6512hePp+on53+nXF2Gr+pSQI8HoJcHkKcbhY4XSyacLPU'
        '4WaF3c3qcTdrx92sH/dwy/gkd9inuNsxrSzAJybO8pmJ83x24sIbD4xNN987cvaO6wvxp8pmM4iXzz+nOTf7mvbsLPqZaYxTHkweDwEuF0ETTkIcLsLsLhbZ'
        'J1g67mSFzclqm5O1NifrbW5usbm5wzbJ3eNT3Dc+zSccZ3lw4hyfd17gS86X+SfXq29+enSm/I4eT9D1hZhfL798q7hwbkKcO4tmdgbt9BR6jwejy4XJ5cZ/'
        'wkmQw0nIuIMwm4NFYw6WjjlYMTrB6tEJ1o5OsG50gltGXdw+6uZjY5N83DbFA+MzfNo+y2ft5/ii4wJfdr7K/3J9ly/azv3k3kH3g9cXQdarFx4SF869Js7N'
        'ImZn0MxMo/V40LvcGJxOTPYJ/O0OAm0OgsfshI3aWWgdZ4nVzvIRO6uG7dxgdXDTiIObR5zcZnVxl9XFvaMe7h+b4pO2GT4zPsvnx8/yD/YL/KP9Al+2X+Af'
        'bOfeuLt7/IW/7UV45fxj4vzZN8XZWcTMNGJqCo3Hg9blQjfhxGCfwDRmx39snMDRcYKtNkJHbCwcsbFk2MayIRsrh8ZZM2jjxiE7G4Yc3Drk4M5hJ3ePuPj4'
        'iIcHRib51Og0nxmd5nNjs3xB0Vm+YJ3hc4OTF+/qsEaKv8l6eXaLOH9Wcb2YnkZMTiLcHoTThdYxgW7cgcE2jtE6jt/IGAEjNoKHxggdHGPB4CiLLaMstYyy'
        'YmCM1ZYx1lpsrBsY52bLOLdb7NxlcXDPkJP7hlw8MOzmU8OTPDgyyWeGJ/l7qSEPD1pcfHrAye1NgzHib6ounH1InJ15ywt/ygvf5UZMOBH2CTQ2O7qxcfTW'
        'MYwjNvyGrARYrARZrIT0jxDWP8KivhGW9I+wvG+EVX1Wbugb5aa+MTb0j3Frn407Buzc1W/nngEH9w1M8HcWJ5+wOPnkgJNP9nv1iV4HD/Taua/LdnF9bd82'
        '8TdR585tELMz/+WLHOHxzIPvQIzZ0VhtaEfG0A9ZMQxaMVmG8R8YIbB/mODeYUJ7BlnYM8TiniGW9QyxonuY1T0jrO2xsq7byobuUW7tGeWOnjHu6rVxd+84'
        '9/aOc1+vnfuluu3c3zPOfd3jfLxrlHs6rNzVOvz7Gyu6Pyk+0uXxGMXZ6QkF/rzIEQ4nYlzCH0dYbWiGRtFarOgGRjD0D2PqG8SvZ5CA7kGCui2EdFpY0Glh'
        'UYeFJZ0WlndYWNk5yJqOQdZ2DrGuc5gNHSPc2mXl9k4rd3Za+ViXlbs7R7nHp45R7m638rH2EQmfO5oH2VDX+8qG5maT+MjWzMzeS5Hjlq53KZEjbA7E6Dhi'
        'ZAwxNIqwjKDpH0bXN4S+exBj1wB+XRb8OwcI7OgnuL2f0PY+Frb1s7i1j6Wt/axoHWBV2wBr2izc2GZhXesgG1oHuaVtiNtah7hdQm4d5s62Ie5sG+bO1iHu'
        'aBnk9uZBbmuycGtDHzfX97K6pC1WfCRrdnaVmJr67eWRI+HbFdeL4THEoBUxMILoG0LTM4i2ewB9Vz+Gjn5M7f34tfUS0NpLUGsvIS09hLX0sLClh8VNfSxr'
        '6mVFUx+rmnpZ09TP2qZ+bmrqZ31jPxua+rm5cYBbmi3cKmE3DXjV0M8tDf0K+PU1vayr7uKGys7/XlrUuE585GrKE3d15PjgS9dbEf3DiN4hRLcF0TWAtr0P'
        'XVsf+tYejM09mJq68W/sJrCxi+CGTkIbu1nQ0Mmi+i6W1HexrK6bFXXdrKrrZnVdNzfU9XBjbQ831fewrq6X9Q29rK/vZYNUXQ/ra3tYV9vNTdVd3FjVwdrK'
        'dtaUtbEsr6FYfKRqamqRcLtfV+BfFjm2S5HjhT+I6LIgOvoRbX1oWnvQNnWjb+rC0NiFsaETv7pOAuo6CKzrILi2g9DadhbUdLCotp0l1e0sre5geVUHK6s6'
        'WFXdyZrqTm6o7mBtdSc3StA+VXWq0Du4obydNeVtrC5tYWVxM8sL6n6/MLd8lfjIlMv17GWRI+ErkTN6KXJEj4Q/oMLvRTT3IJq60TZ0oqvrQF/bjqG2HVNN'
        'K37VbQRUtRJU2UJwRQuhFa0sqGhhYXkri8tbWFrWwrKyVpaXt7KyvI1VFW2srmxndUUbayTsitZLwFeXNLOqWIJvYkVBI8vz6llqrmNBZsVR8ZEpx8TY5ZHj'
        'y/t5kdM5gGjvQ7RK+N2Ixi5EXQea2na01W3oqtrQV7ZgLG/GVNaMf1kTAaVNBBU3ElzcSGhRI2FFjSwsaWRRcRNLiptYWtzEsuImlpc0s0ICLmliZUmz4vKV'
        'hY2sKJTQG1heUM+yfC/4JTm1LM6qIiytfFZ8JMpmWyHG7Bcvjxxf3g964auRI1q8rhcNnQp8UdOGqGxBU9GCtqwJXWkjhpJGjCX1mIrq8S+sJ6CglqCCeoLz'
        'awnJryMsv44F+fUszK9jUUE9iwvqWZJfx9L8Bpbm17NMws71amluraIlOTUsya5mcXYVi9LLWZBeRlhq2UW/yKy14kNfNvvDl1rMS5EzfHXkSPjS9fWdiNp2'
        'RLUXvihvRpQ2oiluQFtQhz6/BkN+NcbcGky5NfibqwjIriQwp5Kg7CpCcqoJzakmzFzDAnM1C801ihZlV7PIXMPibJ+qWJxVzaKsShZllLMwvYIFqWWEpRQT'
        'mlhMSEIx/tH5z4gPfY3Y4q9sMf9k5NRL17cjqloRFS0KeFHciMivQ+RWozFXo82pRJ9ViSGzAmN6Oab0CvzSy/FPryAgvZygzHKCMysIyaggJLOS0IxywtIr'
        'FC3IKPcqrZwFqRUsSClVFJZUQmhiEaEJxYTEFxAcV0BQTD7+Z8wfgW5oaLTtqhaz83+IHAm/vMkLvrAekVeLMFcjsivRZJSjSStDm1KKLrkEfUopxuQSTKnF'
        '+KWW4J9SSkBKCYGKSglKLSE4pZTg5BJCkksJSS4hNKnIq8QiQhKKFOAhsfkEx+QRFJ1PUGQugZFmAk5nYzqZNSI+9DUwfGEuciyXR07TFZFT0Ywoa0YUNyAK'
        '6hB5NYicakRmBSKtDJFSgiaxCE1CEdqEQnQJRejjCzAkFGJMKMIUX4hfQiH+igoIiC8gUFWQdHVs/pwU4HkERZkJjMwh8EyOAj3gZBb+JzLxO56O8Wjqj8SH'
        'vnoHf6nAVyKn/09ETosXfInq+nzp+hrF9SK9DJFaikgqRiQUIuIKEDF5aGLy0MbkoovOQx+bjz46D0N0HsZoM6boXPyizfhFmfGPylEUIF19JpuASAk6iwAJ'
        '/FQWAScz8T+Zgf+xDPyOpuMXkYbpcCrGwykYDyX+l/jQV/fAHy7l/ZWR49toy9Ssl67PrUXkVCEyVNcnlyASi1Tw+YjoXMSZXERkDprTOWhPZaM9k43udDb6'
        'U1mKDKeyMEqdzMB0MhPTyQz8TmTgd1wqHb9jUmleRaRiOpyiyBiejDE8CcOhRAwH49EfiH9DfOiro+8Pc3nf5YUvI0fJetnhNCGK6r3wlaxX4aeUIhJLEHGF'
        'iuNFVC4iyow4k404lY04mYU4kYE4lo7mWBraoxloj6Wji0hFfzQVfUQqhiOpGI4mY4hIxXgkBeORZK8Oq4pIwZRSjH9NG0G9w4SNu1jsnmLF1Ayr3NPcMDHF'
        'TZ6zr6x3n+tf7zoXt27y/JfEh65aen6pvNXOjxxfe6lkff3lWS8jJ7kYEV+IiFUdH2VGRGYjTvvAZyrgRUQaIiIVEZ6C5nASmpeS0b6UpEh3KAndS4mK9Iek'
        'Erw6EI8uMgdDUxdGeePi7CxBMzOETs+wcHKaJZMzrPDMssYzy02eWW72nON2zznunrzA/VOvcL/75V/c434l9/bxlz8k7wiN3edFg/etVlTPby8l/FpEbg0i'
        'S2Z9uTfrEyV8GTcFXtdH5syBP56BOCrBpyIOpyDCkxCHkhAHExEHEhD74hD749Hsj0WzPw6t1J5YtPti0O6NQXc0FW1HL7rzsxjOzmCanSFgeoagqRlCPdMs'
        'dE+x1D3NCvc0a9wz3OSa5WbXWW53nedu9wUJn09Nvspnp7/PF2d+8ManXK/U3W+bWSyu6WroaJuLnKa5jdbXXvrgJ5UgEooQMYWq483zHJ+hOj4VcUTCl+CT'
        'EYcSEfsTEAfiEftiEXtivNodjdgdpUizKwrN7kg0+dWI2Vk058+im53FMDODaXoG/8lJgtxThLonWeiaYolzmhXOKVZPTHPjxAw3O2e53XmOu13nuc/9Mp/0'
        'vMrfT36PL07+gH+a+SFfnvrha/ePn98irtmqbku4lPclaocjIydLZr3q+uQiRLyELzdYNedPZqpRk6GCl45PRrwkHS+hJyD2x82Bf1GCj0LsikTsPIN44Qzi'
        '+VOIF6O8HdiF84jz59CcnUU3M4NhegqTexJ/l7x1N0mo08PCiUmWODwsn5hktWOKGx3TbHDMcNvEWe6aOMfHned5wHWBB12v8DnP9/iHye/z5ckf8GXP9y/e'
        'bz1fKkArrrmqbHpYiZwiNXJ8rk8rV/p6kVCMiMtHROV74+ZU1lzcKBmfgjgswUvHS/CJKvg41fHRV4A/hXj+NGLHKcTeaMSIFXHhHPLSl/ITMD2DbnIavXsS'
        'o2sSf6ebwAk3IQ4PC+xuFts9LBv3sGp8krXjU6yzT3GLfYY77DPc4zjL/RPn+eTEBR50vsJnXd/l885X+YLzVT4/8Qr3Dk/33SHHrtdUmRuXi4K6i96NtgqR'
        'KeFL10v4ssPJV+Mm5+oNVub8JfAJSr7/UfDS7S+c9jp+x0nEc8cRO097D/3On0Oc9cIX0zNoJqfQujzonW6MDjd+dheBdjfBNhdhNheLxpwsHXWxcszNmlEP'
        'N4162DA2xW1j09w1PsO947PcP36WT9jP82nHBR60q7Kd51Nj57ir390vwsOvsZ+E3Npxb+T4XqpkX692OL5NVjpfiRu1s1GiJtEbN/tV8Ht9GS/BR6mOV92+'
        '4wTi2ROI7ce86upX4ctLXzOIqWmEZwrh9KCd8KB3uDHYXfiNOwkYmyBo1EGo1cFCq5MlVifLrU5WWV2stbpYZ3Vzi9XD7dYp7hqd5p7RGe4bneHvRs/ywOis'
        'V9YZ7h+a4uODHjZ0jmWIa6qySnYpG21yqXejjZUdTp7X+adU18vu5ojqetnZyA1W2VzjveD3xl4RNarjn5sH/hmpowhz+aXIka4Xkyp81yRiwo3G7kJnc2IY'
        'm8BkdeA/4iBwxEHI8AQLhu0sGrKzdMjBiqEJ1gw6uXHYxfohN7cMe7h92M2dw5N8bHiSe4anuHdIapJ7Bz3cPeDmY31O7ui2v31D0/BD4pqplPylIrn49Uu9'
        '/fzIOS7hS9enqW1l4tVx86IKfteVUTMP/LajiKePIPbHeG/azYfvnlScLxxuxLgLjc2FdnQC/YgD44gDv6FxAobsBFtshFrGWWgZZ4nFzjKLnZUWO2sGHNxo'
        'mWC9xcnNA05uHXBxu8XFHRY3dw64uLPfyZ0SfM8Et3XZuaXdxrqWkZ8sa5sIFNdMxRelX+pyZOScUOFL8LLDkZHjy/p9vu7Gl/Nn1Jz/E+B98Lce9h70zY8c'
        '1+XwxZgTYXWgHbajGx7HMDiOyWLDf8BGYP8YIX1jhPWNsah3jCV9Npb32VjZO86avnHW9o1zU5+d9b0Obu51cEuPg1t77NzabefWrnFu6bSxoW2U9S3D3NQ4'
        'xPKqnjhxzVRS5Vpxxvw7Bf5xdaNVenoVvvIyNa+7Ufr4ea7fIcGfvDxqno6YA78lHHEoDuGZ9IKf73q7C2FzIkYnECMOxLAdzeA4WosN/cAYxv5R/PqsBPSM'
        'EtQ9SkjPKAu6rSzqHmVJ1yjLu0ZZ2TXG6q5Rbuga48ZOGzd12VjXaWNdh4317WOsa7VK13Nj0xBrGyysqetnZWXXb0IbBxaIa6Yic45d6nIU+OrL1IH58K9o'
        'K+d3NttV8NvmgX8qHLH5EOLJQ4iqZoTDd+3FibBNIMYciuMV8FJDdoTFhugbRds7iq7HiqHHiql7BL+uEQI6RwjqGCG0Y5gFHSMs6hhhSfsIyzpGWNE+wsp2'
        'K6vbrKxptXKDVMsIa5uHuaFpkBsk+Pp+VtX0srKqm+VlHSwsajokrpkKDzeKY+nTc/CT1I1Wwp/3MnXlJrv9GOLZea7fesQL/qmXvOA3HURsO4KwjnsH/775'
        '8/A4YtCGsIwhBuRQaBTRK2VFdI+g6RpB2zWCvnMYQ8cQpvYh/NuGCGwbIrhtiJCWIcJahljYPMji5iGWNg+yrGmI5c1DrGgaYmWjhVX1A4pW1vazsqaXFRJ8'
        'RSfLSttYUtzKwrxG9/vOObBn/NshHbaRkNaR34Q2Wy6GNvQTUtNNSFU7weUtBCu3GeoJKqghKLeKIHMFQdnlBGWUEZRRQlB6KcHpJQSnlRKSLlVGaEYloZlV'
        'hKRVEhhdgF7+hGw6hHjiIOKJfYgTKYghOfoc8wLvtyL65Ah0BNErB0LDiK5hROcQomMQ0T6IaLOgabWgax1E32LB2GLB1GLBv7mfwKYBgpoGCGm0ENY4wIIG'
        'C4vqB1hcP8CS+n6W1vWxrKaXZbW9LKvqZllVF0srOlla1q6AX1TYxML8RhaY6wjLanyfDu48HmNw93h7WOcYoa3DhMgPUN9DcHWHcocnqLSJwOI6AgtqCMir'
        'JCCnnICsUgIyiglIKyQgpYCApDwCEvMITMwlMMFMUHwuQQm5BCfkE5JU6B0rppYTlllFgIyzjfsRj+9D5JR7R57KTQt1+tY5iOiwINotiLYBREv/nJr6EE39'
        'iIZeNA296Bp60df3YWzow1Tfh399HwF1fQTV9hJc20tobS9hNb0sqO5lYXUPiyq7WVTZxeLyTkWLStpYVNzCwqJmFuY3EZZbT2hOLSEZ1QQllz31vvAP6hpv'
        'De2wEtI6SHBjH8G1XQRVtRFY3kRAST0BRTX451fiby7DL7sEv4wi/NLy8UvJwy/JjF9CNn5xmfjFZOAfnY5/VDoBUpHpBEZlEBSdRXBMDsFxeYTIIXpKKf6y'
        'hX18r3ec2SEHPwOINgm5D9Esp28SdC+isQfR0IOo70HUdSPquhA1qqq70FZ3oavpRl/VhaGqB1NVN36VXfhXdRNY1U1QZRfBFV2ElHcSWt5JWGkHYaXthBW3'
        'ElbUQlhBE2F5jYT6wGdVE5xeQVBKGf7xRe/9i1lgq+VfQ9uGCWkeILihh6DaTgKrWgioaMS/pA7/gir88iswmUsxZRVjSi/EmJaHMdmMMTEbY1wmxuh0jFGp'
        'mM6kYDqdhOlUIn4nEvE/noD/8UQCTiYTeDKFoNPpBEdlEhJjJjS+EP0zEd5Bj5y2KRM3OXuQR+By+NOJqOlEVMu5szwS70BUtiMq2hHlHYjydkRZO6K0FW1Z'
        'O7rSdvRlbRjK2jGWd2Aqbce/rJ2A0g4CS9oJLGkjqLiV4MJmgguaCM5vJDi3gWBzHcHZtQRnVROUXklgajkBSaUSPn6x+d3v/QI0DAxK1wfVdxJY00ZAZTP+'
        '5Q34ldRiKqzClF+O0VyKIasIQ0YBhrQ89Mlm9AlZ6OMy0EenoY9MQX86CcPJBAzH4zEcjcEYEYMpIhrT4Rj8jsTgHxFLQEQ8gceTCDqZQvCZLPzDExC16rBH'
        'gq6So0519lAhT2Ll2LPVq9IWRImUHAg1I4qaEYXNiAL5bEFT2IK2oAVdQTP6whYMhS0YC1swFbTgV9iMf34zAXlNBOQ2EGCuIzCnjsCsGgIzqghIryQgtQL/'
        '5DL8E4rxiyvEJOfUZ8zv/UYcVN/1q6DaDq/ryxvwL63Dr6RGgW/ML8dgLkWfXYw+sxBdWh66ZDPaxBy08ZloY9LRRqWgPZ2E9kQCumNx6CJi0B+JQh8eieHQ'
        'GYyHTmM6eAa/g6fxPxRJwEtRBB6OI+hoIkHHkr2Q5ZF3mTrmLFGvthTJ+YOcNzcgCuWJbAMiTx6Ly2cDwlyPyFWfZu9TY65Ha25Al9OAPqceg7kBQ04dxpw6'
        'TNle+WXW4JdRjV9aJX7plfillOOXXIafvJ0RV4gxOh/jmVwMp7PRncx8+b1fgOq2twMq5J1N1fVF1RgLKzHkVaDPLUWXXYI2swhtej6a1Dw0SWa0SWbuKaxi'
        'a+cAR4bG2NLaw2fzK9EfjUNzOArtS2fQHjiNbt9J9PtOYNh7HOPe45j2nsBv30n8958m4GA0QUfi58abyohTXmmRA/4a75Bf3rAwy2F/LSK7FpEl5xHVlz8z'
        'axAZNYj0akWatBo0GdVo06vRZVShS6tGn1aFIbUSQ1qFImNKBcakMoyJJRjjijDGFmKIyccQmYteXhI4kYVOzqrDU977BQgob8K/tN7r+qJqDAWV6PPK0JlL'
        '0eaUoMkuRpNZhEgvQKTk8UzfCL/+/R/4Y/X6G28SOTiG5tBpNPtPotlzHO2LR9HtPoJ+1xEMuyIw7TqK355j+O89QcCBM17YOepQP0s99s6Q0zY5Z5ZH4BVz'
        'Sp33TKlEpFQgkn2qRCTJCV05IrEMTVIFmsRStMnlaBNL0SWVokuQKkYfV4Q+rhB9TD76qDz0kbnoTpnRSfDHMtBGpEn4aPYnTrznC+BfXItfYTXGgkoM+eVe'
        '1+eq8LOKET74qXlUnn+Vv6TcP/kZuv0nES8eQ7PzCNrnD6N7/iX0O17C8PwhjM8fxm/nEfx3H2fzf/+aJ17/FQ//6mf883e/y4MTHta19uOXXY1IVG9YJEiV'
        'zkl+L179XryquGJErBwSlSBi5cmtOiaNLkQTU4AmJh9NdD7aKFVnctGeykV7MgftiSzldoYmIh2NBC9fNL1HK83v+QL4FVRhyivDkFuK3lyCLqdYcb3ILpkH'
        'P5+neod5J5UnD9B2HUW8cBjx3Etoth9At/0A+u0HMGw/gOm5Q/jtOMzG3/2aR3/7K/7jtf/k3/7rl3zr17/goV/9nK/+/Kd8YmKShXIfkIP+aJ/k7Llw7ql8'
        'LY/JVUUWIM7kexWZhziThzidizhtRpzMUSUPFbMRR+UcIwMRnqaeayWph4rxiD3KMfp7/3tnptwyDDml6HOK0WUVe10vlVF4yfkiOZcf/fb1ywD/+Lev89mi'
        'KhbHZvLFgkq+9+vfKN+/ePEirWcvsOpYPGJnBOL5cMSzhxDbDqB5eh+6rXvRP70Xw7b9mLYfuAr81375M/7vL37K//7ZT/jKT3/MP/74R9w96sQ/sQxxMhdx'
        'Khdx0qw+5T+b557ye6ckYBX2CSl5iKie4h5TZ9XKDCPdCz7cd6iY5L0osDfOe7SyKxrxQtS/v+cLYPR1OJmFaDIK5sCn5SuZL5LNiMQc3r548bIF+D8VDYgT'
        'CYhjcYgjsuWMJc/uYc3pJMSe44jd0v1HFPeL7QcRT+9HbNmDZvNudFt2o9/yIsate/5H8F/80Q/53A9+wGe+/wMeuPCKckwgIrJUZSOOZSGOZqnPzHnKUEGr'
        'Uo7O5dBo/kmu76JA4hx4OTySJ7pyaieP0bedXvmeL4AhIx9dej7atDwlaubA5yKSzIiEbER81lURkywjRro8IhZxOBpxKBJxQA7UTyjZf5n7nzmA2LoXsflF'
        'xKZdaJ94Ad2mnRg27/qz4D/1ve/zwKvf475Xvss9F15lWV0P4rAaG4dkdKgKv0IvScjyRoYqH3B5LcYXNb7Jne+GhrwWszMS8fwZeYQ+LN6P0qfkok3NRSOB'
        'p+R6HS/BJ+Yo4EVcJiImg9+/9dZVi3D2l7/itGWMW+UiHTyN2HfS6/552S987n9qD+LJ3YiNO9E8vgPt48+j3/jCXwz+rvOvcNvZl7l59gILytsQB1MQB5IR'
        'B2R0qDow76lA9h2ZS5fPn9j5ZtWx3rh5MfryY3RlfnHy/fkTCDr5UiVhS4i+pw98bAYiOh0RlUrHq9//Hzfd373xJlXuGcLkT8LOI4gdc9k/3/3i8RcQjz6H'
        '9tHn0D264x2BXzdznrVT51g9eRb/tErE3kTEXhkfctOMR7woOxf59fynVOzcUwGuQpeO993OkFdinjuFeFYZHv1SPB3+/vxxKF1cBpr4zHnQvY73gk9DRKYi'
        'TicTFpvJf/2J/n9+vfHWW/xzZrHX/c8cQDy9T8l+n/vFYzsQ33kWzXe2o/vOM+8Y/Ar3LEtdMyy0edAeyUDsjkPsjkXsktkdi9gpY0SCnaed6m2MS7cy5kFX'
        '7iKdVG9nHPdO7Z46elC8XyWPEzQx6QgpH/SoVERkigJenEpCnExEHE9gYVQaYz/6yZ9dhLfefpsNcm/YJqNHdf8TOxGPP4945DnEf2xH8/AzaP992zsGv2hi'
        'mjDHFMHjk5jqexEvRM/peZnfkYgdkYjnJOAziB2q5NcKbB90NWrkzQwp35x665GXxTef93//FkCCPpPidbp8nrkCvNLpxCOOxirdjtxwb4hJJ23UwfTPfsEf'
        '/sjeIKv//Cve6NmiRs9GGT1e94uHtyG+vRXtt7f+VeADbB5MY270VhfieJYXtk/PnvZq+ynEM6fUpwStxotyFUbVM8fVywHqqPSpw2+JzUfe36vsWh9o5TkP'
        '+nEf+DhEhBe8CI/ydjtyw5VvumrH83BR9VUL8dvf/2EueqT7H5Pufxbx788g/u1pxLeeUhbgrwWvGXEihpze499k7A8AAAcOSURBVOlnVdgStNS2E6qOI56W'
        'OubVNp/kiNQ3Jo1APHUEseUw4smD7/8veWuPx3tBy6fydZwKfc7xCviXItEeiuRLOSXebmfvcW+7uStC6XhOdPZftgBvvvX2HPx50aO4/1+3Ir65Be03N//1'
        '4AcnEBYHom/cm/ESuIS9VdVTR1VFILZEqE/pcvVrBXq4V5vD5Yz6g/nNSu2xWC9sRTFz0K8Av7u1h9/8wbsJf7ukxvuiJXt92W7uCCeud+jqn4AnfF3P5dEj'
        'vrUF8dCTygL81eD77V74vTbvZbFLwI96gUttPuLVk+GITYe9kl8/+RJik/p84hBi46EK8fnP6z+YBTgcNQdbBa7o0Blv1Bw4xeRPf34ZXPlO3DA5y1fSC7kv'
        'MpXw5m7efPvty/6d8e/+4PLcnxc94l82Ix7ahPahJ98d+J4xRNcoIrN6DrYC/IgXsAJdPsNV0D7gB1UduCg2HpDnPRrxQZXupTNoFNg+4F7oYv8pNWpOsKW6'
        'mXdaX5Sb+WNXwP/XpxDf3Iz4xiY0X38C3UOb3h34TiuiYwRR2jbncAV2uBf2RhX644cQjx1EPHbAq0f3Ix7b/1Px2L5vfGDgLy3AoVNoDqiwFZ3wbq571IxX'
        'cv4o+5u7lYO2v6RS5O0GCf8RH/y53JfRI772xKUFeFfg24YRrUOI2h4VuAr98YPzoEvtRzx6APHIPqnficf2Zohv7gkV10LpD5xEu+8EGt+mKiXzXR4nyA1W'
        'vtXKnH8+nPsi0xh6+XtXHcz56hevvc7GnNIrYmfb5fC//gSar21E+/WN6P9l07sD3zKIaBpAI98HFOgHL3f6I/u9+s4+qR+Kx/YniM37V4hrqQz7jr2l23MU'
        'zYvqpqoAn4OuHCnIt1p5rCDPdZ45QNjOCL4Qm8HW4hoO1bXxuLmMOw6dQXNV5m+7Cr746uPKAui+sRHDtzb/9eCbLYiGfjT1fWiqOy+KRw+8Lh7d/7Z45MAb'
        '4pF9r4lH970svrO3Wzyy/7R4bPdnxbVa+r0nfqrffRTtziNodswDfgV05UxHHqrJlyt5sCbfbn1tpgSv9PnPXZH5W6+G/9XH0X5tI/qHNimHcX8V+MYBRH0v'
        'mroeCR9tZfvPxYe1DHuONxh2R6B/IRztDjm5Ong1dHmeo7zVzgOvvN2qPf6jat77+vxLG+6Wy+H/Pwn/cfRfl+7fgl7OhN8p+IY+NPUSfDfaqk60FW1oS1vt'
        '4sNapt3Hv2TcHXHR8EI4uucOod1+EI08w9m6z3uOI93+R8FL1++43PWX+ny123noaufrFPibMT78NFr5a69/Mfh+RF0vmppuNFVdaCs70Ja1oituQldYXyI+'
        'zGXcFVFo3HkYw3MH0T2zH+3Te9Eo0HfPQfdFjXS8BP+oCv4y16svWbLP/8YmpduZg/84um88geGbXvj6w7HvHLy8iljZibasDW1JM7qiRnQF8i5Q7ftzh/M9'
        'q/R0g3FneKFxRziGZ/ej37oX3ZY9aDfvRvOEhK5mvBI188D7NtpLrlcjR4G/Ec1XN15yvV7Cl87/t21e+BL4nwNf36e0mJrqHjQybsrb0Za0olVc34Autw5d'
        'TvWbIqv2vR8dvh9lem7/VwzPHKzXb9v3Y/1Te97SPSnHhzuV6ZXmsecQj2xXHT8PvC/rfa7/huzxN6H9xhOKpOv139yMXk7A9pxGK/+K1l8Evhehxo1Gxk1p'
        'G9riZnSFjejy6tGZa9BlV6LPrOgQf+ultzo/967aycYrwfeo4H1x04K2qAldfj263Fp0OVUSPPo05S9w/dMH/fmvjRqcaHr34HsRVdL1nWjK2mV3442bggZ0'
        'ebXozNVe16eXoU8tRp9U9N7fXv7QlMW2XvTZXntX4Cu70JSrcVPSjFaJmzpv3ORUocuQri9Bn1yEPiH/dWOU+bYP+mNfW9Vle/gdg6/uQci4Ke9Ao8RNK9rC'
        'JrSX4qYaXaZ0fSn6lGL0iQXo43MvauPzN3/QH/farPaR8L8cfDeiogNNaTsaGTdFzWjzG9XupgZdlnS9jJsSGTfS9ejjctHF5kd90B/z2q7mwT1/HnyXkvMa'
        'tbvRFjSiVbqbWnRZlejkJitdn1yMPqFAAa+PyUEXk532QX+8D0fV9z4s6nt/88fAizLp+lY0RVfETXaVF750fYp0fSH6+Dwv/Oic17Vncq7hP7B0LVblwDpR'
        '3dN4CXy5GjfFLWgLfa73xY10fTm6VOn6ojnXR+egi8zqNZ7KvP2D/jgf3irv+HtR0l6vKWp5UyNzvqBJiRutWXV9RgW6tDJ1k5Wuz0Ufa35TH2Xu0kXlfOWD'
        '/s//6FRx5zJtQdMmjbm2WJtZPaHLqPqlLr3iDV1KyRv6xKL/1CXkubUxuVXaGPN2EZ37EfofMVyv63W9rtf1ul7X63pdr+t1vcTfUP1/aKMAEe/5DH0AAAAA'
        'SUVORK5CYII='
    ),
    'assets/badges/official/stream.png': (
        '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'
        '17Sk3LYAAAAASUVORK5CYII='
    ),
    'assets/badges/official/sway.png': (
        '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'
    ),
    'assets/badges/official/teams.png': (
        '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'
    ),
    'assets/badges/official/todo.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAEp0lEQVR4nO2YS2wbVRSGp0VsEKwAeShFFKMiYFOJbd3G'
        'duzaSSaJk2BbngXs+thRVoCEskeUOM/m0UlqEietaxvEClGPKlGJDcoCIQQ7hCgrYDVWq7r36qA7M7cJpYWG2vf4cT7pl5ee+b7xeGxNIwiCIAiCIAiCIAiC'
        'IAiCIAjt5BI8nqnAG9nP4NjI5/AUKVFIpgxHM2X2a6bCIVvhkKmwerrKTqs8hp4lXYJQpswcIV9ORMhWxSv7APv4ul5+usycdJlDRowiKJZ/hTnpKxxEAIqg'
        'WP5EyZcvRxHUyn+zxEGMIiiWP35pRz5FQJA/cZmDGEVQSErI32LOxCVPPkVQSKoIobFN5owL+XJNipCpsvdVnkvnyt/i4I4iqJWfKu6STxHUyx/b5CBGERQy'
        'un4nnCqy+ljRk68yQrbK0lovM+rLTxU5iKmOkKmyb7Welr/B6qkNTz5OBHZT61X5o+usPirky6FEYD8oOeGDb9WeD5j2om7a3+mm/Y2eu/quli49pmHKX+fg'
        'DjFCusLOtvyED2SvvhLI2Td004a/LVerPXfyiyc0xfJHCqw+8qkvHzeCpQHsa+kJP5P76vB95fsL5Oyvn01fe1JTgFGA0HCBOUK+HGKE1clJ2I8qX2UEowAh'
        '4yJzRgo78hEjtI98FREMIX+NOcMFDmKYESYut6H8VkYwLAgNCfkXObhDjNDW8lsRwfDlG2scDBkAKcJ4J8hvZgRjt3w5pAgdJb8ZEQwLQoOrzBla3SUfKcL4'
        'VgfKf5QISSHf8uTLoUXYVCD/gT+yECIkffmDFochMcwIquTrpv1bq+Tre4jgyr/gyZfDipDqJvn6Q0RILkFoQMi/wMEdYgQl8nXTflGlfP3uava9/x258leY'
        'M7DCYUAGwIqwoUC+IGDWyurl2/+IIOQnl335clgRVMnXNNgXMO0/8QLY7u0omr8VF/KTyxzEkCOoku8RMGu/YwZ4+cw2nFhoMCkfOYJa+QLdtEuY8uMLDUgs'
        'cUiK4UZQL19wIPvlC6189v9X+fMNSCxyNwBmhOECknxJIHvtkG7WflYlP3hmG2Jzvnw5pAjo8lVHCPryT5zn7pAjtId8VRGCp7ehf3ZHPmqEtTaT3+oIQV9+'
        'fIG7w4ww1K7yWxUhKOTPNCA+78nHjND28psdQciPTjcgJuTL4UWwOkJ+syLclT/HvSFGGLQ6TP6jRhDyI/kG9Ev5c3gROlb+/40QPOXLn+Xe5lAjdLb8vUYQ'
        '8sNTDeif8eVjRljpEvkPG0HKj85wd6gRVrpM/n9FEPf8PiF/2pOPGmG5S+U/KMLBt69D37nbEJnm7jAjJLpd/v0ivH72J4jkuTfECIlekX9vhCPv/bITAClC'
        'YrHH5O+O8No7P/4RnuJ4ERZ7VL7k0Knvjxz96OatpkSY33OE3pYvOZ6Hw31T7IbKCPHzJB8tQpzk430SYvN05aPdjmIkH+87IUbyUSNY9LSDFWGW5KNFiJJ8'
        'vAhRko8awaJ7Pl4Ei+QjRQjnSb4Sjs3AS+FP2HUZIZxntyN59iFd+QqZnIT9fR/Dq8fP3Yn0z8LTKt+bIAiCIAiCIAiCIAiCIAiC0FrAXzTdwgFSF4i7AAAA'
        'AElFTkSuQmCC'
    ),
    'assets/badges/official/visio.png': (
        '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'
        'LAAAAABJRU5ErkJggg=='
    ),
    'assets/badges/official/visualstudio.png': (
        'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAB2HAAAdhwGP5fFlAAAMF0lEQVR4nO2caVRTZxqA02XamXZO22lnn3ZOe2b6Y850'
        'pq1WqlZFXABrkTUgO5IQxCAoKAqiEbITkpAQloQliNYqTl1Ysi+AWgIJEK3dplqLFZfRqllqqxbeOZceLSLEJDcmAvc55/mneb/vey4XLsbgcBgYGBgYGBgY'
        'GBgYGBgYGBgYGBgYGFMYAdEwuy7b3HWANnBDJ7o6dJA2eHFX7slCX69rWsCO167gEzu/L0s7DIjSvONwRGIfUca+ZG/MOVVCwcGjvl7nlISV1OHHI3TaytI6'
        'YbSqskt3IiDKSy/d2JH7pZRCOfGEr9c8ZWAlqv7BS+28zCd2wlhb2YNwRGy/RxXv21vvbzzZJFpz4te+Xv+khr1S9WduSvvXfEInjGcraxAOi+0TquZf+XH3'
        'xq9kYtLnv/X1XiYdLLz62ZLk9k94qZ0wkSMBqu33VSe8OrQ3f6BLmv3Zy77e16SAgm96gpOkP8Jd1QGObGEOwuEqu9PqhJbhPflnjPVZJ1/19R4fWprwTY+V'
        'JOha7nf4twN0VtldFgmxO+8rdRMe+2Z9DyVxurrSlA5wxhbGWeistLvtvsIzX9y7gmkMK0FPL01uB2dtpqMLgNi4/qskX+/7oYC+UkPmJOmHOUnt4KwjASrs'
        'qFRxrwpx0x1mXDu+JLH9FiexHVzxEO0sdFTYUakts+7CTWfosSp/doLuekmiHlx1JIDIjkqdwL4TN11hRcr/yY7Xf8tO0IM7HqKiD9AutDX69BAKwj/8EzVS'
        'sU9I6Lpem3UMBISu77eHybMf9FwW/vBfWXG6QXa8Htz1YPFZaC+3o9NXAQqCD4YzV+o/EZP7huuyj8NoazL7h4RphrwHNZuCVzzPjNV9jubwPRVAV+blAIUr'
        'ZKm8pCPXarKOQ+19lGQer9RT9I97cj4nQfk0I0ZrZMXpAK2TLkDBe83LBISjQwLiEXAmwEgEsrm9hnDieU/Mp1D0jzNjtHJWrA484YGib6BdaEeljm/1XoBN'
        'y5sac99tgJx3G4Aa2wY1a485pSTz+KnK1ebX0M6nR2ulzFgdeEokgF5oR6VXA2QH1b2/fpkUbsuMU0JN5jGnlJCPWSRrjoW6O5uG13CZK7XgSVsYFy7qBXZA'
        'o45n24HzFllL63atD5bCaFmJaqcjiNeYh8Tp/cWuzqXi1TmMGC14TLxmiBqlKdbx7Vq9wAZo1HgzwNol9TvXBdXDaNcH1wM3uR25wp1WvNp8oDHX/LQzM4uj'
        'NCvpeM0QPVoLnpCG116jRWhCkNfW8a1aXZkN0Oj1ANmB9TDWdUFSKEs9CpI1ZqetzujvkxCPvehoHi1CFUTHa3+g4zXgCWlR6tP0SNm/b7++hos+gJZra8B5'
        'C/Li2p1ZgXUwnuuCGpCHMBBnmJ22OqP/gphknjfeLEq4fAYtSm2hIQfnCaM0ekaY+oXRM0YC8G2ARu8HWFoHE5m7rBGq0s2DrkQQrzb/ICL0po+eQ8V3vEKN'
        '1JyjRY0cHGqLQtUSPL7psbH70ZSiD6Ap9WKANQGSnWuX1IIjWYQOv+p08+Xq1WZwxSpSfw2FAo/mh2j+UByuOkWN1ABqI9Q3qOGau+KODaDl2QCNXg+QubgW'
        'HElaIn4Wua1UpZu/q043gytWpPV1UCM15uIINaBXdZESph739nYnANeq0XJHbiNolHotAHlhTWPmohpwJBIA+bPlRPN7Ven9N6vS+8EVRUQT8pMKFIer3bYo'
        'TP3xlhDlK/fbj4YzyQJkLJA0kgNqwJG3AyBUEPsIlaS+4SpSP7hiZVovMKLboQg5TBelhKr2U95rfsqZ/ahLrBpN6chtxG3VnIc4AEIFoX+7qwGqkAikfiiN'
        'O+L84Yeqf6SEqLe7sp9JF2D1fPGONQtrwJFjAyBUEHsrK9OQK9t1eYldPx1wmGpCKaEqe9FyFd7V/Wg4VjXaACq21csB/CXgyPECAA4eERH79rgbQZDcA8Xh'
        'GtgeqrrXFcrTlJCfH65cQcW2qjUcG6BRzbbV47wFaV71jgx/CThyvAAIyJuYRKm9+gpiH7hjeaoJaJE62L5CdcdtIcr2zYvvfrhyNYAaOUQ0ejvA6gVicORE'
        'ARCQdxuXp/aZKgh94I4iQi8w8B1ACVEih79DTDL9As1+VCyrWl1iAzQq2VbvBUhDAswXgyMdBUCgR3/0jiDZ+KMotQ/csTy1D3gJBg3y0IZ2P5MyQPq8anCk'
        'owBbAhUvbV2uPFO0Qg2CFKNbAe64qlfFT+5/Ds1+VGyrSsVGvpGikGWrw3kL0tyqBtI71eDQCQJQQvXPbV2mOLF1uQIQi0I1IEzuhfJVfWj8VEQ48Xd396Ni'
        'TrIAxDkVDaS5VeDIeD/BM2P/niBY9mRBsKxj67sKGG1xmPanCCnuK0zpvSJI7g12OwBr5BDdVsnwcoC0OVXgyLEBKDjKo4XBioOFyxQwntRwHXKIqCxP6b3F'
        'TzRtdHU/SsYkC0CYXSklzqkER44NUBCsqC5cJgdH0iPaR74S0CpI6pW68p59JcOiUjKtgEY5w+rlALMrwZGjA+QHyhhbguXgjMzITuQA0ZtoMpQkd/9xSgZY'
        '5VchJbxdAY68HSB/aRu5IEgOzrolSA4s/BEQJJlQW5ZoHOQmGf3utx8F3apUMqyARgXDVot72AIUBLZF5gfKbrkSoCBIDvmBbQ1liaZWT0QQJJrsgnhTtMMA'
        'tEkWIOWtcmmqXwU4csPS/YEFgbLrBYFycNbNS9tu5S1qWYfMEJNMT5UlGLvKEpErGa3GYX6iiTfRQxsSQDFyiO4rp1m8HGBWBUxk2uwa5Cq+lr9UBk67pO3b'
        'DYtbl4yeUxl3/Df8eOOJsgQTeMR40wER/t7/dC2nWZQKuhVQSbXVeC/ATFH9qrdEMJ5Ev2rIW9wMLh7+iS0Bsr+NN6s0puclfrzpTFn8yAGilhdv+liQZLpr'
        'loJqVUyqAMkzhPUpM0Uw1tRZlbAh4CBsXiJz2rxFbQcp/nqHHwVQnmL6Fz/eeIUfbwKPGGe8XBLXs2R0ADkNuY24r4xq8XKAGeVwlzNFkOO/HzYvbnPS1uFN'
        'i1q5yAOaMzMFMT1zeXE93/HjjOAhb/DijKuR15YVT7IASW8I65JnlMNo181vgk2L2py01Z4X0OrwJ5Px4MX0hfJijbd4sUbwoHXyIqtSTrUCGmVFXgyQOENY'
        'n/SmEG6b9c4eyAtoc86FLV9vClC87u5sfowphRvbM+zJCB/mX7giL7YCGr0agDCzTpL0ZjkkvSEE8pxdkBfQ6pwLWzvXzpP9Du18bkzPNu5KI3jKpo3nQYYc'
        'IhqLLBKctyDOkr6xft6HN3PmH4CNC1udc0GzhDRTjOpfrkZTGt1Tzo0xgids2nAeZEVWlHoxAAJhZoMf+e09n+UuaIaN/q2OvJnrfyjT0/MBB49wort3l8b0'
        'AFr3eiBAK8XLAW6T/rr0ZdKMXYey5+6/sWFBC4w2d/6h79fOaYp6ULMFa//7JCe6R1Ma3QNo3Jt7Dtq2W1HpswA/A4+mvdWYT3577zfZc/ffJM/ee4Y4o3HR'
        'g54qiDc8w8H39HPwPeCungjQtt0mxk1XOOFHf1+C7/6SE9UD7rgn5xy0UayobN1mmb4BENgRXa+WRHVfwAL4EE54zyx2RLetJKobXHHP+nPQilzFKJQV2qp8'
        'ufeHhtLo7iB2uOFGSWQ3OOtIgG1WVB7YfIXp670/NDCiPopnhxuG2BHd4IwfrEMCWNy2ZatluC5j4K5fpU97GGFdOa4EaNlqcdtdmQOKaX/g48EK7yphhXfD'
        '/dyd7V6A/XmXbzasOc0edzgGbuRpmRVmkLLCDODI3VnnoKXQ4rT/ybv0QwN5QCJNPv1L7Jyd+PxQVmj3QWaYASbS2QD7Nly63kAeqND7g0c/emfKw8V/9CtG'
        'SNdRZqgBxvP9tYPQvMUyoU05FyzSjAEq8hXl671MWhhh3S8wVxg+ZawwwFh3Z40f4IOs81driadyfL32KQMr2PAiPcQwwAjpgtHuy/0fNBdY7rg7+9z52vST'
        'Kb5e75SEvvzoa4yQrrP0kC5ArF71BRwqsMChgmvIreh0Lel0mK/XOOWpSvriL5Xxn+3YkXHm4p51F607yWcMtaQvA3y9LgwMDAwMDAwMDAwMDAwMDAwMDAzc'
        'g+H/m6Nkk+BPNz0AAAAASUVORK5CYII='
    ),
    'assets/badges/official/whiteboard.png': (
        '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'
    ),
    'assets/badges/official/word.png': (
        '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'
    ),
    'assets/andre-ascii.png': (
        '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'
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
