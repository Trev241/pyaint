"""Pure image planning: image/grid -> stroke map (``cmap``).

This is the app-agnostic half of the engine. It turns an image into a *plan* —
a mapping of palette colours to the runs that draw it — using **no screen
access and no session state**. Given the same image, palette, and settings it
returns the same plan every time, which is what makes it headlessly testable
and cacheable.

The other half lives in :mod:`pyaint.bot`: :class:`~pyaint.bot.Bot` is the
facade that gathers the taught environment (canvas, palette, settings) and
hands it here, and the drawing *executor* (``Bot.draw``) replays the plan
through :mod:`pyaint.painter`.

Pipeline::

    image --fit--> source --quantize_image--> colour grid --plan--> cmap

:func:`quantize_image` is the shared boundary: every planning mode consumes
the same colour grid. It downscales by supersampling each output cell and
voting in palette space, so isolated compression / anti-aliasing artifacts are
outvoted before planning instead of being compensated for later.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PIL import Image

from pyaint import utils

try:  # numpy powers palette-aware downsampling; fall back if unavailable
    import numpy as _np
except ImportError:  # pragma: no cover - only when numpy is not installed
    _np = None

# ---------------------------------------------------------------------------
# Mode + flag constants. These are re-exported on ``Bot`` for backwards
# compatibility (``Bot.SLOTTED`` etc.); the canonical values live here.
# ---------------------------------------------------------------------------
SLOTTED = "slotted"
LAYERED = "layered"
OUTLINE = "outline"

IGNORE_WHITE = 1 << 0
IGNORE_TRANSPARENT = 1 << 1
ALPHA_CUTOFF = 128  # alpha below this counts as transparent
STROKE_DISTANCE = 1
#: Safety inset (px) applied to every edge of the taught canvas before fitting.
#: Some targets (e.g. skribbl) register a click a hair outside the drawable
#: area as a miss, so strokes are kept this far from the canvas border.
CANVAS_PADDING = 4
BLACK: Colour = (0, 0, 0)
OUTLINE_COLOUR = BLACK

Colour = Tuple[int, int, int]
Point = Tuple[int, int]
#: A stroke is an ordered list of canvas points. A two-point stroke is a plain
#: run (SLOTTED/LAYERED); longer strokes are traced polylines (OUTLINE).
Stroke = List[Point]
#: A stroke map: ``{(r, g, b): [[(x1, y1), (x2, y2), ...], ...]}``.
Cmap = Dict[Colour, List[Stroke]]
#: A quantised grid: ``grid[row][col] -> colour | None`` (``None`` = ignored).
ColourGrid = List[List[Optional[Colour]]]


# ---------------------------------------------------------------------------
# Geometry / raster helpers
# ---------------------------------------------------------------------------
def _resize_nearest(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """Nearest-neighbour resize, tolerating pre-9.1 Pillow."""
    try:
        return image.resize(size, resample=Image.Resampling.NEAREST)
    except AttributeError:
        return image.resize(size, resample=Image.NEAREST)  # type: ignore[attr-defined]


def _inset_canvas(canvas, pad: int = CANVAS_PADDING):
    """Shrink a ``(x, y, w, h)`` canvas by ``pad`` on every edge.

    The inset is clamped so it never eats more than half the smaller
    dimension, keeping tiny canvases (tests, thumbnails) at least 1px wide.
    """
    x, y, w, h = (int(v) for v in canvas)
    p = max(0, min(int(pad), (w - 1) // 2, (h - 1) // 2))
    return x + p, y + p, w - 2 * p, h - 2 * p


def fit_to_canvas(image: Image.Image, canvas, step: int):
    """Fit ``image`` into the canvas (centred), minus a safety inset.

    Returns ``(source, (tw, th), xo, yo)``: the full-resolution source image,
    the output grid size, and the canvas origin. Downsampling is left to
    :func:`quantize_image` so it can vote in palette space. The canvas is
    inset by :data:`CANVAS_PADDING` so edge strokes stay off the border.
    """
    x, y, cw, ch = _inset_canvas(canvas)
    tw, th = (int(p // step) for p in utils.adjusted_img_size(image, (cw, ch)))
    xo = x + ((cw - tw * step) // 2)
    yo = y + ((ch - th * step) // 2)
    return image, (tw, th), xo, yo


def fit_region(image: Image.Image, region, canvas, step: int, canvas_target=None):
    """Crop ``region`` and scale/position it.

    ``canvas_target`` (``(x, y, w, h)``) pins the drawing to a canvas rectangle;
    otherwise the crop is scaled to fit the canvas and centred. Returns
    ``(source, (tw, th), xo, yo)`` -- the full-resolution crop, the output grid
    size, and the canvas origin.
    """
    x1, y1, x2, y2 = region
    cropped = image.crop((x1, y1, x2, y2))
    canvas_x, canvas_y, canvas_w, canvas_h = _inset_canvas(canvas)
    cropped_w, cropped_h = cropped.size

    if canvas_target is not None:
        target_x, target_y, target_w, target_h = _inset_canvas(canvas_target)
        scale = min(target_w / cropped_w, target_h / cropped_h)
        xo, yo = target_x, target_y
    else:
        scale = min(canvas_w / cropped_w, canvas_h / cropped_h)
        scaled_w = int(cropped_w * scale)
        scaled_h = int(cropped_h * scale)
        xo = canvas_x + (canvas_w - scaled_w) // 2
        yo = canvas_y + (canvas_h - scaled_h) // 2

    scaled_w = int(cropped_w * scale)
    scaled_h = int(cropped_h * scale)
    tw, th = scaled_w // step, scaled_h // step
    return cropped, (tw, th), xo, yo


# ---------------------------------------------------------------------------
# Quantise: pixels -> colour grid
# ---------------------------------------------------------------------------
def quantize(pix, w: int, h: int, palette, metric, flags: int) -> ColourGrid:
    """Map every pixel to the nearest palette colour.

    ``pix`` is a PIL pixel-access object. Cells whose alpha is below
    :data:`ALPHA_CUTOFF` (when :data:`IGNORE_TRANSPARENT` is set) become
    ``None``. Returns a row-major grid: ``grid[row][col] -> colour | None``.
    """
    ignore_transparent = bool(flags & IGNORE_TRANSPARENT)
    memo: Dict[Colour, Colour] = {}
    grid: ColourGrid = []
    for i in range(h):
        row: List[Optional[Colour]] = []
        for j in range(w):
            pixel = pix[j, i]
            alpha = pixel[3] if len(pixel) > 3 else 255
            if ignore_transparent and alpha < ALPHA_CUTOFF:
                row.append(None)
                continue
            key = (pixel[0], pixel[1], pixel[2])
            if key not in memo:
                memo[key] = palette.nearest_color(key, metric)
            row.append(memo[key])
        grid.append(row)
    return grid


#: Total source samples used when downsampling. The per-cell sample grid is
#: sized from this budget so noise is outvoted without quantizing the whole
#: source resolution for very large images.
_SAMPLE_BUDGET = 400_000


def quantize_image(image: Image.Image, size, palette, metric, flags: int) -> ColourGrid:
    """Quantize ``image`` into a ``size`` grid using palette-aware voting.

    Unlike :func:`quantize`, which snaps a single sampled pixel per cell, this
    maps each sampled source pixel to its nearest palette colour and takes the
    **majority** per output cell. Voting in palette space removes isolated
    compression / anti-aliasing artifacts without inventing blend colours, so
    they never reach the LAYERED / SLOTTED / OUTLINE planners. Falls back to
    nearest-neighbour sampling when numpy is unavailable.
    """
    tw, th = size
    if tw <= 0 or th <= 0:
        return []
    if _np is None or not hasattr(palette, "nearest_color_indices"):
        small = _resize_nearest(image, (tw, th))
        return quantize(small.load(), tw, th, palette, metric, flags)

    colors = palette.color_list
    if not colors:
        return [[None] * tw for _ in range(th)]

    scale = int(round((_SAMPLE_BUDGET / (tw * th)) ** 0.5))
    scale = max(1, min(8, scale))

    # Supersample each output cell into a scale x scale block. Nearest keeps
    # real palette colours (no blends), and the block spreads the vote across
    # the cell's whole source area.
    sub = _resize_nearest(image, (tw * scale, th * scale))
    arr = _np.asarray(sub, dtype=_np.uint8)
    rgb = arr[:, :, :3].reshape(-1, 3)
    if arr.shape[2] > 3:
        alpha = arr[:, :, 3].reshape(-1)
    else:
        alpha = _np.full(rgb.shape[0], 255, dtype=_np.uint8)

    nearest = palette.nearest_color_indices(rgb, metric)
    none_category = len(colors)
    if flags & IGNORE_TRANSPARENT:
        categories = _np.where(alpha < ALPHA_CUTOFF, none_category, nearest)
    else:
        categories = nearest
    categories = _np.asarray(categories, dtype=_np.int64).reshape(th, scale, tw, scale)

    cell = (
        _np.arange(th)[:, None, None, None] * tw + _np.arange(tw)[None, None, :, None]
    )
    combined = (cell * (none_category + 1) + categories).ravel()
    counts = _np.bincount(combined, minlength=th * tw * (none_category + 1)).reshape(
        th, tw, none_category + 1
    )
    mode = counts.argmax(axis=2)

    return [
        [None if mode[i, j] == none_category else colors[mode[i, j]] for j in range(tw)]
        for i in range(th)
    ]


# ---------------------------------------------------------------------------
# Plan (rows / layered): colour grid -> cmap
# ---------------------------------------------------------------------------
def _emit_run(
    cmap, table_lines, table_colors, col_freq, row, color, start, end, mode, flags
):
    """Record one horizontal run as a stroke (or a layer-table row)."""
    if color is None:
        # Transparent run: never painted, but in Layered it must still be
        # recorded so merged spans break at it instead of bridging over it.
        if mode == LAYERED:
            table_lines[row].append((None, (start, end)))
        return
    if mode == SLOTTED:
        if color == (255, 255, 255) and flags & IGNORE_WHITE:
            return
        cmap.setdefault(color, []).append([start, end])
    else:
        table_lines[row].append((color, (start, end)))
        table_colors[row].add(color)
        col_freq[color] = col_freq.get(color, 0) + end[0] - start[0] + 1


def _merge_layers(cmap, table_lines, table_colors, col_freq, flags):
    """Merge lower-layer runs into fewer strokes (LAYERED mode only)."""
    # Sort colors in decreasing order of their frequency and maintain a
    # height level index for each color.
    col_order = tuple(
        k for k, _ in sorted(col_freq.items(), key=lambda item: item[1], reverse=True)
    )
    col_index = {col_order[i]: i for i in range(len(col_order))}

    # Lines of lower layer colors can be merged into fewer strokes since
    # they will be repainted again by colors from a higher layer.
    for idc, col in enumerate(col_order):
        for idr, row in enumerate(table_lines):
            if col not in table_colors[idr] or (
                col == (255, 255, 255) and flags & IGNORE_WHITE
            ):
                continue

            start, end, exposed = None, None, False
            for idl, line in enumerate(row):
                # A transparent run ranks below every colour, so it always
                # breaks a span: it is never bridged and never painted.
                rank = -1 if line[0] is None else col_index[line[0]]
                if idc <= rank:
                    start = line[1][0] if start is None else start
                    end = line[1][1]
                    exposed = exposed or idc == rank
                if start is not None and (idc > rank or idl == len(row) - 1):
                    if exposed:
                        cmap.setdefault(col, []).append([start, end])
                    start, exposed = None, False
    return cmap


def plan_rows(
    grid: ColourGrid, xo: int, yo: int, step: int, flags: int, mode: str
) -> Cmap:
    """Run-length encode a quantised grid into a stroke map (``cmap``)."""
    cmap: Cmap = {}
    col_freq: Dict[Colour, int] = {}
    table_lines: List[list] = []
    table_colors: List[set] = []
    y = yo
    for i, row in enumerate(grid):
        if mode == LAYERED:
            table_lines.append(list())
            table_colors.append(set())

        x = xo
        start = (x, y)
        old_col = None
        for j, col in enumerate(row):
            if j > 0 and old_col != col:
                _emit_run(
                    cmap,
                    table_lines,
                    table_colors,
                    col_freq,
                    i,
                    old_col,
                    start,
                    (x - step, y),
                    mode,
                    flags,
                )
                start = (x, y)
            old_col = col
            x += step

        # Close the run that contains the final pixel of the row.
        _emit_run(
            cmap,
            table_lines,
            table_colors,
            col_freq,
            i,
            old_col,
            start,
            (x - step, y),
            mode,
            flags,
        )
        y += step

    if mode == SLOTTED:
        return cmap
    return _merge_layers(cmap, table_lines, table_colors, col_freq, flags)


# ---------------------------------------------------------------------------
# Outline / region planning
# ---------------------------------------------------------------------------
def plan_regions(
    grid: ColourGrid,
    xo: int,
    yo: int,
    step: int,
    flags: int,
    mode: str = OUTLINE,
    stroke_distance: int = STROKE_DISTANCE,
    palette=None,
) -> Cmap:
    """Plan an outline-and-fill stroke map from the quantised colour grid.

    Traces region boundaries as strokes in :data:`OUTLINE_COLOUR`.

    Args:
        grid: row-major ``grid[row][col] -> colour | None`` (from
            :func:`quantize`).
        xo, yo: canvas coordinates of the grid's top-left cell.
        step: cell size in pixels.
        flags: :data:`IGNORE_WHITE` / :data:`IGNORE_TRANSPARENT`.
        mode: :data:`OUTLINE`.
        stroke_distance: Retained for API / cache compatibility. It no longer
            changes the plan (every traced contour is one stroke).
        palette: optional :class:`~pyaint.palette.Palette`. The planner is given
            the grid's colours already, but this exposes the swatch set, order
            and screen positions to region logic.

    Returns:
        A :data:`Cmap` sharing the shape :func:`plan_rows` returns, but with
        each value a list of :data:`Stroke` (point lists): one closed polyline
        per traced contour, all in :data:`OUTLINE_COLOUR`.
    """
    return _outline(grid, xo, yo, step, stroke_distance, palette)


#: Contours enclosing fewer than this many grid cells are noise; skip them.
_MIN_CONTOUR_AREA = 10


def _outline(
    grid: ColourGrid,
    xo: int,
    yo: int,
    step: int,
    stroke_distance: int = STROKE_DISTANCE,
    palette=None,
):
    """Trace region boundaries and emit one closed polyline per contour.

    Each region's boundary is walked as a loop of unit lattice edges, so the
    executor can replay it as one continuous drag instead of one stroke per
    edge. Implemented with stdlib/Pillow types only (no OpenCV or NumPy) so
    the frozen build stays dependency-light.

    ``stroke_distance`` is retained only for API / cache compatibility; it no
    longer affects the result (a contour is always one stroke).
    """
    if not grid:
        return {}

    colors = (
        list(palette.color_list)
        if palette is not None
        else sorted({c for row in grid for c in row if c is not None})
    )

    rows = len(grid)
    strokes: List[Stroke] = []
    for color in colors:
        for loop in _trace_contours(grid, color, rows):
            if _contour_area(loop) < _MIN_CONTOUR_AREA:
                continue
            simplified = _drop_collinear(loop)
            if len(simplified) < 3:
                continue
            points: Stroke = [
                (xo + point[1] * step, yo + point[0] * step) for point in simplified
            ]
            points.append(points[0])  # close the loop for one continuous drag
            strokes.append(points)

    return {OUTLINE_COLOUR: strokes} if strokes else {}


def _trace_contours(grid: ColourGrid, color, rows: int) -> List[List[Point]]:
    """Return the boundary loops of every region of ``color`` as corner paths.

    A boundary edge is directed so the coloured cell always sits to its left;
    that keeps in/out degree balanced at every lattice vertex, so each walk is
    guaranteed to close. Loops are lists of ``(row, col)`` lattice corners.
    """

    def filled(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < len(grid[r]) and grid[r][c] == color

    edges: Dict[Point, List[Point]] = {}

    def add(src: Point, dst: Point) -> None:
        edges.setdefault(src, []).append(dst)

    for r in range(rows):
        for c in range(len(grid[r])):
            if not filled(r, c):
                continue
            if not filled(r - 1, c):  # top edge -> interior below, travel left
                add((r, c + 1), (r, c))
            if not filled(r + 1, c):  # bottom edge -> interior above, travel right
                add((r + 1, c), (r + 1, c + 1))
            if not filled(r, c - 1):  # left edge -> interior right, travel down
                add((r, c), (r + 1, c))
            if not filled(r, c + 1):  # right edge -> interior left, travel up
                add((r + 1, c + 1), (r, c + 1))

    loops: List[List[Point]] = []
    while edges:
        start = next(iter(edges))
        loop = [start]
        current = start
        closed = False
        while True:
            outgoing = edges.get(current)
            if not outgoing:
                break
            nxt = outgoing.pop()
            if not outgoing:
                del edges[current]
            if nxt == start:
                closed = True
                break
            loop.append(nxt)
            current = nxt
        if closed and len(loop) >= 4:
            loops.append(loop)
    return loops


def _drop_collinear(points: List[Point]) -> List[Point]:
    """Drop interior corners that lie on a straight run of the loop."""
    if len(points) <= 3:
        return points
    kept: List[Point] = []
    count = len(points)
    for index, current in enumerate(points):
        prev = points[index - 1]
        nxt = points[(index + 1) % count]
        cross = (current[0] - prev[0]) * (nxt[1] - current[1]) - (
            current[1] - prev[1]
        ) * (nxt[0] - current[0])
        if cross != 0:
            kept.append(current)
    return kept or points


def _contour_area(points: List[Point]) -> float:
    """Absolute polygon area (in grid cells) via the shoelace formula."""
    area = 0
    count = len(points)
    for index, (r, c) in enumerate(points):
        nxt_r, nxt_c = points[(index + 1) % count]
        area += c * nxt_r - nxt_c * r
    return abs(area) / 2.0


def plan(
    grid: ColourGrid,
    xo: int,
    yo: int,
    step: int,
    flags: int,
    mode: str,
    stroke_distance: int = STROKE_DISTANCE,
    palette=None,
) -> Cmap:
    """Plan ``grid`` into a stroke map using the requested ``mode``.

    ``stroke_distance`` is accepted for compatibility and ignored by the
    outline planner; ``palette`` is forwarded to :func:`plan_regions`.
    """
    if mode == OUTLINE:
        return plan_regions(grid, xo, yo, step, flags, mode, stroke_distance, palette)
    return plan_rows(grid, xo, yo, step, flags, mode)


# ---------------------------------------------------------------------------
# Whole-image entry points (fit + quantise + plan)
# ---------------------------------------------------------------------------
def plan_image(
    image: Image.Image,
    canvas,
    step: int,
    palette,
    metric,
    flags: int,
    mode: str,
    stroke_distance: int = STROKE_DISTANCE,
) -> Cmap:
    """Fit + quantise + plan a full image. Returns a stroke map (``cmap``)."""
    source, (tw, th), xo, yo = fit_to_canvas(image, canvas, step)
    grid = quantize_image(source, (tw, th), palette, metric, flags)
    return plan(grid, xo, yo, step, flags, mode, stroke_distance, palette)


def plan_region_image(
    image: Image.Image,
    region,
    canvas,
    step: int,
    palette,
    metric,
    flags: int,
    mode: str,
    canvas_target=None,
    stroke_distance: int = STROKE_DISTANCE,
) -> Cmap:
    """Fit + quantise + plan a sub-region. Returns a stroke map (``cmap``)."""
    source, (tw, th), xo, yo = fit_region(image, region, canvas, step, canvas_target)
    grid = quantize_image(source, (tw, th), palette, metric, flags)
    return plan(grid, xo, yo, step, flags, mode, stroke_distance, palette)
