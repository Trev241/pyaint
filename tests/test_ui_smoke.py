"""Headless smoke test for the PySide6 UI.

Runs with the ``offscreen`` Qt platform so it needs no display. It only checks
that the window builds and wires up to the bot; the drawing/automation paths
are covered by the other suites.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from pyaint.bot import Bot  # noqa: E402
from pyaint.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


def test_main_window_builds(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        assert window.windowTitle() == "Pyaint"
        # The shared profile must be the same object the bot sees.
        assert window.bot.profile is window.profile
        # Progress callback is wired so Bot can report from a worker thread.
        assert bot.progress_callback is not None
    finally:
        window.close()


def test_main_window_has_tool_controls(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        assert len(window._tool_controls) == 3  # New Layer / Color Button / Okay
    finally:
        window.close()


def test_progress_overlay_updates(app):
    from pyaint.ui.overlay import ProgressOverlay

    overlay = ProgressOverlay()
    try:
        overlay.show_overlay("Drawing…", "p")
        overlay.update_progress(5, 10, 30.0)
        assert overlay._bar.value() == 50
        assert "5/10" in overlay._label.text()
        assert overlay._hint.text().startswith("ESC stop")
    finally:
        overlay.close()


def test_tool_controls_mutate_profile(app):
    from pyaint.ui.widgets import ToolControls

    entry = {
        "status": True,
        "enabled": False,
        "modifiers": {"ctrl": False, "alt": False, "shift": False},
        "delay": 0.1,
    }
    control = ToolControls("Color Button", lambda: entry, supports_delay=True)
    try:
        control._enable.setChecked(True)
        control._mods["shift"].setChecked(True)
        control._delay.setValue(250)
        assert entry["enabled"] is True
        assert entry["modifiers"]["shift"] is True
        assert entry["delay"] == 0.25
    finally:
        control.close()


def test_countdown_banner_counts_down_and_captures(app):
    from pyaint.ui.countdown import CountdownBanner

    banner = CountdownBanner()
    captured = []
    banner.captured.connect(lambda: captured.append(True))
    try:
        banner.start(seconds=2)
        assert banner._timer.isActive()  # regression: the timer must actually run
        banner._tick()  # 2 -> 1
        assert banner._title.text().endswith("1s…")
        banner._tick()  # 1 -> captured
        assert captured == [True]
        assert not banner._timer.isActive()
    finally:
        banner.close()


def test_countdown_banner_cancel_emits(app):
    from pyaint.ui.countdown import CountdownBanner

    banner = CountdownBanner()
    cancelled = []
    banner.cancelled.connect(lambda: cancelled.append(True))
    try:
        banner.start(seconds=3)
        banner._cancel()
        assert cancelled == [True]
    finally:
        banner.close()


def test_readiness_strip_states(app):
    from pyaint.ui.widgets import ReadinessStrip

    strip = ReadinessStrip()
    try:
        strip.update_steps("skribbl", environment_ready=True, image_ready=False)
        assert strip._chips[0].property("done") is True
        assert strip._chips[1].property("done") is True
        assert strip._chips[2].property("done") is False
        assert strip._chips[3].property("done") is False
    finally:
        strip.close()


def test_detection_checklist(app):
    from pyaint.locators import Detection
    from pyaint.ui.main_window import MainWindow

    good = Detection(canvas=(1, 2, 3, 4), palette=(5, 6, 7, 8), palette_rows=2, palette_cols=3)
    text = MainWindow._detection_checklist(good)
    assert "✓ Canvas" in text and "✓ Palette 2×3" in text

    empty = MainWindow._detection_checklist(Detection())
    assert "✗ Canvas" in empty and "✗ Palette" in empty


def test_theme_resolution_and_stylesheet():
    from pyaint.ui import theme

    assert theme.resolve_tokens("dark") is theme.DARK
    assert theme.resolve_tokens("light") is theme.LIGHT
    # Unknown modes fall back to auto (a real token set).
    assert theme.resolve_tokens("nonsense") in (theme.DARK, theme.LIGHT)
    assert theme.stylesheet(theme.DARK) != theme.stylesheet(theme.LIGHT)
    assert theme.DARK["bg"] != theme.LIGHT["bg"]


def test_detection_lives_in_its_own_tab(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from PIL import Image

    from pyaint.locators import Detection

    bot = Bot()
    window = MainWindow(bot)
    try:
        image = Image.new("RGB", (80, 60), (10, 20, 30))
        window._present_detection(image, Detection(canvas=(5, 5, 50, 40)))
        # A second, named tab is added and selected; the image tab is untouched.
        assert window._tabs.count() == 2
        assert window._tabs.tabText(1) == "Detection"
        assert window._tabs.currentWidget() is window._detection_view
        assert window._apply_detection_btn.isEnabled()

        window._cancel_detection()
        assert window._tabs.currentWidget() is window._image_view

        # A failed detection keeps the tab but disables Apply.
        window._present_detection(image, Detection())
        assert not window._apply_detection_btn.isEnabled()
    finally:
        window.close()


def test_progress_signal_updates_bar(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        window.signals.progress.emit(5, 10, 1.0)
        assert window._progress.value() == 50
    finally:
        window.close()
