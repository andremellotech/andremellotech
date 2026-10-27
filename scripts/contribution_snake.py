"""One card: persistent metrics and recent 3D city above the annual snk animation."""
from PIL import Image, ImageDraw, ImageOps, ImageSequence, ImageChops, GifImagePlugin
from profile_i18n import DEFAULT, localized


def render_snake(root, palette, locale=DEFAULT):
    # The workflow creates this with the same generator and colors as MateusHoffman.
    # Missing upstream output is an error; never silently substitute another route.
    source_path = root/'assets'/f"snake-source-{palette['name']}.gif"
    with Image.open(source_path) as source:
        header = Image.open(root/'assets'/f"{localized('activity',locale)}-{palette['name']}.png").convert('RGBA').crop((0, 0, 1200, 60))
        base = Image.new('RGBA', (1200, 934))
        base.alpha_composite(header)
        draw = ImageDraw.Draw(base)
        draw.rounded_rectangle((24, 76, 1176, 922), radius=12,
                               fill=palette['matte'], outline=palette['line'])
        with Image.open(root/'assets'/f"{localized('streak',locale)}-{palette['name']}.png") as streak:
            if streak.size != (1200,272):
                raise ValueError('The activity card requires a complete contribution summary')
            base.alpha_composite(streak.convert('RGBA'),(0,76))
        draw.line((44,340,1156,340),fill=palette['line'])
        with Image.open(root/'assets'/f"{localized('contribution-city',locale)}-{palette['name']}.png") as city:
            if city.size != (1200,384):
                raise ValueError('The activity card requires a complete recent contribution city')
            base.alpha_composite(city.convert('RGBA'),(0,354))
        output_path = root/'assets'/f"{localized('contribution-snake',locale)}-{palette['name']}.gif"
        shared = emitted = pending = None
        pending_duration = 0
        with output_path.open('wb') as output:
            def emit(frame, duration):
                nonlocal emitted
                if emitted is None:
                    chunks, _ = GifImagePlugin.getheader(frame, info={
                        'loop': source.info.get('loop', 0), 'transparency': 255, 'background': 255})
                    output.writelines(chunks)
                    output.writelines(GifImagePlugin.getdata(frame, duration=duration, disposal=1, transparency=255))
                else:
                    bounds = ImageChops.difference(frame, emitted).getbbox()
                    if bounds:
                        output.writelines(GifImagePlugin.getdata(frame.crop(bounds), offset=bounds[:2],
                                                                duration=duration, disposal=1, transparency=255))
                emitted = frame

            for original in ImageSequence.Iterator(source):
                duration = original.info.get('duration', 100)
                frame = base.copy()
                art = ImageOps.contain(original.convert('RGBA'), (1120, 160), Image.Resampling.LANCZOS)
                frame.alpha_composite(art, ((1200-art.width)//2, 742+(160-art.height)//2))
                if shared is None:
                    frame.save(root/'assets'/f"{localized('activity',locale)}-{palette['name']}.png")
                matte = Image.new('RGBA', frame.size, palette['matte'])
                matte.alpha_composite(frame)
                rgb = matte.convert('RGB')
                if shared is None:
                    shared = rgb.quantize(colors=128, dither=Image.Dither.NONE)
                indexed = rgb.quantize(palette=shared, dither=Image.Dither.NONE)
                indexed.paste(255, mask=frame.getchannel('A').point(lambda a: 255 if a == 0 else 0))
                if pending is not None and indexed.tobytes() == pending.tobytes():
                    pending_duration += duration
                else:
                    if pending is not None:
                        emit(pending, pending_duration)
                    pending, pending_duration = indexed, duration
            if pending is not None:
                emit(pending, pending_duration)
            output.write(b';')
    return output_path
