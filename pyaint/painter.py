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
                    move = 0x0001
                    absolute = 0x8000
                    cx = 65536 * int(x) // width + 1
                    cy = 65536 * int(y) // height + 1
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
            pyautogui.mouseDown(button="left")
            time.sleep(settle)
            pyautogui.mouseUp()
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
        pyautogui.mouseDown(button="left")
        time.sleep(settle)

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
        pyautogui.mouseUp()

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
        pyautogui.mouseDown(button="left")

        if self.bot.draw_state.get("was_paused", False):
            log.info("Replaying stroke after pause - ensuring clean result")
            self.bot.draw_state["was_paused"] = False

        for i in range(1, segments + 1):
            t = i / segments
            self._drag_move(start_pos[0] + dx * t, start_pos[1] + dy * t)
            time.sleep(segment_delay)

        pyautogui.mouseUp()

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
