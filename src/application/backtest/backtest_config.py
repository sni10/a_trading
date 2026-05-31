"""Конфигурация офлайн-бэктеста."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BacktestConfig:
    """Параметры прогона бэктеста.

    Attributes:
        symbol: Торговая пара (например 'BTC/USDT').
        timeframe: Таймфрейм OHLCV-свечей (например '1h').
        since_ms: Начало периода — Unix timestamp в миллисекундах.
        until_ms: Конец периода — Unix timestamp в мс (None = до конца доступных данных).
        initial_balance: Стартовый баланс в котируемой валюте (USDT).
        buy_fee_percent: Комиссия на покупку, % (например 0.1 = 0.1%).
        sell_fee_percent: Комиссия на продажу, % (например 0.1 = 0.1%).
        cache_dir: Директория для кэша OHLCV-данных.
        use_cache: Использовать кэш на диске (True = не скачивать повторно).
    """

    symbol: str
    timeframe: str
    since_ms: int
    until_ms: int | None = None
    initial_balance: float = 1000.0
    buy_fee_percent: float = 0.1
    sell_fee_percent: float = 0.1
    cache_dir: str = "data/ohlcv_cache"
    use_cache: bool = True

    def validate(self) -> None:
        """Проверить корректность параметров. Выбрасывает ValueError при ошибке."""
        if not self.symbol:
            raise ValueError("symbol не может быть пустым")
        if not self.timeframe:
            raise ValueError("timeframe не может быть пустым")
        if self.since_ms <= 0:
            raise ValueError("since_ms должен быть положительным Unix timestamp в мс")
        if self.until_ms is not None and self.until_ms <= self.since_ms:
            raise ValueError("until_ms должен быть > since_ms")
        if self.initial_balance <= 0:
            raise ValueError("initial_balance должен быть > 0")
        if self.buy_fee_percent < 0:
            raise ValueError("buy_fee_percent не может быть отрицательным")
        if self.sell_fee_percent < 0:
            raise ValueError("sell_fee_percent не может быть отрицательным")


__all__ = ["BacktestConfig"]
