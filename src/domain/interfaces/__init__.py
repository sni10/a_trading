"""Публичные интерфейсы доменного слоя.

Этот модуль агрегирует наиболее часто используемые протоколы, чтобы
упростить импорты в остальном коде (например,
``from src.domain.interfaces import ILogger``).
"""

from .cache import IIndicatorStore, IMarketCache
from .currency_pair_repository import ICurrencyPairRepository
from .deal_repository import IDealRepository
from .exchange_connector import IExchangeConnector
from .exchange_pair_metadata_provider import (
    IExchangePairMetadataProvider,
    PairPrecisions,
)
from .logger import ILogger
from .order_repository import IOrderRepository
from .state_snapshot_store import IStateSnapshotStore
from .trade_repository import ITradeRepository

__all__ = [
    "ILogger",
    "IMarketCache",
    "IIndicatorStore",
    "ICurrencyPairRepository",
    "IOrderRepository",
    "ITradeRepository",
    "IDealRepository",
    "IExchangeConnector",
    "IExchangePairMetadataProvider",
    "PairPrecisions",
    "IStateSnapshotStore",
]
