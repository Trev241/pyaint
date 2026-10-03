"""Characterization tests for calibration helpers on ``Bot``.

These pin the colour-lookup and persistence behaviour before the methods are
moved out of ``bot.py`` into a mixin.
"""

from pyaint.bot import Bot

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def test_get_calibrated_position_exact_match_within_tolerance():
    bot = Bot()
    bot.color_calibration_map = {RED: (5, 6)}
    assert bot.get_calibrated_color_position((250, 0, 0)) == (5, 6)


def test_get_calibrated_position_none_when_empty():
    bot = Bot()
    assert bot.get_calibrated_color_position(RED) is None


def test_get_calibrated_position_interpolates_for_far_colour():
    bot = Bot()
    bot.color_calibration_map = {RED: (10, 10), BLUE: (20, 20)}
    pos = bot.get_calibrated_color_position((0, 255, 0), tolerance=0)
    assert pos is not None
    assert isinstance(pos[0], int) and isinstance(pos[1], int)


def test_save_and_load_color_calibration_round_trip(tmp_path):
    bot = Bot()
    bot.color_calibration_map = {RED: (5, 6), BLUE: (7, 8)}
    path = tmp_path / "color_calibration.json"
    assert bot.save_color_calibration(str(path)) is True

    fresh = Bot()
    assert fresh.load_color_calibration(str(path)) is True
    assert fresh.color_calibration_map == {RED: (5, 6), BLUE: (7, 8)}


def test_load_color_calibration_missing_file(tmp_path):
    assert Bot().load_color_calibration(str(tmp_path / "nope.json")) is False


def test_save_color_calibration_without_map_is_false(tmp_path):
    bot = Bot()
    assert bot.save_color_calibration(str(tmp_path / "x.json")) is False
