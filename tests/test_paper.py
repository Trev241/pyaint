"""Tests for the subtle "paper on a desk" surface language.

The hero sheet must be deterministic for a given ``(role, seed_key)`` and stay
close to its rect; every other role must be a plain rounded rectangle, so paper
is confined to the artwork. The whole language must be switchable off.

Geometry/determinism live here as the fast layer. The rendered look is pinned
separately by ``tests/snapshots`` (see ``test_paper_snapshots.py``).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pyaint.ui import paper  # noqa: E402

pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def app():
    yield QApplication.instance() or QApplication([])


def _bounds(rect, role, seed_key=None):
    return paper.paper_path(QRectF(*rect), role, seed_key=seed_key).boundingRect()


def test_hero_is_deterministic(app):
    a = _bounds((0, 0, 300, 200), "hero", "one")
    b = _bounds((0, 0, 300, 200), "hero", "one")
    assert a == b


def test_seed_key_changes_the_shape(app):
    a = _bounds((0, 0, 300, 200), "hero", "one")
    b = _bounds((0, 0, 300, 200), "hero", "two")
    assert a != b


def test_hero_stays_near_its_rect_and_leans(app):
    rect = QRectF(10, 20, 300, 200)
    spec = paper.SILHOUETTES["hero"]
    slack = spec["inset"] + spec["jitter"] + spec["bow"] + 4
    bounds = _bounds((10, 20, 300, 200), "hero", "x")
    assert bounds.left() >= rect.left() - slack
    assert bounds.top() >= rect.top() - slack
    assert bounds.right() <= rect.right() + slack
    assert bounds.bottom() <= rect.bottom() + slack
    # A hero sheet must not be a plain rectangle.
    assert bounds != rect


def test_non_paper_roles_are_plain_rects(app):
    rect = QRectF(0, 0, 300, 200)
    for role in ("card", "chip", "mode", "bar", "column"):
        assert _bounds((0, 0, 300, 200), role, "k") == rect, role


def test_paper_off_flattens_the_hero(app, monkeypatch):
    monkeypatch.setenv("PYAINT_PAPER", "off")
    assert _bounds((0, 0, 300, 200), "hero", "x") == QRectF(0, 0, 300, 200)


def test_paper_amount_is_parsed(app, monkeypatch):
    monkeypatch.setenv("PYAINT_PAPER", "0.25")
    assert paper._paper_amount() == pytest.approx(0.25)
    monkeypatch.setenv("PYAINT_PAPER", "nonsense")
    assert paper._paper_amount() == paper.PAPER_AMOUNT


def test_content_rect_is_the_declared_margin(app):
    from pyaint.ui.paper import content_pad, content_rect

    rect = QRectF(0, 0, 400, 300)
    for role in ("hero", "column", "card", "chip"):
        pad = content_pad(role)
        safe = content_rect(rect, role)
        assert safe.left() == pytest.approx(pad)
        assert safe.top() == pytest.approx(pad)
        assert safe.right() == pytest.approx(400 - pad)
        assert safe.bottom() == pytest.approx(300 - pad)
    assert content_pad("hero") > content_pad("chip")


def test_surface_paints_a_sheet(app):
    from PySide6.QtGui import QImage
    from pyaint.ui.paper import PaperSurface

    surface = PaperSurface("card")
    surface.resize(200, 120)
    image = QImage(200, 120, QImage.Format_ARGB32)
    image.fill(0)
    surface.render(image)
    assert any(image.pixelColor(x, y).alpha() > 0
               for x in range(0, 200, 20) for y in range(0, 120, 20))


def test_segmented_selects_one_tab(app):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    from pyaint.ui.paper import PaperSegmented

    seen: list[str] = []
    control = PaperSegmented(
        [("a", "Alpha", "first"), ("b", "Beta", "second"),
         ("c", "Gamma", "third")],
        "a",
    )
    control.changed.connect(seen.append)
    control.resize(300, 80)
    assert control.value() == "a"
    QTest.mouseClick(control, Qt.LeftButton, pos=QPoint(150, 40))
    assert control.value() == "b"
    assert seen == ["b"]
