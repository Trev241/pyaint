"""The "paper on a desk" surface language — the subtle pass.

Qt stylesheets can only paint rectangles, so the chrome that should look like
paper is drawn by hand here. Only the **hero artwork sheet** is an irregular
quad; every other surface is a plain rounded rect (``PAPER_ROLES``). The hero's
corners are jittered and its four edges bow *inward* by different amounts, so
it leans without ever puffing up. Text, icons and input fields are never
sheared -- only the surface leans ("decoration may tilt; information may not").

Everything is deterministic: a silhouette role fixes the jitter/bow/radius, and
each surface gets a **stable seed** derived from ``(role, seed_key)`` via
``zlib.crc32`` -- never Python's salted ``hash()`` -- so a shape is identical
across repaints, construction orders and runs.

The whole language can be dialled back or switched off with ``PAPER_AMOUNT`` or
the ``PYAINT_PAPER`` environment variable (``0``-``1``, or ``off``).
"""

from __future__ import annotations

import math
import os
import random
import zlib

from PySide6.QtCore import QMargins, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QWidget,
)

from pyaint.ui import theme

#: Base intensity of the paper gesture (0 = plain rectangles, 1 = full lean).
PAPER_AMOUNT = 0.6

#: Roles that draw a real irregular quad. Everything else is a rounded rect, so
#: paper is confined to the artwork sheet -- small/text surfaces stay legible.
PAPER_ROLES = frozenset({"hero"})

#: Roles that carry elevation. Only sheets sit above the desk; controls never do,
#: which is why a button cannot end up with a slab shadow cut off at its corner.
SHADOW_ROLES = frozenset({"hero"})

#: Per-role silhouette parameters. ``seed`` is the fallback stable seed for a
#: role with no ``seed_key``; ``inset`` leaves room for the soft shadow;
#: ``margin`` is the content-safe inset (clear of jitter, bow and radius). For
#: non-paper roles the jitter/bow are ignored -- only ``radius`` applies.
SILHOUETTES: dict[str, dict] = {
    "hero": {"jitter": 8.0, "bow": 14.0, "radius": 18.0, "seed": 1100, "inset": 10.0,
             "margin": 22},
    "column": {"jitter": 0.0, "bow": 0.0, "radius": 10.0, "seed": 2100, "inset": 0.0,
               "margin": 16},
    "bar": {"jitter": 0.0, "bow": 0.0, "radius": 12.0, "seed": 3100, "inset": 0.0,
            "margin": 12},
    "card": {"jitter": 0.0, "bow": 0.0, "radius": 8.0, "seed": 4100, "inset": 0.0,
             "margin": 10},
    "chip": {"jitter": 0.0, "bow": 0.0, "radius": 8.0, "seed": 5100, "inset": 0.0,
             "margin": 8},
    "mode": {"jitter": 0.0, "bow": 0.0, "radius": 6.0, "seed": 6100, "inset": 0.0,
             "margin": 6},
    "badge": {"jitter": 0.0, "bow": 0.0, "radius": 17.0, "seed": 7100, "inset": 0.0,
              "margin": 8},
}

#: Which painted surface a role uses, as ``theme`` token keys.
ROLE_FILL = {
    "hero": "bg_card",
    "column": "bg_side",
    "bar": "bg_card",
    "card": "bg_card",
    "chip": "bg_card",
    "mode": "accent",
    "badge": "accent",
}
ROLE_BORDER = {
    "hero": "border",
    "column": "border",
    "bar": "border",
    "card": "border",
    "chip": "border",
    "mode": None,
    "badge": None,
}


def _paper_amount() -> float:
    """The active paper intensity: ``PAPER_AMOUNT`` unless overridden by env."""
    raw = os.environ.get("PYAINT_PAPER")
    if raw is None:
        return PAPER_AMOUNT
    raw = raw.strip().lower()
    if raw in ("off", "none", "no", "false"):
        return 0.0
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return PAPER_AMOUNT


def tokens(widget=None) -> dict:
    """The active theme tokens, read from the widget, the app, or the default."""
    app = QApplication.instance()
    value = None
    if widget is not None:
        value = widget.property("pyaint_tokens")
    if value is None and app is not None:
        value = app.property("pyaint_tokens")
    return value or theme.resolve_tokens("auto")


