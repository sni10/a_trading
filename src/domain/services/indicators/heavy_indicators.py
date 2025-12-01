"""Тяжёлые индикаторы (HEAVY layer) для расчёта с низкой частотой.

Модуль содержит функции для расчёта тяжёлых индикаторов:
* SMA-100 (простая скользящая средняя)
* MACD (Moving Average Convergence Divergence через TA-Lib)
* Bollinger Bands (через TA-Lib)
* Signal strength (производный показатель от MACD)
* Trend signal (сигнал тренда: -1 bearish, 0 neutral, 1 bullish)

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


def calculate_sma_heavy_100(
    history_list: list[float],
    heavy_window: int = 100,
) -> float | None:
    """Демо-индикатор: SMA по последним N тикам (по умолчанию 100).

    Args:
        history_list: История цен (от старых к новым).
        heavy_window: Размер окна для расчёта SMA.

    Returns:
        Значение SMA или None, если недостаточно истории.
    """
    n = len(history_list)
    if n >= heavy_window:
        return _sma(history_list[-heavy_window:])
    return None


def calculate_macd_indicators(
    history_list: list[float],
    logger: ILogger | None = None,
) -> dict[str, Any]:
    """Расчёт MACD индикаторов через TA-Lib.

    MACD (Moving Average Convergence Divergence) с параметрами:
    - fastperiod=12, slowperiod=26, signalperiod=9

    Также вычисляются производные метрики:
    - signal_strength: 0-100 на основе расхождения MACD
    - trend_signal: -1 (bearish), 0 (neutral), 1 (bullish)

    Args:
        history_list: История цен (минимум 50 значений для корректного расчёта).
        logger: Опциональный логгер для записи ошибок.

    Returns:
        Словарь с ключами:
        - macd, macdsignal, macdhist (основные компоненты MACD)
        - signal_strength (сила сигнала 0-100)
        - trend_signal (направление тренда -1/0/1)

        Если библиотеки недоступны или истории недостаточно — пустой словарь.
    """
    indicators: dict[str, Any] = {}
    n = len(history_list)

    # Проверка доступности библиотек и достаточности истории
    if _np is None or _talib is None or n < 50:
        return indicators

    try:
        closes = _np.array(history_list[-100:], dtype="float64")  # type: ignore[arg-type]

        macd, macdsignal, macdhist = _talib.MACD(  # type: ignore[call-arg]
            closes,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9,
        )

        macd_val = float(macd[-1]) if len(macd) > 0 and not _np.isnan(macd[-1]) else 0.0
        signal_val = (
            float(macdsignal[-1])
            if len(macdsignal) > 0 and not _np.isnan(macdsignal[-1])
            else 0.0
        )
        hist_val = (
            float(macdhist[-1])
            if len(macdhist) > 0 and not _np.isnan(macdhist[-1])
            else 0.0
        )

        # Signal strength (0-100 scale based on MACD divergence)
        signal_strength = (
            min(100.0, abs(macd_val - signal_val) * 10000.0)
            if signal_val != 0.0
            else 0.0
        )

        # Trend signal (-1 bearish, 0 neutral, 1 bullish)
        trend_signal = 1 if macd_val > signal_val and hist_val > 0 else (
            -1 if macd_val < signal_val and hist_val < 0 else 0
        )

        indicators["macd"] = round(macd_val, 8)
        indicators["macdsignal"] = round(signal_val, 8)
        indicators["macdhist"] = round(hist_val, 8)
        indicators["signal_strength"] = round(signal_strength, 2)
        indicators["trend_signal"] = trend_signal

    except Exception as exc:  # pragma: no cover - защитный путь
        if logger:
            logger.log_warning(
                f"⚠️ [WARN] Ошибка при расчёте MACD через ta-lib | error: {exc}"
            )

    return indicators


def calculate_bollinger_bands(
    history_list: list[float],
    logger: ILogger | None = None,
) -> dict[str, float]:
    """Расчёт Bollinger Bands через TA-Lib.

    Bollinger Bands с параметрами:
    - timeperiod=20, nbdevup=2, nbdevdn=2

    Args:
        history_list: История цен (минимум 50 значений для корректного расчёта).
        logger: Опциональный логгер для записи ошибок.

    Returns:
        Словарь с ключами bb_upper, bb_middle, bb_lower (если удалось вычислить).
        Если библиотеки недоступны или истории недостаточно — пустой словарь.
    """
    indicators: dict[str, float] = {}
    n = len(history_list)

    # Проверка доступности библиотек и достаточности истории
    if _np is None or _talib is None or n < 50:
        return indicators

    try:
        closes = _np.array(history_list[-100:], dtype="float64")  # type: ignore[arg-type]

        upperband, middleband, lowerband = _talib.BBANDS(  # type: ignore[call-arg]
            closes,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2,
        )

        if len(upperband) > 0 and not _np.isnan(upperband[-1]):
            indicators["bb_upper"] = round(float(upperband[-1]), 8)
        if len(middleband) > 0 and not _np.isnan(middleband[-1]):
            indicators["bb_middle"] = round(float(middleband[-1]), 8)
        if len(lowerband) > 0 and not _np.isnan(lowerband[-1]):
            indicators["bb_lower"] = round(float(lowerband[-1]), 8)

    except Exception as exc:  # pragma: no cover - защитный путь
        if logger:
            logger.log_warning(
                f"⚠️ [WARN] Ошибка при расчёте BBands через ta-lib | error: {exc}"
            )

    return indicators


def calculate_heavy_indicators(
    history_list: list[float],
    heavy_window: int = 100,
    logger: ILogger | None = None,
) -> dict[str, Any]:
    """Расчёт всех тяжёлых индикаторов (HEAVY layer).

    Главная функция-оркестратор для тяжёлых индикаторов. Вычисляет:
    * sma_heavy_100 (демо)
    * macd, macdsignal, macdhist (реальные через TA-Lib)
    * signal_strength (производный от MACD)
    * trend_signal (производный от MACD)
    * bb_upper, bb_middle, bb_lower (Bollinger Bands через TA-Lib)

    Args:
        history_list: История цен.
        heavy_window: Размер окна для демо-индикатора sma_heavy_100.
        logger: Опциональный логгер для записи ошибок при расчёте MACD/BBands.

    Returns:
        Словарь с вычисленными индикаторами (только те, для которых
        достаточно истории и доступны библиотеки).
    """
    indicators: dict[str, Any] = {}

    # Демо-индикатор SMA-100
    sma_heavy_100 = calculate_sma_heavy_100(history_list, heavy_window)
    if sma_heavy_100 is not None:
        indicators["sma_heavy_100"] = sma_heavy_100

    # Реальные индикаторы MACD и производные метрики
    macd_indicators = calculate_macd_indicators(history_list, logger=logger)
    indicators.update(macd_indicators)

    # Bollinger Bands
    bb_indicators = calculate_bollinger_bands(history_list, logger=logger)
    indicators.update(bb_indicators)

    return indicators


__all__ = [
    "calculate_heavy_indicators",
    "calculate_sma_heavy_100",
    "calculate_macd_indicators",
    "calculate_bollinger_bands",
]
