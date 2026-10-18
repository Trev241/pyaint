"""Non-modal countdown used before a screen capture.

Shown as a floating, top-anchored card while Find the canvas is about to
minimize the window. Unlike a modal dialog it never steals focus or floats over
the target app; unlike a layout banner it takes no space, so showing it moves
nothing. It offers **Capture now** and **Cancel**, and auto-proceeds when the
countdown ends. The progress bar animates smoothly (a high-frequency timer over
a monotonic deadline), not in one-second steps.
"""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class CountdownBanner(QFrame):
    captured = Signal()
    cancelled = Signal()
    shown = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CountdownBanner")
        self._total = 0
        self._deadline = 0.0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        top = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("CountdownTitle")
        self._hint = QLabel(
            "Make sure the canvas is blank and the app is maximized on the primary "
            "monitor, then bring it to the front."
        )
        self._hint.setObjectName("CountdownHint")
        self._hint.setWordWrap(True)
        text.addWidget(self._title)
        text.addWidget(self._hint)
        top.addLayout(text, 1)

        self._capture_btn = QPushButton("Capture now")
        self._capture_btn.setObjectName("Primary")
        self._capture_btn.clicked.connect(self._capture_now)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._cancel)
        top.addWidget(self._capture_btn)
        top.addWidget(self._cancel_btn)
        outer.addLayout(top)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(1000)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(4)
        outer.addWidget(self._bar)

        # ~40 fps keeps the bar visibly smooth without busy-looping.
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.shown.emit()

    def start(self, seconds: int = 4) -> None:
        self._total = max(1, int(seconds))
        self._deadline = time.monotonic() + self._total
        self._bar.setValue(1000)
        self._title.setText(f"Capturing the screen in {self._total}s…")
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            self._timer.stop()
            self.captured.emit()
            return
        fraction = max(0.0, min(1.0, remaining / self._total))
        self._bar.setValue(int(round(fraction * 1000)))
        self._title.setText(f"Capturing the screen in {math.ceil(remaining)}s…")

    def _capture_now(self) -> None:
        self._timer.stop()
        self.captured.emit()

    def _cancel(self) -> None:
        self._timer.stop()
        self.cancelled.emit()
