from __future__ import annotations

from dataclasses import dataclass

from vnpy.trader.constant import Direction, Offset


@dataclass(frozen=True)
class StrategyOrderResult:
    """Result returned by a CTA strategy order submission."""

    vt_orderids: list[str]
    direction: Direction
    offset: Offset
    price: float
    volume: float
    stop: bool
    reason: str

    @property
    def accepted(self) -> bool:
        """Return whether the CTA engine returned at least one order id."""
        return bool(self.vt_orderids)


def submit_cta_order(
    strategy,
    *,
    direction: Direction,
    offset: Offset,
    price: float,
    volume: float,
    reason: str,
    stop: bool = False,
    lock: bool = False,
    net: bool = False,
) -> StrategyOrderResult:
    """Submit a CTA order and log a standard failure line when it is not accepted."""
    vt_orderids = strategy.send_order(direction, offset, price, volume, stop, lock, net)
    result = StrategyOrderResult(
        vt_orderids=list(vt_orderids or []),
        direction=direction,
        offset=offset,
        price=price,
        volume=volume,
        stop=stop,
        reason=reason,
    )
    if not result.accepted:
        strategy.write_log(
            "CTA下单失败: no vt_orderid returned, "
            f"reason={reason}, direction={direction.value}, offset={offset.value}, "
            f"volume={volume}, price={price}, stop={stop}"
        )
    return result
