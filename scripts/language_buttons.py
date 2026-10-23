"""Small locally drawn language buttons, with no external badge dependency."""
from PIL import Image, ImageDraw
from themes import TRANSPARENT


def render_language_buttons(assets, font):
    for locale, label in [('pt-BR', 'Português'), ('en-US', 'English')]:
        face = font(22, True)
        probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        width = round(probe.textlength(label, font=face)) + 74
        image = Image.new('RGBA', (width, 48), TRANSPARENT)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0,0,width-1,47), radius=10, fill='#17324d', outline='#a6b7c8')
        if locale == 'pt-BR':
            draw.rectangle((12,12,44,35), fill='#18864b')
            draw.polygon([(28,14),(42,24),(28,33),(14,24)], fill='#ffcf40')
            draw.ellipse((22,18,34,30), fill='#2055a2')
            draw.line((23,22,33,26), fill='white', width=2)
        else:
            draw.rectangle((12,12,44,35), fill='white')
            for y in range(12,36,4):
                draw.rectangle((12,y,44,min(y+1,35)), fill='#d64b55')
            draw.rectangle((12,12,27,24), fill='#244b7d')
            for x in [15,20,25]:
                for y in [15,19,23]:
                    draw.point((x,y), fill='white')
        draw.text((56,10), label, font=face, fill='white')
        image.save(assets/f'language-{locale}.png')