def _stable_seed(role: str, seed_key) -> int:
    """A deterministic seed for ``(role, seed_key)``; never Python's hash()."""
    spec = SILHOUETTES.get(role, SILHOUETTES["card"])
    if seed_key is None:
        return int(spec["seed"])
    return zlib.crc32(f"{role}:{seed_key}".encode()) & 0x7FFFFFFF


def paper_path(rect: QRectF, role: str = "card", seed_key=None,
               inset: float | None = None) -> QPainterPath:
    """A sheet inside ``rect``.

    For a role in :data:`PAPER_ROLES` this is an irregular quad: jittered
    corners, inward-bowed edges and soft corners, scaled by the paper amount.
    Every other role returns a plain rounded rectangle. Deterministic for a
    given ``(role, seed_key)``.
    """
    spec = SILHOUETTES.get(role, SILHOUETTES["card"])
    amount = _paper_amount() if role in PAPER_ROLES else 0.0
    if inset is None:
        inset = spec["inset"] if amount > 0 else 0.0
    r = QRectF(rect).adjusted(inset, inset, -inset, -inset)
    if r.width() <= 2 or r.height() <= 2:
        r = QRectF(rect)
    jitter = spec["jitter"] * amount
    bow = spec["bow"] * amount
    radius = spec["radius"]

    rnd = random.Random(_stable_seed(role, seed_key))
    base = [(r.left(), r.top()), (r.right(), r.top()),
            (r.right(), r.bottom()), (r.left(), r.bottom())]
    pts = [
        QPointF(x + rnd.uniform(-jitter, jitter), y + rnd.uniform(-jitter, jitter))
        for x, y in base
    ]

    n = len(pts)
    a_pts, b_pts = [], []
    for i in range(n):
        prev, cur, nxt = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        dprev, dnext = cur - prev, nxt - cur
        lprev = max(1e-3, math.hypot(dprev.x(), dprev.y()))
        lnext = max(1e-3, math.hypot(dnext.x(), dnext.y()))
        step = min(radius, lprev / 2.6, lnext / 2.6)
        a_pts.append(cur - dprev / lprev * step)
        b_pts.append(cur + dnext / lnext * step)

    edge_ctrl = []
    for i in range(n):
        A, B = b_pts[i], a_pts[(i + 1) % n]
        mid = (A + B) / 2
        dx, dy = B.x() - A.x(), B.y() - A.y()
        length = max(1e-3, math.hypot(dx, dy))
        # The clockwise point order makes ``(-dy, dx)`` point *into* the sheet,
        # so a positive offset bows the edge inward and the centre never bulges.
        edge_ctrl.append(mid + QPointF(-dy / length, dx / length)
                         * rnd.uniform(0.0, bow))

    path = QPainterPath()
    path.moveTo(b_pts[0])
    for i in range(n):
        j = (i + 1) % n
        path.quadTo(edge_ctrl[i], a_pts[j])
        path.quadTo(pts[j], b_pts[j])
    path.closeSubpath()
    return path


def content_pad(role: str = "card") -> int:
    """The content-safe inset declared for a role (independent of geometry)."""
    return int(SILHOUETTES.get(role, SILHOUETTES["card"])["margin"])


def content_rect(rect: QRectF, role: str = "card") -> QRectF:
    """The rectangle inside a sheet where content is guaranteed to stay clear.

    Derived from the role's declared margin, which accounts for jitter, bow and
    corner radius, so padding is computed rather than guessed. Children that
    respect this never leak past the irregular edge.
    """
    pad = content_pad(role)
    r = QRectF(rect)
    if r.width() - 2 * pad <= 2 or r.height() - 2 * pad <= 2:
        return r
    return r.adjusted(pad, pad, -pad, -pad)


