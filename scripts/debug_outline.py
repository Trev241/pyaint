"""Developer tool: render the OUTLINE cleaner stages for one image.

Usage::

    python scripts/debug_outline.py IMAGE [options]

Options:
    --canvas X Y W H   canvas rectangle (default: 0 0 800 600)
    --step N           pixel size / grid step (default: 4)
    --smoothing N      bilateral smoothing level, 0-5 (default: 2)
    --cleanup N        shading-cleanup Lab distance, 0-30 (default: 10)
    --colors N         adaptive segmentation colours (default: 48)
    --outdir DIR       output directory (default: build/outline_debug)

Writes one PNG per stage (quantized / soft_merged / final / removed / strokes)
plus ``overlay.png`` (the traced strokes drawn black over the source) and
``contact_sheet.png``. The palette is read from ``config.json`` when present;
Outline segments adaptively, so the target palette is only a fallback.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyaint import planner  # noqa: E402
from pyaint.palette import Palette  # noqa: E402


def _config_palette() -> Palette:
    colors = []
    try:
        with open("config.json", encoding="utf-8") as handle:
            config = json.load(handle)
        for key in config.get("Palette", {}).get("color_coords") or {}:
            colors.append(tuple(int(v) for v in ast.literal_eval(key)))
    except Exception:
        pass
    if not colors:
        colors = [(0, 0, 0), (255, 255, 255)]
    return Palette(colors_pos={c: (i % 10, i // 10) for i, c in enumerate(colors)})


def _tile(images, columns=2, background=235):
    """Tile equally-sized BGR images into a grid (nearest, no smoothing)."""
    if not images:
        return None
    rows = (len(images) + columns - 1) // columns
    height, width = images[0].shape[:2]
    sheet = np.full((rows * height, columns * width, 3), background, np.uint8)
    for index, image in enumerate(images):
        row, column = divmod(index, columns)
        sheet[
            row * height : (row + 1) * height,
            column * width : (column + 1) * width,
        ] = image
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--canvas", nargs=4, type=int, default=[0, 0, 800, 600])
    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--smoothing", type=float, default=planner.OUTLINE_SMOOTHING)
    parser.add_argument("--cleanup", type=float, default=planner.OUTLINE_STEP_THRESHOLD)
    parser.add_argument("--colors", type=int, default=planner.OUTLINE_SEGMENTATION_COLORS)
    parser.add_argument("--outdir", default=os.path.join("build", "outline_debug"))
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    palette = _config_palette()

    source_image = Image.open(args.image).convert("RGBA")
    source, (tw, th), xo, yo = planner.fit_to_canvas(
        source_image, tuple(args.canvas), args.step
    )
    stage_path = os.path.join(args.outdir, "stages.png")

    started = time.time()
    cmap = planner.plan_outline(
        source,
        xo,
        yo,
        args.step,
        (tw, th),
        palette,
        0,
        smooth_strength=args.smoothing,
        step_threshold=args.cleanup,
        segmentation_colors=args.colors,
        debug=True,
        debug_path=stage_path,
    )
    elapsed = time.time() - started
    strokes = cmap.get(planner.OUTLINE_COLOUR, [])
    print(
        f"{os.path.basename(args.image)}: {len(strokes)} strokes in {elapsed:.2f}s "
        f"-> {args.outdir}"
    )

    # Map the canvas-space strokes back onto the source for a line-art overlay.
    factor = source.size[0] / (tw * args.step)
    factor_y = source.size[1] / (th * args.step)
    overlay = np.asarray(source.convert("RGB")).copy()
    for stroke in strokes:
        points = np.array(
            [
                [
                    (
                        int(round((x - xo) * factor)),
                        int(round((y - yo) * factor_y)),
                    )
                ]
                for x, y in stroke
            ],
            np.int32,
        ).reshape(-1, 1, 2)
        if len(points) >= 2:
            cv2.polylines(
                overlay, [points], False, (0, 0, 0), 1, lineType=cv2.LINE_AA
            )
    cv2.imwrite(
        os.path.join(args.outdir, "overlay.png"),
        cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
    )

    base = os.path.splitext(stage_path)[0]
    sheet_sources = [
        f"{base}_{name}.png"
        for name in ("quantized", "soft_merged", "final", "removed")
    ]
    tiles = [
        cv2.imread(path)
        for path in sheet_sources
        if os.path.exists(path)
    ]
    sheet = _tile([tile for tile in tiles if tile is not None])
    if sheet is not None:
        cv2.imwrite(os.path.join(args.outdir, "contact_sheet.png"), sheet)

    # Regions + strokes at each stage, side by side: this is the image that
    # makes the merge's effect on the traced contours easy to read.
    contour_sources = [
        f"{base}_{name}_contours.png"
        for name in ("quantized", "soft_merged", "final")
    ]
    contour_tiles = [
        cv2.imread(path) for path in contour_sources if os.path.exists(path)
    ]
    contour_sheet = _tile(
        [tile for tile in contour_tiles if tile is not None], columns=3
    )
    if contour_sheet is not None:
        cv2.imwrite(os.path.join(args.outdir, "contours_sheet.png"), contour_sheet)


if __name__ == "__main__":
    main()
