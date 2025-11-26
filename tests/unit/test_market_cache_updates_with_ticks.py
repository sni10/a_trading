from __future__ import annotations

from typing import Dict, Any

from src.config.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.services.context.state import init_context, update_market_state
from src.infrastructure.cache.in_memory import InMemoryMarketCache


def _build_context_with_cache(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    cfg = AppConfig(symbol=symbol)
    ctx = init_context(cfg)

    pair = CurrencyPair(symbol, symbol.split("/")[0], symbol.split("/")[1])
    cache = InMemoryMarketCache(pair)

    ctx["pairs"] = {symbol: pair}
    ctx["market_caches"] = {symbol: cache}
    return ctx


def test_update_market_state_updates_plain_market_section() -> None:
    ctx = _build_context_with_cache("BTC/USDT")

    update_market_state(ctx, symbol="BTC/USDT", price=123.45, ts=1111111111)

    assert "BTC/USDT" in ctx["market"]
    market_view = ctx["market"]["BTC/USDT"]
    assert market_view["last_price"] == 123.45
    assert market_view["ts"] == 1111111111


def test_update_market_state_updates_inmemory_market_cache_ticker() -> None:
    ctx = _build_context_with_cache("ETH/USDT")

    update_market_state(ctx, symbol="ETH/USDT", price=200.0, ts=2222222222)

    cache = ctx["market_caches"]["ETH/USDT"]
    stored = cache.get_ticker()

    assert stored is not None
    assert stored["symbol"] == "ETH/USDT"
    assert stored["last"] == 200.0
    assert stored["timestamp"] == 2222222222
