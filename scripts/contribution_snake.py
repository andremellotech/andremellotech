"""A deterministic GIF snake using the same public days as the contribution panel."""
import json
from PIL import Image, ImageDraw, ImageColor, ImageChops, GifImagePlugin
from activity_panel import week_grid


def snake_states(cells):
    """Visit every active day on a simple cycle; no self-collision or jumping.

    Restrict the route to columns around real activity so a sparse calendar
    does not spend most of its loop traversing an empty year. A reserved left
    column closes an eight-row cycle (the eighth row is below the calendar).
    """
    food = {(c['column'], c['row']) for c in cells if c['count'] > 0}
    left = max(0, min((x for x, _ in food), default=0) - 1)
    right = max((x for x, _ in food), default=0) + 1
    route = [(x, 0) for x in range(left, right + 1)]
    for row in range(1, 8):
        columns = range(right, left, -1) if row % 2 else range(left + 1, right + 1)
        route.extend((x, row) for x in columns)
    route.extend((left, row) for row in range(7, 0, -1))
    first_food = next((i for i, position in enumerate(route) if position in food), 8)
    offset = (first_food - 8) % len(route)
    route = route[offset:] + route[:offset]
    eaten, states = set(), []
    for step in range(len(route) + 1):
        body = [route[(step - i) % len(route)] for i in range(6)]
        if step and body[0] in food:
            eaten.add(body[0])
        states.append(dict(body=body, eaten=set(eaten)))
    return states


def render_snake(root, palette):
    """Draw once, then encode only changed rectangles in a shared GIF palette."""
    calendar = json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
    cells = week_grid(calendar['days'])
    columns = max(c['column'] for c in cells) + 1
    x0, y0, step = (1200-(columns*19-3))//2, 115, 19
    source = Image.open(root/'assets'/f"activity-{palette['name']}.png").convert('RGBA')
    matte = Image.new('RGBA', source.size, palette['matte'])
    matte.alpha_composite(source)
    base = matte.convert('RGB').quantize(colors=48, dither=Image.Dither.NONE)
    rgb_palette = base.getpalette()
    body_colors = (['#79b8ff', '#669ed8', '#5685b5', '#436c95', '#335574', '#263e55']
                   if palette['name'] == 'dark' else
                   ['#17324d', '#294b70', '#426b94', '#6589ad', '#8aaac8', '#b5cce0'])
    colors = [palette['calendar'][0]] + body_colors + [palette['matte']]
    for index, color in enumerate(colors, 48):
        rgb_palette[index*3:index*3+3] = ImageColor.getrgb(color)
    base.putpalette(rgb_palette)
    base.paste(255, mask=source.getchannel('A').point(lambda alpha: 255 if alpha == 0 else 0))
    output_path = root/'assets'/f"contribution-snake-{palette['name']}.gif"
    previous = None
    states = snake_states(cells)
    with output_path.open('wb') as output:
        for index, state in enumerate(states):
            frame = base.copy()
            draw = ImageDraw.Draw(frame)
            for column, row in state['eaten']:
                x, y = x0 + column*step, y0 + row*step
                draw.rounded_rectangle((x, y, x+15, y+15), radius=3, fill=48)
            for segment in range(5, -1, -1):
                column, row = state['body'][segment]
                x, y = x0 + column*step, y0 + row*step
                if segment < 5:
                    nx, ny = state['body'][segment+1]
                    draw.line((x+7, y+7, x0+nx*step+7, y0+ny*step+7), fill=49+segment, width=10)
                draw.rounded_rectangle((x-1, y-1, x+16, y+16), radius=5, fill=49+segment)
            head, neck = state['body'][:2]
            hx, hy = x0+head[0]*step, y0+head[1]*step
            dx, dy = head[0]-neck[0], head[1]-neck[1]
            for side in (-1, 1):
                ex, ey = hx+7+dx*4-dy*side*3, hy+7+dy*4+dx*side*3
                draw.rectangle((ex-1, ey-1, ex+1, ey+1), fill=55)
            duration = 1200 if index == 0 else 1300 if index == len(states)-1 else 80
            if previous is None:
                header, _ = GifImagePlugin.getheader(frame, info={
                    'loop': 0, 'transparency': 255, 'background': 255})
                output.writelines(header)
                output.writelines(GifImagePlugin.getdata(frame, duration=duration, disposal=1, transparency=255))
            else:
                bounds = ImageChops.difference(frame, previous).getbbox()
                if bounds:
                    output.writelines(GifImagePlugin.getdata(frame.crop(bounds), offset=bounds[:2],
                                                            duration=duration, disposal=1, transparency=255))
            previous = frame
        output.write(b';')
    return output_path
