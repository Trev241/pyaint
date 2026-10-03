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
    return Bot().painter, fake


def names(fake):
    return [c[0] for c in fake.calls]


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------
def test_capabilities_default_bare_bot():
    caps = Bot().painter.capabilities
    assert caps.palette is False
    assert caps.custom_colors is False
    assert caps.new_layer is False
    assert caps.mspaint_double_click is False


def test_capabilities_reflect_profile():
    bot = Bot()
    bot.init_palette(colors_pos={(1, 2, 3): (0, 0)})
    bot.profile["New Layer"].update({"enabled": True, "coords": (5, 5)})
    bot.profile.mspaint_mode["enabled"] = True
    caps = bot.painter.capabilities
    assert caps.palette is True
    assert caps.new_layer is True
    assert caps.mspaint_double_click is True


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


def test_chain_resolves_none_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
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


def test_click_swatch_mspaint_double_clicks(monkeypatch):
    painter, fake = make_painter(monkeypatch)
    painter.bot.profile.mspaint_mode.update({"enabled": True, "delay": 0.2})
    painter.click_swatch(1, 2)
    assert names(fake).count("click") == 2
