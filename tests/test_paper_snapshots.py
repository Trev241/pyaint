"""Render snapshots for the "paper on a desk" hero sheet.

The whole point of the surface language is how the hero looks, so geometry
assertions alone are not enough. Each theme's hero sheet is rendered offscreen
and compared, downsampled, against a checked-in PNG with a small tolerance --
enough to catch a wrecked shape, colour or amount without being brittle to
antialiasing differences between Qt builds.

Regenerate the expectations with ``python tests/test_paper_snapshots.py``.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pyaint.ui import theme  # noqa: E402

pytestmark = pytest.mark.ui

SIZE = (320, 200)
GRID = 16
TOLERANCE = 12  # mean per-channel difference over the downsampled grid

SNAPSHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")


@pytest.fixture(scope="module")
def app():
    yield QApplication.instance() or QApplication([])


def _render(tokens) -> QImage:
    from pyaint.ui.paper import PaperSurface

    surface = PaperSurface("hero")
    surface.resize(*SIZE)
    surface.setProperty("pyaint_tokens", tokens)
    image = QImage(*SIZE, QImage.Format_ARGB32)
    image.fill(0)
    surface.render(image)
    return image


def _signature(image: QImage) -> list[tuple[int, int, int]]:
    small = image.scaled(
        GRID, GRID, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    ).convertToFormat(QImage.Format_RGBA8888)
    return [
        small.pixelColor(x, y).getRgb()[:3]
        for y in range(GRID)
        for x in range(GRID)
    ]


def _mean_diff(a, b) -> float:
    total = 0
    for (r1, g1, b1), (r2, g2, b2) in zip(a, b):
        total += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    return total / (3 * len(a))


@pytest.mark.parametrize("name,tokens", [("light", theme.LIGHT), ("dark", theme.DARK)])
def test_hero_snapshot(app, name, tokens, monkeypatch):
    monkeypatch.setenv("PYAINT_PAPER", "0.6")
    expected_path = os.path.join(SNAPSHOTS, f"paper_hero_{name}.png")
    expected = QImage(expected_path)
    assert not expected.isNull(), f"missing snapshot {expected_path}"
    actual = _render(tokens)
    diff = _mean_diff(_signature(actual), _signature(expected))
    assert diff <= TOLERANCE, f"{name}: hero drifted (mean diff {diff:.1f})"


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    os.makedirs(SNAPSHOTS, exist_ok=True)
    for name, tokens in (("light", theme.LIGHT), ("dark", theme.DARK)):
        path = os.path.join(SNAPSHOTS, f"paper_hero_{name}.png")
        _render(tokens).save(path)
        print("wrote", path)
