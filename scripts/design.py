"""Build the profile with transparent backgrounds and theme-aware text colors."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageChops
import os
from themes import THEMES, TRANSPARENT
from activity_panel import render_activity
from github_layout import build_github_layout
from branding import section_heading, monogram, domain_icon, chamfered_card, data_prism

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
    txt(d, 118, 23, 'ANDREMELLOTECH', 14, palette['brand'], True)
    txt(d, 115, 47, 'André', 44, bold=True)
    txt(d, 127 + d.textlength('André', font=font(44, True)), 47, 'Mello', 44, palette['brand'], True)
    for y, label, size, color, bold in [
        (30, 'DATA & ANALYTICS', 18, palette['brand'], True),
        (59, 'CONSULTORIA · TECNOLOGIA · ENGENHARIA', 14, palette['muted'], False),
    ]:
        txt(d, 1170 - d.textlength(label, font=font(size, bold)), y, label, size, color, bold)
    txt(d, 30, 126, 'Dados, tecnologia e visão de negócio.', 25)
    txt(d, 30, 179, 'PERFORMANCE & ANALYTICS  /  AUTOMATION  /  FINANCIAL MODELING', 14, palette['muted'])
    data_prism(d, palette)
    d.line((30, 218, 1170, 218), fill=palette['line'])
    for left, right, color in [(30, 110, 'brand'), (110, 146, 'cyan'), (146, 166, 'copper')]:
        d.line((left, 218, right, 218), fill=palette[color], width=3)
    save(im, 'hero')

    im, d = canvas(590, 550)
    section_heading(d, palette, font, '01', 'SOBRE MIM', 40)
    txt(d, 30, 89, 'Da análise', 36, palette['text'], True)
    txt(d, 30, 132, 'à decisão.', 36, palette['brand'], True)
    d.line((30, 187, 107, 187), fill=palette['copper'], width=3)
    for i, line in enumerate(['Meu foco conecta análise de performance,',
                              'engenharia, automação e modelagem financeira.',
                              'Uso dados e tecnologia para apoiar decisões',
                              'e melhorar processos.']):
        txt(d, 30, 209 + i * 31, line, 21, palette['muted'])
    d.line((30, 370, 550, 370), fill=palette['line'])
    txt(d, 30, 402, 'CLAREZA NA ANÁLISE. EFICIÊNCIA NA EXECUÇÃO.', 14, palette['muted'])
    for i, label in enumerate(['DADOS', 'ANÁLISE', 'DECISÃO']):
        x = 30 + i * 174
        color = [palette['brand'], palette['cyan'], palette['copper']][i]
        chamfered_card(d, (x, 447, x + 150, 499), palette['surfaces'][i], color, 8)
        face = font(14, True)
        d.text((x + (150 - d.textlength(label, font=face)) / 2, 465), label, font=face, fill=color)
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
        color = [palette['brand'], palette['cyan'], palette['copper']][i]
        chamfered_card(d, (x, 59, x + 376, 250), palette['surfaces'][i], palette['line'], 18)
        d.line((x + 24, 59, x + 100, 59), fill=color, width=3)
        domain_icon(d, palette, i, x + 24, 76)
        txt(d, x + 329, 76, num, 13, color)
        txt(d, x + 24, 115, title, 23, palette['text'], True)
        txt(d, x + 24, 145, subtitle, 23, color, True)
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
        domain = [0, 2, 1, 0, 1][group]
        color = [palette['brand'], palette['cyan'], palette['copper']][domain]
        chamfered_card(d, (left, y, right, y + (140 if group == 4 else 150)),
                       palette['surfaces'][domain], palette['line'], 14)
        d.line((left, y + 24, left, y + 62), fill=color, width=3)
        txt(d, left + 20, y + 17, heading, 20, color, True)
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
            txt(d, 1150 - d.textlength(label, font=font(13)), y + 22, label, 13, palette['copper'])
            txt(d, 220, y + 79, 'MySQL nos servidores de Tibia e GTA V / FiveM.', 17, palette['muted'])
    save(im, 'stack')
    render_activity(ROOT, font, palette)


def contact_button(stem, label, value, start, end, network):
    scale, width, height = 2, 840, 176
    badge = Image.new('RGBA', (width, height), TRANSPARENT)
    draw = ImageDraw.Draw(badge)
    first, last = ImageColor.getrgb(start), ImageColor.getrgb(end)
    for x in range(width):
        ratio = x / (width - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(first, last))
        draw.line((x, 0, x, height - 1), fill=color)
    mask = Image.new('L', badge.size)
    ImageDraw.Draw(mask).polygon([(24, 0), (width - 1, 0), (width - 1, height - 25),
                                 (width - 25, height - 1), (0, height - 1), (0, 24)], fill=255)
    draw.line((48, 3, 196, 3), fill='#e2ad7c', width=4)
    if network == 'linkedin':
        draw.rounded_rectangle((40, 42, 116, 118), radius=10, outline='#b9e4ff', width=2)
        draw.text((51, 46), 'in', font=font(24 * scale, True), fill='white')
    else:
        # Reuse the existing GitHub mark, removing the badge's dark background.
        source = Image.open(A / 'badges/GitHub.webp').convert('RGBA').crop((15, 7, 37, 29))
        alpha = source.convert('L').point(lambda value: max(0, min(255, round((value - 32) * 255 / 223))))
        alpha = ImageChops.multiply(alpha, source.getchannel('A')).resize((72, 72), Image.Resampling.LANCZOS)
        icon = Image.new('RGBA', alpha.size, 'white')
        icon.putalpha(alpha)
        badge.alpha_composite(icon, (42, 44))
    draw.text((160, 24), label, font=font(22 * scale, True), fill='white')
    draw.text((160, 91), value, font=font(15 * scale), fill='#d9eeff')
    draw.line((width - 96, 90, width - 56, 50), fill='white', width=4)
    draw.line((width - 91, 50, width - 56, 50, width - 56, 85), fill='white', width=4)
    badge.putalpha(mask)
    badge.save(A / f'{stem}.png')


if __name__ == '__main__':
    A.mkdir(exist_ok=True)
    for name, palette in THEMES.items():
        render_theme(name, palette)
    contact_button('link-linkedin', 'LinkedIn', 'Conectar com André Mello', '#073c7a', '#0a66c2', 'linkedin')
    contact_button('link-github', 'GitHub', 'Explorar projetos e repositórios', '#092f4b', '#087c89', 'github')
    build_github_layout(ROOT, font)
