"""Screen-input driver for Pyaint (the ``Painter`` seam).

This module isolates every app-specific *action* (clicking swatches, pressing
modifiers, executing a stroke, choosing a colour) from the app-agnostic
*planner* in ``bot.py``. Colours are selected from the sampled palette; the
driver no longer supports arbitrary custom colours.

The ``Painter`` talks to the bot through a duck-typed reference (no import of
``bot`` here) to avoid a circular dependency.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, Sequence, Tuple

import pyautogui

from pyaint.log import log

_MOUSEEVENTF_MOVE = 0x0001
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_ABSOLUTE = 0x8000


def _send_input_mouse(flags: int, x: int = 0, y: int = 0) -> bool:
    """Inject one mouse event via ``SendInput``. Returns True if accepted.

    ``mouse_event`` (what pyautogui uses) is the legacy path; ``SendInput`` is
    the modern one and is accepted by more applications for button
    transitions. When ``flags`` includes ``MOUSEEVENTF_ABSOLUTE``, ``x, y``
    must already be normalised to 0..65535.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        class _INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

        INPUT_MOUSE = 0
        payload = _INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(x, y, 0, flags, 0, None))
        sent = ctypes.windll.user32.SendInput(
            1, ctypes.byref(payload), ctypes.sizeof(payload)
        )
        return sent == 1
    except Exception:
        return False


