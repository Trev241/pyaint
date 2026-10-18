"""Tests for detection annotation and robust palette sampling."""

from PIL import Image

from pyaint import utils
from pyaint.annotate import annotate_detection, annotate_palette
from pyaint.locators import Detection
from pyaint.palette import sample_median


class _FakePix:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


def test_grid_centers_matches_uniform_tiling():
    assert utils.grid_centers((0, 0, 4, 2), 1, 2) == [(1, 1), (3, 1)]
    assert utils.grid_centers((10, 20, 4, 4), 2, 2) == [
        (11, 21), (13, 21), (11, 23), (13, 23),
    ]
    # Degenerate box should not crash.
    assert utils.grid_centers((0, 0, 0, 0), 2, 2) == [(0, 0)] * 4


def test_sample_median_ignores_a_single_bad_pixel():
    data = {(x, y): (255, 0, 0) for y in range(3) for x in range(3)}
    data[(1, 1)] = (0, 0, 255)  # one anomalous centre pixel
    pix = _FakePix(data)
    assert sample_median(pix, 1, 1, 3, 3, radius=1) == (255, 0, 0)
    # radius 0 keeps the exact pixel (for very small cells).
    assert sample_median(pix, 1, 1, 3, 3, radius=0) == (0, 0, 255)


def test_annotate_detection_draws_palette_centres():
    image = Image.new("RGB", (40, 20), (0, 0, 0))
    detection = Detection(
        canvas=(0, 0, 40, 20),
        palette=(10, 5, 20, 8),
        palette_rows=1,
        palette_cols=2,
    )
    annotated = annotate_detection(image, detection)

    assert annotated.size == image.size
    assert annotated is not image
    # Palette centres: cell_w=10, cell_h=8 -> (15, 9) and (25, 9).
    assert annotated.getpixel((15, 9)) == (255, 255, 255)
    assert annotated.getpixel((25, 9)) == (255, 255, 255)
    # The source image must not be mutated.
    assert image.getpixel((15, 9)) == (0, 0, 0)


def test_annotate_palette_crops_and_dots_centres():
    image = Image.new("RGB", (40, 20), (0, 0, 0))
    out = annotate_palette(image, (10, 5, 20, 8), rows=1, cols=2)
    assert out.size == (20, 8)
    # Cell centres, relative to the crop: (5, 4) and (15, 4).
    assert out.getpixel((5, 4)) == (255, 255, 255)
    assert out.getpixel((15, 4)) == (255, 255, 255)


def test_annotate_handles_empty_detection():
    image = Image.new("RGB", (10, 10), (0, 0, 0))
    annotated = annotate_detection(image, Detection())
    assert annotated.size == image.size
    assert annotated.getpixel((5, 5)) == (0, 0, 0)
