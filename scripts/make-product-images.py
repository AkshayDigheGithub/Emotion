#!/usr/bin/env python3
"""Generate the product images referenced by the Product JSON-LD in index.html.

Google needs an `image` on every Product or the listing is invalid, and one
generic og-image for eight different pieces isn't much of a product shot. Each
image here is the piece's own gradient and ink colour — the same palette the
reader actually lands on — with the feeling set in italic serif.

Run from the repo root:  python3 scripts/make-product-images.py
Requires Pillow.  Output: img/<key>.jpg (1200x1200).

The palettes below are copied from the PIECES array in index.html. If you
restyle a piece there, change it here too and re-run.
"""

from PIL import Image, ImageDraw, ImageFont

SIZE = 1200
OUT = "img"

SERIF_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

PIECES = [
    ("calm",      "Calm",      ["#e6f5f1", "#bfe3da", "#8fc7ba"], "#1f3d38"),
    ("nostalgia", "Nostalgia", ["#f4e6cf", "#e0bd8f", "#c98f6a"], "#3d2718"),
    ("happiness", "Happiness", ["#fff4d6", "#ffd889", "#ffb454"], "#4a3200"),
    ("hope",      "Hope",      ["#1b2440", "#3d3d6d", "#5b5590"], "#fdf6ea"),
    ("rage",      "Rage",      ["#0a0505", "#3a0a0a", "#8a0f0f"], "#f5e6e6"),
    ("hurt",      "Hurt",      ["#1a0b0d", "#3d1218", "#6b1a24"], "#f2dfe0"),
    ("sorrow",    "Sorrow",    ["#0e1a2b", "#1c3350", "#33547e"], "#e6ecf5"),
    ("grief",     "Grief",     ["#100e14", "#251f30", "#40374f"], "#e8e3ef"),
]


def rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(stops):
    """Three-stop vertical gradient, 0 -> 0.58 -> 1, same ramp as the pages."""
    a, b, c = (rgb(s) for s in stops)
    img = Image.new("RGB", (1, SIZE))
    px = img.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        if t <= 0.58:
            k = t / 0.58
            start, end = a, b
        else:
            k = (t - 0.58) / 0.42
            start, end = b, c
        px[0, y] = tuple(round(start[i] + (end[i] - start[i]) * k) for i in range(3))
    return img.resize((SIZE, SIZE))


def main():
    for key, name, stops, ink in PIECES:
        img = gradient(stops)
        draw = ImageDraw.Draw(img)
        ink_rgb = rgb(ink)

        title = ImageFont.truetype(SERIF_ITALIC, 210)
        label = ImageFont.truetype(SANS, 40)

        box = draw.textbbox((0, 0), name, font=title)
        draw.text(
            ((SIZE - (box[2] - box[0])) / 2 - box[0], (SIZE - (box[3] - box[1])) / 2 - box[1] - 40),
            name, font=title, fill=ink_rgb,
        )

        rule_y = SIZE / 2 + 130
        draw.line([(SIZE / 2 - 90, rule_y), (SIZE / 2 + 90, rule_y)], fill=ink_rgb, width=2)

        foot = "moodshop.lol"
        box = draw.textbbox((0, 0), foot, font=label)
        draw.text(
            ((SIZE - (box[2] - box[0])) / 2 - box[0], rule_y + 60),
            foot, font=label, fill=ink_rgb,
        )

        path = f"{OUT}/{key}.jpg"
        img.save(path, "JPEG", quality=82, optimize=True, progressive=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
