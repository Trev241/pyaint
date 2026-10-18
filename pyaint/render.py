"""Pure preview rendering: a stroke map or colour grid -> a PIL image.

Used by the live preview. No Qt and no screen access, so it is headlessly
testable and safe to run on a worker thread. Stroke coordinates from the
planner are absolute screen coordinates, so everything is translated by the
canvas origin before drawing.
"""

from __future__ import annotations

from typing import Dict, Tuple

from PIL import Image, ImageDraw

from pyaint import planner

#: Modes drawn as thin black lines; every other mode represents painted fills.
LINE_MODES = frozenset({planner.OUTLINE, planner.SKETCH})


def render_plan(cmap, canvas, step: int, mode: str) -> Image.Image:
    """Render ``cmap`` on the taught ``canvas`` as the drawing would appear.

    Line modes (``OUTLINE``/``SKETCH``) draw thin black polylines. Fill modes
    draw each run as a ``step``-wide block in its palette colour, which is the
    closest cheap approximation of the painted result.
    """
    x, y, width, height = (int(v) for v in canvas)
    width, height = max(1, width), max(1, height)
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    if mode in LINE_MODES:
        for strokes in cmap.values():
            for stroke in strokes:
                points = [(int(px) - x, int(py) - y) for px, py in stroke]
                if len(points) >= 2:
                    draw.line(points, fill=(0, 0, 0), width=1, joint="curve")
        return image

    brush = max(1, int(step))
    for colour, strokes in cmap.items():
        fill = tuple(int(channel) for channel in colour)
        for stroke in strokes:
            points = [(int(px) - x, int(py) - y) for px, py in stroke]
            if len(points) >= 2:
                draw.line(points, fill=fill, width=brush)
            elif points:
                px, py = points[0]
                half = brush // 2
                draw.rectangle(
                    [px - half, py - half, px + half, py + half], fill=fill
                )
    return image


def render_fills(grid, canvas, origin, step: int) -> Image.Image:
    """Render a quantised colour grid as ``step``-sized cells on ``canvas``.

    ``origin`` is the ``(x, y)`` the grid starts at in screen coordinates
    (``fit_to_canvas``'s offset). ``None`` cells are left as background.
    """
    x, y, width, height = (int(v) for v in canvas)
    width, height = max(1, width), max(1, height)
    origin_x, origin_y = int(origin[0]), int(origin[1])
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    cell = max(1, int(step))
    for row_index, row in enumerate(grid):
        top = origin_y - y + row_index * cell
        for col_index, colour in enumerate(row):
            if colour is None:
                continue
            left = origin_x - x + col_index * cell
            draw.rectangle(
                [left, top, left + cell - 1, top + cell - 1],
                fill=tuple(int(channel) for channel in colour),
            )
    return image


def _content_box(cmap, canvas, margin: int = 2):
    """Bounding box (canvas coords) of every stroke, or ``None`` if empty."""
    xs = []
    ys = []
    for strokes in cmap.values():
        for stroke in strokes:
            for px, py in stroke:
                xs.append(px)
                ys.append(py)
    if not xs:
        return None
    x, y, w, h = (int(v) for v in canvas)
    left = max(x, int(min(xs)) - margin)
    top = max(y, int(min(ys)) - margin)
    right = min(x + w, int(max(xs)) + margin + 1)
    bottom = min(y + h, int(max(ys)) + margin + 1)
    if right - left < 2 or bottom - top < 2:
        return None
    return left, top, right, bottom


def preview(image, canvas, step: int, palette, metric, flags: int, mode: str,
            plan_kwargs: Dict) -> Tuple[Image.Image, str]:
    """Plan + render one preview frame. Returns ``(PIL.Image, meta_text)``.

    The frame is cropped to the content the plan actually covers (the fitted
    source rectangle, or the strokes' bounds for line modes), so the preview
    carries no baked-in canvas whitespace and Compare shows matching framing.
    """
    x, y, w, h = (int(v) for v in canvas)
    if mode in LINE_MODES:
        cmap = planner.plan_image(
            image, canvas, step, palette, metric, flags, mode, **plan_kwargs
        )
        strokes = sum(len(lines) for lines in cmap.values())
        frame = render_plan(cmap, canvas, step, mode)
        box = _content_box(cmap, canvas)
        if box is not None:
            frame = frame.crop((box[0] - x, box[1] - y, box[2] - x, box[3] - y))
        return frame, f"{strokes} strokes"

    source, (grid_w, grid_h), origin_x, origin_y = planner.fit_to_canvas(
        image, canvas, step
    )
    grid = planner.quantize_image(
        source, (grid_w, grid_h), palette, metric, flags
    )
    frame = render_fills(grid, canvas, (origin_x, origin_y), step)
    left = max(0, origin_x - x)
    top = max(0, origin_y - y)
    right = min(w, origin_x - x + grid_w * step)
    bottom = min(h, origin_y - y + grid_h * step)
    if right > left and bottom > top:
        frame = frame.crop((left, top, right, bottom))
    return frame, f"{grid_w} \u00d7 {grid_h} cells"
