"""GitHub status cards: public numbers, language mix and streaks."""
import json
import math
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import section_heading, metric_icon
from activity_panel import contribution_summary

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


def render_status(root, font, palette):
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    calendar = json.loads((root / 'data/contributions.json').read_text(encoding='utf-8'))
    summary = contribution_summary(content, calendar)
    stats = content.get('stats', {})
    text, muted, accent, brand = palette['text'], palette['muted'], palette['accent'], palette['brand']
    im = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    d = ImageDraw.Draw(im)
    section_heading(d, palette, font, '02', 'Status do GitHub', 12)
    card = dict(radius=12, fill=palette['surface'], outline=palette['line'])

    d.rounded_rectangle((12, 56, 718, 296), **card)
    d.text((34, 72), 'Estatísticas', font=font(20, True), fill=accent)
    tiles = [('repos', 'Repositórios públicos', content['user']['public_repos']),
             ('stars', 'Estrelas recebidas', stats.get('stars')),
             ('commits', 'Commits públicos', stats.get('commits')),
             ('prs', 'Pull requests', stats.get('pull_requests')),
             ('issues', 'Issues criadas', stats.get('issues')),
             ('followers', 'Seguidores', content['user']['followers'])]
    for i, (kind, label, value) in enumerate(tiles):
        x, y = 34 + (i % 2) * 340, 112 + (i // 2) * 60
        _icon(d, kind, x, y + 6, brand)
        d.text((x + 44, y), label, font=font(13), fill=muted)
        d.text((x + 44, y + 17), _fmt(value), font=font(26, True), fill=text)

    d.rounded_rectangle((738, 56, 1188, 296), **card)
    d.text((760, 72), 'Código nos repositórios', font=font(20, True), fill=accent)
    languages = content.get('languages', {})
    total = sum(languages.values()) or 1
    rows = list(languages.items())[:4]
    others = sum(size for _, size in list(languages.items())[4:])
    if others:
        rows.append(('Outras', others))
    for i, (name, size) in enumerate(rows):
        y = 108 + i * 32
        share = size / total
        d.text((760, y), name, font=font(13), fill=text)
        label = f'{share * 100:.1f}%'.replace('.', ',')
        d.text((1166 - d.textlength(label, font=font(13)), y), label, font=font(13), fill=muted)
        d.rounded_rectangle((760, y + 20, 1166, y + 27), radius=3, fill=palette['line'])
        d.rounded_rectangle((760, y + 20, 760 + max(8, round(406 * share)), y + 27), radius=3,
                            fill=brand)
    d.text((760, 272), 'Por bytes · até 6 repositórios públicos recentes', font=font(11), fill=muted)

    d.rounded_rectangle((12, 316, 1188, 488), **card)
    d.line((412, 340, 412, 464), fill=palette['line'])
    d.line((788, 340, 788, 464), fill=palette['line'])
    columns = [(212, _fmt(summary['total']), 'Contribuições no último ano',
                'atividade pública'),
               (988, _fmt(summary['longest_streak']), 'Maior sequência', 'dias seguidos')]
    for cx, value, label, sub in columns:
        face = font(46, True)
        d.text((cx - d.textlength(value, font=face) / 2, 356), value, font=face, fill=brand)
        face = font(15, True)
        d.text((cx - d.textlength(label, font=face) / 2, 420), label, font=face, fill=accent)
        face = font(12)
        d.text((cx - d.textlength(sub, font=face) / 2, 444), sub, font=face, fill=muted)
    longest = max(summary['longest_streak'], 1)
    _ring(im, (600, 388), 50, summary['current_streak'] / longest, palette['line'], brand)
    value = str(summary['current_streak'])
    face = font(38, True)
    d.text((600 - d.textlength(value, font=face) / 2, 366), value, font=face, fill=text)
    face = font(15, True)
    d.text((600 - d.textlength('Sequência atual', font=face) / 2, 448), 'Sequência atual', font=face, fill=accent)
    im.save(root / 'assets' / f'status-{palette["name"]}.png')
    return summary
