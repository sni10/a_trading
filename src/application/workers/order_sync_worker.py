from __future__ import annotations

"""Периодический воркер синхронизации ордеров с биржей."""

import asyncio
from collections.abc import Callable

from src.config.config import AppConfig
from src.domain.services.order_sync_service import OrderSyncService
from src.infrastructure.logging import log_stage


async def order_sync_worker(
    order_sync: OrderSyncService,
    context: dict,
    config: AppConfig,
    *,
    symbol: str,
    is_stopped: Callable[[], bool] | None = None,
) -> None:
    """Периодически сверять ордера с биржей, даже при стриме."""
    active_interval = getattr(config, "order_sync_interval_seconds", 5.0)
    idle_interval = getattr(config, "order_sync_idle_interval_seconds", 30.0)

    log_stage(
        "FEEDS",
        "Старт воркера синхронизации ордеров",
        symbol=symbol,
        active_interval=active_interval,
        idle_interval=idle_interval,
    )

    while True:
        try:
            await order_sync.sync_orders_with_exchange(
                symbol,
                context=context,
                buy_timeout_sec=config.buy_order_timeout_sec,
            )
        except Exception as exc:  # pragma: no cover - защитный контур
            log_stage(
                "ORDER_SYNC",
                f"Ошибка синхронизации ордеров: {type(exc).__name__}: {exc}",
                symbol=symbol,
            )

        if is_stopped is not None and is_stopped():
            log_stage("STOP", "Остановка воркера синхронизации ордеров", symbol=symbol)
            break

        orders = (context.get("orders") or {}).get(symbol) or []
        has_open = any(str(getattr(order, "status", "")).lower() == "open" for order in orders)
        interval = active_interval if has_open else idle_interval
        await asyncio.sleep(interval)


__all__ = ["order_sync_worker"]
