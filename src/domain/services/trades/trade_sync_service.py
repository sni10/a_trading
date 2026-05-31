from __future__ import annotations

"""Сервис обработки трейдов (исполнений) и обновления ордеров/сделок."""

from typing import Any, Dict, Iterable

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.entities.trade import Trade
from src.domain.interfaces import IDealRepository, ILogger, IOrderRepository, ITradeRepository


class TradeSyncService:
    """Сервис, обновляющий локальное состояние по факту трейдов."""

    def __init__(
        self,
        trade_repo: ITradeRepository,
        order_repo: IOrderRepository,
        deal_repo: IDealRepository | None = None,
        logger: ILogger | None = None,
    ) -> None:
        self._trade_repo = trade_repo
        self._order_repo = order_repo
        self._deal_repo = deal_repo
        self._logger = logger

    def apply_trade(self, trade: Trade, *, symbol: str, context: Dict[str, Any]) -> None:
        """Применить трейд к контексту и БД."""
        trades_list = _ensure_trades_section(context, symbol)

        if trade.exchange_trade_id and _trade_exists(trades_list, trade.exchange_trade_id):
            return

        exchange_order_id = _extract_exchange_order_id(trade)
        orders_list = (context.get("orders") or {}).get(symbol) or []
        order = _find_order_by_exchange_id(orders_list, exchange_order_id)
        if order and order.id is not None:
            trade.order_id = order.id

        self._trade_repo.upsert(trade)
        trades_list.append(trade)

        if order is None:
            if self._logger:
                self._logger.log_stage(
                    "TRADES",
                    f"Trade без локального ордера: {trade.exchange_trade_id}",
                )
            return

        if trade.exchange_trade_id:
            if trade.exchange_trade_id not in order.trades:
                order.trades.append(trade.exchange_trade_id)

        _apply_trade_to_order(order, trades_list, exchange_order_id)
        self._order_repo.upsert(order)

        deals_list = (context.get("deals") or {}).get(symbol) or []
        deal = _find_deal_for_order(deals_list, order)
        if deal is not None:
            _sync_deal_status(deal)
            if self._deal_repo:
                self._deal_repo.update(deal)


def _ensure_trades_section(context: Dict[str, Any], symbol: str) -> list[Trade]:
    trades_section = context.setdefault("trades", {})
    return trades_section.setdefault(symbol, [])


def _trade_exists(trades: Iterable[Trade], exchange_trade_id: str) -> bool:
    return any(t.exchange_trade_id == exchange_trade_id for t in trades if t.exchange_trade_id)


def _extract_exchange_order_id(trade: Trade) -> str | None:
    info = trade.info or {}
    if isinstance(info, dict):
        for key in ("orderId", "order", "_exchange_order_id", "order_id"):
            value = info.get(key)
            if value:
                return str(value)
    return None


def _find_order_by_exchange_id(orders: Iterable[Order], exchange_order_id: str | None) -> Order | None:
    if not exchange_order_id:
        return None
    for order in orders:
        if order.exchange_order_id == exchange_order_id:
            return order
    return None


def _apply_trade_to_order(
    order: Order,
    trades: Iterable[Trade],
    exchange_order_id: str | None,
) -> None:
    if not exchange_order_id:
        return

    related = [
        t for t in trades if _extract_exchange_order_id(t) == exchange_order_id
    ]
    if not related:
        return

    filled = 0.0
    cost_total = 0.0
    last_ts = 0
    for trade in related:
        try:
            filled += float(trade.amount)
            cost_total += float(trade.cost)
        except (TypeError, ValueError):
            continue
        if trade.timestamp and trade.timestamp > last_ts:
            last_ts = trade.timestamp

    order.filled = filled
    order.cost = cost_total
    try:
        order.remaining = max(0.0, float(order.amount) - filled)
    except (TypeError, ValueError):
        pass

    if filled > 0:
        order.average = cost_total / filled

    if order.amount and filled >= float(order.amount):
        order.status = "closed"
    elif str(getattr(order, "status", "")).lower() == "":
        order.status = "open"

    if last_ts:
        order.last_trade_timestamp = last_ts


def _find_deal_for_order(deals: Iterable[Deal], order: Order) -> Deal | None:
    if order.deal_id is not None:
        for deal in deals:
            if getattr(deal, "id", None) == order.deal_id:
                return deal
    for deal in deals:
        if deal.buy_order and deal.buy_order.exchange_order_id == order.exchange_order_id:
            return deal
        if deal.sell_order and deal.sell_order.exchange_order_id == order.exchange_order_id:
            return deal
    return None


def _sync_deal_status(deal: Deal) -> None:
    buy_status = str(getattr(deal.buy_order, "status", "")).lower() if deal.buy_order else ""
    sell_status = str(getattr(deal.sell_order, "status", "")).lower() if deal.sell_order else ""

    if buy_status in {"canceled", "expired", "rejected"}:
        deal.mark_as_canceled()
        deal.metadata.setdefault("cancel_reason", f"buy_{buy_status}")
        return

    if sell_status == "closed":
        deal.mark_as_closed()
        return

    if buy_status == "closed":
        if deal.status == Deal.STATUS_PENDING:
            deal.mark_as_open()
        if deal.sell_order and str(getattr(deal.sell_order, "status", "")).lower() == "open":
            if deal.status != Deal.STATUS_CLOSING:
                deal.status = Deal.STATUS_CLOSING


__all__ = ["TradeSyncService"]
