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

import math
import os
from typing import Dict, List, Optional, Tuple

from PIL import Image

from pyaint import utils

# import numpy as np
import cv2

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

# ---------------------------------------------------------------------------
# Outline cleaner defaults (INSTRUCTIONS.md pipeline). Distances are in canvas
# pixels and areas in grid cells; the planner scales them to the source
# resolution before running the label-map pipeline (see :func:`plan_outline`).
# ---------------------------------------------------------------------------
#: Bilateral-filter strength used before quantising (0 disables smoothing).
OUTLINE_SMOOTHING = 5
#: Lightness weight when matching a pixel to the palette (higher favours
#: matching brightness over hue).
OUTLINE_LIGHTNESS_WEIGHT = 2.0
#: Mean Lab step below which two touching components merge. ``0`` disables the
#: soft-boundary merge. ~2-3 keeps subtle shading, 4-6 keeps only clear steps.
OUTLINE_STEP_THRESHOLD = 4.0
#: Inscribed radius (canvas px) below which a component is "thin" (outlines,
#: lashes) and protected from the soft-boundary merge.
OUTLINE_THIN_WIDTH = 2.0
#: Max canvas-pixel gap between two open stroke endpoints for them to chain.
OUTLINE_JOIN_DISTANCE = 6.0
#: Components up to this many cells may merge into a colour-similar neighbour.
OUTLINE_SMALL_AREA = 12
#: Components below this area merge regardless of colour.
OUTLINE_TINY_AREA = 4
#: Lab distance below which a ``small_area`` component counts as colour-similar.
OUTLINE_SIMILAR_COLOR = 10.0
#: Radius (px) painted as "already drawn" for geometric seam dedupe.
OUTLINE_COVER_RADIUS = 2
#: A duplicate stretch shorter than this many points is kept, not cut.
OUTLINE_MIN_DROP_RUN = 30
#: Open strokes shorter than this many px are dropped (closed loops survive).
OUTLINE_MIN_STROKE = 8
#: Raw contour point floor; shorter contours are ignored.
OUTLINE_MIN_POINTS = 8
#: Polygon simplification tolerance in canvas pixels (1.0 - 1.5 recommended).
OUTLINE_EPSILON = 1.2
#: Developer flag: ``PYAINT_DEBUG_LABELS=1`` writes each label-map stage, a
#: removed-boundary overlay and a stroke view so the pipeline can be eyeballed.
#: Path overridable with the ``_PATH`` var (stages share its stem).
OUTLINE_DEBUG = bool(os.environ.get("PYAINT_DEBUG_LABELS"))
OUTLINE_DEBUG_PATH = os.environ.get(
    "PYAINT_DEBUG_LABELS_PATH", os.path.join("build", "debug_labels.png")
)

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

#: Sample grid budget for :func:`quantize_image`'s ``source_quality`` mode. The
#: vote table is int64, so even a very large source is bounded by this many
#: supersample pixels instead of its full resolution.
_SOURCE_SAMPLE_BUDGET = 16_000_000


