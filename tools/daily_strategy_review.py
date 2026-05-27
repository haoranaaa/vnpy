from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "var" / "strategy_reviews"
DEFAULT_STATE_PATH = Path.home() / ".vntrader" / "okx_auto_state.json"
DEFAULT_STRATEGY_DATA_PATH = Path.home() / ".vntrader" / "cta_strategy_data.json"
DEFAULT_STRATEGY_SETTING_PATH = Path.home() / ".vntrader" / "cta_strategy_setting.json"
DEFAULT_LOG_DIR = Path.home() / ".vntrader" / "log"


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object, returning an empty dict when unavailable."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    """Read text from a path, returning empty text when unavailable."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_log_metrics(log_text: str, strategy_name: str) -> dict[str, Any]:
    """Extract compact runtime process metrics from vn.py logs."""
    reference = f"CtaStrategy_{strategy_name}" if strategy_name else "CtaStrategy_"
    patterns = {
        "order_attempts": "委托下单",
        "trades": "成交",
        "order_failures": "下单失败",
        "order_rejections": "拒单",
        "strategy_exceptions": "触发异常已停止",
        "socket_closed": "socket is already closed",
        "connection_lost": "Connection to remote host was lost",
        "public_reconnects": "Public API connected",
        "private_reconnects": "Private API connected",
    }
    counts = Counter()
    strategy_order_lines: list[str] = []
    failure_lines: list[str] = []

    for line in log_text.splitlines():
        for key, pattern in patterns.items():
            if pattern in line:
                counts[key] += 1
        if "委托下单" in line and reference in line:
            strategy_order_lines.append(line)
        if any(pattern in line for pattern in ("下单失败", "拒单", "触发异常已停止", "socket is already closed")):
            failure_lines.append(line)

    return {
        "counts": dict(counts),
        "strategy_order_count": len(strategy_order_lines),
        "recent_strategy_orders": strategy_order_lines[-10:],
        "recent_failures": failure_lines[-10:],
    }


def run_acceptance_backtest(strategy: str, timeout: int) -> dict[str, Any]:
    """Run the configured acceptance backtest gate and capture its evidence."""
    command = [
        str(PYTHON),
        "tools/strategy_acceptance.py",
        "--strategy",
        strategy,
        "--gate",
        "backtest",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    evidence: dict[str, Any] = {}
    for line in completed.stdout.splitlines():
        if "ACCEPTANCE_BACKTEST_REPORT" not in line:
            continue
        _, _, payload = line.partition("ACCEPTANCE_BACKTEST_REPORT")
        try:
            evidence = json.loads(payload.strip())
        except json.JSONDecodeError:
            evidence = {"raw": payload.strip()}

    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "evidence": evidence,
        "output_tail": "\n".join(completed.stdout.splitlines()[-40:]),
    }


def build_recommendations(report: dict[str, Any]) -> list[dict[str, str]]:
    """Build non-mutating strategy improvement candidates from process and result metrics."""
    recommendations: list[dict[str, str]] = []
    state = report.get("runtime_state") or {}
    latest_error = str(state.get("latest_error") or "")
    latest_signal = state.get("latest_chan_signal") or {}
    sizing = latest_signal.get("sizing") or {}
    log_counts = ((report.get("log_metrics") or {}).get("counts") or {})
    backtest = (report.get("backtest") or {}).get("evidence") or {}

    if latest_error:
        recommendations.append(
            {
                "priority": "high",
                "area": "execution",
                "recommendation": "Fix runtime/exchange connectivity before tuning strategy parameters.",
                "evidence": latest_error[:240],
            }
        )

    if log_counts.get("strategy_exceptions", 0) or log_counts.get("socket_closed", 0):
        recommendations.append(
            {
                "priority": "high",
                "area": "order_routing",
                "recommendation": "Treat order-path reliability as the first optimization target; parameter changes cannot recover failed submissions.",
                "evidence": json.dumps(log_counts, ensure_ascii=False, sort_keys=True),
            }
        )

    if sizing.get("clipped") and sizing.get("reason"):
        recommendations.append(
            {
                "priority": "medium",
                "area": "sizing",
                "recommendation": "Review whether the position cap matches the intended exposure; validate any cap increase with backtest and DEMO first.",
                "evidence": json.dumps(sizing, ensure_ascii=False, sort_keys=True),
            }
        )

    if backtest:
        total_return = float(backtest.get("total_return", 0) or 0)
        sharpe = float(backtest.get("sharpe_ratio", 0) or 0)
        trade_count = int(backtest.get("trade_count", 0) or 0)
        if trade_count == 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "area": "signal",
                    "recommendation": "Backtest produced no trades; inspect signal scarcity before changing sizing.",
                    "evidence": f"trade_count={trade_count}",
                }
            )
        elif total_return <= 0 or sharpe <= 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "area": "strategy_rules",
                    "recommendation": "Keep candidate changes in signal-only mode; require improved return and Sharpe before promotion.",
                    "evidence": f"total_return={total_return:.4f}, sharpe={sharpe:.4f}, trades={trade_count}",
                }
            )

    if not recommendations:
        recommendations.append(
            {
                "priority": "low",
                "area": "monitoring",
                "recommendation": "No urgent issue detected; keep collecting daily review evidence before changing parameters.",
                "evidence": "runtime and backtest review completed",
            }
        )

    return recommendations


