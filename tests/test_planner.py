"""Unit tests for the pure planner boundary (no screen, no Bot)."""

from PIL import Image

from pyaint import planner
from pyaint.palette import Palette

RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


def _palette():
    return Palette(colors_pos={RED: (0, 0), BLUE: (1, 0)})


def _row_image(*pixels):
    image = Image.new("RGBA", (len(pixels), 1))
    for x, pixel in enumerate(pixels):
        image.putpixel((x, 0), pixel)
    return image


def test_quantize_maps_pixels_to_nearest_palette_colour():
    image = _row_image(RED + (255,), BLUE + (255,))
    grid = planner.quantize(image.load(), 2, 1, _palette(), "rgb", 0)
    assert grid == [[RED, BLUE]]


def test_quantize_ignores_transparent_cells():
    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    grid = planner.quantize(
        image.load(), 1, 1, _palette(), "rgb", planner.IGNORE_TRANSPARENT
    )
    assert grid == [[None]]


def test_quantize_image_outvotes_isolated_noise():
    # A flat red field with a single blue speck: each 2x2 output cell sees the
    # speck as at most 1 of 16 votes, so majority sampling drops it.
    image = Image.new("RGBA", (8, 8), RED + (255,))
    image.putpixel((3, 3), BLUE + (255,))
    grid = planner.quantize_image(image, (2, 2), _palette(), "rgb", 0)
    assert grid == [[RED, RED], [RED, RED]]


def test_quantize_image_keeps_real_regions():
    image = Image.new("RGBA", (8, 8), RED + (255,))
    for x in range(4, 8):
        for y in range(8):
            image.putpixel((x, y), BLUE + (255,))
    grid = planner.quantize_image(image, (2, 2), _palette(), "rgb", 0)
    assert grid == [[RED, BLUE], [RED, BLUE]]


def test_quantize_image_honours_transparency():
    image = Image.new("RGBA", (4, 4), RED + (255,))
    for x in range(2, 4):
        for y in range(4):
            image.putpixel((x, y), (0, 0, 0, 0))
    grid = planner.quantize_image(
        image, (2, 2), _palette(), "rgb", planner.IGNORE_TRANSPARENT
    )
    assert grid == [[RED, None], [RED, None]]


def test_supersample_scale_default_is_budgeted_and_capped():
    # 4x4 grid over a 320px source = 80 source px per cell, but the default
    # budget keeps the sample grid cheap and caps at 8.
    image = Image.new("RGB", (320, 320))
    assert planner._supersample_scale(image, (4, 4), False) == 8


def test_supersample_scale_source_quality_samples_every_source_pixel():
    image = Image.new("RGB", (320, 320))
    assert planner._supersample_scale(image, (4, 4), True) == 80


def test_quantize_image_source_quality_votes_every_source_pixel():
    # The top-left 16x16 cell is 60% red; sampling every source pixel resolves
    # it to red instead of letting a sparse sample decide.
    image = Image.new("RGBA", (32, 32), BLUE + (255,))
    for y in range(16):
        for x in range(16):
            if (x + y) % 5 < 3:
                image.putpixel((x, y), RED + (255,))
    grid = planner.quantize_image(
        image, (2, 2), _palette(), "rgb", 0, source_quality=True
    )
    assert grid == [[RED, BLUE], [BLUE, BLUE]]


def test_plan_image_uses_source_quality_for_outline_only(monkeypatch):
    calls = []

    def fake_quantize(image, size, palette, metric, flags, source_quality=False):
        calls.append(source_quality)
        return [[RED]]

    monkeypatch.setattr(planner, "quantize_image", fake_quantize)
    image = Image.new("RGB", (10, 10))
    canvas = (0, 0, 10, 10)
    planner.plan_image(image, canvas, 1, _palette(), "rgb", 0, planner.LAYERED)
    planner.plan_image(image, canvas, 1, _palette(), "rgb", 0, planner.OUTLINE)
    assert calls == [False, True]


def test_nearest_color_indices_match_scalar():
    from pyaint.palette import Palette as P

    colors = [(10, 20, 30), (200, 40, 60), (70, 210, 90), (240, 240, 240)]
    palette = P(colors_pos={c: (0, 0) for c in colors})
    queries = [(12, 18, 33), (199, 41, 55), (60, 60, 60), (250, 250, 250)]
    for metric in ("rgb", "ciede2000"):
        indices = palette.nearest_color_indices(queries, metric)
        for query, index in zip(queries, indices):
            assert palette.color_list[index] == palette.nearest_color(query, metric)


def test_plan_slotted_returns_runs():
    cmap = planner.plan([[RED, RED]], 0, 0, 10, 0, planner.SLOTTED)
    assert cmap == {RED: [[(0, 0), (10, 0)]]}


def test_plan_slotted_ignores_white_when_flagged():
    cmap = planner.plan(
        [[WHITE, RED]], 0, 0, 10, planner.IGNORE_WHITE, planner.SLOTTED
    )
    assert WHITE not in cmap
    assert cmap[RED] == [[(10, 0), (10, 0)]]


def _checkerboard(size=6):
    return [
        [RED if (i + j) % 2 == 0 else BLUE for j in range(size)]
        for i in range(size)
    ]


def test_plan_outline_returns_strokes():
    cmap = planner.plan(_checkerboard(), 0, 0, 10, 0, planner.OUTLINE)
    assert cmap.get(planner.OUTLINE_COLOUR)


def test_outline_emits_one_closed_polyline_per_contour():
    cmap = planner.plan(_checkerboard(), 0, 0, 10, 0, planner.OUTLINE)
    strokes = cmap[planner.OUTLINE_COLOUR]
    assert strokes
    for points in strokes:
        assert isinstance(points, list)
        assert len(points) >= 3  # at least two vertices plus the closing point
        assert points[0] == points[-1]


def test_outline_stroke_distance_no_longer_changes_the_plan():
    grid = _checkerboard()
    fine = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE, stroke_distance=1)
    coarse = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE, stroke_distance=5)
    assert fine == coarse


def test_outline_draws_each_shared_edge_once():
    from collections import Counter

    # Two same-colour blocks meet along one vertical boundary.
    grid = [[RED, RED, BLUE, BLUE], [RED, RED, BLUE, BLUE]]
    cmap = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE)
    segments = Counter()
    for stroke in cmap[planner.OUTLINE_COLOUR]:
        for a, b in zip(stroke, stroke[1:]):
            segments[frozenset((a, b))] += 1
    assert segments
    # The shared edge must not be traced by both region contours.
    assert all(count == 1 for count in segments.values())


# ---------------------------------------------------------------------------
# canvas padding
# ---------------------------------------------------------------------------
def test_inset_canvas_shrinks_every_edge():
    assert planner._inset_canvas((10, 20, 100, 50)) == (14, 24, 92, 42)


def test_inset_canvas_never_eats_tiny_canvases():
    # The inset clamps to leave at least one pixel of width/height.
    assert planner._inset_canvas((0, 0, 1, 1)) == (0, 0, 1, 1)
    assert planner._inset_canvas((0, 0, 2, 1)) == (0, 0, 2, 1)


def test_fit_to_canvas_keeps_origin_inside_padded_border():
    image = Image.new("RGB", (100, 100))
    x, y, w, h = (1000, 2000, 400, 200)
    _, _, xo, yo = planner.fit_to_canvas(image, (x, y, w, h), 10)
    assert xo >= x + planner.CANVAS_PADDING
    assert yo >= y + planner.CANVAS_PADDING
