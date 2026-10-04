"""Threaded helpers for the Image panel's search gallery.

The drawing engine's :meth:`Bot` tasks run on a single "busy" worker, but
browsing search results must never block readiness or drawing. These runnables
go on the global ``QThreadPool`` instead and report back through signals, so the
UI can keep loading thumbnails and pages while staying responsive.

Every result carries the search *generation* it belongs to; the window drops
results whose generation no longer matches, which cancels stale queries and
in-flight thumbnails.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage

from pyaint import image_search


def _safe_emit(signal, *args) -> None:
    """Emit unless the receiver/QObject was torn down (e.g. window closed)."""
    try:
        signal.emit(*args)
    except RuntimeError:
        pass


class _PageSignals(QObject):
    ready = Signal(int, object)  # generation, SearchPage
    failed = Signal(int, str)  # generation, message


class SearchPageTask(QRunnable):
    """Fetch one page of search results."""

    def __init__(self, query: str, cont, generation: int):
        super().__init__()
        self.query = query
        self.cont = cont
        self.generation = generation
        self.signals = _PageSignals()

    def run(self) -> None:  # noqa: D102
        try:
            page = image_search.search_page(self.query, cont=self.cont)
            _safe_emit(self.signals.ready, self.generation, page)
        except Exception as exc:  # noqa: BLE001 - surfaced in the panel
            _safe_emit(self.signals.failed, self.generation, str(exc))


class _ThumbSignals(QObject):
    ready = Signal(int, str, object)  # generation, url, QImage
    failed = Signal(int, str)  # generation, url


class ThumbnailTask(QRunnable):
    """Fetch and decode one gallery thumbnail (as a thread-safe QImage)."""

    def __init__(self, url: str, generation: int):
        super().__init__()
        self.url = url
        self.generation = generation
        self.signals = _ThumbSignals()

    def run(self) -> None:  # noqa: D102
        try:
            image = QImage()
            if not image.loadFromData(image_search.fetch_bytes(self.url)):
                raise ValueError("could not decode image")
            _safe_emit(self.signals.ready, self.generation, self.url, image)
        except Exception:  # noqa: BLE001 - a broken thumbnail is not fatal
            _safe_emit(self.signals.failed, self.generation, self.url)
