"""Small, self-contained line icons drawn with QPainter.

Icons are drawn at the display's device-pixel-ratio so they stay crisp on
scaled displays, and cached by ``(name, color, size, dpr)``. Using QPainter
primitives avoids shipping image assets and keeps the icon set flat and
theme-coloured.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QApplication

_DEFAULT = "#cccccc"


def _poly(s, *pts):
    """Polygon from normalised (0..1) points, scaled to ``s``."""
    return QPolygonF([QPointF(x * s, y * s) for x, y in pts])


def _draw_play(p: QPainter, s: float) -> None:
    p.setBrush(p.pen().color())
    p.drawPolygon(_poly(s, (0.34, 0.24), (0.78, 0.5), (0.34, 0.76)))


def _draw_pause(p: QPainter, s: float) -> None:
    p.setBrush(p.pen().color())
    p.drawRoundedRect(QRectF(0.32 * s, 0.26 * s, 0.12 * s, 0.48 * s), 1, 1)
    p.drawRoundedRect(QRectF(0.56 * s, 0.26 * s, 0.12 * s, 0.48 * s), 1, 1)


def _draw_stop(p: QPainter, s: float) -> None:
    p.setBrush(p.pen().color())
    p.drawRoundedRect(QRectF(0.3 * s, 0.3 * s, 0.4 * s, 0.4 * s), 2, 2)


def _draw_image(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(0.15 * s, 0.2 * s, 0.7 * s, 0.6 * s), 2, 2)
    p.setBrush(p.pen().color())
    p.drawEllipse(QPointF(0.34 * s, 0.38 * s), 0.05 * s, 0.05 * s)
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(_poly(s, (0.19, 0.72), (0.4, 0.5), (0.55, 0.65), (0.68, 0.55), (0.81, 0.72)))


def _draw_sliders(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    for y, kx in ((0.32, 0.38), (0.5, 0.64), (0.68, 0.46)):
        p.drawLine(QPointF(0.16 * s, y * s), QPointF(0.84 * s, y * s))
        p.setBrush(p.pen().color())
        p.drawEllipse(QPointF(kx * s, y * s), 0.06 * s, 0.06 * s)
        p.setBrush(Qt.NoBrush)


def _draw_target(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(0.5 * s, 0.5 * s), 0.28 * s, 0.28 * s)
    p.drawEllipse(QPointF(0.5 * s, 0.5 * s), 0.1 * s, 0.1 * s)
    for a, b in (((0.5, 0.06), (0.5, 0.2)), ((0.5, 0.8), (0.5, 0.94)),
                 ((0.06, 0.5), (0.2, 0.5)), ((0.8, 0.5), (0.94, 0.5))):
        p.drawLine(QPointF(a[0] * s, a[1] * s), QPointF(b[0] * s, b[1] * s))


def _draw_folder(p: QPainter, s: float) -> None:
    path = QPainterPath()
    path.moveTo(0.12 * s, 0.3 * s)
    path.lineTo(0.4 * s, 0.3 * s)
    path.lineTo(0.48 * s, 0.4 * s)
    path.lineTo(0.88 * s, 0.4 * s)
    path.lineTo(0.88 * s, 0.78 * s)
    path.lineTo(0.12 * s, 0.78 * s)
    path.closeSubpath()
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def _draw_globe(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(0.5 * s, 0.5 * s), 0.32 * s, 0.32 * s)
    p.drawEllipse(QRectF(0.34 * s, 0.18 * s, 0.32 * s, 0.64 * s))
    p.drawLine(QPointF(0.18 * s, 0.5 * s), QPointF(0.82 * s, 0.5 * s))


def _draw_download(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(0.5 * s, 0.16 * s), QPointF(0.5 * s, 0.6 * s))
    p.drawPolyline(_poly(s, (0.34, 0.44), (0.5, 0.62), (0.66, 0.44)))
    p.drawLine(QPointF(0.24 * s, 0.8 * s), QPointF(0.76 * s, 0.8 * s))


def _draw_zap(p: QPainter, s: float) -> None:
    p.setBrush(p.pen().color())
    p.drawPolygon(_poly(s, (0.56, 0.1), (0.28, 0.54), (0.47, 0.54),
                        (0.42, 0.9), (0.72, 0.43), (0.52, 0.43)))


def _draw_trash(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(0.18 * s, 0.28 * s), QPointF(0.82 * s, 0.28 * s))
    p.drawPolyline(_poly(s, (0.38, 0.28), (0.38, 0.2), (0.62, 0.2), (0.62, 0.28)))
    p.drawRoundedRect(QRectF(0.24 * s, 0.32 * s, 0.52 * s, 0.5 * s), 2, 2)
    p.drawLine(QPointF(0.42 * s, 0.42 * s), QPointF(0.42 * s, 0.72 * s))
    p.drawLine(QPointF(0.58 * s, 0.42 * s), QPointF(0.58 * s, 0.72 * s))


def _draw_refresh(p: QPainter, s: float) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(0.2 * s, 0.2 * s, 0.6 * s, 0.6 * s), 40 * 16, 280 * 16)
    p.setBrush(p.pen().color())
    p.drawPolygon(_poly(s, (0.62, 0.06), (0.84, 0.26), (0.58, 0.32)))


_DRAWERS = {
    "play": _draw_play,
    "pause": _draw_pause,
    "stop": _draw_stop,
    "image": _draw_image,
    "sliders": _draw_sliders,
    "target": _draw_target,
    "folder": _draw_folder,
    "globe": _draw_globe,
    "download": _draw_download,
    "zap": _draw_zap,
    "trash": _draw_trash,
    "refresh": _draw_refresh,
}


def _device_ratio() -> float:
    app = QApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    return float(screen.devicePixelRatio()) if screen is not None else 1.0


@lru_cache(maxsize=512)
def _render(name: str, color: str, size: int, dpr: float) -> QIcon:
    physical = max(1, int(round(size * dpr)))
    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.transparent)
    drawer = _DRAWERS.get(name)
    if drawer is not None:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(color))
        pen.setWidthF(max(1.4, size * 0.085))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.scale(dpr, dpr)
        drawer(painter, float(size))
        painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return QIcon(pixmap)


def icon(name: str, color: str = _DEFAULT, size: int = 20) -> QIcon:
    """Return a cached, DPR-aware :class:`QIcon` for ``name``."""
    return _render(name, color, size, _device_ratio())
