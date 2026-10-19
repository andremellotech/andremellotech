"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
from themes import THEMES, TRANSPARENT
from activity_panel import render_activity
from github_layout import build_github_layout

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'


def font(size, bold=False, mono=False):
    base = Path('C:/Windows/Fonts') if os.name == 'nt' else Path('/usr/share/fonts/truetype/dejavu')
    if os.name == 'nt':
        name = 'consola.ttf' if mono else 'seguisb.ttf' if bold else 'segoeui.ttf'
    else:
        name = 'DejaVuSansMono.ttf' if mono else 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(str(base / name), size)


BADGE_GROUPS = [
    ('Dados & Automação', [('powerbi', 'Power BI'), ('python', 'Python'), ('excel', 'Excel'), ('alteryx', 'Alteryx')]),
    ('Negócios & Apresentações', [('sap', 'SAP'), ('powerpoint', 'PowerPoint')]),
    ('Linguagens · Conhecimentos', [('HTML2', 'HTML'), ('CSS2', 'CSS'), ('JavaScript2', 'JavaScript'), ('Lua2', 'Lua')]),
    ('Versionamento & Projetos', [('GitHub', 'GitHub')]),
    ('Bancos de dados · Experiência anterior', [('MySQL', 'MySQL')]),
]


def render_theme(name, palette):
    section_color = palette['accent']
    def canvas(w, h):
        image = Image.new('RGBA', (w, h), TRANSPARENT)
        return image, ImageDraw.Draw(image)

    def txt(draw, x, y, value, size=22, color=None, bold=False):
        draw.text((x, y), value, font=font(size, bold), fill=color or palette['text'])

    def save(image, stem):
        image.save(A / f'{stem}-{name}.png')

    im, d = canvas(1200, 224)
    def centered(y, value, size, color=None, bold=False):
        width = d.textlength(value, font=font(size, bold))
        txt(d, (1200 - width) / 2, y, value, size, color, bold)
    d.line((40, 1, 1160, 1), fill=palette['line'])
    centered(22, '@ANDREMELLOTECH', 15, palette['accent'])
    centered(52, 'André Mello', 52, bold=True)
    centered(119, 'Dados, tecnologia e visão de negócio.', 24)
    d.line((520, 166, 680, 166), fill=palette['accent'])
    centered(189, 'PERFORMANCE & ANALYTICS  /  AUTOMATION  /  FINANCIAL MODELING', 15, palette['muted'])
    save(im, 'hero')

    im, d = canvas(590, 550)
    txt(d, 30, 42, '01 / SOBRE MIM', 15, section_color)
    txt(d, 30, 92, 'Entre dados,', 30, palette['accent'], True)
    txt(d, 30, 132, 'tecnologia e negócios.', 30, palette['accent'], True)
    for i, line in enumerate(['Meu foco conecta análise de performance,',
                              'engenharia, automação e modelagem financeira.',
                              'Uso dados e tecnologia para apoiar decisões',
                              'e melhorar processos.']):
        txt(d, 30, 209 + i * 31, line, 21, palette['muted'])
    d.line((30, 370, 550, 370), fill=palette['line'])
    txt(d, 30, 402, 'DA ANÁLISE À EXECUÇÃO', 15, palette['accent'])
    txt(d, 30, 445, 'Clareza na análise.', 22, bold=True)
    txt(d, 30, 480, 'Eficiência na execução.', 22, bold=True)
    save(im, 'about')

    im, d = canvas(1200, 264)
    txt(d, 30, 18, '02 / ÁREAS DE ATUAÇÃO', 15, section_color)
    cards = [('01', 'Performance', '& Analytics', ['Indicadores e análise', 'para apoiar decisões.']),
             ('02', 'Engineering', '& Automation', ['Processos e tecnologia', 'para ganhar eficiência.']),
             ('03', 'Financial', 'Modeling', ['Modelos e cenários', 'para dar contexto aos números.'])]
    for i, (num, title, subtitle, lines) in enumerate(cards):
        x = 12 + i * 400
        d.rounded_rectangle((x, 59, x + 376, 250), radius=20, outline=palette['line'])
        txt(d, x + 24, 76, num, 15, palette['accent'])
        txt(d, x + 24, 109, title, 25, palette['accent'], True)
        txt(d, x + 24, 140, subtitle, 25, palette['accent'], True)
        for j, line in enumerate(lines):
            txt(d, x + 24, 187 + j * 24, line, 18, palette['muted'])
    save(im, 'expertise')

    im, d = canvas(1200, 716)
    txt(d, 30, 12, '03 / TECNOLOGIAS & FERRAMENTAS', 15, section_color)
    for group, (heading, items) in enumerate(BADGE_GROUPS):
        y = 58 + group * 111
        txt(d, 30, y, heading, 22, palette['accent'], True)
        d.line((30, y + 37, 1170, y + 37), fill=palette['line'])
        x = 30
        for stem, label in items:
            badge = Image.open(A / 'badges' / f'{stem}.webp').convert('RGBA')
            if name == 'light':
                # White labels need an opaque base instead of blending into the page.
                # Derive the capsule edge from its alpha so the exterior stays transparent.
                mask = badge.getchannel('A').point(lambda alpha: min(255, round(alpha * 2.5)))
                base = Image.new('RGBA', badge.size, '#0d1117')
                base.putalpha(mask)
                base.alpha_composite(badge)
                badge = base
            badge = badge.resize((round(badge.width * 1.25), 45), Image.Resampling.LANCZOS)
            im.alpha_composite(badge, (x, y + 51))
            x += badge.width + 6
    txt(d, 30, 619, 'MySQL aplicado ao desenvolvimento de servidores de Tibia e GTA V / FiveM.', 19, palette['muted'])
    txt(d, 30, 665, 'Office 365 no trabalho com Excel e PowerPoint.', 19, palette['muted'])
    save(im, 'stack')
    render_activity(ROOT, font, palette)


def link_badge(stem, label, value, color):
    scale = 3
    face = font(13 * scale, True)
    left = round(face.getlength(label)) + 22 * scale
    right = round(face.getlength(value)) + 22 * scale
    badge = Image.new('RGBA', (left + right, 28 * scale), TRANSPARENT)
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle((0, 0, left + right - 1, 28 * scale - 1), radius=4 * scale, fill=color)
    draw.rectangle((0, 0, left - 1, 28 * scale - 1), fill='#424d5d')
    mask = Image.new('L', badge.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, left + right - 1, 28 * scale - 1), radius=4 * scale, fill=255)
    badge.putalpha(mask)
    for x, word in [(11 * scale, label), (left + 11 * scale, value)]:
        bounds = draw.textbbox((0, 0), word, font=face)
        y = (28 * scale - (bounds[3] - bounds[1])) / 2 - bounds[1]
        draw.text((x, y), word, font=face, fill='white')
    badge.save(A / f'{stem}.png')


if __name__ == '__main__':
    A.mkdir(exist_ok=True)
    for name, palette in THEMES.items():
        render_theme(name, palette)
    link_badge('link-linkedin', 'LinkedIn', 'André Mello', '#0a66c2')
    link_badge('link-github', 'GitHub', 'Repositórios', '#116329')
    build_github_layout(ROOT, font)
