"""Floating, always-on-top progress overlay.

Shown while a drawing task runs so the user can see progress over the target
app (the main window is minimized during a draw). It is click-through and never
takes focus, so it cannot interfere with the app being automated.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


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
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
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
        self._hint.setText(f"ESC stop · {pause_key.upper()} pause/resume")
        self._reposition()
        self.show()
        self.raise_()

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
