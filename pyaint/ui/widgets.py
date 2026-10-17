"""Reusable Qt widgets for the Pyaint UI."""

from __future__ import annotations

import html
import math
import re
from typing import Optional

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QEasingCurve,
    QEvent,
    QIODevice,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyleOptionButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


from pyaint.ui import bands, modes
from pyaint.ui.paper import paper_path, tokens


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


class SheetCard(QFrame):
    """A QSS-styled card that lifts itself off the desk with a real shadow.

    A stylesheet cannot paint a box-shadow, and a shadow drawn by hand is
    clipped by the widget's own rect -- which is exactly how the old notices
    ended up with a hard-edged slab. The elevation is therefore a widget
    effect: it renders outside the frame, so the falloff follows the rounded
    corners instead of being cut into a rectangle.
    """

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(name)

    def _refresh_shadow(self) -> None:
        t = tokens(self)
        color = QColor(t.get("shadow", "#3C3228"))
        color.setAlpha(min(255, int(t.get("shadow_alpha", 70)) + 40))
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20.0)
        effect.setOffset(0.0, 3.0)
        effect.setColor(color)
        self.setGraphicsEffect(effect)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._refresh_shadow()


class NoticeBanner(SheetCard):
    """A floating, severity-aware notice.

    Anchored by its owner over the desk (never in the layout, so showing it
    moves nothing). The card is opaque: a translucent notice lets the artwork
    show through its own text. Info/success auto-dismiss quickly, warnings a
    little later, and errors persist until dismissed because they carry the
    fix. Hovering holds it open; clicking anywhere on it dismisses it.
    """

    shown = Signal()

    _GLYPHS = {"info": "i", "success": "\u2713", "warning": "!", "error": "\u2715"}
    #: Auto-dismiss delay in ms; 0 means "stay until dismissed".
    _DURATION = {"info": 4000, "success": 4000, "warning": 8000, "error": 0}

    #: Fixed card width; only the height follows the message.
    WIDTH = 460

    def __init__(self, parent=None):
        super().__init__("NoticeBanner", parent)
        self.setProperty("severity", "info")
        self.setFixedWidth(self.WIDTH)
        self._on_action = None
        self._severity = "info"
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear)

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
        self._severity = severity
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
        self._fit_height()
        self.show()
        self.raise_()
        self._arm()

    def _text_width(self) -> int:
        """The width the layout will give the label, without needing a layout.

        A notice can be raised before its window has ever been laid out (a
        startup warning, a failed restore). Asking the label for its current
        width then returns nonsense, so the card is measured from its own fixed
        width and the parts around the label instead.
        """
        layout = self.layout()
        if layout is None:
            return self.WIDTH
        margins = layout.contentsMargins()
        gap = max(0, layout.spacing())
        gaps = 2  # icon | text, text | close
        used = (
            margins.left()
            + margins.right()
            + self._icon.width()
            + self._close.sizeHint().width()
            + gap * gaps
        )
        if not self._action.isHidden():
            used += self._action.sizeHint().width() + gap
        return max(120, self.WIDTH - used)

    def _fit_height(self) -> None:
        """Grow the card to the wrapped message instead of clipping it.

        ``adjustSize()`` sizes from ``sizeHint()``, which measures the label at
        the *hint's* width -- so a message needing a third line at the card's
        real width overflowed the bottom edge.
        """
        layout = self.layout()
        if layout is None:
            return
        self._text.setMinimumHeight(0)
        width = self._text_width()
        if self.isVisible() and self._text.width() > 20:
            # Once laid out, the label's real width is the one it will wrap at.
            width = min(width, self._text.width())
        needed = self._text.heightForWidth(width)
        if needed <= 0:
            needed = self._text.fontMetrics().height()
        self._text.setMinimumHeight(needed)
        layout.activate()
        margins = layout.contentsMargins()
        self.setFixedHeight(max(36, needed + margins.top() + margins.bottom()))

    def _arm(self) -> None:
        delay = self._DURATION.get(self._severity, 0)
        if delay > 0:
            self._timer.start(delay)
        else:
            self._timer.stop()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Fonts and DPI are only final once the widget is on screen.
        self._fit_height()
        self.shown.emit()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._arm()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clear()
        super().mousePressEvent(event)

    def clear(self):
        self._timer.stop()
        self._on_action = None
        self.hide()

    def _run_action(self):
        callback = self._on_action
        if callback is not None:
            callback()

    def _restyle(self):
        self.style().unpolish(self)
        self.style().polish(self)


