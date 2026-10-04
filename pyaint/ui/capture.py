"""Full-screen click-capture overlay used to teach screen coordinates.

A translucent, always-on-top window covers every screen and records where the
user clicks; the underlying app stays visible through the veil. On the final
click the overlay hides itself and grabs a screenshot of the screen *without*
pyaint on top, so callers can sample colours from the target app rather than
from pyaint's own window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pyautogui
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout


@dataclass
class PickResult:
    points: List[Tuple[int, int]]
    image: object = None  # full-screen PIL image, or None if the grab failed


class _PickOverlay(QDialog):
    def __init__(self, count: int, prompt: str):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowOpacity(0.4)
        self.setStyleSheet("background: #000000;")
        self.setCursor(Qt.CrossCursor)
        self.setModal(True)
        self._count = count
        self._prompt = prompt
        self.points: List[Tuple[int, int]] = []
        self.image = None

        geometry = QRect()
        for screen in QApplication.screens():
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: 600; padding: 48px;"
        )
        layout.addWidget(self._label)
        self._update()

    def _update(self) -> None:
        self._label.setText(
            f"{self._prompt}\n\nClicked {len(self.points)}/{self._count} — press Esc to cancel."
        )

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            point = event.globalPosition().toPoint()
            self.points.append((point.x(), point.y()))
            if len(self.points) >= self._count:
                # Hide now, then finish on the next event-loop turn. Doing the
                # screenshot and accept() inside the mouse event (after
                # processEvents) can re-enter the modal loop and leave a hidden
                # modal dialog blocking the app.
                self.hide()
                # Give the window manager a moment to actually remove the veil
                # before grabbing the screen.
                QTimer.singleShot(50, self._finish)
            else:
                self._update()

    def _finish(self) -> None:
        # Grab the screen with the overlay hidden so the target app (not
        # pyaint) is captured for colour sampling.
        try:
            self.image = pyautogui.screenshot()
        except Exception:
            self.image = None
        self.accept()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.reject()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()


def _window_chain(widget) -> List[object]:
    """Return ``widget`` plus its top-level owner, if it is a separate window."""
    chain = []
    if widget is None or not widget.isVisible():
        return chain
    chain.append(widget)
    owner = widget.parentWidget()
    if owner is not None and owner.isWindow() and owner.isVisible():
        chain.append(owner)
    return chain


def pick_points(
    parent=None, count: int = 2, prompt: str = "Click a point"
) -> Optional[PickResult]:
    """Show the overlay and return the click points (and a screenshot), or None.

    The window chain is *minimized*, never hidden: hiding a dialog ends its
    ``exec()`` loop, which drops Setup out of its modal loop mid-teach and
    leaves the app looking hung. Minimized windows also stay out of the
    screenshot taken for palette sampling.
    """
    overlay = _PickOverlay(count, prompt)
    minimized = _window_chain(parent)
    for widget in minimized:
        widget.showMinimized()
    try:
        accepted = overlay.exec() == QDialog.Accepted
    finally:
        # Restore owners first so the modal dialog is shown and activated last.
        for widget in reversed(minimized):
            widget.setWindowState(
                (widget.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
            )
            widget.showNormal()
            widget.raise_()
            widget.activateWindow()
    if not accepted:
        return None
    return PickResult(overlay.points, overlay.image)
