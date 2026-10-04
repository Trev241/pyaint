"""Headless tests for the pure-ish drawing pipeline.

These deliberately avoid any screen access: Palette is constructed from an
explicit ``colors_pos`` map and Bot receives a canvas via ``init_canvas``.
"""

import json
import os

import pytest
from PIL import Image

from pyaint import utils
from pyaint.bot import Bot, Palette
from pyaint.errors import NoCanvasError
from pyaint.palette import (
    DEFAULT_METRIC,
    METRIC_CIEDE2000,
    METRIC_RGB,
    ciede2000,
)

RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

POSITIONS = {RED: (100, 100), BLUE: (110, 100), WHITE: (120, 100)}


def make_bot(step=2, canvas=(0, 0, 8, 4), positions=None):
    bot = Bot()
    bot.settings[Bot.STEP] = step
    if canvas is not None:
        bot.init_canvas(canvas)
    if positions is not None:
        bot.init_palette(colors_pos=positions)
    return bot


def write_image(tmp_path, pixels, size):
    """pixels: dict {(x, y): rgb}; size: (w, h)."""
    img = Image.new("RGB", size, WHITE)
    for (x, y), rgb in pixels.items():
        img.putpixel((x, y), rgb)
    path = tmp_path / "input.png"
    img.save(path)
    return str(path)


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------
def test_adjusted_img_size_preserves_aspect_ratio():
    img = Image.new("RGB", (100, 50))
    assert utils.adjusted_img_size(img, (200, 200)) == (200, 100)


def test_adjusted_img_size_fits_within_bounds():
    img = Image.new("RGB", (3, 3))
    assert utils.adjusted_img_size(img, (10, 10)) == (10, 10)


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
def test_palette_nearest_color():
    p = Palette(colors_pos=POSITIONS)
    assert p.nearest_color((250, 0, 0)) == RED
    assert p.nearest_color((0, 0, 240)) == BLUE
    assert p.nearest_color((10, 10, 10)) in POSITIONS


def test_palette_dist_is_squared_euclidean():
    assert Palette.dist((0, 0, 0), (3, 4, 0)) == 25


def test_ciede2000_matches_sharma_reference_values():
    # Sharma, Wu & Dalal (2005), CIEDE2000 test data.
    pairs = (
        ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
        ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
        ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
        ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
        ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    )
    for lab1, lab2, expected in pairs:
        assert ciede2000(lab1, lab2) == pytest.approx(expected, abs=1e-4)


def test_default_metric_is_perceptual_ciede2000():
    p = Palette(colors_pos=POSITIONS)
    assert DEFAULT_METRIC == METRIC_CIEDE2000
    assert p.nearest_color((250, 0, 0)) == p.nearest_color(
        (250, 0, 0), METRIC_CIEDE2000
    )


def test_nearest_color_metric_can_change_the_pick():
    palette = {
        (128, 128, 128): (0, 0),
        (140, 110, 90): (1, 0),
        (110, 110, 150): (2, 0),
        (200, 200, 200): (3, 0),
    }
    p = Palette(colors_pos=palette)
    # A near-neutral dark blue: RGB Euclidean picks the warm brown, the
    # perceptual metric picks the cool blue-grey.
    assert p.nearest_color((0, 0, 17), METRIC_RGB) == (140, 110, 90)
    assert p.nearest_color((0, 0, 17), METRIC_CIEDE2000) == (110, 110, 150)


def test_unknown_metric_falls_back_to_default():
    p = Palette(colors_pos=POSITIONS)
    assert p.nearest_color((250, 0, 0), "nonsense") == RED


# ---------------------------------------------------------------------------
# process
# ---------------------------------------------------------------------------
def test_process_requires_canvas(tmp_path):
    path = write_image(tmp_path, {}, (2, 1))
    bot = make_bot(canvas=None, positions=POSITIONS)
    with pytest.raises(NoCanvasError):
        bot.process(path)


