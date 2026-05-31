"""Дисковый кэш OHLCV-свечей для бэктеста.

Свечи хранятся в JSON-файлах в директории cache_dir.
Имя файла кодирует символ, таймфрейм и временной диапазон.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


class OhlcvCache:
    """Кэш OHLCV-данных на диске.

    Позволяет не обращаться к бирже при повторных прогонах бэктеста
    на одних и тех же данных.
    """

    def __init__(self, cache_dir: str = "data/ohlcv_cache") -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _make_filename(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
    ) -> Path:
        """Сформировать путь к файлу кэша."""
        safe_symbol = re.sub(r"[^A-Za-z0-9]", "_", symbol)
        since_str = str(since_ms) if since_ms is not None else "none"
        name = f"{safe_symbol}_{timeframe}_{since_str}.json"
        return self._dir / name

    def load(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
    ) -> list[list] | None:
        """Загрузить свечи из кэша.

        Returns:
            Список свечей или None, если кэш отсутствует.
        """
        path = self._make_filename(symbol, timeframe, since_ms)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def save(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
        candles: list[list],
    ) -> None:
        """Сохранить свечи в кэш."""
        path = self._make_filename(symbol, timeframe, since_ms)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(candles, fh)


__all__ = ["OhlcvCache"]
