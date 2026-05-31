"""Управление асинхронными воркерами.

Содержит вспомогательные функции для запуска и управления фоновыми задачами,
такими как обновление стакана (order book refresh worker).
"""

from __future__ import annotations

from src.application.workers.order_book_refresh_worker import (
    order_book_refresh_worker,
)
from src.config.config import AppConfig
from src.infrastructure.connectors.ccxt_pro_exchange_connector import (
    CcxtProExchangeConnector,
)


async def run_order_book_refresh_worker(
    connector: CcxtProExchangeConnector,
    context: dict,
    cfg: AppConfig,
    *,
    symbol: str,
) -> None:
    """Вспомогательная обёртка для запуска воркера стакана.

    Выделена в отдельную функцию, чтобы её было проще подменять в
    юнит‑тестах через monkeypatch.

    Args:
        connector: Коннектор к бирже для получения данных стакана.
        context: Глобальный контекст приложения с кэшами.
        cfg: Конфигурация приложения.
        symbol: Торговая пара (например, "BTC/USDT").

    Raises:
        RuntimeError: Если market_cache для указанного символа не найден.
    """

    market_caches = context.get("market_caches") or {}
    market_cache = market_caches.get(symbol)
    if market_cache is None:
        raise RuntimeError(f"Market cache for symbol {symbol!r} not found in context")

    await order_book_refresh_worker(
        connector,
        market_cache,
        symbol,
        cfg,
    )


__all__ = ["run_order_book_refresh_worker"]
