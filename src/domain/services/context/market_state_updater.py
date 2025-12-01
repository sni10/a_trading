from __future__ import annotations

from typing import Any, Dict

from src.domain.interfaces.cache import IMarketCache
from src.domain.interfaces.logger import ILogger


def update_market_state(
    context: Dict[str, Any],
    *,
    symbol: str,
    price: float,
    ts: int,
    logger: ILogger | None = None,
) -> None:
    """Обновить разделы ``market`` и ``market_caches`` по простому тику.

    Используется синхронным демо‑конвейером: тик описывается минимальным
    набором полей (``symbol``, ``price``, ``ts``). Функция не делает
    внешнего I/O и работает только с in‑memory структурами контекста.
    """

    market = context.setdefault("market", {})
    market[symbol] = {"last_price": price, "ts": ts}

    caches = context.get("market_caches") or {}
    cache = caches.get(symbol)
    if isinstance(cache, IMarketCache):
        ticker = {
            "symbol": symbol,
            "last": price,
            "timestamp": ts,
        }
        cache.update_ticker(ticker)

    if logger:
        has_cache = isinstance(cache, IMarketCache)
        logger.log_info(
            f"🌐 [FEEDS] Обновление market‑state по тику | symbol: {symbol} | price: {price:.8f} | ts: {ts} | has_cache: {has_cache}"
        )


def update_metrics(
    context: Dict[str, Any],
    ticker_id: int,
    *,
    logger: ILogger | None = None,
) -> None:
    """Обновить агрегированные метрики конвейера в контексте."""

    metrics = context.get("metrics", {})
    metrics["ticks"] = ticker_id
    context["metrics"] = metrics

    if logger:
        logger.log_info(
            f"📂 [STATE] Обновление метрик состояния | ticker_id: {ticker_id}"
        )


__all__ = ["update_market_state", "update_metrics"]
