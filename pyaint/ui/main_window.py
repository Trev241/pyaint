"""VS Code-inspired main window (PySide6).

This is the Qt replacement for the historical Tk ``Window``. It owns the
shared :class:`~pyaint.profile.Profile`, persists ``config.json``, and runs
long tasks on worker threads. Progress is delivered by ``Bot`` through a
callback that emits a Qt signal, so all UI updates happen on the main thread.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import traceback
import urllib.error as urllib_error
import urllib.request

from PIL import Image
from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyaint import config as pyaint_config
from pyaint import paths
from pyaint.annotate import annotate_detection
from pyaint.bot import Bot
from pyaint.locators import detect_target
from pyaint.log import log
from pyaint.profile import Profile
from pyaint.targets import (
    apply_profile_defaults,
    get_recipe,
    list_recipes,
    load_user_recipes,
    merge_drawing_options,
    merge_drawing_settings,
)
from pyaint.ui import theme
from pyaint.ui.countdown import CountdownBanner
from pyaint.ui.icons import icon
from pyaint.ui.overlay import ProgressOverlay
from pyaint.ui.widgets import (
    CollapsibleSection,
    ImagePreview,
    ReadinessStrip,
    Section,
    SliderField,
    ToolControls,
    pil_to_qpixmap,
)
from pyaint.validation import validate_recipe

_PANELS = (("Setup", "target"), ("Image", "image"), ("Draw", "sliders"))


class UiSignals(QObject):
    """Cross-thread signals: workers emit, the main thread consumes."""

    progress = Signal(int, int, float)
    status = Signal(str)
    finished = Signal(str)
    image_ready = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.title = "Pyaint"
        self.setWindowTitle(self.title)
        self.resize(1320, 840)
        self.setMinimumSize(940, 620)
        self.setAcceptDrops(True)

        self._initializing = True
        self._config_path = paths.CONFIG_PATH
        self.profile = Profile()
        self.bot.profile = self.profile
        self.tools = {}
        self.draw_options = 0
        self._mode = Bot.LAYERED
        self._busy = False
        self._last_url = ""
        self._redraw_region = None
        self._recipes = []
        self._recipes_by_name = {}
        self._imname = os.path.join(paths.PROJECT_ROOT, "assets", "sample.png")
        self._detecting = False
        self._detection_result = None
        self._detection_image = None
        self._detection_view = None

        self.signals = UiSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.status.connect(self._set_status)
        self.signals.finished.connect(self._on_task_finished)
        self.signals.image_ready.connect(self._set_image_path)
        self.bot.progress_callback = self._emit_progress

        # Resolve the theme before building widgets so the first paint is right.
        self._theme_mode = "auto"
        try:
            self._theme_mode = str(pyaint_config.load_config(self._config_path).get("theme", "auto"))
        except Exception:
            pass
        if self._theme_mode not in theme.THEME_MODES:
            self._theme_mode = "auto"
        self.tokens = theme.resolve_tokens(self._theme_mode)
        app = QApplication.instance()
        if app is not None:
            theme.apply(app, self.tokens)

        self._build_ui()
        self._overlay = ProgressOverlay()
        self._load_recipes()
        self.load_config()
        self._load_default_image()

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_scheme_changed)
        self._apply_theme()
        self._initializing = False

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_activity_rail())
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)
        self._build_statusbar()

    def _build_activity_rail(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("ActivityRail")
        rail.setFixedWidth(48)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(0)
        self._activity_buttons = []
        for index, (name, icon_name) in enumerate(_PANELS):
            button = QToolButton()
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setIcon(icon(icon_name, self.tokens["fg_muted"], 22))
            button.setIconSize(QSize(22, 22))
            button.setFixedSize(48, 44)
            button.setToolTip(f"{name} panel")
            button.setChecked(index == 0)
            button.clicked.connect(lambda _=False, i=index: self._show_panel(i))
            self._activity_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)
        return rail

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("SideBar")
        side.setFixedWidth(310)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._side_title = QLabel("SETUP")
        self._side_title.setObjectName("SideBarTitle")
        layout.addWidget(self._side_title)
        self._panels = QStackedWidget()
        self._panels.addWidget(self._build_setup_panel())
        self._panels.addWidget(self._build_image_panel())
        self._panels.addWidget(self._build_draw_panel())
        layout.addWidget(self._panels, 1)
        return side

    @staticmethod
    def _scroll_panel() -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll, layout

    def _build_setup_panel(self) -> QWidget:
        scroll, layout = self._scroll_panel()

        target = Section("Choose your app", "Pick the drawing app, then detect or teach its canvas and palette.")
        self._target_combo = QComboBox()
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        target.add(self._target_combo)
        detect_row = QHBoxLayout()
        self._auto_btn = QPushButton("Auto-detect")
        self._auto_btn.setToolTip("Find the canvas and palette from a screenshot")
        self._auto_btn.clicked.connect(self.auto_detect)
        teach_btn = QPushButton("Teach manually…")
        teach_btn.setToolTip("Point at the canvas and palette yourself")
        teach_btn.clicked.connect(self.open_setup)
        detect_row.addWidget(self._auto_btn)
        detect_row.addWidget(teach_btn)
        target.add_layout(detect_row)
        needs = QLabel(
            "Auto-detect needs a blank canvas, the app maximized on the primary "
            "monitor, at 100% display scaling."
        )
        needs.setObjectName("SectionHint")
        needs.setWordWrap(True)
        target.add(needs)
        self._detection_label = QLabel("No regions detected yet.")
        self._detection_label.setObjectName("SectionHint")
        self._detection_label.setWordWrap(True)
        target.add(self._detection_label)
        layout.insertWidget(layout.count() - 1, target)

        return scroll

    def _build_draw_panel(self) -> QWidget:
        scroll, layout = self._scroll_panel()

        mode = Section("Stroke mode", "How the image is turned into strokes.")
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Layered (fewer strokes)", Bot.LAYERED)
        self._mode_combo.addItem("Slotted (exact runs)", Bot.SLOTTED)
        self._mode_combo.setItemData(
            0,
            "Merges a colour's runs where later colours paint over them: fewer "
            "strokes, faster drawing, smoother joins (default).",
            Qt.ToolTipRole,
        )
        self._mode_combo.setItemData(
            1,
            "Draws every run exactly as-is: no overdraw, but more strokes to draw.",
            Qt.ToolTipRole,
        )
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode.add(self._mode_combo)
        layout.insertWidget(layout.count() - 1, mode)

        drawing = Section("Drawing", "How slowly and how finely Pyaint paints.")
        self._setters = [
            SliderField("Time per stroke", 0.0, 1.0, 0.1, 0.01),
            SliderField("Detail (lower = finer)", 1, 50, 12, 1),
            SliderField("Pause after big moves", 0.0, 2.0, 0.5, 0.05),
        ]
        tooltips = (
            "How long each stroke takes (higher = slower, smoother).",
            "Pixel step between sampled points. Lower = finer detail, more strokes.",
            "Pause inserted when the cursor jumps a long way between strokes.",
        )
        for index, field in enumerate(self._setters):
            field.setToolTip(tooltips[index])
            field.changed.connect(lambda value, i=index: self._on_setting_changed(i, value))
            drawing.add(field)

        trigger_row = QHBoxLayout()
        trigger_label = QLabel("Trigger distance (px)")
        trigger_label.setObjectName("FieldHint")
        self._jump_threshold = QSpinBox()
        self._jump_threshold.setRange(1, 200)
        self._jump_threshold.setValue(5)
        self._jump_threshold.setToolTip("Cursor jumps longer than this get the pause above")
        self._jump_threshold.valueChanged.connect(self._on_jump_threshold_changed)
        trigger_row.addWidget(trigger_label)
        trigger_row.addStretch(1)
        trigger_row.addWidget(self._jump_threshold)
        drawing.add_layout(trigger_row)
        layout.insertWidget(layout.count() - 1, drawing)

        options = Section("Options")
        self._chk_ignore = QCheckBox("Ignore white pixels")
        self._chk_ignore.setToolTip("Skip pure-white areas, e.g. a blank background")
        self._chk_skip = QCheckBox("Skip first color")
        self._chk_skip.setToolTip(
            "Don't paint the first colour — useful when it is already on the canvas."
        )
        self._chk_ignore.toggled.connect(self._on_options_changed)
        self._chk_skip.toggled.connect(self._on_skip_changed)
        for box in (self._chk_ignore, self._chk_skip):
            options.add(box)
        layout.insertWidget(layout.count() - 1, options)

        tools = Section(
            "App behaviour",
            "Optional actions Pyaint performs in your app. Tools are hidden unless "
            "the chosen target uses them, and stay disabled until taught in Setup.",
        )
        self._tool_controls = []
        for name, supports_delay in (
            ("New Layer", False),
            ("Color Button", True),
            ("Color Button Okay", True),
        ):
            control = ToolControls(name, lambda n=name: self.profile[n], supports_delay=supports_delay)
            control.changed.connect(self._on_tool_controls_changed)
            tools.add(control)
            self._tool_controls.append(control)
        self._mspaint_box = QWidget()
        mspaint_layout = QVBoxLayout(self._mspaint_box)
        mspaint_layout.setContentsMargins(0, 0, 0, 0)
        mspaint_layout.setSpacing(2)
        self._chk_mspaint = QCheckBox("MS Paint double-click")
        self._chk_mspaint.setToolTip("Some palettes need a double-click to select a colour")
        self._chk_mspaint.toggled.connect(self._on_mspaint_toggled)
        mspaint_layout.addWidget(self._chk_mspaint)
        mspaint_delay_row = QHBoxLayout()
        mspaint_delay_label = QLabel("Double-click delay")
        mspaint_delay_label.setObjectName("FieldHint")
        self._mspaint_delay = QSpinBox()
        self._mspaint_delay.setRange(0, 3000)
        self._mspaint_delay.setSuffix(" ms")
        self._mspaint_delay.setValue(500)
        self._mspaint_delay.valueChanged.connect(self._on_mspaint_delay)
        mspaint_delay_row.addWidget(mspaint_delay_label)
        mspaint_delay_row.addStretch(1)
        mspaint_delay_row.addWidget(self._mspaint_delay)
        mspaint_layout.addLayout(mspaint_delay_row)
        tools.add(self._mspaint_box)
        self._tools_section = tools
        layout.insertWidget(layout.count() - 1, tools)

        advanced = CollapsibleSection("Advanced")
        self._build_advanced_into(advanced)
        layout.insertWidget(layout.count() - 1, advanced)

        return scroll

    def _build_advanced_into(self, container) -> None:
        appearance = Section("Appearance", "Follow the system theme or choose one explicitly.")
        self._theme_combo = QComboBox()
        for mode in theme.THEME_MODES:
            self._theme_combo.addItem(theme.THEME_LABELS[mode], mode)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        appearance.add(self._theme_combo)
        container.add(appearance)

        keys = Section("Input")
        key_row = QHBoxLayout()
        key_label = QLabel("Pause key")
        key_label.setObjectName("FieldLabel")
        self._pause_edit = QLineEdit()
        self._pause_edit.setMaxLength(1)
        self._pause_edit.setFixedWidth(48)
        self._pause_edit.textChanged.connect(self._on_pause_key_changed)
        key_row.addWidget(key_label)
        key_row.addStretch(1)
        key_row.addWidget(self._pause_edit)
        keys.add_layout(key_row)
        container.add(keys)

        files = Section("Files")
        reset = QPushButton("Reset config")
        reset.setObjectName("Danger")
        reset.clicked.connect(self._on_reset_config)
        files.add(reset)
        container.add(files)

    def _build_image_panel(self) -> QWidget:
        scroll, layout = self._scroll_panel()

        load = Section("Load image", "Paste a URL or choose a file. You can also drag an image onto the window.")
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://… or C:\\path\\image.png")
        self._url_edit.returnPressed.connect(self._on_load_clicked)
        load.add(self._url_edit)
        row = QHBoxLayout()
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._on_load_clicked)
        file_btn = QPushButton("Open file…")
        file_btn.clicked.connect(self._open_file)
        row.addWidget(load_btn)
        row.addWidget(file_btn)
        load.add_layout(row)
        layout.insertWidget(layout.count() - 1, load)

        info = Section("Preview")
        self._image_info = QLabel("No image loaded.")
        self._image_info.setObjectName("SectionHint")
        self._image_info.setWordWrap(True)
        info.add(self._image_info)
        layout.insertWidget(layout.count() - 1, info)

        redraw = Section("Redraw region", "Draw only a rectangle you pick on screen.")
        self._region_label = QLabel("No region selected.")
        self._region_label.setObjectName("SectionHint")
        self._region_label.setWordWrap(True)
        redraw.add(self._region_label)
        row2 = QHBoxLayout()
        pick = QPushButton("Pick region")
        pick.clicked.connect(self.pick_region)
        draw = QPushButton("Draw region")
        draw.clicked.connect(self._on_draw_region)
        row2.addWidget(pick)
        row2.addWidget(draw)
        redraw.add_layout(row2)
        layout.insertWidget(layout.count() - 1, redraw)

        return scroll

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._readiness = ReadinessStrip()
        layout.addWidget(self._readiness)
        layout.addWidget(self._build_toolbar())

        self._countdown_banner = CountdownBanner()
        self._countdown_banner.captured.connect(self._begin_capture)
        self._countdown_banner.cancelled.connect(self._cancel_auto_detect)
        layout.addWidget(self._countdown_banner)

        self._detection_view = None
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._image_view = self._build_preview_view("Source image", is_detection=False)
        self._tabs.addTab(self._image_view, "Image")
        layout.addWidget(self._tabs, 1)
        return content

    def _build_preview_view(self, header_text: str, is_detection: bool) -> QWidget:
        stage = QFrame()
        stage.setObjectName("PreviewStage")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(16, 12, 16, 12)
        stage_layout.setSpacing(6)

        header = QLabel(header_text)
        header.setObjectName("StageHeader")
        stage_layout.addWidget(header)

        preview = ImagePreview()
        stage_layout.addWidget(preview, 1)

        if is_detection:
            self._detection_preview = preview
            row = QHBoxLayout()
            self._detection_summary = QLabel("No detection yet.")
            self._detection_summary.setObjectName("StageHeader")
            self._detection_summary.setWordWrap(True)
            row.addWidget(self._detection_summary, 1)
            self._apply_detection_btn = QPushButton("Apply")
            self._apply_detection_btn.setObjectName("Primary")
            self._apply_detection_btn.clicked.connect(self._apply_detection)
            self._retry_detection_btn = QPushButton("Retry")
            self._retry_detection_btn.clicked.connect(self.auto_detect)
            self._cancel_detection_btn = QPushButton("Cancel")
            self._cancel_detection_btn.clicked.connect(self._cancel_detection)
            row.addWidget(self._apply_detection_btn)
            row.addWidget(self._retry_detection_btn)
            row.addWidget(self._cancel_detection_btn)
            stage_layout.addLayout(row)
        else:
            self._preview = preview
        return stage

    def _ensure_detection_tab(self) -> None:
        if self._detection_view is None:
            self._detection_view = self._build_preview_view(
                "Detection preview — screen capture", is_detection=True
            )
            self._tabs.addTab(self._detection_view, "Detection")

    def _show_image_tab(self) -> None:
        if getattr(self, "_tabs", None) is not None:
            self._tabs.setCurrentWidget(self._image_view)

    def _tool_button(self, text: str, icon_name: str, slot, tooltip: str = "") -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("ToolBarButton")
        button.setIcon(icon(icon_name, self.tokens["fg"], 16))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(tooltip or text)
        button.clicked.connect(slot)
        return button

    def _build_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("EditorToolbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self._btn_precompute = self._tool_button(
            "Prepare & cache",
            "download",
            self._on_precompute,
            "Save the stroke map so repeat runs skip processing (drawing time is unchanged)",
        )
        self._btn_test = self._tool_button("Test draw", "zap", self._on_test_draw, "Draw the first 20 strokes")
        self._btn_simple = self._tool_button("Brush test", "play", self._on_simple_test, "Draw 5 lines to tune the brush size")
        for button in (self._btn_precompute, self._btn_test, self._btn_simple):
            layout.addWidget(button)
        layout.addStretch(1)

        self._btn_start = QPushButton("Start")
        self._btn_start.setObjectName("Primary")
        self._btn_start.setIcon(icon("play", self.tokens["accent_fg"], 16))
        self._btn_start.setIconSize(QSize(16, 16))
        self._btn_start.clicked.connect(self._on_start)
        self._btn_pause = self._tool_button("Pause", "pause", self._toggle_pause, "Pause / resume drawing")
        self._btn_stop = self._tool_button("Stop", "stop", self._stop_draw, "Stop drawing (ESC)")
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        layout.addWidget(self._btn_start)
        layout.addWidget(self._btn_pause)
        layout.addWidget(self._btn_stop)
        return bar

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("StatusText")
        bar.addWidget(self._status_label, 1)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedWidth(220)
        bar.addPermanentWidget(self._progress)

    # ------------------------------------------------------------------
    # Recipes / targets
    # ------------------------------------------------------------------
    def _load_recipes(self) -> None:
        for recipe in load_user_recipes():
            issues = validate_recipe(recipe)
            if issues:
                log.info(f"[Recipes] '{recipe.id}' has issues: {issues}")
        self._recipes = list_recipes()
        self._recipes_by_name = {r.name: r for r in self._recipes}
        self._target_combo.blockSignals(True)
        self._target_combo.clear()
        for recipe in self._recipes:
            self._target_combo.addItem(recipe.name, recipe.id)
        self._target_combo.blockSignals(False)

    def _on_target_changed(self, _index: int) -> None:
        if self._initializing:
            return
        recipe_id = self._target_combo.currentData()
        recipe = next((r for r in self._recipes if r.id == recipe_id), None)
        if recipe:
            self.profile.target = recipe.id
            self._apply_recipe(recipe)
            self._store_drawing_settings()
            self._store_drawing_options()
            self._save_config()
            self._set_status(f"Target set to {recipe.name}.")

    def _apply_recipe(self, recipe) -> None:
        apply_profile_defaults(self.profile, recipe)
        self.bot.settings[:] = merge_drawing_settings(self.bot.settings, recipe.drawing_settings or {})
        if "jump_threshold" in (recipe.drawing_settings or {}):
            self.bot.jump_threshold = int(recipe.drawing_settings["jump_threshold"])
            self._jump_threshold.setValue(self.bot.jump_threshold)
        self.draw_options = merge_drawing_options(
            self.draw_options, recipe.drawing_options or {}, Bot.IGNORE_WHITE,
        )
        self.bot.skip_first_color = bool(recipe.skip_first_color)
        self._refresh_drawing_widgets()
        self._refresh_option_widgets()
        self._sync_env_ui()

    def _select_target_id(self, recipe_id: str) -> None:
        for index in range(self._target_combo.count()):
            if self._target_combo.itemData(index) == recipe_id:
                self._target_combo.setCurrentIndex(index)
                return
        self._target_combo.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    def load_config(self) -> None:
        config = pyaint_config.load_config(self._config_path)
        self.profile = Profile.from_config(config)
        self.bot.profile = self.profile
        self.tools = pyaint_config.split_preferences(config)
        self.tools.setdefault("pause_key", "p")

        try:
            recipe = get_recipe(self.profile.target)
            self._select_target_id(recipe.id)
        except Exception:
            pass

        self.bot.pause_key = str(self.tools.get("pause_key", "p"))
        self._pause_edit.setText(self.bot.pause_key)

        settings = self.tools.get("drawing_settings", {})
        self.bot.settings = [
            settings.get("delay", 0.1),
            settings.get("pixel_size", 12),
            settings.get("jump_delay", 0.5),
        ]
        self.bot.jump_threshold = int(settings.get("jump_threshold", 5))
        self._jump_threshold.setValue(self.bot.jump_threshold)

        options = self.tools.get("drawing_options", {})
        self.draw_options = 0
        if options.get("ignore_white_pixels", True):
            self.draw_options |= Bot.IGNORE_WHITE

        self.bot.skip_first_color = bool(self.tools.get("skip_first_color", False))
        mode = self.tools.get("draw_mode", Bot.LAYERED)
        self._mode = mode if mode in (Bot.SLOTTED, Bot.LAYERED) else Bot.LAYERED

        last_url = self.tools.get("last_image_url", "")
        if last_url:
            self._last_url = last_url
            self._url_edit.setText(last_url)

        self._theme_mode = str(self.tools.get("theme", "auto"))
        if self._theme_mode not in theme.THEME_MODES:
            self._theme_mode = "auto"
        self._theme_combo.blockSignals(True)
        index = self._theme_combo.findData(self._theme_mode)
        self._theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self._theme_combo.blockSignals(False)

        self._restore_environment()
        self._refresh_drawing_widgets()
        self._refresh_option_widgets()
        self._sync_env_ui()
        self._refresh_detection_status()
        self._apply_theme()

    def _restore_environment(self) -> None:
        palette = self.profile["Palette"]
        try:
            if palette.get("box") and palette.get("rows") and palette.get("cols"):
                box = palette["box"]
                self.bot.init_palette(
                    pbox=(box[0], box[1], box[2] - box[0], box[3] - box[1]),
                    prows=palette["rows"], pcols=palette["cols"],
                )
            elif palette.get("color_coords"):
                colors_pos = {
                    tuple(map(int, key[1:-1].split(", "))): tuple(value)
                    for key, value in palette["color_coords"].items()
                }
                self.bot.init_palette(colors_pos=colors_pos)
        except Exception as e:
            log.info(f"[Config] palette restore failed: {e}")
        try:
            if self.profile["Canvas"].get("box"):
                self.bot.init_canvas(self.profile["Canvas"]["box"])
        except Exception as e:
            log.info(f"[Config] canvas restore failed: {e}")

    def _store_drawing_settings(self) -> None:
        settings = self.tools.setdefault("drawing_settings", {})
        settings["delay"] = self.bot.settings[0]
        settings["pixel_size"] = self.bot.settings[1]
        settings["jump_delay"] = self.bot.settings[2]
        settings["jump_threshold"] = self.bot.jump_threshold

    def _store_drawing_options(self) -> None:
        options = self.tools.setdefault("drawing_options", {})
        options["ignore_white_pixels"] = bool(self.draw_options & Bot.IGNORE_WHITE)

    def _save_config(self) -> None:
        if self._initializing:
            return
        self.tools["pause_key"] = self.bot.pause_key
        self.tools["skip_first_color"] = bool(self.bot.skip_first_color)
        self.tools["draw_mode"] = self._mode
        self.tools["theme"] = self._theme_mode
        if self._last_url:
            self.tools["last_image_url"] = self._last_url
        payload = pyaint_config.build_payload(self.tools, self.profile)
        if not pyaint_config.save_config(self._config_path, payload):
            log.info(f"Failed to save config to {self._config_path}")

    # ------------------------------------------------------------------
    # Widget <-> state sync
    # ------------------------------------------------------------------
    def _refresh_drawing_widgets(self) -> None:
        for field, value in zip(self._setters, self.bot.settings):
            field.set_value(value)
        mode_index = self._mode_combo.findData(self._mode)
        if mode_index >= 0:
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(mode_index)
            self._mode_combo.blockSignals(False)

    def _refresh_option_widgets(self) -> None:
        self._chk_ignore.setChecked(bool(self.draw_options & Bot.IGNORE_WHITE))
        self._chk_skip.setChecked(bool(self.bot.skip_first_color))

    def _sync_env_ui(self) -> None:
        recipe = get_recipe(self.profile.target)
        used = set(recipe.tools)
        any_visible = False
        for control in self._tool_controls:
            visible = control.name in used
            control.setVisible(visible)
            control.refresh()
            any_visible = any_visible or visible
        self._mspaint_box.setVisible(bool(recipe.supports_mspaint_mode))
        any_visible = any_visible or bool(recipe.supports_mspaint_mode)
        self._tools_section.setVisible(any_visible)
        self._chk_mspaint.setChecked(bool(self.profile.mspaint_mode.get("enabled")))
        self._mspaint_delay.setValue(int(float(self.profile.mspaint_mode.get("delay", 0.5)) * 1000))
        self._mspaint_delay.setEnabled(self._chk_mspaint.isChecked())
        self._refresh_readiness()

    def _refresh_detection_status(self) -> None:
        canvas = self.profile.canvas_rect()
        palette = self.profile.palette_rect()
        parts = []
        if canvas:
            parts.append(f"canvas {canvas}")
        if palette:
            parts.append(f"palette {palette}")
        self._detection_label.setText(
            "Detected: " + "; ".join(parts) if parts else "No regions detected yet — run Auto-detect or teach it manually."
        )
        self._refresh_readiness()

    def _refresh_readiness(self) -> None:
        recipe = get_recipe(self.profile.target)
        environment_ready = (
            getattr(self.bot, "_canvas", None) is not None
            and getattr(self.bot, "_palette", None) is not None
        )
        image_ready = self._has_image()
        self._readiness.update_steps(recipe.name, environment_ready, image_ready)
        if not self._busy:
            self._btn_start.setEnabled(environment_ready and image_ready)

    @staticmethod
    def _detection_checklist(detection) -> str:
        lines = []
        if getattr(detection, "canvas", None):
            lines.append(f"✓ Canvas {detection.canvas}")
        else:
            lines.append("✗ Canvas not found")
        if (
            getattr(detection, "palette", None)
            and detection.palette_rows
            and detection.palette_cols
        ):
            lines.append(
                f"✓ Palette {detection.palette_rows}×{detection.palette_cols} {detection.palette}"
                " — dots mark sampled centres"
            )
        else:
            lines.append("✗ Palette not found")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Setting slots
    # ------------------------------------------------------------------
    def _on_setting_changed(self, index: int, value: float) -> None:
        if self._initializing:
            return
        self.bot.settings[index] = value
        self._store_drawing_settings()
        self._save_config()

    def _on_mode_changed(self, _index: int) -> None:
        if self._initializing:
            return
        self._mode = self._mode_combo.currentData()
        self._save_config()

    def _on_options_changed(self) -> None:
        if self._initializing:
            return
        self.draw_options = 0
        if self._chk_ignore.isChecked():
            self.draw_options |= Bot.IGNORE_WHITE
        self._store_drawing_options()
        self._save_config()

    def _on_skip_changed(self, checked: bool) -> None:
        if self._initializing:
            return
        self.bot.skip_first_color = bool(checked)
        self._save_config()

    def _on_tool_controls_changed(self) -> None:
        if not self._initializing:
            self._save_config()

    def _on_mspaint_toggled(self, checked: bool) -> None:
        if self._initializing:
            return
        self.profile.mspaint_mode["enabled"] = bool(checked)
        self._mspaint_delay.setEnabled(bool(checked))
        self._save_config()

    def _on_mspaint_delay(self, milliseconds: int) -> None:
        if self._initializing:
            return
        self.profile.mspaint_mode["delay"] = milliseconds / 1000.0
        self._save_config()

    def _on_pause_key_changed(self, text: str) -> None:
        if self._initializing:
            return
        self.bot.pause_key = text.strip() or "p"
        self._save_config()

    def _on_jump_threshold_changed(self, value: int) -> None:
        if self._initializing:
            return
        self.bot.jump_threshold = int(value)
        self._store_drawing_settings()
        self._save_config()

    def _on_theme_changed(self, _index: int) -> None:
        if self._initializing:
            return
        self._theme_mode = self._theme_combo.currentData() or "auto"
        self.tools["theme"] = self._theme_mode
        self._apply_theme()
        self._save_config()

    def _on_system_scheme_changed(self, _scheme) -> None:
        if self._theme_mode == "auto":
            self._apply_theme()

    def _apply_theme(self) -> None:
        """Re-resolve tokens, restyle the app, and recolour the icons."""
        self.tokens = theme.resolve_tokens(self._theme_mode)
        app = QApplication.instance()
        if app is not None:
            theme.apply(app, self.tokens)
        self._refresh_icons()

    def _refresh_icons(self) -> None:
        fg = self.tokens["fg"]
        muted = self.tokens["fg_muted"]
        accent_fg = self.tokens["accent_fg"]
        for button, (_, icon_name) in zip(self._activity_buttons, _PANELS):
            button.setIcon(icon(icon_name, muted, 22))
        self._btn_precompute.setIcon(icon("download", fg, 16))
        self._btn_test.setIcon(icon("zap", fg, 16))
        self._btn_simple.setIcon(icon("play", fg, 16))
        self._btn_start.setIcon(icon("play", accent_fg, 16))
        self._btn_pause.setIcon(icon("pause", fg, 16))
        self._btn_stop.setIcon(icon("stop", fg, 16))

    # ------------------------------------------------------------------
    # Threading / tasks
    # ------------------------------------------------------------------
    def _emit_progress(self, completed: int, total: int, eta: float) -> None:
        # Called from the drawing worker thread; Qt queues this onto the loop.
        self.signals.progress.emit(int(completed), int(total), float(eta))

    def _on_progress(self, completed: int, total: int, eta: float) -> None:
        if total > 0:
            self._progress.setValue(int(100 * completed / total))
        self._overlay.update_progress(completed, total, eta)
        self._set_status(f"Drawing {completed}/{total} strokes")

    def _start_task(
        self, name: str, work, minimize: bool = False, overlay: bool = False, interruptible: bool = True
    ) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_running(True, interruptible=interruptible)
        self._progress.setValue(0)
        self._set_status(f"{name}…")
        if overlay:
            self._overlay.show_overlay(f"{name}…", self.bot.pause_key or "p")
        if minimize:
            self.showMinimized()

        def runner():
            try:
                work()
            except Exception as exc:  # noqa: BLE001 - surface any task failure
                log.info(f"[{name}] error: {exc}")
                traceback.print_exc()
                self.signals.status.emit(f"{name} failed: {exc}")
            finally:
                self.signals.finished.emit(name)

        threading.Thread(target=runner, daemon=True).start()

    def _on_task_finished(self, _name: str) -> None:
        self._busy = False
        self._set_running(False)
        self._overlay.hide_overlay()
        if self.isMinimized():
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _set_running(self, running: bool, interruptible: bool = True) -> None:
        for button in (self._btn_precompute, self._btn_test, self._btn_simple, self._btn_start, self._auto_btn):
            button.setEnabled(not running)
        self._btn_stop.setEnabled(running and interruptible)
        self._btn_pause.setEnabled(running and interruptible)
        if self._detection_view is not None:
            self._retry_detection_btn.setEnabled(not running)
            self._cancel_detection_btn.setEnabled(not running)
            self._apply_detection_btn.setEnabled(not running and self._detection_result is not None)
        if not running:
            self._refresh_readiness()

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)
        log.info(text)

    def _toggle_pause(self) -> None:
        if self.bot.drawing:
            self.bot.paused = not self.bot.paused
            self._set_status("Paused" if self.bot.paused else "Resumed")

    def _stop_draw(self) -> None:
        self.bot.terminate = True
        self._set_status("Stopping…")

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------
    def _load_default_image(self) -> None:
        if os.path.exists(self._imname):
            self._set_image_path(self._imname)
        else:
            self._preview.set_placeholder("Drop an image here or load one from the Image panel.")

    def _on_load_clicked(self) -> None:
        text = self._url_edit.text().strip()
        if not text:
            self._open_file()
        elif text.lower().startswith(("http://", "https://")):
            self._start_task("Download image", lambda: self._download_and_show(text), interruptible=False)
        elif os.path.exists(text):
            self._set_image_path(text)
        else:
            self._set_status(f"File not found: {text}")

    def _download_and_show(self, url: str) -> None:
        path = self._fetch_remote_image(url)
        self._last_url = url
        self.tools["last_image_url"] = url
        self._save_config()
        self.signals.image_ready.emit(path)

    def _fetch_remote_image(self, url: str, timeout: int = 15, retries: int = 3) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            },
        )
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    content_type = response.headers.get("content-type", "").lower()
                    if not content_type.startswith("image/"):
                        raise ValueError(f"URL is not an image (content-type: {content_type})")
                    fd, temp_path = tempfile.mkstemp(suffix=".png")
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(response.read())
                    return temp_path
            except urllib_error.HTTPError as exc:
                if exc.code == 429 and attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc
            except urllib_error.URLError as exc:
                if attempt == retries - 1:
                    raise ValueError(f"Network error: {exc.reason}") from exc
        raise ValueError("Failed to fetch image")

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open image", paths.PROJECT_ROOT,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)",
        )
        if path:
            self._last_url = ""
            self._set_image_path(path)

    def _set_image_path(self, path: str) -> None:
        try:
            image = Image.open(path)
        except Exception as exc:
            self._set_status(f"Could not open image: {exc}")
            return
        self._imname = path
        self._preview.set_pixmap(pil_to_qpixmap(image))
        self._show_image_tab()
        self._image_info.setText(f"{os.path.basename(path)} — {image.width}×{image.height}px")
        canvas = getattr(self.bot, "_canvas", None)
        if canvas is not None:
            has_cache, _ = self.bot.get_cached_status(path, flags=self.draw_options, mode=self._mode)
            self._set_status("Cached result available" if has_cache else "No cache — will process live")
        else:
            self._set_status("Image loaded. Detect or teach the canvas next.")
        self._refresh_readiness()

    # Drag & drop
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls() and event.mimeData().urls()[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self._set_image_path(urls[0].toLocalFile())

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------
    def auto_detect(self) -> None:
        if self._detecting:
            return
        recipe = get_recipe(self.profile.target)
        if not recipe.detection:
            QMessageBox.information(
                self, self.title,
                f'No auto-detection configured for "{recipe.name}".\n\nUse "Teach manually" to set it up.',
            )
            return
        self._detecting = True
        self._pending_recipe = recipe
        self._detection_result = None
        self._detection_image = None
        self.showNormal()
        self.raise_()
        self.activateWindow()
        for button in (self._auto_btn, self._btn_start, self._btn_test, self._btn_simple, self._btn_precompute):
            button.setEnabled(False)
        self._countdown_banner.start(seconds=4)

    def _begin_capture(self) -> None:
        self._countdown_banner.stop()
        self.showMinimized()
        # Let the minimize take effect before grabbing the screen.
        QTimer.singleShot(400, self._finish_auto_detect)

    def _cancel_auto_detect(self) -> None:
        self._countdown_banner.stop()
        self._detecting = False
        self._set_running(False)
        self._set_status("Auto-detect cancelled.")

    def _finish_auto_detect(self) -> None:
        try:
            recipe = self._pending_recipe
            image = self.bot.capture_screen()
            detection = detect_target(recipe, image)
            self.showNormal()
            self.raise_()
            self.activateWindow()
            log.info(f"[AutoDetect] {recipe.id}: canvas={detection.canvas} palette={detection.palette}")
            self._present_detection(image, detection)
            self._set_status(
                "Review the detection (white dots = palette cell centres), then Apply or Cancel."
            )
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.showNormal()
            QMessageBox.critical(self, self.title, f"Auto-detect failed: {exc}")
        finally:
            self._detecting = False
            self._set_running(False)

    def _present_detection(self, image, detection) -> None:
        """Show the detection result in its own tab, leaving the image tab alone."""
        self._detection_image = image
        self._ensure_detection_tab()
        if detection:
            self._detection_result = detection
            try:
                annotated = annotate_detection(image, detection)
            except Exception as exc:  # noqa: BLE001
                log.info(f"[AutoDetect] annotation failed: {exc}")
                annotated = image.convert("RGB")
            self._detection_preview.set_pixmap(pil_to_qpixmap(annotated))
            self._detection_summary.setText(self._detection_checklist(detection))
        else:
            self._detection_result = None
            self._detection_preview.set_pixmap(pil_to_qpixmap(image.convert("RGB")))
            self._detection_summary.setText(
                "No regions found. Make sure the canvas is blank and the target "
                "app is maximized on the primary monitor at 100% scaling, then "
                "Retry — or Cancel and teach it manually."
            )
        self._apply_detection_btn.setEnabled(self._detection_result is not None)
        self._tabs.setCurrentWidget(self._detection_view)

    def _apply_detection(self) -> None:
        if not self._detection_result:
            return
        applied = self.bot.apply_detection(self._detection_result, image=self._detection_image)
        self._sync_env_ui()
        self._refresh_detection_status()
        self._store_drawing_settings()
        self._store_drawing_options()
        self._save_config()
        self._set_status(f"Auto-detect applied ({', '.join(applied) or 'nothing'}).")
        palette = getattr(self.bot, "_palette", None)
        if palette is not None and len(palette.colors) <= 1:
            QMessageBox.warning(
                self,
                self.title,
                "The palette sampled as a single colour — the target app may have "
                "been covered when the region was captured. Re-run Auto-detect "
                "with the target app in front, or teach the palette manually.",
            )
        self._show_image_tab()

    def _cancel_detection(self) -> None:
        self._set_status("Auto-detect cancelled.")
        self._show_image_tab()

    # ------------------------------------------------------------------
    # Drawing actions
    # ------------------------------------------------------------------
    def _has_image(self) -> bool:
        return bool(self._imname) and os.path.exists(self._imname)

    def _require_image(self) -> bool:
        if not self._has_image():
            QMessageBox.warning(self, self.title, "Load an image first.")
            return False
        return True

    def _resolve_cmap(self):
        has_cache, cache_file = self.bot.get_cached_status(self._imname, flags=self.draw_options, mode=self._mode)
        if has_cache:
            data = self.bot.load_cached(cache_file)
            if data:
                return data["cmap"]
        return self.bot.process(self._imname, flags=self.draw_options, mode=self._mode)

    def _on_precompute(self) -> None:
        if not self._require_image():
            return
        self._start_task("Prepare & cache", self._precompute_work, interruptible=False)

    def _precompute_work(self) -> None:
        cache_file = self.bot.precompute(self._imname, flags=self.draw_options, mode=self._mode)
        data = self.bot.load_cached(cache_file)
        if data:
            eta = self.bot.estimate_drawing_time(data["cmap"])
            self.signals.status.emit(f"Cached — estimated drawing time {eta}.")
        else:
            self.signals.status.emit("Cached the stroke map.")

    def _on_test_draw(self) -> None:
        if not self._require_image():
            return
        self._start_task("Test draw", self._test_draw_work, minimize=True, overlay=True)

    def _test_draw_work(self) -> None:
        cmap = self._resolve_cmap()
        total = sum(len(lines) for lines in cmap.values())
        self.bot.terminate = False
        self.bot.paused = False
        self.bot.drawing = False
        self.bot.draw_state = {"color_idx": 0, "line_idx": 0, "segment_idx": 0, "current_color": None, "was_paused": False}
        self.signals.status.emit(f"Test drawing {min(20, total)} lines.")
        time.sleep(1.0)
        result = self.bot.test_draw(cmap, max_lines=min(20, total))
        self.signals.status.emit("Test draw completed." if result == "success" else f"Test draw: {result}.")

    def _on_simple_test(self) -> None:
        canvas = getattr(self.bot, "_canvas", None)
        if canvas is None:
            QMessageBox.warning(self, self.title, "Canvas not configured. Run Auto-detect, or teach it manually.")
            return
        self._start_task("Simple test draw", self.bot.simple_test_draw, minimize=True, interruptible=False)

    def _on_start(self) -> None:
        if not self._require_image():
            return
        if getattr(self.bot, "_canvas", None) is None:
            QMessageBox.warning(self, self.title, "Canvas not configured. Run Auto-detect, or teach it manually.")
            return
        palette = getattr(self.bot, "_palette", None)
        if palette is None:
            QMessageBox.warning(self, self.title, "Palette not configured. Run Auto-detect, or teach it manually.")
            return
        if len(palette.colors) <= 1:
            QMessageBox.warning(
                self,
                self.title,
                "The palette has only one distinct colour, so the whole image "
                "would be drawn in that colour. Re-run Auto-detect with the "
                "target app in front, or teach the palette manually.",
            )
            return
        QMessageBox.information(
            self, self.title,
            f"Press ESC to stop.\nPress {self.bot.pause_key or 'p'} to pause/resume.",
        )
        self._start_task("Drawing", self._draw_work, minimize=True, overlay=True)

    def _draw_work(self) -> None:
        start = time.time()
        cmap = self._resolve_cmap()
        eta = self.bot.estimate_drawing_time(cmap)
        self.signals.status.emit(f"Drawing — estimated {eta}. Switch to the target app now.")
        time.sleep(3)
        self.bot.terminate = False
        self.bot.paused = False
        self.bot.drawing = False
        self.bot.draw_state = {"color_idx": 0, "line_idx": 0, "segment_idx": 0, "current_color": None, "was_paused": False}
        result = self.bot.draw(cmap)
        elapsed = time.time() - start
        actual = self.bot._format_time(elapsed)
        if result == "success":
            self.signals.status.emit(f"Finished — {actual} (estimated {eta}).")
        elif result == "terminated":
            self.signals.status.emit(f"Stopped — {actual}.")
        else:
            self.signals.status.emit(f"Drawing result: {result}.")
        self.bot.terminate = False

    # ------------------------------------------------------------------
    # Region redraw
    # ------------------------------------------------------------------
    def pick_region(self):
        from pyaint.ui.capture import pick_points

        if getattr(self.bot, "_canvas", None) is None:
            QMessageBox.warning(self, self.title, "Canvas not configured. Run Auto-detect, or teach it manually.")
            return
        try:
            result = pick_points(self, 2, "Click the UPPER-LEFT then LOWER-RIGHT corner of the region.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.title, f"Region pick failed: {exc}")
            return
        if not result or len(result.points) < 2:
            self._set_status("Region selection cancelled.")
            return
        (x1, y1), (x2, y2) = result.points
        box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        self._redraw_region = box
        self._region_label.setText(f"Region: ({box[0]}, {box[1]}) → ({box[2]}, {box[3]})")
        self._set_status("Region selected. Click 'Draw region'.")

    def _on_draw_region(self) -> None:
        if self._redraw_region is None:
            QMessageBox.warning(self, self.title, "Pick a region first.")
            return
        self._start_task("Region redraw", self._redraw_work, minimize=True, overlay=True)

    def _redraw_work(self) -> None:
        region = self._redraw_region
        image_region = self._canvas_to_image_region(region)
        target = (region[0], region[1], region[2] - region[0], region[3] - region[1])
        cmap = self.bot.process_region(self._imname, image_region, flags=self.draw_options, mode=self._mode, canvas_target=target)
        if not cmap:
            self.signals.status.emit("No drawable content in the selected region.")
            return
        self.signals.status.emit("Redrawing region — switch to the target app.")
        time.sleep(3)
        self.bot.terminate = False
        self.bot.paused = False
        self.bot.drawing = False
        self.bot.draw_state = {"color_idx": 0, "line_idx": 0, "segment_idx": 0, "current_color": None, "was_paused": False}
        result = self.bot.draw(cmap)
        self.signals.status.emit(f"Region redraw: {result}.")
        self.bot.terminate = False

    def _canvas_to_image_region(self, canvas_region):
        canvas = self.bot._canvas
        cx, cy, cw, ch = canvas
        x1, y1, x2, y2 = canvas_region
        try:
            image = Image.open(self._imname)
            from pyaint import utils

            fit_w, fit_h = utils.adjusted_img_size(image, (cw, ch))
            offset_x = cx + (cw - fit_w) // 2
            offset_y = cy + (ch - fit_h) // 2
            sx = image.width / fit_w
            sy = image.height / fit_h
            ix1 = max(0, int((x1 - offset_x) * sx))
            iy1 = max(0, int((y1 - offset_y) * sy))
            ix2 = min(image.width, int((x2 - offset_x) * sx))
            iy2 = min(image.height, int((y2 - offset_y) * sy))
            if ix2 <= ix1 or iy2 <= iy1:
                raise ValueError("region falls outside the drawn image")
            return (ix1, iy1, ix2, iy2)
        except Exception as exc:  # noqa: BLE001
            log.info(f"[Redraw] falling back to raw region: {exc}")
            return canvas_region

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def open_setup(self) -> None:
        from pyaint.ui.setup_dialog import SetupDialog

        recipe = get_recipe(self.profile.target)
        dialog = SetupDialog(self, self.bot, self.profile, required_tools=recipe.tools)
        if dialog.exec():
            self.bot.profile = self.profile
            self._sync_env_ui()
            self._refresh_detection_status()
            self._store_drawing_settings()
            self._store_drawing_options()
            self._save_config()
            self._set_status("Setup saved.")

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------
    def _on_reset_config(self) -> None:
        answer = QMessageBox.question(
            self, self.title,
            "Reset to defaults? This deletes config.json and all taught positions.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if os.path.exists(self._config_path):
                os.remove(self._config_path)
            self._set_status("Config removed. Restart Pyaint to use defaults.")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Could not remove config: {exc}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _show_panel(self, index: int) -> None:
        self._panels.setCurrentIndex(index)
        self._side_title.setText(_PANELS[index][0].upper())

    def closeEvent(self, event):  # noqa: N802
        self._overlay.hide_overlay()
        self._countdown_banner.stop()
        try:
            cache_dir = os.path.join(paths.PROJECT_ROOT, "cache")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
        except Exception as exc:  # noqa: BLE001
            log.info(f"Could not clean cache: {exc}")
        event.accept()


def run(bot: Bot) -> int:
    """Create the application and show the main window (blocking)."""
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Pyaint")
    from pyaint.ui import theme

    theme.apply(app, theme.resolve_tokens("auto"))
    window = MainWindow(bot)
    window.show()
    return app.exec()