def _supersample_scale(image: Image.Image, size, source_quality: bool) -> int:
    """Return the samples-per-output-cell edge used by :func:`quantize_image`.

    The default budget samples a handful of pixels per cell: cheap, but it can
    under-sample a thin anti-aliased line inconsistently, so the line wins in
    one cell and loses in the next and its contour fragments. ``source_quality``
    instead scales the sample grid to at least the source resolution, so every
    source pixel casts a vote and a thin line is cleanly resolved (kept or
    outvoted) instead of broken up across neighbouring cells.
    """
    tw, th = size
    if not source_quality:
        scale = int(round((_SAMPLE_BUDGET / (tw * th)) ** 0.5))
        return max(1, min(8, scale))

    # Ceiling division so the sample grid covers every source pixel.
    scale = max(1, -(-image.width // tw), -(-image.height // th))
    budget = int((_SOURCE_SAMPLE_BUDGET / (tw * th)) ** 0.5)
    return max(1, min(scale, budget))


def quantize_image(
    image: Image.Image,
    size,
    palette,
    metric,
    flags: int,
    source_quality: bool = False,
) -> ColourGrid:
    """Quantize ``image`` into a ``size`` grid using palette-aware voting.

    Unlike :func:`quantize`, which snaps a single sampled pixel per cell, this
    maps each sampled source pixel to its nearest palette colour and takes the
    **majority** per output cell. Voting in palette space removes isolated
    compression / anti-aliasing artifacts without inventing blend colours, so
    they never reach the LAYERED / SLOTTED / OUTLINE planners. Falls back to
    nearest-neighbour sampling when numpy is unavailable.

    ``source_quality`` supersamples at the source resolution (see
    :func:`_supersample_scale`). OUTLINE enables it so a thin anti-aliased
    outline votes consistently instead of fragmenting into tiny regions.
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

    scale = _supersample_scale(image, size, source_quality)

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
    morphology: bool = False,
    double_edges: bool = False,
) -> Cmap:
    """Plan an outline-and-fill stroke map from the quantised colour grid.

    Traces region boundaries as strokes in :data:`OUTLINE_COLOUR`, drawing each
    edge shared by two regions only once.

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
        morphology: Opt-in despeckling of each region mask (open then close)
            before tracing, so anti-aliased specks and 1px breaks do not become
            tiny contours. Off by default because it also erases genuine 1px
            detail.

    Returns:
        A :data:`Cmap` sharing the shape :func:`plan_rows` returns, but with
        each value a list of :data:`Stroke` (point lists): one polyline
        per traced contour, all in :data:`OUTLINE_COLOUR`.
    """
    return _outline(
        grid, xo, yo, step, stroke_distance, palette, morphology, double_edges
    )


# TODO: Remove the per-colour mask morphology now that the label-map cleaner
# (``plan_outline``) handles anti-aliasing. The app's OUTLINE mode no longer
# uses it (the UI control was removed), but the ``morphology`` argument is kept
# for the grid-only tracer. To delete: drop this kernel, ``_despeckle_mask``,
# the ``morphology`` args on ``plan_regions``/``_outline``/``plan``/
# ``plan_image``/``plan_region_image``, ``Bot.outline_morphology``, the
# ``outline_morphology`` terms in ``cache.py``, and the morphology tests.
#: 3x3 ellipse used to despeckle each region mask before contour tracing.
_MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


def _despeckle_mask(mask):
    """TEMPORARY experiment: remove anti-aliasing specks / bridge 1px breaks.

    See the TODO above. A 3x3 kernel also erases genuine 1px detail, so this is
    opt-in and slated for removal.
    """
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _MORPH_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _MORPH_KERNEL)
    return mask


def _outline(
    grid: ColourGrid,
    xo: int,
    yo: int,
    step: int,
    stroke_distance: int = STROKE_DISTANCE,
    palette=None,
    morphology: bool = False,
    double_edges: bool = False,
):
    """Trace region boundaries into polylines.

    By default each region's contour from ``cv2.findContours`` is split into
    runs wherever it crosses a boundary owned by a lower-numbered region, so a
    shared curve is traced exactly once (each run becomes one :data:`Stroke`).

    With ``double_edges`` the tracer instead follows every region's boundary
    along cell *edges* and emits its full closed loop. Shared boundaries are
    then drawn by both neighbours, but on the same geometric segment, so the
    doubled line reads as a single line rather than a two-pixel band. This
    avoids fragmenting a region into a run per shared edge.

    ``stroke_distance`` is retained only for API / cache compatibility; it no
    longer affects the result.
    """
    strokes: List[Stroke] = []
    ids: Dict[Colour, int] = {}

    def brightness(color):
        if color is None:
            return 999

        r, g, b = color  # swap the order if your colors are BGR
        return 0.299 * r + 0.587 * g + 0.114 * b

    # Map each colour to an id (lower = darker) and the grid to a label matrix,
    # so a region mask is just ``labels == id``. Dark outline colours get the
    # lower ids, so they own (trace) the edges they share with a lighter fill.
    unique_colors = {cell for row in grid for cell in row}
    ordered = sorted(unique_colors, key=brightness)
    ids = {color: i + 1 for i, color in enumerate(ordered)}

    labels = _np.array(
        [[ids[cell] for cell in row] for row in grid],
        dtype=_np.uint8,
    )

    if double_edges:
        return _outline_double(labels, ordered, xo, yo, step)

    padded = _np.pad(labels, 1, constant_values=0)

    for region_id in ids.values():
        mask = (labels == region_id).astype(_np.uint8)
        if morphology:
            # Anti-aliased edges leave 1px specks and pinholes; clean them here
            # so they do not each become a tiny contour to trace.
            mask = _despeckle_mask(mask)
        contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for contour in contours:
            points = [(int(p[0][0]), int(p[0][1])) for p in contour]
            keep_flags = [
                not _touches_lower_region(x, y, region_id, padded) for x, y in points
            ]

            for run, closed in _split_into_runs(points, keep_flags):
                if len(run) < 2:
                    continue

                simplified = _simplify(run, closed)
                stroke = [(xo + x * step, yo + y * step) for x, y in simplified]

                if closed:
                    stroke.append(stroke[0])
                if len(stroke) >= 2:
                    strokes.append(stroke)

    return {OUTLINE_COLOUR: strokes} if strokes else {}


def _outline_double(labels, ordered, xo, yo, step) -> Cmap:
    """One closed cell-edge loop per region (shared edges drawn twice)."""
    strokes: List[Stroke] = []
    for region_id in range(1, len(ordered) + 1):
        for loop in _trace_region_boundaries(labels, region_id):
            simplified = _simplify(loop, closed=True)
            if len(simplified) < 2:
                continue
            stroke = [(xo + c * step, yo + r * step) for r, c in simplified]
            if stroke[0] != stroke[-1]:
                stroke.append(stroke[0])
            if len(stroke) >= 2:
                strokes.append(stroke)
    return {OUTLINE_COLOUR: strokes} if strokes else {}


def _region_boundary_edges(labels, region_id):
    """Directed cell-edge boundary of one region, interior kept on the left.

    Corners are ``(row, col)`` on the cell grid. Because each region walks its
    own edges, a boundary shared by two neighbours lands on the same geometric
    segment instead of the two parallel cell-centre contours that
    ``cv2.findContours`` produces.
    """
    height, width = labels.shape
    edges = []
    for r in range(height):
        for c in range(width):
            if int(labels[r][c]) != region_id:
                continue
            if r == 0 or int(labels[r - 1][c]) != region_id:
                edges.append(((r, c + 1), (r, c)))  # top side, west
            if r == height - 1 or int(labels[r + 1][c]) != region_id:
                edges.append(((r + 1, c), (r + 1, c + 1)))  # bottom, east
            if c == 0 or int(labels[r][c - 1]) != region_id:
                edges.append(((r, c), (r + 1, c)))  # left, south
            if c == width - 1 or int(labels[r][c + 1]) != region_id:
                edges.append(((r + 1, c + 1), (r, c + 1)))  # right, north
    return edges


def _turn_angle(in_dir, out_dir):
    cross = in_dir[0] * out_dir[1] - in_dir[1] * out_dir[0]
    dot = in_dir[0] * out_dir[0] + in_dir[1] * out_dir[1]
    return math.atan2(cross, dot)


def _trace_region_boundaries(labels, region_id):
    """Follow a region's directed boundary edges into closed corner loops.

    The directed graph is balanced (every corner has equal in/out degree), so
    any deterministic choice at a diagonal pinch still decomposes it into
    closed trails; preferring the straightest turn keeps the paths tidy.
    """
    remaining = set(_region_boundary_edges(labels, region_id))
    outgoing: Dict = {}
    for start, end in remaining:
        outgoing.setdefault(start, []).append(end)

    loops = []
    while remaining:
        first = next(iter(remaining))
        remaining.discard(first)
        path = [first[0], first[1]]
        current = first
        while current[1] != path[0]:
            options = [
                end
                for end in outgoing.get(current[1], ())
                if (current[1], end) in remaining
            ]
            if not options:
                break
            er, ec = current[1]
            in_dir = (er - current[0][0], ec - current[0][1])
            best, best_key = None, None
            for end in options:
                out_dir = (end[0] - er, end[1] - ec)
                angle = _turn_angle(in_dir, out_dir)
                key = (abs(angle), 0 if angle >= 0 else 1)
                if best is None or key < best_key:
                    best, best_key = end, key
            remaining.discard((current[1], best))
            path.append(best)
            current = (current[1], best)
        loops.append(path)
    return loops


def _touches_lower_region(x, y, region_id, padded_labels):
    """True when any of the 8 neighbours is a lower-numbered region.

    A shared edge belongs to the lower-numbered region, so the higher-numbered
    side drops it. ``padded_labels`` is :data:`labels` padded by one cell.
    """

    offsets = [[-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1]]

    for dx, dy in offsets:
        # If we detect a neighbouring contour cell with a lower colour ID,
        # we must drop this cell to avoid double drawing.
        neighbour_id = padded_labels[y + 1 + dy, x + 1 + dx]
        if 0 < neighbour_id < region_id:
            return True

    return False


def _split_into_runs(points, keep_flags):
    if all(keep_flags):
        return [(points, True)]
    if not any(keep_flags):
        return []

    start = keep_flags.index(False)
    points = points[start:] + points[:start]
    keep_flags = keep_flags[start:] + keep_flags[:start]

    runs = []
    current_run = []
    for point, keep in zip(points, keep_flags):
        if keep:
            current_run.append(point)
        elif current_run:
            runs.append(current_run)
            current_run = []

    if current_run:
        runs.append(current_run)

    return [(run, False) for run in runs]


def _simplify(points, closed, epsilon=0.5):
    array = _np.array(points, dtype=_np.int32).reshape(-1, 1, 2)
    simplified = cv2.approxPolyDP(array, epsilon=epsilon, closed=closed)
    return [[int(p[0][0]), int(p[0][1])] for p in simplified]


# ---------------------------------------------------------------------------
# Outline cleaner: source -> label map -> deduped contours (INSTRUCTIONS.md).
# The helpers below are the label-map pipeline. They operate on integer region
# ids (0 = ignored/background) and are scaled from canvas units to source
# pixels by :func:`plan_outline`.
# ---------------------------------------------------------------------------
def _build_palette(palette_rgb):
    """Palette as a true-scale Lab array; row 0 is a dummy so index == id.

    Uses ``cv2`` on float RGB so ``L`` is in 0-100 and ``a``/``b`` on the
    standard CIELAB scale, matching ``skimage.color.rgb2lab`` (and therefore the
    thresholds in ``INSTRUCTIONS.md``) without the heavier dependency.
    """
    rgb = _np.array(list(palette_rgb), dtype=_np.float32).reshape(-1, 1, 3) / 255.0
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(_np.float32)
    return _np.vstack([_np.zeros((1, 3), _np.float32), lab])


def _bilateral_params(level: float):
    """Map an outline smoothing level to ``cv2.bilateralFilter`` parameters.

    Level ``0`` disables smoothing. Level ``1`` reproduces the recipe's
    original ``(5, 30, 5)``; higher levels widen the kernel and raise the
    colour sigma. Returns ``(diameter, sigma_color, sigma_space)`` or ``None``.
    """
    level = int(round(level))
    if level <= 0:
        return None
    diameter = min(15, 5 + (level - 1))
    sigma_color = 30.0 + (level - 1) * 15.0
    return diameter, sigma_color, float(diameter)


def _quantize_labels(
    source_rgb, palette_lab, alpha, smooth_strength, ignore_transparent
):
    """Nearest-palette labels with edge-preserving smoothing and Lab weighting.

    ``source_rgb`` is an ``(H, W, 3)`` uint8 array, ``palette_lab`` a true-scale
    Lab lookup whose row 0 is the dummy background. Returns ``(labels, lab)``,
    where ``lab`` is the smoothed source in Lab (needed by the soft-boundary
    merge). Lightness is weighted up so colours that differ mainly in lightness
    stay distinct. When ``ignore_transparent`` is set and ``alpha`` is given,
    pixels below :data:`ALPHA_CUTOFF` become label 0.
    """
    image = source_rgb
    params = _bilateral_params(smooth_strength)
    if params is not None:
        diameter, sigma_color, sigma_space = params
        image = cv2.bilateralFilter(
            _np.ascontiguousarray(image), diameter, sigma_color, sigma_space
        )
    image_lab = cv2.cvtColor(
        image.astype(_np.float32) / 255.0, cv2.COLOR_RGB2LAB
    ).astype(_np.float32)
    colors = palette_lab[1:]
    weights = _np.array(
        [OUTLINE_LIGHTNESS_WEIGHT, 1.0, 1.0], _np.float32
    )
    labels = _np.zeros(image_lab.shape[:2], _np.int32)
    for row in range(image_lab.shape[0]):
        gaps = (image_lab[row][:, None, :] - colors[None, :, :]) * weights
        labels[row] = _np.linalg.norm(gaps, axis=2).argmin(axis=1) + 1
    if ignore_transparent and alpha is not None:
        labels[alpha < ALPHA_CUTOFF] = 0
    return labels, image_lab


def _label_components(labels):
    """Split each label into 4-connected components.

    Returns ``(comp, total)`` where ``comp`` is an ``int32`` map (0 =
    background/ignored) and ``total`` is the number of foreground components.
    """
    comp = _np.zeros(labels.shape, _np.int32)
    total = 0
    for region_id in _np.unique(labels):
        if region_id == 0:
            continue
        count, component_map = cv2.connectedComponents(
            (labels == region_id).astype(_np.uint8), connectivity=4
        )
        inside = component_map > 0
        comp[inside] = component_map[inside] + total
        total += count - 1
    return comp, total


def _component_thickness(labels, comp, total):
    """Max inscribed radius (px) of every component, indexed by component id."""
    thickness = _np.zeros(total + 1, _np.float32)
    for region_id in _np.unique(labels):
        if region_id == 0:
            continue
        mask = (labels == region_id).astype(_np.uint8)
        distance = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
        inside = mask > 0
        _np.maximum.at(thickness, comp[inside], distance[inside])
    return thickness


def _merge_soft_boundaries(
    labels, lab, palette_lab, step_threshold, protect_thin=True, thin_width=2.0
):
    """Remove soft tonal boundaries by merging touching low-contrast components.

    For every pair of touching components the mean Lab step across their shared
    boundary is measured; pairs below ``step_threshold`` merge (union-find, so
    a gradient chains into one region). Thin components -- whose inscribed
    radius is below ``thin_width``, such as outlines and lashes -- are protected
    when ``protect_thin`` is set. Each merged group takes the palette colour
    nearest its mean source colour. Runs at the source resolution and is the
    stage that stops shading, gradients and a soft shadow from being traced.
    """
    if step_threshold <= 0:
        return labels
    comp, total = _label_components(labels)
    if total == 0:
        return labels

    protected = _np.zeros(total + 1, bool)
    if protect_thin:
        protected = _component_thickness(labels, comp, total) < float(thin_width)
        protected[0] = True

    # Lab step across every 4-connected boundary between two components.
    first, second, steps = [], [], []
    pairs = (
        (comp[:, :-1], comp[:, 1:], lab[:, :-1], lab[:, 1:]),
        (comp[:-1, :], comp[1:, :], lab[:-1, :], lab[1:, :]),
    )
    for comp_a, comp_b, lab_a, lab_b in pairs:
        differs = (comp_a != comp_b) & (comp_a > 0) & (comp_b > 0)
        if not differs.any():
            continue
        first.append(_np.minimum(comp_a, comp_b)[differs])
        second.append(_np.maximum(comp_a, comp_b)[differs])
        steps.append(_np.linalg.norm(lab_a[differs] - lab_b[differs], axis=1))
    if not first:
        return labels
    first = _np.concatenate(first).astype(_np.int64)
    second = _np.concatenate(second).astype(_np.int64)
    steps = _np.concatenate(steps)

    # Mean step per touching pair.
    keys = first * _np.int64(total + 1) + second
    unique_keys, inverse = _np.unique(keys, return_inverse=True)
    mean_step = _np.bincount(inverse, weights=steps) / _np.bincount(inverse)

    parent = list(range(total + 1))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for key, step in zip(unique_keys.tolist(), mean_step.tolist()):
        a, b = divmod(key, total + 1)
        if step < step_threshold and not (protected[a] or protected[b]):
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_b] = root_a

    roots = _np.fromiter(
        (find(i) for i in range(total + 1)), dtype=_np.int64, count=total + 1
    )
    group = roots[comp]

    # One palette colour per merged group, from its mean source colour.
    flat = group.ravel()
    counts = _np.maximum(_np.bincount(flat, minlength=total + 1), 1)
    means = _np.stack(
        [
            _np.bincount(flat, weights=lab[..., c].ravel(), minlength=total + 1)
            / counts
            for c in range(3)
        ],
        axis=1,
    )
    # Compare against the real palette rows only (row 0 of ``palette_lab`` is
    # the dummy background), so the result is a valid 1..K region id.
    real = palette_lab[1:]
    gaps = _np.linalg.norm(means[:, None, :] - real[None, :, :], axis=2)
    result = (gaps.argmin(axis=1) + 1)[group].astype(_np.uint8)
    result[comp == 0] = 0
    return result


def _pick_merge_target(component_id, ring_ids, palette_lab, skip_ids=frozenset()):
    """Closest-colour neighbour among the labels around a component."""
    candidates = [
        int(n)
        for n in set(ring_ids.tolist())
        if int(n) != component_id and int(n) > 0 and int(n) not in skip_ids
    ]
    if not candidates:
        return None, None
    own = palette_lab[component_id]
    best, best_distance = None, None
    for candidate in candidates:
        distance = float(_np.linalg.norm(palette_lab[candidate] - own))
        if best_distance is None or distance < best_distance:
            best, best_distance = candidate, distance
    return best, best_distance


def _merge_small_regions(
    labels, palette_lab, small_area, tiny_area, similar_color, skip_ids=frozenset()
):
    """Absorb tiny components -- and small colour-close ones -- into a neighbour.

    Selective merging keeps a small high-contrast feature such as a pupil or an
    eyebrow (colour distance above ``similar_color`` and area above
    ``tiny_area``) while dropping anti-aliasing slivers. Run it twice so a chain
    of small regions collapses in one call sequence.
    """
    height, width = labels.shape
    cleaned = labels.copy()
    kernel = _np.ones((3, 3), _np.uint8)

    for region_id in _np.unique(labels):
        region_id = int(region_id)
        if region_id == 0 or region_id in skip_ids:
            continue
        mask = (labels == region_id).astype(_np.uint8)
        count, component_map, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )

        for c in range(1, count):
            area = stats[c, cv2.CC_STAT_AREA]
            if area >= small_area:
                continue

            x0 = max(stats[c, cv2.CC_STAT_LEFT] - 1, 0)
            y0 = max(stats[c, cv2.CC_STAT_TOP] - 1, 0)
            x1 = min(
                stats[c, cv2.CC_STAT_LEFT] + stats[c, cv2.CC_STAT_WIDTH] + 1,
                width,
            )
            y1 = min(
                stats[c, cv2.CC_STAT_TOP] + stats[c, cv2.CC_STAT_HEIGHT] + 1,
                height,
            )

            component = component_map[y0:y1, x0:x1] == c
            ring = cv2.dilate(component.astype(_np.uint8), kernel) > 0
            ring &= ~component
            ring_ids = labels[y0:y1, x0:x1][ring]

            target, distance = _pick_merge_target(
                region_id, ring_ids, palette_lab, skip_ids
            )
            if target is None:
                continue
            if area < tiny_area or distance < similar_color:
                view = cleaned[y0:y1, x0:x1]
                view[component] = target
    return cleaned


def _collect_contours(labels, min_points=OUTLINE_MIN_POINTS):
    """All raw contours from every region, as ``(x, y)`` lists, longest first."""
    contours_out = []
    for region_id in _np.unique(labels):
        if region_id == 0:
            continue
        mask = (labels == region_id).astype(_np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            if len(contour) >= min_points:
                contours_out.append([(int(p[0][0]), int(p[0][1])) for p in contour])
    contours_out.sort(key=len, reverse=True)
    return contours_out


def _boundary_pixels(labels):
    """Boolean map of pixels on a label boundary (used by the debug overlay)."""
    edge = _np.zeros(labels.shape, bool)
    dx = labels[:, 1:] != labels[:, :-1]
    dy = labels[1:, :] != labels[:-1, :]
    edge[:, 1:] |= dx
    edge[:, :-1] |= dx
    edge[1:, :] |= dy
    edge[:-1, :] |= dy
    return edge


def _find_covered_points(points, coverage):
    """True for each point that lies on an already-accepted stroke."""
    height, width = coverage.shape
    covered = []
    for x, y in points:
        covered.append(0 <= x < width and 0 <= y < height and bool(coverage[y, x]))
    return covered


def _paint_coverage(coverage, points, closed=True, radius=OUTLINE_COVER_RADIUS):
    """Mark an accepted stroke so later contours can dedupe against it."""
    if len(points) < 2:
        return
    array = _np.array(points, dtype=_np.int32).reshape(-1, 1, 2)
    cv2.polylines(coverage, [array], closed, 1, thickness=2 * radius + 1)


def _keep_short_drops(keep_flags, min_drop_run):
    """Only drop a stretch if it is at least ``min_drop_run`` points long."""
    flags = list(keep_flags)
    count = len(flags)
    if all(flags) or not any(flags):
        return flags
    start = flags.index(True)
    rotated = flags[start:] + flags[:start]
    i = 0
    while i < count:
        if rotated[i]:
            i += 1
            continue
        j = i
        while j < count and not rotated[j]:
            j += 1
        if j - i < min_drop_run:
            for k in range(i, j):
                rotated[k] = True
        i = j
    return rotated[count - start:] + rotated[:count - start]


def _join_strokes(strokes, max_distance):
    """Chain open strokes whose endpoints lie within ``max_distance``."""
    if max_distance <= 0 or len(strokes) < 2:
        return [list(stroke) for stroke in strokes]

    def cell_of(point):
        return (int(point[0] // max_distance), int(point[1] // max_distance))

    index = {}
    for stroke_id, stroke in enumerate(strokes):
        if stroke[0] == stroke[-1]:
            continue
        for end in (0, -1):
            index.setdefault(cell_of(stroke[end]), []).append((stroke_id, end))

    used = set()

    def nearest_free_endpoint(point):
        cx, cy = cell_of(point)
        best, best_distance = None, max_distance
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for stroke_id, end in index.get((cx + dx, cy + dy), []):
                    if stroke_id in used:
                        continue
                    other = strokes[stroke_id][end]
                    distance = (
                        (other[0] - point[0]) ** 2 + (other[1] - point[1]) ** 2
                    ) ** 0.5
                    if distance <= best_distance:
                        best, best_distance = (stroke_id, end), distance
        return best

    def extend_tail(chain):
        while True:
            found = nearest_free_endpoint(chain[-1])
            if found is None:
                return
            stroke_id, end = found
            used.add(stroke_id)
            addition = strokes[stroke_id]
            chain.extend(addition if end == 0 else addition[::-1])

    joined = []
    for stroke_id, stroke in enumerate(strokes):
        if stroke_id in used:
            continue
        used.add(stroke_id)
        chain = list(stroke)
        if stroke[0] != stroke[-1]:
            extend_tail(chain)
            chain.reverse()
            extend_tail(chain)
        joined.append(chain)
    return joined


def _is_closed(stroke):
    return len(stroke) >= 2 and stroke[0] == stroke[-1]


def _path_length(stroke):
    total = 0.0
    for (x0, y0), (x1, y1) in zip(stroke, stroke[1:]):
        total += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    return total


def _label_debug_image(labels, ordered_palette):
    """Render a label map with its palette colours (BGR, for cv2)."""
    lookup = _np.zeros((len(ordered_palette) + 1, 3), _np.uint8)
    for i, (r, g, b) in enumerate(ordered_palette, start=1):
        lookup[i] = (b, g, r)
    return lookup[labels]


def _save_debug_labels(labels, ordered_palette, path=OUTLINE_DEBUG_PATH):
    """Write the cleaned label map as a colour image (OpenCV writes BGR)."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    cv2.imwrite(path, _label_debug_image(labels, ordered_palette))


def _save_debug_stages(source_rgb, colors, stages, strokes, path):
    """Developer dump: one image per stage, a removed-boundary overlay, and
    every traced stroke in a random colour over a white field.

    Gated by ``PYAINT_DEBUG_LABELS``; writes next to ``debug_labels.png``. Also
    prints the boundary-preservation check from ``INSTRUCTIONS.md`` so a run
    that added (rather than deleted) boundaries is obvious.
    """
    base = os.path.splitext(path)[0]
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    for name, labels in stages.items():
        cv2.imwrite(f"{base}_{name}.png", _label_debug_image(labels, colors))

    if "quantized" in stages and "final" in stages:
        before = _boundary_pixels(stages["quantized"])
        after = _boundary_pixels(stages["final"])
        removed = before & ~after
        overlay = _np.ascontiguousarray(source_rgb[:, :, :3]).copy()
        overlay[removed] = (255, 0, 0)
        cv2.imwrite(
            f"{base}_removed.png", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
        )
        print(
            "outline cleaner: new boundary pixels:",
            int((after & ~before).sum()),
        )
        print("outline cleaner: removed boundary pixels:", int(removed.sum()))

    if strokes:
        width = int(max(x for stroke in strokes for x, _ in stroke)) + 4
        height = int(max(y for stroke in strokes for _, y in stroke)) + 4
        view = _np.full((height, width, 3), 255, _np.uint8)
        rng = _np.random.default_rng(0)
        for stroke in strokes:
            colour = tuple(int(v) for v in rng.integers(0, 200, size=3))
            points = _np.array(stroke, _np.int32).reshape(-1, 1, 2)
            cv2.polylines(view, [points], False, colour, 1)
        # Zoom for legibility, but cap the output so a full-resolution debug
        # run on a large screenshot cannot allocate a huge image.
        zoom = max(1, min(4, 4000 // max(width, height, 1)))
        if zoom > 1:
            view = cv2.resize(
                view,
                (width * zoom, height * zoom),
                interpolation=cv2.INTER_NEAREST,
            )
        cv2.imwrite(f"{base}_strokes.png", view)


def plan_outline(
    source,
    xo: int,
    yo: int,
    step: int,
    size,
    palette,
    flags: int,
    smooth_strength: float = OUTLINE_SMOOTHING,
    join_distance: float = OUTLINE_JOIN_DISTANCE,
    small_area: int = OUTLINE_SMALL_AREA,
    tiny_area: int = OUTLINE_TINY_AREA,
    similar_color: float = OUTLINE_SIMILAR_COLOR,
    double_edges: bool = False,
    debug: Optional[bool] = None,
    debug_path: Optional[str] = None,
    step_threshold: float = OUTLINE_STEP_THRESHOLD,
) -> Cmap:
    """Trace a cleaned label map into deduped outline polylines.

    INSTRUCTIONS.md pipeline: bilateral smooth -> weighted-Lab quantize ->
    soft-boundary merge -> selective small-region merge (twice) -> full
    contours -> geometric dedupe -> simplify -> join -> drop tiny strokes. It
    runs at the source resolution; distances are given in canvas pixels and
    areas in grid cells, then scaled by the source-to-canvas factor before use.

    The soft-boundary merge (``step_threshold``) is what keeps shading,
    gradients and soft shadows from being traced: touching components whose mean
    Lab step is below the threshold merge, while thin components (outlines,
    lashes) are protected. Set ``step_threshold`` to 0 to disable it.

    With ``double_edges`` the geometric dedupe is skipped, so every region's
    full contour is drawn (shared edges overlap) rather than thinned to one
    line. ``debug`` forces/denies the stage dumps for this call; ``None`` falls
    back to the :data:`OUTLINE_DEBUG` environment flag.
    """
    if _np is None:
        return {}
    tw, th = size
    canvas_w, canvas_h = tw * step, th * step
    src_w, src_h = source.size
    if canvas_w <= 0 or canvas_h <= 0 or src_w <= 0 or src_h <= 0:
        return {}
    colors = list(palette.color_list) if palette is not None else []
    if not colors:
        return {}

    factor = src_w / canvas_w
    factor_y = src_h / canvas_h
    scale = min(factor, factor_y)

    rgba = _np.asarray(source)
    if rgba.ndim == 2:
        rgb = _np.repeat(rgba[:, :, None], 3, axis=2)
        alpha = None
    else:
        rgb = _np.ascontiguousarray(rgba[:, :, :3])
        alpha = rgba[:, :, 3] if rgba.shape[2] > 3 else None

    palette_lab = _build_palette(colors)
    labels, lab = _quantize_labels(
        rgb,
        palette_lab,
        alpha,
        smooth_strength,
        bool(flags & IGNORE_TRANSPARENT),
    )
    stages = {"quantized": labels.copy()}

    # Stage 3: delete soft tonal boundaries so shading does not get its own
    # contour. Thin components (outlines, lashes) are protected.
    labels = _merge_soft_boundaries(
        labels,
        lab,
        palette_lab,
        float(step_threshold),
        protect_thin=True,
        thin_width=OUTLINE_THIN_WIDTH * scale,
    )
    stages["soft_merged"] = labels.copy()

    # Stage 4: absorb slivers and specks, twice, so a chain collapses.
    area_factor = (factor * step) * (factor_y * step)
    for _ in range(2):
        labels = _merge_small_regions(
            labels,
            palette_lab,
            max(1, int(round(small_area * area_factor))),
            max(1, int(round(tiny_area * area_factor))),
            float(similar_color),
        )
    stages["final"] = labels.copy()

    if debug is None:
        debug = OUTLINE_DEBUG

    contours = _collect_contours(
        labels, max(2, int(round(OUTLINE_MIN_POINTS * factor)))
    )
    coverage = _np.zeros(labels.shape, _np.uint8)
    radius = max(1, int(round(OUTLINE_COVER_RADIUS * factor)))
    min_drop = max(1, int(round(OUTLINE_MIN_DROP_RUN * factor)))
    epsilon = OUTLINE_EPSILON * factor

    strokes: List[Stroke] = []
    for contour in contours:
        if double_edges:
            keep = [True] * len(contour)
        else:
            covered = _find_covered_points(contour, coverage)
            keep = _keep_short_drops([not value for value in covered], min_drop)
        for run, closed in _split_into_runs(contour, keep):
            if len(run) < 2:
                continue
            path = _simplify(run, closed, epsilon)
            if closed and path:
                path.append(path[0])
            if len(path) < 2:
                continue
            strokes.append(path)
            if not double_edges:
                _paint_coverage(coverage, path, closed, radius)

    joined = _join_strokes(strokes, float(join_distance) * scale)
    min_length = OUTLINE_MIN_STROKE * scale
    kept = [
        stroke
        for stroke in joined
        if _is_closed(stroke) or _path_length(stroke) >= min_length
    ]

    if debug:
        _save_debug_stages(
            rgb, colors, stages, kept, debug_path or OUTLINE_DEBUG_PATH
        )

    result = [
        [(int(round(xo + x / factor)), int(round(yo + y / factor_y))) for x, y in stroke]
        for stroke in kept
        if len(stroke) >= 2
    ]
    return {OUTLINE_COLOUR: result} if result else {}


def plan(
    grid: ColourGrid,
    xo: int,
    yo: int,
    step: int,
    flags: int,
    mode: str,
    stroke_distance: int = STROKE_DISTANCE,
    palette=None,
    morphology: bool = False,
    double_edges: bool = False,
) -> Cmap:
    """Plan ``grid`` into a stroke map using the requested ``mode``.

    ``stroke_distance`` is accepted for compatibility and ignored by the
    outline planner; ``palette``, ``morphology`` and ``double_edges`` are
    forwarded to :func:`plan_regions`.
    """
    if mode == OUTLINE:
        return plan_regions(
            grid, xo, yo, step, flags, mode, stroke_distance, palette, morphology,
            double_edges,
        )
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
    morphology: bool = False,
    double_edges: bool = False,
    smooth_strength: float = OUTLINE_SMOOTHING,
    join_distance: float = OUTLINE_JOIN_DISTANCE,
    small_area: int = OUTLINE_SMALL_AREA,
    tiny_area: int = OUTLINE_TINY_AREA,
    similar_color: float = OUTLINE_SIMILAR_COLOR,
    step_threshold: float = OUTLINE_STEP_THRESHOLD,
) -> Cmap:
    """Fit + quantise + plan a full image. Returns a stroke map (``cmap``).

    OUTLINE runs the label-map cleaner (:func:`plan_outline`) on the source
    directly; the row/layer modes still share :func:`quantize_image`.
    """
    source, (tw, th), xo, yo = fit_to_canvas(image, canvas, step)
    if mode == OUTLINE:
        return plan_outline(
            source,
            xo,
            yo,
            step,
            (tw, th),
            palette,
            flags,
            smooth_strength,
            join_distance,
            small_area,
            tiny_area,
            similar_color,
            double_edges,
            step_threshold=step_threshold,
        )
    grid = quantize_image(source, (tw, th), palette, metric, flags)
    return plan(
        grid, xo, yo, step, flags, mode, stroke_distance, palette, morphology,
        double_edges,
    )


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
    morphology: bool = False,
    double_edges: bool = False,
    smooth_strength: float = OUTLINE_SMOOTHING,
    join_distance: float = OUTLINE_JOIN_DISTANCE,
    small_area: int = OUTLINE_SMALL_AREA,
    tiny_area: int = OUTLINE_TINY_AREA,
    similar_color: float = OUTLINE_SIMILAR_COLOR,
    step_threshold: float = OUTLINE_STEP_THRESHOLD,
) -> Cmap:
    """Fit + quantise + plan a sub-region. Returns a stroke map (``cmap``).

    OUTLINE runs the label-map cleaner (:func:`plan_outline`) on the source
    directly; the row/layer modes still share :func:`quantize_image`.
    """
    source, (tw, th), xo, yo = fit_region(image, region, canvas, step, canvas_target)
    if mode == OUTLINE:
        return plan_outline(
            source,
            xo,
            yo,
            step,
            (tw, th),
            palette,
            flags,
            smooth_strength,
            join_distance,
            small_area,
            tiny_area,
            similar_color,
            double_edges,
            step_threshold=step_threshold,
        )
    grid = quantize_image(source, (tw, th), palette, metric, flags)
    return plan(
        grid, xo, yo, step, flags, mode, stroke_distance, palette, morphology,
        double_edges,
    )
