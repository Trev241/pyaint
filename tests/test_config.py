"""Tests for config.json I/O and the environment/preferences split."""

from pyaint.config import build_payload, load_config, save_config, split_preferences
from pyaint.profile import Profile


def test_load_config_missing_returns_empty(tmp_path):
    assert load_config(str(tmp_path / "nope.json")) == {}


def test_load_config_invalid_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_config(str(path)) == {}


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "config.json"
    payload = {"pause_key": "q", "drawing_settings": {"delay": 0.2}}
    assert save_config(str(path), payload) is True
    assert load_config(str(path)) == payload


def test_split_preferences_excludes_environment_keys():
    config = {
        "Palette": {"status": True},
        "MSPaint Mode": {"enabled": True},
        "color_selection": "palette",
        "target": "skribbl",
        "pause_key": "q",
        "drawing_settings": {"delay": 0.2},
    }
    prefs = split_preferences(config)
    assert prefs == {"pause_key": "q", "drawing_settings": {"delay": 0.2}}


def test_build_payload_merges_environment_and_preferences():
    profile = Profile(target="skribbl")
    payload = build_payload({"pause_key": "q"}, profile)
    assert payload["pause_key"] == "q"
    assert payload["target"] == "skribbl"
    assert payload["color_selection"] == profile.color_selection
    assert "Palette" in payload
