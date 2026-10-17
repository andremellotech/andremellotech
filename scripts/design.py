"""Build the GitHub profile artwork. Requires Pillow; no remote image services."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, os, html

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'
A.mkdir(exist_ok=True)
BG='#080e1c'; PANEL='#101a2d'; WHITE='#eff5ff'; MUTED='#94a5c1'; BLUE='#659aff'; CYAN='#55dfef'
def font(n, bold=False, mono=False):
    base=Path('C:/Windows/Fonts') if os.name=='nt' else Path('/usr/share/fonts/truetype/dejavu')
    name=('consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf') if os.name=='nt' else ('DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(base/name), n)
def canvas(w,h):
    im=Image.new('RGB',(w,h),BG)
    return im,ImageDraw.Draw(im)
def txt(d,x,y,s,n=22,c=WHITE,b=False,mono=False):
    d.text((x,y),s,font=font(n,b,mono),fill=c)
def box(d,xy,fill=PANEL,r=20,outline='#22314d'):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=1)
def save(im,name):
    im.save(A/(name+'.png'))

im,d=canvas(1200,224)
def centered(d,y,value,n,c=WHITE,b=False,mono=False):
    width=d.textlength(value,font=font(n,b,mono))
    txt(d,(1200-width)/2,y,value,n,c,b,mono)
d.line((40,1,1160,1),fill='#233c5e',width=1)
centered(d,22,'@ANDREMELLOTECH',15,CYAN)
centered(d,52,'André Mello',52,b=True)
centered(d,119,'Dados, tecnologia e visão de negócio.',24,WHITE)
d.line((520,166,680,166),fill=BLUE,width=1)
centered(d,189,'PERFORMANCE & ANALYTICS  /  AUTOMATION  /  FINANCIAL MODELING',15,MUTED)
save(im,'hero')

im,d=canvas(590,550)
txt(d,30,42,'01 / SOBRE MIM',15,CYAN)
txt(d,30,92,'Entre dados,',30,b=True)
txt(d,30,132,'tecnologia e negócios.',30,BLUE,b=True)
for i,line in enumerate(['Meu foco conecta análise de performance,','engenharia, automação e modelagem financeira.','Uso dados e tecnologia para apoiar decisões','e melhorar processos.']): txt(d,30,209+i*31,line,21,MUTED)
d.line((30,370,550,370),fill='#263651',width=1)
txt(d,30,402,'DA ANÁLISE À EXECUÇÃO',15,CYAN)
txt(d,30,445,'Clareza na análise.',22,b=True)
txt(d,30,480,'Eficiência na execução.',22,b=True)
save(im,'about')

im,d=canvas(1200,264)
txt(d,30,18,'02 / ÁREAS DE ATUAÇÃO',15,CYAN)
cards=[('01','Performance','& Analytics',['Indicadores e análise','para apoiar decisões.']),('02','Engineering','& Automation',['Processos e tecnologia','para ganhar eficiência.']),('03','Financial','Modeling',['Modelos e cenários','para dar contexto aos números.'])]
for i,(num,a,b,lines) in enumerate(cards):
    x=12+i*400
    box(d,(x,59,x+376,250))
    txt(d,x+24,76,num,15,CYAN)
    txt(d,x+24,109,a,25,b=True); txt(d,x+24,140,b,25,BLUE,b=True)
    for j,s in enumerate(lines): txt(d,x+24,187+j*24,s,18,MUTED)
save(im,'expertise')

# Tools confirmed by André; MySQL is contextualized as previous experience.
BADGE_GROUPS = [('Dados & Automação', [('powerbi', 'Power BI'), ('python', 'Python'), ('excel', 'Excel'), ('alteryx', 'Alteryx')]), ('Negócios & Apresentações', [('sap', 'SAP'), ('powerpoint', 'PowerPoint')]), ('Linguagens · Conhecimentos', [('HTML2', 'HTML'), ('CSS2', 'CSS'), ('JavaScript2', 'JavaScript'), ('Lua2', 'Lua')]), ('Versionamento & Projetos', [('GitHub', 'GitHub')]), ('Bancos de dados · Experiência anterior', [('MySQL', 'MySQL')])]
im,d=canvas(1200,716)
txt(d,30,12,'03 / TECNOLOGIAS & FERRAMENTAS',15,CYAN)
for gi,(heading,items) in enumerate(BADGE_GROUPS):
    y=58+gi*111
    txt(d,30,y,heading,22,WHITE,True)
    d.line((30,y+37,1170,y+37),fill='#22314d',width=1)
    x=30
    for stem,label in items:
        badge=Image.open(A/'badges'/(stem+'.webp')).convert('RGBA')
        badge=badge.resize((round(badge.width*1.25),45),Image.Resampling.LANCZOS)
        im.paste(badge,(x,y+51),badge)
        x+=badge.width+6
txt(d,30,619,'MySQL aplicado ao desenvolvimento de servidores de Tibia e GTA V / FiveM.',19,MUTED)
txt(d,30,665,'Office 365 no trabalho com Excel e PowerPoint.',19,MUTED)
save(im,'stack')
badge_html='<div align="left">\n'
for gi,(heading,items) in enumerate(BADGE_GROUPS):
    badge_html+='<h3>'+heading+'</h3>\n<p>'
    badge_html+=' '.join('<img src="./assets/badges/'+stem+'.webp" height="36" alt="'+label+'" />' for stem,label in items)
    badge_html+='</p>\n'
    if gi==1: badge_html+='<p><sub>Office 365 no trabalho com Excel e PowerPoint.</sub></p>\n'
    if gi==4: badge_html+='<p><sub>MySQL aplicado ao desenvolvimento de servidores de Tibia e GTA V / FiveM.</sub></p>\n'
badge_html+='</div>'

content=json.loads((ROOT/'data/github-content.json').read_text(encoding='utf-8'))
contrib=json.loads((ROOT/'data/contributions.json').read_text(encoding='utf-8'))
im,d=canvas(1200,180)
txt(d,30,12,'ATIVIDADE PÚBLICA',16,CYAN,mono=True)
stats=contrib['stats']; days=contrib['days']
for i,(v,label) in enumerate([(content['user']['public_repos'],'REPOSITÓRIOS'),(stats['total'],'CONTRIBUIÇÕES'),(sum(x['count']>0 for x in days),'DIAS ATIVOS'),(stats['longest_streak'],'MAIOR SEQUÊNCIA / DIAS')]):
    x=30+i*300
    txt(d,x,56,str(v),45,CYAN if i==1 else WHITE,True)
    txt(d,x,119,label,13,MUTED,mono=True)
txt(d,30,157,'Snapshot público: '+content['as_of']+' · Valores referentes ao período do calendário.',13,MUTED)
save(im,'activity')

def link_badge(name,label,value,color):
    # Render at 3x for crisp display at a compact 28-pixel height.
    scale=3; f=font(13*scale,True)
    left=round(f.getlength(label))+22*scale
    right=round(f.getlength(value))+22*scale
    badge=Image.new('RGBA',(left+right,28*scale))
    bd=ImageDraw.Draw(badge)
    bd.rounded_rectangle((0,0,left+right-1,28*scale-1),radius=4*scale,fill=color)
    bd.rectangle((0,0,left-1,28*scale-1),fill='#424d5d')
    mask=Image.new('L',badge.size);md=ImageDraw.Draw(mask)
    md.rounded_rectangle((0,0,left+right-1,28*scale-1),radius=4*scale,fill=255)
    badge.putalpha(mask)
    for x,word in [(11*scale,label),(left+11*scale,value)]:
        bounds=bd.textbbox((0,0),word,font=f)
        y=(28*scale-(bounds[3]-bounds[1]))/2-bounds[1]
        bd.text((x,y),word,font=f,fill='white')
    badge.save(A/(name+'.png'))
    return badge
link_badge('link-linkedin','LinkedIn','André Mello','#0a66c2')
link_badge('link-github','GitHub','Repositórios','#237d70')

readme='''<div align="center">

<img src="./assets/hero.png" width="100%" alt="André Mello — Dados, tecnologia e visão de negócio. Performance, análise, automação e modelagem financeira." />

<br><br>

<picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/andre-ascii.png"><img src="./assets/andre-ascii.gif" width="36%" alt="Retrato animado de André Mello em arte ASCII" /></picture>
<img src="./assets/about.png" width="49%" alt="Sobre mim: foco em análise de performance, engenharia, automação e modelagem financeira." />

<br><br>

<img src="./assets/expertise.png" width="100%" alt="Áreas de atuação: Performance e Analytics; Engineering e Automation; Financial Modeling." />

<br>

<img src="./assets/stack.png" width="100%" alt="Ferramentas: Power BI, SAP e Excel." />

<br>

<h3>Contato & Projetos</h3>

<p>Conheça meu trabalho e vamos conversar.</p>

<p>
<a href="https://www.linkedin.com/in/aamello/"><img src="./assets/link-linkedin.png" height="28" alt="LinkedIn — André Mello" /></a>
&nbsp;
<a href="https://github.com/andremellotech?tab=repositories"><img src="./assets/link-github.png" height="28" alt="GitHub — explorar meus repositórios" /></a>
</p>

</div>

<details>
<summary>Sobre mim — versão em texto</summary>

<h3>André Mello</h3>
<p>Meu foco conecta análise de performance, engenharia, automação e modelagem financeira. Uso dados e tecnologia para apoiar decisões e melhorar processos.</p>
<ul>
<li><strong>Performance & Analytics:</strong> indicadores e análise para apoiar decisões.</li>
<li><strong>Engineering & Automation:</strong> processos e tecnologia para ganhar eficiência.</li>
<li><strong>Financial Modeling:</strong> modelos e cenários para dar contexto aos números.</li>
<li><strong>Dados e automação:</strong> Power BI, Python, Excel e Alteryx.</li>
<li><strong>Negócios e apresentações:</strong> SAP, PowerPoint e Office 365.</li>
<li><strong>Conhecimentos em linguagens:</strong> HTML, CSS, JavaScript e Lua.</li>
<li><strong>Versionamento e projetos:</strong> GitHub.</li>
<li><strong>Experiência anterior com MySQL:</strong> desenvolvimento de servidores de Tibia e GTA V / FiveM.</li>
</ul>

</details>

<details>
<summary>Atividade pública no GitHub</summary>

<a href="https://github.com/andremellotech#contribution-activity"><img src="./assets/activity.png" width="100%" alt="Métricas públicas do GitHub, com data do snapshot. Clique para abrir o calendário de contribuições." /></a>

</details>
'''
readme=readme.replace('<img src="./assets/stack.png" width="100%" alt="Ferramentas: Power BI, SAP e Excel." />',badge_html)
(ROOT/'README.md').write_text(readme,encoding='utf-8')
preview='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>André Mello — prévia do perfil</title><style>body{margin:0;background:#080e1c;color:#eff5ff;font:16px system-ui}main{max-width:1000px;margin:32px auto;padding:24px}img{vertical-align:middle;max-width:100%}img[width]{height:auto}img[height="36"]{height:36px;width:auto}img[height="28"]{height:28px;width:auto}a{color:#659aff}details{text-align:left;margin-top:16px;padding:18px 24px;border:1px solid #22314d;border-radius:12px}h3{font-size:18px;font-weight:600}summary{cursor:pointer}li{margin:8px 0}div[align="left"] h3{border-bottom:1px solid #22314d;padding-bottom:12px}div[align="left"] p{line-height:2.8}div[align="left"] p img{margin-bottom:4px}@media(max-width:600px){main{padding:10px;margin:8px auto}picture img,img[alt^="Sobre mim"]{width:100%}}</style><main>'+readme+'</main></html>'
(ROOT/'previa.html').write_text(preview,encoding='utf-8')
# A static contact sheet permits visual inspection without browser dependencies.
sheet=Image.new('RGB',(1200,3200),BG)
y=0
for name in ['hero','about-pair','expertise','stack','contacts']:
    if name=='about-pair':
        panel=Image.new('RGB',(1200,550),BG)
        portrait=Image.open(A/'andre-ascii.png').convert('RGB'); portrait.thumbnail((590,550))
        panel.paste(portrait,(84,(550-portrait.height)//2))
        panel.paste(Image.open(A/'about.png'),(532,0))
    elif name=='contacts':
        panel,pd=canvas(1200,180)
        centered(pd,12,'Contato & Projetos',22,b=True)
        centered(pd,54,'Conheça meu trabalho e vamos conversar.',19,MUTED)
        badges=[]
        for stem in ['link-linkedin','link-github']:
            badge=Image.open(A/(stem+'.png')).convert('RGBA')
            badge=badge.resize((round(badge.width/2),42),Image.Resampling.LANCZOS)
            badges.append(badge)
        bx=(1200-sum(b.width for b in badges)-14)//2
        for badge in badges:
            panel.paste(badge,(bx,105),badge);bx+=badge.width+14
    else: panel=Image.open(A/(name+'.png'))
    sheet.paste(panel,(0,y)); y+=panel.height+28
sheet.crop((0,0,1200,y)).save(ROOT/'PREVIA.png')
print('Profile built: typography header, 12 tool badges, compact contact links and collapsible activity.')

from github_layout import build_github_layout
from activity_panel import render_activity
render_activity(ROOT,font)
build_github_layout(ROOT)


