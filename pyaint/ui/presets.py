"""Named SKETCH tuning presets.

A preset is a plain mapping of ``Bot`` attribute names to values. Applying one
is just ``setattr``, and the live settings can be matched back to a preset so
the UI can show which one (if any) is active. Keeping the data here means the
tuning can be unit-tested without building a window.

Presets are **immutable**: they ship with the app and are identical on every
machine. Any manual tweak makes the live settings stop matching, and the UI
reports that state as *Custom* (see :data:`CUSTOM_PRESET`) rather than saving a
modified preset under a built-in name.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pyaint import planner

#: Every bot attribute a SKETCH preset controls. This is also the set compared
#: when deciding whether the live settings still match a preset.
#:
#: ``sketch_join_turn`` is deliberately absent: it has no UI and is always the
#: planner default, so pinning it would only cause spurious drift.
SKETCH_PRESET_FIELDS = (
    "sketch_edge_source",
    "sketch_smoothing",
    "sketch_join_distance",
    "sketch_min_stroke",
    "sketch_epsilon",
    "sketch_hue_merge",
    "sketch_hue_threshold",
    "sketch_gradient_keep",
    "canny_auto",
    "canny_low",
    "canny_high",
    "canny_color_edges",
)

#: Canned looks, ordered from bold-and-simple to detailed-and-selective.
SKETCH_PRESETS = (
    {
        "key": "cartoon",
        "label": "Cartoon",
        "tagline": "Best for flat, cel-shaded art",
        "description": (
            "For illustrations, anime and flat-colour art with clear outlines. "
            "Keeps colour boundaries, smooths lines and bridges small gaps so "
            "the outlines read as one continuous ink drawing."
        ),
        "settings": {
            "sketch_edge_source": planner.EDGE_EDGEDRAWING,
            "sketch_smoothing": 2,
            "sketch_join_distance": 12.0,
            "sketch_min_stroke": 10,
            "sketch_epsilon": 1.5,
            "sketch_hue_merge": True,
            "sketch_hue_threshold": 10.0,
            "sketch_gradient_keep": 1.0,
            "canny_auto": True,
            "canny_low": 50,
            "canny_high": 150,
            "canny_color_edges": False,
        },
    },
    {
        "key": "realistic",
        "label": "Realistic",
        "tagline": "Best for photos and painterly art",
        "description": (
            "For photos and detailed, softly shaded images. Aggressive colour "
            "merging and weak-edge pruning drop soft shading, gradients and "
            "texture noise so the strong structural outlines stay."
        ),
        "settings": {
            "sketch_edge_source": planner.EDGE_EDGEDRAWING,
            "sketch_smoothing": 4,
            "sketch_join_distance": 7.0,
            "sketch_min_stroke": 5,
            "sketch_epsilon": 1.0,
            "sketch_hue_merge": True,
            "sketch_hue_threshold": 28.0,
            "sketch_gradient_keep": 0.6,
            "canny_auto": True,
            "canny_low": 50,
            "canny_high": 150,
            "canny_color_edges": True,
        },
    },
)

#: The manual state shown once an advanced knob no longer matches a preset.
#: Not a selectable option: it is a read-only description of the live values.
CUSTOM_PRESET = {
    "key": "custom",
    "label": "Custom",
    "tagline": "Custom — you've tuned the settings",
    "description": (
        "One or more advanced settings differ from the presets. Pick a preset "
        "to reset the line quality, or keep tuning under Advanced."
    ),
    "settings": {},
}

#: Selectable options for the preset control: the canned looks only.
SKETCH_PRESET_OPTIONS = tuple(
    (preset["key"], preset["label"]) for preset in SKETCH_PRESETS
)


def preset_by_key(key: str) -> Dict[str, Any]:
    """Return the preset with ``key`` (the ``Custom`` entry as a fallback)."""
    for preset in SKETCH_PRESETS:
        if preset["key"] == key:
            return preset
    return CUSTOM_PRESET


def _values_match(a: Any, b: Any) -> bool:
    # ``bool`` is a subclass of ``int``, so check it first to avoid True == 1.
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-6
    return a == b


def match_preset(values: Dict[str, Any]) -> Optional[str]:
    """Return the key of the preset whose settings equal ``values``, if any."""
    for preset in SKETCH_PRESETS:
        settings = preset["settings"]
        if all(
            field in values and _values_match(values[field], settings[field])
            for field in settings
        ):
            return preset["key"]
    return None