def soft_shadow(painter: QPainter, path: QPainterPath, color: QColor,
                offset: float = 2.0, spread: float = 7.0,
                passes: int = 8) -> None:
    """Paint a soft falloff under ``path``.

    Qt has no blur for direct painting, so the shadow is *stroked*: each pass
    widens the outline and fades, and round joins keep the corners soft. The
    result is a real gradient rather than the hard-edged offset copies this
    used to draw, which read as a second, square-cornered rectangle.
    """
    painter.save()
    painter.setBrush(Qt.NoBrush)
    shifted = QPainterPath(path)
    shifted.translate(0, offset)
    for step in range(passes - 1, -1, -1):
        width = spread * 2.0 * (step + 1) / passes
        fade = 1.0 - (step + 1) / (passes + 1)
        shade = QColor(color)
        shade.setAlpha(max(1, int(color.alpha() * fade ** 2.4 * 0.55)))
        pen = QPen(shade, width)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(shifted)
    painter.restore()


def paint_paper(painter: QPainter, path: QPainterPath, t: dict,
                fill: str | None = None, border: str | None = None,
                shadow: bool = False, shadow_color: QColor | None = None,
                width: float = 1.0) -> None:
    """Paint a sheet: optional soft shadow, fill, hairline.

    ``shadow`` is off by default and only :data:`SHADOW_ROLES` turn it on, so a
    control can never paint itself a drop shadow.
    """
    if shadow:
        if shadow_color is not None:
            color = QColor(shadow_color)
        else:
            color = QColor(t.get("shadow", "#3C3228"))
            color.setAlpha(int(t.get("shadow_alpha", 70)))
        soft_shadow(painter, path, color)
    if fill is not None:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(fill))
        painter.drawPath(path)
    if border is not None:
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(border), width))
        painter.drawPath(path)


class PaperSurface(QFrame):
    """A frame whose background is a paper sheet (irregular for the hero role).

    Children sit in the normal rectangular layout; keep them inside
    :meth:`content_rect` so they never leak past the sheet's edge.
    """

    def __init__(self, role: str = "card", fill: str | None = None,
                 border: str | None = None, regular: bool = False,
                 seed_key=None, parent=None):
        super().__init__(parent)
        self._role = role if role in SILHOUETTES else "card"
        self._seed_key = seed_key
        self._fill = fill
        self._border = border
        self._regular = regular
        self._path = None
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setProperty("paperRole", self._role)

    def shape_path(self) -> QPainterPath:
        if self._path is None:
            self._rebuild()
        return self._path

    def content_rect(self) -> QRectF:
        """The safe inner rectangle for children of this sheet."""
        return content_rect(QRectF(self.rect()), self._role)

    def content_margins(self) -> QMargins:
        """The declared safe inset as layout margins (geometry-independent)."""
        pad = 12 if self._regular else content_pad(self._role)
        return QMargins(pad, pad, pad, pad)

    def _rebuild(self) -> None:
        self._path = paper_path(QRectF(self.rect()), self._role, self._seed_key)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._rebuild()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._path is None:
            self._rebuild()
        t = tokens(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        fill = self._fill or t.get(ROLE_FILL.get(self._role, "bg_card"))
        border_key = ROLE_BORDER.get(self._role, "border")
        border = self._border if self._border is not None else (
            t.get(border_key) if border_key else None
        )
        paint_paper(painter, self._path, t, fill, border,
                    shadow=self._role in SHADOW_ROLES)
        painter.end()


class PaperButton(QPushButton):
    """A push button painted as a paper chip; the label is drawn by the style."""

    def __init__(self, text: str = "", role: str = "chip", primary: bool = False,
                 seed_key=None, parent=None):
        super().__init__(text, parent)
        self._role = role if role in SILHOUETTES else "chip"
        self._seed_key = seed_key
        self._primary = primary
        self._path = None
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setProperty("paperRole", self._role)
        self.setProperty("primary", primary)
        self.setMinimumHeight(34)

    def _rebuild(self) -> None:
        self._path = paper_path(QRectF(self.rect()), self._role, self._seed_key)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._rebuild()
        super().resizeEvent(event)

    def _colors(self, t: dict):
        if self._primary:
            base = t["accent"]
            hover = t.get("accent_hover", base)
            down = t.get("accent_pressed", base)
        else:
            base = t.get("bg_card", "#FFFFFF")
            hover = t.get("bg_hover", base)
            down = t.get("bg_active", base)
        if not self.isEnabled():
            return t.get("bg_hover", base)
        if self.isDown():
            return down
        if self.underMouse():
            return hover
        return base

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._path is None:
            self._rebuild()
        t = tokens(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        fill = self._colors(t)
        border = None if self._primary else t.get("border")
        paint_paper(painter, self._path, t, fill, border, shadow=False)
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(t.get("accent", "#E07856")), 2.0))
            painter.drawPath(self._path)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        self.style().drawControl(QStyle.ControlElement.CE_PushButtonLabel,
                                 option, painter, self)
        painter.end()


