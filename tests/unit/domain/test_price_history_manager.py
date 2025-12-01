"""Юнит-тесты для PriceHistoryManager.

Проверяем, что менеджер корректно обновляет и ограничивает историю цен
и тикеров в контексте, не добавляя побочных эффектов.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from src.domain.services.indicators.price_history_manager import PriceHistoryManager
from src.domain.services.ticker.ticker_source import Ticker


@pytest.mark.unit
def test_update_history_creates_and_appends_price_and_ticker() -> None:
    manager = PriceHistoryManager(max_history_length=3)
    context: Dict[str, Any] = {}
    symbol = "BTC/USDT"

    ticker: Ticker = {
        "symbol": symbol,
        "timestamp": 1,
        "datetime": "2023-01-01T00:00:00Z",
        "last": 100.0,
        "open": 100.0,
        "high": 100.0,
        "low": 100.0,
        "close": 100.0,
        "bid": 99.5,
        "ask": 100.5,
        "baseVolume": 1.0,
        "quoteVolume": 100.0,
    }

    manager.update_history(context, symbol=symbol, ticker=ticker)

    # История цен и тикеров должна появиться в контексте
    assert "price_history" in context
    assert "ticker_history" in context

    prices = manager.get_price_history(context, symbol)
    tickers = manager.get_ticker_history(context, symbol)

    assert prices == [100.0]
    assert len(tickers) == 1
    assert tickers[0]["symbol"] == symbol


@pytest.mark.unit
def test_update_history_respects_max_history_length() -> None:
    manager = PriceHistoryManager(max_history_length=2)
    context: Dict[str, Any] = {}
    symbol = "ETH/USDT"

    def _make_ticker(ts: int, price: float) -> Ticker:
        return {
            "symbol": symbol,
            "timestamp": ts,
            "datetime": f"2023-01-01T00:00:0{ts}Z",
            "last": price,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "bid": price - 0.5,
            "ask": price + 0.5,
            "baseVolume": 1.0,
            "quoteVolume": price,
        }

    # Добавляем три тика при max_history_length=2 — первый должен "выпасть".
    manager.update_history(context, symbol=symbol, ticker=_make_ticker(1, 10.0))
    manager.update_history(context, symbol=symbol, ticker=_make_ticker(2, 20.0))
    manager.update_history(context, symbol=symbol, ticker=_make_ticker(3, 30.0))

    prices = manager.get_price_history(context, symbol)
    tickers = manager.get_ticker_history(context, symbol)

    assert prices == [20.0, 30.0]
    assert [t["last"] for t in tickers] == [20.0, 30.0]


@pytest.mark.unit
def test_get_history_returns_empty_lists_for_unknown_symbol() -> None:
    manager = PriceHistoryManager(max_history_length=2)
    context: Dict[str, Any] = {}

    assert manager.get_price_history(context, "UNKNOWN") == []
    assert manager.get_ticker_history(context, "UNKNOWN") == []

