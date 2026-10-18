"""Render, persist, and load the small region previews shown in Setup.

A preview is an annotated crop of the screenshot that was used to *detect* or
*teach* a region. Keeping it on disk means the Setup window can show the same
picture the user approved in the auto-detect overlay, even after the target app
has been moved, covered, or closed.
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image, ImageDraw
from PySide6.QtGui import QPixmap

from pyaint import paths
from pyaint.annotate import annotate_palette
from pyaint.log import log

CANVAS_OUTLINE = (241, 76, 76)  # matches the detection overlay and annotated preview


def preview_path(name: str, target: str = "") -> str:
    """On-disk path for a tool's preview.

    ``target`` is part of the filename so each per-target snapshot keeps its
    own preview instead of overwriting the previous target's.
    """
    safe = name.replace(" ", "_").lower()
    if target:
        safe = f"{target}_{safe}"
    return os.path.join(paths.PROJECT_ROOT, "previews", f"{safe}_preview.png")


def render_box_preview(image, name: str, box, rows=None, cols=None) -> Image.Image:
    """Return an annotated crop of ``box`` (corner ``x1, y1, x2, y2``)."""
    x1, y1, x2, y2 = (int(v) for v in box)
    width, height = max(1, x2 - x1), max(1, y2 - y1)
    if name == "Palette":
        if not rows or not cols:
            raise ValueError("palette preview needs rows and cols")
        return annotate_palette(image, (x1, y1, width, height), rows, cols)
    crop = image.crop((x1, y1, x1 + width, y1 + height)).convert("RGB")
    draw = ImageDraw.Draw(crop)
    draw.rectangle(
        [0, 0, crop.width - 1, crop.height - 1],
        outline=CANVAS_OUTLINE,
        width=3,
    )
    return crop


def save_preview(image, name: str, target: str = "") -> Optional[str]:
    """Persist ``image`` and return its app-root-relative path (or ``None``)."""
    try:
        filepath = preview_path(name, target)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        image.save(filepath)
        return os.path.relpath(filepath, paths.PROJECT_ROOT)
    except Exception as exc:  # noqa: BLE001
        log.info(f"[Preview] could not save {name} preview: {exc}")
        return None


def store_box_preview(
    entry, name: str, box, image, target: str = "", rows=None, cols=None
) -> Optional[Image.Image]:
    """Render + persist ``box`` and record the path on ``entry``.

    Returns the rendered PIL image so the caller can display it immediately, or
    ``None`` if it could not be produced.
    """
    if image is None:
        return None
    try:
        preview = render_box_preview(image, name, box, rows, cols)
    except Exception as exc:  # noqa: BLE001
        log.info(f"[Preview] could not render {name} preview: {exc}")
        return None
    stored = save_preview(preview, name, target)
    if stored:
        entry["preview"] = stored
    return preview


def resolve_preview(path) -> Optional[str]:
    """Resolve a stored preview path against the app root, if it exists."""
    if not path:
        return None
    resolved = path
    if not os.path.isabs(resolved):
        resolved = os.path.join(paths.PROJECT_ROOT, resolved)
    return resolved if os.path.exists(resolved) else None


def load_preview_pixmap(path) -> Optional[QPixmap]:
    """Load a stored preview into a pixmap, or ``None`` if missing/invalid."""
    resolved = resolve_preview(path)
    if resolved is None:
        return None
    pixmap = QPixmap(resolved)
    return None if pixmap.isNull() else pixmap


def delete_preview(path) -> None:
    """Remove a stored preview file, ignoring missing files and errors."""
    resolved = resolve_preview(path)
    if resolved is None:
        return
    try:
        os.remove(resolved)
    except Exception:
        pass
