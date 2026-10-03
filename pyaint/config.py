"""config.json I/O and the environment/preferences split.

Keeps ``Window`` focused on widgets: this module owns reading/writing the file
and separating the taught environment (owned by ``Profile``) from user
preferences (owned by the window).
"""

import json
from typing import Any, Dict, Mapping

from pyaint.profile import ENV_CONFIG_KEYS, Profile

# Environment keys that older config files may still contain. Dropped so they
# do not leak into the preferences dict (and thus back into config.json).
_LEGACY_ENV_KEYS = frozenset({"Custom Colors", "color_preview_spot", "color_selection"})


def load_config(path: str) -> Dict[str, Any]:
    """Read a config file; return ``{}`` when missing or invalid."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(path: str, payload: Mapping[str, Any]) -> bool:
    """Write ``payload`` as JSON. Returns ``False`` on failure."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def split_preferences(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Return only the non-environment (preference) keys from a config dict."""
    return {
        key: value
        for key, value in config.items()
        if key not in ENV_CONFIG_KEYS and key not in _LEGACY_ENV_KEYS
    }


def build_payload(
    preferences: Mapping[str, Any], profile: Profile
) -> Dict[str, Any]:
    """Merge preferences with the environment subset of ``profile``."""
    payload: Dict[str, Any] = dict(preferences)
    payload.update(profile.to_config())
    return payload
