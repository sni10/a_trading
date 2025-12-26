"""Схема конфигурации для прототипа.

Содержит только dataclass :class:`AppConfig` с полями и валидацией.
Логика загрузки из env вынесена в ``config_loader.py``.

Минимальный AppConfig на этом этапе:

* environment – логический режим запуска (local/dev/prod).
* symbol – **одна** торгуемая пара на процесс ("BTC/USDT" и т.п.).
* indicator_*_interval – частота обновления уровней индикаторов в тиках
  (fast/medium/heavy: 1 / 3 / 5 по умолчанию).
* max_ticks, ticker_sleep_sec – параметры демо‑конвейера.
* trading – настройки торговых параметров
* cache – настройки кэша рыночных данных
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class CacheConfig:
    """Настройки кэша рыночных данных.

    Определяет размеры буферов для различных типов данных:
    стакан заявок, история трейдов, бары OHLCV, индикаторы.

    Общий лимит ~2MB на символ.
    """

    # Таймфрейм для баров OHLCV
    bar_timeframe: Literal["1m", "5m"] = "1m"

    # Количество баров в истории (10000 = ~1MB)
    bar_window_size: int = 10000

    # Глубина стакана заявок в уровнях (2000 = ~200KB)
    orderbook_depth: int = 2000

    # Размер истории трейдов (5000 = ~500KB)
    trades_history_size: int = 5000

    # Размер окна для всех индикаторов (10000 = ~1-1.5MB)
    indicator_window_size: int = 10000

    def validate(self) -> None:
        """Валидация параметров кэша."""
        if self.bar_window_size < 100:
            raise ValueError("bar_window_size must be >= 100")

        if self.orderbook_depth < 10:
            raise ValueError("orderbook_depth must be >= 10")

        if self.trades_history_size < 100:
            raise ValueError("trades_history_size must be >= 100")

        if self.indicator_window_size < 100:
            raise ValueError("indicator_window_size must be >= 100")

    def estimate_total_size_mb(self) -> float:
        """Оценить общий размер кэша в MB."""
        # Оценки размера на элемент (в байтах):
        ORDERBOOK_LEVEL_SIZE = 100  # bid/ask уровень
        TRADE_SIZE = 100  # один трейд
        BAR_SIZE = 100  # один OHLCV бар
        INDICATOR_VALUE_SIZE = 50  # одно значение индикатора

        orderbook_mb = (self.orderbook_depth * 2 * ORDERBOOK_LEVEL_SIZE) / 1024 / 1024
        trades_mb = (self.trades_history_size * TRADE_SIZE) / 1024 / 1024
        bars_mb = (self.bar_window_size * BAR_SIZE) / 1024 / 1024

        # Индикаторы: 3 кэша (fast, medium, heavy), ~5 индикаторов в каждом
        indicators_per_cache = 5
        num_caches = 3
        indicators_mb = (
            self.indicator_window_size
            * indicators_per_cache
            * num_caches
            * INDICATOR_VALUE_SIZE
        ) / 1024 / 1024

        return orderbook_mb + trades_mb + bars_mb + indicators_mb


@dataclass
class DatabaseConfig:
    """Настройки подключения к БД.

    В прототипе поддерживаются 2 backend'а:
    - SQLite (локальный файл)
    - PostgreSQL (строка подключения)

    ВАЖНО: доступ к БД — только через SQLAlchemy (ORM/expressions).
    """

    database_type: Literal["sqlite", "postgresql"] = "sqlite"
    database_path: str = "data/deviant.db"
    database_url: str | None = None
    database_schema: str | None = None  # PostgreSQL schema (default: public)

    def validate(self) -> None:
        """Fail-fast валидация DB-конфига."""

        if self.database_type not in ("sqlite", "postgresql"):
            raise ValueError("DATABASE_TYPE must be 'sqlite' or 'postgresql'")

        if self.database_type == "sqlite":
            if not self.database_path:
                raise ValueError("DATABASE_PATH must be non-empty for sqlite")

        if self.database_type == "postgresql":
            if not self.database_url:
                raise ValueError("DATABASE_URL is required for postgresql")
            if not self.database_url.startswith("postgresql://"):
                raise ValueError("DATABASE_URL must start with 'postgresql://' for postgresql")


@dataclass
class AppConfig:
    """Конфигурация раннего прототипа.

    Содержит только ГЛОБАЛЬНЫЕ настройки приложения.

    Параметры торговли (deal_quota, profit_markup и т.д.) и symbol
    находятся в CurrencyPair entity и загружаются из БД.
    """

    # Общие параметры окружения
    environment: str = "local"

    # Базовые настройки конвейера
    max_ticks: int = 10
    ticker_sleep_sec: float = 0.2

    # Частота обновления индикаторов (в тиках)
    # Применяются ко ВСЕМ торгуемым парам
    indicator_fast_interval: int = 1
    indicator_medium_interval: int = 3
    indicator_heavy_interval: int = 5

    # Параметры интеграции с биржевым коннектором
    exchange_id: str = "binance"
    sandbox_mode: bool = False
    order_book_refresh_interval_seconds: float = 5.0
    buy_order_timeout_sec: float = 30.0

    # API‑ключи биржи. На раннем этапе они опциональны: если заданы,
    # коннектор будет аутентифицироваться и сможет работать с приватными
    # методами. Для получения только публичных данных (тикер/стакан)
    # поля могут оставаться пустыми.
    #
    # Источники значений:
    # * прямые переменные окружения ``EXCHANGE_API_KEY`` /
    #   ``EXCHANGE_API_SECRET``;
    # * либо пути к файлам с ключами через
    #   ``EXCHANGE_API_KEY_FILE`` / ``EXCHANGE_API_SECRET_FILE`` –
    #   содержимое файла читается целиком и используется как значение
    #   ключа. Это позволяет хранить секреты в ``secure_api_keys``.
    exchange_api_key: str | None = None
    exchange_api_secret: str | None = None

    # Интервал между файловыми снапшотами state в тиках. Значение 0
    # отключает периодическое сохранение снапшотов.
    state_snapshot_interval_ticks: int = 100

    # Настройки кэша рыночных данных (ГЛОБАЛЬНО для всех пар)
    cache: CacheConfig = None  # type: ignore

    # Настройки БД (ГЛОБАЛЬНО для приложения)
    database: DatabaseConfig = None  # type: ignore

    def __post_init__(self):
        """Инициализация вложенных конфигов."""
        if self.cache is None:
            self.cache = CacheConfig()

        if self.database is None:
            self.database = DatabaseConfig()

    def validate(self) -> None:
        """Проверить базовые инварианты конфига.

        Вызывается один раз при старте. При нарушении инвариантов
        выбрасывает ValueError (fail‑fast), чтобы не запускать конвейер
        с некорректными настройками.
        """

        if self.indicator_fast_interval < 1:
            raise ValueError("indicator_fast_interval must be >= 1")

        if self.indicator_medium_interval < 1:
            raise ValueError("indicator_medium_interval must be >= 1")

        if self.indicator_heavy_interval < 1:
            raise ValueError("indicator_heavy_interval must be >= 1")

        if self.indicator_medium_interval < self.indicator_fast_interval:
            raise ValueError(
                "indicator_medium_interval must be >= indicator_fast_interval"
            )

        if self.indicator_heavy_interval < self.indicator_medium_interval:
            raise ValueError(
                "indicator_heavy_interval must be >= indicator_medium_interval"
            )

        if self.max_ticks <= 0:
            raise ValueError("max_ticks must be > 0")

        if self.ticker_sleep_sec < 0:
            raise ValueError("ticker_sleep_sec must be >= 0")

        if self.order_book_refresh_interval_seconds <= 0:
            raise ValueError("order_book_refresh_interval_seconds must be > 0")

        if self.buy_order_timeout_sec < 0:
            raise ValueError("buy_order_timeout_sec must be >= 0")

        if self.state_snapshot_interval_ticks < 0:
            raise ValueError("state_snapshot_interval_ticks must be >= 0")

        # Валидация вложенных конфигов
        self.cache.validate()

        self.database.validate()


__all__ = ["AppConfig", "CacheConfig", "DatabaseConfig"]
