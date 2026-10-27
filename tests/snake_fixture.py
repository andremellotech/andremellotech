"""Small controlled GIF input for the compositor, independent of network and solver."""
from PIL import Image, ImageDraw


def write_snake_fixture(root):
    (root/'assets').mkdir(parents=True, exist_ok=True)
    for theme, background, snake in [('light', '#ffffff', '#005bcf'), ('dark', '#0d1117', '#429aff')]:
        frames = []
        for x in [20, 40, 60]:
            frame = Image.new('RGB', (240, 90), background)
            draw = ImageDraw.Draw(frame)
            draw.rectangle((140, 20, 151, 31), fill='#FF8545')
            draw.rounded_rectangle((x, 20, x+11, 31), radius=3, fill=snake)
            frames.append(frame)
        frames[0].save(root/'assets'/f'snake-source-{theme}.gif', save_all=True,
                       append_images=frames[1:], duration=[80, 120, 160], loop=0)
        header = Image.new('RGBA', (1200, 316))
        ImageDraw.Draw(header).rectangle((30, 12, 200, 35), fill='#294b70')
        header.save(root/'assets'/f'activity-{theme}.png')
        streak = Image.new('RGBA', (1200, 272))
        ImageDraw.Draw(streak).rectangle((280,40,340,90), fill='#a65d00')
        streak.save(root/'assets'/f'streak-{theme}.png')
        city=Image.new('RGBA',(1200,384))
        ImageDraw.Draw(city).rectangle((600,70,660,130),fill='#168479')
        city.save(root/'assets'/f'contribution-city-{theme}.png')
