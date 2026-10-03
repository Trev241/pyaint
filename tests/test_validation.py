"""Tests for recipe validation (the per-recipe self-test)."""

from pyaint.targets import CURRENT_RECIPE_SCHEMA, REGISTRY, Recipe
from pyaint.validation import validate_recipe


def test_all_builtin_recipes_validate():
    for recipe in REGISTRY.all(include_hidden=True):
        assert validate_recipe(recipe) == [], (recipe.id, validate_recipe(recipe))


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
