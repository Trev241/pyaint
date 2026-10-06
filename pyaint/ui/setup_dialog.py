"""Setup dialog: teach Pyaint where the target app's tools are.

Reuses the shared :class:`~pyaint.profile.Profile` so there is nothing to merge
back. Click capture is handled by :mod:`pyaint.ui.capture`.
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyaint import paths
from pyaint.annotate import annotate_palette
from pyaint.log import log
from pyaint.ui.capture import pick_points
from pyaint.ui.widgets import CheckBox, ImagePreview, pil_to_qpixmap

_FRIENDLY = {
    "Palette": "Palette",
    "Canvas": "Canvas",
    "New Layer": "New layer",
    "Color Button": "Color button",
    "Color Button Okay": "Color button OK",
}

_DESCRIPTIONS = {
    "Palette": "A grid of swatches. Click its top-left and bottom-right corners, then set the rows and columns.",
    "Canvas": "The drawing surface. Click its top-left and bottom-right corners.",
    "New Layer": "The button that creates a new layer (optional).",
    "Color Button": "A button clicked before palette selection (optional).",
    "Color Button Okay": "A button clicked after palette selection (optional).",
}

_BOX_TOOLS = {"Palette", "Canvas"}
_COORD_TOOLS = {"New Layer", "Color Button", "Color Button Okay"}
_MODIFIER_TOOLS = {"New Layer", "Color Button", "Color Button Okay"}
_DELAY_TOOLS = {"Color Button", "Color Button Okay"}


def _preview_path(name: str, target: str = "") -> str:
    """Stable on-disk path for a tool's annotated preview.

    The target id is part of the filename so each app's per-target snapshot
    keeps its own preview instead of overwriting the previous target's.
    """
    safe = name.replace(" ", "_").lower()
    if target:
        safe = f"{target}_{safe}"
    return os.path.join(paths.PROJECT_ROOT, "previews", f"{safe}_preview.png")


def _save_preview(image, name: str, target: str = ""):
    """Persist ``image`` so the preview survives closing Setup. Returns path."""
    try:
        filepath = _preview_path(name, target)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        image.save(filepath)
        return os.path.relpath(filepath, paths.PROJECT_ROOT)
    except Exception as exc:  # noqa: BLE001
        log.info(f"[Setup] could not save {name} preview: {exc}")
        return None


def _load_preview_pixmap(path) -> Optional[QPixmap]:
    """Resolve a stored preview path (absolute or relative to the app root)."""
    if not path:
        return None
    resolved = path
    if not os.path.isabs(resolved):
        resolved = os.path.join(paths.PROJECT_ROOT, resolved)
    if not os.path.exists(resolved):
        return None
    pixmap = QPixmap(resolved)
    return None if pixmap.isNull() else pixmap


def _delete_preview(path) -> None:
    if not path:
        return
    resolved = path
    if not os.path.isabs(resolved):
        resolved = os.path.join(paths.PROJECT_ROOT, resolved)
    try:
        if os.path.exists(resolved):
            os.remove(resolved)
    except Exception:
        pass


class SetupDialog(QDialog):
    def __init__(self, parent, bot, profile, required_tools=()):
        super().__init__(parent)
        self.setWindowTitle("Pyaint — Setup")
        self.resize(920, 600)
        self.bot = bot
        self.profile = profile
        self._current = None

        self._tools = [t for t in required_tools if t in _FRIENDLY]

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: tool list
        self._list = QListWidget()
        self._list.setFixedWidth(240)
        for name in self._tools:
            self._list.addItem(QListWidgetItem())
        self._list.currentRowChanged.connect(self._select_tool)
        root.addWidget(self._list)

        # Right: details + buttons
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 16)
        right_layout.setSpacing(10)

        self._name_label = QLabel()
        self._name_label.setObjectName("DialogTitle")
        right_layout.addWidget(self._name_label)

        self._desc_label = QLabel()
        self._desc_label.setObjectName("DialogHint")
        self._desc_label.setWordWrap(True)
        right_layout.addWidget(self._desc_label)

        self._status_label = QLabel()
        self._status_label.setObjectName("DialogStatus")
        right_layout.addWidget(self._status_label)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self._teach_btn = QPushButton("Teach…")
        self._teach_btn.setToolTip("Capture this region from the target app")
        self._teach_btn.clicked.connect(self._teach)
        action_row.addWidget(self._teach_btn)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("Danger")
        self._clear_btn.setToolTip("Forget this tool's taught position")
        self._clear_btn.clicked.connect(self._clear_current)
        action_row.addWidget(self._clear_btn)
        action_row.addStretch(1)
        right_layout.addLayout(action_row)

        # Palette geometry
        self._palette_box = QWidget()
        palette_layout = QHBoxLayout(self._palette_box)
        palette_layout.setContentsMargins(0, 0, 0, 0)
        palette_layout.addWidget(QLabel("Rows"))
        self._rows = QSpinBox()
        self._rows.setRange(1, 50)
        self._rows.setValue(int(self.profile["Palette"].get("rows", 6) or 6))
        palette_layout.addWidget(self._rows)
        palette_layout.addWidget(QLabel("Columns"))
        self._cols = QSpinBox()
        self._cols.setRange(1, 50)
        self._cols.setValue(int(self.profile["Palette"].get("cols", 8) or 8))
        palette_layout.addWidget(self._cols)
        palette_layout.addStretch(1)
        right_layout.addWidget(self._palette_box)

        self._preview_label = QLabel("Preview")
        self._preview_label.setObjectName("FieldLabel")
        self._preview_label.setVisible(False)
        right_layout.addWidget(self._preview_label)

        self._palette_preview = ImagePreview()
        self._palette_preview.setMinimumHeight(120)
        self._palette_preview.setVisible(False)
        right_layout.addWidget(self._palette_preview)

        self._palette_feedback = QLabel()
        self._palette_feedback.setObjectName("DialogHint")
        self._palette_feedback.setWordWrap(True)
        self._palette_feedback.setVisible(False)
        right_layout.addWidget(self._palette_feedback)

        # Enabling (optional tools)
        self._enable_box = QWidget()
        enable_layout = QVBoxLayout(self._enable_box)
        enable_layout.setContentsMargins(0, 0, 0, 0)
        self._enable = CheckBox("Enable this tool")
        self._enable.toggled.connect(self._on_enable_toggled)
        enable_layout.addWidget(self._enable)

        modifier_row = QHBoxLayout()
        modifier_row.addWidget(QLabel("Modifiers:"))
        self._modifiers = {}
        for key in ("ctrl", "alt", "shift"):
            box = CheckBox(key.capitalize())
            box.toggled.connect(self._on_modifiers_toggled)
            self._modifiers[key] = box
            modifier_row.addWidget(box)
        modifier_row.addStretch(1)
        enable_layout.addLayout(modifier_row)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay (ms)"))
        self._delay = QSpinBox()
        self._delay.setRange(0, 5000)
        self._delay.setSingleStep(50)
        self._delay.setValue(100)
        self._delay.valueChanged.connect(self._on_delay_changed)
        delay_row.addWidget(self._delay)
        delay_row.addStretch(1)
        enable_layout.addLayout(delay_row)
        right_layout.addWidget(self._enable_box)

        right_layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        right_layout.addLayout(buttons)

        root.addWidget(right, 1)

        self._refresh_list()
        if self._list.count():
            self._list.setCurrentRow(0)

    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        current = self._current
        self._list.blockSignals(True)
        for row, name in enumerate(self._tools):
            entry = self.profile.get(name, {})
            mark = "✓" if entry.get("status") else "○"
            self._list.item(row).setText(f"  {mark}   {_FRIENDLY[name]}")
        self._list.blockSignals(False)
        if current in self._tools:
            self._list.setCurrentRow(self._tools.index(current))

    def _select_tool(self, row: int) -> None:
        if row < 0 or row >= len(self._tools):
            self._current = None
            return
        name = self._tools[row]
        self._current = name
        entry = self.profile.get(name, {})
        self._name_label.setText(_FRIENDLY[name])
        self._desc_label.setText(_DESCRIPTIONS.get(name, ""))
        status = "Configured" if entry.get("status") else "Not set"
        self._status_label.setText(f"Status: {status}")
        is_palette = name == "Palette"
        is_box = name in _BOX_TOOLS
        self._palette_box.setVisible(is_palette)
        self._preview_label.setVisible(is_box)
        self._palette_preview.setVisible(is_box)
        self._palette_feedback.setVisible(is_box)
        if is_box:
            self._show_box_preview(name, entry)
        self._enable_box.setVisible(name in _MODIFIER_TOOLS)
        self._clear_btn.setEnabled(
            bool(entry.get("status") or entry.get("box") or entry.get("coords"))
        )
        self._enable.setChecked(bool(entry.get("enabled")))
        modifiers = entry.get("modifiers", {}) or {}
        for key, box in self._modifiers.items():
            box.setChecked(bool(modifiers.get(key, False)))
        self._delay.setValue(int(float(entry.get("delay", 0.1)) * 1000))

    def _show_box_preview(self, name: str, entry) -> None:
        """Refresh the captured-region preview and feedback for a box tool."""
        if name == "Palette":
            self._preview_label.setText("Palette preview")
            empty = "No preview yet — click Teach… to capture the swatch grid."
        else:
            self._preview_label.setText("Canvas preview")
            empty = "No preview yet — click Teach… to capture the canvas."

        pixmap = _load_preview_pixmap(entry.get("preview"))
        if pixmap is not None:
            self._palette_preview.set_pixmap(pixmap)
        else:
            self._palette_preview.set_placeholder(empty)

        if name != "Palette":
            self._palette_feedback.setText(
                "✓ Canvas region captured."
                if entry.get("status") and pixmap is not None
                else empty
            )
            return

        coords = entry.get("color_coords") or {}
        rows = entry.get("rows")
        cols = entry.get("cols")
        if entry.get("status") and coords:
            grid = f" ({rows} × {cols})" if rows and cols else ""
            self._palette_feedback.setText(f"✓ {len(coords)} colours sampled{grid}.")
        elif entry.get("status"):
            self._palette_feedback.setText(
                "Configured, but no colour preview is saved. Teach it again to "
                "check the swatches."
            )
        else:
            self._palette_feedback.setText(
                "Not set — teach the palette to sample its swatches."
            )

    def _teach(self) -> None:
        name = self._current
        if name is None:
            return
        friendly = _FRIENDLY[name]
        if name in _BOX_TOOLS:
            result = pick_points(self, 2, f"Click the UPPER-LEFT then LOWER-RIGHT corner of the {friendly}.")
            if not result:
                return
            (x1, y1), (x2, y2) = result.points
            box = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            self._apply_box(name, box, image=result.image)
        else:
            result = pick_points(self, 1, f"Click the {friendly} in the target app.")
            if not result:
                return
            x, y = result.points[0]
            entry = self.profile[name]
            entry["coords"] = [x, y]
            entry["status"] = True
        self._refresh_list()
        self._select_tool(self._list.currentRow())

    def _apply_box(self, name: str, box, image=None) -> None:
        entry = self.profile[name]
        entry["box"] = list(box)
        try:
            if name == "Canvas":
                self.bot.init_canvas(box)
                self._store_box_preview(name, entry, box, image)
            elif name == "Palette":
                if not self._setup_palette(box, image=image):
                    # Sampling failed; do not leave a half-configured palette
                    # showing as ready. The warning was already shown.
                    entry["status"] = False
                    return
        except Exception as exc:  # noqa: BLE001
            entry["status"] = False
            log.info(f"[Setup] applying {name} failed: {exc}")
            self.raise_()
            self.activateWindow()
            QMessageBox.warning(
                self,
                "Setup",
                f"Could not apply the {_FRIENDLY.get(name, name)} setting: {exc}",
            )
            return
        entry["status"] = True

    def _store_box_preview(self, name: str, entry, box, image) -> bool:
        """Annotate and persist the captured region so feedback survives."""
        if image is None:
            return False
        try:
            x, y = box[0], box[1]
            w, h = box[2] - box[0], box[3] - box[1]
            if name == "Palette":
                preview = annotate_palette(
                    image, (x, y, w, h), entry["rows"], entry["cols"]
                )
            else:
                from PIL import ImageDraw

                preview = image.crop((x, y, x + w, y + h)).convert("RGB")
                draw = ImageDraw.Draw(preview)
                draw.rectangle(
                    [0, 0, preview.width - 1, preview.height - 1],
                    outline=(241, 76, 76),
                    width=3,
                )
            stored = _save_preview(preview, name, self.profile.target)
            if stored:
                entry["preview"] = stored
            self._palette_preview.set_pixmap(pil_to_qpixmap(preview))
            return True
        except Exception as exc:  # noqa: BLE001
            log.info(f"[Setup] {name} preview failed: {exc}")
            return False

    def _setup_palette(self, box, image=None) -> bool:
        """Sample a taught palette box. Returns ``False`` if it could not run."""
        rows = self._rows.value()
        cols = self._cols.value()
        entry = self.profile["Palette"]
        entry["rows"] = rows
        entry["cols"] = cols
        if image is None:
            # Without the screenshot from teaching time, the only fallback is a
            # fresh grab -- which shows this dialog, not the target palette. Do
            # not silently sample the wrong thing.
            self.raise_()
            self.activateWindow()
            QMessageBox.warning(
                self,
                "Palette",
                "Could not capture the screen while teaching, so the palette "
                "cannot be sampled. Close other windows and try again.",
            )
            return False
        if box[2] - box[0] < 2 or box[3] - box[1] < 2:
            self.raise_()
            self.activateWindow()
            QMessageBox.warning(
                self,
                "Palette",
                "The two corners are on top of each other, so there is no "
                "palette to sample. Pick the top-left and bottom-right corners "
                "of the swatch grid.",
            )
            return False
        try:
            palette = self.bot.init_palette(
                pbox=(box[0], box[1], box[2] - box[0], box[3] - box[1]),
                prows=rows,
                pcols=cols,
                image=image,
            )
            entry["color_coords"] = {str(k): list(v) for k, v in palette.colors_pos.items()}
            self._store_box_preview("Palette", entry, box, image)
            if len(palette.colors) <= 1:
                # Make sure the warning is not a hidden modal if the picker
                # left the dialog behind/ inactive.
                self.raise_()
                self.activateWindow()
                QMessageBox.warning(
                    self,
                    "Palette",
                    "Only one distinct colour was sampled. Make sure the target "
                    "app was visible when you clicked the corners, and that the "
                    "rows/columns match the palette.",
                )
            return True
        except Exception as exc:  # noqa: BLE001
            log.info(f"[Setup] palette sampling failed: {exc}")
            self.raise_()
            self.activateWindow()
            QMessageBox.warning(
                self,
                "Palette",
                f"Could not sample the palette: {exc}. Make sure the target app "
                "was visible when you clicked the corners.",
            )
            return False

    # ------------------------------------------------------------------
    def _clear_current(self) -> None:
        """Forget the selected tool's taught position."""
        name = self._current
        if name is None:
            return
        entry = self.profile.get(name)
        if not entry:
            return
        if not (entry.get("status") or entry.get("box") or entry.get("coords")):
            return
        answer = QMessageBox.question(
            self,
            "Clear setting",
            f"Forget the learned {_FRIENDLY[name]} position? You can teach it "
            "again at any time.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._clear_tool(name)
        self._refresh_list()
        self._select_tool(self._list.currentRow())

    def _clear_tool(self, name: str) -> None:
        entry = self.profile[name]
        entry["status"] = False
        if name in _BOX_TOOLS:
            entry["box"] = None
            _delete_preview(entry.get("preview"))
            entry["preview"] = None
            if name == "Palette":
                entry["color_coords"] = None
                self.bot._palette = None
            # ``bot._canvas`` derives from ``profile["Canvas"]["box"]`` above.
        else:
            entry["coords"] = None

    # ------------------------------------------------------------------
    def _on_enable_toggled(self, checked: bool) -> None:
        if self._current:
            self.profile[self._current]["enabled"] = bool(checked)

    def _on_modifiers_toggled(self) -> None:
        if not self._current:
            return
        self.profile[self._current]["modifiers"] = {
            key: box.isChecked() for key, box in self._modifiers.items()
        }

    def _on_delay_changed(self, milliseconds: int) -> None:
        if self._current:
            self.profile[self._current]["delay"] = milliseconds / 1000.0

    def _save(self) -> None:
        # Normalise tuple boxes for JSON serialization.
        for name in _BOX_TOOLS:
            box = self.profile.get(name, {}).get("box")
            if isinstance(box, tuple):
                self.profile[name]["box"] = list(box)
        self.accept()
