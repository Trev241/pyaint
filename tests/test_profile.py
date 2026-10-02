"""Tests for the taught-environment Profile."""

import copy

import pyaint_profile
from pyaint_profile import Profile, box_to_wh


def test_defaults_are_deep_isolated():
    a = Profile()
    b = Profile()
    a["New Layer"]["modifiers"]["ctrl"] = True
    a["Palette"]["rows"] = 99
    assert b["New Layer"]["modifiers"]["ctrl"] is False
    assert b["Palette"]["rows"] == 6


def test_mapping_access_over_tools():
    p = Profile()
    assert "Palette" in p
    assert "MSPaint Mode" not in p  # not a tool entry
    assert set(p.keys()) == set(pyaint_profile.TOOL_KEYS)
    assert p["Canvas"]["status"] is False
    assert p.get("missing") is None


def test_from_config_reads_environment_only():
    config = {
        "Palette": {"status": True, "box": [1, 2, 3, 4], "rows": 2, "cols": 3},
        "Canvas": {"status": True, "box": [0, 0, 10, 10]},
        "MSPaint Mode": {"enabled": True, "delay": 0.25},
        "color_selection": "custom",
        "drawing_settings": {"delay": 0.5},  # preference, must be ignored
        "pause_key": "q",
    }
    p = Profile.from_config(config)
    assert p["Palette"]["status"] is True
    assert p["Palette"]["rows"] == 2
    assert p["Palette"]["box"] == [1, 2, 3, 4]
    assert p.mspaint_mode == {"enabled": True, "delay": 0.25}
    assert p.color_selection == "custom"
    # untouched tools keep defaults
    assert p["Custom Colors"]["status"] is False


def test_to_config_round_trip():
    config = {
        "Palette": {"status": True, "box": [1, 2, 3, 4], "rows": 4, "cols": 5},
        "MSPaint Mode": {"enabled": True, "delay": 0.4},
        "color_selection": "palette",
    }
    p = Profile.from_config(config)
    out = p.to_config()
    p2 = Profile.from_config(out)
    assert p2["Palette"]["rows"] == 4
    assert p2["Palette"]["cols"] == 5
    assert p2.mspaint_mode == {"enabled": True, "delay": 0.4}
    assert p2.color_selection == "palette"
    # calibration is not part of config.json
    assert "calibration" not in out


def test_invalid_color_selection_falls_back_to_auto():
    assert Profile(color_selection="nonsense").color_selection == Profile.AUTO
    assert Profile(color_selection="palette").color_selection == Profile.PALETTE


def test_preset_dict_round_trip_with_calibration():
    p = Profile()
    p["Canvas"] = {"status": True, "box": [0, 0, 20, 20], "preview": None}
    p.calibration = {(255, 0, 0): (5, 6), (1, 2, 3): (7, 8)}
    data = p.to_dict()
    assert data["version"] == 1
    assert data["calibration"]["255,0,0"] == [5, 6]

    restored = Profile.from_dict(data)
    assert restored["Canvas"]["box"] == [0, 0, 20, 20]
    assert restored.calibration == {(255, 0, 0): (5, 6), (1, 2, 3): (7, 8)}


def test_to_dict_is_a_copy():
    p = Profile()
    data = p.to_dict()
    data["tools"]["Palette"]["rows"] = 1234
    assert p["Palette"]["rows"] == 6


def test_box_to_wh_normalizes_and_handles_missing():
    assert box_to_wh([10, 20, 40, 60]) == (10, 20, 30, 40)
    assert box_to_wh([40, 60, 10, 20]) == (10, 20, 30, 40)
    assert box_to_wh(None) is None
    assert box_to_wh([]) is None
    assert box_to_wh([1, 2, 3]) is None


def test_rect_helpers():
    p = Profile.from_config(
        {
            "Canvas": {"box": [0, 0, 10, 20]},
            "Custom Colors": {"box": [5, 5, 15, 25]},
            "Palette": {"box": [1, 1, 9, 9]},
        }
    )
    assert p.canvas_rect() == (0, 0, 10, 20)
    assert p.custom_colors_rect() == (5, 5, 10, 20)
    assert p.palette_rect() == (1, 1, 8, 8)
    assert Profile().canvas_rect() is None


def test_from_config_does_not_alias_input():
    config = {"Palette": {"status": False, "rows": 3}}
    original = copy.deepcopy(config)
    p = Profile.from_config(config)
    p["Palette"]["rows"] = 42
    assert config == original
