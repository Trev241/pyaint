"""Reusable Qt widgets for the Pyaint UI."""

from __future__ import annotations

import html
import re
from typing import Optional

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QPointF,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QImage, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyleOptionButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


from pyaint.ui import bands


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


class CheckBoxField(QWidget):
    """A checkbox with an optional one-line description underneath it.

    The plain :class:`CheckBox` only carries a tooltip; an on-screen hint is
    far easier to discover, so the tunable controls use this wrapper.
    """

    toggled = Signal(bool)

    def __init__(self, label: str, hint: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        self._check = CheckBox(label)
        self._check.toggled.connect(self._on_toggled)
        layout.addWidget(self._check)

        self._hint = QLabel()
        self._hint.setObjectName("FieldHint")
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)
        self.set_hint(hint)

    def _on_toggled(self, checked: bool) -> None:
        self.toggled.emit(checked)

    def set_hint(self, text: str) -> None:
        self._hint.setText(text or "")
        self._hint.setVisible(bool(text))

    def isChecked(self) -> bool:  # noqa: N802 - Qt-style API
        return self._check.isChecked()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt-style API
        self._check.setChecked(checked)

    def setToolTip(self, text: str) -> None:  # noqa: N802 - Qt-style API
        super().setToolTip(text)
        self._check.setToolTip(text)

    def blockSignals(self, block: bool) -> bool:  # noqa: N802 - Qt-style API
        # The public ``toggled`` signal is forwarded manually, so block the
        # inner checkbox to suppress it as Qt callers expect.
        self._check.blockSignals(block)
        return super().blockSignals(block)


