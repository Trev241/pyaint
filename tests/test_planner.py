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


def _soft_lab_palette():
    # True-scale Lab rows for the synthetic tones below (row 0 = dummy).
    return np.array(
        [[0, 0, 0], [50, 0, 0], [53, 0, 0], [90, 0, 0]], dtype=np.float32
    )


def test_merge_soft_boundaries_drops_soft_step_keeps_hard():
    labels = np.ones((40, 40), dtype=np.int32)
    labels[:, 20:30] = 2  # L=53 vs L=50: a soft step
    labels[:, 30:] = 3  # L=90: a hard step
    lab = np.zeros((40, 40, 3), dtype=np.float32)
    lab[labels == 1] = [50, 0, 0]
    lab[labels == 2] = [53, 0, 0]
    lab[labels == 3] = [90, 0, 0]

    merged = planner._merge_soft_boundaries(
        labels, lab, _soft_lab_palette(), 4.0, protect_thin=False, thin_width=0.0
    )

    # The soft pair becomes one region; the hard edge is preserved.
    assert merged[0, 0] == merged[0, 25]
    assert (merged[:, 30:] == 3).all()
    before = planner._boundary_pixels(labels)
    after = planner._boundary_pixels(merged)
    assert int((after & ~before).sum()) == 0
    assert int((before & ~after).sum()) == 80


def test_merge_soft_boundaries_protects_thin_components():
    labels = np.ones((40, 40), dtype=np.int32)
    labels[:, 20] = 2  # a 1px soft line (an outline / lash)
    lab = np.zeros((40, 40, 3), dtype=np.float32)
    lab[labels == 1] = [50, 0, 0]
    lab[labels == 2] = [53, 0, 0]

    merged = planner._merge_soft_boundaries(
        labels, lab, _soft_lab_palette(), 4.0, protect_thin=True, thin_width=2.0
    )
    assert (merged == 2).sum() == 40  # the thin line survives


def test_merge_soft_boundaries_disabled_returns_labels():
    labels = np.ones((4, 4), dtype=np.int32)
    labels[0, 0] = 2
    lab = np.zeros((4, 4, 3), dtype=np.float32)
    merged = planner._merge_soft_boundaries(
        labels, lab, _soft_lab_palette(), 0.0
    )
    assert (merged == labels).all()


def test_merge_soft_boundaries_uses_component_means():
    # The two regions touch with a tiny local step (col 19 -> 20 is 49 -> 51)
    # but their means are ~21 and ~79. Comparing means (not the local step)
    # keeps them apart, which is the anti-chaining fix.
    labels = np.ones((10, 40), dtype=np.int32)
    labels[:, 20:] = 2
    lab = np.zeros((10, 40, 3), dtype=np.float32)
    lab[:, :20] = [20.0, 0.0, 0.0]
    lab[:, 20:] = [80.0, 0.0, 0.0]
    lab[:, 19] = [49.0, 0.0, 0.0]
    lab[:, 20] = [51.0, 0.0, 0.0]
    palette = np.array(
        [[0, 0, 0], [20, 0, 0], [80, 0, 0]], dtype=np.float32
    )
    kept = planner._merge_soft_boundaries(
        labels, lab, palette, 10.0, protect_thin=False, thin_width=0.0
    )
    assert (kept == labels).all()


def test_merge_soft_boundaries_merges_close_component_means():
    labels = np.ones((10, 40), dtype=np.int32)
    labels[:, 20:] = 2
    lab = np.zeros((10, 40, 3), dtype=np.float32)
    lab[:, :20] = [50.0, 0.0, 0.0]
    lab[:, 20:] = [54.0, 0.0, 0.0]
    palette = np.array(
        [[0, 0, 0], [50, 0, 0], [54, 0, 0]], dtype=np.float32
    )
    merged = planner._merge_soft_boundaries(
        labels, lab, palette, 10.0, protect_thin=False, thin_width=0.0
    )
    assert (merged == merged[0, 0]).all()


def test_adaptive_segmentation_splits_distinct_colours():
    image = np.zeros((12, 12, 3), dtype=np.uint8)
    image[:, :4] = (200, 30, 30)
    image[:, 4:8] = (30, 200, 30)
    image[:, 8:] = (30, 30, 200)
    _, lab = planner._smooth_to_lab(image, 0)
    palette_lab, labels, palette_rgb = planner._adaptive_segmentation(
        image, lab, 48
    )
    assert len(np.unique(labels)) == 3
    assert palette_lab.shape == (4, 3)
    assert len(palette_rgb) == 3


def test_adaptive_segmentation_is_deterministic():
    rng = np.random.default_rng(0)
    image = rng.integers(0, 256, size=(20, 20, 3), dtype=np.uint8)
    _, lab = planner._smooth_to_lab(image, 0)
    first = planner._adaptive_segmentation(image, lab, 8)[1]
    second = planner._adaptive_segmentation(image, lab, 8)[1]
    assert np.array_equal(first, second)


def test_plan_outline_shading_cleanup_reduces_tonal_strokes():
    # A smooth grey ramp quantises into several close tonal bands. With shading
    # cleanup on, they collapse into one region; a hard red block still traces.
    width, height = 60, 24
    image = Image.new("RGB", (width, height))
    for x in range(width):
        value = 90 + 2 * x  # 90..208 grey ramp
        for y in range(height):
            image.putpixel((x, y), (value, value, value))
    for x in range(44, 60):
        for y in range(height):
            image.putpixel((x, y), RED)
    palette = Palette(
        colors_pos={
            (100, 100, 100): (0, 0),
            (130, 130, 130): (1, 0),
            (160, 160, 160): (2, 0),
            (190, 190, 190): (3, 0),
            RED: (4, 0),
        }
    )

    off = planner.plan_outline(
        image,
        0,
        0,
        1,
        (width, height),
        palette,
        0,
        step_threshold=0.0,
        segmentation_colors=0,
    )
    on = planner.plan_outline(
        image,
        0,
        0,
        1,
        (width, height),
        palette,
        0,
        step_threshold=12.0,
        segmentation_colors=0,
    )
    assert len(on[planner.OUTLINE_COLOUR]) < len(off[planner.OUTLINE_COLOUR])


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


