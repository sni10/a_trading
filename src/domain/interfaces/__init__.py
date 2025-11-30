"""Публичные интерфейсы доменного слоя.

Этот модуль агрегирует наиболее часто используемые протоколы, чтобы
упростить импорты в остальном коде (например,
``from src.domain.interfaces import ILogger``).
"""

from .cache import IIndicatorStore, IMarketCache
from .currency_pair_repository import ICurrencyPairRepository
from .exchange_pair_metadata_provider import (
    IExchangePairMetadataProvider,
    PairPrecisions,
)
from .logger import ILogger
from .state_snapshot_store import IStateSnapshotStore

__all__ = [
    "ILogger",
    "IMarketCache",
    "IIndicatorStore",
    "ICurrencyPairRepository",
    "IExchangePairMetadataProvider",
    "PairPrecisions",
    "IStateSnapshotStore",
]
