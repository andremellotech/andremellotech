"""Draw real contribution counts and their calendar as one profile panel."""
from pathlib import Path
from datetime import date,timedelta
import json
from PIL import Image,ImageDraw
from fetch_contributions import derive_stats
from themes import THEMES, TRANSPARENT
from branding import section_heading

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

def render_activity(root,font,palette=None):
    palette=palette or THEMES['dark']
    colors=palette['calendar']
    white,muted,accent=palette['text'],palette['muted'],palette['accent']
    content=json.loads((root/'data/github-content.json').read_text(encoding='utf-8'))
    calendar=json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    summary=contribution_summary(content,calendar)
    cells=week_grid(calendar['days'])
    im=Image.new('RGBA',(1200,316),TRANSPARENT);d=ImageDraw.Draw(im)
    def text(x,y,value,size=18,color=None,bold=False):d.text((x,y),str(value),font=font(size,bold),fill=color or white)
    section_heading(d,palette,font,'03','Atividade & contribuições',12)
    d.rounded_rectangle((12,60,1188,304),radius=12,fill=palette['matte'],outline=palette['line'])
    columns=max(c['column'] for c in cells)+1;step=19;size=16
    x0=(1200-(columns*step-3))//2;y0=115
    months=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    prev=None;starts=[]
    for c in cells:
        day=date.fromisoformat(c['date']);key=day.strftime('%Y-%m')
        if key!=prev:
            label=months[day.month-1]
            starts.append((x0+c['column']*step,label));prev=key
        x=x0+c['column']*step;y=y0+c['row']*step
        d.rounded_rectangle((x,y,x+size-1,y+size-1),radius=3,fill=colors[c['level']])
    for row,label in [(1,'Seg'),(3,'Qua'),(5,'Sex')]:text(x0-42,y0+row*step,label,12,muted)
    for index,(x,label) in enumerate(starts):
        if index+1<len(starts) and starts[index+1][0]-x<35:continue
        text(x,83,label,13,muted)
    text(929,275,'Menos',12,muted)
    for i,color in enumerate(colors):d.rounded_rectangle((976+i*20,277,991+i*20,292),radius=3,fill=color)
    text(1085,275,'Mais',12,muted)
    im.save(root/'assets'/('activity-'+palette['name']+'.png'))
    return summary