class PaperSegmented(QWidget):
    """A segmented paper strip: one rounded sheet, the chosen segment tinted.

    Same call surface as the old Look control (``options`` may be
    ``(key, label)`` or ``(key, label, tagline)``), so mode-aware preset
    swapping keeps working. Each option's tagline is a tooltip rather than a
    second piece of UI.
    """

    changed = Signal(str)

    def __init__(self, options, current=None, seed_key="look", parent=None):
        super().__init__(parent)
        self._options: list[tuple[str, str, str]] = []
        self._value = None
        self._hover = None
        self._seed_key = seed_key
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(46)
        self.set_options(options, current)

    def set_options(self, options, current=None) -> None:
        if current is None:
            current = self._value
        self._options = [
            (o[0], o[1], o[2] if len(o) > 2 else "") for o in options
        ]
        keys = [o[0] for o in self._options]
        if current not in keys:
            current = keys[0] if keys else None
        self._value = current
        self.update()

    def value(self):
        return self._value

    def set_value(self, key) -> None:
        if key in [o[0] for o in self._options] and key != self._value:
            self._value = key
            self.update()

    def _strip_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(0, 2, 0, -2)

    def _segments(self) -> list[QRectF]:
        rect = self._strip_rect()
        count = len(self._options)
        if count == 0 or rect.width() <= 2:
            return []
        width = rect.width() / count
        return [
            QRectF(rect.left() + i * width, rect.top(), width, rect.height())
            for i in range(count)
        ]

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        t = tokens(self)
        strip = paper_path(self._strip_rect(), "card", seed_key=self._seed_key)
        paint_paper(painter, strip, t, t.get("bg_card"), t.get("border"))
        segments = self._segments()

        # Fills are clipped to the sheet, so a segment never spills past the
        # rounded edge; the whole control reads as one shape.
        painter.save()
        painter.setClipPath(strip)
        for index, seg in enumerate(segments):
            key = self._options[index][0]
            if key == self._value:
                tint = QColor(t.get("accent"))
                tint.setAlpha(46)
                painter.fillRect(seg, tint)
            elif index == self._hover:
                painter.fillRect(seg, QColor(t.get("bg_hover")))
        painter.restore()
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(t.get("accent", "#E07856")), 2.0))
            painter.drawPath(strip)

        for index, seg in enumerate(segments):
            if index:
                painter.setPen(
                    QPen(QColor(t.get("border_input", t.get("border"))), 1.0)
                )
                painter.drawLine(QPointF(seg.left(), seg.top() + 6),
                                 QPointF(seg.left(), seg.bottom() - 6))
        for index, seg in enumerate(segments):
            selected = self._options[index][0] == self._value
            font = QFont(self.font())
            font.setWeight(QFont.DemiBold if selected else QFont.Normal)
            painter.setFont(font)
            painter.setPen(QColor(t.get("accent") if selected
                                  else t.get("fg_muted")))
            painter.drawText(seg, Qt.AlignCenter, self._options[index][1])
        painter.end()

    def _index_at(self, position) -> int | None:
        for index, seg in enumerate(self._segments()):
            if seg.contains(position):
                return index
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        index = self._index_at(event.position())
        if index != self._hover:
            self._hover = index
            if index is not None and self._options[index][2]:
                self.setToolTip(self._options[index][2])
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hover is not None:
            self._hover = None
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        index = self._index_at(event.position())
        if index is None:
            return
        key = self._options[index][0]
        if key != self._value:
            self._value = key
            self.update()
            self.changed.emit(key)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        keys = [o[0] for o in self._options]
        if not keys or event.key() not in (Qt.Key_Left, Qt.Key_Right):
            return super().keyPressEvent(event)
        index = keys.index(self._value) if self._value in keys else 0
        step = -1 if event.key() == Qt.Key_Left else 1
        new = keys[(index + step) % len(keys)]
        if new != self._value:
            self._value = new
            self.update()
            self.changed.emit(new)
