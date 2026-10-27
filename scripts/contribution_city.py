"""Render a full year of real GitHub activity as a locally hosted isometric city."""
from datetime import date, timedelta
import json
from PIL import Image, ImageDraw, ImageColor, ImageChops
from branding import TYPE, section_heading
from themes import TRANSPARENT
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 846


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


def render_city(root, font, palette, locale=DEFAULT):
    calendar = json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    model = build_city_model(calendar)
    canvas = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    section_heading(ImageDraw.Draw(canvas), palette, font, tr(locale, 'Atividade e contribuições'), 12)
    ImageDraw.Draw(canvas).rounded_rectangle((24,76,1176,834),radius=12,
                                            fill=palette['matte'],outline=palette['line'])
    with Image.open(root/'assets'/f'{localized("streak",locale)}-{palette["name"]}.png') as streak:
        if streak.size != (1200,272):
            raise ValueError('The activity card requires a complete contribution summary')
        canvas.alpha_composite(streak.convert('RGBA'), (0,76))
    scale = 2
    image = Image.new('RGBA',(1200*scale,HEIGHT*scale),TRANSPARENT)
    draw = ImageDraw.Draw(image)
    def text(x,y,value,size=18,bold=False,color=None):
        draw.text((x*scale,y*scale),str(value),font=font(size*scale,bold),fill=color or palette['muted'])
    def line(points, color, width=1):
        draw.line([(round(x*scale),round(y*scale)) for x,y in points],fill=color,width=width*scale)
    line([(44,340),(1156,340)],palette['line'])
    text(44,362,tr(locale,'Contribuições em 3D'),TYPE['card'],True,palette['accent'])
    text(44,400,tr(locale,'Últimos 12 meses')+' · '+_span(model,locale))
    annual = f"{model['total']} "+tr(locale,'contribuições em 12 meses')
    activity = f"{model['active_days']} "+tr(locale,'dias ativos')+' · '+tr(locale,'Pico diário')+f": {model['peak']}"
    text(1156-draw.textlength(annual,font=font(22*scale,True))/scale,362,annual,22,True,palette['text'])
    text(1156-draw.textlength(activity,font=font(18*scale))/scale,400,activity)

    light = palette['name'] == 'light'
    colors = (dict(ground='#edf3f7',edge='#d4e0e9',rim='#bacbd8',front='#288b91',side='#215976',roof='#8bd3ce')
              if light else
              dict(ground='#162635',edge='#253b4e',rim='#3b5871',front='#318e9a',side='#224e6b',roof='#8bd7d0'))
    cells = [dict(item,x=(item['week']-item['row'])*14,y=(item['week']+item['row'])*3.8)
             for item in model['days']]
    left=min(c['x']-13 for c in cells); right=max(c['x']+13 for c in cells)
    top=min(c['y']-c['height'] for c in cells); bottom=max(c['y']+10.2 for c in cells)
    box=(64,456,1136,720)
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
        points=[(x,y),(x+13,y+3.6),(x,y+7.2),(x-13,y+3.6)]
        if c['row']==6:
            polygon([(x-13,y+3.6),(x,y+7.2),(x,y+10.2),(x-13,y+6.6)],colors['rim'])
        polygon(points,colors['ground'],colors['edge'])
        ground_draw.polygon([project(x,y) for x,y in points],fill=255)
    # Shadows add depth on the floor without introducing extra activity.
    shadow=Image.new('RGBA',image.size,TRANSPARENT)
    sd=ImageDraw.Draw(shadow)
    for c in ordered:
        if c['height']>0:
            x,y=c['x'],c['y'];reach=c['height']*.23
            sd.polygon([project(px,py) for px,py in [(x-10,y+4),(x+10,y+4),(x+10+reach,y+12),(x-10+reach,y+12)]],
                       fill=(25,58,78,24) if light else (0,0,0,42))
    shadow.putalpha(ImageChops.multiply(shadow.getchannel('A'),ground_mask))
    image.alpha_composite(shadow)
    draw=ImageDraw.Draw(image)
    for c in ordered:
        if c['height']==0:
            continue
        x,y,h=c['x'],c['y'],c['height']
        tone=.85+.15*c['count']/(model['peak'] or 1)
        polygon([(x-13,y+3.6),(x,y+7.2),(x,y+7.2-h),(x-13,y+3.6-h)],_shade(colors['side'],tone))
        polygon([(x,y+7.2),(x+13,y+3.6),(x+13,y+3.6-h),(x,y+7.2-h)],_shade(colors['front'],tone))
        polygon([(x,y-h),(x+13,y+3.6-h),(x,y+7.2-h),(x-13,y+3.6-h)],_shade(colors['roof'],tone))
    months=(['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'] if locale==DEFAULT
            else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    previous=None
    markers=[]
    for c in cells:
        day=date.fromisoformat(c['date']);month=(day.year,day.month)
        if month!=previous:
            markers.append((c['week'],months[day.month-1]));previous=month
    for index,(week,label) in enumerate(markers):
        if index+1<len(markers) and markers[index+1][0]-week<3:
            continue
        px,py=project((week-6)*14,(week+6)*3.8+10.2)
        draw.line((px,py,px,py+5*scale),fill=palette['line'],width=scale)
        draw.text((px,py+10*scale),label,font=font(TYPE['meta']*scale),fill=palette['muted'],anchor='mt')
    line([(44,780),(1156,780)],palette['line'])
    text(44,795,tr(locale,'Cada bloco representa um dia.'),TYPE['meta'])
    legend=tr(locale,'Altura proporcional às contribuições.')
    text(1156-draw.textlength(legend,font=font(TYPE['meta']*scale))/scale,795,legend,TYPE['meta'])
    canvas.alpha_composite(image.resize((1200,HEIGHT),Image.Resampling.LANCZOS))
    canvas.save(root/'assets'/f'{localized("activity",locale)}-{palette["name"]}.png')
    return model
