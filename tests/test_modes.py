"""Unit tests for the pure mode-family data (no Qt needed)."""

from pyaint import planner
from pyaint.ui import modes


def test_every_mode_has_one_family_and_label():
    assert modes.modes() == (
        planner.LAYERED,
        planner.SLOTTED,
        planner.OUTLINE,
        planner.SKETCH,
    )
    for mode in modes.modes():
        assert modes.MODE_LABELS[mode]
        assert modes.family_of(mode) in ("Runs", "Contours")
    assert modes.family_of(planner.LAYERED) == "Runs"
    assert modes.family_of(planner.SKETCH) == "Contours"


def test_outline_and_sketch_share_the_contours_family():
    # The family name is technique-based, so Outline can grow a fill stage.
    assert modes.family_of(planner.OUTLINE) == modes.family_of(planner.SKETCH)


def test_unknown_mode_is_safe():
    assert modes.family_of("nope") == ""
