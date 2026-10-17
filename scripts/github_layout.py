"""Keep the approved dark composition intact inside GitHub's README renderer."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

BG='#080e1c'
def build_github_layout(root):
    a=root/'assets'
    panels=[]
    for name in ['hero','about-pair','expertise','stack']:
        if name=='about-pair':
            panel=Image.new('RGB',(1200,550),BG)
            panel.paste(Image.open(a/'andre-ascii.png').convert('RGB'),(84,0))
            panel.paste(Image.open(a/'about.png'),(532,0))
        else:panel=Image.open(a/(name+'.png')).convert('RGB')
        panels.append(panel)
    height=sum(p.height for p in panels)+28*len(panels)+102
    main=Image.new('RGB',(1200,height),BG)
    y=0
    portrait_y=panels[0].height+28
    for p in panels:main.paste(p,(0,y));y+=p.height+28
    d=ImageDraw.Draw(main)
    fonts=Path('C:/Windows/Fonts') if os.name=='nt' else Path('/usr/share/fonts/truetype/dejavu')
    heading=ImageFont.truetype(str(fonts/('seguisb.ttf' if os.name=='nt' else 'DejaVuSans-Bold.ttf')),22)
    body=ImageFont.truetype(str(fonts/('segoeui.ttf' if os.name=='nt' else 'DejaVuSans.ttf')),19)
    for offset,text,f,color in [(12,'Contato & Projetos',heading,'#eff5ff'),(54,'Conheça meu trabalho e vamos conversar.',body,'#94a5c1')]:
        d.text(((1200-d.textlength(text,font=f))/2,y+offset),text,font=f,fill=color)
    main.save(a/'profile-card.png')

    # One global palette keeps all non-animated text and panels pixel-stable.
    palette=main.quantize(colors=256,dither=Image.Dither.NONE)
    portrait=Image.open(a/'andre-ascii.gif')
    frames=[];durations=[]
    for i in range(portrait.n_frames):
        portrait.seek(i)
        frame=palette.copy()
        avatar=portrait.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE)
        frame.paste(avatar,(84,portrait_y))
        frames.append(frame)
        durations.append(portrait.info.get('duration',80))
    frames[0].save(a/'profile-card.gif',save_all=True,append_images=frames[1:],
                   loop=0,duration=durations,disposal=1,optimize=True)

    footer=Image.new('RGB',(1200,84),BG)
    for stem,side in [('link-linkedin',0),('link-github',1)]:
        half=Image.new('RGB',(600,84),BG)
        badge=Image.open(a/(stem+'.png')).convert('RGBA')
        badge=badge.resize((round(badge.width/2),42),Image.Resampling.LANCZOS)
        x=600-badge.width-8 if side==0 else 8
        half.paste(badge,(x,12),badge)
        half.save(a/('footer-linkedin.png' if side==0 else 'footer-github.png'))
        footer.paste(half,(600*side,0))
    preview=Image.new('RGB',(1200,height+84),BG)
    preview.paste(main,(0,0));preview.paste(footer,(0,height));preview.save(root/'PREVIA.png')

    old=(root/'README.md').read_text(encoding='utf-8')
    details=old[old.index('<details>'):]
    alt=('André Mello — Dados, tecnologia e visão de negócio. Performance e Analytics; '
         'Engineering e Automation; Financial Modeling. Ferramentas: Power BI, Python, Excel, '
         'Alteryx, SAP e PowerPoint; conhecimentos em HTML, CSS, JavaScript e Lua; GitHub; '
         'experiência anterior em MySQL nos servidores de Tibia e GTA V / FiveM. '
         'Office 365 com Excel e PowerPoint. Apresentação completa na versão em texto abaixo.')
    # Adjacent inline images with align=top avoid paragraph and baseline gaps.
    visual=('<p align="center"><picture><source media="(prefers-reduced-motion: reduce)" '
            'srcset="./assets/profile-card.png"><img src="./assets/profile-card.gif" '
            'width="100%" align="top" alt="'+alt+'" /></picture>'
            '<a href="https://www.linkedin.com/in/aamello/"><img src="./assets/footer-linkedin.png" '
            'width="50%" align="top" alt="LinkedIn — André Mello" /></a>'
            '<a href="https://github.com/andremellotech?tab=repositories"><img '
            'src="./assets/footer-github.png" width="50%" align="top" '
            'alt="GitHub — explorar meus repositórios" /></a></p>')
    readme=visual+'\n\n'+details
    (root/'README.md').write_text(readme,encoding='utf-8')
    html=('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>André Mello — prévia compatível com GitHub</title>'
          '<style>body{background:#f6f8fa;color:#1f2328;margin:0;font:14px/1.5 system-ui}'
          'main{max-width:900px;background:white;border:1px solid #d1d9e0;border-radius:6px;'
          'padding:24px;margin:24px auto}p{margin:0 0 16px}img{max-width:100%;height:auto;'
          'vertical-align:top}details{margin:12px 0}summary{cursor:pointer}'
          'a{color:#0969da}@media(max-width:600px){main{padding:12px;margin:8px}}</style>'
          '<main>'+readme+'</main></html>')
    (root/'previa.html').write_text(html,encoding='utf-8')
    print('Continuous GitHub card:',len(frames),'frames,',(a/'profile-card.gif').stat().st_size,'bytes')