class SetupRow(QWidget):
    """The setup disclosure row: the control *is* the panel's top edge.

    The whole row is one click target (pointer cursor, hover tint, focus ring,
    Space/Enter), so the chevron never has to be aimed at. The readiness steps
    inside it are **status only** -- no fill, no border, no hover: a check for
    done, a hollow ring for pending. Nothing in the row may look tappable.
    """

    toggled = Signal(bool)

    HEIGHT = 44

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SetupRow")
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("Canvas and palette status — click to review setup.")
        self.setAccessibleName("Setup")
        self.setAccessibleDescription(
            "Shows which setup steps are done. Press to reveal the setup actions."
        )
        self._steps = [("Target", True), ("Canvas", False),
                       ("Image", False), ("Draw", False)]
        self._open = False
        self._hover = False
        self._angle = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_angle)

    # -- state ---------------------------------------------------------
    def steps(self):
        return list(self._steps)

    def update_steps(self, target_name: str, environment_ready: bool,
                     image_ready: bool) -> None:
        """The four readiness checks, in order."""
        self._steps = [
            ("Target", True),
            ("Canvas", bool(environment_ready)),
            ("Image", bool(image_ready)),
            ("Draw", bool(environment_ready and image_ready)),
        ]
        self.update()

    def is_open(self) -> bool:
        return self._open

    def set_open(self, open_: bool) -> None:
        """Set the disclosure state without emitting ``toggled``."""
        open_ = bool(open_)
        if open_ == self._open:
            return
        self._open = open_
        target = 180.0 if open_ else 0.0
        if self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._angle)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._angle = target
            self.update()

    def toggle(self) -> None:
        self.set_open(not self._open)
        self.toggled.emit(self._open)

    def _on_angle(self, value) -> None:
        self._angle = float(value)
        self.update()

    # -- events --------------------------------------------------------
    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.rect().contains(
                event.position().toPoint()):
            self.toggle()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
            return
        super().keyPressEvent(event)

    # -- painting ------------------------------------------------------
    @staticmethod
    def _check(painter: QPainter, cx: float, cy: float, colour: QColor) -> None:
        h = 6.0
        path = QPainterPath(QPointF(cx - h * 0.85, cy))
        path.lineTo(QPointF(cx - h * 0.15, cy + h * 0.65))
        path.lineTo(QPointF(cx + h * 0.9, cy - h * 0.7))
        pen = QPen(colour, 1.7)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

    @staticmethod
    def _ring(painter: QPainter, cx: float, cy: float, colour: QColor) -> None:
        pen = QPen(colour, 1.4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(cx, cy), 5.5, 5.5)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = tokens(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        card = QColor(t.get("bg_card", "#FFFDFA"))
        painter.fillRect(
            QRectF(self.rect()),
            QColor(t.get("bg_hover", card.name())) if self._hover else card,
        )
        painter.setPen(QPen(QColor(t.get("border", "#E6DED2")), 1.0))
        painter.drawLine(QPointF(0, self.height() - 0.5),
                         QPointF(self.width(), self.height() - 0.5))

        ink = QColor(t.get("fg", "#2B2622"))
        muted = QColor(t.get("fg_muted", "#6B6157"))
        success = QColor(t.get("success", "#4F7A4A"))
        pending = QColor(t.get("warning", "#C58A1E"))

        font = QFont(self.font())
        font.setPixelSize(13)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(ink)
        painter.drawText(QRectF(16, 0, 64, self.height()),
                         int(Qt.AlignLeft | Qt.AlignVCenter), "Setup")

        x = 78.0
        cy = self.height() / 2.0
        for label, done in self._steps:
            if done:
                self._check(painter, x + 7, cy, success)
            else:
                self._ring(painter, x + 6, cy, pending)
            font.setPixelSize(12)
            font.setWeight(QFont.Normal if done else QFont.DemiBold)
            painter.setFont(font)
            painter.setPen(muted if done else ink)
            width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(QRectF(x + 18, 0, width + 8, self.height()),
                             int(Qt.AlignLeft | Qt.AlignVCenter), label)
            x += 18 + width + 22

        painter.save()
        painter.translate(self.width() - 24.0, cy)
        painter.rotate(self._angle)
        chevron = QPainterPath(QPointF(-8, -4.0))
        chevron.lineTo(QPointF(0, 4.0))
        chevron.lineTo(QPointF(8, -4.0))
        pen = QPen(ink, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(chevron)
        painter.restore()

        if self.hasFocus():
            pen = QPen(QColor(t.get("accent", "#B8542F")), 2.0)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(pen)
            painter.drawRoundedRect(
                QRectF(self.rect()).adjusted(2, 2, -2, -2), 8, 8)
        painter.end()


class _SectionChevron(QWidget):
    """A small painted chevron: down when open, right when collapsed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._open = False

    def set_open(self, open_: bool) -> None:
        open_ = bool(open_)
        if open_ != self._open:
            self._open = open_
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = tokens(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(t.get("fg_muted", "#6B6157")), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.rotate(0.0 if self._open else -90.0)
        path = QPainterPath(QPointF(-3.5, -2.0))
        path.lineTo(QPointF(0.0, 1.5))
        path.lineTo(QPointF(3.5, -2.0))
        painter.drawPath(path)


class SectionHeader(QWidget):
    """A section title, with an optional disclosure chevron on the right.

    Collapsible headers use the same dark title type as a plain section, so a
    closed section still reads as a heading rather than a muted label. For an
    interactive header the whole row is the click target (pointer cursor, hover
    tint, Space/Enter), and the chevron sits at the trailing edge where a
    disclosure is expected.
    """

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        collapsible: bool = False,
        nested: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("SectionHeader")
        self.setProperty("collapsible", collapsible)
        self.setProperty("nested", nested)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._collapsible = collapsible
        self._open = False

        # The header owns the section inset, so the title and the body below it
        # share one rail. A nested header adds no inset: its parent body already
        # provides it.
        layout = QHBoxLayout(self)
        if nested:
            layout.setContentsMargins(0, 8, 0, 2)
        else:
            layout.setContentsMargins(12, 12, 12, 2)
        layout.setSpacing(6)

        self._title = QLabel(title)
        self._title.setObjectName("SectionSubtitle" if nested else "SectionTitle")
        self._title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title, 1)

        self._chevron = _SectionChevron()
        self._chevron.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._chevron.setVisible(collapsible)
        layout.addWidget(self._chevron)

        if collapsible:
            self.setCursor(Qt.PointingHandCursor)
            self.setFocusPolicy(Qt.StrongFocus)
            self.setAccessibleName(title)
            self.setAccessibleDescription(
                "Press to expand or collapse this section."
            )
            self._set_chevron(False)

    # -- state ---------------------------------------------------------
    def is_open(self) -> bool:
        return self._open

    def set_open(self, open_: bool) -> None:
        """Set the disclosure state without emitting ``toggled``."""
        if not self._collapsible:
            return
        self._open = bool(open_)
        self._set_chevron(self._open)

    def toggle(self) -> None:
        if not self._collapsible:
            return
        self.set_open(not self._open)
        self.toggled.emit(self._open)

    def _set_chevron(self, open_: bool) -> None:
        self._chevron.set_open(open_)
        if self._collapsible:
            self.setAccessibleDescription(
                "Expanded. Press to collapse this section."
                if open_
                else "Collapsed. Press to expand this section."
            )

    # -- events --------------------------------------------------------
    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if (
            self._collapsible
            and event.button() == Qt.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.toggle()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self._collapsible and event.key() in (
            Qt.Key_Space,
            Qt.Key_Return,
            Qt.Key_Enter,
        ):
            self.toggle()
            event.accept()
            return
        super().keyPressEvent(event)


class CollapsibleSection(QFrame):
    """A section whose body can be expanded/collapsed from its header."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        expanded: bool = False,
        nested: bool = False,
        hint: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("Section")
        self.setProperty("nested", nested)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 4 if nested else 8)
        self._layout.setSpacing(2)

        self._header = SectionHeader(title, collapsible=True, nested=nested)
        self._header.toggled.connect(self._on_toggle)
        self._layout.addWidget(self._header)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("SectionSubHint" if nested else "SectionHint")
            hint_label.setWordWrap(True)
            self._layout.addWidget(hint_label)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        inset = 0 if nested else 12
        self._body_layout.setContentsMargins(inset, 0, inset, 0)
        self._body_layout.setSpacing(4)
        self._layout.addWidget(self._body)

        self.set_expanded(expanded)

    @property
    def header(self) -> SectionHeader:
        return self._header

    def add(self, widget: QWidget) -> QWidget:
        self._body_layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._body_layout.addLayout(layout)

    def is_expanded(self) -> bool:
        return self._header.is_open()

    def set_expanded(self, expanded: bool) -> None:
        """Open or close the body without emitting ``toggled``."""
        self._header.set_open(expanded)
        self._body.setVisible(bool(expanded))

    def _on_toggle(self, checked: bool) -> None:
        self._body.setVisible(bool(checked))
        self.toggled.emit(bool(checked))


class Section(QFrame):
    """A titled group of controls with a bottom divider.

    Controls live in an inner container with the same horizontal inset as the
    title, so every section shares one content rail. ``nested`` drops the
    inset (and the divider) for subgroups inside another section's body.
    """

    def __init__(
        self,
        title: str,
        hint: Optional[str] = None,
        nested: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("Section")
        self.setProperty("nested", nested)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 4 if nested else 8)
        self._layout.setSpacing(2)

        self._header = SectionHeader(title, nested=nested)
        self._layout.addWidget(self._header)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("SectionSubHint" if nested else "SectionHint")
            hint_label.setWordWrap(True)
            self._layout.addWidget(hint_label)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        inset = 0 if nested else 12
        self._body_layout.setContentsMargins(inset, 0, inset, 0)
        self._body_layout.setSpacing(4)
        self._layout.addWidget(self._body)

    @property
    def header(self) -> SectionHeader:
        return self._header

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
    """A labelled slider showing ``value unit · band``.

    The number keeps settings reproducible from a screenshot; the band word
    keeps them readable. ``control`` is a key in :mod:`pyaint.ui.bands`.

    The pip meter was removed on purpose: the value and the band word already
    carry the read, and the pips only added row noise (see the conformance
    review).
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

    def value(self) -> float:
        return self._slider.value() * self._resolution

    def set_value(self, value: float, emit: bool = False) -> None:
        self._block = not emit
        self._slider.setValue(round(value / self._resolution))
        self._update_label(value)
        self._block = False


class GuidePanel(QFrame):
    """A docked "voice" note with a fixed seat and a fixed minimum height.

    It talks to the user in plain prose; the note is swapped as the cursor
    moves, but the panel never resizes with its copy, so nothing jumps.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GuidePanel")
        # Fixed seat: the note can change freely without resizing the layout.
        self.setFixedHeight(52)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(0)
        self._text = QLabel()
        self._text.setObjectName("GuideText")
        self._text.setWordWrap(True)
        outer.addWidget(self._text)

    def set_mark_color(self, color: str) -> None:
        """Kept for compatibility; the mark now lives on the straddling badge."""

    def set_note(self, kicker: str, text: str) -> None:
        # The "About this mode" kicker was removed by request; only the note is
        # shown. The argument is kept so existing callers need no change.
        self._text.setText(text or "")


class ModeRail(QWidget):
    """A single-choice mode picker: one *Mode* heading, family subheadings,
    and radio items.

    Exactly one mode is active at any time; the radio dots make that explicit
    across the ``Runs`` and ``Contours`` families, which only describe how the
    modes produce the image.
    """

    modeChanged = Signal(str)

    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeRail")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Mode")
        title.setObjectName("FieldLabel")
        header.addWidget(title)
        header.addStretch(1)
        hint = QLabel("choose one")
        hint.setObjectName("FieldHint")
        header.addWidget(hint)
        layout.addLayout(header)
        layout.addSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}
        for family, items in modes.MODE_FAMILIES:
            family_label = QLabel(family)
            family_label.setObjectName("FamilyLabel")
            layout.addWidget(family_label)
            for name, mode in items:
                button = QRadioButton(name)
                button.setObjectName("ModeRailItem")
                button.setChecked(mode == current)
                button.toggled.connect(
                    lambda checked, m=mode: self._on_toggled(checked, m)
                )
                button.installEventFilter(self)
                self._group.addButton(button)
                self._buttons[mode] = button
                layout.addWidget(button)
        layout.addStretch(1)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        # Repaint so the hover highlight tracks the pointer; the shape is the
        # same irregular quad as the selection, only the fill differs.
        if event.type() in (QEvent.Enter, QEvent.Leave):
            self.update()
        return super().eventFilter(obj, event)

    def paintEvent(self, event) -> None:  # noqa: N802
        """One rounded highlight behind the selected *or* hovered mode.

        Both states use the same shape: hovering shows it in a quiet tone,
        selecting fills it with the accent. Unselected modes carry no surface
        at all, so four blocks never sit side by side.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        t = tokens(self)
        accent = QColor(t.get("accent", "#E07856"))
        hover = QColor(t.get("bg_hover", "#302B27"))
        for mode, button in self._buttons.items():
            selected = button.isChecked()
            if not (selected or button.underMouse()):
                continue
            rect = QRectF(button.geometry()).adjusted(-5, 0, 5, 0)
            seed = 6100 + (sum(ord(c) for c in mode) % 500)
            path = paper_path(rect, "mode", seed_key=seed, inset=0.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent if selected else hover)
            painter.drawPath(path)
        painter.end()

    def _on_toggled(self, checked: bool, mode: str) -> None:
        if checked:
            self.modeChanged.emit(mode)

    def mode(self) -> str:
        """The active mode, or '' if nothing is selected."""
        for mode, button in self._buttons.items():
            if button.isChecked():
                return mode
        return ""

    def set_mode(self, mode: str) -> None:
        """Select ``mode`` without re-emitting when it is already active."""
        button = self._buttons.get(mode)
        if button is not None and not button.isChecked():
            button.setChecked(True)



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
