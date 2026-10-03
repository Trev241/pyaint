"""Reusable Qt widgets for the Pyaint UI."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
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
