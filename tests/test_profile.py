"""Tests for the taught-environment Profile."""

import copy

from pyaint import profile as pyaint_profile
from pyaint.profile import Profile, box_to_wh


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
        "drawing_settings": {"delay": 0.5},  # preference, must be ignored
        "pause_key": "q",
    }
    p = Profile.from_config(config)
    assert p["Palette"]["status"] is True
    assert p["Palette"]["rows"] == 2
    assert p["Palette"]["box"] == [1, 2, 3, 4]
    assert p.mspaint_mode == {"enabled": True, "delay": 0.25}
    # untouched tools keep defaults
    assert p["New Layer"]["status"] is False


def test_to_config_round_trip():
    config = {
        "Palette": {"status": True, "box": [1, 2, 3, 4], "rows": 4, "cols": 5},
        "MSPaint Mode": {"enabled": True, "delay": 0.4},
        "target": "skribbl",
    }
    p = Profile.from_config(config)
    out = p.to_config()
    p2 = Profile.from_config(out)
    assert p2["Palette"]["rows"] == 4
    assert p2["Palette"]["cols"] == 5
    assert p2.mspaint_mode == {"enabled": True, "delay": 0.4}
    assert p2.target == "skribbl"


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
            "Palette": {"box": [1, 1, 9, 9]},
        }
    )
    assert p.canvas_rect() == (0, 0, 10, 20)
    assert p.palette_rect() == (1, 1, 8, 8)
    assert Profile().canvas_rect() is None


def test_from_config_does_not_alias_input():
    config = {"Palette": {"status": False, "rows": 3}}
    original = copy.deepcopy(config)
    p = Profile.from_config(config)
    p["Palette"]["rows"] = 42
    assert config == original


def test_snapshot_and_apply_environment_round_trip():
    p = Profile(target="skribbl")
    p["Palette"]["status"] = True
    p["Palette"]["box"] = [1, 2, 3, 4]
    p.mspaint_mode["enabled"] = True
    snapshot = p.snapshot_environment()

    p["Palette"]["box"] = None
    p.mspaint_mode["enabled"] = False
    p.apply_environment(snapshot)

    assert p["Palette"]["box"] == [1, 2, 3, 4]
    assert p["Palette"]["status"] is True
    assert p.mspaint_mode["enabled"] is True
    # The environment carries geometry only; target identity is preserved.
    assert p.target == "skribbl"
    # The snapshot must be isolated from later mutations.
    snapshot["tools"]["Palette"]["box"] = [9, 9, 9, 9]
    assert p["Palette"]["box"] == [1, 2, 3, 4]


def test_apply_environment_resets_missing_tools():
    p = Profile()
    p["Canvas"]["box"] = [0, 0, 5, 5]
    p["Palette"]["status"] = True
    p.apply_environment({"tools": {"Canvas": {"box": [9, 9, 9, 9]}}})
    assert p["Canvas"]["box"] == [9, 9, 9, 9]
    # A tool absent from the snapshot falls back to defaults, not the old value.
    assert p["Palette"]["status"] is False