# ---------------------------------------------------------------------------
# Canny sketch mode
# ---------------------------------------------------------------------------
def _rectangle_image(width=60, height=40):
    image = Image.new("RGB", (width, height), WHITE)
    for x in range(10, 50):
        image.putpixel((x, 8), (0, 0, 0))
        image.putpixel((x, 31), (0, 0, 0))
    for y in range(8, 32):
        image.putpixel((10, y), (0, 0, 0))
        image.putpixel((49, y), (0, 0, 0))
    return image


def _sketch_canny(image, **kwargs):
    width, height = image.size
    options = dict(
        edge_source=planner.EDGE_CANNY,
        smooth_strength=0,
        canny_low=50,
        canny_high=150,
        canny_auto=False,
        hue_merge=False,
    )
    options.update(kwargs)
    return planner.plan_sketch(image, 0, 0, 1, (width, height), None, 0, **options)


def test_trace_edge_chains_follows_a_straight_line():
    edges = np.zeros((10, 10), dtype=np.uint8)
    edges[5, 1:8] = 255
    chains = planner._trace_edge_chains(edges)
    assert len(chains) == 1
    assert chains[0] == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5)]


def test_trace_edge_chains_handles_an_l_corner():
    edges = np.zeros((10, 10), dtype=np.uint8)
    edges[2, 2:7] = 255
    edges[2:7, 6] = 255
    chains = planner._trace_edge_chains(edges)
    # The 8-connected corner leaves a short diagonal fragment; the longest
    # chain must still run the whole L, and every edge pixel is covered.
    longest = max(chains, key=len)
    assert longest[0] == (2, 2)
    assert longest[-1] == (6, 6)
    covered = {(x, y) for chain in chains for x, y in chain}
    ys, xs = np.where(edges > 0)
    assert covered == set(zip(xs.tolist(), ys.tolist()))


def test_join_strokes_direction_filter_keeps_crossings_apart():
    collinear = [[(0, 0), (10, 0)], [(10, 1), (20, 1)]]
    assert len(planner._join_strokes(collinear, 3.0, max_turn_degrees=60)) == 1
    corner = [[(0, 0), (10, 0)], [(10, 1), (10, 11)]]
    assert len(planner._join_strokes(corner, 3.0, max_turn_degrees=60)) == 2
    # The original behaviour (no direction filter) still joins the corner.
    assert len(planner._join_strokes(corner, 3.0)) == 1


def test_plan_sketch_canny_flat_image_has_no_strokes():
    flat = Image.new("RGB", (40, 30), WHITE)
    assert _sketch_canny(flat) == {}


def test_plan_sketch_canny_traces_a_rectangle():
    cmap = _sketch_canny(_rectangle_image())
    strokes = cmap[planner.OUTLINE_COLOUR]
    assert strokes
    xs = [x for stroke in strokes for x, _ in stroke]
    ys = [y for stroke in strokes for _, y in stroke]
    assert min(xs) <= 10 and max(xs) >= 49
    assert min(ys) <= 8 and max(ys) >= 31
    # At least one trace should close back on itself (the border loop).
    assert any(stroke[0] == stroke[-1] for stroke in strokes)


def test_plan_sketch_is_deterministic():
    rng = np.random.default_rng(0)
    image = Image.fromarray(
        rng.integers(0, 256, size=(40, 40, 3), dtype=np.uint8), "RGB"
    )
    first = _sketch_canny(image)
    second = _sketch_canny(image)
    assert first == second


def test_plan_sketch_edgedrawing_source_traces_a_rectangle():
    import pytest

    cv2 = pytest.importorskip("cv2")
    if not hasattr(cv2, "ximgproc"):
        pytest.skip("opencv-contrib (cv2.ximgproc) not installed")
    image = _rectangle_image()
    cmap = planner.plan_sketch(
        image,
        0,
        0,
        1,
        image.size,
        None,
        0,
        edge_source=planner.EDGE_EDGEDRAWING,
        smooth_strength=0,
        hue_merge=False,
    )
    assert cmap[planner.OUTLINE_COLOUR]


def test_keep_by_hue_drops_same_hue_and_keeps_colour_boundary():
    image = np.zeros((40, 60, 3), np.uint8)
    image[:, :30] = (200, 30, 30)
    image[:, 30:] = (200, 30, 30)  # same red on both sides
    hue, sat = planner._hue_planes(image)
    stroke = [(30, y) for y in range(5, 35)]
    assert planner._keep_by_hue(stroke, hue, sat, 15.0) is False

    image[:, 30:] = (30, 30, 200)  # blue on the right
    hue, sat = planner._hue_planes(image)
    assert planner._keep_by_hue(stroke, hue, sat, 15.0) is True


def test_plan_image_routes_sketch_mode():
    image = _rectangle_image()
    cmap = planner.plan_image(
        image,
        (0, 0, 60, 40),
        1,
        _palette(),
        "rgb",
        0,
        planner.SKETCH,
        sketch_edge_source=planner.EDGE_CANNY,
        sketch_smoothing=0,
        sketch_hue_merge=False,
        canny_low=50,
        canny_high=150,
        canny_auto=False,
    )
    assert planner.OUTLINE_COLOUR in cmap
    assert cmap[planner.OUTLINE_COLOUR]
