"""Qualitative band labels for numeric settings.

Each control maps a value to a short descriptive word so a number reads at a
glance (``12 px · Balanced``). The descriptor is a pure function of the value,
so nothing extra is stored and nothing can desync with ``config.json``.

Bands are ordered and **upper-bound inclusive**; the final entry is the
catch-all. A control's value is always displayed as ``<number> <unit> ·
<label>`` so settings stay reproducible from a screenshot.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

#: control key -> (unit, ((upper_bound_inclusive | None, label), ...))
CONTROL_BANDS: Dict[str, Tuple[str, Tuple[Tuple[Optional[float], str], ...]]] = {
    "detail": ("px", ((8, "Fine"), (17, "Balanced"), (None, "Coarse"))),
    "time_per_stroke": ("s", ((0.05, "Quick"), (0.2, "Steady"), (None, "Slow"))),
    "pause_after_big_moves": (
        "s",
        ((0.05, "Short"), (0.5, "Steady"), (None, "Long")),
    ),
    "pause_between_strokes": (
        "s",
        ((0.02, "Short"), (0.15, "Steady"), (None, "Long")),
    ),
    "hue_difference": ("\u00b0", ((10, "Tight"), (30, "Balanced"), (None, "Loose"))),
    "canny_low": ("", ((80, "Low"), (180, "Medium"), (None, "High"))),
    "canny_high": ("", ((100, "Low"), (200, "Medium"), (None, "High"))),
    "drawing_speed": (
        "px/s",
        ((800, "Relaxed"), (2500, "Steady"), (None, "Brisk")),
    ),
    "skip_soft_shading": ("", ((0, "Off"), (5, "Light"), (None, "Strong"))),
    # Underlying value is the *keep* percentage, so the bands descend in
    # meaning: 100 = keep everything = Off.
    "skip_faint_edges": ("%", ((59, "Strong"), (99, "Light"), (None, "Off"))),
    "join_distance": ("px", ((4, "Close"), (10, "Balanced"), (None, "Loose"))),
    "smoothing": ("", ((0, "Off"), (2, "Light"), (None, "Strong"))),
    "event_interval": ("ms", ((8, "Fast"), (25, "Balanced"), (None, "Relaxed"))),
    "min_stroke": ("px", ((5, "Fine"), (20, "Balanced"), (None, "Coarse"))),
    "simplify": ("px", ((1.0, "Fine"), (3.0, "Balanced"), (None, "Coarse"))),
}


def unit(control: str) -> str:
    """Return the unit for ``control`` ('' when unknown or unitless)."""
    entry = CONTROL_BANDS.get(control)
    return entry[0] if entry else ""


def describe(control: str, value: float) -> str:
    """Return the band label for ``value`` ('' for an unknown control)."""
    entry = CONTROL_BANDS.get(control)
    if entry is None:
        return ""
    table = entry[1]
    for upper, label in table:
        if upper is None or value <= upper:
            return label
    return table[-1][1]


def band_index(control: str, value: float) -> int:
    """0-based index of the band ``value`` sits in (for a pip meter)."""
    entry = CONTROL_BANDS.get(control)
    if entry is None:
        return 0
    table = entry[1]
    for index, (upper, _label) in enumerate(table):
        if upper is None or value <= upper:
            return index
    return len(table) - 1


def band_count(control: str) -> int:
    """How many bands ``control`` has (0 when unknown)."""
    entry = CONTROL_BANDS.get(control)
    return len(entry[1]) if entry else 0
