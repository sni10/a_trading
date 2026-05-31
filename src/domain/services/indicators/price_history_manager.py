"""Управление историей цен и тикеров для расчёта индикаторов.

Класс :class:`PriceHistoryManager` инкапсулирует логику хранения исторических
данных по символам и предоставляет удобный API для добавления и извлечения истории.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any, Deque, Dict

from src.domain.services.ticker.ticker_source import Ticker


class PriceHistoryManager:
    """Менеджер истории цен и тикеров для одного или нескольких символов.

    Хранит две структуры данных:
    * ``price_history`` — история цен (последняя цена из тикера)
    * ``ticker_history`` — история полных тикеров (для объёмных индикаторов)

    Обе истории ограничены по размеру через ``deque(maxlen=...)`` для
    автоматической очистки старых данных.
    """

    def __init__(self, max_history_length: int = 500) -> None:
        """Инициализировать менеджер истории.

        Args:
            max_history_length: Максимальная длина истории для каждого символа.
        """
        self._max_length = max_history_length

    def update_history(
        self,
        context: Dict[str, Any],
        *,
        symbol: str,
        ticker: Ticker,
    ) -> None:
        """Обновить историю цен и тикеров для указанного символа.

        Метод автоматически создаёт структуры данных в контексте, если они
        ещё не существуют, и добавляет новый тикер в историю.

        Args:
            context: Глобальный контекст приложения.
            symbol: Торговая пара (например, "BTC/USDT").
            ticker: Новый тикер для добавления в историю.
        """
        last_price = float(ticker["last"])

        # --- История цен по инструменту (общая для всех индикаторов) ---
        price_history_root: Dict[str, Deque[float]] = context.setdefault(
            "price_history", {}
        )
        history: Deque[float] = price_history_root.setdefault(
            symbol, deque(maxlen=self._max_length)
        )
        history.append(last_price)

        # Также храним историю тикеров – на будущее для объёмных и
        # спред‑зависимых индикаторов.
        ticker_history_root: Dict[str, Deque[Ticker]] = context.setdefault(
            "ticker_history", {}
        )
        ticker_hist: Deque[Ticker] = ticker_history_root.setdefault(
            symbol, deque(maxlen=self._max_length)
        )
        ticker_hist.append(ticker)

    def get_price_history(
        self,
        context: Dict[str, Any],
        symbol: str,
    ) -> Sequence[float]:
        """Получить историю цен для символа в виде последовательности.

        Args:
            context: Глобальный контекст приложения.
            symbol: Торговая пара.

        Returns:
            Список исторических цен (от старых к новым).
            Если история пуста, возвращается пустой список.
        """
        price_history_root = context.get("price_history", {})
        history = price_history_root.get(symbol, deque())
        return list(history)

    def get_ticker_history(
        self,
        context: Dict[str, Any],
        symbol: str,
    ) -> Sequence[Ticker]:
        """Получить историю тикеров для символа.

        Args:
            context: Глобальный контекст приложения.
            symbol: Торговая пара.

        Returns:
            Список исторических тикеров (от старых к новым).
            Если история пуста, возвращается пустой список.
        """
        ticker_history_root = context.get("ticker_history", {})
        history = ticker_history_root.get(symbol, deque())
        return list(history)


__all__ = ["PriceHistoryManager"]
