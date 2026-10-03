"""Screen locators: automatic detection of a target's canvas and palette.

Phase 2 of the roadmap. Locators find the screen rectangles Pyaint needs so the
user does not have to click-teach them. Everything here is **pure over a PIL
image** (plus an injectable window provider), which keeps it fully testable
without a display; only :func:`get_window_rect` touches the OS.

Recipes describe which locator to use via their ``detection`` mapping::

    "detection": {
        "canvas":  {"type": "white_rect"},
        "palette": {"type": "color_grid"}
    }

Supported locator types: ``white_rect`` (a large near-white canvas),
``color_grid`` (a grid of colourful swatches, returns rows/cols),
``color_signature`` (match a known set of colours), and ``window_relative``
(a sub-rectangle of an OS window). Anything that fails returns ``None`` so the
caller can fall back to manual teaching.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image

RGB = Tuple[int, int, int]
Rect = Tuple[int, int, int, int]  # (x, y, width, height)
WindowProvider = Callable[[str], Optional[Rect]]

_MAX_DIM = 720


# ---------------------------------------------------------------------------
# Low-level mask helpers
# ---------------------------------------------------------------------------
def _downscale(image: Image.Image, max_dim: int) -> Tuple[Image.Image, float]:
    width, height = image.size
    scale = min(1.0, max_dim / max(width, height))
    if scale >= 1.0:
        return image, 1.0
    try:
        resample = Image.Resampling.NEAREST
    except AttributeError:  # older Pillow
        resample = Image.NEAREST
    # NEAREST preserves exact swatch colours; BICUBIC would blend tiny palette
    # cells into desaturated mush and make the colour mask miss them.
    small = image.resize(
        (max(1, int(width * scale)), max(1, int(height * scale))), resample=resample
    )
    return small, scale


def _mask(image: Image.Image, predicate: Callable[[RGB], bool]) -> List[List[bool]]:
    width, height = image.size
    pixels = image.load()
    return [
        [bool(predicate(tuple(pixels[x, y][:3]))) for x in range(width)]
        for y in range(height)
    ]


def _dilate(mask: List[List[bool]], radius: int) -> List[List[bool]]:
    """Binary dilation with a square kernel (separable, O(n * radius))."""
    if radius <= 0:
        return mask
    height = len(mask)
    width = len(mask[0]) if height else 0

    horizontal = [[False] * width for _ in range(height)]
    for y in range(height):
        row = mask[y]
        out = horizontal[y]
        for x in range(width):
            if row[x]:
                for xx in range(max(0, x - radius), min(width, x + radius + 1)):
                    out[xx] = True

    dilated = [[False] * width for _ in range(height)]
    for y in range(height):
        row = horizontal[y]
        for x in range(width):
            if row[x]:
                for yy in range(max(0, y - radius), min(height, y + radius + 1)):
                    dilated[yy][x] = True
    return dilated


def _components(
    mask: List[List[bool]],
) -> List[Tuple[int, Tuple[int, int, int, int]]]:
    """Return (area, (minx, miny, maxx, maxy)) for every 4-connected blob."""
    height = len(mask)
    width = len(mask[0]) if height else 0
    seen = [[False] * width for _ in range(height)]
    components: List[Tuple[int, Tuple[int, int, int, int]]] = []

    for y in range(height):
        for x in range(width):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            minx = maxx = x
            miny = maxy = y
            area = 0
            while stack:
                cx, cy = stack.pop()
                area += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            components.append((area, (minx, miny, maxx, maxy)))
    return components


def _largest_component(
    mask: List[List[bool]],
) -> Optional[Tuple[int, Tuple[int, int, int, int]]]:
    """Return (area, bbox) for the largest 4-connected blob, or None."""
    components = _components(mask)
    return max(components, key=lambda c: c[0]) if components else None


def _scale_rect(rect: Rect, scale: float, size: Tuple[int, int]) -> Rect:
    x, y, w, h = rect
    inv = 1.0 / scale if scale else 1.0
    ox = max(0, min(int(round(x * inv)), size[0] - 1))
    oy = max(0, min(int(round(y * inv)), size[1] - 1))
    ow = max(1, min(int(round(w * inv)), size[0] - ox))
    oh = max(1, min(int(round(h * inv)), size[1] - oy))
    return (ox, oy, ow, oh)


def _count_bands(
    mask: List[List[bool]], x0: int, x1: int, y0: int, y1: int, axis: str
) -> int:
    """Count runs of non-empty rows (axis='y') or columns (axis='x')."""
    bands = 0
    in_band = False
    if axis == "y":
        for y in range(y0, y1 + 1):
            has = any(mask[y][x] for x in range(x0, x1 + 1))
            if has and not in_band:
                bands += 1
            in_band = has
    else:
        for x in range(x0, x1 + 1):
            has = any(mask[y][x] for y in range(y0, y1 + 1))
            if has and not in_band:
                bands += 1
            in_band = has
    return bands


# ---------------------------------------------------------------------------
# Locator algorithms
# ---------------------------------------------------------------------------
def find_white_rect(
    image: Image.Image,
    threshold: int = 235,
    min_fraction: float = 0.02,
    max_fraction: float = 0.9,
    min_rectangularity: float = 0.85,
    max_dim: int = _MAX_DIM,
    aspect: Optional[float] = None,
    aspect_tolerance: float = 0.15,
) -> Optional[Rect]:
    """Find the largest near-white, roughly rectangular region (the canvas)."""
    small, scale = _downscale(image, max_dim)
    mask = _mask(small, lambda c: min(c) >= threshold)
    component = _largest_component(mask)
    if component is None:
        return None

    area, (x0, y0, x1, y1) = component
    bw = x1 - x0 + 1
    bh = y1 - y0 + 1
    if bw <= 0 or bh <= 0:
        return None

    rectangularity = area / (bw * bh)
    fraction = (bw * bh) / (small.size[0] * small.size[1])
    if rectangularity < min_rectangularity or not (min_fraction <= fraction <= max_fraction):
        return None
    if aspect is not None and abs((bw / bh) - aspect) > aspect_tolerance:
        return None
    return _scale_rect((x0, y0, bw, bh), scale, image.size)


def find_color_rect(
    image: Image.Image,
    color: Sequence[int],
    tolerance: int = 40,
    min_fraction: float = 0.02,
    max_fraction: float = 0.95,
    min_rectangularity: float = 0.85,
    max_dim: int = _MAX_DIM,
    aspect: Optional[float] = None,
    aspect_tolerance: float = 0.15,
) -> Optional[Rect]:
    """Largest near-uniform rectangular region of a given colour (e.g. a solid
    black canvas). ``tolerance`` is a per-channel (Chebyshev) bound."""
    target = tuple(int(v) for v in color[:3])
    small, scale = _downscale(image, max_dim)
    mask = _mask(
        small, lambda c: max(abs(c[i] - target[i]) for i in range(3)) <= tolerance
    )
    component = _largest_component(mask)
    if component is None:
        return None

    area, (x0, y0, x1, y1) = component
    bw = x1 - x0 + 1
    bh = y1 - y0 + 1
    if bw <= 0 or bh <= 0:
        return None
    rectangularity = area / (bw * bh)
    fraction = (bw * bh) / (small.size[0] * small.size[1])
    if rectangularity < min_rectangularity or not (min_fraction <= fraction <= max_fraction):
        return None
    if aspect is not None and abs((bw / bh) - aspect) > aspect_tolerance:
        return None
    return _scale_rect((x0, y0, bw, bh), scale, image.size)


def find_color_signature(
    image: Image.Image,
    colors: Sequence[Sequence[int]],
    tolerance: int = 30,
    gap: int = 3,
    max_dim: int = _MAX_DIM,
    min_colors: int = 1,
    min_fill: float = 0.0,
) -> Optional[Rect]:
    """Find the region containing the most *distinct* target colours.

    A palette is a compact block that contains many different swatch colours,
    whereas a large single-colour UI panel (white chat, black canvas) contains
    only one. Scoring candidate blobs by how many distinct target colours they
    cover therefore picks the palette and ignores the surrounding UI — which is
    essential when the page background is itself saturated.
    """
    if not colors:
        return None
    palette = [tuple(int(v) for v in c[:3]) for c in colors]
    tolerance_sq = tolerance * tolerance

    small, scale = _downscale(image, max_dim)
    width, height = small.size
    pixels = small.load()
    cache: Dict[RGB, int] = {}
    matched = [[0] * width for _ in range(height)]
    mask = [[False] * width for _ in range(height)]

    for y in range(height):
        row_bits = matched[y]
        row_mask = mask[y]
        for x in range(width):
            c = tuple(pixels[x, y][:3])
            bits = cache.get(c)
            if bits is None:
                bits = 0
                for i, p in enumerate(palette):
                    if (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2 <= tolerance_sq:
                        bits |= 1 << i
                cache[c] = bits
            row_bits[x] = bits
            if bits:
                row_mask[x] = True

    components = _components(_dilate(mask, gap))
    if not components:
        return None

    best_key = None
    best_bbox = None
    for area, (x0, y0, x1, y1) in components:
        cover = 0
        matched_count = 0
        for y in range(y0, y1 + 1):
            row_bits = matched[y]
            for x in range(x0, x1 + 1):
                bits = row_bits[x]
                if bits:
                    cover |= bits
                    matched_count += 1
        distinct = bin(cover).count("1")
        if distinct < min_colors:
            continue
        bbox_area = (x1 - x0 + 1) * (y1 - y0 + 1)
        fill = matched_count / bbox_area if bbox_area else 0.0
        if fill < min_fill:
            continue
        # Prefer blobs covering the most distinct colours; break ties by how
        # densely they fill their bounding box. A palette is a solid block;
        # sparse colourful text (e.g. a rainbow logo) is not, so it loses.
        key = (distinct, round(fill, 3), x1 - x0 + 1, area)
        if best_key is None or key > best_key:
            best_key = key
            best_bbox = (x0, y0, x1, y1)

    if best_bbox is None:
        return None
    x0, y0, x1, y1 = best_bbox
    return _scale_rect((x0, y0, x1 - x0 + 1, y1 - y0 + 1), scale, image.size)


def find_color_grid(
    image: Image.Image,
    min_saturation: int = 25,
    min_fraction: float = 0.0002,
    max_fraction: float = 0.6,
    gap: int = 4,
    max_dim: int = _MAX_DIM,
) -> Optional[Tuple[Rect, int, int]]:
    """Find a grid of colourful swatches and estimate its rows/columns.

    Returns ``(rect, rows, cols)`` or ``None``. Saturation is used rather than
    exact colours so it works without hard-coding an app's palette.
    """
    small, scale = _downscale(image, max_dim)
    mask = _mask(small, lambda c: (max(c) - min(c)) >= min_saturation)
    if not any(any(row) for row in mask):
        return None

    merged = _dilate(mask, gap)
    components = _components(merged)
    if not components:
        return None

    # A palette is a wide, short strip. Prefer the widest component (tie-break
    # on area) rather than simply the largest blob, so a colourful avatar or
    # button does not win over the palette.
    area, (x0, y0, x1, y1) = max(
        components, key=lambda c: (c[1][2] - c[1][0] + 1, c[0])
    )

    bw = x1 - x0 + 1
    bh = y1 - y0 + 1
    fraction = (bw * bh) / (small.size[0] * small.size[1])
    if not (min_fraction <= fraction <= max_fraction):
        return None

    rows = _count_bands(mask, x0, x1, y0, y1, "y")
    cols = _count_bands(mask, x0, x1, y0, y1, "x")
    if rows < 1 or cols < 1:
        return None
    return _scale_rect((x0, y0, bw, bh), scale, image.size), rows, cols


def find_center_rect(
    image: Image.Image,
    tolerance: int = 30,
    min_fraction: float = 0.02,
) -> Optional[Rect]:
    """Grow a solid-colour rectangle out from the image centre.

    Fast and border-aware: it walks left/right/up/down from the centre pixel
    until the colour changes, so a thin (even 1px) border around the canvas is
    respected — unlike connected-component detection after downscaling, which
    can merge the canvas with a same-coloured toolbar.
    """
    width, height = image.size
    pixels = image.load()
    cx, cy = width // 2, height // 2
    seed = tuple(pixels[cx, cy][:3])

    def match(c: RGB) -> bool:
        return max(abs(c[i] - seed[i]) for i in range(3)) <= tolerance

    left = cx
    while left > 0 and match(tuple(pixels[left - 1, cy][:3])):
        left -= 1
    right = cx
    while right < width - 1 and match(tuple(pixels[right + 1, cy][:3])):
        right += 1
    top = cy
    while top > 0 and match(tuple(pixels[cx, top - 1][:3])):
        top -= 1
    bottom = cy
    while bottom < height - 1 and match(tuple(pixels[cx, bottom + 1][:3])):
        bottom += 1

    bw = right - left + 1
    bh = bottom - top + 1
    if bw * bh < min_fraction * width * height:
        return None
    return (left, top, bw, bh)


def window_relative_rect(window: Rect, normalized: Sequence[float]) -> Rect:
    """Map a normalized ``(x, y, w, h)`` (0..1) onto an absolute window rect."""
    wx, wy, ww, wh = window
    nx, ny, nw, nh = normalized
    return (
        int(round(wx + nx * ww)),
        int(round(wy + ny * wh)),
        max(1, int(round(nw * ww))),
        max(1, int(round(nh * wh))),
    )


def get_window_rect(title_substring: str) -> Optional[Rect]:
    """Best-effort client-rect lookup for a window whose title contains the
    given text. Windows-only; returns ``None`` elsewhere or on failure."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None

    try:
        user32 = ctypes.windll.user32
        found: List[Rect] = []

        def callback(hwnd, _):
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if title_substring.lower() in buffer.value.lower() and user32.IsWindowVisible(hwnd):
                rect = wintypes.RECT()
                if user32.GetClientRect(hwnd, ctypes.byref(rect)):
                    origin = wintypes.POINT(0, 0)
                    user32.ClientToScreen(hwnd, ctypes.byref(origin))
                    found.append(
                        (
                            origin.x,
                            origin.y,
                            rect.right - rect.left,
                            rect.bottom - rect.top,
                        )
                    )
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found[0] if found else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Detection orchestration
# ---------------------------------------------------------------------------
@dataclass
class Detection:
    """What auto-detection found. Falsy when nothing usable was detected."""

    canvas: Optional[Rect] = None
    palette: Optional[Rect] = None
    palette_rows: Optional[int] = None
    palette_cols: Optional[int] = None

    def __bool__(self) -> bool:
        return self.canvas is not None or self.palette is not None

    def summary(self) -> str:
        parts: List[str] = []
        if self.canvas:
            parts.append(f"canvas {self.canvas}")
        if self.palette:
            grid = ""
            if self.palette_rows and self.palette_cols:
                grid = f" ({self.palette_rows}x{self.palette_cols})"
            parts.append(f"palette {self.palette}{grid}")
        return "; ".join(parts)


