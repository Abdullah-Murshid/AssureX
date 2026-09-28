"""
AssureX Claim Engine - Settings Loader
Reads config/settings.yaml once and caches the result.
Falls back to hard-coded defaults if the file is absent so nothing breaks
in tests that don't write a config dir.
"""

import os
import functools
from typing import Any

# Default values mirror the original hard-coded constants.
_DEFAULTS = {
    "model_version": "v2",
    "uncertainty_threshold": 0.60,
    "strong_match_threshold": 0.10,
    "acceptable_match_threshold": 0.25,
    "pdf_render_dpi": 200,
    "model_ready_timeout_seconds": 15,
    "warranty_alert_days": 30,
    "disagreement_alert_rate": 0.20,
    "manual_review_spike_rate": 0.40,
}

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),   # config/
    "..",                         # project root
    "config",
    "settings.yaml",
)


@functools.lru_cache(maxsize=1)
def get_settings() -> dict:
    """Load settings.yaml and merge with defaults. Cached after first call."""
    settings = dict(_DEFAULTS)
    path = os.path.normpath(CONFIG_PATH)
    if os.path.exists(path):
        try:
            import yaml  # pyyaml is in requirements.txt
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            settings.update(loaded)
        except Exception as e:
            print(f"[settings] Warning: could not load {path}: {e}")
    return settings


def get(key: str, default: Any = None) -> Any:
    """Convenience accessor: get_settings()[key] with an optional fallback."""
    return get_settings().get(key, default)


def save_setting(key: str, value: Any) -> bool:
    """Update a single setting in settings.yaml and invalidate the cache."""
    return update_settings({key: value})


def update_settings(updates: dict) -> bool:
    """Update settings in settings.yaml and invalidate the cache."""
    path = os.path.normpath(CONFIG_PATH)
    try:
        import yaml
        current = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                current = yaml.safe_load(f) or {}
        current.update(updates)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(current, f, default_flow_style=False, sort_keys=False)
        get_settings.cache_clear()
        return True
    except Exception as e:
        print(f"[settings] Warning: could not save settings to {path}: {e}")
        return False
