"""Unit tests for the pure descriptor bands (no Qt needed)."""

from pyaint.ui import bands


def test_known_controls_have_units_and_bands():
    for control in (
        "detail",
        "drawing_speed",
        "skip_soft_shading",
        "skip_faint_edges",
        "join_distance",
        "smoothing",
    ):
        assert bands.band_count(control) >= 2
        assert bands.describe(control, 0) != ""


def test_detail_bands_at_boundaries():
    assert bands.describe("detail", 1) == "Fine"
    assert bands.describe("detail", 8) == "Fine"
    assert bands.describe("detail", 9) == "Balanced"
    assert bands.describe("detail", 12) == "Balanced"
    assert bands.describe("detail", 17) == "Balanced"
    assert bands.describe("detail", 18) == "Coarse"
    assert bands.unit("detail") == "px"


def test_skip_faint_edges_descends_with_the_keep_percentage():
    # 100% kept = nothing skipped = Off; a low keep percentage prunes hard.
    assert bands.describe("skip_faint_edges", 100) == "Off"
    assert bands.describe("skip_faint_edges", 80) == "Light"
    assert bands.describe("skip_faint_edges", 40) == "Strong"
    assert bands.unit("skip_faint_edges") == "%"


def test_band_index_tracks_the_label():
    assert bands.band_index("detail", 4) == 0
    assert bands.band_index("detail", 12) == 1
    assert bands.band_index("detail", 40) == 2


def test_unknown_control_is_safe():
    assert bands.describe("nope", 5) == ""
    assert bands.unit("nope") == ""
    assert bands.band_count("nope") == 0