_WHITE_RECT_KEYS = {"threshold", "min_fraction", "max_fraction", "min_rectangularity", "max_dim", "aspect", "aspect_tolerance"}
_COLOR_RECT_KEYS = {"tolerance", "min_fraction", "max_fraction", "min_rectangularity", "max_dim", "aspect", "aspect_tolerance"}
_COLOR_GRID_KEYS = {"min_saturation", "min_fraction", "max_fraction", "gap", "max_dim"}
_COLOR_SIGNATURE_KEYS = {"tolerance", "gap", "max_dim", "min_colors", "min_fill"}

LocatorHandler = Callable[
    [Image.Image, Any, Dict[str, Any], Optional["WindowProvider"]],
    Tuple[Optional[Rect], Optional[int], Optional[int]],
]

# Registered locator types: name -> (handler, allowed params).
_LOCATORS: Dict[str, Tuple[LocatorHandler, set]] = {}


def register_locator(name: str, allowed_params):
    """Register a locator type usable as ``{"type": name, ...}`` in a recipe."""

    def decorator(func: LocatorHandler) -> LocatorHandler:
        _LOCATORS[name] = (func, set(allowed_params) | {"region"})
        return func

    return decorator


def available_locators() -> List[str]:
    """Names of every registered locator type."""
    return list(_LOCATORS)


