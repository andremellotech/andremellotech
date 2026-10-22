"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
from themes import THEMES, TRANSPARENT
from activity_panel import render_activity
from github_layout import build_github_layout
from branding import section_heading, monogram, domain_icon

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
    def canvas(w, h):
        image = Image.new('RGBA', (w, h), TRANSPARENT)
        return image, ImageDraw.Draw(image)

    def txt(draw, x, y, value, size=22, color=None, bold=False):
        draw.text((x, y), value, font=font(size, bold), fill=color or palette['text'])

    def save(image, stem):
        image.save(A / f'{stem}-{name}.png')

    im, d = canvas(1200, 224)
    monogram(d, palette, font)
    txt(d, 118, 23, 'ANDREMELLOTECH', 14, palette['muted'])
    txt(d, 115, 47, 'André Mello', 44, bold=True)
    for y, label, size, color, bold in [
        (30, 'DATA & ANALYTICS', 18, palette['brand'], True),
        (59, 'CONSULTORIA · TECNOLOGIA · ENGENHARIA', 14, palette['muted'], False),
    ]:
        txt(d, 1170 - d.textlength(label, font=font(size, bold)), y, label, size, color, bold)
    txt(d, 30, 126, 'Dados, tecnologia e visão de negócio.', 25)
    txt(d, 30, 179, 'PERFORMANCE & ANALYTICS  /  AUTOMATION  /  FINANCIAL MODELING', 14, palette['muted'])
    d.line((30, 218, 1170, 218), fill=palette['line'])
    d.line((30, 218, 104, 218), fill=palette['brand'], width=3)
    save(im, 'hero')

    im, d = canvas(590, 550)
    section_heading(d, palette, font, '01', 'SOBRE MIM', 40)
    txt(d, 30, 89, 'Da análise', 36, palette['text'], True)
    txt(d, 30, 132, 'à decisão.', 36, palette['text'], True)
    for i, line in enumerate(['Meu foco conecta análise de performance,',
                              'engenharia, automação e modelagem financeira.',
                              'Uso dados e tecnologia para apoiar decisões',
                              'e melhorar processos.']):
        txt(d, 30, 209 + i * 31, line, 21, palette['muted'])
    d.line((30, 370, 550, 370), fill=palette['line'])
    txt(d, 30, 402, 'CLAREZA NA ANÁLISE. EFICIÊNCIA NA EXECUÇÃO.', 14, palette['muted'])
    for i, label in enumerate(['DADOS', 'ANÁLISE', 'DECISÃO']):
        x = 30 + i * 174
        d.rounded_rectangle((x, 447, x + 150, 499), radius=7, outline=palette['line'])
        face = font(14, True)
        d.text((x + (150 - d.textlength(label, font=face)) / 2, 465), label, font=face, fill=palette['accent'])
        if i < 2:
            d.line((x + 154, 473, x + 170, 473), fill=palette['brand'])
            d.line((x + 166, 469, x + 170, 473, x + 166, 477), fill=palette['brand'])
    save(im, 'about')

    im, d = canvas(1200, 264)
    section_heading(d, palette, font, '02', 'ÁREAS DE ATUAÇÃO', 12)
    cards = [('01', 'Data &', 'Analytics', ['Indicadores e análise', 'para apoiar decisões.']),
             ('02', 'Technology &', 'Engineering', ['Processos e tecnologia', 'para ganhar eficiência.']),
             ('03', 'Business &', 'Financial Modeling', ['Modelos e cenários', 'para dar contexto aos números.'])]
    for i, (num, title, subtitle, lines) in enumerate(cards):
        x = 12 + i * 400
        d.rounded_rectangle((x, 59, x + 376, 250), radius=10, outline=palette['line'])
        domain_icon(d, palette, i, x + 24, 76)
        txt(d, x + 329, 76, num, 13, palette['muted'])
        txt(d, x + 24, 115, title, 23, palette['text'], True)
        txt(d, x + 24, 145, subtitle, 23, palette['text'], True)
        for j, line in enumerate(lines):
            txt(d, x + 24, 187 + j * 24, line, 18, palette['muted'])
    save(im, 'expertise')

    im, d = canvas(1200, 570)
    section_heading(d, palette, font, '03', 'TECNOLOGIAS & FERRAMENTAS', 12)
    for group, (heading, items) in enumerate(BADGE_GROUPS):
        if group == 4:
            left, y, right = 30, 408, 1170
            heading = 'Banco de dados'
        else:
            left, y, right = (30 if group % 2 == 0 else 612), 60 + (group // 2) * 174, (588 if group % 2 == 0 else 1170)
        d.rounded_rectangle((left, y, right, y + (140 if group == 4 else 150)), radius=10, outline=palette['line'])
        txt(d, left + 20, y + 17, heading, 20, palette['text'], True)
        x = left + 20
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
            badge = badge.resize((round(badge.width * 1.2), 43), Image.Resampling.LANCZOS)
            im.alpha_composite(badge, (x, y + 65))
            x += badge.width + 6
        if group == 1:
            txt(d, left + 20, y + 122, 'Office 365 com Excel e PowerPoint.', 15, palette['muted'])
        if group == 4:
            label = 'EXPERIÊNCIA ANTERIOR'
            txt(d, 1150 - d.textlength(label, font=font(13)), y + 22, label, 13, palette['muted'])
            txt(d, 220, y + 79, 'MySQL nos servidores de Tibia e GTA V / FiveM.', 17, palette['muted'])
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
    draw.rectangle((0, 0, left - 1, 28 * scale - 1), fill='#59636e')
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
    link_badge('link-linkedin', 'LinkedIn', 'André Mello', '#334a60')
    link_badge('link-github', 'GitHub', 'Repositórios', '#334a60')
    build_github_layout(ROOT, font)