def _focus_window_at(x: int, y: int) -> bool:
    """Bring the top-level window at ``(x, y)`` to the foreground (Windows).

    Clicking an inactive window only activates it on Windows; the click is
    eaten. That silently drops the first stroke of a drawing, so the target is
    focused explicitly before any synthetic input. Returns True if a focus
    attempt was made.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [POINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.AttachThreadInput.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.BOOL,
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        hwnd = user32.WindowFromPoint(POINT(int(x), int(y)))
        if not hwnd:
            return False
        root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
        if root:
            hwnd = root
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

        if user32.GetForegroundWindow() != hwnd:
            # Foreground lock: briefly attach to the current foreground thread
            # so SetForegroundWindow is permitted, then detach.
            foreground = user32.GetForegroundWindow()
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            current_thread = kernel32.GetCurrentThreadId()
            fg_thread = (
                user32.GetWindowThreadProcessId(foreground, None)
                if foreground
                else 0
            )
            attached = []
            for thread in (fg_thread, target_thread):
                if thread and thread != current_thread:
                    if user32.AttachThreadInput(current_thread, thread, True):
                        attached.append(thread)
            user32.SetForegroundWindow(hwnd)
            for thread in attached:
                user32.AttachThreadInput(current_thread, thread, False)
        return bool(user32.GetForegroundWindow() == hwnd)
    except Exception:
        return False


class _PaletteStrategy:
    name = "palette"

    def __init__(self, painter: "ScreenPainter") -> None:
        self.painter = painter

    def can_handle(self, target: Tuple[int, int, int]) -> bool:
        palette = self.painter.bot._palette
        return palette is not None and target in palette.colors

    def select(self, target: Tuple[int, int, int]) -> None:
        x, y = self.painter.bot._palette.colors_pos[target]
        self.painter.click_swatch(x, y)


class ColorSelectionChain:
    """Colour selection from the sampled palette.

    ``resolve`` decides whether a colour is selectable (no input performed);
    ``apply`` clicks the swatch. Colours absent from the palette are skipped.
    """

    PALETTE = "palette"
    NONE = "none"

    def __init__(self, painter: "ScreenPainter") -> None:
        self.painter = painter
        self.palette = _PaletteStrategy(painter)

    def resolve(self, target: Tuple[int, int, int]) -> str:
        if self.palette.can_handle(target):
            return self.PALETTE
        return self.NONE

    def apply(self, target: Tuple[int, int, int]) -> str:
        source = self.resolve(target)
        if source == self.PALETTE:
            self.palette.select(target)
        return source


class ScreenPainter:
    """Drives a painting application through synthetic screen input."""

    MODIFIER_KEYS: Sequence[Tuple[str, str]] = (
        ("ctrl", "ctrl"),
        ("alt", "alt"),
        ("shift", "shift"),
    )

    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.color_chain = ColorSelectionChain(self)

    # -- window focus ----------------------------------------------------
    def focus_target(self, canvas) -> bool:
        """Bring the window under ``canvas`` to the foreground before drawing.

        Without this the first click on an inactive window only activates it
        and is consumed, so the first stroke draws nothing while every later
        stroke works. Returns True if a focus attempt was made.
        """
        if not canvas:
            return False
        x, y, w, h = canvas
        return _focus_window_at(x + w // 2, y + h // 2)

    # -- colour selection ------------------------------------------------
    def resolve_color_source(self, target: Tuple[int, int, int]) -> str:
        return self.color_chain.resolve(target)

    def select_color(self, target: Tuple[int, int, int]) -> str:
        return self.color_chain.apply(target)

    def click_swatch(self, x: int, y: int) -> None:
        """Click a palette swatch, honouring MSPaint double-click mode."""
        bot = self.bot
        if bot.mspaint_mode.get("enabled", False):
            pyautogui.click((x, y))
            delay = bot.mspaint_mode.get("delay", 0.5)
            log.info(f"[MSPaintMode] Waiting {delay} seconds between double-click...")
            time.sleep(delay)
            pyautogui.click((x, y))
            log.info(f"[MSPaintMode] Double-click completed at {(x, y)}")
        else:
            pyautogui.click((x, y))
        wait = bot.color_button.get("delay", 0.1)
        log.debug(f"[DEBUG] Waiting {wait} seconds after swatch click...")
        time.sleep(wait)

    # -- modifier click helpers -----------------------------------------
    def _release_all_modifiers(self, label=None) -> None:
        """Brute-force release ctrl/alt/shift (backup for error paths)."""
        for key in ("shift", "alt", "ctrl"):
            try:
                pyautogui.keyUp(key)
                time.sleep(0.05)
            except Exception:
                pass
        if label:
            log.info(f"[{label}] force-released all modifiers as backup")

    def _click_with_modifiers(
        self,
        coords: Tuple[int, int],
        modifiers: Dict[str, bool],
        label: str,
    ) -> None:
        """Press ``modifiers``, click ``coords``, then release everything."""
        x, y = coords
        modifiers = modifiers or {}
        pressed = []

        for mod_key, pygui_key in self.MODIFIER_KEYS:
            if modifiers.get(mod_key):
                pyautogui.keyDown(pygui_key)
                pressed.append(pygui_key)
                log.info(f"[{label}] pressed modifier: {pygui_key}")

        log.info(f"[{label}] performing mouseDown at {(x, y)}")
        pyautogui.mouseDown(x, y, button="left")
        time.sleep(0.08)
        pyautogui.mouseUp(x, y, button="left")
        log.info(f"[{label}] mouse click performed at {(x, y)}")

        for pygui_key in reversed(pressed):
            pyautogui.keyUp(pygui_key)
            log.info(f"[{label}] released modifier: {pygui_key}")
            time.sleep(0.05)

        self._release_all_modifiers(label)
        time.sleep(0.1)

    # -- app actions -----------------------------------------------------
    def new_layer(self) -> None:
        """Create a new layer (if enabled), with modifiers held during the click."""
        nl = self.bot.new_layer
        if not (nl.get("enabled") and nl.get("coords")):
            return
        try:
            nx, ny = nl["coords"]
            log.info(f"[NewLayer] attempting click at {(nx, ny)} with mods={nl.get('modifiers')}")
            self._click_with_modifiers((nx, ny), nl.get("modifiers", {}), "NewLayer")
            time.sleep(0.75)
            log.info("[NewLayer] waiting 0.75 seconds before painting...")
            time.sleep(0.75)
        except Exception as e:
            log.info(f"[NewLayer] Error during new layer creation: {e}")
            self._release_all_modifiers()

    def color_button(self) -> None:
        """Click the colour button (if enabled) before palette selection."""
        cb = self.bot.color_button
        if not (cb.get("enabled") and cb.get("coords")):
            return
        try:
            cx, cy = cb["coords"]
            log.info(f"[ColorButton] attempting click at {(cx, cy)} with mods={cb.get('modifiers')}, delay={cb.get('delay')}")
            self._click_with_modifiers((cx, cy), cb.get("modifiers", {}), "ColorButton")
            delay = cb.get("delay", 0.1)
            log.info(f"[ColorButton] waiting {delay} seconds before palette selection...")
            time.sleep(delay)
        except Exception as e:
            log.info(f"[ColorButton] Error during color button click: {e}")
            self._release_all_modifiers()

    def color_button_okay(self) -> None:
        """Click the colour dialog's OK button (if enabled) after selection."""
        cbo = self.bot.color_button_okay
        if not (cbo.get("enabled") and cbo.get("coords")):
            return
        try:
            cx, cy = cbo["coords"]
            log.info(f"[ColorButtonOkay] attempting click at {(cx, cy)} with mods={cbo.get('modifiers')}")
            self._click_with_modifiers((cx, cy), cbo.get("modifiers", {}), "ColorButtonOkay")
            delay = cbo.get("delay", 0.1)
            log.info(f"[ColorButtonOkay] waiting {delay} seconds before starting to draw...")
            time.sleep(delay)
        except Exception as e:
            log.info(f"[ColorButtonOkay] Error during color button okay click: {e}")
            self._release_all_modifiers()

    # -- stroke execution ------------------------------------------------
    def _left_is_down(self) -> bool:
        """Whether Windows currently reports the left mouse button held."""
        if sys.platform == "win32":
            try:
                import ctypes

                return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
            except Exception:
                return False
        # Non-Windows: cannot read button state, so trust the synthetic press.
        return True

    def press_left(self, attempts: int = 5) -> None:
        """Press the left button and confirm it actually went down.

        The first synthetic press after a UI interaction (palette click, dialog
        OK) can be swallowed by the target app, producing a stroke that draws
        nothing. SendInput is preferred over pyautogui's legacy mouse_event,
        and the press is re-sent until the OS reports the button held.
        """
        if not _send_input_mouse(_MOUSEEVENTF_LEFTDOWN):
            pyautogui.mouseDown(button="left")
        if self._left_is_down():
            return
        for _ in range(max(1, attempts) - 1):
            time.sleep(0.02)
            if not _send_input_mouse(_MOUSEEVENTF_LEFTDOWN):
                pyautogui.mouseDown(button="left")
            if self._left_is_down():
                return
        log.warning("[Press] left button not confirmed down after retries")

    def release_left(self) -> None:
        """Release the left button."""
        if not _send_input_mouse(_MOUSEEVENTF_LEFTUP):
            pyautogui.mouseUp()

    def _drag_move(self, x: int, y: int) -> None:
        """Move the cursor while a button is held so apps register a drag.

        ``pyautogui.moveTo`` uses ``SetCursorPos`` on Windows, which GDI apps
        such as MS Paint do *not* treat as a drag: they receive button-down and
        button-up but not the connecting motion, so only a dot is painted.
        Sending an explicit ``MOUSEEVENTF_MOVE`` makes the app receive
        ``WM_MOUSEMOVE`` with the button bit set, which actually paints.
        Falls back to ``pyautogui.moveTo`` off Windows or if the call fails.
        """
        if sys.platform == "win32":
            try:
                import ctypes

                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
                if width and height:
                    absolute = 0x8000
                    move = 0x0001
                    cx = 65536 * int(x) // width + 1
                    cy = 65536 * int(y) // height + 1
                    if _send_input_mouse(move | absolute, cx, cy):
                        return
                    user32.mouse_event(
                        move | absolute,
                        ctypes.c_long(cx),
                        ctypes.c_long(cy),
                        0,
                        0,
                    )
                    return
            except Exception:
                pass
        pyautogui.moveTo(x, y)

    def execute_path(
        self,
        points: Sequence[Tuple[int, int]],
        speed: float = 1500.0,
        frame_interval: float = 1.0 / 60.0,
        settle: float = 0.03,
        prime: bool = False,
    ) -> None:
        """Draw a polyline as one continuous, human-paced drag.

        The button is pressed once, the cursor is walked along the path with at
        most one ``moveTo`` per ``frame_interval`` (and always one at every
        vertex, so corners are never skipped), then released once. Few
        down/up events plus a steady move stream is the input shape a human
        produces and that browser apps are built to handle.

        ``speed`` is in pixels per second; ``frame_interval`` caps the event
        rate at ``1 / frame_interval`` Hz. ``settle`` is a short pause after
        the button goes down / before it comes up so a web app can register
        the stroke endpoints.
        """
        pts = [(int(x), int(y)) for x, y in points]
        if not pts:
            return

        # A single point, or a degenerate path: tap once in place.
        if len(pts) == 1 or all(p == pts[0] for p in pts):
            pyautogui.moveTo(*pts[0])
            self.press_left()
            time.sleep(settle)
            self.release_left()
            return

        interval = max(float(frame_interval), 1e-4)
        step = max(float(speed), 1.0) * interval

        # Cumulative distance to each vertex.
        cum = [0.0]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            cum.append(cum[-1] + ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        total = cum[-1]

        # Emit on a fixed distance cadence, but always include every vertex so
        # a fast speed can never cut a corner.
        distances = set(cum)
        if total > 0:
            distances.update(i * step for i in range(int(total / step) + 1))
            distances.add(total)

        def point_at(distance: float) -> Tuple[int, int]:
            edge = 0
            while edge < len(cum) - 2 and cum[edge + 1] < distance:
                edge += 1
            span = cum[edge + 1] - cum[edge]
            t = 0.0 if span <= 0 else (distance - cum[edge]) / span
            (x1, y1), (x2, y2) = pts[edge], pts[edge + 1]
            return int(round(x1 + (x2 - x1) * t)), int(round(y1 + (y2 - y1) * t))

        pyautogui.moveTo(*pts[0])
        # Let the app register the new cursor position before the press.
        time.sleep(min(settle, 0.05))
        if prime:
            # Some apps ignore the first synthetic interaction after a UI
            # change. A throwaway double-click warms up the canvas/tool before
            # the real drag; the dot it may leave sits on the first vertex.
            log.info("[Prime] double-clicking before the first stroke")
            for _ in range(2):
                self.press_left()
                time.sleep(0.05)
                self.release_left()
                time.sleep(0.05)
            pyautogui.moveTo(*pts[0])
            time.sleep(min(settle, 0.05))
        self.press_left()
        time.sleep(max(settle, 0.12) if prime else settle)

        last = time.perf_counter()
        for distance in sorted(distances):
            self._drag_move(*point_at(distance))
            # Hold the cadence even if the move ran long; never sleep a
            # negative amount.
            wait = interval - (time.perf_counter() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.perf_counter()

        time.sleep(settle)
        self.release_left()

    def execute_stroke(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        delay: float,
    ) -> None:
        """Draw one run as a left-button drag, segmented for smoothness."""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < 1:  # Very short line
            pyautogui.moveTo(start_pos)
            pyautogui.dragTo(end_pos[0], end_pos[1], 0, button="left")
            return

        segments = max(2, min(10, int(distance / 10)))
        segment_delay = delay / segments

        pyautogui.moveTo(start_pos)
        self.press_left()

        if self.bot.draw_state.get("was_paused", False):
            log.info("Replaying stroke after pause - ensuring clean result")
            self.bot.draw_state["was_paused"] = False

        for i in range(1, segments + 1):
            t = i / segments
            self._drag_move(start_pos[0] + dx * t, start_pos[1] + dy * t)
            time.sleep(segment_delay)

        self.release_left()

    def execute_test_stroke(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
    ) -> None:
        """Draw one run the simplified way used by ``Bot.test_draw``."""
        distance = (
            (end_pos[0] - start_pos[0]) ** 2 + (end_pos[1] - start_pos[1]) ** 2
        ) ** 0.5
        pyautogui.moveTo(start_pos)
        if distance < 1:  # Very short line
            pyautogui.dragTo(end_pos[0], end_pos[1], 0.2, button="left")
        else:
            pyautogui.dragTo(end_pos[0], end_pos[1], 0.2, button="left")
            time.sleep(0.2)