def test_process_maps_pixels_to_palette_colors(tmp_path):
    path = write_image(tmp_path, {(0, 0): RED, (1, 0): BLUE}, (2, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    cmap = bot.process(path)
    assert set(cmap).issubset(set(POSITIONS))
    assert RED in cmap and BLUE in cmap
    assert all(lines for lines in cmap.values())


def test_process_respects_color_metric(tmp_path):
    palette = {
        (128, 128, 128): (0, 0),
        (140, 110, 90): (1, 0),
        (110, 110, 150): (2, 0),
        (200, 200, 200): (3, 0),
    }
    path = write_image(tmp_path, {(0, 0): (0, 0, 17)}, (1, 1))
    bot = make_bot(step=1, canvas=(0, 0, 1, 1), positions=palette)
    assert bot.color_metric == DEFAULT_METRIC
    assert (110, 110, 150) in bot.process(path, mode=Bot.SLOTTED)

    bot.color_metric = METRIC_RGB
    assert (140, 110, 90) in bot.process(path, mode=Bot.SLOTTED)


def test_process_ignore_white_slotted_omits_white(tmp_path):
    path = write_image(tmp_path, {(0, 0): RED, (1, 0): WHITE}, (2, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    cmap = bot.process(path, flags=Bot.IGNORE_WHITE, mode=Bot.SLOTTED)
    assert WHITE not in cmap
    assert RED in cmap


def test_process_ignores_transparent_pixels(tmp_path):
    palette = {RED: (0, 0), BLUE: (1, 0), WHITE: (2, 0), (0, 0, 0): (3, 0)}
    img = Image.new("RGBA", (2, 1), (0, 0, 0, 0))  # transparent black
    img.putpixel((1, 0), (255, 0, 0, 255))
    path = tmp_path / "transparent.png"
    img.save(path)

    bot = make_bot(step=1, canvas=(0, 0, 2, 1), positions=palette)
    cmap = bot.process(str(path), flags=Bot.IGNORE_TRANSPARENT, mode=Bot.SLOTTED)
    assert (0, 0, 0) not in cmap  # the bug: transparent was painted black
    assert RED in cmap

    # Without the flag the transparent pixel still maps to its RGB (black).
    legacy = bot.process(str(path), flags=0, mode=Bot.SLOTTED)
    assert (0, 0, 0) in legacy


def test_layered_transparent_gap_is_not_bridged(tmp_path):
    palette = {RED: (0, 0), WHITE: (2, 0), (0, 0, 0): (3, 0)}
    img = Image.new("RGBA", (3, 1), (0, 0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0, 255))
    img.putpixel((2, 0), (255, 0, 0, 255))
    path = tmp_path / "gap.png"
    img.save(path)

    bot = make_bot(step=1, canvas=(0, 0, 3, 1), positions=palette)
    cmap = bot.process(str(path), flags=Bot.IGNORE_TRANSPARENT, mode=Bot.LAYERED)
    # Two separate strokes; the transparent middle must not be painted over.
    assert cmap[RED] == [((0, 0), (0, 0)), ((2, 0), (2, 0))]


def test_transparent_alpha_cutoff(tmp_path):
    palette = {(0, 0, 0): (3, 0), RED: (0, 0)}
    img = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    img.putpixel((0, 0), (0, 0, 0, Bot.ALPHA_CUTOFF - 1))
    img.putpixel((1, 0), (0, 0, 0, Bot.ALPHA_CUTOFF))
    path = tmp_path / "alpha.png"
    img.save(path)

    bot = make_bot(step=1, canvas=(0, 0, 2, 1), positions=palette)
    cmap = bot.process(str(path), flags=Bot.IGNORE_TRANSPARENT, mode=Bot.SLOTTED)
    assert cmap[(0, 0, 0)] == [((1, 0), (1, 0))]


def test_process_coordinates_within_canvas(tmp_path):
    path = write_image(tmp_path, {(0, 0): RED, (1, 0): BLUE}, (2, 1))
    cx, cy, cw, ch = (10, 20, 8, 4)
    bot = make_bot(step=2, canvas=(cx, cy, cx + cw, cy + ch), positions=POSITIONS)
    cmap = bot.process(path)
    for lines in cmap.values():
        for start, end in lines:
            for x, y in (start, end):
                assert cx <= x <= cx + cw
                assert cy <= y <= cy + ch


def test_palette_samples_from_provided_image():
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    img = Image.new("RGB", (40, 40))
    for i, c in enumerate(colours):
        r, cc = divmod(i, 2)
        for y in range(r * 20, r * 20 + 20):
            for x in range(cc * 20, cc * 20 + 20):
                img.putpixel((x, y), c)
    palette = Palette(box=(0, 0, 40, 40), rows=2, columns=2, image=img)
    assert set(palette.colors) == set(colours)


def test_apply_detection_samples_from_provided_image(monkeypatch):
    """Auto-detect must sample the captured screenshot, not a fresh one."""
    import pyaint.palette as palette_mod
    from pyaint.locators import Detection

    def fail_screenshot(*args, **kwargs):
        raise AssertionError("apply_detection should use the provided image")

    monkeypatch.setattr(palette_mod.pyautogui, "screenshot", fail_screenshot)

    img = Image.new("RGB", (60, 40), (255, 255, 255))
    img.paste((255, 0, 0), (10, 10, 20, 20))
    img.paste((0, 0, 255), (20, 10, 30, 20))
    detection = Detection(
        canvas=(0, 0, 60, 40), palette=(10, 10, 20, 10), palette_rows=1, palette_cols=2
    )
    bot = Bot()
    applied = bot.apply_detection(detection, image=img)
    assert "canvas" in applied and "palette" in applied
    assert len(bot._palette.colors) == 2


def test_process_accepts_mode_strings_from_config(tmp_path):
    """Regression: mode was compared with ``is`` and crashed on JSON strings."""
    path = write_image(tmp_path, {(0, 0): RED}, (1, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    for mode in (Bot.LAYERED, Bot.SLOTTED):
        parsed = json.loads(json.dumps(mode))  # a distinct string object
        cmap = bot.process(path, mode=parsed)
        assert cmap


def test_slotted_returns_plain_columns(tmp_path):
    path = write_image(tmp_path, {(0, 0): RED, (1, 0): BLUE}, (2, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    cmap = bot.process(path, mode=Bot.SLOTTED)
    for color, lines in cmap.items():
        assert color in POSITIONS
        for line in lines:
            assert len(line) == 2  # (start, end), not (color, ...)


# ---------------------------------------------------------------------------
# precompute / cache
# ---------------------------------------------------------------------------
def test_cache_filename_requires_canvas():
    bot = make_bot(canvas=None, positions=POSITIONS)
    assert bot.get_cache_filename("whatever.png") is None


def test_cache_filename_depends_on_color_metric(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = write_image(tmp_path, {(0, 0): RED}, (2, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    bot.color_metric = METRIC_RGB
    rgb_name = bot.get_cache_filename(path)
    bot.color_metric = METRIC_CIEDE2000
    ciede_name = bot.get_cache_filename(path)
    assert rgb_name != ciede_name


def test_precompute_then_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = write_image(tmp_path, {(0, 0): RED, (1, 0): BLUE}, (2, 1))
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)

    live = bot.process(path)
    cache_file = bot.precompute(path)
    assert os.path.exists(cache_file)

    cached = bot.load_cached(cache_file)
    assert cached is not None
    assert set(cached["cmap"].keys()) == set(live.keys())


def test_load_cached_rejects_stale(tmp_path):
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    assert bot.load_cached(str(tmp_path / "nope.json")) is None


# ---------------------------------------------------------------------------
# process_region
# ---------------------------------------------------------------------------
def test_process_region_stays_within_canvas_target(tmp_path):
    path = write_image(
        tmp_path,
        {(0, 0): RED, (1, 0): BLUE, (0, 1): RED, (1, 1): BLUE},
        (2, 2),
    )
    bot = make_bot(step=2, canvas=(0, 0, 20, 20), positions=POSITIONS)
    cmap = bot.process_region(
        path, (0, 0, 2, 2), canvas_target=(10, 10, 4, 4), mode=Bot.SLOTTED
    )
    assert cmap
    for lines in cmap.values():
        for start, end in lines:
            for x, y in (start, end):
                assert 10 <= x <= 14
                assert 10 <= y <= 14


# ---------------------------------------------------------------------------
# colour-selection strategy (profile-driven, no clicks performed)
# ---------------------------------------------------------------------------
def test_color_source_uses_palette(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    assert bot._color_source(RED) == "palette"


def test_color_source_none_when_absent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    bot = make_bot(step=2, canvas=(0, 0, 4, 2), positions=POSITIONS)
    assert bot._color_source((1, 2, 3)) == "none"
