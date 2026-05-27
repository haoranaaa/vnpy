from __future__ import annotations

from vnpy.trader.constant import Direction, Offset
from vnpy_ctastrategy.execution import submit_cta_order


class DummyStrategy:
    def __init__(self, vt_orderids: list[str]) -> None:
        self.vt_orderids = vt_orderids
        self.orders = []
        self.logs: list[str] = []

    def send_order(
        self,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        stop: bool,
        lock: bool,
        net: bool,
    ) -> list[str]:
        self.orders.append((direction, offset, price, volume, stop, lock, net))
        return self.vt_orderids

    def write_log(self, msg: str) -> None:
        self.logs.append(msg)


def test_submit_cta_order_returns_accepted_order_ids() -> None:
    strategy = DummyStrategy(["OKX.1"])

    result = submit_cta_order(
        strategy,
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=100,
        volume=0.1,
        reason="unit",
    )

    assert result.accepted is True
    assert result.vt_orderids == ["OKX.1"]
    assert strategy.logs == []


def test_submit_cta_order_logs_standard_failure() -> None:
    strategy = DummyStrategy([])

    result = submit_cta_order(
        strategy,
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=99,
        volume=0.1,
        reason="unit failure",
        stop=True,
    )

    assert result.accepted is False
    assert "CTA下单失败" in strategy.logs[0]
    assert "unit failure" in strategy.logs[0]