def locator_params(name: str) -> Optional[set]:
    """Allowed parameter names for a locator type, or ``None`` if unknown."""
    entry = _LOCATORS.get(name)
    return set(entry[1]) if entry else None


@register_locator("white_rect", _WHITE_RECT_KEYS)
def _locate_white_rect(image, recipe, params, provider):
    return find_white_rect(image, **params), None, None


@register_locator("color_rect", _COLOR_RECT_KEYS | {"color"})
def _locate_color_rect(image, recipe, params, provider):
    color = params.pop("color", None)
    if not color:
        return None, None, None
    return find_color_rect(image, color, **params), None, None


@register_locator("color_grid", _COLOR_GRID_KEYS)
def _locate_color_grid(image, recipe, params, provider):
    result = find_color_grid(image, **params)
    return result if result else (None, None, None)


@register_locator("color_signature", _COLOR_SIGNATURE_KEYS | {"colors", "rows", "cols"})
def _locate_color_signature(image, recipe, params, provider):
    colors = params.pop("colors", None) or getattr(recipe, "palette", None)
    rows, cols = params.pop("rows", None), params.pop("cols", None)
    if not colors:
        return None, None, None
    return find_color_signature(image, colors, **params), rows, cols


@register_locator("center_rect", {"tolerance", "min_fraction"})
def _locate_center_rect(image, recipe, params, provider):
    return find_center_rect(image, **params), None, None


