"""Быстрые индикаторы (FAST layer) для расчёта на каждом тике.

Модуль содержит чистые функции для расчёта быстрых индикаторов:
* SMA-5, SMA-7, SMA-25 (простые скользящие средние)
* Spread и mid-price (на основе bid/ask из тикера)

Все функции — pure functions без side effects, работают с иммутабельными данными.
"""

from __future__ import annotations

from typing import Any

from src.domain.services.ticker.ticker_source import Ticker


def _sma(values: list[float]) -> float:
    """Простейшая скользящая средняя по списку значений.

    Предполагается, что ``values`` не пустой (контролируется вызывающим
    кодом через длину history).
    """
    return sum(values) / len(values)


def calculate_sma_fast_5(
    history_list: list[float],
    fast_window: int = 5,
) -> float | None:
    """Демо-индикатор: SMA по последним N тикам (по умолчанию 5).

    Args:
        history_list: История цен (от старых к новым).
        fast_window: Размер окна для расчёта SMA.

    Returns:
        Значение SMA или None, если недостаточно истории.
    """
    n = len(history_list)
    if n >= fast_window:
        return _sma(history_list[-fast_window:])
    return None


def calculate_sma_7(history_list: list[float]) -> float | None:
    """Реальный индикатор: SMA-7 по истории цен.

    Из старого проекта (bad_example/indicator_calculator_service.py).

    Args:
        history_list: История цен.

    Returns:
        Значение SMA-7 или None, если недостаточно истории.
    """
    n = len(history_list)
    if n >= 7:
        return _sma(history_list[-7:])
    # Для n < 7 всё равно считаем, если есть хоть одна цена
    if n >= 1:
        return _sma(history_list[-n:])
    return None


def calculate_sma_25(history_list: list[float]) -> float | None:
    """Реальный индикатор: SMA-25 по истории цен.

    Из старого проекта (bad_example/indicator_calculator_service.py).

    Args:
        history_list: История цен.

    Returns:
        Значение SMA-25 или None, если недостаточно истории.
    """
    n = len(history_list)
    if n >= 25:
        return _sma(history_list[-25:])
    return None


def calculate_spread_and_mid(
    ticker: Ticker,
    last_price: float,
) -> dict[str, float]:
    """Расчёт спреда bid-ask и средней цены (mid-price).

    Args:
        ticker: Тикер с полями bid и ask.
        last_price: Последняя цена (fallback для mid, если bid/ask недоступны).

    Returns:
        Словарь с ключами 'spread' и 'mid_price'.
    """
    bid = float(ticker["bid"])
    ask = float(ticker["ask"])
    spread = max(0.0, ask - bid)
    mid = (ask + bid) / 2.0 if ask and bid else last_price

    return {"spread": spread, "mid_price": mid}


def calculate_fast_indicators(
    ticker: Ticker,
    history_list: list[float],
    fast_window: int = 5,
) -> dict[str, Any]:
    """Расчёт всех быстрых индикаторов (FAST layer).

    Главная функция-оркестратор для быстрых индикаторов. Вычисляет:
    * sma_fast_5 (демо)
    * sma_7 (реальный)
    * sma_25 (реальный)
    * spread
    * mid_price

    Args:
        ticker: Тикер с ценами bid/ask/last.
        history_list: История цен.
        fast_window: Размер окна для демо-индикатора sma_fast_5.

    Returns:
        Словарь с вычисленными индикаторами (только те, для которых
        достаточно истории).
    """
    indicators: dict[str, Any] = {}
    last_price = float(ticker["last"])

    # Демо-индикатор SMA-5
    sma_fast_5 = calculate_sma_fast_5(history_list, fast_window)
    if sma_fast_5 is not None:
        indicators["sma_fast_5"] = sma_fast_5

    # Реальные индикаторы SMA-7 и SMA-25
    sma_7 = calculate_sma_7(history_list)
    if sma_7 is not None:
        indicators["sma_7"] = sma_7

    sma_25 = calculate_sma_25(history_list)
    if sma_25 is not None:
        indicators["sma_25"] = sma_25

    # Спред и mid-price
    spread_mid = calculate_spread_and_mid(ticker, last_price)
    indicators.update(spread_mid)

    return indicators


__all__ = [
    "calculate_fast_indicators",
    "calculate_sma_fast_5",
    "calculate_sma_7",
    "calculate_sma_25",
    "calculate_spread_and_mid",
]
