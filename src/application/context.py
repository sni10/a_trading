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
from src.infrastructure.logging.logging_setup import log_stage
from src.infrastructure.repositories import InMemoryCurrencyPairRepository


def build_context(
    config: AppConfig,
    context: Dict[str, Any],
    pair_repository: ICurrencyPairRepository | None = None,
) -> Dict[str, Any]:
    """Создать CurrencyPair и in-memory кэши для активных пар.

    В текущем прототипе один процесс обслуживает **одну** пару из
    :class:`AppConfig` (``config.symbol``).

    Возвращает тот же dict `context`, дополнив его ключами:

    * "pairs" – dict[symbol, CurrencyPair]
    * "market_caches" – dict[symbol, IMarketCache]
    * "indicator_stores" – dict[symbol, IIndicatorStore]
    """

    # Если репозиторий не передан явно (юнит‑тестом или другим
    # use‑case), создаём in-memory реализацию из одиночного символа
    # AppConfig. Тем самым точкой агрегации становится CurrencyPair,
    # а не «сырые» строки символов.
    if pair_repository is None:
        log_stage(
            "BOOT",
            "Создание in-memory репозитория валютных пар по конфигу",
            symbol=config.symbol,
        )
        pair_repository = InMemoryCurrencyPairRepository.from_symbols([config.symbol])

    pairs: Dict[str, CurrencyPair] = {}
    market_caches: Dict[str, IMarketCache] = {}
    indicator_stores: Dict[str, IIndicatorStore] = {}

    log_stage(
        "BOOT",
        "Старт сборки контекста под тиковый конвейер",
        environment=config.environment,
        base_symbol=config.symbol,
    )

    active_pairs = list(pair_repository.list_active())
    log_stage(
        "BOOT",
        "Активные пары, полученные из репозитория",
        pairs=[p.symbol for p in active_pairs],
    )

    for pair in active_pairs:
        symbol = pair.symbol
        pairs[symbol] = pair
        market_caches[symbol] = InMemoryMarketCache(pair)
        indicator_stores[symbol] = InMemoryIndicatorStore(pair, config)

        log_stage(
            "BOOT",
            "Созданы in-memory кэши для пары",
            symbol=symbol,
            bar_window_size=pair.bar_window_size,
            trades_history_size=pair.trades_history_size,
            orderbook_depth=pair.orderbook_depth,
            indicator_window_size=pair.indicator_window_size,
        )

    # Сохраняем построенные структуры в общий dict‑контекст.
    context["pairs"] = pairs
    context["market_caches"] = market_caches
    context["indicator_stores"] = indicator_stores

    # Параллельно кладём сам репозиторий в контекст, чтобы другие
    # сервисы могли получать пары через абстракцию, а не по dict.
    context["pair_repository"] = pair_repository

    log_stage(
        "BOOT",
        "Контекст конвейера собран",
        pairs_count=len(pairs),
        has_market_caches=bool(market_caches),
        has_indicator_stores=bool(indicator_stores),
    )

    return context


__all__ = ["build_context"]
