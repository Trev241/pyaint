"""Tests for screen locators and auto-detection (headless, synthetic images)."""

from PIL import Image

from pyaint.bot import Bot
from pyaint import bot as bot_module
from pyaint.locators import (
    Detection,
    detect_target,
    find_color_grid,
    find_color_rect,
    find_color_signature,
    find_white_rect,
    window_relative_rect,
)
from pyaint.targets import SKRIBBL_PALETTE, Recipe, get_recipe

SWATCH_COLORS = [
    (255, 0, 0),
    (0, 200, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (128, 0, 128),
    (255, 128, 0),
]


def make_screen():
    """A gray screen with a white canvas and a 2x4 colourful palette grid."""
    img = Image.new("RGB", (300, 200), (120, 120, 120))
    for y in range(20, 130):
        for x in range(30, 210):
            img.putpixel((x, y), (255, 255, 255))
    for r in range(2):
        for c in range(4):
            color = SWATCH_COLORS[r * 4 + c]
            x0 = 40 + c * 20
            y0 = 150 + r * 20
            for y in range(y0, y0 + 14):
                for x in range(x0, x0 + 14):
                    img.putpixel((x, y), color)
    return img


def make_skribbl_screen():
    """A blue page with a black canvas and the real 2x13 skribbl palette."""
    img = Image.new("RGB", (800, 600), (36, 81, 149))
    for y in range(60, 360):
        for x in range(200, 600):
            img.putpixel((x, y), (0, 0, 0))
    for i, color in enumerate(SKRIBBL_PALETTE):
        r, c = divmod(i, 13)
        for y in range(400 + r * 20, 420 + r * 20):
            for x in range(100 + c * 20, 120 + c * 20):
                img.putpixel((x, y), tuple(color))
    return img


# ---------------------------------------------------------------------------
# White rectangle (canvas)
# ---------------------------------------------------------------------------
def test_find_white_rect_finds_canvas():
    rect = find_white_rect(make_screen())
    assert rect == (30, 20, 180, 110)


def test_find_white_rect_aspect_filter():
    img = Image.new("RGB", (400, 400), (0, 0, 0))
    for y in range(50, 200):
        for x in range(50, 250):
            img.putpixel((x, y), (255, 255, 255))  # 200x150, aspect 1.333
    assert find_white_rect(img, aspect=1.3333, aspect_tolerance=0.15) == (50, 50, 200, 150)
    assert find_white_rect(img, aspect=1.0, aspect_tolerance=0.15) is None


def test_find_white_rect_none_when_absent():
    assert find_white_rect(Image.new("RGB", (100, 100), (20, 20, 20))) is None


def test_find_white_rect_rejects_tiny_regions():
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    for y in range(5):
        for x in range(5):
            img.putpixel((x, y), (255, 255, 255))
    assert find_white_rect(img, min_fraction=0.02) is None


# ---------------------------------------------------------------------------
# Colour grid (palette)
# ---------------------------------------------------------------------------
def test_find_color_grid_detects_rows_and_columns():
    result = find_color_grid(make_screen())
    assert result is not None
    rect, rows, cols = result
    assert (rows, cols) == (2, 4)
    # bbox encloses the swatches, not the white canvas
    assert rect[0] <= 40 and rect[1] <= 150
    assert rect[0] + rect[2] >= 113 and rect[1] + rect[3] >= 183


def test_find_color_grid_none_without_colour():
    assert find_color_grid(Image.new("RGB", (100, 100), (128, 128, 128))) is None


# ---------------------------------------------------------------------------
# Colour signature
# ---------------------------------------------------------------------------
def test_find_color_signature_matches_known_colour():
    rect = find_color_signature(make_screen(), [(255, 0, 0)])
    assert rect is not None
    assert rect[0] <= 40 and rect[0] + rect[2] >= 54


def test_find_color_signature_none_without_colours():
    assert find_color_signature(make_screen(), []) is None


def test_find_color_signature_none_when_no_match():
    assert find_color_signature(make_screen(), [(1, 2, 3)], tolerance=1) is None


def test_find_color_signature_prefers_multicolour_region():
    img = Image.new("RGB", (400, 200), (10, 10, 10))
    # A large single-colour white block...
    for y in range(20, 180):
        for x in range(20, 120):
            img.putpixel((x, y), (255, 255, 255))
    # ...and a small two-colour block that should win.
    for y in range(20, 40):
        for x in range(200, 260):
            img.putpixel((x, y), (255, 0, 0) if x < 230 else (0, 255, 0))
    rect = find_color_signature(
        img, [(255, 255, 255), (255, 0, 0), (0, 255, 0)], tolerance=10, gap=0
    )
    assert rect is not None and rect[0] >= 190


def _sparse_colour_frame(size=(400, 200), box=(10, 10, 310, 120)):
    red, green, blue = (255, 0, 0), (0, 255, 0), (0, 0, 255)
    img = Image.new("RGB", size, (0, 0, 0))
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        for t in range(2):
            img.putpixel((x, y0 + t), red)
            img.putpixel((x, y1 - t), blue)
    for y in range(y0, y1 + 1):
        for t in range(2):
            img.putpixel((x0 + t, y), red)
            img.putpixel((x1 - t, y), green)
    return img


def test_find_color_signature_prefers_dense_over_sparse_same_colours():
    red, green, blue = (255, 0, 0), (0, 255, 0), (0, 0, 255)
    img = _sparse_colour_frame()
    # A dense block with the same three colours.
    for i, c in enumerate((red, green, blue)):
        for y in range(60 + i * 10, 70 + i * 10):
            for x in range(340, 380):
                img.putpixel((x, y), c)
    rect = find_color_signature(img, [red, green, blue], tolerance=10, gap=0)
    assert rect is not None and 340 <= rect[0] <= 360


def test_find_color_signature_min_fill_skips_sparse():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    img = _sparse_colour_frame()
    assert find_color_signature(img, colors, tolerance=10, gap=0) is not None
    assert find_color_signature(img, colors, tolerance=10, gap=0, min_fill=0.5) is None


# ---------------------------------------------------------------------------
# Colour rectangle (canvas of a known colour)
# ---------------------------------------------------------------------------
def test_find_color_rect_finds_black_canvas():
    assert find_color_rect(make_skribbl_screen(), (0, 0, 0), tolerance=40) == (
        200,
        60,
        400,
        300,
    )


def test_find_color_rect_none_when_absent():
    assert find_color_rect(Image.new("RGB", (100, 100), (0, 255, 0)), (0, 0, 0)) is None


def test_find_color_rect_aspect_filter_rejects_wrong_shape():
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    for y in range(50, 250):
        for x in range(50, 250):
            img.putpixel((x, y), (0, 0, 0))  # 200x200 square, aspect 1.0
    assert find_color_rect(img, (0, 0, 0), aspect=1.3333, aspect_tolerance=0.15) is None
    assert find_color_rect(img, (0, 0, 0), aspect=1.0, aspect_tolerance=0.15) == (
        50,
        50,
        200,
        200,
    )


# ---------------------------------------------------------------------------
# Window relative
# ---------------------------------------------------------------------------
def test_window_relative_rect_maps_normalized_coordinates():
    assert window_relative_rect((100, 50, 400, 300), (0.25, 0.5, 0.5, 0.25)) == (
        200,
        200,
        200,
        75,
    )


# ---------------------------------------------------------------------------
# detect_target orchestration
# ---------------------------------------------------------------------------
def test_detect_target_for_skribbl_recipe():
    detection = detect_target(get_recipe("skribbl"), make_skribbl_screen())
    assert detection
    assert detection.canvas == (200, 60, 400, 300)
    assert detection.palette == (100, 400, 260, 40)
    assert (detection.palette_rows, detection.palette_cols) == (2, 13)
    assert "canvas" in detection.summary() and "palette" in detection.summary()


def test_detect_target_without_detection_config_is_falsy():
    detection = detect_target(Recipe(id="x", name="x"), make_screen())
    assert not detection


def test_detect_target_window_relative_uses_provider():
    recipe = Recipe(
        id="w",
        name="w",
        detection={
            "canvas": {
                "type": "window_relative",
                "window": "skribbl",
                "rect": [0.1, 0.1, 0.8, 0.8],
            }
        },
    )
    detection = detect_target(
        recipe,
        Image.new("RGB", (10, 10), (0, 0, 0)),
        window_provider=lambda title: (100, 100, 200, 100),
    )
    assert detection.canvas == (120, 110, 160, 80)


def test_register_locator_adds_detection_type():
    from pyaint import locators

    def handler(image, recipe, params, provider):
        return (1, 2, 3, 4), None, None

    locators.register_locator("fixed-test-rect", set())(handler)
    try:
        recipe = Recipe(
            id="x", name="X", detection={"canvas": {"type": "fixed-test-rect"}}
        )
        detection = detect_target(recipe, Image.new("RGB", (10, 10)))
        assert detection.canvas == (1, 2, 3, 4)
    finally:
        locators._LOCATORS.pop("fixed-test-rect", None)


# ---------------------------------------------------------------------------
# Bot integration
# ---------------------------------------------------------------------------
def test_bot_detect_target_captures_screen(monkeypatch):
    bot = Bot()
    monkeypatch.setattr(bot, "capture_screen", lambda: make_skribbl_screen())
    detection = bot.detect_target(get_recipe("skribbl"))
    assert detection.canvas and detection.palette


def test_bot_apply_detection_updates_profile(monkeypatch):
    monkeypatch.chdir(".")  # keep cwd stable
    screen = make_screen()

    def fake_screenshot(region=None):
        if region:
            x, y, w, h = region
            return screen.crop((x, y, x + w, y + h))
        return screen

    monkeypatch.setattr(bot_module.pyautogui, "screenshot", fake_screenshot)

    bot = Bot()
    detection = Detection(
        canvas=(30, 20, 180, 110),
        palette=(40, 150, 74, 34),
        palette_rows=2,
        palette_cols=4,
    )
    applied = bot.apply_detection(detection)

    assert applied == ["canvas", "palette"]
    assert bot.profile["Canvas"]["box"] == [30, 20, 210, 130]
    assert bot.profile["Canvas"]["status"] is True
    assert bot.profile["Palette"]["status"] is True
    assert bot.profile["Palette"]["rows"] == 2
    assert bot.profile["Palette"]["cols"] == 4
    assert bot._palette is not None
