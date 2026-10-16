"""Settings-inspector construction, split out of :mod:`pyaint.ui.main_window`.

Behaviour-preserving extraction: these methods were part of ``MainWindow`` and
still run against it through :class:`InspectorMixin`, so every ``self._*``
attribute and ``self._on_*`` handler resolves exactly as before.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyaint.bot import Bot
from pyaint.palette import METRIC_CIEDE2000, METRIC_RGB
from pyaint.ui import theme
from pyaint.ui.paper import PaperSurface
from pyaint.ui.presets import SKETCH_PRESET_OPTIONS
from pyaint.ui.widgets import (
    CheckBox,
    CheckBoxField,
    CollapsibleSection,
    DualReadoutSlider,
    NoticeBanner,
    Section,
    SegmentedControl,
)


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


class InspectorMixin:
    """Builds the settings inspector; mixed into :class:`MainWindow`."""

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
        # "Customize" is a regular quad: it holds the most text and controls,
        # so it stays a clean rounded panel (the mode highlight carries the
        # irregular character instead).
        side = PaperSurface("column", regular=True)
        side.setFixedWidth(300)
        side_layout = QVBoxLayout(side)
        # Keep every control inside the declared content-safe inset, or the
        # column's bowed edge would eat into the labels and sliders.
        safe = side.content_margins()
        side_layout.setContentsMargins(safe.left(), 10, safe.right(), 10)
        side_layout.setSpacing(0)

        scroll, layout = self._scroll_panel()

        # Mode + Look + the Fine-tune toggle lead the column, so the decision
        # and the knobs that refine it are never separated.
        self._build_sidebar_head(layout)

        drawing = Section("Drawing", "How slowly and how finely Pyaint paints.")
        self._drawing_section = drawing

        # Kept in this order: index matches ``Bot.settings`` (delay, step, jump).
        delay = DualReadoutSlider("Time per stroke", "time_per_stroke", 0.0, 1.0, 0.1, 0.01)
        delay.setToolTip("How long each run takes (higher = slower, smoother).")
        detail = DualReadoutSlider("Detail", "detail", 1, 50, 12, 1)
        detail.setToolTip(
            "Pixel step between sampled points. Lower = finer detail, more strokes."
        )
        jump = DualReadoutSlider("Pause after big moves", "pause_after_big_moves", 0.0, 2.0, 0.5, 0.05)
        jump.setToolTip(
            "Pause inserted when the cursor jumps a long way between runs."
        )
        self._setters = [delay, detail, jump]
        for index, field in enumerate(self._setters):
            field.changed.connect(
                lambda value, i=index: self._on_setting_changed(i, value)
            )
        # Detail shapes the quantised grid, so it applies to every mode.
        drawing.add(detail)

        # Outline pacing: the prototype's continuous-stroke knobs, surfaced
        # only while Outline is selected.
        self._stroke_speed = DualReadoutSlider("Stroke speed", "drawing_speed", 200, 5000, 1500, 50)
        self._stroke_speed.setToolTip(
            "How fast the cursor travels while tracing an outline (higher = faster)."
        )
        self._event_interval = DualReadoutSlider("Event interval", "event_interval", 2, 50, 17, 1)
        self._event_interval.setToolTip(
            "Time between cursor move events. Lower = smoother, but a heavier "
            "input load on the target."
        )
        self._travel_delay = DualReadoutSlider("Pause between strokes", "pause_between_strokes", 0.0, 1.0, 0.05, 0.01)
        self._travel_delay.setToolTip(
            "Pause inserted when moving between separate outline strokes."
        )
        # Label-map cleaner thresholds, exposed so more aggressive values can be
        # trialled against fragmentation.
        self._outline_smoothing = DualReadoutSlider("Smoothing", "smoothing", 0, 5, 2, 1)
        self._outline_smoothing.setToolTip(
            "Outline only: edge-preserving bilateral smoothing before tracing. "
            "Higher values remove more anti-aliasing specks but round fine detail."
        )
        self._outline_join_distance = DualReadoutSlider("Join distance", "join_distance", 0.0, 20.0, 6.0, 0.5
        )
        self._outline_join_distance.setToolTip(
            "Outline only: chain open stroke endpoints within this many pixels "
            "into one longer stroke. Raise it to remove fragmentation."
        )
        self._outline_step_threshold = DualReadoutSlider("Shading cleanup", "skip_soft_shading", 0.0, 30.0, 10.0, 1.0
        )
        self._outline_step_threshold.setToolTip(
            "Outline only: merge touching regions whose mean colours are within "
            "this Lab distance, so soft shading and gradients are not traced. "
            "Raise it for cleaner lines, lower it for more detail; 0 keeps "
            "every region boundary."
        )
        for field in (
            self._stroke_speed,
            self._event_interval,
            self._travel_delay,
            self._outline_smoothing,
            self._outline_join_distance,
            self._outline_step_threshold,
        ):
            field.changed.connect(self._on_outline_settings_changed)

        # Sketch (edge trace) controls. A preset chooses the whole look; the
        # individual knobs live under Advanced so a first-time user is not
        # confronted with a wall of sliders.
        self._sketch_source = QComboBox()
        self._sketch_source.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self._sketch_source.setMinimumContentsLength(8)
        self._sketch_source.addItem("Edge drawing", Bot.EDGE_EDGEDRAWING)
        self._sketch_source.addItem("Canny", Bot.EDGE_CANNY)
        self._sketch_source.setToolTip(
            "Which edge detector finds the lines. 'Edge drawing' returns long "
            "connected strokes; 'Canny' is the lighter classic."
        )
        self._sketch_hue_merge = CheckBoxField(
            "Merge by colour",
            "Drop strokes whose two sides share a hue, so soft shading is not "
            "traced while real colour boundaries stay.",
        )
        self._sketch_hue_threshold = DualReadoutSlider("Colour difference", "hue_difference",
            0,
            60,
            15,
            1,
            hint=(
                "Minimum hue difference (degrees) across a stroke to keep it. "
                "Higher drops more shading edges."
            ),
        )
        self._sketch_smoothing = DualReadoutSlider("Smoothing", "smoothing",
            0,
            5,
            3,
            1,
            hint=(
                "Edge-preserving blur before detection. Higher removes "
                "texture but rounds fine detail."
            ),
        )
        self._sketch_join_distance = DualReadoutSlider("Join distance", "join_distance",
            0.0,
            20.0,
            10.0,
            0.5,
            hint=(
                "Bridge open stroke ends within this many pixels into one "
                "longer, continuous line."
            ),
        )
        self._sketch_min_stroke = DualReadoutSlider("Min stroke", "min_stroke",
            0,
            60,
            8,
            1,
            hint="Discard open strokes shorter than this, removing specks.",
        )
        self._sketch_epsilon = DualReadoutSlider("Simplify", "simplify",
            0.0,
            5.0,
            1.2,
            0.1,
            hint=(
                "Polygon simplification tolerance. Higher = fewer, "
                "straighter points per stroke."
            ),
        )
        self._sketch_gradient_keep = DualReadoutSlider("Keep strongest %", "skip_faint_edges",
            10,
            100,
            100,
            5,
            hint=(
                "Keep only the highest-gradient strokes. 100 keeps them all; "
                "lower values prune weak edges and soft shading."
            ),
        )
        # Canny-only thresholds.
        self._canny_auto_toggle = CheckBoxField(
            "Auto Canny thresholds",
            "Derive the thresholds from the image's gradient (Otsu). Turn off "
            "to set Low/High by hand.",
        )
        self._canny_low = DualReadoutSlider("Canny low", "canny_low",
            0,
            255,
            50,
            1,
            hint="Weaker edges below this gradient are discarded.",
        )
        self._canny_high = DualReadoutSlider("Canny high", "canny_high",
            0,
            255,
            150,
            1,
            hint="Strong edges above this gradient seed the trace.",
        )
        self._canny_color_edges_toggle = CheckBoxField(
            "Trace colour edges",
            "Also detect edges on colour, so boundaries between equally bright "
            "colours are sketched.",
        )
        for field in (
            self._sketch_hue_threshold,
            self._sketch_smoothing,
            self._sketch_join_distance,
            self._sketch_min_stroke,
            self._sketch_epsilon,
            self._sketch_gradient_keep,
            self._canny_low,
            self._canny_high,
        ):
            field.changed.connect(self._on_sketch_settings_changed)
        self._sketch_source.currentIndexChanged.connect(
            self._on_sketch_source_changed
        )
        self._sketch_hue_merge.toggled.connect(self._on_sketch_settings_changed)
        self._canny_auto_toggle.toggled.connect(self._on_sketch_settings_changed)
        self._canny_color_edges_toggle.toggled.connect(
            self._on_sketch_settings_changed
        )

        # Plain containers toggled by visibility: a hidden widget takes no
        # layout space, so each mode shows only its own controls.
        self._runs_controls = QWidget()
        runs_layout = QVBoxLayout(self._runs_controls)
        runs_layout.setContentsMargins(0, 0, 0, 0)
        runs_layout.setSpacing(4)
        runs_layout.addWidget(delay)
        runs_layout.addWidget(jump)
        drawing.add(self._runs_controls)

        self._outline_controls = QWidget()
        outline_layout = QVBoxLayout(self._outline_controls)
        outline_layout.setContentsMargins(0, 0, 0, 0)
        outline_layout.setSpacing(4)
        self._chk_double_edges = CheckBoxField(
            "Double-paint edges",
            "Off keeps each shared border as one clean line; on draws every "
            "region's full border, so shared edges look heavier.",
        )
        self._chk_double_edges.toggled.connect(
            self._on_outline_double_edges_changed
        )
        outline_layout.addWidget(self._outline_smoothing)
        outline_layout.addWidget(self._outline_step_threshold)
        outline_layout.addWidget(self._outline_join_distance)
        outline_layout.addWidget(self._chk_double_edges)
        drawing.add(self._outline_controls)

        self._sketch_controls = QWidget()
        sketch_layout = QVBoxLayout(self._sketch_controls)
        sketch_layout.setContentsMargins(0, 0, 0, 0)
        sketch_layout.setSpacing(6)
        self._sketch_preset_title = QLabel()
        self._sketch_preset_title.setObjectName("PresetTagline")
        sketch_layout.addWidget(self._sketch_preset_title)
        self._sketch_preset_desc = QLabel()
        self._sketch_preset_desc.setObjectName("PresetHint")
        self._sketch_preset_desc.setWordWrap(True)
        sketch_layout.addWidget(self._sketch_preset_desc)

        self._sketch_advanced = CollapsibleSection("Advanced settings")
        advanced_hint = QLabel(
            "Fine-tune the chosen preset. Changing any value switches the "
            "preset to Custom."
        )
        advanced_hint.setObjectName("SectionHint")
        advanced_hint.setWordWrap(True)
        self._sketch_advanced.add(advanced_hint)
        for widget in (
            self._sketch_source,
            self._sketch_hue_merge,
            self._sketch_hue_threshold,
            self._sketch_smoothing,
            self._sketch_join_distance,
            self._sketch_min_stroke,
            self._sketch_epsilon,
            self._sketch_gradient_keep,
            self._canny_auto_toggle,
            self._canny_low,
            self._canny_high,
            self._canny_color_edges_toggle,
        ):
            self._sketch_advanced.add(widget)
        sketch_layout.addWidget(self._sketch_advanced)
        drawing.add(self._sketch_controls)

        # Pacing controls are shared by the continuous-stroke modes.
        self._continuous_controls = QWidget()
        continuous_layout = QVBoxLayout(self._continuous_controls)
        continuous_layout.setContentsMargins(0, 0, 0, 0)
        continuous_layout.setSpacing(4)
        continuous_layout.addWidget(self._stroke_speed)
        continuous_layout.addWidget(self._event_interval)
        continuous_layout.addWidget(self._travel_delay)
        drawing.add(self._continuous_controls)

        trigger_row = QHBoxLayout()
        trigger_label = QLabel("Trigger distance")
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

        diagnostics = CollapsibleSection("Diagnostics")
        diag_note = QLabel(
            "Calibration aids. For normal use, just press Start drawing."
        )
        diag_note.setObjectName("SectionHint")
        diag_note.setWordWrap(True)
        diagnostics.add(diag_note)
        self._btn_precompute = self._tool_button(
            "Save the plan for next time",
            "download",
            self._on_precompute,
            "Save the stroke map so repeat runs skip processing (drawing time is unchanged)",
        )
        self._btn_test = self._tool_button(
            "Try 20 strokes", "zap", self._on_test_draw, "Draw the first 20 strokes"
        )
        self._btn_simple = self._tool_button(
            "Check brush size",
            "play",
            self._on_simple_test,
            "Draw 5 lines to tune the brush size",
        )
        for button in (self._btn_precompute, self._btn_test, self._btn_simple):
            diagnostics.add(button)

        redraw = Section("Redraw region", "Draw only a rectangle you pick on screen.")
        self._region_label = QLabel("No area selected yet.")
        self._region_label.setObjectName("SectionHint")
        self._region_label.setWordWrap(True)
        redraw.add(self._region_label)
        row2 = QHBoxLayout()
        pick = QPushButton("Select area")
        pick.clicked.connect(self.pick_region)
        draw = QPushButton("Draw area")
        draw.clicked.connect(self._on_draw_region)
        row2.addWidget(pick)
        row2.addWidget(draw)
        redraw.add_layout(row2)
        layout.insertWidget(layout.count() - 1, diagnostics)
        layout.insertWidget(layout.count() - 1, redraw)

        advanced = CollapsibleSection("Advanced")
        self._build_advanced_into(advanced)
        layout.insertWidget(layout.count() - 1, advanced)

        # The global material is demoted below the mode work.
        env = Section(
            "Environment",
            "Where Pyaint finds the canvas and palette. Switch targets above.",
        )
        self._detection_label = QLabel("Pyaint doesn't know where your canvas is yet.")
        self._detection_label.setObjectName("SectionHint")
        self._detection_label.setWordWrap(True)
        env.add(self._detection_label)
        # Target-specific: some desktop palettes need a double-click to select.
        self._chk_mspaint = CheckBox("MS Paint double-click")
        self._chk_mspaint.setToolTip(
            "Some palettes need a double-click to select a colour."
        )
        self._chk_mspaint.toggled.connect(self._on_mspaint_toggled)
        env.add(self._chk_mspaint)
        needs = QLabel(
            "Finding the canvas needs a blank canvas and the target app visible "
            "on the primary monitor at 100% display scaling."
        )
        needs.setObjectName("SectionHint")
        needs.setWordWrap(True)
        env.add(needs)
        layout.insertWidget(layout.count() - 1, env)

        # Appearance is a common preference, so it sits at the top level, not
        # buried inside Advanced.
        appearance = Section(
            "Appearance", "Follow the system theme or choose one explicitly."
        )
        self._theme_combo = QComboBox()
        self._theme_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self._theme_combo.setMinimumContentsLength(8)
        for mode in theme.THEME_MODES:
            self._theme_combo.addItem(theme.THEME_LABELS[mode], mode)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        appearance.add(self._theme_combo)
        layout.insertWidget(layout.count() - 1, appearance)

        # A destructive global action on its own, at the very bottom.
        reset_section = Section("Reset")
        reset = QPushButton("Reset all settings")
        reset.setObjectName("Danger")
        reset.clicked.connect(self._on_reset_config)
        reset_section.add(reset)
        layout.insertWidget(layout.count() - 1, reset_section)

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
        matching = Section("Matching")
        metric_row = QHBoxLayout()
        metric_label = QLabel("Colour matching")
        metric_label.setObjectName("FieldHint")
        self._metric_combo = QComboBox()
        self._metric_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self._metric_combo.setMinimumContentsLength(8)
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
        matching.add_layout(metric_row)
        container.add(matching)

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
