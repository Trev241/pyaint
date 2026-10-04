"""Reusable Qt widgets for the Pyaint UI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QStyleOptionButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def pil_to_qpixmap(image) -> QPixmap:
    """Convert a PIL image to a QPixmap without depending on Pillow's Qt glue."""
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class CheckBox(QCheckBox):
    """A QCheckBox that draws a real check mark over the accent-filled box.

    Qt's stylesheet does not render a check glyph for ``QCheckBox::indicator``
    once the indicator is customised, so the default look is an unlabelled
    filled square. This paints the missing check on top.
    """

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self.isChecked():
            return

        option = QStyleOptionButton()
        option.initFrom(self)
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = self.palette().color(QPalette.ColorRole.HighlightedText)
        pen = QPen(color)
        pen.setWidthF(max(1.4, indicator.width() * 0.14))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        left = indicator.left()
        top = indicator.top()
        width = indicator.width()
        height = indicator.height()
        painter.drawPolyline([
            QPointF(left + width * 0.22, top + height * 0.52),
            QPointF(left + width * 0.42, top + height * 0.72),
            QPointF(left + width * 0.82, top + height * 0.22),
        ])
        painter.end()


class NoticeBanner(QFrame):
    """A persistent, severity-aware message bar.

    Used for the things a user must not miss: what is blocking a draw, what
    failed, or the result of a switch. It stays visible until replaced or
    dismissed, unlike a transient status-bar message.
    """

    _GLYPHS = {"info": "i", "success": "\u2713", "warning": "!", "error": "\u2715"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NoticeBanner")
        self.setProperty("severity", "info")
        self._on_action = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._icon = QLabel()
        self._icon.setObjectName("NoticeIcon")
        self._icon.setFixedWidth(16)
        layout.addWidget(self._icon)

        self._text = QLabel()
        self._text.setObjectName("NoticeText")
        self._text.setWordWrap(True)
        layout.addWidget(self._text, 1)

        self._action = QPushButton()
        self._action.setObjectName("NoticeAction")
        self._action.clicked.connect(self._run_action)
        self._action.hide()
        layout.addWidget(self._action)

        self._close = QToolButton()
        self._close.setObjectName("NoticeClose")
        self._close.setText("\u2715")
        self._close.setToolTip("Dismiss")
        self._close.clicked.connect(self.clear)
        layout.addWidget(self._close)

        self.hide()

    def show_notice(self, text, severity="info", action_text=None, on_action=None):
        """Show a message; ``on_action`` runs when the action button is used."""
        severity = severity if severity in self._GLYPHS else "info"
        self.setProperty("severity", severity)
        self._icon.setText(self._GLYPHS[severity])
        self._text.setText(text)
        self._on_action = on_action
        if action_text and on_action is not None:
            self._action.setText(action_text)
            self._action.show()
        else:
            self._action.hide()
        self._restyle()
        self.show()

    def clear(self):
        self._on_action = None
        self.hide()

    def _run_action(self):
        callback = self._on_action
        if callback is not None:
            callback()

    def _restyle(self):
        self.style().unpolish(self)
        self.style().polish(self)


class ReadinessStrip(QFrame):
    """A compact step indicator: Target › Canvas & palette › Image › Draw."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReadinessStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        self._chips = []
        for index, text in enumerate(("Target", "Canvas & palette", "Image", "Draw")):
            if index:
                separator = QLabel("›")
                separator.setObjectName("ReadySep")
                layout.addWidget(separator)
            chip = QLabel(text)
            chip.setObjectName("ReadyChip")
            chip.setProperty("done", False)
            layout.addWidget(chip)
            self._chips.append(chip)
        layout.addStretch(1)

    def _set_step(self, index: int, text: str, done: bool) -> None:
        chip = self._chips[index]
        chip.setText(("✓ " if done else "✗ ") + text)
        chip.setProperty("done", bool(done))
        chip.setProperty("state", "done" if done else "missing")
        chip.style().unpolish(chip)
        chip.style().polish(chip)

    def update_steps(self, target_name: str, environment_ready: bool, image_ready: bool) -> None:
        self._set_step(0, f"Target · {target_name}", True)
        self._set_step(1, "Canvas & palette", environment_ready)
        self._set_step(2, "Image", image_ready)
        self._set_step(3, "Draw", environment_ready and image_ready)
        ready = environment_ready and image_ready
        self.setProperty("ready", bool(ready))
        self.style().unpolish(self)
        self.style().polish(self)


class CollapsibleSection(QFrame):
    """A section whose body can be expanded/collapsed by clicking its header."""

    def __init__(self, title: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("Section")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 8)
        self._layout.setSpacing(4)

        self._toggle = QToolButton()
        self._toggle.setObjectName("CollapsibleHeader")
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(expanded)
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self._toggle.clicked.connect(self._on_toggle)
        self._layout.addWidget(self._toggle)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(4)
        self._body.setVisible(expanded)
        self._layout.addWidget(self._body)

    def add(self, widget: QWidget) -> QWidget:
        self._body_layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._body_layout.addLayout(layout)

    def _on_toggle(self, checked: bool) -> None:
        self._toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._body.setVisible(checked)


class Section(QFrame):
    """A titled group of controls with a bottom divider.

    Controls live in an inner container with horizontal padding so inputs and
    buttons no longer touch the edges of the side panel.
    """

    def __init__(self, title: str, hint: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Section")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 8)
        self._layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        self._layout.addWidget(title_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("SectionHint")
            hint_label.setWordWrap(True)
            self._layout.addWidget(hint_label)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12, 0, 12, 0)
        self._body_layout.setSpacing(4)
        self._layout.addWidget(self._body)

    def add(self, widget: QWidget) -> QWidget:
        self._body_layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._body_layout.addLayout(layout)


class SliderField(QWidget):
    """A labelled slider with a live value readout.

    ``resolution`` is the smallest step; values are integers internally, so a
    resolution of ``0.01`` maps the slider range to floats with two decimals.
    """

    changed = Signal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        resolution: float = 0.01,
        parent=None,
    ):
        super().__init__(parent)
        self._resolution = resolution
        self._block = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(label)
        self._label.setObjectName("FieldLabel")
        self._label.setContentsMargins(0, 0, 0, 0)
        self._value_label = QLabel()
        self._value_label.setObjectName("FieldValue")
        self._value_label.setContentsMargins(0, 0, 0, 0)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self._label)
        header.addStretch(1)
        header.addWidget(self._value_label)
        outer.addLayout(header)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(round(minimum / resolution))
        self._slider.setMaximum(round(maximum / resolution))
        self._slider.setValue(round(value / resolution))
        self._slider.valueChanged.connect(self._on_slider)
        outer.addWidget(self._slider)

        self._update_label(value)

    def _on_slider(self, raw: int) -> None:
        value = raw * self._resolution
        self._update_label(value)
        if not self._block:
            self.changed.emit(value)

    def _update_label(self, value: float) -> None:
        if self._resolution >= 1:
            self._value_label.setText(str(int(round(value))))
        else:
            self._value_label.setText(f"{value:.2f}")

    def value(self) -> float:
        return self._slider.value() * self._resolution

    def set_value(self, value: float, emit: bool = False) -> None:
        self._block = not emit
        self._slider.setValue(round(value / self._resolution))
        self._update_label(value)
        self._block = False


class ToolControls(QFrame):
    """Enable + modifier (+ optional delay) controls for one taught tool.

    Mutates the tool's entry dict in place and emits ``changed`` so the window
    can persist. The enable/modifier controls are disabled until the tool has
    been taught (``entry["status"]`` is true).
    """

    changed = Signal()

    def __init__(self, title: str, get_entry, supports_delay: bool = False, parent=None):
        super().__init__(parent)
        self.name = title
        self._get_entry = get_entry
        self._loading = True
        self.setObjectName("ToolControls")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setObjectName("FieldHint")
        self._enable = CheckBox("Enable")
        self._enable.toggled.connect(self._on_enable)
        header.addWidget(label)
        header.addStretch(1)
        header.addWidget(self._enable)
        layout.addLayout(header)

        mods = QHBoxLayout()
        mods.setContentsMargins(0, 0, 0, 0)
        mods_label = QLabel("Modifiers")
        mods_label.setObjectName("FieldHint")
        mods.addWidget(mods_label)
        self._mods = {}
        for key in ("ctrl", "alt", "shift"):
            box = CheckBox(key.capitalize())
            box.toggled.connect(self._on_modifiers)
            self._mods[key] = box
            mods.addWidget(box)
        mods.addStretch(1)
        layout.addLayout(mods)

        self._delay = None
        if supports_delay:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            delay_label = QLabel("Delay")
            delay_label.setObjectName("FieldHint")
            self._delay = QSpinBox()
            self._delay.setRange(0, 5000)
            self._delay.setSingleStep(50)
            self._delay.setSuffix(" ms")
            self._delay.valueChanged.connect(self._on_delay)
            row.addWidget(delay_label)
            row.addStretch(1)
            row.addWidget(self._delay)
            layout.addLayout(row)

        self._status = QLabel("Not configured — teach it in Setup to enable.")
        self._status.setObjectName("FieldHint")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._loading = False
        self.refresh()

    def _on_enable(self, checked: bool) -> None:
        if self._loading:
            return
        self._get_entry()["enabled"] = bool(checked)
        self.changed.emit()

    def _on_modifiers(self) -> None:
        if self._loading:
            return
        self._get_entry()["modifiers"] = {k: b.isChecked() for k, b in self._mods.items()}
        self.changed.emit()

    def _on_delay(self, milliseconds: int) -> None:
        if self._loading:
            return
        self._get_entry()["delay"] = milliseconds / 1000.0
        self.changed.emit()

    def refresh(self) -> None:
        entry = self._get_entry()
        self._loading = True
        status = bool(entry.get("status"))
        self._enable.setChecked(bool(entry.get("enabled")))
        self._enable.setEnabled(status)
        modifiers = entry.get("modifiers", {}) or {}
        for key, box in self._mods.items():
            box.setChecked(bool(modifiers.get(key, False)))
            box.setEnabled(status)
        if self._delay is not None:
            self._delay.setValue(int(float(entry.get("delay", 0.1)) * 1000))
            self._delay.setEnabled(status)
        self._status.setVisible(not status)
        self._loading = False


class ImagePreview(QLabel):
    """A label that scales its pixmap to fit while preserving aspect ratio.

    Accepts local image files dropped onto it and reports the path through
    :attr:`fileDropped`; the frame highlights while a valid file is hovered.
    """

    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewImage")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(200, 160)
        self.setAcceptDrops(True)
        self._original: Optional[QPixmap] = None

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._original = pixmap
        self._rescale()

    def set_placeholder(self, text: str) -> None:
        self._original = None
        self.setText(text)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    # -- drag & drop ----------------------------------------------------
    @staticmethod
    def _first_local_file(event) -> Optional[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if url.isLocalFile():
                return url.toLocalFile()
        return None

    def dragEnterEvent(self, event):  # noqa: N802
        if self._first_local_file(event):
            self._set_drag_active(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802
        if self._first_local_file(event):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):  # noqa: N802
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # noqa: N802
        path = self._first_local_file(event)
        self._set_drag_active(False)
        if path:
            event.acceptProposedAction()
            self.fileDropped.emit(path)

    def _set_drag_active(self, active: bool) -> None:
        if getattr(self, "_drag_active", False) == active:
            return
        self._drag_active = active
        self.setProperty("dragActive", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _rescale(self) -> None:
        if self._original is None:
            return
        scaled = self._original.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
