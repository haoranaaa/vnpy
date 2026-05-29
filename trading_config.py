"""Trading config loader with local-private override support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_TRADING_CONFIG = Path(__file__).parent / "config" / "trading_config.json"
USER_TRADING_CONFIG = Path.home() / ".vntrader" / "trading_config.local.json"


def _is_default_public_config(path: Path) -> bool:
    """Return whether path points at the repository default trading config."""
    return path.resolve() == DEFAULT_TRADING_CONFIG.resolve()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return base recursively overlaid with override."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_trading_config_path(config_path: str | Path | None = None) -> Path:
    """Return the highest-precedence private config path when present."""
    path = Path(config_path) if config_path is not None else DEFAULT_TRADING_CONFIG
    if _is_default_public_config(path) and USER_TRADING_CONFIG.exists():
        return USER_TRADING_CONFIG
    local_path = path.with_name(f"{path.stem}.local{path.suffix}")
    if local_path.exists():
        return local_path
    return path


def load_trading_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load JSON trading config, overlaying repo-local and user-private overrides."""
    path = Path(config_path) if config_path is not None else DEFAULT_TRADING_CONFIG
    public_path = path
    user_override_enabled = False
    if path == USER_TRADING_CONFIG:
        public_path = DEFAULT_TRADING_CONFIG
        user_override_enabled = True
    elif path.name.endswith(".local.json"):
        candidate = path.with_name(path.name.replace(".local.json", ".json"))
        public_path = candidate if candidate.exists() else DEFAULT_TRADING_CONFIG
        user_override_enabled = _is_default_public_config(public_path)
    else:
        user_override_enabled = _is_default_public_config(public_path)

    with public_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    local_path = public_path.with_name(f"{public_path.stem}.local{public_path.suffix}")
    if local_path.exists():
        with local_path.open("r", encoding="utf-8") as f:
            config = _deep_merge(config, json.load(f))

    if (
        user_override_enabled
        and USER_TRADING_CONFIG.exists()
        and USER_TRADING_CONFIG != local_path
    ):
        with USER_TRADING_CONFIG.open("r", encoding="utf-8") as f:
            config = _deep_merge(config, json.load(f))

    return config
