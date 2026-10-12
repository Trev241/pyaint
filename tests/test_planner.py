"""Unit tests for the pure planner boundary (no screen, no Bot)."""

import numpy as np
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


def test_plan_image_routes_outline_to_label_pipeline(monkeypatch):
    quantize_calls = []
    outline_calls = []

    def fake_quantize(image, size, palette, metric, flags, source_quality=False):
        quantize_calls.append(source_quality)
        return [[RED]]

    def fake_outline(source, xo, yo, step, size, palette, flags, *args, **kwargs):
        outline_calls.append((size, flags))
        return {}

    monkeypatch.setattr(planner, "quantize_image", fake_quantize)
    monkeypatch.setattr(planner, "plan_outline", fake_outline)
    image = Image.new("RGB", (10, 10))
    canvas = (0, 0, 10, 10)
    planner.plan_image(image, canvas, 1, _palette(), "rgb", 0, planner.LAYERED)
    planner.plan_image(image, canvas, 1, _palette(), "rgb", 0, planner.OUTLINE)
    assert quantize_calls == [False]
    assert len(outline_calls) == 1


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


def test_outline_morphology_removes_isolated_specks():
    # A small blue speck inside a red block leaves a hole in the red mask (and
    # a speck in the blue one). Morphology closes the hole and deletes the
    # speck, so the region traces as one contour instead of two.
    grid = [[RED] * 8 for _ in range(8)]
    for i in (3, 4):
        for j in (3, 4):
            grid[i][j] = BLUE
    plain = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE)
    cleaned = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE, morphology=True)
    assert len(cleaned[planner.OUTLINE_COLOUR]) < len(plain[planner.OUTLINE_COLOUR])
    assert len(cleaned[planner.OUTLINE_COLOUR]) == 1


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


def test_outline_double_edges_overlap_on_the_same_segment():
    from collections import Counter

    grid = [[RED, RED, BLUE, BLUE], [RED, RED, BLUE, BLUE]]
    cmap = planner.plan(grid, 0, 0, 10, 0, planner.OUTLINE, double_edges=True)
    strokes = cmap[planner.OUTLINE_COLOUR]
    # Every region is one closed loop (no fragmentation into runs).
    assert strokes
    assert all(stroke[0] == stroke[-1] for stroke in strokes)

    segments = Counter()
    for stroke in strokes:
        for a, b in zip(stroke, stroke[1:]):
            segments[frozenset((a, b))] += 1
    # The shared vertical edge is drawn by both neighbours, but on the same
    # geometric segment rather than two parallel cell-centre contours.
    shared = frozenset({(20, 0), (20, 20)})
    assert segments[shared] == 2
    assert all(count <= 2 for count in segments.values())


def test_outline_double_edges_keeps_checkerboard_loops_closed():
    cmap = planner.plan(
        _checkerboard(), 0, 0, 10, 0, planner.OUTLINE, double_edges=True
    )
    strokes = cmap[planner.OUTLINE_COLOUR]
    assert strokes
    assert all(stroke[0] == stroke[-1] for stroke in strokes)


# ---------------------------------------------------------------------------
# outline cleaner helpers (INSTRUCTIONS.md label-map pipeline)
# ---------------------------------------------------------------------------
def test_keep_short_drops_keeps_short_stretches():
    flags = [True, True, False, False, True, True]
    assert planner._keep_short_drops(flags, 5) == [True] * 6
    assert planner._keep_short_drops(flags, 2) == flags


def test_join_strokes_chains_near_endpoints():
    strokes = [[(0, 0), (10, 0)], [(12, 0), (20, 0)]]
    joined = planner._join_strokes(strokes, 3.0)
    assert len(joined) == 1
    assert joined[0][0] == (0, 0) or joined[0][0] == (20, 0)
    assert set(joined[0]) == {(0, 0), (10, 0), (12, 0), (20, 0)}


def test_join_strokes_leaves_closed_loops_alone():
    loop = [(0, 0), (10, 0), (10, 10), (0, 0)]
    joined = planner._join_strokes([loop], 5.0)
    assert joined == [loop]


def test_build_palette_has_dummy_background_row():
    lab = planner._build_palette([(255, 0, 0), (0, 0, 255)])
    assert lab.shape == (3, 3)
    assert (lab[0] == 0).all()


def test_merge_small_regions_keeps_high_contrast_pupil():
    labels = np.ones((12, 12), dtype=np.int32)
    labels[5:8, 5:8] = 2  # area 9, above tiny_area but below small_area
    lab = planner._build_palette([(200, 200, 200), (0, 0, 0)])
    kept = planner._merge_small_regions(labels, lab, 12, 4, 10.0)
    assert (kept == 2).sum() == 9


def test_merge_small_regions_absorbs_tiny_specks():
    labels = np.ones((12, 12), dtype=np.int32)
    labels[5:6, 5:6] = 2  # area 1, below tiny_area, so merged regardless
    lab = planner._build_palette([(200, 200, 200), (0, 0, 0)])
    merged = planner._merge_small_regions(labels, lab, 12, 4, 10.0)
    assert (merged == 2).sum() == 0


def test_collect_contours_skips_background_and_sorts_longest_first():
    labels = np.zeros((12, 12), dtype=np.int32)
    labels[1:4, 1:4] = 1
    labels[5:11, 5:11] = 2
    contours = planner._collect_contours(labels, min_points=2)
    assert len(contours) == 2
    assert len(contours[0]) >= len(contours[1])


def test_plan_image_outline_bands_parallel_shared_boundaries():
    # Two same-size blocks meet along a vertical seam. ``findContours`` traces
    # that seam as two parallel pixel lines; the geometric dedupe drops the
    # covered one, so the doubled pass must draw strictly more than the single.
    image = Image.new("RGB", (20, 80), RED)
    for y in range(80):
        for x in range(10, 20):
            image.putpixel((x, y), BLUE)
    canvas = (0, 0, 20, 80)

    def total_length(cmap):
        return sum(
            planner._path_length(stroke)
            for stroke in cmap[planner.OUTLINE_COLOUR]
        )

    single = planner.plan_image(
        image, canvas, 2, _palette(), "rgb", 0, planner.OUTLINE
    )
    doubled = planner.plan_image(
        image, canvas, 2, _palette(), "rgb", 0, planner.OUTLINE, double_edges=True
    )
    assert total_length(doubled) > total_length(single)


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