class SegmentedControl(QWidget):
    """A compact grid of mutually-exclusive, checkable buttons.

    ``options`` is a sequence of ``(key, label)`` pairs; ``changed`` fires with
    the key when the user picks one. ``set_value`` never emits, so the owner
    can sync the control without re-triggering its own handler.
    """

    changed = Signal(str)

    def __init__(self, options, columns: int = 0, parent=None):
        super().__init__(parent)
        self.setObjectName("SegmentedGroup")
        self._buttons: dict = {}
        columns = columns or len(options)

        grid = QGridLayout(self)
        grid.setContentsMargins(1, 1, 1, 1)
        grid.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for index, (key, label) in enumerate(options):
            button = QPushButton(label)
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda checked, k=key: self._on_clicked(k, checked)
            )
            self._group.addButton(button)
            self._buttons[key] = button
            grid.addWidget(button, index // columns, index % columns)
        for column in range(columns):
            grid.setColumnStretch(column, 1)

    def _on_clicked(self, key: str, checked: bool) -> None:
        if checked:
            self.changed.emit(key)

    def value(self):
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return None

    def set_value(self, key) -> None:
        # Relax exclusivity while clearing so the group can momentarily hold no
        # checked button (e.g. switching straight from one preset to another).
        self._group.setExclusive(False)
        for item_key, button in self._buttons.items():
            button.setChecked(item_key == key)
        self._group.setExclusive(True)


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

    def set_expanded(self, expanded: bool) -> None:
        """Open or close the body without needing a click on the header."""
        self._toggle.setChecked(expanded)
        self._on_toggle(expanded)

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
        hint: str = "",
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

        self._hint = QLabel()
        self._hint.setObjectName("FieldHint")
        self._hint.setWordWrap(True)
        outer.addWidget(self._hint)
        self.set_hint(hint)

        self._update_label(value)

    def set_hint(self, text: str) -> None:
        self._hint.setText(text or "")
        self._hint.setVisible(bool(text))

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


class BandPips(QWidget):
    """A small meter that lights one pip per descriptor band.

    Shows at a glance which qualitative band a continuous value sits in, so a
    slider reads like a mode without pretending to be discrete.
    """

    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self._count = max(1, int(count))
        self._index = 0
        self.setFixedSize(self._count * 11 + 2, 12)

    def set_index(self, index: int) -> None:
        index = max(0, min(self._count - 1, int(index)))
        if index != self._index:
            self._index = index
            self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        on = self.palette().color(QPalette.ColorRole.Highlight)
        off = self.palette().color(QPalette.ColorRole.Mid)
        for i in range(self._count):
            painter.setBrush(on if i <= self._index else off)
            painter.drawRoundedRect(QRectF(i * 11 + 1, 4, 9, 4), 2, 2)
        painter.end()


class DualReadoutSlider(QWidget):
    """A labelled slider showing ``value unit · band`` and a pip meter.

    The number keeps settings reproducible from a screenshot; the band word
    keeps them readable. ``control`` is a key in :mod:`pyaint.ui.bands`.
    """

    changed = Signal(float)

    def __init__(
        self,
        label: str,
        control: str,
        minimum: float,
        maximum: float,
        value: float,
        resolution: float = 0.01,
        hint: str = "",
        pips: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._control = control
        self._resolution = resolution
        self._block = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        self._label = QLabel(label)
        self._label.setObjectName("FieldLabel")
        header.addWidget(self._label)
        count = bands.band_count(control)
        self._pips = BandPips(count) if (pips and count) else None
        if self._pips is not None:
            header.addWidget(self._pips)
        header.addStretch(1)
        self._value_label = QLabel()
        self._value_label.setObjectName("FieldValue")
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self._value_label)
        self._band_label = QLabel()
        self._band_label.setObjectName("FieldBand")
        header.addWidget(self._band_label)
        outer.addLayout(header)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(round(minimum / resolution))
        self._slider.setMaximum(round(maximum / resolution))
        self._slider.setValue(round(value / resolution))
        self._slider.valueChanged.connect(self._on_slider)
        outer.addWidget(self._slider)

        self._hint = QLabel()
        self._hint.setObjectName("FieldHint")
        self._hint.setWordWrap(True)
        outer.addWidget(self._hint)
        self.set_hint(hint)
        self._update_label(value)

    def set_hint(self, text: str) -> None:
        self._hint.setText(text or "")
        self._hint.setVisible(bool(text))

    def _on_slider(self, raw: int) -> None:
        value = raw * self._resolution
        self._update_label(value)
        if not self._block:
            self.changed.emit(value)

    def _format_number(self, value: float) -> str:
        if self._resolution >= 1:
            number = str(int(round(value)))
        else:
            number = f"{value:.2f}"
        unit = bands.unit(self._control)
        if unit == "%":
            return f"{number}%"
        if unit:
            return f"{number} {unit}"
        return number

    def _update_label(self, value: float) -> None:
        self._value_label.setText(self._format_number(value))
        self._band_label.setText(bands.describe(self._control, value))
        if self._pips is not None:
            self._pips.set_index(bands.band_index(self._control, value))

    def value(self) -> float:
        return self._slider.value() * self._resolution

    def set_value(self, value: float, emit: bool = False) -> None:
        self._block = not emit
        self._slider.setValue(round(value / self._resolution))
        self._update_label(value)
        self._block = False


# ---------------------------------------------------------------------------
# Drag & drop helpers
#
# Browsers do not hand over image files on a drag: they publish an http(s) URL
# (``text/uri-list``), an HTML fragment (``text/html``), a ``data:`` URI, or,
# for some apps, raw image bytes. Only local files appear in ``urls()`` as
# ``isLocalFile()``; everything else must be recognised from the other formats.
# ---------------------------------------------------------------------------

_RAW_IMAGE_FORMATS = (
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
)
_DATA_URI_RE = re.compile(
    r"data:image/[A-Za-z0-9.+-]+(?:;base64)?,[A-Za-z0-9+/=%\-_.~]+"
)
_IMG_SRC_RE = re.compile(r"""<img[^>]+src\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)
_URL_IN_TEXT_RE = re.compile(r"(?:https?://|data:image/)[^\s\"'<>]+")


def _mime_text(mime, fmt: str) -> str:
    """Decode a textual MIME payload, tolerating malformed clipboard data."""
    if not mime.hasFormat(fmt):
        return ""
    try:
        return bytes(mime.data(fmt)).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001 - a bad payload is not fatal
        return ""


def local_path_from_mime(mime) -> Optional[str]:
    """The first dropped local file path, if any."""
    if not mime.hasUrls():
        return None
    for url in mime.urls():
        if url.isLocalFile():
            return url.toLocalFile()
    return None


def remote_source_from_mime(mime) -> Optional[str]:
    """The first droppable remote image source: an http(s) or ``data:`` URL.

    A real image URL is preferred over an embedded ``data:`` thumbnail, so a
    browser drag from an image grid loads the full-resolution file when one is
    offered.
    """
    html_text = _mime_text(mime, "text/html")
    html_match = _IMG_SRC_RE.search(html_text) if html_text else None
    if html_match:
        candidate = html.unescape(html_match.group(1)).strip()
        if candidate.startswith(("http://", "https://")):
            return candidate
    if mime.hasUrls():
        for url in mime.urls():
            text = url.toString()
            if text.startswith(("http://", "https://")):
                return text
    for fmt in ("text/html", "text/uri-list", "text/plain"):
        text = _mime_text(mime, fmt)
        if not text:
            continue
        data_match = _DATA_URI_RE.search(text)
        if data_match:
            return data_match.group(0)
        url_match = _URL_IN_TEXT_RE.search(text)
        if url_match:
            return url_match.group(0)
    return None


def raw_image_from_mime(mime) -> Optional[bytes]:
    """Raw image bytes carried directly in the drag payload."""
    for fmt in _RAW_IMAGE_FORMATS:
        if mime.hasFormat(fmt):
            raw = bytes(mime.data(fmt))
            if raw:
                return raw
    image_data = mime.imageData() if mime.hasImage() else None
    if isinstance(image_data, QByteArray):
        return bytes(image_data)
    if isinstance(image_data, (QImage, QPixmap)):
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image_data.save(buffer, "PNG")
        return bytes(buffer.data())
    return None


def accepts_image_drop(mime) -> bool:
    """Whether a drag payload can become an image (local, remote, or raw)."""
    return bool(
        local_path_from_mime(mime)
        or remote_source_from_mime(mime)
        or raw_image_from_mime(mime) is not None
    )


class ImagePreview(QLabel):
    """A label that scales its pixmap to fit while preserving aspect ratio.

    Accepts local image files dropped onto it and reports the path through
    :attr:`fileDropped`; the frame highlights while a valid file is hovered.
    """

    fileDropped = Signal(str)
    remoteDropped = Signal(str)
    rawDropped = Signal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewImage")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
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
    def dragEnterEvent(self, event):  # noqa: N802
        if accepts_image_drop(event.mimeData()):
            self._set_drag_active(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802
        if accepts_image_drop(event.mimeData()):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):  # noqa: N802
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # noqa: N802
        mime = event.mimeData()
        path = local_path_from_mime(mime)
        remote = None if path else remote_source_from_mime(mime)
        raw = None if (path or remote) else raw_image_from_mime(mime)
        self._set_drag_active(False)
        if path:
            event.acceptProposedAction()
            self.fileDropped.emit(path)
        elif remote:
            event.acceptProposedAction()
            self.remoteDropped.emit(remote)
        elif raw is not None:
            event.acceptProposedAction()
            self.rawDropped.emit(raw)

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
        # ``contentsRect`` (not ``size``) so a margin/padding on the label is
        # respected and the scaled image never spills over the text padding.
        scaled = self._original.scaled(
            self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)


class GalleryTile(QFrame):
    """One clickable thumbnail in the search gallery (a masonry cell)."""

    clicked = Signal(object)

    def __init__(self, candidate, parent=None):
        super().__init__(parent)
        self.candidate = candidate
        self.setObjectName("GalleryTile")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(candidate.title)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._image = QLabel()
        self._image.setObjectName("GalleryImage")
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setMinimumHeight(60)
        layout.addWidget(self._image)

        self._pixmap: Optional[QPixmap] = None
        self._column_width = 180
        ratio = (candidate.height / candidate.width) if candidate.width else 0.75
        self._ratio = max(0.25, min(4.0, ratio))

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._refresh()

    def set_column_width(self, width: int) -> None:
        self._column_width = max(1, width)
        self._refresh()

    def preferred_height(self, width: int) -> int:
        return max(60, int(width * self._ratio))

    def _refresh(self) -> None:
        if self._pixmap is None:
            return
        height = self.preferred_height(self._column_width)
        self._image.setFixedHeight(height)
        self._image.setPixmap(
            self._pixmap.scaled(
                self._column_width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.candidate)
        super().mousePressEvent(event)


class MasonryGallery(QScrollArea):
    """A Pinterest-style, lazily-filled gallery of image thumbnails.

    Tiles are sized from each image's aspect ratio and packed into the
    currently-shortest column, reflowing when the panel is resized. Emits
    ``nearBottom`` so the owner can page in more results while scrolling.
    """

    candidateSelected = Signal(object)
    nearBottom = Signal()

    TARGET_COLUMN = 190
    SPACING = 8
    MARGIN = 8
    NEAR_BOTTOM_PX = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Gallery")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._container.setObjectName("GalleryContainer")
        self.setWidget(self._container)
        self._tiles: list = []
        self._by_url: dict = {}
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    # -- population -----------------------------------------------------
    def add_candidates(self, candidates) -> None:
        for candidate in candidates:
            tile = GalleryTile(candidate)
            tile.clicked.connect(self.candidateSelected)
            tile.setParent(self._container)
            tile.show()
            self._tiles.append(tile)
            self._by_url[candidate.thumb_url] = tile
        self._relayout()

    def add_candidate(self, candidate) -> GalleryTile:
        self.add_candidates([candidate])
        return self._tiles[-1]

    def clear(self) -> None:
        for tile in self._tiles:
            tile.setParent(None)
            tile.deleteLater()
        self._tiles = []
        self._by_url = {}
        self._container.setMinimumHeight(0)

    def count(self) -> int:
        return len(self._tiles)

    def first_candidate(self):
        return self._tiles[0].candidate if self._tiles else None

    def set_thumbnail(self, url: str, pixmap: QPixmap) -> None:
        tile = self._by_url.get(url)
        if tile is not None:
            tile.set_thumbnail(pixmap)

    # -- layout ---------------------------------------------------------
    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _columns(self):
        width = max(1, self.viewport().width() - 2 * self.MARGIN)
        columns = max(
            1, (width + self.SPACING) // (self.TARGET_COLUMN + self.SPACING)
        )
        column_width = (width - (columns - 1) * self.SPACING) // columns
        return columns, max(40, column_width)

    def _relayout(self) -> None:
        columns, column_width = self._columns()
        heights = [self.MARGIN] * columns
        for tile in self._tiles:
            column = min(range(columns), key=lambda c: heights[c])
            x = self.MARGIN + column * (column_width + self.SPACING)
            y = heights[column]
            height = tile.preferred_height(column_width)
            tile.set_column_width(column_width)
            tile.setGeometry(x, y, column_width, height)
            heights[column] = y + height + self.SPACING
        self._container.setMinimumHeight(max(heights) + self.MARGIN)

    def _on_scroll(self, value: int) -> None:
        bar = self.verticalScrollBar()
        if bar.maximum() - value <= self.NEAR_BOTTOM_PX:
            self.nearBottom.emit()
