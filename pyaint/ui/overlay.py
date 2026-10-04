"""Floating, always-on-top progress overlay.

Shown while a drawing task runs so the user can see progress over the target
app (the main window is minimized during a draw). It is click-through and
never takes focus, so it cannot block the bot's synthetic clicks on the target
app. Pause and stop are keyboard-only (the global hotkey listener), because
the bot owns the mouse while drawing.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyaint import utils


def _format_eta(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"
    return f"{int(seconds // 3600)}:{int((seconds % 3600) // 60):02d}h"


class ProgressOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._pause_key = "p"
        self._paused = False
        self.setFixedWidth(380)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("ProgressOverlay")
        self._card = card
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        self._label = QLabel("Preparing…")
        self._label.setObjectName("OverlayText")
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        layout.addWidget(self._bar)

        self._hint = QLabel("ESC stop")
        self._hint.setObjectName("OverlayHint")
        layout.addWidget(self._hint)

    # ------------------------------------------------------------------
    def show_overlay(self, text: str = "Preparing…", pause_key: str = "p") -> None:
        self._bar.setValue(0)
        self._label.setText(text)
        self._pause_key = (pause_key or "p").upper()
        self._paused = False
        self._update_hint()
        self._reposition()
        self.show()
        self.raise_()

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            return
        self._paused = bool(paused)
        self._update_hint()

    def _update_hint(self) -> None:
        if self._paused:
            self._hint.setText(f"PAUSED — {self._pause_key} resume · ESC stop")
        else:
            self._hint.setText(f"ESC stop · {self._pause_key} pause/resume")

    def show_message(self, text: str) -> None:
        """Update the headline text without touching the progress bar.

        Used for the visible "switch to the target app" countdown so the wait
        is explained instead of looking frozen.
        """
        self._card.setProperty("severity", "info")
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)
        self._label.setText(text)

    def show_error(self, text: str) -> None:
        """Show a persistent error card that the user cannot miss."""
        self._card.setProperty("severity", "error")
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)
        self._bar.setValue(0)
        self._label.setText(text)
        self._hint.setText("Reopening Pyaint")
        self._reposition()
        self.show()
        self.raise_()

    def update_progress(self, completed: int, total: int, eta_seconds: float) -> None:
        if total > 0:
            self._bar.setValue(int(100 * completed / total))
            self._label.setText(
                f"Drawing {completed}/{total} strokes — ETA {_format_eta(eta_seconds)}"
            )
        else:
            self._bar.setValue(0)

    def hide_overlay(self) -> None:
        self.hide()

    # ------------------------------------------------------------------
    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.adjustSize()
        x = geometry.center().x() - self.width() // 2
        y = geometry.top() + 16
        self.move(x, y)


CANVAS_OUTLINE = QColor(241, 76, 76)   # matches the old annotated preview
PALETTE_OUTLINE = QColor(78, 201, 176)
DOT_FILL = QColor(255, 255, 255)
DOT_OUTLINE = QColor(20, 20, 20)
SCRIM = QColor(0, 0, 0, 130)
_LABEL_BG = QColor(0, 0, 0, 175)


class DetectionOverlay(QWidget):
    """Full-screen review overlay for an auto-detection result.

    The target app stays visible underneath while the detected canvas and
    palette are spotlighted and the palette cell centres are marked. The user
    decides whether to use the regions, retry, teach manually, or discard.
    """

    confirmed = Signal()
    retry_requested = Signal()
    teach_requested = Signal()
    dismissed = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        # Unlike the drawing overlay, this window must be able to take focus
        # when the user clicks its buttons: a non-activating tool window leaves
        # the app in the background, and a modal dialog opened from it (e.g.
        # Setup) then cannot receive input. It still shows without stealing
        # focus from the target app.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._regions = []  # list[(QRectF, label, QColor)]
        self._dots = []     # list[QPointF]

        self._card = QFrame(self)
        self._card.setObjectName("DetectionCard")
        self._card.setFixedWidth(560)
        card = QVBoxLayout(self._card)
        card.setContentsMargins(16, 12, 16, 12)
        card.setSpacing(8)

        title = QLabel("Review detected regions")
        title.setObjectName("DetectionTitle")
        card.addWidget(title)

        self._summary = QLabel()
        self._summary.setObjectName("DetectionSummary")
        self._summary.setWordWrap(True)
        card.addWidget(self._summary)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self._confirm_btn = QPushButton("Use these regions")
        self._confirm_btn.setObjectName("Primary")
        self._confirm_btn.clicked.connect(self.confirmed.emit)
        self._retry_btn = QPushButton("Try again")
        self._retry_btn.clicked.connect(self.retry_requested.emit)
        self._teach_btn = QPushButton("Teach manually…")
        self._teach_btn.clicked.connect(self.teach_requested.emit)
        self._dismiss_btn = QPushButton("Not now")
        self._dismiss_btn.clicked.connect(self.dismissed.emit)
        for button in (self._confirm_btn, self._retry_btn, self._teach_btn, self._dismiss_btn):
            buttons.addWidget(button)
        card.addLayout(buttons)

        self.hide()

    # ------------------------------------------------------------------
    def show_detection(self, detection, image_size, summary: str, screen) -> None:
        """Present ``detection`` scaled from the screenshot onto ``screen``."""
        self._summary.setText(summary)
        usable = bool(detection) and bool(detection.canvas or detection.palette)
        self._confirm_btn.setEnabled(usable)
        self._build_geometry(detection, image_size, screen)
        self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self._position_card()

    def hide_detection(self) -> None:
        self.hide()

    # ------------------------------------------------------------------
    def _build_geometry(self, detection, image_size, screen) -> None:
        self._regions = []
        self._dots = []
        width, height = image_size
        geometry = screen.geometry()
        if width <= 0 or height <= 0 or geometry.width() <= 0 or geometry.height() <= 0:
            return
        sx = geometry.width() / width
        sy = geometry.height() / height

        canvas = getattr(detection, "canvas", None)
        if canvas:
            x, y, w, h = canvas
            self._regions.append(
                (QRectF(x * sx, y * sy, w * sx, h * sy), "Canvas", CANVAS_OUTLINE)
            )

        palette = getattr(detection, "palette", None)
        if palette:
            x, y, w, h = palette
            rows = getattr(detection, "palette_rows", None)
            cols = getattr(detection, "palette_cols", None)
            label = f"Palette {rows}×{cols}" if rows and cols else "Palette"
            self._regions.append(
                (QRectF(x * sx, y * sy, w * sx, h * sy), label, PALETTE_OUTLINE)
            )
            if rows and cols:
                for cx, cy in utils.grid_centers(palette, rows, cols):
                    self._dots.append(QPointF(cx * sx, cy * sy))

    def _position_card(self) -> None:
        self._card.adjustSize()
        width = self.width()
        height = self.height()
        margin = 24
        x = max(margin, (width - self._card.width()) // 2)
        y = height - self._card.height() - margin
        if self._regions:
            union = self._regions[0][0]
            for rect, _, _ in self._regions[1:]:
                union = union.united(rect)
            # Put the card on the side with the most free space.
            if union.center().y() > height / 2:
                y = margin
        self._card.move(x, y)

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        scrim = QPainterPath()
        scrim.setFillRule(Qt.OddEvenFill)
        scrim.addRect(QRectF(self.rect()))
        for rect, _, _ in self._regions:
            scrim.addRect(rect)
        painter.fillPath(scrim, SCRIM)

        for rect, label, color in self._regions:
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            self._draw_label(painter, rect, label, color)

        if self._dots:
            painter.setPen(QPen(DOT_OUTLINE, 1))
            painter.setBrush(DOT_FILL)
            for dot in self._dots:
                painter.drawEllipse(dot, 3.5, 3.5)
        painter.end()

    def _draw_label(self, painter, rect, text, color) -> None:
        metrics = painter.fontMetrics()
        padding = 5
        width = metrics.horizontalAdvance(text) + padding * 2
        height = metrics.height() + 4
        label = QRectF(rect.left(), rect.top() - height - 4, width, height)
        if label.top() < 0:
            label.moveTop(rect.top() + 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_LABEL_BG)
        painter.drawRoundedRect(label, 3, 3)
        painter.setPen(color)
        painter.setBrush(Qt.NoBrush)
        painter.drawText(label, Qt.AlignCenter, text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._card.isVisible():
            self._position_card()
