from __future__ import annotations

from typing import Dict, Any

from src.config.config import AppConfig
from src.domain.services.context.state import init_context
from src.domain.entities.currency_pair import CurrencyPair
from src.infrastructure.cache.in_memory import InMemoryMarketCache
from src.domain.services.market_data.orderflow_simulator import (
    update_orderflow_from_tick,
)


def _build_context_with_cache(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    cfg = AppConfig(symbol=symbol)
    ctx = init_context(cfg)

    pair = CurrencyPair(symbol, symbol.split("/")[0], symbol.split("/")[1])
    cache = InMemoryMarketCache(pair)

    ctx["pairs"] = {symbol: pair}
    ctx["market_caches"] = {symbol: cache}
    return ctx


def test_tick_sequence_fills_trades_history_until_window_limit_via_orderflow_simulator() -> None:
    symbol = "BTC/USDT"
    ctx = _build_context_with_cache(symbol)

    cache: InMemoryMarketCache = ctx["market_caches"][symbol]

    # sanity: окно trades ограничено параметром пары
    window_size = cache.pair.trades_history_size

    # прокручиваем окно + несколько тиков поверх
    total_ticks = window_size + 5
    for i in range(total_ticks):
        price = 100.0 + i
        ts = 1_000_000_000 + i
        update_orderflow_from_tick(ctx, symbol=symbol, price=price, ts=ts)

    trades = cache.get_trades()

    # к моменту total_ticks trades должны быть ограничены window_size
    assert len(trades) == window_size

    # и содержать последние window_size элементов последовательности
    # (старые трейды вытеснены deque.maxlen внутри InMemoryMarketCache)
    expected_first_price = 100.0 + (total_ticks - window_size)
    assert trades[0]["price"] == expected_first_price
    assert trades[-1]["price"] == 100.0 + total_ticks - 1
