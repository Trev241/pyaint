"""Threaded planning + rendering for the live preview.

Planning can take seconds on a full-resolution image, so it runs off the GUI
thread on the global ``QThreadPool`` and reports back through signals. Every
result carries the *generation* it belongs to; the window drops stale results
when settings change faster than planning finishes. All inputs are snapshotted
by the caller so the worker never touches the mutable ``Bot``.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage

from pyaint import render


def _safe_emit(signal, *args) -> None:
    """Emit unless the receiver was torn down (e.g. the window closed)."""
    try:
        signal.emit(*args)
    except RuntimeError:
        pass


def pil_to_qimage(image: Image.Image) -> QImage:
    """Copy a PIL image into a QImage owned by the current thread."""
    rgb = image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    return QImage(
        data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888
    ).copy()


class _PlanSignals(QObject):
    ready = Signal(int, object, str)  # generation, QImage, meta text
    failed = Signal(int, str)  # generation, message


class PlanPreviewTask(QRunnable):
    """Plan + render one preview frame; emits a canvas-sized ``QImage``."""

    def __init__(
        self,
        generation: int,
        image_path: str,
        canvas: Tuple[int, int, int, int],
        step: int,
        palette,
        metric: str,
        flags: int,
        mode: str,
        plan_kwargs: Optional[Dict] = None,
    ):
        super().__init__()
        self.generation = generation
        self.image_path = image_path
        self.canvas = canvas
        self.step = step
        self.palette = palette
        self.metric = metric
        self.flags = flags
        self.mode = mode
        self.plan_kwargs = plan_kwargs or {}
        self.signals = _PlanSignals()

    def run(self) -> None:  # noqa: D102
        try:
            image = Image.open(self.image_path).convert("RGBA")
            frame, meta = render.preview(
                image,
                self.canvas,
                self.step,
                self.palette,
                self.metric,
                self.flags,
                self.mode,
                self.plan_kwargs,
            )
            _safe_emit(
                self.signals.ready, self.generation, pil_to_qimage(frame), meta
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in the preview
            _safe_emit(self.signals.failed, self.generation, str(exc))
