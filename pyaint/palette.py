"""Palette sampling and nearest-colour matching."""

import math

import pyautogui

# Colour-matching metrics. ``ciede2000`` is the perceptual default; ``rgb`` is
# the legacy squared-Euclidean metric, kept selectable for comparison.
METRIC_CIEDE2000 = "ciede2000"
METRIC_RGB = "rgb"
METRICS = (METRIC_CIEDE2000, METRIC_RGB)
DEFAULT_METRIC = METRIC_CIEDE2000

# D65 reference white (matches sRGB) and the CIE constants used by Lab.
_WHITE_X, _WHITE_Y, _WHITE_Z = 0.95047, 1.00000, 1.08883
_EPSILON = 216 / 24389  # (6/29)**3
_KAPPA = 24389 / 27  # (29/3)**3


def _srgb_to_linear(channel: float) -> float:
    channel = channel / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def rgb_to_lab(color):
    """Convert an sRGB ``(r, g, b)`` triplet to CIELAB (D65)."""
    r, g, b = (_srgb_to_linear(c) for c in color[:3])
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t):
        return t ** (1 / 3) if t > _EPSILON else (_KAPPA * t + 16) / 116

    fx, fy, fz = f(x / _WHITE_X), f(y / _WHITE_Y), f(z / _WHITE_Z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(lab1, lab2):
    """CIEDE2000 colour difference (\u0394E00) between two CIELAB triplets."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = 0.5 * (c1 + c2)
    c_bar7 = c_bar ** 7
    g = 0.5 * (1 - math.sqrt(c_bar7 / (c_bar7 + 25 ** 7)))

    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if c1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if c2p else 0.0

    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp_deg = 0.0
    else:
        dhp_deg = h2p - h1p
        if dhp_deg > 180:
            dhp_deg -= 360
        elif dhp_deg < -180:
            dhp_deg += 360
    dhp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp_deg) / 2)

    l_bar_p = 0.5 * (l1 + l2)
    c_bar_p = 0.5 * (c1p + c2p)
    if c1p * c2p == 0:
        h_bar_p = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_bar_p = 0.5 * (h1p + h2p)
    elif h1p + h2p < 360:
        h_bar_p = 0.5 * (h1p + h2p + 360)
    else:
        h_bar_p = 0.5 * (h1p + h2p - 360)

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar_p - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar_p))
        + 0.32 * math.cos(math.radians(3 * h_bar_p + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar_p - 63))
    )
    delta_theta = 30 * math.exp(-(((h_bar_p - 275) / 25) ** 2))
    c_bar_p7 = c_bar_p ** 7
    rc = 2 * math.sqrt(c_bar_p7 / (c_bar_p7 + 25 ** 7))
    sl = 1 + (0.015 * (l_bar_p - 50) ** 2) / math.sqrt(20 + (l_bar_p - 50) ** 2)
    sc = 1 + 0.045 * c_bar_p
    sh = 1 + 0.015 * c_bar_p * t
    rt = -math.sin(math.radians(2 * delta_theta)) * rc

    return math.sqrt(
        (dlp / sl) ** 2
        + (dcp / sc) ** 2
        + (dhp / sh) ** 2
        + rt * (dcp / sc) * (dhp / sh)
    )


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
        self._lab_lookup = {}

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

    def nearest_color(self, query, metric=DEFAULT_METRIC):
        """Return the palette colour closest to ``query`` under ``metric``.

        ``ciede2000`` (default) compares perceptual CIELAB difference;
        ``rgb`` is the legacy squared-Euclidean distance.
        """
        if metric not in METRICS:
            metric = DEFAULT_METRIC
        if metric == METRIC_RGB:
            return min(self.colors, key=lambda color: self.dist(color, query))
        query_lab = self._lab(query)
        return min(
            self.colors,
            key=lambda color: ciede2000(self._lab(color), query_lab),
        )

    def _lab(self, color):
        """Cached sRGB→CIELAB conversion for a palette/query colour."""
        lab = self._lab_lookup.get(color)
        if lab is None:
            lab = rgb_to_lab(color)
            self._lab_lookup[color] = lab
        return lab

    @staticmethod
    def dist(colx, coly):
        """Legacy squared Euclidean distance between two RGB triplets.

        The square root is unnecessary for ordering, so it is skipped. This
        ignores perceptual weighting; ``nearest_color`` uses CIEDE2000 by
        default and only falls back here when ``metric='rgb'``.
        """
        return sum((s - q) ** 2 for s, q in zip(colx, coly))
