"""Render a full year of real GitHub activity as a locally hosted isometric city."""
from datetime import date, timedelta
import json, math
from PIL import Image, ImageDraw, ImageColor, ImageChops, GifImagePlugin
from branding import TYPE, section_heading
from themes import TRANSPARENT
from profile_i18n import DEFAULT, tr, localized

HEIGHT = 918
FRAME_COUNT = 32
FRAME_DURATION = 140
PALETTE_COLORS = 64


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


def _city_geometry(model, angle):
    """Rotate the camera, retaining every day's count and vertical height."""
    norm=math.sqrt(.5)
    u=(11.3*math.cos(angle)/norm,6.8*math.sin(angle)/norm)
    v=(-11.3*math.sin(angle)/norm,6.8*math.cos(angle)/norm)
    cells=[]
    for item in model['days']:
        x=12*(item['week']*math.cos(angle)-item['row']*math.sin(angle))/norm
        y=7.2*(item['week']*math.sin(angle)+item['row']*math.cos(angle))/norm
        points=[(x,y),(x+u[0],y+u[1]),(x+u[0]+v[0],y+u[1]+v[1]),(x+v[0],y+v[1])]
        cells.append(dict(item,x=x,y=y,points=points,depth=y+(u[1]+v[1])/2))
    return sorted(cells,key=lambda c:(c['depth'],c['week']))


def _city_bounds(model, angles):
    # One camera envelope for the whole loop avoids frame-by-frame zoom changes.
    points=[(x,y-h) for angle in angles for c in _city_geometry(model,angle)
            for x,y in c['points'] for h in [0,c['height']]]
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)


def _city_scene(root, font, palette, model, locale, angle=math.pi/4, bounds=None):
    scale=2
    width,height=1112,540
    image=Image.new('RGBA',(width*scale,height*scale),TRANSPARENT)
    draw=ImageDraw.Draw(image)
    def text(x,y,value,size=18,bold=False,color=None,mono=False):
        draw.text((round(x*scale),round(y*scale)),str(value),
                  font=font(size*scale,bold,mono),fill=color or palette['muted'])
    text(34,40,tr(locale,'CIDADE DE CONTRIBUIÇÕES'),14,True,palette['accent'],mono=True)
    text(34,72,model['total'],TYPE['name'],True,palette['text'])
    text(34,126,tr(locale,'contribuições nos'))
    text(34,153,tr(locale,'últimos 12 meses'))
    text(34,206,str(model['active_days'])+' '+tr(locale,'dias ativos'),TYPE['meta'],True)
    text(34,237,tr(locale,'Pico diário')+': '+str(model['peak']),TYPE['meta'])
    text(34,472,'@'+profile_username(root),16,mono=True)
    text(34,505,_span(model,locale),16)

    light=palette['name']=='light'
    colors=(dict(ground='#e7eef3',edge='#c8d6e0',front='#28a495',side='#226f79',roof='#81d7cc')
            if light else
            dict(ground='#172635',edge='#263e50',front='#39a99d',side='#286574',roof='#8ce6db'))
    cells=_city_geometry(model,angle)
    left,top,right,bottom=bounds or _city_bounds(model,[angle])
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
        polygon(cell['points'],colors['ground'],colors['edge'])
        ground_draw.polygon([project(x,y) for x,y in cell['points']],fill=255)
    shadow=Image.new('RGBA',image.size,TRANSPARENT)
    sd=ImageDraw.Draw(shadow)
    for cell in cells:
        if cell['height']>0:
            points=cell['points'];reach=cell['height']*.20
            sd.polygon([project(x,y) for x,y in [points[3],points[1],
                       (points[1][0]+reach,points[1][1]+10),
                       (points[3][0]+reach,points[3][1]+10)]],
                       fill=(19,78,74,24) if light else (0,0,0,40))
    shadow.putalpha(ImageChops.multiply(shadow.getchannel('A'),ground_mask))
    image.alpha_composite(shadow)
    draw=ImageDraw.Draw(image)
    for cell in cells:
        if cell['height']==0:
            continue
        p=cell['points'];h=cell['height']
        roof=[(x,y-h) for x,y in p]
        tone=.88+.12*cell['count']/(model['peak'] or 1)
        polygon([p[3],p[2],roof[2],roof[3]],_shade(colors['side'],tone))
        polygon([p[2],p[1],roof[1],roof[2]],_shade(colors['front'],tone))
        polygon(roof,_shade(colors['roof'],tone))
    return image.resize((width,height),Image.Resampling.LANCZOS)


def profile_username(root):
    content=json.loads((root/'data/github-content.json').read_text(encoding='utf-8'))
    return content['user']['login']


def _write_animation(path, frames, matte):
    """Write stable full-card text once, then only changed city rectangles."""
    shared=previous=None
    with path.open('wb') as output:
        for frame in frames:
            background=Image.new('RGBA',frame.size,matte)
            background.alpha_composite(frame)
            rgb=background.convert('RGB')
            if shared is None:
                shared=rgb.quantize(colors=PALETTE_COLORS,dither=Image.Dither.NONE)
                # Median quantization can turn white into a near-white gray.
                # Pin the actual card surface so the city joins the other panels.
                colors=shared.getpalette()
                surface=ImageColor.getrgb(matte)
                closest=min(range(PALETTE_COLORS),key=lambda i:sum((colors[3*i+j]-surface[j])**2 for j in range(3)))
                colors[3*closest:3*closest+3]=surface
                shared.putpalette(colors)
            indexed=rgb.quantize(palette=shared,dither=Image.Dither.NONE)
            # Pillow's approximate palette lookup may still choose a near-white
            # entry even when exact white exists. Preserve flat surface pixels.
            red,green,blue=ImageChops.difference(rgb,Image.new('RGB',rgb.size,matte)).split()
            surface_mask=ImageChops.lighter(ImageChops.lighter(red,green),blue).point(lambda v:255 if v==0 else 0)
            indexed.paste(closest,mask=surface_mask)
            indexed.paste(255,mask=frame.getchannel('A').point(lambda a:255 if a==0 else 0))
            if previous is None:
                chunks,_=GifImagePlugin.getheader(indexed,info={'loop':0,'transparency':255,'background':255})
                output.writelines(chunks)
                output.writelines(GifImagePlugin.getdata(indexed,duration=FRAME_DURATION,disposal=1,transparency=255))
            else:
                area=ImageChops.difference(indexed,previous).getbbox()
                if area:
                    output.writelines(GifImagePlugin.getdata(indexed.crop(area),offset=area[:2],
                                                            duration=FRAME_DURATION,disposal=1,transparency=255))
                else:
                    # Preserve timing even at a quantized camera turning point.
                    output.writelines(GifImagePlugin.getdata(indexed.crop((40,80,41,81)),offset=(40,80),
                                                            duration=FRAME_DURATION,disposal=1,transparency=255))
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
    angles=[math.pi/4+.065*math.sin(2*math.pi*i/FRAME_COUNT) for i in range(FRAME_COUNT)]
    bounds=_city_bounds(model,angles)
    stem=root/'assets'/f'{localized("activity",locale)}-{palette["name"]}'
    def frames():
        for index,angle in enumerate(angles):
            frame=base.copy()
            frame.alpha_composite(_city_scene(root,font,palette,model,locale,angle,bounds),(44,354))
            if index==0:
                frame.save(stem.with_suffix('.png'))
            yield frame
    _write_animation(stem.with_suffix('.gif'),frames(),palette['matte'])
    return model
