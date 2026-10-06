"""Setup dialog: teach Pyaint where the target app's tools are.

Reuses the shared :class:`~pyaint.profile.Profile` so there is nothing to merge
back. Click capture is handled by :mod:`pyaint.ui.capture`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
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

        self._teach_btn = QPushButton("Teach…")
        self._teach_btn.clicked.connect(self._teach)
        right_layout.addWidget(self._teach_btn, 0, Qt.AlignLeft)

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

        self._palette_preview = ImagePreview()
        self._palette_preview.setMinimumHeight(90)
        self._palette_preview.setVisible(False)
        right_layout.addWidget(self._palette_preview)

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
        self._palette_box.setVisible(name == "Palette")
        self._palette_preview.setVisible(name == "Palette")
        self._enable_box.setVisible(name in _MODIFIER_TOOLS)
        self._enable.setChecked(bool(entry.get("enabled")))
        modifiers = entry.get("modifiers", {}) or {}
        for key, box in self._modifiers.items():
            box.setChecked(bool(modifiers.get(key, False)))
        self._delay.setValue(int(float(entry.get("delay", 0.1)) * 1000))

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
            try:
                preview = annotate_palette(
                    image,
                    (box[0], box[1], box[2] - box[0], box[3] - box[1]),
                    rows,
                    cols,
                )
                self._palette_preview.set_pixmap(pil_to_qpixmap(preview))
            except Exception as exc:  # noqa: BLE001
                log.info(f"[Setup] palette preview failed: {exc}")
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
