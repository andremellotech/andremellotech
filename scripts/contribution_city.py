"""Render a full year of real GitHub activity as a locally hosted isometric city."""
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
