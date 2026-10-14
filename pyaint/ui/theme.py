"""Theming for the PySide6 UI — "Studio Warm".

Two flat token sets (warm-paper light, warm-charcoal dark) plus an ``auto`` mode
that follows the OS colour scheme. Surfaces are warm, never gray; one clay
accent carries every highlight. Everything visual (surfaces, text, accent)
comes from these tokens, so switching themes is a single re-apply.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

DARK = {
    "bg": "#1E1B19",
    "bg_activity": "#171513",
    "bg_side": "#171513",
    "bg_status": "#171513",
    "bg_input": "#2E2926",
    "bg_hover": "#2A2623",
    "bg_active": "#332E2A",
    "bg_card": "#262220",
    "border": "#3A342F",
    "border_input": "#4A423C",
    "fg": "#ECE5DC",
    "fg_muted": "#B3A79A",
    "fg_dim": "#948A7E",
    "accent": "#E07856",
    "accent_hover": "#D66B49",
    "accent_pressed": "#C55F3F",
    "accent_fg": "#1E1B19",
    "danger": "#E07068",
    "success": "#7FB07A",
    "warning": "#E0B84E",
    "notice_info_bg": "rgba(224, 120, 86, 0.16)",
    "notice_success_bg": "rgba(127, 176, 122, 0.16)",
    "notice_warning_bg": "rgba(224, 184, 78, 0.16)",
    "notice_error_bg": "rgba(224, 112, 104, 0.16)",
    "scrollbar": "rgba(150, 140, 128, 0.40)",
    "scrollbar_hover": "rgba(170, 160, 148, 0.70)",
}

LIGHT = {
    "bg": "#FAF7F2",
    "bg_activity": "#F2ECE4",
    "bg_side": "#F2ECE4",
    "bg_status": "#F2ECE4",
    "bg_input": "#FFFFFF",
    "bg_hover": "#EDE6DC",
    "bg_active": "#E4DACD",
    "bg_card": "#FFFDFA",
    "border": "#E6DED2",
    "border_input": "#D9CFC1",
    "fg": "#2B2622",
    "fg_muted": "#6B6157",
    "fg_dim": "#736A5F",
    "accent": "#B8542F",
    "accent_hover": "#A94A2B",
    "accent_pressed": "#964124",
    "accent_fg": "#FFFFFF",
    "danger": "#B23A34",
    "success": "#4F7A4A",
    "warning": "#C58A1E",
    "notice_info_bg": "rgba(184, 84, 47, 0.10)",
    "notice_success_bg": "rgba(79, 122, 74, 0.12)",
    "notice_warning_bg": "rgba(197, 138, 30, 0.14)",
    "notice_error_bg": "rgba(178, 58, 52, 0.12)",
    "scrollbar": "rgba(120, 105, 92, 0.35)",
    "scrollbar_hover": "rgba(120, 105, 92, 0.60)",
}

THEME_MODES = ("auto", "dark", "light")
THEME_LABELS = {"auto": "Auto (follow system)", "dark": "Dark", "light": "Light"}

# Backwards-compatible default (the dark set). Prefer ``resolve_tokens``.
TOKENS = DARK


def system_scheme() -> str:
    """Return ``"dark"`` or ``"light"`` for the current OS colour scheme.

    Unknown schemes fall back to dark, matching the app's historical look.
    """
    try:
        from PySide6.QtGui import QGuiApplication

        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
    except Exception:
        pass
    return "dark"


def resolve_tokens(mode: str = "auto") -> dict:
    """Return the token set for a mode (``auto`` | ``dark`` | ``light``)."""
    if mode == "light":
        return LIGHT
    if mode == "dark":
        return DARK
    return LIGHT if system_scheme() == "light" else DARK


def stylesheet(tokens: dict | None = None) -> str:
    """Return the application-wide Qt stylesheet for ``tokens``."""
    t = tokens or TOKENS
    return f"""
    * {{
        font-family: "Segoe UI", "SF Pro Text", "Ubuntu", sans-serif;
        font-size: 13px;
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
        padding: 10px 12px 4px 12px;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    /* --- Scrollbars ----------------------------------------------------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scrollbar']};
        min-height: 28px;
        border-radius: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: none;
        border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['scrollbar']};
        min-width: 28px;
        border-radius: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {t['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        background: none;
        border: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    QAbstractScrollArea::corner {{
        background: transparent;
        border: none;
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
        padding: 12px 12px 2px 12px;
    }}
    #SectionHint {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 0 12px 6px 12px;
    }}
    #CollapsibleHeader {{
        background: transparent;
        border: none;
        color: {t['fg_muted']};
        font-size: 11px;
        font-weight: 700;
        padding: 12px 10px 2px 8px;
        text-align: left;
    }}
    #CollapsibleHeader:hover {{ color: {t['fg']}; }}

    /* --- Readiness strip ------------------------------------------------ */
    #ReadinessStrip {{
        background: {t['bg_side']};
        border-bottom: 1px solid {t['border']};
    }}
    #ReadyChip {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 2px 4px;
    }}
    #ReadyChip[done="true"] {{
        color: {t['success']};
        font-weight: 600;
    }}
    #ReadyChip[state="missing"] {{
        color: {t['warning']};
        font-weight: 600;
    }}
    #ReadySep {{ color: {t['fg_dim']}; }}
    #FieldLabel {{
        color: {t['fg_muted']};
        font-size: 11px;
    }}
    #FieldHint {{
        color: {t['fg_muted']};
        font-size: 11px;
    }}
    #FieldValue {{
        color: {t['fg']};
        font-size: 11px;
        font-weight: 600;
    }}
    #FieldBand {{
        color: {t['accent']};
        font-size: 11px;
        font-weight: 600;
    }}
    #FamilyLabel {{
        color: {t['fg_muted']};
        font-size: 11px;
        font-weight: 600;
        padding: 6px 0 1px 2px;
    }}
    QRadioButton#ModeRailItem {{
        color: {t['fg_muted']};
        padding: 6px 8px;
        border-radius: 8px;
        spacing: 8px;
    }}
    QRadioButton#ModeRailItem:hover {{
        background: {t['bg_hover']};
        color: {t['fg']};
    }}
    QRadioButton#ModeRailItem:checked {{
        color: {t['fg']};
        font-weight: 600;
    }}
    QRadioButton#ModeRailItem::indicator {{
        width: 13px;
        height: 13px;
        border-radius: 7px;
        border: 2px solid {t['border_input']};
        background: transparent;
    }}
    QRadioButton#ModeRailItem::indicator:checked {{
        border: 2px solid {t['accent']};
        background: {t['accent']};
    }}

    /* --- Dialog text ---------------------------------------------------- */
    #DialogTitle {{
        font-size: 18px;
        font-weight: 600;
        color: {t['fg']};
    }}
    #DialogHint {{
        color: {t['fg_muted']};
    }}
    #DialogStatus {{
        color: {t['success']};
    }}
    #CountdownBanner {{
        background: {t['bg_card']};
        border-bottom: 1px solid {t['border']};
        border-left: 3px solid {t['accent']};
    }}
    #CountdownTitle {{
        color: {t['fg']};
        font-size: 13px;
        font-weight: 600;
    }}
    #CountdownHint {{
        color: {t['fg_muted']};
        font-size: 11px;
    }}

    /* --- Persistent notice banner -------------------------------------- */
    #NoticeBanner {{
        background: {t['notice_info_bg']};
        border-bottom: 1px solid {t['border']};
        border-left: 4px solid {t['accent']};
    }}
    #NoticeBanner[severity="success"] {{
        background: {t['notice_success_bg']};
        border-left: 4px solid {t['success']};
    }}
    #NoticeBanner[severity="warning"] {{
        background: {t['notice_warning_bg']};
        border-left: 4px solid {t['warning']};
    }}
    #NoticeBanner[severity="error"] {{
        background: {t['notice_error_bg']};
        border-left: 4px solid {t['danger']};
    }}
    #NoticeIcon {{ color: {t['accent']}; font-weight: 700; }}
    #NoticeBanner[severity="success"] #NoticeIcon {{ color: {t['success']}; }}
    #NoticeBanner[severity="warning"] #NoticeIcon {{ color: {t['warning']}; }}
    #NoticeBanner[severity="error"]   #NoticeIcon {{ color: {t['danger']}; }}
    #NoticeText {{ color: {t['fg']}; font-weight: 600; }}
    #NoticeAction {{ padding: 3px 10px; }}
    #NoticeClose {{
        background: transparent;
        border: none;
        color: {t['fg_muted']};
        padding: 2px 6px;
    }}
    #NoticeClose:hover {{ color: {t['fg']}; }}

    /* --- Top bar / target switcher ------------------------------------- */
    #TopBar {{
        background: {t['bg_side']};
        border-bottom: 1px solid {t['border']};
    }}
    #TopBarLabel {{ color: {t['fg_muted']}; font-size: 11px; }}
    #EnvChip {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 2px 10px;
        border: 1px solid {t['border_input']};
        border-radius: 10px;
    }}
    #EnvChip[state="ready"] {{ color: {t['success']}; border-color: {t['success']}; }}
    #EnvChip[state="partial"] {{ color: {t['warning']}; border-color: {t['warning']}; }}

    /* --- Action bar ----------------------------------------------------- */
    #ActionBar {{
        background: {t['bg_side']};
        border-top: 1px solid {t['border']};
    }}
    #ReadinessStripInline {{ background: transparent; border: none; }}
    #ReadinessStripInline[ready="false"] {{
        background: {t['notice_warning_bg']};
        border-top: 1px solid {t['warning']};
    }}
    #FixButton {{ color: {t['warning']}; border-color: {t['warning']}; }}

    /* --- Overlay severity ---------------------------------------------- */
    #ProgressOverlay[severity="error"] {{ border: 1px solid {t['danger']}; }}

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
        padding: 3px 0;
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
        background: {t['border_input']};
        border-radius: 1px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t['accent']};
    }}
    QSlider::handle:horizontal {{
        background: {t['fg']};
        width: 10px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {t['accent']};
    }}

    /* --- Progress / status --------------------------------------------- */
    QProgressBar {{
        background: {t['border_input']};
        border: none;
        border-radius: 2px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {t['accent']};
        border-radius: 2px;
    }}
    /* --- Content toolbar ------------------------------------------------ */
    #EditorToolbar {{
        background: {t['bg']};
        border-bottom: 1px solid {t['border']};
    }}

    /* --- Editor tabs ---------------------------------------------------- */
    QTabWidget::pane {{
        border: none;
        background: {t['bg']};
    }}
    QTabBar {{
        background: {t['bg_activity']};
        qproperty-drawBase: 0;
    }}
    QTabBar::tab {{
        background: {t['bg_activity']};
        color: {t['fg_muted']};
        padding: 6px 14px;
        border: none;
        border-right: 1px solid {t['border']};
        border-top: 1px solid transparent;
    }}
    QTabBar::tab:hover {{
        background: {t['bg_hover']};
        color: {t['fg']};
    }}
    QTabBar::tab:selected {{
        background: {t['bg']};
        color: {t['fg']};
        border-top: 1px solid {t['accent']};
    }}

    /* --- Preview -------------------------------------------------------- */
    #ImagePanel {{
        background: {t['bg']};
    }}
    #ImageHeader {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 8px;
    }}
    #ImageTitle {{
        color: {t['fg']};
        font-size: 11px;
        font-weight: 700;
    }}
    #SourceLabel {{
        color: {t['fg_dim']};
        font-size: 11px;
    }}
    #ImageMeta {{
        color: {t['fg_muted']};
        font-size: 11px;
    }}
    #SearchField {{
        background: {t['bg_input']};
        border: 1px solid {t['border_input']};
        border-radius: 8px;
        padding: 6px 8px;
        min-height: 18px;
    }}
    #SearchField:focus {{
        border: 1px solid {t['accent']};
    }}
    #LoadButton {{
        padding: 6px 16px;
        border-radius: 8px;
        font-weight: 600;
    }}
    #PreviewStage {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 8px;
    }}
    #PreviewImage {{
        background: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
    }}
    #PreviewImage[dragActive="true"] {{
        background: {t['bg_card']};
        border: 2px dashed {t['accent']};
        border-radius: 8px;
    }}
    #StageHeader {{
        color: {t['fg_muted']};
        font-size: 11px;
        font-weight: 700;
        padding: 0 2px;
    }}
    #StageMeta {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 0 2px;
    }}
    #ViewToggleGroup {{
        background: {t['bg_input']};
        border: 1px solid {t['border_input']};
        border-radius: 8px;
    }}
    QPushButton#ViewToggle {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 3px 10px;
        color: {t['fg_dim']};
        font-size: 11px;
    }}
    QPushButton#ViewToggle:hover {{
        color: {t['fg']};
    }}
    QPushButton#ViewToggle:checked {{
        background: {t['bg_active']};
        color: {t['fg']};
        font-weight: 600;
    }}
    #SegmentedGroup {{
        background: {t['bg_input']};
        border: 1px solid {t['border_input']};
        border-radius: 8px;
    }}
    QPushButton#SegmentButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px 8px;
        color: {t['fg_dim']};
        font-size: 11px;
    }}
    QPushButton#SegmentButton:hover {{
        color: {t['fg']};
    }}
    QPushButton#SegmentButton:checked {{
        background: {t['accent']};
        color: {t['accent_fg']};
        font-weight: 600;
    }}
    #PresetTagline {{
        color: {t['fg']};
        font-size: 12px;
        font-weight: 600;
        padding: 4px 2px 0 2px;
    }}
    #PresetHint {{
        color: {t['fg_muted']};
        font-size: 11px;
        padding: 0 2px 2px 2px;
    }}
    #PaneLabel {{
        color: {t['fg_dim']};
        font-size: 10px;
        font-weight: 700;
        padding: 0 2px;
    }}
    #ModeHint {{
        color: {t['fg_muted']};
        font-size: 11px;
        padding: 0 2px;
    }}
    #StageHint {{
        color: {t['fg_dim']};
        font-size: 11px;
        padding: 0 2px;
    }}

    /* --- Search gallery ------------------------------------------------- */
    #Gallery {{
        background: {t['bg']};
        border: none;
    }}
    #GalleryContainer {{ background: {t['bg']}; }}
    #GalleryTile {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 8px;
    }}
    #GalleryTile:hover {{ border: 1px solid {t['accent']}; }}
    #GalleryImage {{ background: {t['bg_input']}; }}

    /* --- Floating progress overlay -------------------------------------- */
    #ProgressOverlay {{
        background: {t['bg_card']};
        border: 1px solid {t['border_input']};
        border-radius: 8px;
    }}
    #OverlayText {{
        color: {t['fg']};
        font-weight: 600;
    }}
    #OverlayHint {{
        color: {t['fg_dim']};
        font-size: 11px;
    }}

    /* --- Detection review overlay --------------------------------------- */
    #DetectionCard {{
        background: {t['bg_card']};
        border: 1px solid {t['border_input']};
        border-radius: 8px;
    }}
    #DetectionTitle {{
        color: {t['fg']};
        font-size: 14px;
        font-weight: 600;
    }}
    #DetectionSummary {{
        color: {t['fg_muted']};
        font-size: 12px;
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
        border-radius: 8px;
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


def apply(app, tokens: dict | None = None) -> None:
    """Apply the base palette and stylesheet to a QApplication."""
    t = tokens or resolve_tokens("auto")
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(t["bg"]))
    palette.setColor(palette.ColorRole.WindowText, QColor(t["fg"]))
    palette.setColor(palette.ColorRole.Base, QColor(t["bg_input"]))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(t["bg_card"]))
    palette.setColor(palette.ColorRole.Text, QColor(t["fg"]))
    palette.setColor(palette.ColorRole.Button, QColor(t["bg_input"]))
    palette.setColor(palette.ColorRole.ButtonText, QColor(t["fg"]))
    palette.setColor(palette.ColorRole.Highlight, QColor(t["accent"]))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(t["accent_fg"]))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet(t))
