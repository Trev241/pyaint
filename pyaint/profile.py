"""Taught-environment profile: the single source of truth for Pyaint's
environment geometry.

This module intentionally imports nothing from ``pyautogui`` or ``tkinter`` so
that a profile can be serialized, tested, and shared as a preset without a
display attached.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from typing import Any, Dict, Optional, Tuple


def _modifiers() -> Dict[str, bool]:
    return {"ctrl": False, "alt": False, "shift": False}


# Ordered to preserve the existing Setup-window row order.
TOOL_KEYS = (
    "Palette",
    "Canvas",
    "New Layer",
    "Color Button",
    "Color Button Okay",
)

DEFAULT_TOOLS: Dict[str, Dict[str, Any]] = {
    "Palette": {
        "status": False,
        "box": None,
        "rows": 6,
        "cols": 8,
        "color_coords": None,
        "preview": None,
    },
    "Canvas": {"status": False, "box": None, "preview": None},
    "New Layer": {
        "status": False,
        "coords": None,
        "enabled": False,
        "modifiers": _modifiers(),
    },
    "Color Button": {
        "status": False,
        "coords": None,
        "enabled": False,
        "delay": 0.1,
        "modifiers": _modifiers(),
    },
    "Color Button Okay": {
        "status": False,
        "coords": None,
        "enabled": False,
        "delay": 0.1,
        "modifiers": _modifiers(),
    },
}

DEFAULT_MSPAINT_MODE: Dict[str, Any] = {"enabled": False, "delay": 0.5}

# Keys that belong to the environment profile rather than to preferences.
# Used to split a loaded config.json into Profile + preferences.
ENV_CONFIG_KEYS = frozenset(TOOL_KEYS) | {"MSPaint Mode", "target"}


def box_to_wh(box: Optional[Any]) -> Optional[Tuple[int, int, int, int]]:
    """Convert a corner box ``(x1, y1, x2, y2)`` to ``(x, y, w, h)``.

    Tolerant of reversed corners; returns ``None`` for missing/short boxes.
    """
    if not box or len(box) != 4:
        return None
    x1, y1, x2, y2 = (int(v) for v in box)
    return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))


class Profile(Mapping):
    """Owns everything the user has "taught" Pyaint about their environment.

    Mapping access iterates the tool entries (``Palette``, ``Canvas``, ...) so
    the existing setup UI can keep using ``profile[name]`` / ``profile.items()``
    while still mutating the single shared instance.
    """

    def __init__(
        self,
        tools: Optional[Mapping[str, Any]] = None,
        mspaint_mode: Optional[Mapping[str, Any]] = None,
        target: str = "generic",
    ) -> None:
        self.tools: Dict[str, Dict[str, Any]] = {}
        for key in TOOL_KEYS:
            merged = copy.deepcopy(DEFAULT_TOOLS[key])
            incoming = (tools or {}).get(key)
            if isinstance(incoming, Mapping):
                # Preserve unknown keys from the incoming config too.
                merged.update(copy.deepcopy(dict(incoming)))
            self.tools[key] = merged

        self.mspaint_mode = copy.deepcopy(DEFAULT_MSPAINT_MODE)
        if isinstance(mspaint_mode, Mapping):
            self.mspaint_mode.update(copy.deepcopy(dict(mspaint_mode)))

        # Name of the selected target recipe (``pyaint.targets``). Stored as a
        # plain string so this module does not depend on the registry.
        self.target = str(target) if target else "generic"

    # ------------------------------------------------------------------
    # Mapping access over tool entries
    # ------------------------------------------------------------------
    def __getitem__(self, key: str) -> Dict[str, Any]:
        return self.tools[key]

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self.tools[key] = value

    def __iter__(self) -> Iterator[str]:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)

    def __contains__(self, key: object) -> bool:
        return key in self.tools

    def get(self, key: str, default: Any = None) -> Any:
        return self.tools.get(key, default)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, config: Optional[Mapping[str, Any]]) -> "Profile":
        """Build a Profile from the environment subset of a ``config.json`` dict."""
        config = config or {}
        tools = {
            key: config[key]
            for key in TOOL_KEYS
            if isinstance(config.get(key), Mapping)
        }
        return cls(
            tools=tools,
            mspaint_mode=config.get("MSPaint Mode"),
            target=config.get("target", "generic"),
        )

    def to_config(self) -> Dict[str, Any]:
        """Return the environment subset for merging into ``config.json``."""
        payload: Dict[str, Any] = copy.deepcopy(self.tools)
        payload["MSPaint Mode"] = copy.deepcopy(self.mspaint_mode)
        payload["target"] = self.target
        return payload

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def canvas_rect(self) -> Optional[Tuple[int, int, int, int]]:
        return box_to_wh(self.tools["Canvas"].get("box"))

    def palette_rect(self) -> Optional[Tuple[int, int, int, int]]:
        return box_to_wh(self.tools["Palette"].get("box"))
