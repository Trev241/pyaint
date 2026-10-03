"""Visual theme for the PySide6 UI.

Design tokens are based on VS Code's "Dark Modern" palette: flat surfaces,
1px borders, no gradients or bevels, and a single blue accent. Everything is
centralised here so the look can be adjusted (or a light theme added) in one
place.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont

# --- Design tokens ---------------------------------------------------------
TOKENS = {
    # Surfaces
    "bg": "#1f1f1f",            # editor / content
    "bg_activity": "#181818",   # activity rail
    "bg_side": "#181818",       # side bar
    "bg_status": "#181818",     # status bar
    "bg_input": "#313131",      # text inputs, sliders
    "bg_hover": "#2a2d2e",      # hover
    "bg_active": "#37373d",     # pressed / selected control
    "bg_card": "#232323",       # raised section
    # Lines
    "border": "#2b2b2b",
    "border_input": "#3c3c3c",
    # Text
    "fg": "#cccccc",
    "fg_muted": "#9d9d9d",
    "fg_dim": "#6e7681",
    # Accent
    "accent": "#0078d4",
    "accent_hover": "#026ec1",
    "accent_pressed": "#025a9e",
    "accent_fg": "#ffffff",
    # Feedback
    "danger": "#f14c4c",
    "success": "#4ec9b0",
    "warning": "#cca700",
}

ACCENT = TOKENS["accent"]


def mono_font(size: int = 10) -> QFont:
    font = QFont("Cascadia Mono")
    font.setStyleHint(QFont.Monospace)
    font.setPointSize(size)
    return font


def stylesheet() -> str:
    """Return the application-wide Qt stylesheet."""
    t = TOKENS
    return f"""
    * {{
        font-family: "Segoe UI", "SF Pro Text", "Ubuntu", sans-serif;
        font-size: 12px;
        outline: none;
    }}

    QMainWindow, QDialog {{
        background: {t['bg']};
    }}
    QWidget {{
        color: {t['fg']};
    }}
    QToolTip {{
        background: {t['bg_card']};
        color: {t['fg']};
        border: 1px solid {t['border_input']};
        padding: 4px 6px;
    }}

    /* --- Activity rail -------------------------------------------------- */
    #ActivityRail {{
        background: {t['bg_activity']};
        border-right: 1px solid {t['border']};
    }}
    #ActivityRail QToolButton {{
        background: transparent;
        border: none;
        border-left: 2px solid transparent;
        padding: 10px 0;
    }}
    #ActivityRail QToolButton:hover {{
        background: {t['bg_hover']};
    }}
    #ActivityRail QToolButton:checked {{
        border-left: 2px solid {t['accent']};
        background: {t['bg_active']};
    }}

    /* --- Side bar ------------------------------------------------------- */
    #SideBar {{
        background: {t['bg_side']};
        border-right: 1px solid {t['border']};
    }}
    #SideBarTitle {{
        color: {t['fg_muted']};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1px;
        padding: 10px 12px 4px 12px;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    /* --- Sections ------------------------------------------------------- */
    #Section {{
        background: transparent;
        border-bottom: 1px solid {t['border']};
    }}
    #SectionTitle {{
        color: {t['fg']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        padding: 12px 12px 2px 12px;
    }}
    #SectionHint {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 0 12px 6px 12px;
    }}
    #FieldLabel {{
        color: {t['fg_muted']};
        font-size: 11px;
        padding: 0 12px;
    }}
    #FieldValue {{
        color: {t['fg']};
        font-size: 11px;
        font-weight: 600;
        padding: 0 12px;
    }}

    /* --- Buttons -------------------------------------------------------- */
    QPushButton {{
        background: {t['bg_input']};
        border: 1px solid {t['border_input']};
        border-radius: 2px;
        padding: 5px 12px;
        color: {t['fg']};
    }}
    QPushButton:hover {{
        background: {t['bg_active']};
    }}
    QPushButton:pressed {{
        background: {t['bg_hover']};
    }}
    QPushButton:disabled {{
        color: {t['fg_dim']};
        background: {t['bg_card']};
    }}
    QPushButton#Primary {{
        background: {t['accent']};
        border: 1px solid {t['accent']};
        color: {t['accent_fg']};
        font-weight: 600;
    }}
    QPushButton#Primary:hover {{
        background: {t['accent_hover']};
    }}
    QPushButton#Primary:pressed {{
        background: {t['accent_pressed']};
    }}
    QPushButton#Danger {{
        color: {t['danger']};
    }}
    QPushButton#ToolBarButton {{
        background: transparent;
        border: 1px solid transparent;
        padding: 4px 10px;
    }}
    QPushButton#ToolBarButton:hover {{
        background: {t['bg_hover']};
    }}

    /* --- Inputs --------------------------------------------------------- */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {t['bg_input']};
        border: 1px solid {t['border_input']};
        border-radius: 2px;
        padding: 4px 6px;
        selection-background-color: {t['accent']};
        min-height: 18px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {t['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}
    QComboBox QAbstractItemView {{
        background: {t['bg_card']};
        border: 1px solid {t['border_input']};
        selection-background-color: {t['accent']};
        outline: none;
    }}

    /* --- Checkboxes ----------------------------------------------------- */
    QCheckBox {{
        color: {t['fg']};
        spacing: 8px;
        padding: 3px 12px;
    }}
    QCheckBox:disabled {{
        color: {t['fg_dim']};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {t['border_input']};
        border-radius: 2px;
        background: {t['bg_input']};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {t['accent']};
    }}
    QCheckBox::indicator:checked {{
        background: {t['accent']};
        border: 1px solid {t['accent']};
        image: none;
    }}

    /* --- Sliders -------------------------------------------------------- */
    QSlider::groove:horizontal {{
        height: 3px;
        background: {t['bg_input']};
        border-radius: 1px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t['accent']};
    }}
    QSlider::handle:horizontal {{
        background: {t['fg']};
        width: 10px;
        margin: -5px 0;
        border-radius: 5px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {t['accent']};
    }}

    /* --- Progress / status --------------------------------------------- */
    QProgressBar {{
        background: {t['bg_input']};
        border: none;
        border-radius: 2px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {t['accent']};
        border-radius: 2px;
    }}
    QStatusBar {{
        background: {t['bg_status']};
        color: {t['fg_muted']};
        border-top: 1px solid {t['border']};
    }}
    QStatusBar::item {{ border: none; }}
    #StatusText {{ color: {t['fg_muted']}; padding-left: 8px; }}

    /* --- Content toolbar ------------------------------------------------ */
    #EditorToolbar {{
        background: {t['bg']};
        border-bottom: 1px solid {t['border']};
    }}

    /* --- Preview -------------------------------------------------------- */
    #PreviewStage {{
        background: {t['bg']};
    }}
    #PreviewImage {{
        background: transparent;
    }}

    /* --- Lists (setup dialog) ------------------------------------------ */
    QListWidget {{
        background: {t['bg_side']};
        border: 1px solid {t['border']};
        outline: none;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-bottom: 1px solid {t['border']};
    }}
    QListWidget::item:selected {{
        background: {t['bg_active']};
    }}

    QGroupBox {{
        border: 1px solid {t['border']};
        border-radius: 3px;
        margin-top: 12px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {t['fg_muted']};
    }}
    """


def apply(app) -> None:
    """Apply the base palette and stylesheet to a QApplication."""
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(TOKENS["bg"]))
    palette.setColor(palette.ColorRole.WindowText, QColor(TOKENS["fg"]))
    palette.setColor(palette.ColorRole.Base, QColor(TOKENS["bg_input"]))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(TOKENS["bg_card"]))
    palette.setColor(palette.ColorRole.Text, QColor(TOKENS["fg"]))
    palette.setColor(palette.ColorRole.ButtonText, QColor(TOKENS["fg"]))
    palette.setColor(palette.ColorRole.Highlight, QColor(TOKENS["accent"]))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(TOKENS["accent_fg"]))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())
