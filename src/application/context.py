"""Высокоуровневая сборка контекста под тиковый конвейер.

На этом этапе мы не переписываем существующий dict‑контекст, а
"обогащаем" его сущностями CurrencyPair и in-memory кэшами.

Используем только мок‑данные/структуры:

* символы берём из AppConfig;
* базовая/котируемая валюта для пары – простое разбиение "BTC/USDT";
* форма кэша ориентирована на структуры ccxt (см. doc/ccxt_data_structures.md
  и doc/EXCHANGE_INTEGRATION.md).
"""

from __future__ import annotations

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.cache import IIndicatorStore, IMarketCache
from src.infrastructure.cache.in_memory import (
    InMemoryIndicatorStore,
    InMemoryMarketCache,
)


def build_context(config: AppConfig, context: Dict[str, Any]) -> Dict[str, Any]:
    """Создать CurrencyPair и in-memory кэши для всех символов.

    Возвращает тот же dict `context`, дополнив его ключами:

    * "pairs" – dict[symbol, CurrencyPair]
    * "market_caches" – dict[symbol, IMarketCache]
    * "indicator_stores" – dict[symbol, IIndicatorStore]
    """

    pairs: Dict[str, CurrencyPair] = {}
    market_caches: Dict[str, IMarketCache] = {}
    indicator_stores: Dict[str, IIndicatorStore] = {}

    for symbol in config.symbols:
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
        else:
            # Фолбэк на случай нестандартного символа
            base, quote = symbol, "USDT"

        pair = CurrencyPair(symbol=symbol, base_currency=base, quote_currency=quote)
        pairs[symbol] = pair
        market_caches[symbol] = InMemoryMarketCache(pair)
        indicator_stores[symbol] = InMemoryIndicatorStore(pair, config)

    context["pairs"] = pairs
    context["market_caches"] = market_caches
    context["indicator_stores"] = indicator_stores

    return context


__all__ = ["build_context"]
