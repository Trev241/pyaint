"""Screen-input driver for Pyaint (the ``Painter`` seam).

This module isolates every app-specific *action* (clicking swatches, pressing
modifiers, executing a stroke, choosing a colour) from the app-agnostic
*planner* in ``bot.py``.

Phase 0 is a **behaviour-preserving extraction**: the methods here contain the
same operations, in the same order, that previously lived inline in
``Bot.draw`` / ``Bot.test_draw`` / ``Bot._select_color``. No drawing semantics
change; the win is that the planner no longer hard-codes screen input, so a
future browser/native transport can implement the same surface.

The ``Painter`` talks to the bot through a duck-typed reference (no import of
``bot`` here) to avoid a circular dependency.
"""

from __future__ import annotations
from pyaint.log import log

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import pyautogui

from pyaint.errors import NoCustomColorsError
from pyaint.profile import Profile


@dataclass
class Capabilities:
    """What the active target/driver can currently do.

    Derived from the taught :class:`~pyaint.profile.Profile` so the planner can
    eventually branch on *capability* rather than on app identity. Phase 0 only
    populates it; behaviour is still driven by the same checks as before.
    """

    palette: bool = False
    custom_colors: bool = False
    calibration: bool = False
    new_layer: bool = False
    color_button: bool = False
    color_button_okay: bool = False
    mspaint_double_click: bool = False

    @classmethod
    def from_bot(cls, bot: Any) -> "Capabilities":
        profile = bot.profile

        def enabled(name: str) -> bool:
            entry = profile.get(name, {})
            return bool(entry.get("enabled") and entry.get("coords"))

        return cls(
            palette=bot._palette is not None,
            custom_colors=bot._custom_colors is not None,
            calibration=bool(bot.color_calibration_map),
            new_layer=enabled("New Layer"),
            color_button=enabled("Color Button"),
            color_button_okay=enabled("Color Button Okay"),
            mspaint_double_click=bool(profile.mspaint_mode.get("enabled")),
        )


# ---------------------------------------------------------------------------
# Colour selection strategies
# ---------------------------------------------------------------------------
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


class _CalibratedStrategy:
    name = "calibrated"

    def __init__(self, painter: "ScreenPainter") -> None:
        self.painter = painter

    def can_handle(self, target: Tuple[int, int, int]) -> bool:
        return bool(self.painter.bot.get_calibrated_color_position(target, tolerance=20))

    def select(self, target: Tuple[int, int, int]) -> None:
        # Resolved again on purpose: this mirrors the pre-refactor behaviour
        # (``_color_source`` probed, then ``_select_color`` looked up once more).
        pos = self.painter.bot.get_calibrated_color_position(target, tolerance=20)
        if pos:
            self.painter.click_swatch(pos[0], pos[1])


class _KeyboardStrategy:
    name = "keyboard"

    def __init__(self, painter: "ScreenPainter") -> None:
        self.painter = painter

    def can_handle(self, target: Tuple[int, int, int]) -> bool:
        bot = self.painter.bot
        return (
            not os.path.exists("color_calibration.json")
            and bot._custom_colors is not None
        )

    def select(self, target: Tuple[int, int, int]) -> None:
        self.painter.enter_rgb_keyboard(target)


class ColorSelectionChain:
    """Ordered colour-selection strategies.

    ``resolve`` decides *how* a colour should be selected (no input performed);
    ``apply`` performs it and returns the chosen source. The semantics match the
    historical ``Bot._color_source`` / ``Bot._select_color`` exactly.
    """

    PALETTE = "palette"
    CALIBRATED = "calibrated"
    KEYBOARD = "keyboard"
    NONE = "none"

    def __init__(self, painter: "ScreenPainter") -> None:
        self.painter = painter
        self.palette = _PaletteStrategy(painter)
        self.calibrated = _CalibratedStrategy(painter)
        self.keyboard = _KeyboardStrategy(painter)

    def resolve(self, target: Tuple[int, int, int], force_custom: bool = False) -> str:
        selection = self.painter.bot.profile.color_selection
        if (
            not force_custom
            and selection != Profile.CUSTOM
            and self.palette.can_handle(target)
        ):
            return self.PALETTE
        if selection == Profile.PALETTE:
            return self.NONE
        if self.calibrated.can_handle(target):
            return self.CALIBRATED
        if self.keyboard.can_handle(target):
            return self.KEYBOARD
        return self.NONE

    def apply(self, target: Tuple[int, int, int], force_custom: bool = False) -> str:
        source = self.resolve(target, force_custom)
        if source == self.PALETTE:
            self.palette.select(target)
        elif source == self.CALIBRATED:
            self.calibrated.select(target)
        elif source == self.KEYBOARD:
            self.keyboard.select(target)
        return source


