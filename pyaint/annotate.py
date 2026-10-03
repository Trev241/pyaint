"""Annotate a detection screenshot with regions and palette cell centres.

Pure over PIL, so it can be tested and used off the UI thread. The palette cell
centres are drawn so the user can visually confirm, in the auto-detect preview,
that colours will be sampled from the middle of each swatch — the friendly
replacement for the old manual-centering workflow.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from pyaint import utils

CANVAS_OUTLINE = (241, 76, 76)   # red
PALETTE_OUTLINE = (78, 201, 176)  # teal
CENTER_FILL = (255, 255, 255)
CENTER_OUTLINE = (20, 20, 20)

# Skip centre dots if a recipe claims an absurd grid; avoids a wall of dots.
_MAX_CENTER_DOTS = 400


def annotate_detection(image: Image.Image, detection) -> Image.Image:
    """Return a copy of ``image`` with the detection drawn on top."""
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)

    canvas = getattr(detection, "canvas", None)
    if canvas:
        x, y, w, h = canvas
        draw.rectangle([x, y, x + w, y + h], outline=CANVAS_OUTLINE, width=4)

    palette = getattr(detection, "palette", None)
    if palette:
        x, y, w, h = palette
        draw.rectangle([x, y, x + w, y + h], outline=PALETTE_OUTLINE, width=4)
        rows = getattr(detection, "palette_rows", None)
        cols = getattr(detection, "palette_cols", None)
        if rows and cols and rows * cols <= _MAX_CENTER_DOTS:
            for cx, cy in utils.grid_centers(palette, rows, cols):
                draw.ellipse(
                    [cx - 3, cy - 3, cx + 3, cy + 3],
                    fill=CENTER_FILL,
                    outline=CENTER_OUTLINE,
                )
    return annotated
