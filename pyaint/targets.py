"""Target recipes: declarative descriptions of how to drive a drawing app.

A *recipe* is data, not code. It says which parts of the taught environment a
target actually needs, which colour-selection strategy to use, and what drawing
defaults to apply. This lets Pyaint support several applications without a
code branch per app (see ``AGENTS/proposals/ADR-0001-driver-strategy.md``).

Built-in recipes cover the common cases; additional recipes can be dropped in
as JSON files and loaded with :meth:`RecipeRegistry.load_dir`. The engine still
falls back to fully manual configuration for anything not covered.
"""

from __future__ import annotations

import copy
import glob
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from pyaint import paths
from pyaint.profile import AUTO, TOOL_KEYS, VALID_COLOR_SELECTION

DEFAULT_RECIPE_ID = "generic"

# Bump when the recipe schema changes in a backwards-incompatible way.
CURRENT_RECIPE_SCHEMA = 1

# The two tools every target needs; used as a safe fallback.
_MINIMUM_TOOLS: Tuple[str, ...] = ("Palette", "Canvas")


@dataclass
class Recipe:
    """A declarative target profile."""

    id: str
    name: str
    description: str = ""
    # Which Profile tools this target uses (controls what Setup shows).
    tools: Tuple[str, ...] = _MINIMUM_TOOLS
    # Colour-selection strategy to apply: "auto" | "palette" | "custom".
    color_selection: str = AUTO
    # Capability hints (informational for now; drive degradation later).
    supports_custom_colors: bool = False
    supports_layers: bool = False
    supports_mspaint_mode: bool = False
    # Drawing defaults applied when the target is selected.
    drawing_settings: Dict[str, Any] = field(default_factory=dict)
    drawing_options: Dict[str, bool] = field(default_factory=dict)
    skip_first_color: bool = False
    # Optional fixed palette [(r, g, b), ...] when the app's colours are known.
    palette: Optional[List[Sequence[int]]] = None
    # Locator specs used for auto-detection (see ``pyaint.locators``).
    detection: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    # Schema version (for forward compatibility).
    schema_version: int = CURRENT_RECIPE_SCHEMA
    # Hidden recipes are infrastructure (bases) and are not shown in the UI.
    hidden: bool = False
    # Optional parent recipe id; the registry deep-merges parent then child.
    extends: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialization / validation
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Recipe":
        if not data.get("id"):
            raise ValueError("recipe is missing an 'id'")

        requested = data.get("tools") or _MINIMUM_TOOLS
        tools = tuple(t for t in requested if t in TOOL_KEYS) or _MINIMUM_TOOLS

        color_selection = data.get("color_selection", AUTO)
        if color_selection not in VALID_COLOR_SELECTION:
            color_selection = AUTO

        palette = data.get("palette")
        palette = [list(c) for c in palette] if palette else None

        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            description=str(data.get("description", "")),
            tools=tools,
            color_selection=color_selection,
            supports_custom_colors=bool(data.get("supports_custom_colors", False)),
            supports_layers=bool(data.get("supports_layers", False)),
            supports_mspaint_mode=bool(data.get("supports_mspaint_mode", False)),
            drawing_settings=dict(data.get("drawing_settings") or {}),
            drawing_options=dict(data.get("drawing_options") or {}),
            skip_first_color=bool(data.get("skip_first_color", False)),
            palette=palette,
            detection=copy.deepcopy(dict(data.get("detection") or {})),
            notes=str(data.get("notes", "")),
            schema_version=int(data.get("schema_version", CURRENT_RECIPE_SCHEMA)),
            hidden=bool(data.get("hidden", False)),
            extends=data.get("extends"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tools": list(self.tools),
            "color_selection": self.color_selection,
            "supports_custom_colors": self.supports_custom_colors,
            "supports_layers": self.supports_layers,
            "supports_mspaint_mode": self.supports_mspaint_mode,
            "drawing_settings": dict(self.drawing_settings),
            "drawing_options": dict(self.drawing_options),
            "skip_first_color": self.skip_first_color,
            "palette": [list(c) for c in self.palette] if self.palette else None,
            "detection": copy.deepcopy(self.detection),
            "notes": self.notes,
            "schema_version": self.schema_version,
            "hidden": self.hidden,
            "extends": self.extends,
        }


# ---------------------------------------------------------------------------
# Applying a recipe's defaults
# ---------------------------------------------------------------------------
def merge_drawing_settings(
    current: Sequence[float], updates: Mapping[str, Any]
) -> List[float]:
    """Return ``current`` with only the recipe-provided settings overlaid."""
    merged = list(current)
    if not updates:
        return merged
    if len(merged) > 0:
        merged[0] = updates.get("delay", merged[0])
    if len(merged) > 1:
        merged[1] = updates.get("pixel_size", merged[1])
    if len(merged) > 2:
        merged[2] = updates.get("precision", merged[2])
    if len(merged) > 3:
        merged[3] = updates.get("jump_delay", merged[3])
    return merged


