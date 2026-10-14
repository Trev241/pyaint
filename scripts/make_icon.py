"""Generate assets/pyaint.ico — a clay brush swipe on warm paper.

Run:  python build/make_icon.py
Writes a multi-size ICO (16-256 px) used for the window and the frozen exe.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAPER = (255, 253, 250, 255)
BORDER = (230, 222, 210, 255)
CLAY = (184, 84, 47, 255)
SS = 4  # supersample factor


def _bezier(p0, p1, p2, p3, steps):
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def make(size: int) -> Image.Image:
    s = size * SS
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = int(s * 0.22)
    draw.rounded_rectangle(
        [1 * SS, 1 * SS, s - 1 * SS, s - 1 * SS],
        radius=radius,
        fill=PAPER,
        outline=BORDER,
        width=max(1, int(s * 0.012)),
    )

    stroke_w = s * 0.16
    for x, y in _bezier(
        (0.30 * s, 0.74 * s),
        (0.30 * s, 0.32 * s),
        (0.64 * s, 0.20 * s),
        (0.78 * s, 0.30 * s),
        140,
    ):
        r = stroke_w / 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=CLAY)
    dot = s * 0.085
    draw.ellipse(
        [0.70 * s - dot, 0.72 * s - dot, 0.70 * s + dot, 0.72 * s + dot],
        fill=CLAY,
    )
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    base = make(256)
    path = os.path.join(ROOT, "assets", "pyaint.ico")
    base.save(
        path,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote", path)
    make(256).save(os.path.join(ROOT, "build", "pyaint_icon_256.png"))


if __name__ == "__main__":
    main()