# ---------------------------------------------------------------------------
# The screen driver
# ---------------------------------------------------------------------------
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

    # -- capabilities ----------------------------------------------------
    @property
    def capabilities(self) -> Capabilities:
        return Capabilities.from_bot(self.bot)

    # -- colour selection ------------------------------------------------
    def resolve_color_source(
        self, target: Tuple[int, int, int], force_custom: bool = False
    ) -> str:
        return self.color_chain.resolve(target, force_custom)

    def select_color(
        self, target: Tuple[int, int, int], force_custom: bool = False
    ) -> str:
        return self.color_chain.apply(target, force_custom)

    def click_swatch(self, x: int, y: int) -> None:
        """Click a palette/spectrum swatch, honouring MSPaint double-click mode."""
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

    def enter_rgb_keyboard(self, c: Iterable[int]) -> None:
        """Fallback: type the RGB values directly into the app's colour dialog."""
        cc_box = self.bot._custom_colors
        if cc_box is None:
            raise NoCustomColorsError(
                "Bot could not continue because custom colors are not initialized"
            )
        center_x = cc_box[0] + cc_box[2] // 2
        center_y = cc_box[1] + cc_box[3] // 2
        log.debug(f"[DEBUG] Spectrum not available - clicking center of box at: ({center_x}, {center_y})")
        pyautogui.click((center_x, center_y), clicks=3, interval=.15)
        log.debug(f"[DEBUG] Using keyboard input method - typing RGB: {c}")
        pyautogui.press("tab", presses=7, interval=.05)
        for val in c:
            for n in (d for d in str(val)):
                pyautogui.press(str(n))
            pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("enter")
        pyautogui.PAUSE = 0.0

    # -- modifier click helpers -----------------------------------------
    def _release_all_modifiers(self, label: Optional[str] = None) -> None:
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
        """Press ``modifiers``, click ``coords``, then release everything.

        Shared by the New Layer / Color Button / Color Button Okay actions; the
        caller prints its own "attempting" line beforehand.
        """
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
            # Wait for the target app to process the click, then ensure the
            # layer is ready before painting.
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
    def execute_stroke(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        delay: float,
    ) -> None:
        """Draw one run as a left-button drag, segmented for smoothness.

        When the previous stroke was interrupted by a pause, it is replayed so
        the resumed line is clean (matching the historical behaviour).
        """
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < 1:  # Very short line
            pyautogui.moveTo(start_pos)
            pyautogui.dragTo(end_pos[0], end_pos[1], 0, button="left")
            return

        # Break into segments for smooth drawing
        segments = max(2, min(10, int(distance / 10)))  # 2-10 segments based on length
        segment_delay = delay / segments

        pyautogui.moveTo(start_pos)
        pyautogui.mouseDown(button="left")

        # Always replay the current stroke when resuming from pause
        if self.bot.draw_state.get("was_paused", False):
            log.info("Replaying stroke after pause - ensuring clean result")
            self.bot.draw_state["was_paused"] = False

        for i in range(1, segments + 1):
            t = i / segments
            pyautogui.moveTo(start_pos[0] + dx * t, start_pos[1] + dy * t)
            time.sleep(segment_delay)  # Distribute the stroke delay across segments

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
            time.sleep(0.2)  # Delay between strokes
