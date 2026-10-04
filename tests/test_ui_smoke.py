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
    from PySide6.QtCore import Qt

    from pyaint.ui.overlay import ProgressOverlay

    overlay = ProgressOverlay()
    try:
        # Click-through: the bot owns the mouse, so the overlay must never
        # intercept clicks meant for the target app (e.g. the palette).
        assert overlay.windowFlags() & Qt.WindowTransparentForInput
        overlay.show_overlay("Drawing…", "p")
        overlay.update_progress(5, 10, 30.0)
        assert overlay._bar.value() == 50
        assert "5/10" in overlay._label.text()
        assert overlay._hint.text().startswith("ESC stop")
        overlay.set_paused(True)
        assert "PAUSED" in overlay._hint.text()
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


def test_detection_uses_review_overlay(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from PIL import Image

    from pyaint.locators import Detection

    bot = Bot()
    window = MainWindow(bot)
    try:
        # Detection no longer opens a tab; it stays in the single image view.
        assert window._tabs.count() == 1

        image = Image.new("RGB", (80, 60), (10, 20, 30))
        window._present_detection(image, Detection(canvas=(5, 5, 50, 40)))
        assert window._detection_overlay.isVisible()
        assert window._detection_overlay._confirm_btn.isEnabled()
        assert window._detection_result is not None

        # A failed detection shows the same overlay but disables confirm.
        window._present_detection(image, Detection())
        assert window._detection_overlay.isVisible()
        assert not window._detection_overlay._confirm_btn.isEnabled()
        assert window._detection_result is None

        window._dismiss_detection()
        assert not window._detection_overlay.isVisible()
    finally:
        window.close()


def test_pick_points_minimizes_instead_of_hiding_parent(app, monkeypatch):
    """Hiding a dialog ends its exec() loop, which broke manual teaching."""
    from PySide6.QtWidgets import QDialog, QWidget

    import pyaint.ui.capture as capture

    parent = QWidget()
    parent.show()
    seen = {}

    class FakeOverlay:
        def __init__(self, count, prompt):
            self.points = [(1, 1), (2, 2)]
            self.image = None

        def exec(self):
            seen["minimized_during"] = parent.isMinimized()
            return QDialog.Accepted

    monkeypatch.setattr(capture, "_PickOverlay", FakeOverlay)
    try:
        result = capture.pick_points(parent, 2, "prompt")
        assert seen["minimized_during"] is True
        assert not parent.isMinimized()
        assert result is not None and len(result.points) == 2
    finally:
        parent.close()


def test_progress_signal_updates_bar(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        window.signals.progress.emit(5, 10, 1.0)
        assert window._progress.value() == 50
    finally:
        window.close()


def test_notice_banner_severity_and_action(app):
    from pyaint.ui.widgets import NoticeBanner

    banner = NoticeBanner()
    fired = []
    try:
        banner.show_notice("Something missing", "warning", "Fix", lambda: fired.append(True))
        assert banner.property("severity") == "warning"
        assert not banner._action.isHidden()
        banner._action.click()
        assert fired == [True]

        banner.show_notice("It broke", "error")
        assert banner.property("severity") == "error"
        assert banner._action.isHidden()

        banner.clear()
        assert banner.isHidden()
    finally:
        banner.close()


def test_target_switcher_remembers_environment(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        # Deterministic environment: colour-position palette (no screenshot).
        window._config_path = str(tmp_path / "config.json")
        window.profile["Palette"]["box"] = None
        window.profile["Palette"]["color_coords"] = {"(255, 0, 0)": [1, 1], "(0, 255, 0)": [2, 2]}
        window.profile["Palette"]["status"] = True
        window.profile["Canvas"]["box"] = [10, 10, 110, 110]
        window._environments = {window.profile.target: window.profile.snapshot_environment()}
        window._restore_environment()
        first = window.profile.target

        ids = [window._target_combo.itemData(i) for i in range(window._target_combo.count())]
        other = next(i for i in ids if i != first)
        window._target_combo.setCurrentIndex(ids.index(other))
        assert window.profile.target == other
        # The new target has no taught geometry of its own.
        assert window.bot._palette is None
        assert window.bot._canvas is None

        window._target_combo.setCurrentIndex(ids.index(first))
        assert window.profile.target == first
        assert window.bot._canvas == (10, 10, 100, 100)
        assert window.bot._palette is not None
        assert len(window.bot._palette.colors) == 2
    finally:
        window.close()


def test_preflight_reports_missing_pieces(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        # Clear any environment restored from the developer's config.
        window.profile["Canvas"]["box"] = None
        window.profile["Palette"]["box"] = None
        window.profile["Palette"]["color_coords"] = None
        window.bot._palette = None
        window._refresh_readiness()

        reasons = [reason for reason, _, _ in window._preflight_issues()]
        assert "canvas not set" in reasons
        assert "palette not set" in reasons
        assert window._fix_btn.isVisibleTo(window)
    finally:
        window.close()


def test_image_field_browse_action_and_empty_load(app, tmp_path, monkeypatch):
    """Browse is a field helper; an empty Load must not silently open a dialog."""
    from PIL import Image
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        picked = tmp_path / "picked.png"
        Image.new("RGB", (24, 24), (1, 2, 3)).save(picked)
        calls = {"count": 0}

        def fake_dialog(*args, **kwargs):
            calls["count"] += 1
            return str(picked), "Images (*.png)"

        monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_dialog)

        # Empty field: Load is disabled and never reaches the file dialog.
        window._url_edit.clear()
        assert not window._load_btn.isEnabled()
        window._on_load_clicked()
        assert calls["count"] == 0

        # The folder action opens the picker and mirrors the path into the field.
        window._browse_action.trigger()
        assert calls["count"] == 1
        assert window._url_edit.text() == str(picked)
        assert window._load_btn.isEnabled()
        assert window._imname == str(picked)
    finally:
        window.close()


def test_image_preview_accepts_file_drops(app):
    from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from pyaint.ui.widgets import ImagePreview

    preview = ImagePreview()
    seen = []
    preview.fileDropped.connect(seen.append)
    try:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("C:/tmp/pic.png")])
        enter = QDragEnterEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        preview.dragEnterEvent(enter)
        assert preview.property("dragActive") == "true"

        drop = QDropEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        preview.dropEvent(drop)
        assert seen == ["C:/tmp/pic.png"]
        assert preview.property("dragActive") == "false"
    finally:
        preview.close()