@register_locator("window_relative", {"window", "rect", "rows", "cols"})
def _locate_window_relative(image, recipe, params, provider):
    normalized = params.get("rect")
    if not normalized or len(normalized) != 4:
        return None, None, None
    provider_fn = provider or get_window_rect
    window = provider_fn(params.get("window", ""))
    if not window:
        return None, None, None
    return window_relative_rect(window, normalized), params.get("rows"), params.get("cols")


def _run_spec(
    spec: Dict[str, Any],
    image: Image.Image,
    recipe: Any,
    window_provider: Optional[WindowProvider],
) -> Tuple[Optional[Rect], Optional[int], Optional[int]]:
    if not isinstance(spec, dict):
        return None, None, None
    entry = _LOCATORS.get(spec.get("type"))
    if entry is None:
        return None, None, None
    handler, allowed = entry

    # Optional absolute-pixel region of interest: detect inside a crop, then
    # offset the result back to full-image coordinates.
    region = spec.get("region")
    offset = (0, 0)
    work = image
    if isinstance(region, (list, tuple)) and len(region) == 4:
        rx, ry, rw, rh = (int(v) for v in region)
        work = image.crop((rx, ry, rx + rw, ry + rh))
        offset = (rx, ry)

    params = {k: v for k, v in spec.items() if k in allowed and k != "region"}
    try:
        rect, rows, cols = handler(work, recipe, params, window_provider)
    except TypeError:
        return None, None, None
    if rect and offset != (0, 0):
        rect = (rect[0] + offset[0], rect[1] + offset[1], rect[2], rect[3])
    return rect, rows, cols


