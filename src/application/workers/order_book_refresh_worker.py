from __future__ import annotations

"""Периодический воркер обновления стакана через ``fetch_order_book``.

Использует абстракции ``IExchangeConnector`` и ``IMarketCache`` и живёт в
слое ``application``, не добавляя собственную бизнес‑логику.
"""

import asyncio
from collections.abc import Callable

from src.config.config import AppConfig
from src.domain.interfaces.cache import IMarketCache
from src.infrastructure.connectors.interfaces.exchange_connector import (
    IExchangeConnector,
)
from src.infrastructure.logging.logging_setup import log_stage


async def order_book_refresh_worker(
    connector: IExchangeConnector,
    market_cache: IMarketCache,
    symbol: str,
    config: AppConfig,
    *,
    is_stopped: Callable[[], bool] | None = None,
) -> None:
    """Простейший асинхронный воркер обновления стакана.

    Периодически вызывает ``connector.fetch_order_book`` и складывает
    результат в ``market_cache.update_orderbook``. Интервал обновления
    задаётся полем ``order_book_refresh_interval_seconds`` конфигурации.

    В реальной реализации сюда стоит добавить подробный ``try/except``,
    backoff и более сложную стратегию восстановления соединения.
    """

    interval = getattr(config, "order_book_refresh_interval_seconds", 5.0)

    log_stage(
        "FEEDS",
        "Старт воркера обновления стакана",
        symbol=symbol,
        interval=interval,
    )

    while True:
        # Всегда делаем хотя бы одну попытку обновления стакана, даже если
        # флаг остановки уже поднят – это упрощает использование воркера в
        # unit‑тестах и при кратковременных джобах.
        order_book = await connector.fetch_order_book(symbol)
        market_cache.update_orderbook(order_book)

        if is_stopped is not None and is_stopped():
            log_stage("STOP", "Остановка воркера обновления стакана", symbol=symbol)
            break

        await asyncio.sleep(interval)


__all__ = ["order_book_refresh_worker"]
