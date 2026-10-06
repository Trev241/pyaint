"""Full-screen click-capture overlay used to teach screen coordinates.

A translucent, always-on-top window covers every screen and records where the
user clicks; the underlying app stays visible through the veil. Before the
veil appears, pyaint is minimized and a clean full-screen screenshot is taken,
so callers can sample colours from the target app rather than from pyaint's own
window -- or from the darkened veil.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pyautogui
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication
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
                # Accept straight away. The clean screenshot is taken before
                # the overlay appears, so there is nothing left to do here.
                # Hiding a modal QDialog exits its exec() loop immediately with
                # ``Rejected``, so the old ``hide()`` + deferred ``accept()``
                # made ``pick_points`` return ``None`` and silently discarded
                # every taught point.
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
    # Make pyaint fully transparent as well as minimized. Windows animates the
    # minimize by default, so a fixed sleep can still catch a half-faded
    # window in the grab; zero opacity removes it from the shot immediately.
    for widget in minimized:
        try:
            widget.setWindowOpacity(0.0)
        except Exception:
            pass
        widget.showMinimized()

    # Grab the target screen *before* the overlay is shown: it is translucent,
    # so grabbing after hiding it can capture the veil (giving darkened, wrong
    # palette colours). Wait briefly for the minimize to finish first so pyaint
    # itself is not in the shot.
    image = None
    try:
        QApplication.processEvents()
        time.sleep(0.15)
        QApplication.processEvents()
        image = pyautogui.screenshot()
    except Exception:
        image = None

    try:
        accepted = overlay.exec() == QDialog.Accepted
    finally:
        # Restore owners first so the modal dialog is shown and activated last.
        for widget in reversed(minimized):
            widget.setWindowState(
                (widget.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
            )
            widget.showNormal()
            try:
                widget.setWindowOpacity(1.0)
            except Exception:
                pass
            widget.raise_()
            widget.activateWindow()
    if not accepted:
        return None
    return PickResult(_to_screenshot_points(overlay.points, image), image)


def _to_screenshot_points(points, image):
    """Map Qt's logical click points onto the physical screenshot pixels.

    On a scaled display Qt reports logical coordinates while ``screenshot()``
    returns physical pixels, so without this a manually taught box lands in the
    wrong place (and samples the wrong colours).
    """
    if image is None or not points:
        return points
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return points
    geo = screen.geometry()
    if geo.width() <= 0 or geo.height() <= 0:
        return points
    scale_x = image.width / geo.width()
    scale_y = image.height / geo.height()
    if abs(scale_x - 1.0) < 1e-6 and abs(scale_y - 1.0) < 1e-6:
        return points
    return [(int(round(x * scale_x)), int(round(y * scale_y))) for x, y in points]
