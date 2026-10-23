"""Professional experience and results supplied by André, separate from GitHub data."""
from PIL import Image, ImageDraw
from themes import TRANSPARENT
from branding import MARGIN, TYPE, section_heading, domain_icon, wrapped_text

HEIGHT = 512
RESULTS = [
    ('R$ 660 mi', 'Portfólio de ativos', 'sob governança'),
    ('+25%', 'Eficiência operacional', 'com dados e automação'),
    ('240 h/ano', 'Retrabalho eliminado', 'por meio de automação'),
    ('Até 80', 'Liderança de equipes', 'multifuncionais'),
]
PILLARS = [
    ('Governança e PMO', 'Portfólio, indicadores executivos e acompanhamento físico-financeiro.'),
    ('Engenharia e contratos', 'Ativos físicos, terceiros e contratos com CAPEX de até R$ 125 milhões.'),
    ('Dados e automação', 'Painéis executivos e integração de dados com Power BI, SAP e Power Automate.'),
]
ALT = ('Atuação e resultados informados por André: governança de R$ 660 milhões em ativos físicos; '
       'aumento de 25% na eficiência operacional; eliminação de 240 horas anuais de retrabalho; '
       'liderança de equipes com até 80 profissionais. Governança de portfólio e PMO, engenharia '
       'e contratos com CAPEX de até R$ 125 milhões, análise de dados e automação.')


def render_professional(root, font, palette):
    image = Image.new('RGBA', (1200, HEIGHT), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    section_heading(draw, palette, font, 'Atuação e resultados', 12)
    draw.text((MARGIN, 70), 'Engenharia e visão de negócio para transformar informação em ação.',
              font=font(TYPE['body']), fill=palette['muted'])
    for index, (value, title, detail) in enumerate(RESULTS):
        left = MARGIN + index * 294
        draw.rounded_rectangle((left, 112, left + 270, 260), radius=12,
                               fill=palette['surface'], outline=palette['line'])
        draw.line((left + 20, 132, left + 56, 132), fill=palette['brand'], width=3)
        draw.text((left + 20, 143), value, font=font(TYPE['number'], True), fill=palette['text'])
        draw.text((left + 20, 199), title, font=font(TYPE['meta'], True), fill=palette['accent'])
        draw.text((left + 20, 226), detail, font=font(TYPE['meta']), fill=palette['muted'])
    for index, (title, description) in enumerate(PILLARS):
        left = MARGIN + index * 392
        draw.rounded_rectangle((left, 284, left + 368, 496), radius=12,
                               fill=palette['matte'], outline=palette['line'])
        domain_icon(draw, palette, index, left + 20, 306)
        draw.text((left + 60, 305), title, font=font(TYPE['card'], True), fill=palette['accent'])
        used = wrapped_text(draw, (left + 20, 354), description, font(TYPE['body']),
                            palette['muted'], width=328)
        if used > 116:
            raise ValueError('Professional description exceeds its card: ' + title)
    image.save(root/'assets'/f'professional-{palette["name"]}.png')
