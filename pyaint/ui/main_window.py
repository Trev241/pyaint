"""VS Code-inspired main window (PySide6).

This is the Qt replacement for the historical Tk ``Window``. It owns the
shared :class:`~pyaint.profile.Profile`, persists ``config.json``, and runs
long tasks on worker threads. Progress is delivered by ``Bot`` through a
callback that emits a Qt signal, so all UI updates happen on the main thread.
"""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
import tempfile
import threading
import time
import traceback
import urllib.error as urllib_error
import urllib.parse
import urllib.request

from typing import Optional

from PIL import Image
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QApplication,
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
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyaint import config as pyaint_config
from pyaint import image_search
from pyaint import paths
from pyaint.bot import Bot
from pyaint.locators import detect_target
from pyaint.log import log
from pyaint.palette import DEFAULT_METRIC, METRIC_CIEDE2000, METRIC_RGB, METRICS
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
from pyaint.ui.overlay import DetectionOverlay, ProgressOverlay
from pyaint.ui.widgets import (
    CheckBox,
    CollapsibleSection,
    ImagePreview,
    MasonryGallery,
    NoticeBanner,
    ReadinessStrip,
    Section,
    SliderField,
    ToolControls,
    accepts_image_drop,
    local_path_from_mime,
    pil_to_qpixmap,
    raw_image_from_mime,
    remote_source_from_mime,
)
from pyaint.validation import validate_recipe


class UiSignals(QObject):
    """Cross-thread signals: workers emit, the main thread consumes."""

    progress = Signal(int, int, float)
    status = Signal(str)
    finished = Signal(str)
    image_ready = Signal(str)
    message = Signal(str)


class WheelGuard(QObject):
    """Forward wheel events over value widgets to their scroll area.

    Without this, hovering a slider, spinbox, or combobox while scrolling the
    settings panel changes the control's value instead of scrolling the panel.
    """

    def __init__(self, scroll: QScrollArea, parent=None):
        super().__init__(parent)
        self._scroll = scroll

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            QApplication.sendEvent(self._scroll.viewport(), event)
            return True
        return super().eventFilter(obj, event)


_PATH_LIKE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|\.{1,2}[\\/]|[\\/]|~)")
#: Image-search hosts that wrap the real file in a redirect/page URL.
_REDIRECT_HOSTS = ("google.", "bing.", "duckduckgo.", "yandex.", "search.brave.")


def _looks_like_path(text: str) -> bool:
    """True when ``text`` looks like a filesystem path, not a search query."""
    return bool(_PATH_LIKE.match(text))


def _decode_data_uri(uri: str) -> bytes:
    """Decode an ``image/...`` data URI into raw bytes."""
    header, separator, payload = uri.partition(",")
    if not separator:
        raise ValueError("malformed data URI")
    if ";base64" in header.lower():
        return base64.b64decode(payload)
    return urllib.parse.unquote_to_bytes(payload)


