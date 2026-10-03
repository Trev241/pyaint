"""Characterization tests for time formatting and drawing-time estimation."""

import utils
from bot import Bot

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def test_format_time_units():
    bot = Bot()
    assert bot._format_time(30) == "30s"
    assert bot._format_time(90) == "1:30"
    assert bot._format_time(3600) == "1:00h"


def test_estimate_drawing_time_seconds_is_positive_and_scales():
    bot = Bot()
    cmap = {RED: [((0, 0), (10, 0))], BLUE: [((0, 10), (10, 10)), ((0, 20), (10, 20))]}
    estimate = bot._estimate_drawing_time_seconds(cmap)
    assert estimate > 0


def test_estimate_drawing_time_returns_string():
    bot = Bot()
    cmap = {RED: [((0, 0), (10, 0))]}
    assert bot.estimate_drawing_time(cmap).startswith("~")


# ---------------------------------------------------------------------------
# Pure helpers in utils
# ---------------------------------------------------------------------------
def test_utils_format_duration():
    assert utils.format_duration(30) == "30s"
    assert utils.format_duration(90) == "1:30"
    assert utils.format_duration(3661) == "1:01h"


def test_utils_format_estimate():
    assert utils.format_estimate(5) == "~5.0 seconds"
    assert utils.format_estimate(30).startswith("~30")
    assert "minutes" in utils.format_estimate(90)
    assert "hours" in utils.format_estimate(7200)


def test_utils_estimate_drawing_seconds_adds_jump_delay():
    cmap = {RED: [((0, 0), (10, 0)), ((500, 500), (510, 500))]}
    base = utils.estimate_drawing_seconds(cmap, 0.1, 0.0, 5)
    with_jump = utils.estimate_drawing_seconds(cmap, 0.1, 0.5, 5)
    assert with_jump > base
