from __future__ import annotations

"""Воркер стрима трейдов через WebSocket (ccxt.pro watch_my_trades)."""

import asyncio
from collections.abc import Callable

from src.domain.interfaces.exchange_connector import IExchangeConnector
from src.domain.services.trades.trade_sync_service import TradeSyncService
from src.infrastructure.logging import log_stage


async def trade_stream_worker(
    connector: IExchangeConnector,
    trade_sync: TradeSyncService,
    context: dict,
    *,
    symbol: str,
    is_stopped: Callable[[], bool] | None = None,
) -> None:
    """Слушать поток трейдов и обновлять локальный state + БД."""
    log_stage("FEEDS", "Старт воркера стрима трейдов", symbol=symbol)

    while True:
        try:
            async for trade in connector.stream_my_trades(symbol):
                trade_sync.apply_trade(trade, symbol=symbol, context=context)

                if is_stopped is not None and is_stopped():
                    log_stage("STOP", "Остановка воркера стрима трейдов", symbol=symbol)
                    return
        except Exception as exc:  # pragma: no cover - защитный контур
            log_stage(
                "TRADES",
                f"Ошибка стрима трейдов: {type(exc).__name__}: {exc}",
                symbol=symbol,
            )
            await asyncio.sleep(1)

        if is_stopped is not None and is_stopped():
            log_stage("STOP", "Остановка воркера стрима трейдов", symbol=symbol)
            break


__all__ = ["trade_stream_worker"]
