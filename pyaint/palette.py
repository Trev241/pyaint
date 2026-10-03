"""Palette sampling and nearest-colour matching."""

import pyautogui


def sample_median(pix, x, y, width, height, radius=1):
    """Return the median RGB of a small square neighbourhood around ``(x, y)``.

    Sampling a single pixel is easily thrown off by an anti-aliased border or
    gap between swatches. The median of a few neighbours is robust to that while
    still landing on the swatch centre. ``radius=0`` returns the exact pixel.
    """
    x0, x1 = max(0, x - radius), min(width - 1, x + radius)
    y0, y1 = max(0, y - radius), min(height - 1, y + radius)
    samples = [pix[xx, yy][:3] for yy in range(y0, y1 + 1) for xx in range(x0, x1 + 1)]
    if not samples:
        return tuple(pix[x, y][:3])
    mid = len(samples) // 2
    return tuple(sorted(sample[i] for sample in samples)[mid] for i in range(3))


class Palette:
    """A rectangular grid of colour swatches and their screen coordinates.

    Build either from an explicit ``colors_pos`` map ``{(r, g, b): (x, y)}``
    (used in tests) or by sampling a screen ``box`` ``(left, top, width,
    height)`` divided into ``rows`` x ``columns`` evenly sized cells.

    If ``image`` (a full-screen PIL image) is given, the box is cropped from it
    instead of taking a fresh screenshot. This lets callers sample from the
    screenshot the detection was computed on, before pyaint is brought back to
    the front over the target app.
    """

    def __init__(self, colors_pos=None, box=None, rows=None, columns=None, image=None):
        if colors_pos is not None:
            self.colors_pos = colors_pos
            self.colors = colors_pos.keys()
            return

        if box is None or rows is None or columns is None:
            raise ValueError("box, rows, and columns must be provided when colors_pos is None")

        self.box = box
        self.rows = rows
        self.columns = columns

        self._csizex = int(box[2] // columns)
        self._csizey = int(box[3] // rows)

        if image is not None:
            left, top, width, height = box
            pix = image.crop((left, top, left + width, top + height)).load()
        else:
            pix = pyautogui.screenshot(region=box).load()

        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()

        # Sample a small median neighbourhood; only widen it when cells are big
        # enough that neighbours can't bleed in.
        sample_radius = 1 if min(self._csizex, self._csizey) >= 4 else 0

        for i in range(columns * rows):
            row = i // columns
            col = i % columns
            x = col * self._csizex + self._csizex // 2
            y = row * self._csizey + self._csizey // 2

            # Clamp coordinates to valid range to prevent index out of bounds.
            x = max(0, min(x, box[2] - 1))
            y = max(0, min(y, box[3] - 1))
            colour = sample_median(pix, x, y, box[2], box[3], sample_radius)
            self.colors_pos[colour] = (box[0] + x, box[1] + y)
            self.colors.add(colour)

    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.dist(color, query))

    @staticmethod
    def dist(colx, coly):
        """Squared Euclidean distance between two RGB triplets.

        The square root is unnecessary for ordering, so it is skipped.
        """
        return sum((s - q) ** 2 for s, q in zip(colx, coly))