def _run_chain(
    spec: Any,
    image: Image.Image,
    recipe: Any,
    window_provider: Optional[WindowProvider],
) -> Tuple[Optional[Rect], Optional[int], Optional[int]]:
    """Try a spec, or an ordered list of specs, returning the first success."""
    specs = spec if isinstance(spec, list) else [spec]
    for item in specs:
        if not isinstance(item, dict):
            continue
        rect, rows, cols = _run_spec(item, image, recipe, window_provider)
        if rect:
            return rect, rows, cols
    return None, None, None


def detect_target(
    recipe: Any,
    image: Image.Image,
    window_provider: Optional[WindowProvider] = None,
) -> Detection:
    """Run a recipe's configured locators against ``image``.

    Never raises for "not found"; callers are expected to fall back to manual
    teaching when the returned :class:`Detection` is falsy.
    """
    detection = Detection()
    config = getattr(recipe, "detection", None) or {}

    canvas_spec = config.get("canvas")
    if canvas_spec:
        rect, _, _ = _run_chain(canvas_spec, image, recipe, window_provider)
        detection.canvas = rect

    palette_spec = config.get("palette")
    if palette_spec:
        rect, rows, cols = _run_chain(palette_spec, image, recipe, window_provider)
        detection.palette = rect
        detection.palette_rows = rows
        detection.palette_cols = cols

    return detection
