"""Unit tests for the pure preset data (no Qt needed)."""

from pyaint.ui import presets


def test_cartoon_and_realistic_exist_with_expected_shape():
    keys = {preset["key"] for preset in presets.SKETCH_PRESETS}
    assert {"cartoon", "realistic"} <= keys
    for preset in presets.SKETCH_PRESETS:
        assert preset["label"]
        assert preset["description"]
        assert set(preset["settings"]) == set(presets.SKETCH_PRESET_FIELDS)


def test_cartoon_is_less_aggressive_than_realistic():
    """Cartoon keeps colour edges and all strokes; Realistic tones harder."""
    cartoon = presets.preset_by_key("cartoon")["settings"]
    realistic = presets.preset_by_key("realistic")["settings"]
    assert cartoon["sketch_hue_threshold"] < realistic["sketch_hue_threshold"]
    assert cartoon["sketch_gradient_keep"] > realistic["sketch_gradient_keep"]
    assert cartoon["sketch_min_stroke"] > realistic["sketch_min_stroke"]


def test_match_preset_round_trips_and_handles_ints_and_bools():
    for preset in presets.SKETCH_PRESETS:
        values = dict(preset["settings"])
        # ``min_stroke`` etc. can arrive as floats from the sliders.
        values["sketch_min_stroke"] = float(values["sketch_min_stroke"])
        assert presets.match_preset(values) == preset["key"]


def test_match_preset_returns_none_for_a_manual_change():
    values = dict(presets.preset_by_key("cartoon")["settings"])
    values["sketch_hue_threshold"] = 999.0
    assert presets.match_preset(values) is None


def test_drawing_presets_control_pacing_only():
    keys = {preset["key"] for preset in presets.DRAWING_PRESETS}
    assert {"balanced", "smooth", "draft"} <= keys
    for preset in presets.DRAWING_PRESETS:
        assert preset["label"]
        assert preset["description"]
        assert set(preset["settings"]) == set(presets.DRAWING_PRESET_FIELDS)


def test_drawing_preset_match_round_trips_and_rejects_tuning():
    for preset in presets.DRAWING_PRESETS:
        values = dict(preset["settings"])
        assert presets.match_drawing_preset(values) == preset["key"]
    tuned = dict(presets.drawing_preset_by_key("smooth")["settings"])
    tuned["pixel_size"] = 999
    assert presets.match_drawing_preset(tuned) is None


def test_look_options_are_mode_aware():
    from pyaint import planner

    assert {key for key, _ in presets.look_options(planner.SKETCH)} == {
        preset["key"] for preset in presets.SKETCH_PRESETS
    }
    assert {key for key, _ in presets.look_options(planner.OUTLINE)} == {
        preset["key"] for preset in presets.DRAWING_PRESETS
    }
    assert presets.look_by_key(planner.SKETCH, "cartoon") is presets.preset_by_key(
        "cartoon"
    )
    assert (
        presets.look_by_key(planner.LAYERED, "draft")
        is presets.drawing_preset_by_key("draft")
    )
