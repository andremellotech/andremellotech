"""A local isometric city built only from validated recent GitHub contributions."""
from datetime import date, timedelta
import json
from PIL import Image, ImageDraw, ImageColor
from branding import TYPE
from themes import TRANSPARENT
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 384
PERIOD = 30


def build_city_model(calendar):
    try:
        end=date.fromisoformat(calendar['as_of'])
        source=calendar['days']
    except (KeyError,TypeError,ValueError) as error:
        raise ValueError('The contribution city requires a dated calendar') from error
    if not isinstance(source,list):
        raise ValueError('The contribution city requires daily records')
    start=end-timedelta(days=PERIOD-1)
    selected={}
    for item in source:
        try:
            day=date.fromisoformat(item['date'])
        except (KeyError,TypeError,ValueError) as error:
            raise ValueError('Invalid contribution date') from error
        if not start<=day<=end:
            continue
        count=item.get('count')
        if day in selected or type(count) is not int or count<0:
            raise ValueError('Duplicate or invalid contribution day')
        selected[day]=count
    expected=[start+timedelta(days=i) for i in range(PERIOD)]
    if set(selected)!=set(expected):
        raise ValueError('The contribution city requires thirty complete days')
    peak=max(selected.values())
    sunday=start-timedelta(days=(start.weekday()+1)%7)
    days=[dict(date=day.isoformat(),count=selected[day],week=(day-sunday).days//7,
               row=(day.weekday()+1)%7,height=128*selected[day]/(peak or 1)) for day in expected]
    return dict(start=start.isoformat(),end=end.isoformat(),days=days,
                total=sum(selected.values()),active_days=sum(v>0 for v in selected.values()),peak=peak)


def _span(model,locale):
    months=(['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'] if locale==DEFAULT
            else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    first,last=date.fromisoformat(model['start']),date.fromisoformat(model['end'])
    def label(day,year=False):
        if locale==DEFAULT:
            return f'{day.day} {months[day.month-1]}'+(f' {day.year}' if year else '')
        return f'{months[day.month-1]} {day.day}'+(f', {day.year}' if year else '')
    return label(first,first.year!=last.year)+' — '+label(last,True)


def _shade(color,factor):
    return tuple(max(0,min(255,round(v*factor))) for v in ImageColor.getrgb(color))


def render_city(root,font,palette,locale=DEFAULT):
    calendar=json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    model=build_city_model(calendar)
    scale=2
    image=Image.new('RGBA',(1200*scale,HEIGHT*scale),TRANSPARENT)
    draw=ImageDraw.Draw(image)
    def text(x,y,value,size=18,bold=False,color=None):
        draw.text((x*scale,y*scale),value,font=font(size*scale,bold),fill=color or palette['muted'])
    text(44,12,tr(locale,'Contribuições em 3D'),TYPE['card'],True,palette['accent'])
    text(44,50,tr(locale,'Últimos 30 dias'))
    text(44,104,str(model['active_days'])+' '+tr(locale,'dias com atividade'),TYPE['body'],True,palette['text'])
    text(44,142,tr(locale,'Máximo diário')+': '+str(model['peak']))
    text(44,214,tr(locale,'Cada prédio é um dia com atividade.'))
    text(44,244,tr(locale,'Altura = contribuições.'))
    text(44,296,_span(model,locale))

    # The coordinate grid preserves weekdays and week order. Zero days are flat
    # ground tiles; positive counts produce linearly proportional building heights.
    colors=(dict(ground='#e5eef1',edge='#cedfe3',front='#34a694',side='#237c79',roof='#8cded0')
            if palette['name']=='light' else
            dict(ground='#192d37',edge='#2c4650',front='#2b9689',side='#1b6468',roof='#71cdbd'))
    cells=[]
    for item in model['days']:
        x=(item['week']-item['row'])*26
        y=(item['week']+item['row'])*10
        cells.append(dict(item,x=x,y=y))
    left=min(c['x']-24 for c in cells); right=max(c['x']+24 for c in cells)
    top=min(c['y']-c['height'] for c in cells); bottom=max(c['y']+18 for c in cells)
    box=(398,4,1156,284)
    zoom=min((box[2]-box[0])/(right-left),(box[3]-box[1])/(bottom-top or 1))
    ox=(box[0]+box[2]-(left+right)*zoom)/2
    oy=(box[1]+box[3]-(top+bottom)*zoom)/2
    def polygon(points,fill,outline=None):
        draw.polygon([(round((ox+x*zoom)*scale),round((oy+y*zoom)*scale)) for x,y in points],
                     fill=fill,outline=outline,width=scale)
    for cell in sorted(cells,key=lambda c:(c['week']+c['row'],c['week'])):
        x,y=cell['x'],cell['y']
        polygon([(x,y),(x+24,y+9),(x,y+18),(x-24,y+9)],colors['ground'],colors['edge'])
    for cell in sorted(cells,key=lambda c:(c['week']+c['row'],c['week'])):
        if cell['height']==0:
            continue
        x,y,h=cell['x'],cell['y'],cell['height']
        tone=.88+.12*cell['count']/(model['peak'] or 1)
        polygon([(x-24,y+9),(x,y+18),(x,y+18-h),(x-24,y+9-h)],_shade(colors['side'],tone))
        polygon([(x,y+18),(x+24,y+9),(x+24,y+9-h),(x,y+18-h)],_shade(colors['front'],tone))
        polygon([(x,y-h),(x+24,y+9-h),(x,y+18-h),(x-24,y+9-h)],_shade(colors['roof'],tone))

    draw.line((44*scale,336*scale,1156*scale,336*scale),fill=palette['line'],width=scale)
    text(44,350,tr(locale,'Calendário anual · cobrinha'),TYPE['meta'],True,palette['accent'])
    image=image.resize((1200,HEIGHT),Image.Resampling.LANCZOS)
    image.save(root/'assets'/f'{localized("contribution-city",locale)}-{palette["name"]}.png')
    return model
