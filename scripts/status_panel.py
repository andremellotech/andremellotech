"""GitHub status cards: public numbers, language mix and streaks."""
import json
import math
from datetime import date
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import TYPE, section_heading, metric_icon
from fetch_contributions import derive_stats
from profile_i18n import DEFAULT, tr, localized

# GitHub Linguist colors, verified against its languages.yml.
LANGUAGE_COLORS = {'HTML':'#e34c26', 'TypeScript':'#3178c6', 'C#':'#7355dd',
                   'Python':'#3572A5', 'JavaScript':'#f1e05a', 'CSS':'#663399',
                   'Lua':'#000080', 'PowerShell':'#012456', 'SQL':'#e38c00', 'Power Query':'#ffb900'}

HEIGHT = 640


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
    im = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
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
    rail = Image.new('RGBA', (394, 12), TRANSPARENT)
    rd = ImageDraw.Draw(rail)
    consumed = 0
    for name, size in rows:
        start = round(394*consumed/total)
        consumed += size
        end = round(394*consumed/total)
        if end > start:
            rd.rectangle((start,0,end-1,11), fill=LANGUAGE_COLORS.get(name, palette['muted']))
    mask = Image.new('L', rail.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,393,11), radius=6, fill=255)
    rail.putalpha(mask)
    im.alpha_composite(rail, (762,168))
    legend_face = font(TYPE['meta'])
    measure = lambda value: d.textlength(value, font=legend_face)
    for item in language_legend(rows, total, measure, locale):
        x, y = item['x'], item['y']
        d.ellipse((x,y+5,x+10,y+15), fill=LANGUAGE_COLORS.get(item['source'],palette['muted']))
        d.text((x+18, y), item['name'], font=legend_face, fill=text)
        d.text((item['right'] - measure(item['share']), y), item['share'], font=legend_face, fill=muted)

    d.rounded_rectangle((24, 356, 1176, 628), **card)
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
    im.save(root / 'assets' / f'{localized("status", locale)}-{palette["name"]}.png')
    return summary
