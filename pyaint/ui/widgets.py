"""Reusable Qt widgets for the Pyaint UI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def pil_to_qpixmap(image) -> QPixmap:
    """Convert a PIL image to a QPixmap without depending on Pillow's Qt glue."""
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class Section(QFrame):
    """A titled group of controls with a bottom divider."""

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

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


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
        outer.setContentsMargins(12, 4, 12, 4)
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
        self._get_entry = get_entry
        self._loading = True
        self.setObjectName("ToolControls")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setObjectName("FieldHint")
        self._enable = QCheckBox("Enable")
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
            box = QCheckBox(key.capitalize())
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
        self._loading = False


class ImagePreview(QLabel):
    """A label that scales its pixmap to fit while preserving aspect ratio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewImage")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(200, 160)
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

    def _rescale(self) -> None:
        if self._original is None:
            return
        scaled = self._original.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
