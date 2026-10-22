"""Curated public work, using real project previews and verified descriptions."""
import json
from PIL import Image, ImageDraw, ImageOps
from branding import section_heading
from themes import TRANSPARENT


PROJECTS = [
    dict(repo='financial-performance-analytics', title='Performance financeira',
         lines=['Orçado × realizado, build-up', 'e projeção de fechamento.'],
         tools='Power BI · Excel · Python'),
    dict(repo='finance-close-automation', title='Automação de fechamento',
         lines=['Validação, conciliação e', 'rastreabilidade de CSV e Excel.'],
         tools='Python · pandas · Excel'),
    dict(repo='sap-project-financial-control-tower', title='Controle financeiro SAP',
         lines=['Custos e projeção por PEP.', 'CSV, sem conexão ativa com o SAP.'],
         tools='Python · SQL · JavaScript'),
]


def selected_projects(root):
    content = json.loads((root / 'data/github-content.json').read_text(encoding='utf-8'))
    owner = content['user']['login']
    available = {repo['name']: repo for repo in content['repositories']
                 if not repo.get('private') and not repo.get('fork')}
    selected = []
    for project in PROJECTS:
        url = f'https://github.com/{owner}/{project["repo"]}'
        if available.get(project['repo'], {}).get('html_url') == url:
            selected.append(dict(project, url=url))
    return selected


def render_projects(root, palette, font):
    projects = selected_projects(root)
    if not projects:
        return
    panel = Image.new('RGBA', (1200, 532), TRANSPARENT)
    draw = ImageDraw.Draw(panel)
    section_heading(draw, palette, font, '02', 'PROJETOS EM DESTAQUE', 12)
    draw.text((30, 47), 'Casos de portfólio com dados fictícios. Clique para explorar.',
              font=font(17), fill=palette['muted'])
    width = 1200 // len(projects)
    for index, project in enumerate(projects):
        left, right = index * width + 12, (index + 1) * width - 12
        draw.rounded_rectangle((left, 88, right, 516), radius=10,
                               fill=palette['surface'], outline=palette['line'])
        with Image.open(root / 'assets/project-previews' / f'{project["repo"]}.jpg') as source:
            preview = ImageOps.fit(source.convert('RGBA'), (width - 56, 168),
                                   Image.Resampling.LANCZOS, centering=(.5, 0))
        panel.alpha_composite(preview, (left + 16, 104))
        draw.rectangle((left + 16, 104, right - 16, 272), outline=palette['line'])
        draw.text((left + 20, 280), 'PRÉVIA WEB · DADOS FICTÍCIOS', font=font(11), fill=palette['muted'])
        size = 23
        while draw.textlength(project['title'], font=font(size, True)) > width - 64:
            size -= 1
        draw.text((left + 20, 310), project['title'], font=font(size, True), fill=palette['text'])
        for line_index, line in enumerate(project['lines']):
            draw.text((left + 20, 353 + line_index * 25), line,
                      font=font(17), fill=palette['muted'])
        draw.text((left + 20, 419), project['tools'], font=font(15), fill=palette['accent'])
        draw.line((left + 20, 458, right - 20, 458), fill=palette['line'])
        draw.text((left + 20, 478), 'Explorar projeto', font=font(17, True), fill=palette['brand'])
        draw.line((right - 42, 497, right - 26, 481), fill=palette['brand'], width=2)
        draw.line((right - 40, 481, right - 26, 481, right - 26, 495), fill=palette['brand'], width=2)
    panel.save(root / 'assets' / f'projects-{palette["name"]}.png')
