from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, AsyncIterator, Dict, List

import pytest

from src.application.workers.order_book_refresh_worker import (
    order_book_refresh_worker,
)
from src.config.config import AppConfig
from src.domain.interfaces.cache import IMarketCache
from src.domain.services.indicators.indicator_engine import compute_indicators
from src.domain.services.tick.tick_source import Ticker, TickSource
from src.infrastructure.connectors.interfaces.exchange_connector import (
    IExchangeConnector,
    UnifiedTicker,
)


class FakeExchangeConnector(IExchangeConnector):
    """Простая фейковая реализация коннектора для юнит‑тестов.

    Не использует сеть и возвращает заранее заданную последовательность
    тиков и один снимок стакана.
    """

    def __init__(self, ticks: List[Ticker], order_book: Dict[str, Any]) -> None:
        self._ticks = deque(ticks)
        self._order_book = order_book

    async def stream_ticks(self, symbol: str) -> AsyncIterator[UnifiedTicker]:  # type: ignore[override]
        while self._ticks:
            # Приводим доменный Ticker к инфраструктурному UnifiedTicker,
            # чтобы соответствовать контракту IExchangeConnector.
            tick = self._ticks.popleft()
            yield UnifiedTicker(symbol=tick["symbol"], price=tick["price"], ts=tick["ts"])

    async def fetch_order_book(self, symbol: str) -> dict:  # type: ignore[override]
        return self._order_book


class FakeMarketCache(IMarketCache):  # type: ignore[misc]
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.orderbook: Dict[str, Any] | None = None

    # Реализации методов, не используемых тестом, оставляем простыми
    def update_ticker(self, ticker: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_ticker(self) -> Dict[str, Any] | None:  # pragma: no cover
        return None

    def update_orderbook(self, orderbook: Dict[str, Any]) -> None:
        self.orderbook = orderbook

    def get_orderbook(self) -> Dict[str, Any] | None:  # pragma: no cover
        return self.orderbook

    def add_trade(self, trade: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_trades(self, limit: int | None = None) -> List[Dict[str, Any]]:  # pragma: no cover
        return []

    def add_bar(self, bar: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_bars(self, limit: int | None = None) -> List[Dict[str, Any]]:  # pragma: no cover
        return []


async def _drain_tick_source(source: TickSource, limit: int) -> List[Ticker]:
    result: List[Ticker] = []
    async for tick in source.stream():
        result.append(tick)
        if len(result) >= limit:
            break
    return result


@pytest.mark.unit
def test_tick_source_streams_unified_ticks() -> None:
    symbol = "BTC/USDT"
    ticks: List[Ticker] = [
        Ticker(symbol=symbol, price=100.0, ts=1),
        Ticker(symbol=symbol, price=101.0, ts=2),
    ]

    connector = FakeExchangeConnector(ticks=ticks, order_book={})
    source = TickSource(connector, symbol)

    out_ticks = asyncio.run(_drain_tick_source(source, limit=10))

    assert len(out_ticks) == 2
    assert out_ticks[0]["symbol"] == symbol
    assert out_ticks[0]["price"] == 100.0
    assert out_ticks[1]["price"] == 101.0


@pytest.mark.unit
def test_order_book_refresh_worker_updates_cache_once() -> None:
    symbol = "ETH/USDT"
    order_book = {
        "bids": [[10.0, 1.0]],
        "asks": [[11.0, 2.0]],
        "symbol": symbol,
        "timestamp": 123,
        "datetime": "2025-01-01T00:00:00Z",
        "nonce": None,
    }

    connector = FakeExchangeConnector(ticks=[], order_book=order_book)
    cache = FakeMarketCache(symbol)

    cfg = AppConfig(order_book_refresh_interval_seconds=0.0)

    # Флаг остановки после первого цикла
    calls: List[int] = []

    def is_stopped() -> bool:
        return bool(calls)

    async def runner() -> None:
        calls.append(1)
        await order_book_refresh_worker(
            connector,
            cache,
            symbol,
            cfg,
            is_stopped=is_stopped,
        )

    asyncio.run(runner())

    assert cache.orderbook is not None
    assert cache.orderbook["bids"][0][0] == 10.0
    assert cache.orderbook["asks"][0][0] == 11.0


@pytest.mark.unit
def test_compute_indicators_uses_price_history_and_triggers() -> None:
    from src.infrastructure.cache.in_memory import InMemoryIndicatorStore
    from src.domain.entities.currency_pair import CurrencyPair

    symbol = "BTC/USDT"
    pair = CurrencyPair(symbol, "BTC", "USDT", indicator_window_size=500)
    cfg = AppConfig(
        indicator_fast_interval=1,
        indicator_medium_interval=2,
        indicator_heavy_interval=10,
    )
    store = InMemoryIndicatorStore(pair, cfg)

    context: Dict[str, Any] = {
        "market": {symbol: {"ts": 1}},
        "indicator_stores": {symbol: store},
    }

    # Первый тик: сформируется только fast‑индикатор, т.к. истории ещё мало
    snapshot1 = compute_indicators(context, tick_id=1, symbol=symbol, price=100.0)
    assert snapshot1["price"] == 100.0
    # fast_interval == 1, поэтому fast_history должен обновиться
    assert list(store.fast_history) == [100.0]

    # Заполняем ещё несколько тиков, чтобы запустились medium/fast
    for tid, price in [(2, 101.0), (3, 102.0), (4, 103.0), (5, 104.0)]:
        compute_indicators(context, tick_id=tid, symbol=symbol, price=price)

    history = context["price_history"][symbol]
    assert len(history) >= 5

    # На тике 4 medium_interval == 2, поэтому SMA medium должна посчитаться
    snapshot_last = compute_indicators(
        context, tick_id=6, symbol=symbol, price=105.0
    )

    assert snapshot_last["symbol"] == symbol
    assert "sma_fast_5" in snapshot_last or "sma_medium_20" in snapshot_last
