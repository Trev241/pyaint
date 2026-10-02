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

import glob
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from pyaint_profile import AUTO, TOOL_KEYS, VALID_COLOR_SELECTION

DEFAULT_RECIPE_ID = "generic"

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
    notes: str = ""

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
            notes=str(data.get("notes", "")),
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
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Built-in recipes
# ---------------------------------------------------------------------------
_BUILTIN_DATA: Tuple[Dict[str, Any], ...] = (
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
        "description": "Classic sampled-palette workflow; optional double-click mode.",
        "tools": ["Palette", "Canvas", "Custom Colors", "Color Button", "Color Button Okay"],
        "color_selection": AUTO,
        "supports_custom_colors": True,
        "supports_layers": False,
        "supports_mspaint_mode": True,
        "drawing_settings": {
            "delay": 0.05,
            "pixel_size": 8,
            "precision": 0.9,
            "jump_delay": 0.5,
            "jump_threshold": 5,
        },
        "drawing_options": {"ignore_white_pixels": True, "use_custom_colors": False},
        "notes": "Sampled palette. Enable MSPaint Mode if the app needs double-clicks to pick colours.",
    },
    {
        "id": "gimp",
        "name": "GIMP",
        "description": "Layer-based editor using its colour dialog.",
        "tools": ["Palette", "Canvas", "Custom Colors", "New Layer", "Color Button", "Color Button Okay"],
        "color_selection": "custom",
        "supports_custom_colors": True,
        "supports_layers": True,
        "supports_mspaint_mode": False,
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
        "description": "Browser drawing game with a fixed on-screen palette.",
        "tools": ["Palette", "Canvas"],
        "color_selection": "palette",
        "supports_custom_colors": False,
        "supports_layers": False,
        "supports_mspaint_mode": False,
        "drawing_settings": {
            "delay": 0.03,
            "pixel_size": 8,
            "precision": 0.9,
            "jump_delay": 0.2,
            "jump_threshold": 5,
        },
        "drawing_options": {"ignore_white_pixels": True, "use_custom_colors": False},
        "skip_first_color": False,
        # Phase 2 will populate/verify the fixed palette via colour-signature
        # detection; until then the palette is sampled from the screen.
        "palette": None,
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

    def get(self, recipe_id: str) -> Optional[Recipe]:
        return self._recipes.get(recipe_id)

    def require(self, recipe_id: str) -> Recipe:
        """Return the named recipe, falling back to the default."""
        return self.get(recipe_id) or self._recipes[DEFAULT_RECIPE_ID]

    def all(self) -> List[Recipe]:
        return list(self._recipes.values())

    def ids(self) -> List[str]:
        return list(self._recipes.keys())

    def load_dir(self, path: str) -> List[Recipe]:
        """Load/override recipes from ``*.json`` files in ``path``."""
        loaded: List[Recipe] = []
        for filepath in sorted(glob.glob(os.path.join(path, "*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    recipe = Recipe.from_dict(json.load(handle))
            except Exception:
                continue
            self.register(recipe, replace=True)
            loaded.append(recipe)
        return loaded


BUILTIN_RECIPES: Tuple[Recipe, ...] = tuple(
    Recipe.from_dict(data) for data in _BUILTIN_DATA
)

REGISTRY = RecipeRegistry(BUILTIN_RECIPES)


def list_recipes() -> List[Recipe]:
    return REGISTRY.all()


def get_recipe(recipe_id: str) -> Recipe:
    return REGISTRY.require(recipe_id)
