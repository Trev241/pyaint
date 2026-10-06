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


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point the window at a throwaway config.json for every test.

    ``MainWindow.closeEvent`` flushes settings and clears the cache dir, so a
    test that clears the profile would otherwise overwrite the developer's real
    config (and delete the real cache) on close.
    """
    from pyaint import paths

    monkeypatch.setattr(paths, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(paths, "CONFIG_PATH", str(tmp_path / "config.json"))
    yield


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


def test_mode_specific_controls_switch_with_stroke_mode(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        layered = window._mode_combo.findData(Bot.LAYERED)
        outline = window._mode_combo.findData(Bot.OUTLINE)

        window._mode_combo.setCurrentIndex(layered)
        assert window._runs_controls.isVisibleTo(window)
        assert not window._outline_controls.isVisibleTo(window)
        assert window._mode_hint.property("experimental") != "true"

        window._mode_combo.setCurrentIndex(outline)
        assert window._outline_controls.isVisibleTo(window)
        assert not window._runs_controls.isVisibleTo(window)
        assert window._mode_hint.property("experimental") == "true"
        assert "Experimental" in window._mode_hint.text()

        window._stroke_speed.set_value(2000, emit=True)
        assert bot.stroke_speed == pytest.approx(2000)
        window._event_interval.set_value(20, emit=True)
        assert bot.frame_interval == pytest.approx(0.02)
        window._travel_delay.set_value(0.2, emit=True)
        assert bot.travel_delay == pytest.approx(0.2)
    finally:
        window.close()


def test_outline_settings_persist(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    window = MainWindow(Bot())
    try:
        window._mode_combo.setCurrentIndex(window._mode_combo.findData(Bot.OUTLINE))
        window._stroke_speed.set_value(2000, emit=True)
        window._event_interval.set_value(25, emit=True)
        window._travel_delay.set_value(0.2, emit=True)
        window._save_config()
    finally:
        window.close()

    restored = MainWindow(Bot())
    try:
        assert restored.bot.stroke_speed == pytest.approx(2000)
        assert restored.bot.frame_interval == pytest.approx(0.025)
        assert restored.bot.travel_delay == pytest.approx(0.2)
        assert restored._mode == Bot.OUTLINE
    finally:
        restored.close()


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
        # Detection is an overlay; the Image panel stays on the preview page.
        assert window._image_stack.currentWidget() is window._preview_page

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


def test_apply_detection_keeps_taught_palette_and_warns(app, tmp_path, monkeypatch):
    """A canvas-only re-detect must keep the taught palette and say so."""
    monkeypatch.chdir(tmp_path)
    from PIL import Image

    from pyaint.locators import Detection

    bot = Bot()
    window = MainWindow(bot)
    try:
        white = Image.new("RGB", (300, 200), (255, 255, 255))
        # Seed a previously taught canvas and palette.
        bot.apply_detection(
            Detection(
                canvas=(30, 20, 180, 110),
                palette=(40, 150, 74, 34),
                palette_rows=2,
                palette_cols=4,
            ),
            image=white,
        )
        assert bot._palette is not None
        assert window._environment_ready()

        # Re-detect finds only the canvas: the taught palette is kept.
        window._detection_result = Detection(
            canvas=(30, 20, 180, 110), palette_expected=True
        )
        window._detection_image = white
        window._apply_detection()

        assert bot._palette is not None
        assert bot.profile["Palette"]["status"] is True
        assert window._environment_ready()
        notice = window._notice._text.text().lower()
        assert "palette" in notice and "keeping" in notice
    finally:
        window.close()


def test_apply_detection_stores_region_previews(app, tmp_path, monkeypatch):
    """Auto-detected regions must show up as previews in Setup."""
    import os

    monkeypatch.chdir(tmp_path)
    from PIL import Image

    from pyaint import paths
    from pyaint.locators import Detection
    from pyaint.ui.setup_dialog import SetupDialog

    bot = Bot()
    window = MainWindow(bot)
    try:
        image = Image.new("RGB", (300, 200), (255, 255, 255))
        window._detection_result = Detection(
            canvas=(10, 10, 200, 120),
            palette=(20, 150, 120, 40),
            palette_rows=2,
            palette_cols=4,
        )
        window._detection_image = image
        window._apply_detection()

        assert window.profile["Canvas"]["preview"]
        assert window.profile["Palette"]["preview"]
        for name in ("Canvas", "Palette"):
            path = os.path.join(paths.PROJECT_ROOT, window.profile[name]["preview"])
            assert os.path.exists(path)

        # Reopening Setup must load the saved preview rather than a blank pane.
        dialog = SetupDialog(
            None, bot, window.profile, required_tools=("Palette", "Canvas")
        )
        try:
            assert dialog._palette_preview._original is not None
        finally:
            dialog.close()
    finally:
        window.close()


def test_reset_config_wipes_everything_immediately(app, tmp_path, monkeypatch):
    """Reset must reinitialize live state, not just delete the file."""
    import os

    from PySide6.QtWidgets import QMessageBox

    from pyaint import paths
    from pyaint.locators import Detection

    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        # Seed a taught environment and a non-default preference.
        window.profile.target = "mspaint"
        window.profile["Palette"].update(
            {"status": True, "box": [10, 10, 90, 50], "rows": 2, "cols": 4}
        )
        window.profile["Canvas"].update({"status": True, "box": [0, 0, 200, 200]})
        bot._palette = object()
        window._save_config()
        assert os.path.exists(paths.CONFIG_PATH)

        monkeypatch.setattr(
            QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes)
        )
        window._on_reset_config()

        # Live state is back to defaults, without a restart.
        assert window.profile.target == "generic"
        assert window.profile["Palette"]["status"] is False
        assert window.profile["Palette"]["box"] is None
        assert window.profile["Canvas"]["status"] is False
        assert bot._palette is None
        # The fresh defaults are written back out.
        assert os.path.exists(paths.CONFIG_PATH)
    finally:
        window.close()


def test_pick_points_minimizes_and_captures_before_overlay(app, monkeypatch):
    """Hiding a dialog ends its exec() loop, which broke manual teaching; and
    the clean screenshot must be taken before the translucent veil appears."""
    from PIL import Image
    from PySide6.QtWidgets import QDialog, QWidget

    import pyaint.ui.capture as capture

    parent = QWidget()
    parent.show()
    events = []
    sentinel = Image.new("RGB", (10, 10), (1, 2, 3))

    class FakeOverlay:
        def __init__(self, count, prompt):
            self.points = [(1, 1), (2, 2)]

        def exec(self):
            events.append(("exec", parent.isMinimized()))
            return QDialog.Accepted

    def fake_screenshot(*args, **kwargs):
        events.append(("screenshot", parent.isMinimized()))
        return sentinel

    monkeypatch.setattr(capture, "_PickOverlay", FakeOverlay)
    monkeypatch.setattr(capture.pyautogui, "screenshot", fake_screenshot)
    try:
        result = capture.pick_points(parent, 2, "prompt")
        # Grabbed while pyaint is minimized and *before* the overlay runs.
        assert events[0] == ("screenshot", True)
        assert events[1] == ("exec", True)
        assert result is not None and len(result.points) == 2
        assert result.image is sentinel
        assert not parent.isMinimized()
    finally:
        parent.close()


def test_pick_points_real_overlay_accepts_on_final_click(app, monkeypatch):
    """Regression: the real overlay must return its points, not vanish.

    Hiding a modal QDialog exits its ``exec()`` loop with ``Rejected``, so the
    old ``hide()`` + deferred ``accept()`` made ``pick_points`` return ``None``
    and silently dropped every taught point (preview blank, status unset).
    """
    from PIL import Image
    from PySide6.QtCore import QPointF, QEvent, QTimer, Qt
    from PySide6.QtGui import QMouseEvent

    import pyaint.ui.capture as capture

    sentinel = Image.new("RGB", (10, 10), (1, 2, 3))
    monkeypatch.setattr(capture.pyautogui, "screenshot", lambda *a, **k: sentinel)

    real_overlay = capture._PickOverlay

    class ClickingOverlay(real_overlay):
        def showEvent(self, event):  # noqa: N802
            super().showEvent(event)
            QTimer.singleShot(0, self._click_corners)

        def _click_corners(self):
            for _ in range(2):
                click = QMouseEvent(
                    QEvent.MouseButtonPress,
                    QPointF(4, 5),
                    QPointF(4, 5),
                    Qt.LeftButton,
                    Qt.LeftButton,
                    Qt.NoModifier,
                )
                self.mousePressEvent(click)

    monkeypatch.setattr(capture, "_PickOverlay", ClickingOverlay)
    result = capture.pick_points(None, 2, "prompt")
    assert result is not None
    assert len(result.points) == 2
    assert result.image is sentinel


def test_setup_teach_palette_samples_and_previews(app, tmp_path, monkeypatch):
    """Two taught corners must set the palette status and fill the preview."""
    monkeypatch.chdir(tmp_path)
    from PIL import Image

    import pyaint.ui.setup_dialog as setup_module
    from pyaint.profile import Profile
    from pyaint.ui.capture import PickResult
    from pyaint.ui.setup_dialog import SetupDialog

    image = Image.new("RGB", (400, 300), (240, 240, 240))
    colors = [
        (255, 0, 0), (0, 200, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 128, 0),
    ]
    # 2 rows x 4 columns inside (100, 50)-(260, 130).
    for index, color in enumerate(colors):
        row, col = divmod(index, 4)
        for y in range(50 + row * 40, 50 + (row + 1) * 40):
            for x in range(100 + col * 40, 100 + (col + 1) * 40):
                image.putpixel((x, y), color)

    profile = Profile()
    profile["Palette"]["rows"] = 2
    profile["Palette"]["cols"] = 4
    dialog = SetupDialog(None, Bot(), profile, required_tools=("Palette", "Canvas"))
    try:
        assert dialog._current == "Palette"
        monkeypatch.setattr(
            setup_module,
            "pick_points",
            lambda parent, count, prompt: PickResult([(100, 50), (260, 130)], image),
        )
        dialog._teach()
        assert profile["Palette"]["status"] is True
        assert profile["Palette"]["color_coords"]
        assert dialog._palette_preview._original is not None
    finally:
        dialog.close()


def test_setup_teach_palette_failure_keeps_status_unset(app, tmp_path, monkeypatch):
    """A failed sample must not claim the palette is configured."""
    monkeypatch.chdir(tmp_path)
    from PySide6.QtWidgets import QMessageBox

    import pyaint.ui.setup_dialog as setup_module
    from pyaint.profile import Profile
    from pyaint.ui.capture import PickResult
    from pyaint.ui.setup_dialog import SetupDialog

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    profile = Profile()
    dialog = SetupDialog(None, Bot(), profile, required_tools=("Palette", "Canvas"))
    try:
        # No screenshot was captured, so sampling must fail rather than fall
        # back to a fresh grab that shows the dialog itself.
        monkeypatch.setattr(
            setup_module,
            "pick_points",
            lambda parent, count, prompt: PickResult([(10, 10), (80, 60)], None),
        )
        dialog._teach()
        assert profile["Palette"]["status"] is False
        assert dialog._palette_preview._original is None
    finally:
        dialog.close()


def _teachable_palette_image():
    """A 2x4 swatch grid inside (100, 50)-(260, 130)."""
    from PIL import Image

    image = Image.new("RGB", (400, 300), (240, 240, 240))
    colors = [
        (255, 0, 0), (0, 200, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 128, 0),
    ]
    for index, color in enumerate(colors):
        row, col = divmod(index, 4)
        for y in range(50 + row * 40, 50 + (row + 1) * 40):
            for x in range(100 + col * 40, 100 + (col + 1) * 40):
                image.putpixel((x, y), color)
    return image


def test_setup_palette_preview_persists_across_reopen(app, tmp_path, monkeypatch):
    """The captured palette preview must survive closing and reopening Setup."""
    monkeypatch.chdir(tmp_path)
    import pyaint.ui.setup_dialog as setup_module
    from pyaint.profile import Profile
    from pyaint.ui.capture import PickResult
    from pyaint.ui.setup_dialog import SetupDialog

    image = _teachable_palette_image()
    profile = Profile()
    profile["Palette"]["rows"] = 2
    profile["Palette"]["cols"] = 4
    dialog = SetupDialog(None, Bot(), profile, required_tools=("Palette", "Canvas"))
    try:
        monkeypatch.setattr(
            setup_module,
            "pick_points",
            lambda parent, count, prompt: PickResult([(100, 50), (260, 130)], image),
        )
        dialog._teach()
        assert profile["Palette"]["preview"]
    finally:
        dialog.close()

    reopened = SetupDialog(None, Bot(), profile, required_tools=("Palette", "Canvas"))
    try:
        assert reopened._current == "Palette"
        assert reopened._palette_preview._original is not None
        assert "colours sampled" in reopened._palette_feedback.text()
    finally:
        reopened.close()


def test_setup_clear_tool_forgets_palette(app, tmp_path, monkeypatch):
    """The Clear button must unset the tool and remove its preview."""
    import os

    monkeypatch.chdir(tmp_path)
    import pyaint.ui.setup_dialog as setup_module
    from pyaint import paths
    from pyaint.profile import Profile
    from pyaint.ui.capture import PickResult
    from pyaint.ui.setup_dialog import SetupDialog

    image = _teachable_palette_image()
    profile = Profile()
    profile["Palette"]["rows"] = 2
    profile["Palette"]["cols"] = 4
    bot = Bot()
    dialog = SetupDialog(None, bot, profile, required_tools=("Palette", "Canvas"))
    try:
        monkeypatch.setattr(
            setup_module,
            "pick_points",
            lambda parent, count, prompt: PickResult([(100, 50), (260, 130)], image),
        )
        dialog._teach()
        assert profile["Palette"]["status"] is True
        preview_file = os.path.join(paths.PROJECT_ROOT, profile["Palette"]["preview"])
        assert os.path.exists(preview_file)

        dialog._clear_tool("Palette")
        assert profile["Palette"]["status"] is False
        assert profile["Palette"]["box"] is None
        assert profile["Palette"]["color_coords"] is None
        assert profile["Palette"]["preview"] is None
        assert bot._palette is None
        assert not os.path.exists(preview_file)
    finally:
        dialog.close()


def test_pick_points_scales_logical_clicks_to_screenshot(app, monkeypatch):
    """A scaled display must not offset a manually taught box."""
    from PIL import Image
    from PySide6.QtCore import QRect

    import pyaint.ui.capture as capture

    class FakeScreen:
        def geometry(self):
            return QRect(0, 0, 1280, 720)

    monkeypatch.setattr(
        capture.QGuiApplication, "primaryScreen", staticmethod(lambda: FakeScreen())
    )
    physical = Image.new("RGB", (1920, 1080))
    assert capture._to_screenshot_points([(100, 50)], physical) == [(150, 75)]

    # A 1:1 display passes clicks through untouched.
    assert capture._to_screenshot_points(
        [(100, 50)], Image.new("RGB", (1280, 720))
    ) == [(100, 50)]
    assert capture._to_screenshot_points([(1, 2)], None) == [(1, 2)]


def test_progress_signal_updates_overlay_bar(app, tmp_path, monkeypatch):
    """Drawing progress goes to the floating overlay, not a status bar."""
    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    try:
        window.signals.progress.emit(5, 10, 1.0)
        assert window._overlay._bar.value() == 50
        assert not hasattr(window, "_progress")
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


def test_image_preview_accepts_remote_url_drops(app):
    """Browser drags carry a URL, not a local file, so they must be accepted."""
    from PySide6.QtCore import QByteArray, QMimeData, QPoint, Qt
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from pyaint.ui.widgets import ImagePreview

    preview = ImagePreview()
    seen = []
    preview.remoteDropped.connect(seen.append)
    try:
        mime = QMimeData()
        mime.setData("text/uri-list", QByteArray(b"https://example.com/cat.png"))
        enter = QDragEnterEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        preview.dragEnterEvent(enter)
        assert preview.property("dragActive") == "true"

        drop = QDropEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        preview.dropEvent(drop)
        assert seen == ["https://example.com/cat.png"]
        assert preview.property("dragActive") == "false"
    finally:
        preview.close()


def test_image_preview_accepts_data_uri_drops(app):
    from PySide6.QtCore import QByteArray, QMimeData, QPoint, Qt
    from PySide6.QtGui import QDropEvent

    from pyaint.ui.widgets import ImagePreview

    preview = ImagePreview()
    seen = []
    preview.remoteDropped.connect(seen.append)
    uri = "data:image/png;base64,iVBORw0KGgo="
    try:
        mime = QMimeData()
        mime.setData("text/plain", QByteArray(uri.encode()))
        drop = QDropEvent(
            QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        preview.dropEvent(drop)
        assert seen == [uri]
    finally:
        preview.close()


def test_remote_source_prefers_image_url_over_page_url():
    from PySide6.QtCore import QByteArray, QMimeData

    from pyaint.ui.widgets import remote_source_from_mime

    mime = QMimeData()
    mime.setData(
        "text/html",
        QByteArray(b'<a href="#"><img src="https://example.com/real.png"></a>'),
    )
    mime.setData("text/uri-list", QByteArray(b"https://www.google.com/search?q=cat"))
    assert remote_source_from_mime(mime) == "https://example.com/real.png"


def test_main_window_routes_remote_drops(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QByteArray, QMimeData

    monkeypatch.chdir(tmp_path)
    bot = Bot()
    window = MainWindow(bot)
    seen = []
    monkeypatch.setattr(window, "_load_dropped_url", seen.append)
    try:
        mime = QMimeData()
        mime.setData("text/uri-list", QByteArray(b"https://example.com/a.png"))
        window._handle_image_drop(mime)
        assert seen == ["https://example.com/a.png"]
    finally:
        window.close()


def test_decode_data_uri_and_unwrap_redirect():
    import base64

    from pyaint.ui.main_window import _decode_data_uri, _unwrap_image_redirect

    payload = base64.b64encode(b"hello").decode()
    assert _decode_data_uri(f"data:image/png;base64,{payload}") == b"hello"

    wrapped = (
        "https://www.google.com/imgres?imgurl=https%3A%2F%2Fexample.com%2Fcat.png&tbnid=x"
    )
    assert _unwrap_image_redirect(wrapped) == "https://example.com/cat.png"
    other = "https://example.com/page?url=https://evil.test/x.png"
    assert _unwrap_image_redirect(other) == other


def test_startup_restores_palette_from_saved_coords_without_screenshot(
    app, tmp_path, monkeypatch
):
    """A saved palette must rebuild offline, not by re-screenshotting the box."""
    import json

    import pyaint.palette as palette_module
    from pyaint import paths

    config = {
        "target": "mspaint",
        "Canvas": {"status": True, "box": [10, 20, 210, 120]},
        "Palette": {
            "status": True,
            "box": [10, 10, 210, 40],
            "rows": 1,
            "cols": 2,
            "color_coords": {"(255, 0, 0)": [15, 15], "(0, 0, 255)": [115, 15]},
        },
    }
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_PATH", str(cfg))

    def no_screenshot(*args, **kwargs):
        raise AssertionError("startup must not screenshot the palette")

    monkeypatch.setattr(palette_module.pyautogui, "screenshot", no_screenshot)

    bot = Bot()
    window = MainWindow(bot)
    try:
        assert bot._canvas == (10, 20, 200, 100)
        palette = bot._palette
        assert palette is not None
        assert len(palette.colors) == 2
        assert (255, 0, 0) in palette.colors
        assert palette.colors_pos[(255, 0, 0)] == (15, 15)
        assert window._environment_ready()
    finally:
        window.close()


def test_close_flushes_pending_settings(app, tmp_path, monkeypatch):
    """Closing the window must persist settings that no slot saved eagerly."""
    import json

    from pyaint import paths

    cfg = tmp_path / "config.json"
    monkeypatch.setattr(paths, "CONFIG_PATH", str(cfg))
    bot = Bot()
    window = MainWindow(bot)
    try:
        window.bot.pause_key = "q"
        window.close()
        assert json.loads(cfg.read_text(encoding="utf-8"))["pause_key"] == "q"
    finally:
        window.close()


def test_color_metric_option_defaults_and_persists(app):
    import json

    from pyaint import paths
    from pyaint.palette import DEFAULT_METRIC, METRIC_RGB

    bot = Bot()
    window = MainWindow(bot)
    try:
        assert window._metric_combo.currentData() == DEFAULT_METRIC
        assert bot.color_metric == DEFAULT_METRIC

        legacy = window._metric_combo.findData(METRIC_RGB)
        window._metric_combo.setCurrentIndex(legacy)
        assert bot.color_metric == METRIC_RGB
        with open(paths.CONFIG_PATH, encoding="utf-8") as handle:
            assert json.load(handle)["color_metric"] == METRIC_RGB
    finally:
        window.close()


def test_transparent_option_defaults_on_and_persists(app):
    import json

    from pyaint import paths

    bot = Bot()
    window = MainWindow(bot)
    try:
        assert window._chk_transparent.isChecked()
        assert window.draw_options & Bot.IGNORE_TRANSPARENT

        window._chk_transparent.setChecked(False)
        assert not (window.draw_options & Bot.IGNORE_TRANSPARENT)
        with open(paths.CONFIG_PATH, encoding="utf-8") as handle:
            options = json.load(handle)["drawing_options"]
        assert options["ignore_transparent_pixels"] is False
    finally:
        window.close()


def test_load_field_routes_url_path_and_search(app, monkeypatch):
    from pyaint.ui.main_window import _looks_like_path

    # Path detection uses shape, not existence, so typos don't search.
    assert _looks_like_path(r"C:\pics\a.png")
    assert _looks_like_path("./a.png")
    assert _looks_like_path("/tmp/a.png")
    assert not _looks_like_path("cartoon cat")

    bot = Bot()
    window = MainWindow(bot)
    try:
        started = []
        monkeypatch.setattr(
            window, "_start_task", lambda name, work, **kwargs: started.append(name)
        )
        searched = []
        monkeypatch.setattr(window, "_start_search", lambda query: searched.append(query))

        window._url_edit.setText("https://example.com/a.png")
        window._on_load_clicked()
        assert started == ["Download image"]

        # A missing but path-shaped value stays a "not found", not a search.
        window._url_edit.setText(r"C:\definitely\missing\file.png")
        window._on_load_clicked()
        assert started == ["Download image"]
        assert searched == []

        window._url_edit.setText("cartoon cat")
        window._on_load_clicked()
        assert searched == ["cartoon cat"]
    finally:
        window.close()


def _png_bytes(color=(255, 0, 0), size=(8, 8)):
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_search_gallery_populates_selects_and_returns(app, monkeypatch):
    import pyaint.image_search as image_search
    from pyaint.image_search import ImageCandidate, SearchPage

    candidates = [
        ImageCandidate(
            url="https://example/full1.png",
            thumb_url="https://example/thumb1.png",
            mime="image/png",
            title="File:One.png",
            source_url="https://commons.example/One",
            width=100,
            height=80,
        ),
        ImageCandidate(
            url="https://example/full2.png",
            thumb_url="https://example/thumb2.png",
            mime="image/png",
            title="File:Two.png",
            source_url="https://commons.example/Two",
            width=80,
            height=120,
        ),
    ]

    def fake_search_page(query, **kwargs):
        return SearchPage(candidates=candidates, next_continue=None)

    monkeypatch.setattr(image_search, "search_page", fake_search_page)
    monkeypatch.setattr(image_search, "fetch_bytes", lambda url, timeout=30: _png_bytes())

    bot = Bot()
    window = MainWindow(bot)
    try:
        # Run the page fetch synchronously instead of on the thread pool.
        monkeypatch.setattr(
            window,
            "_request_search_page",
            lambda cont: window._on_search_page(
                window._search_generation,
                fake_search_page(window._search_query, cont=cont),
            ),
        )
        monkeypatch.setattr(window, "_start_thumbnails", lambda candidates: None)
        # Commit synchronously instead of via the busy worker thread.
        monkeypatch.setattr(window, "_start_task", lambda name, work, **kw: work())

        window._start_search("cats")
        assert window._gallery.count() == 2
        assert window._image_stack.currentWidget() is window._gallery
        assert window._gallery.first_candidate() == candidates[0]

        window._on_candidate_selected(candidates[1])
        assert window._image_stack.currentWidget() is window._preview_page
        assert "File:Two.png" in window._image_info.text()
        assert not window._back_btn.isHidden()

        window._show_results()
        assert window._image_stack.currentWidget() is window._gallery
    finally:
        window.close()


def test_double_enter_selects_first_result(app, monkeypatch):
    from pyaint.image_search import ImageCandidate

    bot = Bot()
    window = MainWindow(bot)
    try:
        selected = []
        monkeypatch.setattr(window, "_on_candidate_selected", selected.append)
        monkeypatch.setattr(window, "_start_search", lambda query: None)
        window._search_query = "cats"
        window._gallery.add_candidate(
            ImageCandidate(
                url="u",
                thumb_url="t",
                mime="image/png",
                title="File:Cats.png",
                source_url="s",
                width=10,
                height=10,
            )
        )
        window._image_stack.setCurrentWidget(window._gallery)
        window._url_edit.setText("cats")
        window._on_load_clicked()
        assert len(selected) == 1
    finally:
        window.close()


def test_search_page_task_reports_page(monkeypatch):
    import pyaint.image_search as image_search
    from pyaint.ui.search_tasks import SearchPageTask

    monkeypatch.setattr(image_search, "search_page", lambda q, **kw: "PAGE")
    task = SearchPageTask("q", None, 7)
    got = []
    task.signals.ready.connect(lambda generation, page: got.append((generation, page)))
    task.run()
    assert got == [(7, "PAGE")]


def test_image_source_selector_defaults_and_persists(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pyaint.image_search as image_search

    window = MainWindow(Bot())
    try:
        assert window._provider == image_search.DEFAULT_PROVIDER == "openverse"
        assert window._provider_combo.currentData() == "openverse"

        window._provider_combo.setCurrentIndex(
            window._provider_combo.findData("commons")
        )
        assert window._provider == "commons"
        assert window.tools.get("image_search_provider") == "commons"
    finally:
        window.close()

    restored = MainWindow(Bot())
    try:
        assert restored._provider == "commons"
        assert restored._provider_combo.currentData() == "commons"
    finally:
        restored.close()


def test_changing_source_reruns_active_search(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    window = MainWindow(Bot())
    try:
        seen = []
        monkeypatch.setattr(window, "_start_search", seen.append)
        window._search_query = "cats"
        window._image_stack.setCurrentWidget(window._gallery)
        window._provider_combo.setCurrentIndex(
            window._provider_combo.findData("commons")
        )
        assert seen == ["cats"]
    finally:
        window.close()


def test_drawing_settings_are_per_target(app):
    bot = Bot()
    window = MainWindow(bot)
    try:
        ids = [
            window._target_combo.itemData(i)
            for i in range(window._target_combo.count())
        ]
        assert "mspaint" in ids and "skribbl" in ids

        # Tune MS Paint fast.
        window._target_combo.setCurrentIndex(ids.index("mspaint"))
        window.bot.settings[:] = [0.01, 4, 0.05]
        window.bot.jump_threshold = 3
        window._store_drawing_settings()
        window._save_config()

        # skribbl falls back to its slower recipe defaults.
        window._target_combo.setCurrentIndex(ids.index("skribbl"))
        assert window.bot.settings[0] == pytest.approx(0.05)
        assert window.bot.settings[2] == pytest.approx(0.5)
        assert window.bot.jump_threshold == 5

        # Tune skribbl slower still; it must not leak into MS Paint.
        window.bot.settings[:] = [0.2, 10, 1.0]
        window._store_drawing_settings()
        window._save_config()

        window._target_combo.setCurrentIndex(ids.index("mspaint"))
        assert window.bot.settings[0] == pytest.approx(0.01)
        assert window.bot.settings[1] == pytest.approx(4)
        assert window.bot.jump_threshold == 3

        window._target_combo.setCurrentIndex(ids.index("skribbl"))
        assert window.bot.settings[0] == pytest.approx(0.2)
        assert window.bot.settings[1] == pytest.approx(10)
    finally:
        window.close()
