"""Static self-tests for target recipes.

``validate_recipe`` checks a recipe against the schema and the set of
registered locator types, so a typo in a user/community recipe is reported
instead of silently doing nothing. It needs no screen, so it can run in tests
and at startup.
"""

from typing import Any, List

from pyaint.locators import available_locators, locator_params
from pyaint.profile import TOOL_KEYS
from pyaint.targets import CURRENT_RECIPE_SCHEMA, Recipe

_SETTING_KEYS = {"delay", "pixel_size", "jump_delay", "jump_threshold"}
_OPTION_KEYS = {"ignore_white_pixels"}


def _validate_detection(detection: Any) -> List[str]:
    issues: List[str] = []
    if not isinstance(detection, dict):
        return ["detection must be an object"]
    for element in ("canvas", "palette"):
        spec = detection.get(element)
        if spec is None:
            continue
        specs = spec if isinstance(spec, list) else [spec]
        for item in specs:
            if not isinstance(item, dict):
                issues.append(f"{element}: locator spec must be an object")
                continue
            kind = item.get("type")
            if kind not in available_locators():
                issues.append(
                    f"{element}: unknown locator type {kind!r} "
                    f"(known: {sorted(available_locators())})"
                )
                continue
            allowed = locator_params(kind) or set()
            unknown = set(item) - allowed - {"type"}
            if unknown:
                issues.append(
                    f"{element}: {kind} got unknown params {sorted(unknown)} "
                    f"(allowed: {sorted(allowed)})"
                )
    return issues


def validate_recipe(recipe: Recipe) -> List[str]:
    """Return a list of human-readable problems (empty means valid)."""
    issues: List[str] = []
    if not recipe.id:
        issues.append("missing id")
    if recipe.schema_version > CURRENT_RECIPE_SCHEMA:
        issues.append(
            f"schema_version {recipe.schema_version} is newer than supported "
            f"{CURRENT_RECIPE_SCHEMA}"
        )
    if not recipe.tools:
        issues.append("recipe uses no tools")
    unknown_tools = [t for t in recipe.tools if t not in TOOL_KEYS]
    if unknown_tools:
        issues.append(f"unknown tools: {unknown_tools}")
    unknown_settings = set(recipe.drawing_settings) - _SETTING_KEYS
    if unknown_settings:
        issues.append(f"unknown drawing_settings: {sorted(unknown_settings)}")
    unknown_options = set(recipe.drawing_options) - _OPTION_KEYS
    if unknown_options:
        issues.append(f"unknown drawing_options: {sorted(unknown_options)}")
    for color in recipe.palette or []:
        if (
            len(color) != 3
            or any(not isinstance(v, int) or not 0 <= v <= 255 for v in color)
        ):
            issues.append(f"invalid palette colour: {color!r}")
    issues.extend(_validate_detection(recipe.detection))
    return issues
