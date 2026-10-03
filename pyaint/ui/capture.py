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
from PySide6.QtCore import QRect, Qt
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
                # Grab the screen with the overlay hidden so the target app (not
                # pyaint) is captured for colour sampling.
                self.hide()
                QApplication.processEvents()
                try:
                    self.image = pyautogui.screenshot()
                except Exception:
                    self.image = None
                self.accept()
            else:
                self._update()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.reject()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()


def pick_points(
    parent=None, count: int = 2, prompt: str = "Click a point"
) -> Optional[PickResult]:
    """Show the overlay and return the click points (and a screenshot), or None."""
    overlay = _PickOverlay(count, prompt)
    hidden = parent is not None and parent.isVisible()
    if hidden:
        parent.hide()
    try:
        accepted = overlay.exec() == QDialog.Accepted
    finally:
        if hidden:
            parent.show()
            parent.raise_()
            parent.activateWindow()
    if not accepted:
        return None
    return PickResult(overlay.points, overlay.image)