def _unwrap_image_redirect(url: str) -> str:
    """Pull the real image URL out of a search-engine result/redirect URL."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if not parsed.query or not any(marker in host for marker in _REDIRECT_HOSTS):
        return url
    params = urllib.parse.parse_qs(parsed.query)
    for key in ("imgurl", "mediaurl", "image_url", "url"):
        values = params.get(key)
        if values and values[0].startswith(("http://", "https://")):
            return values[0]
    return url


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
        self._pending_source = None
        self._search_query = ""
        self._search_continue = None
        self._search_generation = 0
        self._search_loading = False
        self._provider = image_search.DEFAULT_PROVIDER
        self._redraw_region = None
        self._recipes = []
        self._recipes_by_name = {}
        self._imname = os.path.join(paths.PROJECT_ROOT, "assets", "sample.png")
        self._detecting = False
        self._detection_result = None
        self._detection_image = None
        # Per-target environment snapshots, so switching targets is instant.
        self._environments = {}
        # Per-target drawing settings/options, so each app keeps its own tuning.
        self._drawing_by_target = {}
        self._last_error = None

        self.signals = UiSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.status.connect(self._set_status)
        self.signals.finished.connect(self._on_task_finished)
        self.signals.image_ready.connect(self._set_image_path)
        self.bot.progress_callback = self._emit_progress

        # Resolve the theme before building widgets so the first paint is right.
        self._theme_mode = "auto"
        try:
            self._theme_mode = str(
                pyaint_config.load_config(self._config_path).get("theme", "auto")
            )
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
        self._detection_overlay = DetectionOverlay()
        self._detection_overlay.confirmed.connect(self._apply_detection)
        self._detection_overlay.retry_requested.connect(self._retry_detection)
        self._detection_overlay.teach_requested.connect(self._teach_detection)
        self._detection_overlay.dismissed.connect(self._dismiss_detection)
        self.signals.message.connect(self._overlay.show_message)
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
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Always-visible target switcher, then the persistent notice banner.
        root.addWidget(self._build_topbar())
        self._notice = NoticeBanner()
        root.addWidget(self._notice)

        self._countdown_banner = CountdownBanner()
        self._countdown_banner.captured.connect(self._begin_capture)
        self._countdown_banner.cancelled.connect(self._cancel_auto_detect)
        root.addWidget(self._countdown_banner)

        # Hub: the preview is the hero, settings live in the inspector.
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_content(), 1)
        body.addWidget(self._build_inspector())
        root.addLayout(body, 1)

        root.addWidget(self._build_action_bar())
        self._build_statusbar()

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        label = QLabel("Drawing in")
        label.setObjectName("TopBarLabel")
        layout.addWidget(label)

        self._target_combo = QComboBox()
        self._target_combo.setMinimumWidth(200)
        self._target_combo.setToolTip("Choose the app Pyaint draws in")
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        layout.addWidget(self._target_combo)

        self._auto_btn = QPushButton("Auto-detect")
        self._auto_btn.setToolTip("Find the canvas and palette from a screenshot")
        self._auto_btn.clicked.connect(self.auto_detect)
        layout.addWidget(self._auto_btn)

        self._teach_btn = QPushButton("Set up\u2026")
        self._teach_btn.setToolTip("Teach Pyaint where the canvas and palette are")
        self._teach_btn.clicked.connect(self.open_setup)
        layout.addWidget(self._teach_btn)

        layout.addStretch(1)
        self._env_chip = QLabel("Not set up")
        self._env_chip.setObjectName("EnvChip")
        self._env_chip.setToolTip("Canvas and palette status")
        layout.addWidget(self._env_chip)
        return bar

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

    def _build_inspector(self) -> QWidget:
        side = QFrame()
        side.setObjectName("SideBar")
        side.setFixedWidth(320)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        title = QLabel("SETTINGS")
        title.setObjectName("SideBarTitle")
        side_layout.addWidget(title)

        scroll, layout = self._scroll_panel()

        env = Section(
            "Environment",
            "Where Pyaint finds the canvas and palette. Switch targets above.",
        )
        self._detection_label = QLabel("No regions detected yet.")
        self._detection_label.setObjectName("SectionHint")
        self._detection_label.setWordWrap(True)
        env.add(self._detection_label)
        needs = QLabel(
            "Auto-detect needs a blank canvas, the app maximized on the primary "
            "monitor, at 100% display scaling."
        )
        needs.setObjectName("SectionHint")
        needs.setWordWrap(True)
        env.add(needs)
        layout.insertWidget(layout.count() - 1, env)

        mode = Section("Stroke mode", "How the image is turned into strokes.")
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Layered (fewer strokes)", Bot.LAYERED)
        self._mode_combo.addItem("Slotted (exact runs)", Bot.SLOTTED)
        self._mode_combo.addItem("Outline (outline and fill)", Bot.OUTLINE)
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
        self._mode_combo.setItemData(
            2,
            "Outlines regions to be filled in later, fastest",
            Qt.ToolTipRole,
        )
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode.add(self._mode_combo)
        self._stroke_distance = SliderField("Stroke distance", 1, 50, 1, 1)
        self._stroke_distance.setToolTip(
            "Outline only: how many traced boundary cells each stroke covers. "
            "1 draws every traced cell separately; higher values join them into "
            "longer, fewer strokes."
        )
        self._stroke_distance.changed.connect(self._on_stroke_distance_changed)
        mode.add(self._stroke_distance)
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
            field.changed.connect(
                lambda value, i=index: self._on_setting_changed(i, value)
            )
            drawing.add(field)

        trigger_row = QHBoxLayout()
        trigger_label = QLabel("Trigger distance (px)")
        trigger_label.setObjectName("FieldHint")
        self._jump_threshold = QSpinBox()
        self._jump_threshold.setRange(1, 200)
        self._jump_threshold.setValue(5)
        self._jump_threshold.setToolTip(
            "Cursor jumps longer than this get the pause above"
        )
        self._jump_threshold.valueChanged.connect(self._on_jump_threshold_changed)
        trigger_row.addWidget(trigger_label)
        trigger_row.addStretch(1)
        trigger_row.addWidget(self._jump_threshold)
        drawing.add_layout(trigger_row)
        layout.insertWidget(layout.count() - 1, drawing)

        options = Section("Options")
        metric_row = QHBoxLayout()
        metric_label = QLabel("Colour matching")
        metric_label.setObjectName("FieldHint")
        self._metric_combo = QComboBox()
        self._metric_combo.addItem("Perceptual (CIEDE2000)", METRIC_CIEDE2000)
        self._metric_combo.addItem("Legacy (squared RGB)", METRIC_RGB)
        self._metric_combo.setItemData(
            0,
            "Matches colours by perceived difference in CIELAB; picks the "
            "visually closest swatch (default).",
            Qt.ToolTipRole,
        )
        self._metric_combo.setItemData(
            1,
            "Original squared-distance RGB matching; kept for comparison.",
            Qt.ToolTipRole,
        )
        self._metric_combo.currentIndexChanged.connect(self._on_metric_changed)
        metric_row.addWidget(metric_label)
        metric_row.addStretch(1)
        metric_row.addWidget(self._metric_combo)
        options.add_layout(metric_row)
        self._chk_ignore = CheckBox("Ignore white pixels")
        self._chk_ignore.setToolTip("Skip pure-white areas, e.g. a blank background")
        self._chk_transparent = CheckBox("Ignore transparent pixels")
        self._chk_transparent.setToolTip(
            "Skip see-through areas of a PNG instead of painting them black."
        )
        self._chk_skip = CheckBox("Skip first color")
        self._chk_skip.setToolTip(
            "Don't paint the first colour — useful when it is already on the canvas."
        )
        self._chk_ignore.toggled.connect(self._on_options_changed)
        self._chk_transparent.toggled.connect(self._on_options_changed)
        self._chk_skip.toggled.connect(self._on_skip_changed)
        for box in (self._chk_ignore, self._chk_transparent, self._chk_skip):
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
            control = ToolControls(
                name, lambda n=name: self.profile[n], supports_delay=supports_delay
            )
            control.changed.connect(self._on_tool_controls_changed)
            tools.add(control)
            self._tool_controls.append(control)
        self._mspaint_box = QWidget()
        mspaint_layout = QVBoxLayout(self._mspaint_box)
        mspaint_layout.setContentsMargins(0, 0, 0, 0)
        mspaint_layout.setSpacing(2)
        self._chk_mspaint = CheckBox("MS Paint double-click")
        self._chk_mspaint.setToolTip(
            "Some palettes need a double-click to select a colour"
        )
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

        diagnostics = CollapsibleSection("Diagnostics")
        diag_note = QLabel(
            "Calibration aids. For normal use, just press Start drawing."
        )
        diag_note.setObjectName("SectionHint")
        diag_note.setWordWrap(True)
        diagnostics.add(diag_note)
        self._btn_precompute = self._tool_button(
            "Prepare & cache",
            "download",
            self._on_precompute,
            "Save the stroke map so repeat runs skip processing (drawing time is unchanged)",
        )
        self._btn_test = self._tool_button(
            "Test draw", "zap", self._on_test_draw, "Draw the first 20 strokes"
        )
        self._btn_simple = self._tool_button(
            "Brush test",
            "play",
            self._on_simple_test,
            "Draw 5 lines to tune the brush size",
        )
        for button in (self._btn_precompute, self._btn_test, self._btn_simple):
            diagnostics.add(button)

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
        diagnostics.add(redraw)
        layout.insertWidget(layout.count() - 1, diagnostics)

        advanced = CollapsibleSection("Advanced")
        self._build_advanced_into(advanced)
        layout.insertWidget(layout.count() - 1, advanced)

        side_layout.addWidget(scroll, 1)
        self._guard_scroll_wheel(scroll)
        return side

    def _guard_scroll_wheel(self, scroll: QScrollArea) -> None:
        """Make wheel scrolling move the panel, not the control under the cursor."""
        guard = WheelGuard(scroll, self)
        for widget in scroll.findChildren(QWidget):
            if isinstance(widget, (QComboBox, QSpinBox, QSlider)):
                widget.installEventFilter(guard)

    def _build_advanced_into(self, container) -> None:
        appearance = Section(
            "Appearance", "Follow the system theme or choose one explicitly."
        )
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

    def _build_content(self) -> QWidget:
        """The Image panel: source controls stacked over preview/gallery."""
        panel = QFrame()
        panel.setObjectName("ImagePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        layout.addWidget(self._build_image_header())

        # The stage swaps between a committed image, the search gallery, and a
        # message (searching / no results / failed).
        self._image_stack = QStackedWidget()
        self._image_stack.addWidget(self._build_preview_page())
        self._gallery = MasonryGallery()
        self._gallery.candidateSelected.connect(self._on_candidate_selected)
        self._gallery.nearBottom.connect(self._load_more_results)
        self._image_stack.addWidget(self._gallery)
        self._image_message = QLabel("")
        self._image_message.setObjectName("StageHint")
        self._image_message.setAlignment(Qt.AlignCenter)
        self._image_message.setWordWrap(True)
        self._image_stack.addWidget(self._image_message)
        layout.addWidget(self._image_stack, 1)
        return panel

    def _build_image_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("ImageHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(9)

        # Title on the left, search source on the right: one balanced line.
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("Image")
        title.setObjectName("ImageTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        source_label = QLabel("Source")
        source_label.setObjectName("SourceLabel")
        title_row.addWidget(source_label)
        self._provider_combo = QComboBox()
        self._provider_combo.setMinimumWidth(150)
        for provider in image_search.PROVIDERS:
            self._provider_combo.addItem(provider.name, provider.id)
            self._provider_combo.setItemData(
                self._provider_combo.count() - 1, provider.description, Qt.ToolTipRole
            )
        self._provider_combo.setToolTip(
            "Where online image searches look. Openverse has the broadest coverage."
        )
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        title_row.addWidget(self._provider_combo)
        layout.addLayout(title_row)

        # The source field and its submit action share one row.
        row = QHBoxLayout()
        row.setSpacing(8)
        self._url_edit = QLineEdit()
        self._url_edit.setObjectName("SearchField")
        self._url_edit.setPlaceholderText(
            "Paste a URL or path, or type words to search"
        )
        self._url_edit.setToolTip(
            "Image URL or file path — or type words to search online"
        )
        self._url_edit.returnPressed.connect(self._on_load_clicked)
        # Browse is a trailing action *inside* the field, so it reads as a
        # navigation helper for the path rather than a second submit button.
        self._browse_action = self._url_edit.addAction(
            icon("folder", self.tokens["fg"], 16), QLineEdit.TrailingPosition
        )
        self._browse_action.setToolTip("Browse for an image file…")
        self._browse_action.triggered.connect(self._open_file)
        self._url_edit.textChanged.connect(self._on_url_changed)
        row.addWidget(self._url_edit, 1)
        self._load_btn = QPushButton("Load")
        self._load_btn.setObjectName("LoadButton")
        self._load_btn.setToolTip("Load the URL or path, or search for the words above")
        self._load_btn.setEnabled(False)
        self._load_btn.clicked.connect(self._on_load_clicked)
        row.addWidget(self._load_btn)
        layout.addLayout(row)

        # A quiet meta line: back-to-results (when relevant) and the source.
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        self._back_btn = QPushButton("← Results")
        self._back_btn.setObjectName("ToolBarButton")
        self._back_btn.setToolTip("Back to the search results")
        self._back_btn.clicked.connect(self._show_results)
        self._back_btn.setVisible(False)
        info_row.addWidget(self._back_btn)
        self._image_info = QLabel("No image loaded.")
        self._image_info.setObjectName("ImageMeta")
        self._image_info.setWordWrap(True)
        info_row.addWidget(self._image_info, 1)
        layout.addLayout(info_row)
        return header

    def _build_preview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._preview = ImagePreview()
        self._preview.fileDropped.connect(self._load_local_path)
        self._preview.remoteDropped.connect(self._load_dropped_url)
        self._preview.rawDropped.connect(self._load_dropped_bytes)
        layout.addWidget(self._preview, 1)

        hint = QLabel(
            "Tip: drag an image from a browser or a file onto this preview to "
            "load it, or use the field above."
        )
        hint.setObjectName("StageHint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        self._preview_page = page
        return page

    def _tool_button(
        self, text: str, icon_name: str, slot, tooltip: str = ""
    ) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("ToolBarButton")
        button.setIcon(icon(icon_name, self.tokens["fg"], 16))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(tooltip or text)
        button.clicked.connect(slot)
        return button

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("ActionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._readiness = ReadinessStrip()
        self._readiness.setObjectName("ReadinessStripInline")
        layout.addWidget(self._readiness, 1)

        self._fix_btn = QPushButton("Fix")
        self._fix_btn.setObjectName("FixButton")
        self._fix_btn.setToolTip("Set up what is missing")
        self._fix_btn.clicked.connect(self._on_fix)
        self._fix_btn.setVisible(False)
        layout.addWidget(self._fix_btn)

        self._btn_start = QPushButton("Start drawing")
        self._btn_start.setObjectName("Primary")
        self._btn_start.setIcon(icon("play", self.tokens["accent_fg"], 16))
        self._btn_start.setIconSize(QSize(16, 16))
        self._btn_start.clicked.connect(self._on_start)
        layout.addWidget(self._btn_start)
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
        self._recipe_issues = []
        for recipe in load_user_recipes():
            issues = validate_recipe(recipe)
            if issues:
                self._recipe_issues.append((recipe.id, issues))
                log.info(f"[Recipes] '{recipe.id}' has issues: {issues}")
        self._recipes = list_recipes()
        self._recipes_by_name = {r.name: r for r in self._recipes}
        self._target_combo.blockSignals(True)
        self._target_combo.clear()
        for recipe in self._recipes:
            self._target_combo.addItem(recipe.name, recipe.id)
        self._target_combo.blockSignals(False)
        if self._recipe_issues:
            names = ", ".join(rid for rid, _ in self._recipe_issues)
            self._notice.show_notice(
                f"{len(self._recipe_issues)} recipe(s) could not be fully loaded: {names}",
                "warning",
            )

    def _on_target_changed(self, _index: int) -> None:
        if self._initializing:
            return
        recipe_id = self._target_combo.currentData()
        recipe = next((r for r in self._recipes if r.id == recipe_id), None)
        if recipe is None:
            return
        previous = self.profile.target
        if previous == recipe.id:
            return

        # Remember the old target's geometry and drawing prefs, then restore
        # the new target's. Capture the incoming snapshot before applying the
        # recipe: syncing the widgets can fire a save that re-snapshots the
        # target, so reading it afterwards could pick up the recipe defaults.
        self._environments[previous] = self.profile.snapshot_environment()
        self._drawing_by_target[previous] = self._drawing_snapshot()
        saved_drawing = self._drawing_by_target.get(recipe.id)
        self.profile.target = recipe.id
        if recipe.id in self._environments:
            self.profile.apply_environment(self._environments[recipe.id])
        else:
            self.profile.apply_environment(Profile().snapshot_environment())

        self._apply_recipe(recipe)
        if saved_drawing is not None:
            self._apply_drawing(saved_drawing)
            self._drawing_by_target[recipe.id] = self._drawing_snapshot()
        self._restore_environment()
        self._store_drawing_settings()
        self._store_drawing_options()
        self._save_config()
        self._refresh_detection_status()
        self._sync_env_ui()
        if self._environment_ready():
            self._notice.show_notice(f"Switched to {recipe.name}.", "success")
            self._set_status(f"Target set to {recipe.name}.")
        else:
            self._notice.show_notice(
                f'"{recipe.name}" is not set up yet \u2014 find its canvas and palette.',
                "warning",
                "Auto-detect" if recipe.detection else "Set up",
                self.auto_detect if recipe.detection else self.open_setup,
            )
            self._set_status(f"Target set to {recipe.name} \u2014 setup needed.")

    def _apply_recipe(self, recipe) -> None:
        apply_profile_defaults(self.profile, recipe)
        self.bot.settings[:] = merge_drawing_settings(
            self.bot.settings, recipe.drawing_settings or {}
        )
        if "jump_threshold" in (recipe.drawing_settings or {}):
            self.bot.jump_threshold = int(recipe.drawing_settings["jump_threshold"])
            self._jump_threshold.setValue(self.bot.jump_threshold)
        self.draw_options = merge_drawing_options(
            self.draw_options,
            recipe.drawing_options or {},
            Bot.IGNORE_WHITE,
            Bot.IGNORE_TRANSPARENT,
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
        envs = self.tools.get("environments")
        self._environments = dict(envs) if isinstance(envs, dict) else {}
        self._environments.setdefault(
            self.profile.target, self.profile.snapshot_environment()
        )

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
        if options.get("ignore_transparent_pixels", True):
            self.draw_options |= Bot.IGNORE_TRANSPARENT

        self.bot.skip_first_color = bool(self.tools.get("skip_first_color", False))
        mode = self.tools.get("draw_mode", Bot.LAYERED)
        self._mode = (
            mode if mode in (Bot.SLOTTED, Bot.LAYERED, Bot.OUTLINE) else Bot.LAYERED
        )
        self.bot.stroke_distance = max(
            1, int(settings.get("stroke_distance", Bot.STROKE_DISTANCE))
        )

        metric = self.tools.get("color_metric", DEFAULT_METRIC)
        if metric not in METRICS:
            metric = DEFAULT_METRIC
        self.bot.color_metric = metric
        metric_index = self._metric_combo.findData(metric)
        self._metric_combo.blockSignals(True)
        self._metric_combo.setCurrentIndex(metric_index if metric_index >= 0 else 0)
        self._metric_combo.blockSignals(False)

        last_url = self.tools.get("last_image_url", "")
        if last_url:
            self._last_url = last_url
            self._url_edit.setText(last_url)

        provider = str(
            self.tools.get("image_search_provider", image_search.DEFAULT_PROVIDER)
        )
        if provider not in image_search.PROVIDER_IDS:
            provider = image_search.DEFAULT_PROVIDER
        self._provider = provider
        provider_index = self._provider_combo.findData(provider)
        self._provider_combo.blockSignals(True)
        self._provider_combo.setCurrentIndex(
            provider_index if provider_index >= 0 else 0
        )
        self._provider_combo.blockSignals(False)

        self._theme_mode = str(self.tools.get("theme", "auto"))
        if self._theme_mode not in theme.THEME_MODES:
            self._theme_mode = "auto"
        self._theme_combo.blockSignals(True)
        index = self._theme_combo.findData(self._theme_mode)
        self._theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self._theme_combo.blockSignals(False)

        drawing_by_target = self.tools.get("drawing_by_target")
        self._drawing_by_target = (
            dict(drawing_by_target) if isinstance(drawing_by_target, dict) else {}
        )
        if self.profile.target not in self._drawing_by_target:
            # Migrate the legacy global drawing prefs to the active target.
            self._drawing_by_target[self.profile.target] = self._drawing_snapshot()
        self._apply_drawing(self._drawing_by_target[self.profile.target])

        self._restore_environment()
        self._refresh_drawing_widgets()
        self._refresh_option_widgets()
        self._sync_env_ui()
        self._refresh_detection_status()
        self._apply_theme()

    def _restore_environment(self) -> None:
        # Reset the live palette first so switching to an unconfigured target
        # cannot silently keep the previous target's swatches.
        self.bot._palette = None
        palette = self.profile["Palette"]
        try:
            # Prefer the saved colour/position map: it rebuilds the palette
            # offline. Re-sampling the saved box instead needs the target app
            # to be open and uncovered at that exact spot, which is rarely true
            # at startup -- that produced a one-colour palette and forced users
            # to auto-detect again on every launch.
            colors_pos = self._stored_palette_positions(palette)
            if colors_pos:
                self.bot.init_palette(colors_pos=colors_pos)
            elif palette.get("box") and palette.get("rows") and palette.get("cols"):
                box = palette["box"]
                self.bot.init_palette(
                    pbox=(box[0], box[1], box[2] - box[0], box[3] - box[1]),
                    prows=palette["rows"],
                    pcols=palette["cols"],
                )
        except Exception as e:
            log.info(f"[Config] palette restore failed: {e}")
        try:
            if self.profile["Canvas"].get("box"):
                self.bot.init_canvas(self.profile["Canvas"]["box"])
        except Exception as e:
            log.info(f"[Config] canvas restore failed: {e}")

    @staticmethod
    def _stored_palette_positions(palette) -> Optional[dict]:
        """Rebuild ``{colour: (x, y)}`` from saved ``Palette.color_coords``.

        Returns ``None`` when the entry is absent or malformed, so callers can
        fall back to re-sampling the saved box.
        """
        coords = palette.get("color_coords")
        if not isinstance(coords, dict) or not coords:
            return None
        positions = {}
        try:
            for key, value in coords.items():
                colour = tuple(int(part) for part in str(key).strip("()").split(","))
                position = tuple(int(part) for part in value)
                if len(colour) < 3 or len(position) != 2:
                    return None
                positions[colour[:3]] = position
        except (TypeError, ValueError):
            return None
        return positions or None

    def _drawing_snapshot(self) -> dict:
        """Current target's drawing settings/options, for per-target memory."""
        return {
            "settings": [float(v) for v in self.bot.settings],
            "jump_threshold": int(self.bot.jump_threshold),
            "stroke_distance": int(self.bot.stroke_distance),
            "drawing_options": {
                "ignore_white_pixels": bool(self.draw_options & Bot.IGNORE_WHITE),
                "ignore_transparent_pixels": bool(
                    self.draw_options & Bot.IGNORE_TRANSPARENT
                ),
            },
            "draw_mode": self._mode,
            "skip_first_color": bool(self.bot.skip_first_color),
        }

    def _apply_drawing(self, data) -> None:
        """Apply a per-target drawing snapshot, then sync the widgets."""
        if not isinstance(data, dict):
            return
        settings = data.get("settings")
        if isinstance(settings, (list, tuple)) and len(settings) >= 3:
            self.bot.settings = [
                float(settings[0]),
                float(settings[1]),
                float(settings[2]),
            ]
        if "jump_threshold" in data:
            self.bot.jump_threshold = int(data["jump_threshold"])
        if "stroke_distance" in data:
            self.bot.stroke_distance = max(1, int(data["stroke_distance"]))
        options = data.get("drawing_options") or {}
        self.draw_options = 0
        if options.get("ignore_white_pixels", True):
            self.draw_options |= Bot.IGNORE_WHITE
        if options.get("ignore_transparent_pixels", True):
            self.draw_options |= Bot.IGNORE_TRANSPARENT
        mode = data.get("draw_mode", Bot.LAYERED)
        self._mode = (
            mode if mode in (Bot.SLOTTED, Bot.LAYERED, Bot.OUTLINE) else Bot.LAYERED
        )
        self.bot.skip_first_color = bool(data.get("skip_first_color", False))
        self._jump_threshold.setValue(self.bot.jump_threshold)
        self._refresh_drawing_widgets()
        self._refresh_option_widgets()

    def _store_drawing_settings(self) -> None:
        settings = self.tools.setdefault("drawing_settings", {})
        settings["delay"] = self.bot.settings[0]
        settings["pixel_size"] = self.bot.settings[1]
        settings["jump_delay"] = self.bot.settings[2]
        settings["jump_threshold"] = self.bot.jump_threshold
        settings["stroke_distance"] = int(self.bot.stroke_distance)

    def _store_drawing_options(self) -> None:
        options = self.tools.setdefault("drawing_options", {})
        options["ignore_white_pixels"] = bool(self.draw_options & Bot.IGNORE_WHITE)
        options["ignore_transparent_pixels"] = bool(
            self.draw_options & Bot.IGNORE_TRANSPARENT
        )

    def _save_config(self) -> None:
        if self._initializing:
            return
        self.tools["pause_key"] = self.bot.pause_key
        self.tools["skip_first_color"] = bool(self.bot.skip_first_color)
        self.tools["draw_mode"] = self._mode
        self.tools["color_metric"] = self.bot.color_metric
        self.tools["theme"] = self._theme_mode
        self.tools["image_search_provider"] = self._provider
        if self._last_url:
            self.tools["last_image_url"] = self._last_url
        self._drawing_by_target[self.profile.target] = self._drawing_snapshot()
        self.tools["drawing_by_target"] = self._drawing_by_target
        self._environments[self.profile.target] = self.profile.snapshot_environment()
        self.tools["environments"] = self._environments
        payload = pyaint_config.build_payload(self.tools, self.profile)
        if not pyaint_config.save_config(self._config_path, payload):
            log.info(f"Failed to save config to {self._config_path}")
            self._notice.show_notice(
                f"Could not save settings to {os.path.basename(self._config_path)} "
                "\u2014 changes will be lost on exit.",
                "error",
            )

    # ------------------------------------------------------------------
    # Widget <-> state sync
    # ------------------------------------------------------------------
    def _refresh_drawing_widgets(self) -> None:
        for field, value in zip(self._setters, self.bot.settings):
            field.set_value(value)
        self._stroke_distance.set_value(int(self.bot.stroke_distance))
        mode_index = self._mode_combo.findData(self._mode)
        if mode_index >= 0:
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(mode_index)
            self._mode_combo.blockSignals(False)
        self._update_stroke_distance_visibility()

    def _update_stroke_distance_visibility(self) -> None:
        """Only OUTLINE mode uses a configurable stroke distance."""
        self._stroke_distance.setVisible(self._mode == Bot.OUTLINE)

    def _refresh_option_widgets(self) -> None:
        self._chk_ignore.setChecked(bool(self.draw_options & Bot.IGNORE_WHITE))
        self._chk_transparent.setChecked(
            bool(self.draw_options & Bot.IGNORE_TRANSPARENT)
        )
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
        self._mspaint_delay.setValue(
            int(float(self.profile.mspaint_mode.get("delay", 0.5)) * 1000)
        )
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
            "Detected: " + "; ".join(parts)
            if parts
            else "No regions detected yet — run Auto-detect or teach it manually."
        )
        self._refresh_readiness()

    def _environment_ready(self) -> bool:
        return (
            getattr(self.bot, "_canvas", None) is not None
            and getattr(self.bot, "_palette", None) is not None
        )

    def _refresh_readiness(self) -> None:
        recipe = get_recipe(self.profile.target)
        environment_ready = self._environment_ready()
        image_ready = self._has_image()
        self._readiness.update_steps(recipe.name, environment_ready, image_ready)
        if hasattr(self, "_fix_btn"):
            self._fix_btn.setVisible(not environment_ready)
        self._update_env_chip()
        if not self._busy:
            # Keep Start clickable: clicking it explains what is missing rather
            # than leaving a greyed-out button with no reason.
            self._btn_start.setEnabled(True)
            self._btn_start.setToolTip(
                "Start drawing"
                if (environment_ready and image_ready)
                else "Not ready yet — click to see what is missing"
            )

    def _update_env_chip(self) -> None:
        if not hasattr(self, "_env_chip"):
            return
        canvas = getattr(self.bot, "_canvas", None)
        palette = getattr(self.bot, "_palette", None)
        if canvas is not None and palette is not None and len(palette.colors) > 1:
            state, text = "ready", f"Ready \u00b7 {len(palette.colors)} colours"
        elif canvas is not None or palette is not None:
            state, text = "partial", "Partly set up"
        else:
            state, text = "none", "Not set up"
        self._env_chip.setText(text)
        if self._env_chip.property("state") != state:
            self._env_chip.setProperty("state", state)
            self._env_chip.style().unpolish(self._env_chip)
            self._env_chip.style().polish(self._env_chip)

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
        self._update_stroke_distance_visibility()
        self._save_config()

    def _on_stroke_distance_changed(self, value: float) -> None:
        if self._initializing:
            return
        self.bot.stroke_distance = max(1, int(round(value)))
        self._store_drawing_settings()
        self._save_config()

    def _on_metric_changed(self, _index: int) -> None:
        if self._initializing:
            return
        self.bot.color_metric = self._metric_combo.currentData() or DEFAULT_METRIC
        self._save_config()

    def _on_options_changed(self) -> None:
        if self._initializing:
            return
        self.draw_options = 0
        if self._chk_ignore.isChecked():
            self.draw_options |= Bot.IGNORE_WHITE
        if self._chk_transparent.isChecked():
            self.draw_options |= Bot.IGNORE_TRANSPARENT
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
        accent_fg = self.tokens["accent_fg"]
        self._btn_precompute.setIcon(icon("download", fg, 16))
        self._btn_test.setIcon(icon("zap", fg, 16))
        self._btn_simple.setIcon(icon("play", fg, 16))
        self._btn_start.setIcon(icon("play", accent_fg, 16))
        self._browse_action.setIcon(icon("folder", fg, 16))

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
        # Pause/stop are toggled by the global hotkey listener, so mirror the
        # bot's pause state onto the overlay here.
        self._overlay.set_paused(self.bot.paused)
        self._set_status(f"Drawing {completed}/{total} strokes")

    def _start_task(
        self,
        name: str,
        work,
        minimize: bool = False,
        overlay: bool = False,
        interruptible: bool = True,
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
                self._last_error = (name, str(exc))
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
        # A failure must not vanish with the overlay: surface it as a banner.
        error = self._last_error
        self._last_error = None
        if error:
            name, message = error
            self._notice.show_notice(f"{name} failed: {message}", "error")

    def _ready_countdown(self, name=None, seconds: int = 3) -> None:
        """Explain the pre-draw pause instead of sleeping silently."""
        if name is None:
            name = get_recipe(self.profile.target).name
        for remaining in range(int(seconds), 0, -1):
            self.signals.message.emit(
                f"Switch to {name} — drawing starts in {remaining}…"
            )
            time.sleep(1)

    def _set_running(self, running: bool, interruptible: bool = True) -> None:
        for button in (
            self._btn_precompute,
            self._btn_test,
            self._btn_simple,
            self._btn_start,
            self._auto_btn,
        ):
            button.setEnabled(not running)
        if not running:
            self._overlay.set_paused(False)
            self._refresh_readiness()

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)
        log.info(text)

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------
    def _load_default_image(self) -> None:
        if os.path.exists(self._imname):
            self._set_image_path(self._imname)
        else:
            self._preview.set_placeholder("Drag an image here, or use the field above.")
            self._image_stack.setCurrentWidget(self._preview_page)

    def _on_url_changed(self, text: str) -> None:
        self._load_btn.setEnabled(bool(text.strip()))

    def _on_load_clicked(self) -> None:
        text = self._url_edit.text().strip()
        if not text:
            self._set_status(
                "Enter a URL, file path, or search words — or click the folder to browse."
            )
            return
        if text.lower().startswith(("http://", "https://")):
            self._start_task(
                "Download image",
                lambda: self._download_and_show(text),
                interruptible=False,
            )
        elif os.path.exists(text):
            self._load_local_path(text)
        elif _looks_like_path(text):
            self._set_status(f"File not found: {text}")
        elif (
            text == self._search_query
            and self._image_stack.currentWidget() is self._gallery
            and self._gallery.count()
        ):
            # Enter twice on the same query commits the first result.
            first = self._gallery.first_candidate()
            if first is not None:
                self._on_candidate_selected(first)
        else:
            self._start_search(text)

    # ------------------------------------------------------------------
    # Image search gallery
    # ------------------------------------------------------------------
    def _start_search(self, query: str) -> None:
        self._search_query = query
        self._search_generation += 1
        self._search_continue = None
        self._search_loading = True
        self._pending_source = None
        self._gallery.clear()
        provider_name = image_search.provider_name(self._provider)
        self._image_message.setText(f'Searching {provider_name} for "{query}"…')
        self._image_stack.setCurrentWidget(self._image_message)
        self._back_btn.setVisible(False)
        self._image_info.setText(f'Searching {provider_name} for "{query}"…')
        self._request_search_page(None)

    def _on_provider_changed(self, _index: int) -> None:
        self._provider = (
            self._provider_combo.currentData() or image_search.DEFAULT_PROVIDER
        )
        self._save_config()
        # Re-run the last search so switching sources is immediately visible.
        if self._search_query and self._image_stack.currentWidget() in (
            self._gallery,
            self._image_message,
        ):
            self._start_search(self._search_query)

    def _request_search_page(self, cont) -> None:
        from pyaint.ui.search_tasks import SearchPageTask

        task = SearchPageTask(
            self._search_query, cont, self._search_generation, provider=self._provider
        )
        task.signals.ready.connect(self._on_search_page)
        task.signals.failed.connect(self._on_search_failed)
        QThreadPool.globalInstance().start(task)

    def _on_search_page(self, generation: int, page) -> None:
        if generation != self._search_generation:
            return
        self._search_loading = False
        self._search_continue = page.next_continue
        if page.candidates:
            self._gallery.add_candidates(page.candidates)
            self._image_stack.setCurrentWidget(self._gallery)
            self._back_btn.setVisible(False)
            self._image_info.setText(
                f"{self._gallery.count()} results — press Enter to use the first, "
                "or click one."
            )
            self._start_thumbnails(page.candidates)
        elif self._gallery.count() == 0:
            provider_name = image_search.provider_name(self._provider)
            self._image_message.setText(
                f'No images found for "{self._search_query}" on {provider_name}.\n'
                "Try different words, or switch the search source above."
            )
            self._image_stack.setCurrentWidget(self._image_message)
            self._image_info.setText(
                f'No images found for "{self._search_query}" on {provider_name}.'
            )

    def _on_search_failed(self, generation: int, message: str) -> None:
        if generation != self._search_generation:
            return
        self._search_loading = False
        self._image_message.setText(f"Image search failed: {message}")
        self._image_stack.setCurrentWidget(self._image_message)
        self._image_info.setText(f"Image search failed: {message}")

    def _load_more_results(self) -> None:
        if self._search_loading or not self._search_continue:
            return
        self._search_loading = True
        self._request_search_page(self._search_continue)

    def _start_thumbnails(self, candidates) -> None:
        from pyaint.ui.search_tasks import ThumbnailTask

        for candidate in candidates:
            task = ThumbnailTask(candidate.thumb_url, self._search_generation)
            task.signals.ready.connect(self._on_thumbnail_ready)
            task.signals.failed.connect(self._on_thumbnail_failed)
            QThreadPool.globalInstance().start(task)

    def _on_thumbnail_ready(self, generation: int, url: str, image) -> None:
        if generation != self._search_generation:
            return
        self._gallery.set_thumbnail(url, QPixmap.fromImage(image))

    def _on_thumbnail_failed(self, generation: int, url: str) -> None:
        # A thumbnail that won't decode just leaves an empty tile.
        return

    def _on_candidate_selected(self, candidate) -> None:
        self._start_task(
            "Download image",
            lambda: self._commit_candidate(candidate),
            interruptible=False,
        )

    def _commit_candidate(self, candidate) -> None:
        """Worker: download the chosen result and hand it to the preview."""
        data = image_search.fetch_bytes(candidate.url)
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            image.convert("RGBA").save(path, format="PNG")
        self._pending_source = (candidate.title, candidate.source_url)
        self.signals.image_ready.emit(path)

    def _show_results(self) -> None:
        if self._gallery.count():
            self._image_stack.setCurrentWidget(self._gallery)
            self._back_btn.setVisible(False)

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
                        raise ValueError(
                            f"URL is not an image (content-type: {content_type})"
                        )
                    fd, temp_path = tempfile.mkstemp(suffix=".png")
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(response.read())
                    return temp_path
            except urllib_error.HTTPError as exc:
                if exc.code == 429 and attempt < retries - 1:
                    time.sleep(min(2**attempt, 10))
                    continue
                raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc
            except urllib_error.URLError as exc:
                if attempt == retries - 1:
                    raise ValueError(f"Network error: {exc.reason}") from exc
        raise ValueError("Failed to fetch image")

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open image",
            paths.PROJECT_ROOT,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)",
        )
        if path:
            self._load_local_path(path)

    def _load_local_path(self, path: str) -> None:
        """Load a local image and mirror it into the URL/path field.

        Also forgets any remembered URL so a later restart doesn't resurrect a
        remote source that is no longer the loaded image.
        """
        self._last_url = ""
        self.tools["last_image_url"] = ""
        if self._url_edit.text().strip() != path:
            self._url_edit.setText(path)
        self._set_image_path(path)

    def _set_image_path(self, path: str) -> None:
        try:
            image = Image.open(path)
        except Exception as exc:
            self._set_status(f"Could not open image: {exc}")
            return
        self._imname = path
        self._preview.set_pixmap(pil_to_qpixmap(image))
        self._image_stack.setCurrentWidget(self._preview_page)
        note = self._pending_source
        self._pending_source = None
        info = f"{os.path.basename(path)} — {image.width}×{image.height}px"
        if note:
            info += f" · {note[0]}"
        self._image_info.setText(info)
        self._back_btn.setVisible(self._gallery.count() > 0)
        canvas = getattr(self.bot, "_canvas", None)
        if canvas is not None:
            has_cache, _ = self.bot.get_cached_status(
                path, flags=self.draw_options, mode=self._mode
            )
            self._set_status(
                "Cached result available"
                if has_cache
                else "No cache — will process live"
            )
        else:
            self._set_status("Image loaded. Detect or teach the canvas next.")
        self._refresh_readiness()

    # Drag & drop
    def dragEnterEvent(self, event):  # noqa: N802
        if accepts_image_drop(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        self._handle_image_drop(event.mimeData())

    def _handle_image_drop(self, mime) -> None:
        """Load an image dropped from anywhere: a file, a browser, or another app."""
        path = local_path_from_mime(mime)
        if path:
            self._load_local_path(path)
            return
        remote = remote_source_from_mime(mime)
        if remote:
            self._load_dropped_url(remote)
            return
        raw = raw_image_from_mime(mime)
        if raw is not None:
            self._load_dropped_bytes(raw)
            return
        self._set_status("That drop did not contain an image.")

    def _load_dropped_url(self, url: str) -> None:
        """Load an http(s) or ``data:`` image URL dropped onto the window."""
        if url.startswith("data:image/"):
            try:
                data = _decode_data_uri(url)
            except Exception as exc:  # noqa: BLE001 - surface it instead of crashing
                self._set_status(f"Could not read dropped image: {exc}")
                return
            self._load_dropped_bytes(data)
            return
        url = _unwrap_image_redirect(url)
        self._url_edit.setText(url)
        self._start_task(
            "Download image",
            lambda: self._download_and_show(url),
            interruptible=False,
        )

    def _load_dropped_bytes(self, data: bytes) -> None:
        """Persist raw dropped image bytes and load them like a local file."""
        fd, path = tempfile.mkstemp(suffix=".png")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        except Exception as exc:  # noqa: BLE001 - surface it instead of crashing
            self._set_status(f"Could not save dropped image: {exc}")
            return
        self._load_local_path(path)

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------
    def auto_detect(self) -> None:
        if self._detecting:
            return
        self._detection_overlay.hide_detection()
        recipe = get_recipe(self.profile.target)
        if not recipe.detection:
            self._notice.show_notice(
                f'No auto-detection is configured for "{recipe.name}".',
                "info",
                "Set up",
                self.open_setup,
            )
            return
        self._detecting = True
        self._pending_recipe = recipe
        self._detection_result = None
        self._detection_image = None
        self.showNormal()
        self.raise_()
        self.activateWindow()
        for button in (
            self._auto_btn,
            self._btn_start,
            self._btn_test,
            self._btn_simple,
            self._btn_precompute,
        ):
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
            log.info(
                f"[AutoDetect] {recipe.id}: canvas={detection.canvas} palette={detection.palette}"
            )
            self._present_detection(image, detection)
            self._set_status("Review the detected regions, then use or discard them.")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.showNormal()
            self.raise_()
            self.activateWindow()
            QMessageBox.critical(self, self.title, f"Auto-detect failed: {exc}")
        finally:
            self._detecting = False
            self._set_running(False)

    def _present_detection(self, image, detection) -> None:
        """Review the detection on-screen, over the still-minimized target app."""
        self._detection_image = image
        self._detection_result = detection if detection else None
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.showNormal()
            self._notice.show_notice(
                "Could not open the detection review overlay.", "error"
            )
            return
        summary = self._detection_checklist(detection)
        if not detection:
            summary += (
                "\n\nMake sure the canvas is blank and the target app is maximized "
                "on the primary monitor at 100% display scaling."
            )
        self._detection_overlay.show_detection(detection, image.size, summary, screen)

    def _apply_detection(self) -> None:
        self._detection_overlay.hide_detection()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if not self._detection_result:
            self._set_status("Nothing to apply.")
            return
        applied = self.bot.apply_detection(
            self._detection_result, image=self._detection_image
        )
        self._sync_env_ui()
        self._refresh_detection_status()
        self._store_drawing_settings()
        self._store_drawing_options()
        self._save_config()
        self._refresh_readiness()
        palette = getattr(self.bot, "_palette", None)
        if palette is not None and len(palette.colors) <= 1:
            self._notice.show_notice(
                "The palette sampled as a single colour — the target app may have "
                "been covered. Re-run Auto-detect with the app in front, or teach it.",
                "error",
                "Re-detect",
                self.auto_detect,
            )
        else:
            self._notice.show_notice("Canvas and palette detected.", "success")
        self._set_status(f"Auto-detect applied ({', '.join(applied) or 'nothing'}).")

    def _retry_detection(self) -> None:
        self._detection_overlay.hide_detection()
        if self._detecting:
            return
        self._detecting = True
        QTimer.singleShot(300, self._finish_auto_detect)

    def _teach_detection(self) -> None:
        self._detection_overlay.hide_detection()
        # Open Setup from the next event-loop turn. Opening a modal dialog from
        # inside the overlay button's own event can leave the dialog unable to
        # take focus (the app was only just activated by that same click).
        QTimer.singleShot(0, self._open_setup_from_detection)

    def _open_setup_from_detection(self) -> None:
        # The window was minimized for the detection capture; make sure it is
        # genuinely restored and active before opening a modal dialog, or the
        # dialog can end up owned by a minimized window and become a hidden
        # modal that blocks all input.
        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.open_setup()

    def _dismiss_detection(self) -> None:
        self._detection_overlay.hide_detection()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._set_status("Auto-detect dismissed — no changes made.")

    # ------------------------------------------------------------------
    # Drawing actions
    # ------------------------------------------------------------------
    def _has_image(self) -> bool:
        return bool(self._imname) and os.path.exists(self._imname)

    def _require_image(self) -> bool:
        if not self._has_image():
            self._notice.show_notice(
                "Load an image first.", "warning", "Choose image", self._open_file
            )
            return False
        return True

    def _resolve_cmap(self):
        has_cache, cache_file = self.bot.get_cached_status(
            self._imname, flags=self.draw_options, mode=self._mode
        )
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
        cache_file = self.bot.precompute(
            self._imname, flags=self.draw_options, mode=self._mode
        )
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
        self.bot.draw_state = {
            "color_idx": 0,
            "line_idx": 0,
            "segment_idx": 0,
            "current_color": None,
            "was_paused": False,
        }
        self.signals.status.emit(f"Test drawing {min(20, total)} lines.")
        self._ready_countdown(seconds=2)
        result = self.bot.test_draw(cmap, max_lines=min(20, total))
        self.signals.status.emit(
            "Test draw completed." if result == "success" else f"Test draw: {result}."
        )

    def _on_simple_test(self) -> None:
        if getattr(self.bot, "_canvas", None) is None:
            self._notice.show_notice(
                "Canvas not set yet.", "warning", "Auto-detect", self._on_fix
            )
            return
        self._start_task(
            "Brush test", self.bot.simple_test_draw, minimize=True, interruptible=False
        )

    # ------------------------------------------------------------------
    # Pre-flight
    # ------------------------------------------------------------------
    def _preflight_issues(self):
        """Return ``(reason, action_text, action)`` for everything missing."""
        issues = []
        if not self._has_image():
            issues.append(("no image loaded", "Choose image", self._open_file))
        if getattr(self.bot, "_canvas", None) is None:
            issues.append(("canvas not set", "Set up", self._on_fix))
        palette = getattr(self.bot, "_palette", None)
        if palette is None:
            issues.append(("palette not set", "Set up", self._on_fix))
        elif len(palette.colors) <= 1:
            issues.append(
                ("palette has only one colour", "Auto-detect", self.auto_detect)
            )
        return issues

    def _on_fix(self) -> None:
        recipe = get_recipe(self.profile.target)
        if recipe.detection:
            self.auto_detect()
        else:
            self.open_setup()

    def _on_start(self) -> None:
        issues = self._preflight_issues()
        if issues:
            summary = ", ".join(reason for reason, _, _ in issues)
            _, action_text, action = issues[0]
            self._notice.show_notice(
                f"Not ready to draw — {summary}.", "warning", action_text, action
            )
            return
        self._notice.clear()
        self._start_task("Drawing", self._draw_work, minimize=True, overlay=True)

    def _draw_work(self) -> None:
        start = time.time()
        cmap = self._resolve_cmap()
        eta = self.bot.estimate_drawing_time(cmap)
        self._ready_countdown()
        self.signals.status.emit(f"Drawing — estimated {eta}.")
        self.bot.terminate = False
        self.bot.paused = False
        self.bot.drawing = False
        self.bot.draw_state = {
            "color_idx": 0,
            "line_idx": 0,
            "segment_idx": 0,
            "current_color": None,
            "was_paused": False,
        }
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
            self._notice.show_notice(
                "Canvas not set yet.", "warning", "Auto-detect", self._on_fix
            )
            return
        try:
            result = pick_points(
                self, 2, "Click the UPPER-LEFT then LOWER-RIGHT corner of the region."
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.title, f"Region pick failed: {exc}")
            return
        if not result or len(result.points) < 2:
            self._set_status("Region selection cancelled.")
            return
        (x1, y1), (x2, y2) = result.points
        box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        self._redraw_region = box
        self._region_label.setText(
            f"Region: ({box[0]}, {box[1]}) → ({box[2]}, {box[3]})"
        )
        self._set_status("Region selected. Click 'Draw region'.")

    def _on_draw_region(self) -> None:
        if self._redraw_region is None:
            self._notice.show_notice(
                "Pick a region first.", "warning", "Pick region", self.pick_region
            )
            return
        self._start_task(
            "Region redraw", self._redraw_work, minimize=True, overlay=True
        )

    def _redraw_work(self) -> None:
        region = self._redraw_region
        image_region = self._canvas_to_image_region(region)
        target = (region[0], region[1], region[2] - region[0], region[3] - region[1])
        cmap = self.bot.process_region(
            self._imname,
            image_region,
            flags=self.draw_options,
            mode=self._mode,
            canvas_target=target,
        )
        if not cmap:
            self.signals.status.emit("No drawable content in the selected region.")
            return
        self._ready_countdown()
        self.signals.status.emit("Redrawing region…")
        self.bot.terminate = False
        self.bot.paused = False
        self.bot.drawing = False
        self.bot.draw_state = {
            "color_idx": 0,
            "line_idx": 0,
            "segment_idx": 0,
            "current_color": None,
            "was_paused": False,
        }
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

        # Never open the modal Setup dialog from a minimized/background window:
        # it can become a hidden modal that blocks all input.
        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )
        self.showNormal()
        self.raise_()
        self.activateWindow()
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
            self,
            self.title,
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
    def closeEvent(self, event):  # noqa: N802
        self._overlay.hide_overlay()
        self._detection_overlay.hide_detection()
        self._countdown_banner.stop()
        # Flush any pending settings. Most edits save eagerly, but a few (e.g.
        # the loaded image path) can be pending, and a crash-free close is the
        # last chance to persist them.
        self._save_config()
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
