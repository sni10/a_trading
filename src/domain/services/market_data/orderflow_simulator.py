"""Симуляция стакана и трейдов поверх тиков.

На этом этапе прототипа реального коннектора к бирже ещё нет, поэтому
по каждому тику мы синтетически формируем:

* срез стакана (order book) в форме, совместимой с ccxt `fetch_order_book()`;
* одну упрощённую сделку (trade) в формате ccxt‑подобного dict;
* опционально — простой бар OHLCV на основе цены тика.

Все данные пишутся в :class:`IMarketCache`, чтобы позже можно было
прозрачно заменить эту симуляцию реальным поставщиком рыночных данных
или вынести хранение из памяти в Redis/БД.
"""

from __future__ import annotations

from typing import Any, Dict

from src.domain.interfaces.cache import IMarketCache
from src.infrastructure.logging.logging_setup import log_stage


def update_orderflow_from_tick(
    context: Dict[str, Any], *, symbol: str, price: float, ts: int
) -> None:
    """Обновить стакан, трейды и (опционально) бар по тику.

    Контракт симуляции:

    * читает из ``context["market_caches"][symbol]`` объект
      :class:`IMarketCache` и, если он есть, вызывает на нём:
        - ``update_orderbook(orderbook_dict)``;
        - ``add_trade(trade_dict)``;
        - ``add_bar(bar_dict)`` (упрощённый OHLCV‑бар на один тик).
    * структура dict'ов максимально приближена к примерам из
      ``doc/ccxt_data_structures.md`` (``fetch_order_book()`` и trades);
    * количество уровней стакана ограничивается настройками пары
      (``CurrencyPair.orderbook_depth``) через реализацию
      :class:`InMemoryMarketCache`.

    В реальной системе эта функция будет заменена коннектором к бирже
    или внешнему поставщику ордерфлоу, но контракт для бизнес‑кода
    останется прежним.
    """

    caches = context.get("market_caches") or {}
    cache = caches.get(symbol)
    if not isinstance(cache, IMarketCache):
        return

    pairs = context.get("pairs") or {}
    pair = pairs.get(symbol)

    # Ограничиваемся небольшим количеством уровней для симуляции, реальный
    # depth всё равно нарежет InMemoryMarketCache.update_orderbook().
    max_levels = 10
    depth = getattr(pair, "orderbook_depth", max_levels)
    levels = min(depth, max_levels)

    spread = max(price * 0.0005, 0.01)  # минимальный спред ~0.01
    bids = []
    asks = []
    for i in range(levels):
        # Чем дальше от mid, тем хуже цена и больше объём
        bid_price = price - spread * (i + 1)
        ask_price = price + spread * (i + 1)
        volume = 1.0 + i
        bids.append([round(bid_price, 2), volume])
        asks.append([round(ask_price, 2), volume])

    orderbook = {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "timestamp": ts,
    }
    cache.update_orderbook(orderbook)

    # Один упрощённый trade на тик: сделка по текущей цене.
    trade = {
        "symbol": symbol,
        "price": float(price),
        "amount": 1.0,
        "timestamp": ts,
        # Минимальный набор полей под формат ccxt; при замене
        # провайдера сюда можно будет подставить реальные id/side и т.п.
    }
    cache.add_trade(trade)

    # Простейший бар OHLCV: один тик == один бар.
    bar = {
        "symbol": symbol,
        "timestamp": ts,
        "open": float(price),
        "high": float(price),
        "low": float(price),
        "close": float(price),
        "volume": 1.0,
    }
    cache.add_bar(bar)

    log_stage(
        "FEEDS",
        "Симуляция стакана, трейда и бара по тику",
        symbol=symbol,
        price=price,
        ts=ts,
        levels=levels,
    )


__all__ = ["update_orderflow_from_tick"]
