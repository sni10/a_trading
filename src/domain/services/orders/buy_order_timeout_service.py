from __future__ import annotations

"""Таймауты BUY-ордеров: отмена протухших заявок и закрытие сделки."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order


@dataclass(frozen=True)
class BuyOrderTimeoutResult:
    canceled_orders: int
    canceled_deals: int


def cancel_stale_buy_orders(
    context: Dict[str, Any],
    *,
    symbol: str,
    now_ts: int,
    timeout_sec: float,
) -> BuyOrderTimeoutResult:
    """Отменить протухшие BUY-ордера и закрыть связанные сделки."""

    if timeout_sec <= 0 or now_ts <= 0:
        return BuyOrderTimeoutResult(0, 0)

    orders = (context.get("orders") or {}).get(symbol) or []
    if not orders:
        return BuyOrderTimeoutResult(0, 0)

    deals = (context.get("deals") or {}).get(symbol) or []
    deal_map = _index_deals(deals)
    orders_by_id = _index_orders(orders)

    timeout_ms = int(timeout_sec * 1000)
    canceled_order_ids: set[int] = set()
    canceled_deal_ids: set[int] = set()

    for order in list(orders):
        if not _is_open_buy(order):
            continue
        if not _is_timed_out(order, now_ts, timeout_ms):
            continue
        _cancel_order(order, now_ts, canceled_order_ids)
        _cancel_linked_entities(
            order=order,
            now_ts=now_ts,
            deal_map=deal_map,
            orders_by_id=orders_by_id,
            canceled_order_ids=canceled_order_ids,
            canceled_deal_ids=canceled_deal_ids,
        )

    return BuyOrderTimeoutResult(len(canceled_order_ids), len(canceled_deal_ids))


def _index_deals(deals: Iterable[Deal]) -> Dict[int, Deal]:
    return {deal.id: deal for deal in deals if getattr(deal, "id", None) is not None}


def _index_orders(orders: Iterable[Order]) -> Dict[int, Order]:
    return {order.id: order for order in orders if getattr(order, "id", None) is not None}


def _is_open_buy(order: Order) -> bool:
    return str(getattr(order, "side", "")).lower() == "buy" and str(
        getattr(order, "status", "")
    ).lower() == "open"


def _is_timed_out(order: Order, now_ts: int, timeout_ms: int) -> bool:
    try:
        order_ts = int(order.timestamp)
    except (TypeError, ValueError):
        return False
    return (now_ts - order_ts) >= timeout_ms


def _cancel_linked_entities(
    *,
    order: Order,
    now_ts: int,
    deal_map: Dict[int, Deal],
    orders_by_id: Dict[int, Order],
    canceled_order_ids: set[int],
    canceled_deal_ids: set[int],
) -> None:
    deal_id = getattr(order, "deal_id", None)
    if deal_id is None:
        return

    deal = deal_map.get(int(deal_id))
    if not deal:
        return

    if deal.buy_order:
        _cancel_order(deal.buy_order, now_ts, canceled_order_ids)
        _cancel_order_mirror(
            deal.buy_order, orders_by_id, now_ts, canceled_order_ids
        )
    if deal.sell_order:
        _cancel_order(deal.sell_order, now_ts, canceled_order_ids)
        _cancel_order_mirror(
            deal.sell_order, orders_by_id, now_ts, canceled_order_ids
        )

    if deal.status != Deal.STATUS_CANCELED:
        deal.mark_as_canceled()
        deal.metadata.setdefault("cancel_reason", "buy_order_timeout")
    canceled_deal_ids.add(deal.id)


def _cancel_order_mirror(
    order: Order,
    orders_by_id: Dict[int, Order],
    now_ts: int,
    canceled_order_ids: set[int],
) -> None:
    order_id = getattr(order, "id", None)
    if order_id is None:
        return
    mirror = orders_by_id.get(int(order_id))
    if mirror and mirror is not order:
        _cancel_order(mirror, now_ts, canceled_order_ids)


def _cancel_order(
    order: Order,
    now_ts: int,
    canceled_order_ids: set[int],
) -> None:
    if str(getattr(order, "status", "")).lower() == "closed":
        return
    order.status = "canceled"
    order.last_trade_timestamp = now_ts
    try:
        amount = float(order.amount)
        filled = float(order.filled)
        order.remaining = max(0.0, amount - filled)
    except (TypeError, ValueError):
        pass
    if order.id is not None:
        canceled_order_ids.add(int(order.id))


__all__ = ["BuyOrderTimeoutResult", "cancel_stale_buy_orders"]
