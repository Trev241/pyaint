"""Unit tests for the pure plan renderer (no Qt, no screen)."""

from PIL import Image

from pyaint import planner, render
from pyaint.palette import Palette


def test_render_plan_line_art_translates_canvas_origin():
    cmap = {planner.OUTLINE_COLOUR: [[(110, 110), (115, 110)]]}
    image = render.render_plan(cmap, (100, 100, 20, 20), 1, planner.OUTLINE)
    assert image.size == (20, 20)
    assert image.getpixel((10, 10)) == (0, 0, 0)
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_render_plan_empty_cmap_is_blank():
    image = render.render_plan({}, (0, 0, 8, 6), 1, planner.SKETCH)
    assert image.size == (8, 6)
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_render_plan_fill_mode_uses_palette_colour():
    cmap = {(255, 0, 0): [[(0, 2), (5, 2)]]}
    image = render.render_plan(cmap, (0, 0, 8, 6), 2, planner.SLOTTED)
    assert image.getpixel((2, 2)) == (255, 0, 0)


def test_render_fills_places_cells_at_origin():
    grid = [[None, (0, 0, 255)], [None, None]]
    image = render.render_fills(grid, (0, 0, 10, 10), (4, 2), 2)
    assert image.size == (10, 10)
    assert image.getpixel((6, 2)) == (0, 0, 255)
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_preview_fill_mode_reports_grid_cells():
    image = Image.new("RGB", (8, 8), (255, 0, 0))
    palette = Palette(colors_pos={(255, 0, 0): (0, 0)})
    frame, meta = render.preview(
        image, (0, 0, 16, 16), 2, palette, "rgb", 0, planner.SLOTTED, {}
    )
    assert frame.size == (16, 16)
    assert "cells" in meta
    assert frame.getpixel((4, 4)) == (255, 0, 0)
