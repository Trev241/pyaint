"""Characterization tests for ``Bot.draw`` / ``Bot.test_draw``.

These exercise the drawing loop headlessly by replacing ``Bot.painter`` with a
recording fake and disabling the Tk progress overlay. They pin the ordering and
the pause/skip/resume behaviour so the engine can be refactored safely.
"""

import time

from pyaint.bot import Bot

RED = (255, 0, 0)
BLUE = (0, 0, 255)

POSITIONS = {RED: (10, 10), BLUE: (20, 10)}


class FakePainter:
    """Records every app action instead of touching the screen."""

    def __init__(self):
        self.calls = []

    def _rec(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    # Actions used by Bot.draw / Bot.test_draw.
    def new_layer(self):
        self._rec("new_layer")

    def color_button(self):
        self._rec("color_button")

    def color_button_okay(self):
        self._rec("color_button_okay")

    def select_color(self, target, force_custom=False):
        self._rec("select_color", target, force_custom)
        return "palette"

    def execute_stroke(self, start, end, delay):
        self._rec("execute_stroke", start, end, delay)

    def execute_test_stroke(self, start, end):
        self._rec("execute_test_stroke", start, end)

    def names(self):
        return [c[0] for c in self.calls]

    def select_calls(self):
        return [c for c in self.calls if c[0] == "select_color"]


def make_bot(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no color_calibration.json
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    bot = Bot()
    bot.progress_overlay_enabled = False  # avoid Tk
    bot.init_canvas((0, 0, 100, 100))
    bot.init_palette(colors_pos=dict(POSITIONS))
    fake = FakePainter()
    bot.painter = fake
    return bot, fake


def cmap():
    return {RED: [((0, 0), (9, 0))], BLUE: [((0, 10), (9, 10))]}


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------
def test_draw_selects_each_colour_and_draws_each_stroke(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    assert bot.draw(cmap()) == "success"
    assert fake.names().count("select_color") == 2
    assert fake.names().count("execute_stroke") == 2
    assert bot.drawing is False


def test_draw_skip_first_color(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    bot.skip_first_color = True
    bot.draw(cmap())
    targets = [c[1][0] for c in fake.select_calls()]
    assert RED not in targets and BLUE in targets


def test_draw_resumes_skipping_completed_colours(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    bot.draw_state["color_idx"] = 1
    bot.draw(cmap())
    targets = [c[1][0] for c in fake.select_calls()]
    assert RED not in targets and BLUE in targets


def test_draw_calls_new_layer_and_color_button_when_enabled(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    bot.profile["New Layer"].update({"enabled": True, "coords": (5, 5)})
    bot.profile["Color Button"].update({"enabled": True, "coords": (6, 6)})
    bot.draw(cmap())
    assert "new_layer" in fake.names()
    assert "color_button" in fake.names()


def test_draw_forces_custom_colours_when_okay_enabled(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    bot.profile["Color Button Okay"].update({"enabled": True, "coords": (7, 7)})
    bot.draw(cmap())
    assert all(call[1][1] is True for call in fake.select_calls())
    assert "color_button_okay" in fake.names()


class TerminatingPainter(FakePainter):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def execute_stroke(self, start, end, delay):
        super().execute_stroke(start, end, delay)
        self.bot.terminate = True


def test_draw_returns_terminated_when_stopped(monkeypatch, tmp_path):
    bot, _ = make_bot(monkeypatch, tmp_path)
    bot.painter = TerminatingPainter(bot)
    assert bot.draw(cmap()) == "terminated"
    assert bot.drawing is False


# ---------------------------------------------------------------------------
# test_draw()
# ---------------------------------------------------------------------------
def test_test_draw_limits_number_of_lines(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    assert bot.test_draw(cmap(), max_lines=1) == "success"
    assert fake.names().count("execute_test_stroke") == 1


def test_test_draw_selects_colours(monkeypatch, tmp_path):
    bot, fake = make_bot(monkeypatch, tmp_path)
    bot.test_draw(cmap(), max_lines=5)
    assert len(fake.select_calls()) >= 1
