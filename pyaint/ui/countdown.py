"""A modal countdown dialog used before the screen is captured.

Used by Auto-detect so the user gets an unmissable warning (with a cancel and a
"capture now" option) before pyaint minimizes itself.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class CountdownDialog(QDialog):
    def __init__(
        self,
        parent=None,
        seconds: int = 3,
        title: str = "Auto-detect",
        heading: str = "Capturing the screen",
        message: str = "Bring the target application to the front now.",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(360)

        self._total = max(1, seconds)
        self._remaining = self._total

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(8)

        self._heading = QLabel(heading)
        self._heading.setObjectName("DialogTitle")
        layout.addWidget(self._heading)

        self._message = QLabel(message)
        self._message.setObjectName("DialogHint")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        self._count = QLabel(str(self._remaining))
        self._count.setObjectName("CountdownNumber")
        self._count.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._count)

        self._bar = QProgressBar()
        self._bar.setRange(0, self._total)
        self._bar.setValue(self._total)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        layout.addWidget(self._bar)

        buttons = QHBoxLayout()
        capture_now = QPushButton("Capture now")
        capture_now.setObjectName("Primary")
        capture_now.clicked.connect(self._capture_now)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(capture_now)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self.accept()
            return
        self._count.setText(str(self._remaining))
        self._bar.setValue(self._remaining)

    def _capture_now(self) -> None:
        self._timer.stop()
        self.accept()
