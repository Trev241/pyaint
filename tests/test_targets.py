"""Tests for target recipes and the ``Profile.target`` field."""

import json

from pyaint import profile as pyaint_profile
from pyaint.profile import Profile
from pyaint.targets import (
    DEFAULT_RECIPE_ID,
    Recipe,
    RecipeRegistry,
    apply_profile_defaults,
    disabled_tools,
    get_recipe,
    list_recipes,
    load_user_recipes,
    merge_drawing_options,
    merge_drawing_settings,
)
import pytest


# ---------------------------------------------------------------------------
# Built-in registry
# ---------------------------------------------------------------------------
def test_builtin_recipes_present_and_valid():
    ids = {r.id for r in list_recipes()}
    assert {"generic", "mspaint", "skribbl"} <= ids
    for recipe in list_recipes():
        assert recipe.tools, recipe.id
        assert set(recipe.tools) <= set(pyaint_profile.TOOL_KEYS)


def test_skribbl_recipe_is_palette_only():
    recipe = get_recipe("skribbl")
    assert recipe.tools == ("Palette", "Canvas")
    assert recipe.supports_layers is False
    assert recipe.drawing_options["ignore_white_pixels"] is True


def test_get_recipe_falls_back_to_generic():
    assert get_recipe("does-not-exist").id == DEFAULT_RECIPE_ID
    assert DEFAULT_RECIPE_ID in get_recipe("nonsense").id


def test_available_locators_registry():
    from pyaint.locators import available_locators, locator_params

    names = available_locators()
    assert {"white_rect", "color_rect", "color_grid", "color_signature", "center_rect", "window_relative"} <= set(names)
    assert "color" in locator_params("color_rect")
    assert locator_params("does-not-exist") is None


# ---------------------------------------------------------------------------
# Recipe serialization / validation
# ---------------------------------------------------------------------------
def test_recipe_dict_round_trip():
    original = get_recipe("mspaint")
    restored = Recipe.from_dict(original.to_dict())
    assert restored == original


def test_recipe_from_dict_filters_unknown_tools():
    recipe = Recipe.from_dict({"id": "x", "tools": ["Palette", "Bogus", "Canvas"]})
    assert recipe.tools == ("Palette", "Canvas")


def test_recipe_from_dict_requires_id():
    with pytest.raises(ValueError):
        Recipe.from_dict({"name": "no id"})


# ---------------------------------------------------------------------------
# Applying recipe defaults
# ---------------------------------------------------------------------------
def test_merge_drawing_settings_overlays_present_keys_only():
    base = [0.1, 12, 0.5]
    assert merge_drawing_settings(base, {"delay": 0.2, "pixel_size": 8}) == [
        0.2,
        8,
        0.5,
    ]
    assert merge_drawing_settings(base, {}) == base


def test_merge_drawing_options_sets_and_clears_bits():
    ignore = 1
    assert merge_drawing_options(0, {"ignore_white_pixels": True}, ignore) == ignore
    assert merge_drawing_options(1, {"ignore_white_pixels": False}, ignore) == 0
    assert merge_drawing_options(0, {}, ignore) == 0


def test_merge_drawing_options_sets_and_clears_transparent_bit():
    white, transparent = 1, 2
    assert (
        merge_drawing_options(0, {"ignore_transparent_pixels": True}, white, transparent)
        == transparent
    )
    assert (
        merge_drawing_options(transparent, {"ignore_transparent_pixels": False}, white, transparent)
        == 0
    )


def test_apply_profile_defaults_disables_unused_tools():
    recipe = get_recipe("skribbl")
    assert set(disabled_tools(recipe)) == {
        "New Layer",
        "Color Button",
        "Color Button Okay",
    }
    profile = Profile()
    profile["New Layer"]["enabled"] = True
    profile.mspaint_mode["enabled"] = True
    apply_profile_defaults(profile, recipe)
    assert profile["New Layer"]["enabled"] is False
    assert profile.mspaint_mode["enabled"] is False


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------
def test_registry_load_dir(tmp_path):
    payload = {
        "id": "myapp",
        "name": "My App",
        "tools": ["Palette", "Canvas"],
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
# Inheritance / hidden base recipes
# ---------------------------------------------------------------------------
def test_registry_resolves_extends_with_deep_merge():
    registry = RecipeRegistry()
    registry.add_from_dict(
        {
            "id": "base",
            "name": "Base",
            "tools": ["Palette", "Canvas"],
            "drawing_settings": {"delay": 0.1, "pixel_size": 4},
            "drawing_options": {"ignore_white_pixels": True},
        }
    )
    child = registry.add_from_dict(
        {
            "id": "child",
            "name": "Child",
            "extends": "base",
            "drawing_settings": {"pixel_size": 9},
        }
    )
    assert child.tools == ("Palette", "Canvas")
    assert child.drawing_settings == {"delay": 0.1, "pixel_size": 9}
    assert child.drawing_options == {"ignore_white_pixels": True}
    assert child.extends == "base"


def test_add_from_dict_does_not_inherit_hidden():
    registry = RecipeRegistry()
    registry.add_from_dict(
        {"id": "base", "name": "Base", "hidden": True, "tools": ["Palette", "Canvas"]}
    )
    child = registry.add_from_dict({"id": "child", "name": "Child", "extends": "base"})
    assert child.hidden is False


def test_hidden_recipes_resolvable_but_not_listed():
    listed = {r.id for r in list_recipes()}
    assert "desktop-base" not in listed and "browser-base" not in listed
    assert get_recipe("desktop-base").hidden is True


def test_builtin_children_inherit_from_base():
    mspaint = get_recipe("mspaint")
    assert set(mspaint.tools) == {
        "Palette", "Canvas", "Color Button", "Color Button Okay",
    }
    assert mspaint.supports_layers is False  # overridden
    assert mspaint.supports_mspaint_mode is True  # inherited

    skribbl = get_recipe("skribbl")
    assert skribbl.tools == ("Palette", "Canvas")
    assert skribbl.drawing_options["ignore_white_pixels"] is True


# ---------------------------------------------------------------------------
# Profile.target integration
# ---------------------------------------------------------------------------
def test_target_is_an_environment_config_key():
    assert "target" in pyaint_profile.ENV_CONFIG_KEYS


def test_profile_target_round_trips_through_config():
    profile = Profile(target="skribbl")
    assert profile.to_config()["target"] == "skribbl"
    assert Profile.from_config(profile.to_config()).target == "skribbl"


def test_profile_target_defaults_to_generic():
    assert Profile().target == DEFAULT_RECIPE_ID
    assert Profile.from_config({}).target == DEFAULT_RECIPE_ID
