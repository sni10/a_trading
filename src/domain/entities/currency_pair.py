"""CurrencyPair entity with trading and cache settings."""

import time
from typing import Literal


class CurrencyPair:
    """Валютная пара с настройками торговли и кеширования.

    Содержит:
    - Торговые настройки (из bad_example config.json)
    - Настройки кеша рыночных данных (стакан, трейды, бары)
    - Технические параметры биржи (шаги цены и количества)
    """

    def __init__(
        self,
        symbol: str,
        base_currency: str,
        quote_currency: str,
        # Trading settings (from bad_example)
        deal_quota: float = 25.0,
        profit_markup: float = 1.5,
        deal_count: int = 3,
        order_life_time: int = 1,
        # Exchange technical params
        min_step: float = 0.0001,
        price_step: float = 0.01,
        # Cache settings (новые, под лимит ~2MB на символ)
        bar_timeframe: Literal["1m", "5m"] = "1m",
        bar_window_size: int = 10000,
        orderbook_depth: int = 2000,
        trades_history_size: int = 5000,
        indicator_window_size: int = 10000,
        # Meta
        enabled: bool = True,
        pair_id: int | None = None,
        created_at: int | None = None,
        updated_at: int | None = None,
    ):
        """Создать валютную пару с настройками.

        Args:
            symbol: Символ пары на бирже (например "BTC/USDT")
            base_currency: Базовая валюта (например "BTC")
            quote_currency: Котируемая валюта (например "USDT")

            # Trading settings:
            deal_quota: Размер сделки в quote валюте (например 25.0 USDT)
            profit_markup: Желаемый профит в % (например 1.5 = 1.5%)
            deal_count: Макс. количество одновременно открытых сделок
            order_life_time: Время жизни ордера в минутах до отмены

            # Exchange params:
            min_step: Минимальный шаг количества (lot size step)
            price_step: Минимальный шаг цены (tick size)

            # Cache settings (под лимит ~2MB на символ):
            bar_timeframe: Таймфрейм баров ("1m" или "5m")
            bar_window_size: Кол-во баров в истории (10000 = ~1MB)
            orderbook_depth: Глубина стакана в уровнях (2000 = ~200KB)
            trades_history_size: Кол-во последних трейдов (5000 = ~500KB)
            indicator_window_size: Размер окна для всех индикаторов (10000 = ~1-1.5MB)

            # Meta:
            enabled: Активна ли пара для торговли
            pair_id: ID в БД (если загружено из БД)
            created_at: Timestamp создания (ms)
            updated_at: Timestamp последнего обновления (ms)
        """
        # Core
        self.pair_id = pair_id
        self.symbol = symbol
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.enabled = enabled

        # Trading settings
        self.deal_quota = deal_quota
        self.profit_markup = profit_markup
        self.deal_count = deal_count
        self.order_life_time = order_life_time

        # Exchange params
        self.min_step = min_step
        self.price_step = price_step

        # Cache settings
        self.bar_timeframe = bar_timeframe
        self.bar_window_size = bar_window_size
        self.orderbook_depth = orderbook_depth
        self.trades_history_size = trades_history_size
        self.indicator_window_size = indicator_window_size

        # Timestamps
        self.created_at = created_at or int(time.time() * 1000)
        self.updated_at = updated_at or int(time.time() * 1000)

    def estimate_cache_size_mb(self) -> float:
        """Оценить размер кеша в памяти для этой пары.

        Returns:
            Размер в MB (приблизительная оценка)
        """
        # Оценки на один элемент:
        # - 1 уровень стакана: ~100 байт
        # - 1 трейд: ~100 байт
        # - 1 бар OHLCV: ~100 байт
        # - 1 значение индикатора: ~50 байт (float + metadata)

        orderbook_mb = (self.orderbook_depth * 2 * 100) / 1024 / 1024  # bid + ask
        trades_mb = (self.trades_history_size * 100) / 1024 / 1024
        bars_mb = (self.bar_window_size * 100) / 1024 / 1024

        # Индикаторы: 3 кеша (fast, medium, heavy), каждый ~5 индикаторов
        # Все используют одинаковый indicator_window_size
        indicators_per_cache = 5  # примерная оценка
        num_caches = 3  # fast, medium, heavy
        indicators_mb = (
            self.indicator_window_size * indicators_per_cache * num_caches * 50
        ) / 1024 / 1024

        return orderbook_mb + trades_mb + bars_mb + indicators_mb

    def __repr__(self) -> str:
        cache_mb = self.estimate_cache_size_mb()
        return (
            f"<CurrencyPair(symbol={self.symbol}, "
            f"deal_quota={self.deal_quota}, "
            f"profit_markup={self.profit_markup}%, "
            f"deal_count={self.deal_count}, "
            f"cache≈{cache_mb:.2f}MB)>"
        )

    def to_dict(self) -> dict:
        """Сериализовать в dict для БД."""
        return {
            "pair_id": self.pair_id,
            "symbol": self.symbol,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "enabled": self.enabled,
            # Trading
            "deal_quota": self.deal_quota,
            "profit_markup": self.profit_markup,
            "deal_count": self.deal_count,
            "order_life_time": self.order_life_time,
            # Exchange
            "min_step": self.min_step,
            "price_step": self.price_step,
            # Cache
            "bar_timeframe": self.bar_timeframe,
            "bar_window_size": self.bar_window_size,
            "orderbook_depth": self.orderbook_depth,
            "trades_history_size": self.trades_history_size,
            "indicator_window_size": self.indicator_window_size,
            # Meta
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CurrencyPair":
        """Десериализовать из dict (из БД)."""
        return cls(**data)
