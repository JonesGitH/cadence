"""Generates static/icon.ico from scratch using Pillow. Run before building."""
import os
from PIL import Image, ImageDraw


def draw_icon(size: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    d.rounded_rectangle([pad, pad, size - pad, size - pad],
                        radius=max(2, size // 6), fill='#2563eb')
    cx, cy, r = size // 2, size // 2, size // 4
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill='white')
    return img


def make_icon():
    out    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'icon.ico')
    frames = [draw_icon(s) for s in (16, 32, 48, 64, 128, 256)]
    frames[0].save(out, format='ICO',
                   append_images=frames[1:],
                   sizes=[(f.width, f.height) for f in frames])
    print(f'Icon saved → {out}')


if __name__ == '__main__':
    make_icon()
