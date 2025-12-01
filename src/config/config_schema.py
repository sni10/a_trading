"""Схема конфигурации для прототипа.

Содержит только dataclass :class:`AppConfig` с полями и валидацией.
Логика загрузки из env вынесена в ``config_loader.py``.

Минимальный AppConfig на этом этапе:

* environment – логический режим запуска (local/dev/prod).
* symbol – **одна** торгуемая пара на процесс ("BTC/USDT" и т.п.).
* indicator_*_interval – частота обновления уровней индикаторов в тиках
  (fast/medium/heavy: 1 / 3 / 5 по умолчанию).
* max_ticks, ticker_sleep_sec – параметры демо‑конвейера.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppConfig:
    """Конфигурация раннего прототипа.

    На этом этапе сюда выносятся только действительно необходимые
    параметры. При развитии прототипа класс можно расширять, но
    стараться не тянуть внутрь бизнес‑логику.
    """

    # Общие параметры окружения
    environment: str = "local"

    # Базовые настройки конвейера
    # В раннем прототипе один процесс всегда обслуживает **одну**
    # валютную пару. Поэтому здесь фиксируем одиночный ``symbol``.
    # Поддержка нескольких пар (и связанных списков) будет добавляться
    # отдельно, когда появится полноценный MarketBus.
    symbol: str = "BTC/USDT"
    max_ticks: int = 10
    ticker_sleep_sec: float = 0.2

    # Частота обновления индикаторов (в тиках)
    indicator_fast_interval: int = 1
    indicator_medium_interval: int = 3
    indicator_heavy_interval: int = 5

    # Параметры интеграции с биржевым коннектором
    # (используются только в async‑конвейере и воркерах рынка).
    exchange_id: str = "binance"
    sandbox_mode: bool = False
    order_book_refresh_interval_seconds: float = 5.0

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

        if self.state_snapshot_interval_ticks < 0:
            raise ValueError("state_snapshot_interval_ticks must be >= 0")


__all__ = ["AppConfig"]
