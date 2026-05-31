from __future__ import annotations

"""Таймауты BUY-ордеров: отмена протухших заявок и закрытие сделки.

Два режима таймаута:
1. **Exchange timeout** (``timeout_sec``): для ордеров, уже размещённых
   на бирже (``exchange_order_id`` не пуст). Таймаут считается от
   ``order.timestamp`` (биржевого). Отменённые ордера добавляются в
   ``exchange_order_ids_to_cancel`` — их нужно отменить на бирже
   асинхронно.
2. **Pending-send timeout** (``pending_send_timeout_sec``): для ордеров,
   которые были созданы локально, но не отправлены на биржу
   (``exchange_order_id is None``). Если execution_worker не успел
   разместить ордер за это время — сделка и ордера отменяются локально.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order


@dataclass(frozen=True)
class BuyOrderTimeoutResult:
    canceled_orders: int
    canceled_deals: int
    exchange_order_ids_to_cancel: list[str] = field(default_factory=list)


def cancel_stale_buy_orders(
    context: Dict[str, Any],
    *,
    symbol: str,
    now_ts: int,
    timeout_sec: float,
    pending_send_timeout_sec: float = 0,
) -> BuyOrderTimeoutResult:
    """Отменить протухшие BUY-ордера и закрыть связанные сделки.

    Args:
        context: Глобальный контекст приложения.
        symbol: Торговая пара.
        now_ts: Текущий timestamp (мс).
        timeout_sec: Таймаут для ордеров, уже размещённых на бирже.
        pending_send_timeout_sec: Таймаут для ордеров, не отправленных
            на биржу (``exchange_order_id is None``). 0 = не проверять.
    """

    if now_ts <= 0:
        return BuyOrderTimeoutResult(0, 0)
    if timeout_sec <= 0 and pending_send_timeout_sec <= 0:
        return BuyOrderTimeoutResult(0, 0)

    orders = (context.get("orders") or {}).get(symbol) or []
    if not orders:
        return BuyOrderTimeoutResult(0, 0)

    deals = (context.get("deals") or {}).get(symbol) or []
    deal_map = _index_deals(deals)
    orders_by_id = _index_orders(orders)

    timeout_ms = int(timeout_sec * 1000)
    pending_timeout_ms = int(pending_send_timeout_sec * 1000)
    canceled_order_ids: set[int] = set()  # id(order) — Python object identity
    canceled_deal_ids: set[int] = set()
    exchange_ids_to_cancel: list[str] = []

    for order in list(orders):
        if not _is_open_buy(order):
            continue

        has_exchange_id = bool(order.exchange_order_id)

        if has_exchange_id:
            # Ордер на бирже — проверяем основной таймаут
            if timeout_sec <= 0:
                continue
            if not _is_timed_out(order, now_ts, timeout_ms):
                continue
            exchange_ids_to_cancel.append(str(order.exchange_order_id))
        else:
            # Ордер ещё не отправлен — проверяем pending-send таймаут
            if pending_send_timeout_sec <= 0:
                continue
            if not _is_timed_out(order, now_ts, pending_timeout_ms):
                continue

        _cancel_order(order, now_ts, canceled_order_ids)
        _cancel_linked_entities(
            order=order,
            now_ts=now_ts,
            deal_map=deal_map,
            orders_by_id=orders_by_id,
            canceled_order_ids=canceled_order_ids,
            canceled_deal_ids=canceled_deal_ids,
            all_deals=deals,
        )

    return BuyOrderTimeoutResult(
        len(canceled_order_ids),
        len(canceled_deal_ids),
        exchange_ids_to_cancel,
    )


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
    all_deals: list[Deal] | None = None,
) -> None:
    # Найти deal: сначала по deal_id (если есть DB ID), потом по object reference
    deal: Deal | None = None
    deal_id = getattr(order, "deal_id", None)
    if deal_id is not None:
        deal = deal_map.get(int(deal_id))

    if deal is None and all_deals:
        # Fallback: найти deal по ссылке на ордер
        for d in all_deals:
            if d.buy_order is order or d.sell_order is order:
                deal = d
                break

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
    canceled_deal_ids.add(id(deal))


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
    canceled_order_ids.add(id(order))


__all__ = ["BuyOrderTimeoutResult", "cancel_stale_buy_orders"]
