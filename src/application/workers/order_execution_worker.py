from __future__ import annotations

"""Воркер размещения ордеров на бирже."""

import asyncio
from collections.abc import Callable

from src.config.config import AppConfig
from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.interfaces.exchange_connector import IExchangeConnector
from src.domain.services.order_sync_service import OrderSyncService
from src.infrastructure.logging import log_stage


async def order_execution_worker(
    connector: IExchangeConnector,
    order_sync: OrderSyncService,
    context: dict,
    config: AppConfig,
    *,
    symbol: str,
    is_stopped: Callable[[], bool] | None = None,
) -> None:
    """Размещать BUY/SELL ордера на бирже по локальным сделкам."""
    interval = getattr(config, "order_execution_interval_seconds", 0.5)
    retry_sec = getattr(config, "order_execution_retry_seconds", 2.0)

    log_stage(
        "EXEC",
        "Старт воркера исполнения ордеров",
        symbol=symbol,
        interval=interval,
        retry_sec=retry_sec,
    )

    while True:
        await _place_pending_orders(
            connector,
            order_sync,
            context,
            symbol=symbol,
            retry_sec=retry_sec,
        )

        if is_stopped is not None and is_stopped():
            log_stage("STOP", "Остановка воркера исполнения ордеров", symbol=symbol)
            break

        await asyncio.sleep(interval)


async def _place_pending_orders(
    connector: IExchangeConnector,
    order_sync: OrderSyncService,
    context: dict,
    *,
    symbol: str,
    retry_sec: float,
) -> None:
    deals = (context.get("deals") or {}).get(symbol) or []
    if not deals:
        return

    execution_state = context.setdefault("execution", {}).setdefault(symbol, {})
    now_ts = _now_ms()

    for deal in deals:
        if not isinstance(deal, Deal):
            continue
        if deal.status == Deal.STATUS_CANCELED:
            continue

        buy_order = deal.buy_order
        if _can_place_order(buy_order, execution_state, now_ts, retry_sec):
            created = await _create_exchange_order(connector, buy_order, symbol)
            if created is not None:
                order_sync.apply_exchange_order_to_local(
                    buy_order,
                    created,
                    symbol=symbol,
                    context=context,
                )
            _mark_attempt(execution_state, buy_order, now_ts)

        sell_order = deal.sell_order
        if _can_place_sell(deal, execution_state, now_ts, retry_sec):
            created = await _create_exchange_order(connector, sell_order, symbol)
            if created is not None:
                order_sync.apply_exchange_order_to_local(
                    sell_order,
                    created,
                    symbol=symbol,
                    context=context,
                )
            _mark_attempt(execution_state, sell_order, now_ts)


def _can_place_order(
    order: Order | None,
    execution_state: dict,
    now_ts: int,
    retry_sec: float,
) -> bool:
    if order is None:
        return False
    if order.exchange_order_id:
        return False
    if str(getattr(order, "status", "")).lower() != "open":
        return False
    if not _ready_for_retry(execution_state, order, now_ts, retry_sec):
        return False
    return True


def _can_place_sell(
    deal: Deal,
    execution_state: dict,
    now_ts: int,
    retry_sec: float,
) -> bool:
    buy_order = deal.buy_order
    sell_order = deal.sell_order
    if buy_order is None or sell_order is None:
        return False
    if not buy_order.is_filled():
        return False
    return _can_place_order(sell_order, execution_state, now_ts, retry_sec)


def _ready_for_retry(
    execution_state: dict,
    order: Order,
    now_ts: int,
    retry_sec: float,
) -> bool:
    order_key = _order_key(order)
    last_attempt = execution_state.get(order_key)
    if last_attempt is None:
        return True
    return (now_ts - last_attempt) >= int(retry_sec * 1000)


def _mark_attempt(execution_state: dict, order: Order | None, now_ts: int) -> None:
    if order is None:
        return
    execution_state[_order_key(order)] = now_ts


def _order_key(order: Order) -> str:
    if order.id is not None:
        return f"local:{order.id}"
    if order.exchange_order_id:
        return f"exchange:{order.exchange_order_id}"
    return f"tmp:{id(order)}"


async def _create_exchange_order(
    connector: IExchangeConnector,
    order: Order | None,
    symbol: str,
) -> Order | None:
    if order is None:
        return None
    try:
        created = await connector.create_order(
            symbol=symbol,
            order_type=str(order.type or "limit"),
            side=str(order.side or "buy"),
            amount=float(order.amount),
            price=float(order.price) if order.price is not None else None,
            params={},
        )
        return created
    except Exception as exc:  # pragma: no cover - защитный контур
        log_stage(
            "EXEC",
            f"Ошибка создания ордера: {type(exc).__name__}: {exc}",
            symbol=symbol,
        )
        return None


def _now_ms() -> int:
    return int(asyncio.get_event_loop().time() * 1000)


__all__ = ["order_execution_worker"]
