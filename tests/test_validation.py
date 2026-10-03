"""Tests for recipe validation (the per-recipe self-test)."""

from pyaint.profile import Profile
from pyaint.targets import (
    CURRENT_RECIPE_SCHEMA,
    REGISTRY,
    Recipe,
    apply_profile_defaults,
    get_recipe,
)
from pyaint.validation import recipe_is_valid, validate_recipe


def test_all_builtin_recipes_validate():
    for recipe in REGISTRY.all(include_hidden=True):
        assert validate_recipe(recipe) == [], (recipe.id, validate_recipe(recipe))


def test_builtin_visible_recipes_are_valid():
    for recipe in REGISTRY.all():
        assert recipe_is_valid(recipe)


def test_validate_flags_unknown_locator_type():
    recipe = Recipe(id="x", name="X", detection={"canvas": {"type": "bogus"}})
    assert any("unknown locator" in issue for issue in validate_recipe(recipe))


def test_validate_flags_unknown_params_and_settings():
    recipe = Recipe(
        id="x",
        name="X",
        detection={"canvas": {"type": "white_rect", "nope": 1}},
        drawing_settings={"bogus": 1},
        drawing_options={"also_bogus": True},
    )
    issues = validate_recipe(recipe)
    assert any("unknown params" in issue for issue in issues)
    assert any("drawing_settings" in issue for issue in issues)
    assert any("drawing_options" in issue for issue in issues)


def test_validate_flags_newer_schema_version():
    recipe = Recipe(id="x", name="X", schema_version=CURRENT_RECIPE_SCHEMA + 1)
    assert any("schema_version" in issue for issue in validate_recipe(recipe))


def test_validate_flags_bad_palette_colours():
    recipe = Recipe(id="x", name="X", palette=[(1, 2), (1, 2, 300)])
    issues = validate_recipe(recipe)
    assert len([i for i in issues if "palette colour" in i]) == 2


def test_gimp_recipe_uses_custom_colour_selection():
    profile = Profile()
    apply_profile_defaults(profile, get_recipe("gimp"))
    assert profile.color_selection == "custom"
