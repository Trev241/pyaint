"""Mode families and labels — one source of truth for the UI.

Exactly one mode is active at a time. The two families only *describe* how the
modes produce the image; they are not separate choices, and the rail renders
them as radio items so that is unambiguous.

- **Runs** paints colour in scan-line runs (`LAYERED`, `SLOTTED`).
- **Contours** traces lines (`SKETCH` gradient edges).

`OUTLINE` is retired from the rail (Edge tracing is the shipped contour mode)
but the planner, its settings and its tests are kept. It still has a label and
a family so old configs and internal callers do not lose their meaning.
"""

from __future__ import annotations

from typing import Dict, Tuple

from pyaint import planner

#: The mode a fresh profile starts in.
DEFAULT_MODE = planner.SKETCH

#: (family label, ((mode label, mode constant), ...)) for the visible rail.
MODE_FAMILIES: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("Runs", (("Layered", planner.LAYERED), ("Slotted", planner.SLOTTED))),
    ("Contours", (("Edge tracing", planner.SKETCH),)),
)

#: Every mode, including the retired Outline, for labels/family lookups.
ALL_MODE_FAMILIES: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("Runs", (("Layered", planner.LAYERED), ("Slotted", planner.SLOTTED))),
    ("Contours", (("Outline", planner.OUTLINE), ("Edge tracing", planner.SKETCH))),
)

#: mode constant -> display label (includes retired modes)
MODE_LABELS: Dict[str, str] = {
    mode: label for _family, items in ALL_MODE_FAMILIES for label, mode in items
}


def family_of(mode: str) -> str:
    """Return the family label a mode belongs to ('' when unknown)."""
    for family, items in ALL_MODE_FAMILIES:
        if any(mode == item_mode for _label, item_mode in items):
            return family
    return ""


def modes() -> Tuple[str, ...]:
    """Every mode constant, including retired ones, in display order."""
    return tuple(mode for _family, items in ALL_MODE_FAMILIES for _label, mode in items)


def visible_modes() -> Tuple[str, ...]:
    """Mode constants the UI offers."""
    return tuple(mode for _family, items in MODE_FAMILIES for _label, mode in items)