def merge_drawing_options(
    flags: int,
    updates: Mapping[str, bool],
    ignore_white_bit: int,
    use_custom_bit: int,
) -> int:
    """Apply ``ignore_white_pixels`` / ``use_custom_colors`` to a flag bitmask."""
    if "ignore_white_pixels" in updates:
        if updates["ignore_white_pixels"]:
            flags |= ignore_white_bit
        else:
            flags &= ~ignore_white_bit
    if "use_custom_colors" in updates:
        if updates["use_custom_colors"]:
            flags |= use_custom_bit
        else:
            flags &= ~use_custom_bit
    return flags


def disabled_tools(recipe: "Recipe") -> Tuple[str, ...]:
    """Tools that should be switched off because the recipe does not use them."""
    return tuple(
        tool
        for tool in ("New Layer", "Color Button", "Color Button Okay")
        if tool not in recipe.tools
    )


def apply_profile_defaults(profile: Any, recipe: "Recipe") -> None:
    """Apply the environment-side recipe defaults to a ``Profile`` in place."""
    profile.color_selection = recipe.color_selection
    for tool in disabled_tools(recipe):
        profile[tool]["enabled"] = False
    if not recipe.supports_mspaint_mode:
        profile.mspaint_mode["enabled"] = False


# skribbl.io's fixed 2x13 palette (top row then bottom row), sampled from a
# real screenshot. Used only to *locate* the palette grid; the drawing colours
# are still sampled from the screen.
SKRIBBL_PALETTE = [
    (255, 255, 255), (193, 193, 193), (239, 19, 11), (255, 113, 0),
    (255, 228, 0), (0, 204, 0), (0, 255, 145), (0, 178, 255),
    (35, 31, 211), (163, 0, 186), (223, 105, 167), (255, 172, 142),
    (160, 82, 45),
    (0, 0, 0), (80, 80, 80), (116, 11, 7), (194, 56, 0),
    (232, 162, 0), (0, 70, 25), (0, 120, 93), (0, 86, 158),
    (14, 8, 101), (85, 0, 105), (135, 53, 84), (204, 119, 77),
    (99, 48, 13),
]


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base`` (dicts only)."""
    result: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Built-in recipes
# ---------------------------------------------------------------------------
_BUILTIN_DATA: Tuple[Dict[str, Any], ...] = (
    # Hidden base recipes (not shown in the UI; used via "extends").
    {
        "id": "desktop-base",
        "name": "Desktop app (base)",
        "hidden": True,
        "tools": [
            "Palette", "Canvas", "Custom Colors",
            "New Layer", "Color Button", "Color Button Okay",
        ],
        "color_selection": AUTO,
        "supports_custom_colors": True,
        "supports_layers": True,
        "supports_mspaint_mode": True,
    },
    {
        "id": "browser-base",
        "name": "Browser canvas (base)",
        "hidden": True,
        "tools": ["Palette", "Canvas"],
        "color_selection": "palette",
        "supports_custom_colors": False,
        "supports_layers": False,
        "supports_mspaint_mode": False,
        "drawing_options": {"ignore_white_pixels": True, "use_custom_colors": False},
    },
    {
        "id": "generic",
        "name": "Generic / other app",
        "description": "Full manual setup for any painting application.",
        "tools": list(TOOL_KEYS),
        "color_selection": AUTO,
        "supports_custom_colors": True,
        "supports_layers": True,
        "supports_mspaint_mode": True,
        "notes": "Teach every tool manually; enable custom colours only if the app has a colour dialog.",
    },
    {
        "id": "mspaint",
        "name": "MS Paint",
        "extends": "desktop-base",
        "description": "Classic sampled-palette workflow; optional double-click mode.",
        # Classic Paint has no layers; override the desktop base's tool list.
        "tools": ["Palette", "Canvas", "Custom Colors", "Color Button", "Color Button Okay"],
        "supports_layers": False,
        "drawing_settings": {
            "delay": 0.05,
            "pixel_size": 8,
            "precision": 0.9,
            "jump_delay": 0.5,
            "jump_threshold": 5,
        },
        "drawing_options": {"ignore_white_pixels": True, "use_custom_colors": False},
        # Best-effort: canvas is a white rectangle; palette is a swatch grid.
        # Needs a real-app screenshot to tune (see HANDOFF).
        "detection": {
            "canvas": {"type": "white_rect"},
            "palette": {"type": "color_grid"},
        },
        "notes": "Sampled palette. Enable MSPaint Mode if the app needs double-clicks to pick colours.",
    },
    {
        "id": "gimp",
        "name": "GIMP",
        "extends": "desktop-base",
        "description": "Layer-based editor using its colour dialog.",
        "color_selection": "custom",
        "drawing_settings": {
            "delay": 0.05,
            "pixel_size": 6,
            "precision": 0.95,
            "jump_delay": 0.5,
            "jump_threshold": 5,
        },
        "drawing_options": {"ignore_white_pixels": True, "use_custom_colors": False},
        "notes": "Uses the colour dialog. Run calibration or rely on RGB keyboard entry.",
    },
    {
        "id": "skribbl",
        "name": "skribbl.io",
        "extends": "browser-base",
        "description": "Browser drawing game with a fixed on-screen palette.",
        "drawing_settings": {
            "delay": 0.03,
            "pixel_size": 8,
            "precision": 0.9,
            "jump_delay": 0.2,
            "jump_threshold": 5,
        },
        "skip_first_color": False,
        "palette": None,
        "detection": {
            "canvas": [
                {"type": "white_rect", "aspect": 1.3333, "aspect_tolerance": 0.2},
                {
                    "type": "color_rect",
                    "color": [0, 0, 0],
                    "tolerance": 40,
                    "aspect": 1.3333,
                    "aspect_tolerance": 0.2,
                },
            ],
            "palette": {
                "type": "color_signature",
                "colors": SKRIBBL_PALETTE,
                "tolerance": 25,
                "gap": 0,
                "min_colors": 5,
                "rows": 2,
                "cols": 13,
            },
        },
        "notes": "Teach only the palette grid and the canvas. Fast settings tuned for a short turn timer.",
    },
)


class RecipeRegistry:
    """A small in-memory registry of :class:`Recipe` objects."""

    def __init__(self, recipes: Sequence[Recipe] = ()) -> None:
        self._recipes: Dict[str, Recipe] = {}
        for recipe in recipes:
            self.register(recipe)

    def register(self, recipe: Recipe, replace: bool = False) -> None:
        if not replace and recipe.id in self._recipes:
            raise ValueError(f"recipe already registered: {recipe.id}")
        self._recipes[recipe.id] = recipe

    def add_from_dict(self, data: Mapping[str, Any], replace: bool = True) -> Recipe:
        """Build a recipe, resolving ``extends`` against already-registered ones."""
        parent_id = data.get("extends")
        parent = self._recipes.get(parent_id) if parent_id else None
        merged = copy.deepcopy(parent.to_dict()) if parent else {}
        merged = _deep_merge(merged, {k: v for k, v in data.items() if k != "extends"})
        # ``hidden`` and ``extends`` describe the child, not the parent, so do
        # not inherit them from a hidden base.
        merged["hidden"] = bool(data.get("hidden", False))
        if parent_id:
            merged["extends"] = parent_id
        recipe = Recipe.from_dict(merged)
        self.register(recipe, replace=replace)
        return recipe

    def get(self, recipe_id: str) -> Optional[Recipe]:
        return self._recipes.get(recipe_id)

    def require(self, recipe_id: str) -> Recipe:
        """Return the named recipe, falling back to the default."""
        return self.get(recipe_id) or self._recipes[DEFAULT_RECIPE_ID]

    def all(self, include_hidden: bool = False) -> List[Recipe]:
        recipes = list(self._recipes.values())
        if include_hidden:
            return recipes
        return [r for r in recipes if not r.hidden]

    def ids(self) -> List[str]:
        return list(self._recipes.keys())

    def load_dir(self, path: str) -> List[Recipe]:
        """Load/override recipes from ``*.json`` files in ``path``."""
        loaded: List[Recipe] = []
        for filepath in sorted(glob.glob(os.path.join(path, "*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                loaded.append(self.add_from_dict(data))
            except Exception:
                continue
        return loaded


def _build_builtins() -> "RecipeRegistry":
    registry = RecipeRegistry()
    for data in _BUILTIN_DATA:
        registry.add_from_dict(data)
    return registry


REGISTRY = _build_builtins()
BUILTIN_RECIPES: Tuple[Recipe, ...] = tuple(REGISTRY.all(include_hidden=True))


def list_recipes() -> List[Recipe]:
    return REGISTRY.all()


def get_recipe(recipe_id: str) -> Recipe:
    return REGISTRY.require(recipe_id)


def default_recipe_dirs() -> List[str]:
    """Directories scanned for user-supplied recipes."""
    return [paths.TARGETS_DIR, paths.USER_TARGETS_DIR]


def load_user_recipes(paths: Optional[Sequence[str]] = None) -> List[Recipe]:
    """Load (and let override built-ins) recipes from the targets directories.

    Scans ``<repo>/targets`` and ``~/.pyaint/targets`` by default. Invalid files
    are skipped. Returns the recipes that were loaded.
    """
    loaded: List[Recipe] = []
    for path in (paths if paths is not None else default_recipe_dirs()):
        if os.path.isdir(path):
            loaded.extend(REGISTRY.load_dir(path))
    return loaded
