from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools import daily_strategy_review


def test_parse_log_metrics_counts_strategy_orders_and_failures() -> None:
    text = "\n".join(
        [
            "委托下单 -> OKX：OrderRequest(reference='CtaStrategy_Chan_Auto')",
            "[Chan_Auto] 触发异常已停止",
            "websocket._exceptions.WebSocketConnectionClosedException: socket is already closed.",
            "OKX | Private API connected",
        ]
    )

    metrics = daily_strategy_review.parse_log_metrics(text, "Chan_Auto")

    assert metrics["strategy_order_count"] == 1
    assert metrics["counts"]["strategy_exceptions"] == 1
    assert metrics["counts"]["socket_closed"] == 1
    assert metrics["counts"]["private_reconnects"] == 1
    assert len(metrics["recent_failures"]) == 2


def test_build_recommendations_prioritizes_execution_before_tuning() -> None:
    report = {
        "runtime_state": {
            "latest_error": "socket is already closed",
            "latest_chan_signal": {
                "sizing": {
                    "clipped": True,
                    "reason": "max_position_ratio",
                }
            },
        },
        "log_metrics": {"counts": {"strategy_exceptions": 1}},
        "backtest": {
            "evidence": {
                "total_return": -1,
                "sharpe_ratio": -0.2,
                "trade_count": 3,
            }
        },
    }

    recommendations = daily_strategy_review.build_recommendations(report)

    assert recommendations[0]["area"] == "execution"
    assert any(item["area"] == "sizing" for item in recommendations)
    assert any(item["area"] == "strategy_rules" for item in recommendations)


def test_build_report_writes_review_inputs_without_backtest(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    strategy_data_path = tmp_path / "data.json"
    strategy_setting_path = tmp_path / "setting.json"
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    state_path.write_text(
        json.dumps(
            {
                "strategy_name": "Chan_Auto",
                "latest_error": "",
                "latest_chan_signal": {"signal_key": "first_buy:1:8"},
            }
        )
    )
    strategy_data_path.write_text("{}")
    strategy_setting_path.write_text("{}")
    (log_dir / "vt_20260527.log").write_text("Private API connected")

    args = argparse.Namespace(
        strategy="chan",
        date="2026-05-27",
        output_root=tmp_path / "reviews",
        state_path=state_path,
        strategy_data_path=strategy_data_path,
        strategy_setting_path=strategy_setting_path,
        log_dir=log_dir,
        skip_backtest=True,
        backtest_timeout=1,
    )

    report = daily_strategy_review.build_report(args)

    assert report["review_date"] == "2026-05-27"
    assert report["runtime_state"]["strategy_name"] == "Chan_Auto"
    assert report["backtest"]["skipped"] is True
