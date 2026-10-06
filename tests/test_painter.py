"""Characterization tests for the ``ScreenPainter`` seam (Phase 0).

These run headless by swapping the module's ``pyautogui`` for a fake that
records calls. They pin the behaviour that used to live inline in ``Bot`` so
later driver work can move safely.
"""

from pyaint import painter as painter_mod
from pyaint.bot import Bot


class FakePyAutoGUI:
    """Minimal recorder stand-in for ``pyautogui``."""

    PAUSE = 0.0
    MINIMUM_DURATION = 0.0

    def __init__(self):
        self.calls = []

    def _record(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return call

    def __getattr__(self, name):
        # Any pyautogui function we don't explicitly define is still recorded.
        return self._record(name)


def make_painter(monkeypatch):
    fake = FakePyAutoGUI()
    monkeypatch.setattr(painter_mod, "pyautogui", fake)
    monkeypatch.setattr(painter_mod.time, "sleep", lambda *_: None)
    painter = Bot().painter
    # Record drag moves through the same recorder and keep tests off the real
    # Windows mouse_event() / GetAsyncKeyState() paths.
    monkeypatch.setattr(painter, "_drag_move", fake.moveTo)
    monkeypatch.setattr(painter, "_left_is_down", lambda: True)
    return painter, fake


def names(fake):
    return [c[0] for c in fake.calls]


# ---------------------------------------------------------------------------
# Colour selection
# ---------------------------------------------------------------------------
def test_chain_selects_palette_and_clicks(monkeypatch):
    bot = Bot()
    bot.init_palette(colors_pos={(1, 2, 3): (7, 8)})
    clicked = {}
    monkeypatch.setattr(
        bot.painter, "click_swatch", lambda x, y: clicked.update(x=x, y=y)
    )
    assert bot.painter.select_color((1, 2, 3)) == "palette"
    assert clicked == {"x": 7, "y": 8}


def test_chain_resolves_none_when_unconfigured():
    bot = Bot()
    assert bot.painter.resolve_color_source((9, 9, 9)) == "none"


# ---------------------------------------------------------------------------
# Modifier clicks
# ---------------------------------------------------------------------------
def test_click_with_modifiers_presses_then_releases_in_reverse(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter._click_with_modifiers((10, 20), {"ctrl": True, "shift": True}, "T")
    events = names(fake)
    assert events[:2] == ["keyDown", "keyDown"]
    assert events[2:4] == ["mouseDown", "mouseUp"]
    keyups = [c[1][0] for c in fake.calls if c[0] == "keyUp"]
    assert keyups.index("shift") < keyups.index("ctrl")


def test_new_layer_skips_when_disabled(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.new_layer()
    assert fake.calls == []


def test_color_button_okay_clicks_when_enabled(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.bot.profile["Color Button Okay"].update(
        {"enabled": True, "coords": (3, 4)}
    )
    painter.color_button_okay()
    assert "mouseDown" in names(fake)


# ---------------------------------------------------------------------------
# Stroke execution
# ---------------------------------------------------------------------------
def test_execute_stroke_segments_and_clears_replay(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.bot.draw_state["was_paused"] = True
    painter.execute_stroke((0, 0), (100, 0), 1.0)
    events = names(fake)
    assert events[0] == "moveTo"
    assert "mouseDown" in events
    assert events[-1] == "mouseUp"
    # initial moveTo + one per segment (100px -> 10 segments)
    assert events.count("moveTo") == 11
    assert painter.bot.draw_state["was_paused"] is False


def test_execute_stroke_short_uses_drag_not_segments(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.execute_stroke((0, 0), (0, 0), 1.0)
    events = names(fake)
    assert "dragTo" in events
    assert "mouseDown" not in events


def test_execute_path_presses_once_and_visits_every_vertex(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.execute_path(
        [(0, 0), (100, 0), (100, 100)], speed=1000.0, frame_interval=1 / 60
    )
    events = names(fake)
    assert events.count("mouseDown") == 1
    assert events.count("mouseUp") == 1
    assert events[0] == "moveTo"
    coords = {c[1][:2] for c in fake.calls if c[0] == "moveTo"}
    assert {(0, 0), (100, 0), (100, 100)}.issubset(coords)


def test_execute_path_single_point_taps_in_place(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.execute_path([(5, 5)])
    events = names(fake)
    assert events.count("mouseDown") == 1
    assert events.count("mouseUp") == 1
    assert events.count("moveTo") == 1


def test_execute_path_uses_drag_moves_while_button_held(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    drags = []
    monkeypatch.setattr(painter, "_drag_move", lambda x, y: drags.append((x, y)))
    painter.execute_path([(0, 0), (100, 0)], speed=1000.0, frame_interval=1 / 60)
    assert (100, 0) in drags  # the drag went through _drag_move
    # plain moveTo is used only once, to park the cursor before mouseDown
    assert names(fake).count("moveTo") == 1


def test_press_left_retries_until_button_is_confirmed(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    states = iter([False, False, True])
    monkeypatch.setattr(painter, "_left_is_down", lambda: next(states))
    painter.press_left(attempts=5)
    assert names(fake).count("mouseDown") == 3


def test_click_swatch_mspaint_double_clicks(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.bot.profile.mspaint_mode.update({"enabled": True, "delay": 0.2})
    painter.click_swatch(1, 2)
    assert names(fake).count("click") == 2
