from __future__ import annotations

"""Воркер стрима ордеров через WebSocket (ccxt.pro watch_orders)."""

import asyncio
from collections.abc import Callable

from src.domain.services.order_sync_service import OrderSyncService
from src.domain.interfaces.exchange_connector import IExchangeConnector
from src.infrastructure.logging import log_stage


async def order_stream_worker(
    connector: IExchangeConnector,
    order_sync: OrderSyncService,
    context: dict,
    *,
    symbol: str,
    is_stopped: Callable[[], bool] | None = None,
) -> None:
    """Слушать поток ордеров и обновлять локальный state + БД."""
    log_stage("FEEDS", "Старт воркера стрима ордеров", symbol=symbol)

    while True:
        try:
            async for order in connector.stream_orders(symbol):
                order_sync.apply_exchange_order(order, symbol=symbol, context=context)

                if is_stopped is not None and is_stopped():
                    log_stage(
                        "STOP",
                        "Остановка воркера стрима ордеров",
                        symbol=symbol,
                    )
                    return
        except Exception as exc:  # pragma: no cover - защитный контур
            log_stage(
                "ORDER_STREAM",
                f"Ошибка стрима ордеров: {type(exc).__name__}: {exc}",
                symbol=symbol,
            )
            await asyncio.sleep(1)

        if is_stopped is not None and is_stopped():
            log_stage("STOP", "Остановка воркера стрима ордеров", symbol=symbol)
            break


__all__ = ["order_stream_worker"]
