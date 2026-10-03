"""Non-modal in-window countdown banner used before a screen capture.

Shown above the content area when Auto-detect is about to minimize the window.
Unlike a modal dialog it never steals focus or floats over the target app, but
it is large and high-contrast enough to be unmissable. It offers **Capture now**
and **Cancel**, and auto-proceeds when the countdown ends.
"""

from __future__ import annotations

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CountdownBanner")
        self._total = 0
        self._remaining = 0

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
        self._bar.setRange(0, 1)
        self._bar.setValue(1)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(4)
        outer.addWidget(self._bar)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self, seconds: int = 4) -> None:
        self._total = max(1, int(seconds))
        self._remaining = self._total
        self._bar.setRange(0, self._total)
        self._bar.setValue(self._total)
        self._title.setText(f"Capturing the screen in {self._remaining}s…")
        self.show()
        self._timer.start(1000)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self.captured.emit()
            return
        self._title.setText(f"Capturing the screen in {self._remaining}s…")
        self._bar.setValue(self._remaining)

    def _capture_now(self) -> None:
        self._timer.stop()
        self.captured.emit()

    def _cancel(self) -> None:
        self._timer.stop()
        self.cancelled.emit()