def write_markdown(report: dict[str, Any], path: Path) -> None:
    """Write a human-readable daily review summary."""
    state = report.get("runtime_state") or {}
    latest_signal = state.get("latest_chan_signal") or {}
    sizing = latest_signal.get("sizing") or {}
    backtest = report.get("backtest") or {}
    evidence = backtest.get("evidence") or {}

    lines = [
        f"# Strategy Daily Review - {report['review_date']}",
        "",
        "## Runtime",
        f"- strategy: `{state.get('strategy_name', '-')}`",
        f"- server: `{state.get('okx_server', '-')}`",
        f"- trade enabled: `{state.get('strategy_trade_enabled', '-')}`",
        f"- latest tick: `{state.get('latest_tick_ts', '-')}`",
        f"- latest order: `{state.get('latest_order_ts', '-')}`",
        f"- latest trade: `{state.get('latest_trade_ts', '-')}`",
        f"- latest error: `{state.get('latest_error', '')[:240]}`",
        "",
        "## Latest Signal",
        f"- signal key: `{latest_signal.get('signal_key', '-')}`",
        f"- type: `{latest_signal.get('type', '-')}`",
        f"- bar time: `{latest_signal.get('bar_datetime', '-')}`",
        f"- close: `{latest_signal.get('bar_close_price', '-')}`",
        f"- stop: `{latest_signal.get('stop_price', '-')}`",
        f"- order volume: `{sizing.get('order_volume', '-')}`",
        f"- order value: `{sizing.get('order_value', '-')}`",
        f"- sizing reason: `{sizing.get('reason', '-')}`",
        "",
        "## Log Metrics",
        "```json",
        json.dumps(report.get("log_metrics", {}), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Backtest",
        f"- passed: `{backtest.get('passed', False)}`",
        f"- return code: `{backtest.get('returncode', '-')}`",
        f"- total return: `{evidence.get('total_return', '-')}`",
        f"- sharpe: `{evidence.get('sharpe_ratio', '-')}`",
        f"- max drawdown: `{evidence.get('max_drawdown', '-')}`",
        f"- trades: `{evidence.get('trade_count', '-')}`",
        "",
        "## Recommendations",
    ]
    for item in report.get("recommendations", []):
        lines.append(
            f"- [{item['priority']}] {item['area']}: {item['recommendation']} "
            f"(evidence: `{item['evidence']}`)"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    """Build the daily strategy review report."""
    now = datetime.now().astimezone()
    review_date = args.date or now.strftime("%Y-%m-%d")
    state = load_json(args.state_path)
    strategy_name = str(state.get("strategy_name") or "Chan_Auto")
    log_path = args.log_dir / f"vt_{review_date.replace('-', '')}.log"
    log_metrics = parse_log_metrics(read_text(log_path), strategy_name)
    backtest = (
        {"skipped": True, "reason": "disabled by --skip-backtest"}
        if args.skip_backtest
        else run_acceptance_backtest(args.strategy, args.backtest_timeout)
    )
    report = {
        "review_date": review_date,
        "generated_at": now.isoformat(),
        "strategy": args.strategy,
        "paths": {
            "state": str(args.state_path),
            "strategy_data": str(args.strategy_data_path),
            "strategy_setting": str(args.strategy_setting_path),
            "log": str(log_path),
        },
        "runtime_state": state,
        "strategy_data": load_json(args.strategy_data_path),
        "strategy_setting": load_json(args.strategy_setting_path),
        "log_metrics": log_metrics,
        "backtest": backtest,
    }
    report["recommendations"] = build_recommendations(report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run daily strategy review.")
    parser.add_argument("--strategy", default="chan")
    parser.add_argument("--date", default="")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--strategy-data-path", type=Path, default=DEFAULT_STRATEGY_DATA_PATH)
    parser.add_argument("--strategy-setting-path", type=Path, default=DEFAULT_STRATEGY_SETTING_PATH)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--skip-backtest", action="store_true")
    parser.add_argument("--backtest-timeout", type=int, default=900)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Write daily review artifacts and print the output directory."""
    args = parse_args(argv)
    report = build_report(args)
    output_dir = args.output_root / report["review_date"]
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    summary_path = output_dir / "summary.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, summary_path)
    print(f"daily strategy review written: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
