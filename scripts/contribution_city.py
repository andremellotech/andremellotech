"""Render a full year of real GitHub activity as a locally hosted isometric city."""
from datetime import date, timedelta
import json
from PIL import Image, ImageDraw, ImageColor, ImageChops
from branding import TYPE, section_heading
from themes import TRANSPARENT
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 918


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
        selected[day] = count
    expected = [start+timedelta(days=i) for i in range((end-start).days+1)]
    if set(selected) != set(expected):
        raise ValueError('The contribution city requires a complete year of daily data')
    peak = max(selected.values())
    sunday = start-timedelta(days=(start.weekday()+1) % 7)
    days = [dict(date=day.isoformat(), count=selected[day], week=(day-sunday).days//7,
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


def _aurora_background(size, light):
    """A quiet diagonal three-stop gradient in the reference's Aurora palette."""
    width, height = size
    small = Image.new('RGB', (278,135))
    pixels = small.load()
    stops = (['#effcf9','#d4f2ed','#edf9f6'] if light else ['#042f2e','#134e4a','#042f2e'])
    stops = [ImageColor.getrgb(color) for color in stops]
    for y in range(small.height):
        for x in range(small.width):
            t = .64*x/(small.width-1)+.36*y/(small.height-1)
            index = 0 if t <= .54 else 1
            u = t/.54 if index == 0 else (t-.54)/.46
            pixels[x,y] = tuple(round(stops[index][i]*(1-u)+stops[index+1][i]*u) for i in range(3))
    return small.resize((width,height),Image.Resampling.LANCZOS).convert('RGBA')


def _city_scene(root, font, palette, model, locale):
    scale = 2
    width, height = 1112, 540
    light = palette['name'] == 'light'
    image = _aurora_background((width*scale,height*scale),light)
    draw = ImageDraw.Draw(image)
    ink = '#134e4a' if light else '#ccfbf1'
    muted = '#236a64' if light else '#5eead4'
    edge = '#8bcbbf' if light else '#2b978a'
    def text(x,y,value,size=18,bold=False,color=None,mono=False):
        draw.text((round(x*scale),round(y*scale)),str(value),
                  font=font(size*scale,bold,mono),fill=color or muted)
    text(34,40,tr(locale,'CIDADE DE CONTRIBUIÇÕES'),14,True,mono=True)
    text(34,72,model['total'],TYPE['name'],True,ink)
    text(34,126,tr(locale,'contribuições nos'))
    text(34,153,tr(locale,'últimos 12 meses'))
    text(34,206,str(model['active_days'])+' '+tr(locale,'dias ativos'),TYPE['meta'],True)
    text(34,237,tr(locale,'Pico diário')+': '+str(model['peak']),TYPE['meta'])
    text(34,472,'@'+profile_username(root),16,mono=True)
    text(34,505,_span(model,locale),16)

    colors = (dict(ground='#c6e7df',edge='#acd6cd',front='#28ab99',side='#187c73',roof='#80ded0')
              if light else
              dict(ground='#195752',edge='#104944',front='#42b8a7',side='#2b8c82',roof='#8ce6db'))
    # The steeper, even isometric projection follows the Aurora reference.
    # All 365/366 days remain in their original week/weekday positions.
    cells = [dict(item,x=(item['week']-item['row'])*12,y=(item['week']+item['row'])*7.2)
             for item in model['days']]
    left=min(c['x']-11.3 for c in cells); right=max(c['x']+11.3 for c in cells)
    top=min(c['y']-c['height'] for c in cells); bottom=max(c['y']+13.6 for c in cells)
    box=(298,26,1072,498)
    zoom=min((box[2]-box[0])/(right-left),(box[3]-box[1])/(bottom-top or 1))
    ox=(box[0]+box[2]-(left+right)*zoom)/2
    oy=(box[1]+box[3]-(top+bottom)*zoom)/2
    def project(x,y):
        return (round((ox+x*zoom)*scale),round((oy+y*zoom)*scale))
    def polygon(points,fill,outline=None):
        draw.polygon([project(x,y) for x,y in points],fill=fill,outline=outline,width=scale)
    ordered=sorted(cells,key=lambda c:(c['week']+c['row'],c['week']))
    ground_mask=Image.new('L',image.size)
    ground_draw=ImageDraw.Draw(ground_mask)
    for c in ordered:
        x,y=c['x'],c['y']
        points=[(x,y),(x+11.3,y+6.8),(x,y+13.6),(x-11.3,y+6.8)]
        polygon(points,colors['ground'],colors['edge'])
        ground_draw.polygon([project(x,y) for x,y in points],fill=255)
    shadow=Image.new('RGBA',image.size,TRANSPARENT)
    sd=ImageDraw.Draw(shadow)
    for c in ordered:
        if c['height']>0:
            x,y=c['x'],c['y'];reach=c['height']*.20
            sd.polygon([project(px,py) for px,py in [(x-10,y+7),(x+10,y+7),(x+10+reach,y+18),(x-10+reach,y+18)]],
                       fill=(19,78,74,28) if light else (0,0,0,48))
    shadow.putalpha(ImageChops.multiply(shadow.getchannel('A'),ground_mask))
    image.alpha_composite(shadow)
    draw=ImageDraw.Draw(image)
    for c in ordered:
        if c['height']==0:
            continue
        x,y,h=c['x'],c['y'],c['height']
        tone=.88+.12*c['count']/(model['peak'] or 1)
        polygon([(x-11.3,y+6.8),(x,y+13.6),(x,y+13.6-h),(x-11.3,y+6.8-h)],_shade(colors['side'],tone))
        polygon([(x,y+13.6),(x+11.3,y+6.8),(x+11.3,y+6.8-h),(x,y+13.6-h)],_shade(colors['front'],tone))
        polygon([(x,y-h),(x+11.3,y+6.8-h),(x,y+13.6-h),(x-11.3,y+6.8-h)],_shade(colors['roof'],tone))
    mask=Image.new('L',image.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,width*scale-1,height*scale-1),radius=22*scale,fill=255)
    image.putalpha(mask)
    ImageDraw.Draw(image).rounded_rectangle((0,0,width*scale-1,height*scale-1),
                                           radius=22*scale,outline=edge,width=scale)
    return image.resize((width,height),Image.Resampling.LANCZOS)


def profile_username(root):
    content=json.loads((root/'data/github-content.json').read_text(encoding='utf-8'))
    return content['user']['login']


def render_city(root, font, palette, locale=DEFAULT):
    calendar=json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    model=build_city_model(calendar)
    canvas=Image.new('RGBA',(1200,HEIGHT),TRANSPARENT)
    draw=ImageDraw.Draw(canvas)
    section_heading(draw,palette,font,tr(locale,'Atividade e contribuições'),12)
    draw.rounded_rectangle((24,76,1176,906),radius=12,fill=palette['matte'],outline=palette['line'])
    with Image.open(root/'assets'/f'{localized("streak",locale)}-{palette["name"]}.png') as streak:
        if streak.size != (1200,272):
            raise ValueError('The activity card requires a complete contribution summary')
        canvas.alpha_composite(streak.convert('RGBA'),(0,76))
    draw.line((44,340,1156,340),fill=palette['line'])
    canvas.alpha_composite(_city_scene(root,font,palette,model,locale),(44,354))
    canvas.save(root/'assets'/f'{localized("activity",locale)}-{palette["name"]}.png')
    return model
