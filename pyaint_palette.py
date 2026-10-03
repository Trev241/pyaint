"""Palette sampling and nearest-colour matching.

Extracted from ``bot.py`` so the engine module is smaller and this piece can be
used/tested independently. ``bot`` re-exports :class:`Palette` for backwards
compatibility (``from bot import Palette`` keeps working).
"""

import pyautogui


class Palette:
    """A set of colour swatches and their screen coordinates.

    Build either from an explicit ``colors_pos`` map
    ``{(r, g, b): (x, y)}`` (used in tests) or by sampling a screen ``box``
    ``(left, top, width, height)`` divided into ``rows`` x ``columns`` cells.
    """

    def __init__(self, colors_pos=None, box=None, rows=None, columns=None, valid_positions=None, manual_centers=None):
        if colors_pos is not None:
            self.colors_pos = colors_pos
            self.colors = colors_pos.keys()
            return

        # Validate required parameters
        if box is None or rows is None or columns is None:
            raise ValueError("box, rows, and columns must be provided when colors_pos is None")

        self.box = box
        self.rows = rows
        self.columns = columns

        self._csizex = int(box[2] // columns)
        self._csizey = int(box[3] // rows)

        pix = pyautogui.screenshot(region=box).load()

        # Obtain RGB values of palette colors along with their coordinates
        # COLOR LAYOUT    :    ((r, g, b) : (x, y))
        self.colors_pos = dict()
        self.colors = set()

        # If valid_positions is None, assume all positions are valid
        if valid_positions is None:
            valid_positions = set(range(columns * rows))

        # If manual_centers is None, use automatic center calculation
        if manual_centers is None:
            manual_centers = {}

        for i in range(columns * rows):
            # Skip invalid positions
            if i not in valid_positions:
                continue

            # Use manual center if provided, otherwise calculate automatic center
            if i in manual_centers:
                # Use manually picked center coordinates (relative to palette box)
                center_x, center_y = manual_centers[i]
                # Convert to absolute screen coordinates
                x = center_x
                y = center_y
            else:
                # Calculate automatic center of the grid cell
                row = i // columns
                col = i % columns
                x = col * self._csizex + self._csizex // 2
                y = row * self._csizey + self._csizey // 2

            # Clamp coordinates to valid range to prevent index out of bounds
            x = max(0, min(x, box[2] - 1))
            y = max(0, min(y, box[3] - 1))
            col = (pix[x, y][:3])
            self.colors_pos[col] = (box[0] + x, box[1] + y)
            self.colors.add(col)

    def nearest_color(self, query):
        return min(self.colors, key=lambda color: Palette.dist(color, query))

    @staticmethod
    def dist(colx, coly):
        """
        Returns the squared distance between two RGB triplets. Since finding the root of
        the distances has no effect on the sorting order of the final distances, it has
        been avoided altogether for the sake of performance
        """
        return sum((s - q) ** 2 for s, q in zip(colx, coly))
