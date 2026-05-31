"""Источник исторических тиков для бэктеста.

Преобразует OHLCV-свечи в поток доменных тик-словарей, совместимых
с форматом, ожидаемым TickPipelineService.process_tick().

Допущение (bar-vs-tick): close-цена свечи используется как «last» тика.
Это упрощение достаточно для проверки логики стратегии, но не для
точного прогноза доходности.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class HistoricalTickSource:
    """Генератор тиков из списка OHLCV-свечей.

    Каждая свеча превращается в один тик:
    ``last = close``, ``ts = timestamp_ms`` свечи.
    """

    def __init__(
        self,
        candles: list[list],
        symbol: str,
        until_ms: int | None = None,
    ) -> None:
        """
        Args:
            candles: Список свечей [[ts_ms, open, high, low, close, volume], ...].
            symbol: Торговая пара.
            until_ms: Ограничение по времени (включительно); None = все свечи.
        """
        self._candles = candles
        self._symbol = symbol
        self._until_ms = until_ms

    def __len__(self) -> int:
        """Число свечей с учётом фильтра until_ms."""
        if self._until_ms is None:
            return len(self._candles)
        return sum(1 for c in self._candles if c[0] <= self._until_ms)

    def stream(self) -> Iterator[dict[str, Any]]:
        """Итератор тиков из свечей в хронологическом порядке.

        Yields:
            dict с полями: symbol, last, ts.
        """
        for candle in self._candles:
            ts_ms: int = int(candle[0])
            close: float = float(candle[4])

            if self._until_ms is not None and ts_ms > self._until_ms:
                break

            yield {
                "symbol": self._symbol,
                "last": close,
                "ts": ts_ms,
            }


__all__ = ["HistoricalTickSource"]
