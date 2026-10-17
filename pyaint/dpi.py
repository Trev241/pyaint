"""Windows DPI awareness, claimed before any automation library can pin it.

``pyautogui`` and ``pyscreeze`` call ``SetProcessDPIAware()`` at import time.
That pins the process to *system* DPI awareness, and it is a one-way door: Qt
can no longer opt into per-monitor awareness afterwards. A system-aware app is
bitmap-stretched by Windows whenever it sits on a monitor whose scaling differs
from the system DPI. The window keeps its old pixel layout (so text wraps at
the old width and leaves dead space), Qt never receives ``WM_DPICHANGED``, and
screen metrics can keep reporting the scale that was active when the process
started -- including after the user switches displays.

:func:`enable_per_monitor_dpi` is therefore called from ``pyaint/__init__.py``,
before any module imports ``pyautogui``. The later ``SetProcessDPIAware()``
calls fail harmlessly and the process stays per-monitor v2 aware.

Everything here is best-effort and Windows-only; on other platforms it reports
``"unavailable"`` and does nothing.
"""

from __future__ import annotations

import ctypes
import sys

# DPI_AWARENESS_CONTEXT pseudo-handles (Win10 1607+). They are negative values
# cast to a HANDLE, which is why ctypes sees them as ``c_void_p(handle)``.
UNAWARE = -1
SYSTEM_AWARE = -2
PER_MONITOR_AWARE = -3
PER_MONITOR_AWARE_V2 = -4
UNAWARE_GDISCALED = -5

_LEVELS = {
    UNAWARE: "unaware",
    SYSTEM_AWARE: "system",
    PER_MONITOR_AWARE: "per-monitor",
    PER_MONITOR_AWARE_V2: "per-monitor-v2",
    UNAWARE_GDISCALED: "unaware-gdiscaled",
}

# The level claimed (or observed) on the first call, so the answer is stable
# even if a host process changes awareness later.
_claimed = None


def _is_windows() -> bool:
    return sys.platform == "win32"


def _lib(name: str):
    """Return ``ctypes.windll.<name>`` or None when it is unavailable."""
    try:
        return getattr(ctypes.windll, name)
    except (AttributeError, OSError):
        return None


def _signature(function, restype, argtypes) -> None:
    function.restype = restype
    function.argtypes = argtypes


def enable_per_monitor_dpi() -> str:
    """Claim per-monitor DPI awareness for this process; idempotent.

    Call this before ``pyautogui`` (or Qt) is imported. Returns the resulting
    awareness level, e.g. ``"per-monitor-v2"``. When another host already set
    awareness, the highest reachable level is used and the current one is
    reported instead.
    """
    global _claimed
    if _claimed is not None:
        return _claimed
    if not _is_windows():
        _claimed = "unavailable"
        return _claimed

    user32 = _lib("user32")

    # Windows 10 1703+: per-monitor v2. This is what Qt itself asks for, and
    # it makes GetCursorPos, screen metrics and screenshots share one physical
    # pixel space that follows the monitor.
    if user32 is not None:
        set_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
        if set_context is not None:
            _signature(set_context, ctypes.c_bool, [ctypes.c_void_p])
            if set_context(ctypes.c_void_p(PER_MONITOR_AWARE_V2)):
                _claimed = _LEVELS[PER_MONITOR_AWARE_V2]
                return _claimed

    # Windows 8.1+: per-monitor v1.
    shcore = _lib("shcore")
    if shcore is not None:
        set_awareness = getattr(shcore, "SetProcessDpiAwareness", None)
        if set_awareness is not None:
            _signature(set_awareness, ctypes.c_long, [ctypes.c_int])
            # PROCESS_PER_MONITOR_DPI_AWARE == 2; S_OK == 0.
            if set_awareness(2) == 0:
                _claimed = _LEVELS[PER_MONITOR_AWARE]
                return _claimed

    # Windows Vista+: system awareness. Still vastly better than unaware.
    if user32 is not None:
        set_legacy = getattr(user32, "SetProcessDPIAware", None)
        if set_legacy is not None:
            _signature(set_legacy, ctypes.c_bool, [])
            if set_legacy():
                _claimed = _LEVELS[SYSTEM_AWARE]
                return _claimed

    # Awareness was already claimed (e.g. pyautogui was imported first, or an
    # embedding host set it). Report what the process actually has.
    _claimed = current_awareness()
    return _claimed


def current_awareness() -> str:
    """Return the process's DPI awareness as a short name."""
    if not _is_windows():
        return "unavailable"

    user32 = _lib("user32")
    if user32 is not None:
        get_context = getattr(user32, "GetThreadDpiAwarenessContext", None)
        equal = getattr(user32, "AreDpiAwarenessContextsEqual", None)
        if get_context is not None and equal is not None:
            _signature(get_context, ctypes.c_void_p, [])
            _signature(equal, ctypes.c_bool, [ctypes.c_void_p, ctypes.c_void_p])
            context = get_context()
            for handle, name in _LEVELS.items():
                if equal(context, ctypes.c_void_p(handle)):
                    return name

    shcore = _lib("shcore")
    if shcore is not None:
        get_awareness = getattr(shcore, "GetProcessDpiAwareness", None)
        if get_awareness is not None:
            _signature(
                get_awareness,
                ctypes.c_long,
                [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)],
            )
            value = ctypes.c_int()
            if get_awareness(None, ctypes.byref(value)) == 0:
                return {0: "unaware", 1: "system", 2: "per-monitor"}.get(
                    value.value, "unknown"
                )

    if user32 is not None:
        is_aware = getattr(user32, "IsProcessDPIAware", None)
        if is_aware is not None:
            _signature(is_aware, ctypes.c_bool, [])
            return _LEVELS[SYSTEM_AWARE] if is_aware() else _LEVELS[UNAWARE]

    return "unknown"
