"""Средние индикаторы (MEDIUM layer) для расчёта с умеренной частотой.

Модуль содержит функции для расчёта средних индикаторов:
* SMA-20 (простая скользящая средняя)
* RSI-5, RSI-15 (Relative Strength Index через TA-Lib)

Индикаторы используют TA-Lib для расчётов, если библиотека доступна.
При ошибках используется логирование через ILogger.
"""

from __future__ import annotations

from typing import Any

from src.domain.interfaces.logger import ILogger

# Опциональные зависимости numpy/talib
try:  # pragma: no cover - окружения без numpy/talib
    import numpy as _np  # type: ignore[import]
    import talib as _talib  # type: ignore[import]
except Exception:  # pragma: no cover - защитный импорт
    _np = None  # type: ignore[assignment]
    _talib = None  # type: ignore[assignment]


def _sma(values: list[float]) -> float:
    """Простейшая скользящая средняя по списку значений.

    Предполагается, что ``values`` не пустой (контролируется вызывающим
    кодом через длину history).
    """
    return sum(values) / len(values)


def calculate_sma_medium_20(
    history_list: list[float],
    medium_window: int = 20,
) -> float | None:
    """Демо-индикатор: SMA по последним N тикам (по умолчанию 20).

    Args:
        history_list: История цен (от старых к новым).
        medium_window: Размер окна для расчёта SMA.

    Returns:
        Значение SMA или None, если недостаточно истории.
    """
    n = len(history_list)
    if n >= medium_window:
        return _sma(history_list[-medium_window:])
    return None


def calculate_rsi_indicators(
    history_list: list[float],
    logger: ILogger | None = None,
) -> dict[str, float]:
    """Расчёт индикаторов RSI-5 и RSI-15 через TA-Lib.

    Реальные индикаторы из старого проекта (bad_example).
    Требует numpy и talib. При ошибках логирует через ILogger.

    Args:
        history_list: История цен (минимум 30 значений для корректного расчёта).
        logger: Опциональный логгер для записи ошибок.

    Returns:
        Словарь с ключами 'rsi_5' и/или 'rsi_15' (если удалось вычислить).
        Если библиотеки недоступны или истории недостаточно — пустой словарь.
    """
    indicators: dict[str, float] = {}
    n = len(history_list)

    # Проверка доступности библиотек и достаточности истории
    if _np is None or _talib is None or n < 30:
        return indicators

    try:
        closes = _np.array(history_list[-30:], dtype="float64")  # type: ignore[arg-type]

        rsi_5 = _talib.RSI(closes, timeperiod=5)  # type: ignore[call-arg]
        rsi_15 = _talib.RSI(closes, timeperiod=15)  # type: ignore[call-arg]

        if len(rsi_5) > 0 and not _np.isnan(rsi_5[-1]):
            indicators["rsi_5"] = round(float(rsi_5[-1]), 8)
        if len(rsi_15) > 0 and not _np.isnan(rsi_15[-1]):
            indicators["rsi_15"] = round(float(rsi_15[-1]), 8)
    except Exception as exc:  # pragma: no cover - защитный путь
        if logger:
            logger.log_warning(
                f"⚠️ [WARN] Ошибка при расчёте RSI через ta-lib | error: {exc}"
            )

    return indicators


def calculate_medium_indicators(
    history_list: list[float],
    medium_window: int = 20,
    logger: ILogger | None = None,
) -> dict[str, Any]:
    """Расчёт всех средних индикаторов (MEDIUM layer).

    Главная функция-оркестратор для средних индикаторов. Вычисляет:
    * sma_medium_20 (демо)
    * rsi_5 (реальный)
    * rsi_15 (реальный)

    Args:
        history_list: История цен.
        medium_window: Размер окна для демо-индикатора sma_medium_20.
        logger: Опциональный логгер для записи ошибок при расчёте RSI.

    Returns:
        Словарь с вычисленными индикаторами (только те, для которых
        достаточно истории и доступны библиотеки).
    """
    indicators: dict[str, Any] = {}

    # Демо-индикатор SMA-20
    sma_medium_20 = calculate_sma_medium_20(history_list, medium_window)
    if sma_medium_20 is not None:
        indicators["sma_medium_20"] = sma_medium_20

    # Реальные индикаторы RSI-5 и RSI-15
    rsi_indicators = calculate_rsi_indicators(history_list, logger=logger)
    indicators.update(rsi_indicators)

    return indicators


__all__ = [
    "calculate_medium_indicators",
    "calculate_sma_medium_20",
    "calculate_rsi_indicators",
]
