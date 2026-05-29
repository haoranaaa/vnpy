"""Tests for local private trading configuration loading."""

from __future__ import annotations

import json
from pathlib import Path

import trading_config
from trading_config import load_trading_config, resolve_trading_config_path


def test_local_trading_config_takes_precedence(tmp_path: Path, monkeypatch) -> None:
    public_cfg = tmp_path / "trading_config.json"
    local_cfg = tmp_path / "trading_config.local.json"
    monkeypatch.setattr(
        trading_config,
        "USER_TRADING_CONFIG",
        tmp_path / ".vntrader" / "trading_config.local.json",
    )

    public_cfg.write_text(
        json.dumps({"telegram": {"bot_token": "", "chat_id": ""}}),
        encoding="utf-8",
    )
    local_cfg.write_text(
        json.dumps({"telegram": {"bot_token": "private", "chat_id": "42"}}),
        encoding="utf-8",
    )

    assert resolve_trading_config_path(public_cfg) == local_cfg
    assert load_trading_config(public_cfg)["telegram"]["bot_token"] == "private"


def test_local_trading_config_merges_public_defaults(tmp_path: Path, monkeypatch) -> None:
    public_cfg = tmp_path / "trading_config.json"
    local_cfg = tmp_path / "trading_config.local.json"
    monkeypatch.setattr(
        trading_config,
        "USER_TRADING_CONFIG",
        tmp_path / ".vntrader" / "trading_config.local.json",
    )

    public_cfg.write_text(
        json.dumps(
            {
                "telegram": {"bot_token": "", "chat_id": ""},
                "notification": {"mode": "notify_only"},
                "runtime": {"init_timeout": 180, "init_days": 3},
            }
        ),
        encoding="utf-8",
    )
    local_cfg.write_text(
        json.dumps({"telegram": {"bot_token": "private", "chat_id": "42"}}),
        encoding="utf-8",
    )

    config = load_trading_config(public_cfg)

    assert config["telegram"]["bot_token"] == "private"
    assert config["notification"]["mode"] == "notify_only"
    assert config["runtime"]["init_timeout"] == 180


def test_user_trading_config_overrides_repo_local(
    tmp_path: Path,
    monkeypatch,
) -> None:
    public_cfg = tmp_path / "trading_config.json"
    local_cfg = tmp_path / "trading_config.local.json"
    user_cfg = tmp_path / ".vntrader" / "trading_config.local.json"
    user_cfg.parent.mkdir()

    public_cfg.write_text(
        json.dumps(
            {
                "telegram": {"bot_token": "", "chat_id": ""},
                "strategy": {"vt_symbol": "BTCUSDT_SWAP_OKX.GLOBAL"},
            }
        ),
        encoding="utf-8",
    )
    local_cfg.write_text(
        json.dumps({"telegram": {"bot_token": "repo", "chat_id": "1"}}),
        encoding="utf-8",
    )
    user_cfg.write_text(
        json.dumps({"telegram": {"bot_token": "user", "chat_id": "2"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(trading_config, "DEFAULT_TRADING_CONFIG", public_cfg)
    monkeypatch.setattr(trading_config, "USER_TRADING_CONFIG", user_cfg)

    config = load_trading_config(public_cfg)

    assert resolve_trading_config_path(public_cfg) == user_cfg
    assert config["telegram"]["bot_token"] == "user"
    assert config["telegram"]["chat_id"] == "2"
    assert config["strategy"]["vt_symbol"] == "BTCUSDT_SWAP_OKX.GLOBAL"
