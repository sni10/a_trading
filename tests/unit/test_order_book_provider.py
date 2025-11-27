from __future__ import annotations

from typing import Any, Dict, List

from src.domain.interfaces.cache import IMarketCache
from src.domain.services.market_data.order_book_provider import (
    get_order_book_from_context,
)


class FakeMarketCache(IMarketCache):  # type: ignore[misc]
    def __init__(self, symbol: str, orderbook: Dict[str, Any] | None) -> None:
        self.symbol = symbol
        self._orderbook = orderbook

    # --- Ticker ---
    def update_ticker(self, ticker: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_ticker(self) -> Dict[str, Any] | None:  # pragma: no cover
        return None

    # --- Order book ---
    def update_orderbook(self, orderbook: Dict[str, Any]) -> None:  # pragma: no cover
        self._orderbook = orderbook

    def get_orderbook(self) -> Dict[str, Any] | None:
        return self._orderbook

    # --- Trades ---
    def add_trade(self, trade: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_trades(self, limit: int | None = None) -> List[Dict[str, Any]]:  # pragma: no cover
        return []

    # --- Bars ---
    def add_bar(self, bar: Dict[str, Any]) -> None:  # pragma: no cover
        pass

    def get_bars(self, limit: int | None = None) -> List[Dict[str, Any]]:  # pragma: no cover
        return []


def test_get_order_book_from_context_returns_snapshot_when_available() -> None:
    symbol = "BTC/USDT"
    order_book = {
        "bids": [[100.0, 1.0]],
        "asks": [[101.0, 2.0]],
        "symbol": symbol,
        "timestamp": 123,
        "datetime": "2025-01-01T00:00:00Z",
        "nonce": None,
    }

    cache = FakeMarketCache(symbol, order_book)
    context: Dict[str, Any] = {"market_caches": {symbol: cache}}

    snapshot = get_order_book_from_context(context, symbol=symbol)

    assert snapshot is not None
    assert snapshot["symbol"] == symbol
    assert snapshot["bids"][0][0] == 100.0
    assert snapshot["asks"][0][0] == 101.0


def test_get_order_book_from_context_returns_none_when_no_cache() -> None:
    symbol = "ETH/USDT"
    context: Dict[str, Any] = {"market_caches": {}}

    snapshot = get_order_book_from_context(context, symbol=symbol)

    assert snapshot is None
