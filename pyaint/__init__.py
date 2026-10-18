"""Pyaint — transform images into automated brush strokes.

The package groups the pure planner (:mod:`pyaint.planner`), the drawing engine
and executor (:mod:`pyaint.bot`), the taught-environment profile, the
screen-input driver, target recipes/locators and the PySide6 UI
(:mod:`pyaint.ui`).
"""

# Claim per-monitor DPI awareness before any submodule imports pyautogui.
# pyautogui/pyscreeze pin the process to *system* awareness on import, which
# Qt cannot upgrade afterwards; the window would then stay stretched at the old
# scale after the user changes monitors or Windows scaling. See pyaint/dpi.py.
from . import dpi as _dpi

__version__ = "2026.1.1"

_dpi.enable_per_monitor_dpi()
