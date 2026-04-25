"""Generates static/icon.ico from scratch using Pillow. Run before building."""
import os
from PIL import Image, ImageDraw, ImageFont


def draw_icon(size: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    # Blue rounded square background
    pad = max(1, size // 16)
    d.rounded_rectangle([pad, pad, size - pad, size - pad],
                        radius=max(2, size // 8), fill='#1E40AF')

    # White "C" centred — use a truetype font if available, else fallback
    font_size = int(size * 0.72)
    font = None
    for path in [
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/calibrib.ttf',
    ]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except OSError:
            continue

    text = 'C'
    if font:
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2 - bbox[0]
        y = (size - th) // 2 - bbox[1]
        d.text((x, y), text, font=font, fill='white')
    else:
        # PIL default bitmap font fallback
        d.text((size // 4, size // 8), text, fill='white')

    return img


def make_icon():
    out    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'icon.ico')
    frames = [draw_icon(s) for s in (16, 32, 48, 64, 128, 256)]
    frames[0].save(out, format='ICO',
                   append_images=frames[1:],
                   sizes=[(f.width, f.height) for f in frames])
    print(f'Icon saved -> {out}')


if __name__ == '__main__':
    make_icon()
