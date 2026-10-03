"""Tests for target recipes and the ``Profile.target`` field."""

import json

import pyaint_profile
from pyaint_profile import Profile
from pyaint_targets import (
    DEFAULT_RECIPE_ID,
    Recipe,
    RecipeRegistry,
    get_recipe,
    list_recipes,
    load_user_recipes,
)
import pytest


# ---------------------------------------------------------------------------
# Built-in registry
# ---------------------------------------------------------------------------
def test_builtin_recipes_present_and_valid():
    ids = {r.id for r in list_recipes()}
    assert {"generic", "mspaint", "gimp", "skribbl"} <= ids
    for recipe in list_recipes():
        assert recipe.tools, recipe.id
        assert set(recipe.tools) <= set(pyaint_profile.TOOL_KEYS)
        assert recipe.color_selection in pyaint_profile.VALID_COLOR_SELECTION


def test_skribbl_recipe_is_palette_only():
    recipe = get_recipe("skribbl")
    assert recipe.tools == ("Palette", "Canvas")
    assert recipe.color_selection == "palette"
    assert recipe.supports_custom_colors is False
    assert recipe.supports_layers is False
    assert recipe.drawing_options["ignore_white_pixels"] is True


def test_get_recipe_falls_back_to_generic():
    assert get_recipe("does-not-exist").id == DEFAULT_RECIPE_ID
    assert DEFAULT_RECIPE_ID in get_recipe("nonsense").id


# ---------------------------------------------------------------------------
# Recipe serialization / validation
# ---------------------------------------------------------------------------
def test_recipe_dict_round_trip():
    original = get_recipe("gimp")
    restored = Recipe.from_dict(original.to_dict())
    assert restored == original


def test_recipe_from_dict_filters_unknown_tools():
    recipe = Recipe.from_dict({"id": "x", "tools": ["Palette", "Bogus", "Canvas"]})
    assert recipe.tools == ("Palette", "Canvas")


def test_recipe_from_dict_invalid_color_selection_falls_back():
    assert Recipe.from_dict({"id": "x", "color_selection": "wat"}).color_selection == "auto"


def test_recipe_from_dict_requires_id():
    with pytest.raises(ValueError):
        Recipe.from_dict({"name": "no id"})


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------
def test_registry_load_dir(tmp_path):
    payload = {
        "id": "myapp",
        "name": "My App",
        "tools": ["Palette", "Canvas"],
        "color_selection": "palette",
    }
    (tmp_path / "myapp.json").write_text(json.dumps(payload), encoding="utf-8")

    registry = RecipeRegistry()
    loaded = registry.load_dir(str(tmp_path))
    assert [r.id for r in loaded] == ["myapp"]
    assert registry.get("myapp").name == "My App"


def test_registry_load_dir_skips_invalid(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    registry = RecipeRegistry()
    assert registry.load_dir(str(tmp_path)) == []


def test_load_user_recipes_registers_recipe(tmp_path):
    payload = {
        "id": "community-test",
        "name": "Community Test",
        "tools": ["Palette", "Canvas"],
    }
    (tmp_path / "community.json").write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_user_recipes([str(tmp_path)])
    assert [r.id for r in loaded] == ["community-test"]
    assert get_recipe("community-test").name == "Community Test"


def test_load_user_recipes_ignores_missing_dir():
    assert load_user_recipes(["/definitely/not/a/real/dir"]) == []


# ---------------------------------------------------------------------------
# Profile.target integration
# ---------------------------------------------------------------------------
def test_target_is_an_environment_config_key():
    assert "target" in pyaint_profile.ENV_CONFIG_KEYS


def test_profile_target_round_trips_through_config_and_preset():
    profile = Profile(target="skribbl")
    assert profile.to_config()["target"] == "skribbl"
    assert Profile.from_config(profile.to_config()).target == "skribbl"

    preset = profile.to_dict()
    assert preset["target"] == "skribbl"
    assert Profile.from_dict(preset).target == "skribbl"


def test_profile_target_defaults_to_generic():
    assert Profile().target == DEFAULT_RECIPE_ID
    assert Profile.from_config({}).target == DEFAULT_RECIPE_ID
