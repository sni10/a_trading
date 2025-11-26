from __future__ import annotations

from typing import Dict, Any

from src.domain.entities.currency_pair import CurrencyPair
from src.infrastructure.cache.in_memory import InMemoryMarketCache


def _make_orderbook(levels: int) -> Dict[str, Any]:
    bids = [[100.0 - i, 1.0 + i] for i in range(levels)]
    asks = [[100.0 + i, 1.0 + i] for i in range(levels)]
    return {"bids": bids, "asks": asks, "symbol": "ETH/USDT"}


def test_market_cache_respects_pair_window_sizes() -> None:
    pair = CurrencyPair(
        symbol="ETH/USDT",
        base_currency="ETH",
        quote_currency="USDT",
        bar_window_size=10,
        orderbook_depth=5,
        trades_history_size=7,
    )

    cache = InMemoryMarketCache(pair)

    # Bars window respects maxlen
    for i in range(20):
        cache.add_bar({"i": i})

    bars = cache.get_bars()
    assert len(bars) == 10
    assert bars[0]["i"] == 10  # старые элементы вытеснены

    # Trades window respects maxlen
    for i in range(15):
        cache.add_trade({"id": i})

    trades = cache.get_trades()
    assert len(trades) == 7
    assert trades[0]["id"] == 8

    # Orderbook is trimmed to depth
    ob = _make_orderbook(levels=20)
    cache.update_orderbook(ob)
    trimmed = cache.get_orderbook()
    assert trimmed is not None
    assert len(trimmed["bids"]) == 5
    assert len(trimmed["asks"]) == 5


def test_market_cache_ticker_roundtrip() -> None:
    pair = CurrencyPair("ETH/USDT", "ETH", "USDT")
    cache = InMemoryMarketCache(pair)

    ticker = {
        "symbol": "ETH/USDT",
        "last": 100.5,
        "bid": 100.4,
        "ask": 100.6,
    }
    cache.update_ticker(ticker)
    stored = cache.get_ticker()

    assert stored is not None
    assert stored["last"] == 100.5
