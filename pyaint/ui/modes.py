"""Mode families and labels — one source of truth for the UI.

Exactly one mode is active at a time. The two families only *describe* how the
modes produce the image; they are not separate choices, and the rail renders
them as radio items so that is unambiguous.

- **Runs** paints colour in scan-line runs (`LAYERED`, `SLOTTED`).
- **Contours** traces lines (`OUTLINE` region boundaries, `SKETCH` gradient
  edges). The name is technique-based so `OUTLINE` can grow an optional fill
  stage later without contradicting the label.
"""

from __future__ import annotations

from typing import Dict, Tuple

from pyaint import planner

#: (family label, ((mode label, mode constant), ...))
MODE_FAMILIES: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("Runs", (("Layered", planner.LAYERED), ("Slotted", planner.SLOTTED))),
    ("Contours", (("Outline", planner.OUTLINE), ("Edge tracing", planner.SKETCH))),
)

#: mode constant -> display label
MODE_LABELS: Dict[str, str] = {
    mode: label for _family, items in MODE_FAMILIES for label, mode in items
}


def family_of(mode: str) -> str:
    """Return the family label a mode belongs to ('' when unknown)."""
    for family, items in MODE_FAMILIES:
        if any(mode == item_mode for _label, item_mode in items):
            return family
    return ""


def modes() -> Tuple[str, ...]:
    """All mode constants, in display order."""
    return tuple(mode for _family, items in MODE_FAMILIES for _label, mode in items)
