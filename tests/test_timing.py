"""Characterization tests for time formatting and drawing-time estimation."""

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
