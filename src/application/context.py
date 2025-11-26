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
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.infrastructure.cache.in_memory import (
    InMemoryIndicatorStore,
    InMemoryMarketCache,
)
from src.infrastructure.repositories import InMemoryCurrencyPairRepository


def build_context(
    config: AppConfig,
    context: Dict[str, Any],
    pair_repository: ICurrencyPairRepository | None = None,
) -> Dict[str, Any]:
    """Создать CurrencyPair и in-memory кэши для всех активных пар.

    Возвращает тот же dict `context`, дополнив его ключами:

    * "pairs" – dict[symbol, CurrencyPair]
    * "market_caches" – dict[symbol, IMarketCache]
    * "indicator_stores" – dict[symbol, IIndicatorStore]
    """

    # Если репозиторий не передан явно (юнит‑тестом или другим
    # use‑case), создаём in-memory реализацию из списка символов
    # AppConfig. Тем самым точкой агрегации становится CurrencyPair,
    # а не «сырые» строки символов.
    if pair_repository is None:
        pair_repository = InMemoryCurrencyPairRepository.from_symbols(config.symbols)

    pairs: Dict[str, CurrencyPair] = {}
    market_caches: Dict[str, IMarketCache] = {}
    indicator_stores: Dict[str, IIndicatorStore] = {}

    for pair in pair_repository.list_active():
        symbol = pair.symbol
        pairs[symbol] = pair
        market_caches[symbol] = InMemoryMarketCache(pair)
        indicator_stores[symbol] = InMemoryIndicatorStore(pair, config)

    # Сохраняем построенные структуры в общий dict‑контекст.
    context["pairs"] = pairs
    context["market_caches"] = market_caches
    context["indicator_stores"] = indicator_stores

    # Параллельно кладём сам репозиторий в контекст, чтобы другие
    # сервисы могли получать пары через абстракцию, а не по dict.
    context["pair_repository"] = pair_repository

    return context


__all__ = ["build_context"]
