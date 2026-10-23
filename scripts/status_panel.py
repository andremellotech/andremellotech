"""GitHub status cards: public numbers, language mix and streaks."""
import json
import math
from datetime import date
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import section_heading, metric_icon
from fetch_contributions import derive_stats

# GitHub Linguist colors, verified against its languages.yml.
LANGUAGE_COLORS = {'HTML':'#e34c26', 'TypeScript':'#3178c6', 'C#':'#7355dd',
                   'Python':'#3572A5', 'JavaScript':'#f1e05a', 'CSS':'#663399',
                   'Lua':'#000080', 'PowerShell':'#012456', 'SQL':'#e38c00', 'Power Query':'#ffb900'}

HEIGHT = 500


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


def _fmt(value):
    return '—' if value is None else f'{value:,}'.replace(',', '.')


def _flame(image, x, y, color, background):
    s = 4
    layer = Image.new('RGBA', (32*s, 36*s), TRANSPARENT)
    draw = ImageDraw.Draw(layer)
    outer = [(16,0),(22,11),(26,8),(30,18),(30,25),(26,31),(16,35),
             (6,31),(1,24),(2,16),(8,9),(9,17),(14,12)]
    inner = [(16,17),(22,25),(21,30),(16,32),(11,29),(11,25)]
    draw.polygon([(a*s,b*s) for a,b in outer], fill=color)
    draw.polygon([(a*s,b*s) for a,b in inner], fill=background)
    image.alpha_composite(layer.resize((26,30), Image.Resampling.LANCZOS), (x,y))


def render_status(root, font, palette):
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    history = json.loads((root/'data/contributions-history.json').read_text(encoding='utf-8'))
    summary = derive_stats(history['days'], date.fromisoformat(history['as_of']))
    stats = content.get('stats', {})
    text, muted, accent, brand = palette['text'], palette['muted'], palette['accent'], palette['brand']
    blue = '#2f80ed' if palette['name'] == 'light' else '#58a6ff'
    fire = '#fb8c00'
    im = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    d = ImageDraw.Draw(im)
    section_heading(d, palette, font, 'Status do GitHub', 12)
    card = dict(radius=12, fill=palette['matte'], outline=palette['line'])

    d.rounded_rectangle((12, 56, 718, 296), **card)
    d.text((34, 72), 'Estatísticas do GitHub', font=font(20, True), fill=blue)
    tiles = [('repos', 'Repositórios públicos', content['user']['public_repos']),
             ('stars', 'Estrelas recebidas', stats.get('stars')),
             ('commits', 'Commits públicos', stats.get('commits')),
             ('prs', 'Pull requests', stats.get('pull_requests')),
             ('issues', 'Issues criadas', stats.get('issues')),
             ('followers', 'Seguidores', content['user']['followers'])]
    for i, (kind, label, value) in enumerate(tiles):
        x, y = 34 + (i % 2) * 340, 112 + (i // 2) * 60
        _icon(d, kind, x, y + 6, blue)
        d.text((x + 44, y), label, font=font(13), fill=muted)
        d.text((x + 44, y + 17), _fmt(value), font=font(26, True), fill=text)

    d.rounded_rectangle((738, 56, 1188, 296), **card)
    d.text((760, 72), 'Linguagens mais usadas', font=font(20, True), fill=blue)
    languages = content.get('languages', {})
    total = sum(languages.values()) or 1
    rows = list(languages.items())[:5]
    others = sum(size for _, size in list(languages.items())[5:])
    if others:
        rows.append(('Outras', others))
    rail = Image.new('RGBA', (406, 12), TRANSPARENT)
    rd = ImageDraw.Draw(rail)
    consumed = 0
    for name, size in rows:
        start = round(406*consumed/total)
        consumed += size
        end = round(406*consumed/total)
        if end > start:
            rd.rectangle((start,0,end-1,11), fill=LANGUAGE_COLORS.get(name, palette['muted']))
    mask = Image.new('L', rail.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,405,11), radius=6, fill=255)
    rail.putalpha(mask)
    im.alpha_composite(rail, (760,112))
    for i, (name, size) in enumerate(rows):
        x, y = 760 + (i % 2)*210, 146 + (i//2)*38
        share = size / total
        d.ellipse((x,y+5,x+10,y+15), fill=LANGUAGE_COLORS.get(name,palette['muted']))
        d.text((x+18, y), name, font=font(13), fill=text)
        label = f'{share * 100:.1f}%'.replace('.', ',')
        d.text((x+196 - d.textlength(label, font=font(12)), y+1), label, font=font(12), fill=muted)
    d.text((760, 272), 'Por bytes · até 6 repositórios públicos recentes', font=font(11), fill=muted)

    d.rounded_rectangle((12, 316, 1188, 488), **card)
    d.line((412, 340, 412, 464), fill=palette['line'])
    d.line((788, 340, 788, 464), fill=palette['line'])
    columns = [(212, _fmt(summary['total']), 'Total Contributions'),
               (988, _fmt(summary['longest_streak']), 'Longest Streak')]
    for cx, value, label in columns:
        face = font(46, True)
        d.text((cx - d.textlength(value, font=face) / 2, 359), value, font=face, fill=text)
        face = font(16)
        d.text((cx - d.textlength(label, font=face) / 2, 436), label, font=face, fill=text)
    _ring(im, (600, 392), 43, 1, palette['line'], fire, 6)
    d.rectangle((582,330,618,354), fill=palette['matte'])
    _flame(im, 587, 325, fire, palette['matte'])
    value = str(summary['current_streak'])
    face = font(38, True)
    d.text((600 - d.textlength(value, font=face) / 2, 369), value, font=face, fill=text)
    face = font(15, True)
    d.text((600 - d.textlength('Current Streak', font=face) / 2, 451), 'Current Streak', font=face, fill=fire)
    im.save(root / 'assets' / f'status-{palette["name"]}.png')
    return summary
