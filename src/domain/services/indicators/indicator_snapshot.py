"""Создание снапшотов индикаторов и backward compatibility.

Модуль отвечает за:
* Создание snapshot-словаря с индикаторами
* Backward compatibility: placeholder-значения для старых полей "sma" и "rsi"
* Сохранение снапшотов в контекст через record_indicators
* Логирование результата
"""

from __future__ import annotations

from typing import Any, Dict

from src.domain.interfaces.logger import ILogger
from src.domain.services.context.state import record_indicators

_RESERVED_KEYS = {"symbol", "ticker_id", "price", "sma", "rsi", "ts"}


def create_indicator_snapshot(
    *,
    context: Dict[str, Any],
    symbol: str,
    ticker_id: int,
    last_price: float,
    indicators: Dict[str, Any],
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Создание снапшота индикаторов с backward compatibility.

    Функция создаёт единый snapshot-словарь, который включает:
    - Базовые поля: symbol, ticker_id, price, ts
    - Placeholder-поля для обратной совместимости: sma, rsi
    - Все вычисленные индикаторы из параметра indicators

    Также функция:
    - Сохраняет snapshot в контекст через record_indicators
    - Логирует результат формирования snapshot

    Args:
        context: Глобальный контекст приложения.
        symbol: Торговая пара (например, "BTC/USDT").
        ticker_id: Уникальный ID тикера.
        last_price: Последняя цена из тикера.
        indicators: Словарь с вычисленными индикаторами (fast/medium/heavy).
        logger: Опциональный логгер для записи информации.

    Returns:
        Словарь-снапшот с полным набором индикаторов.
    """
    # Извлечение timestamp из контекста
    ts = context.get("market", {}).get(symbol, {}).get("ts")

    merged_indicators = _merge_indicators(context, symbol, indicators)
    sma_placeholder = _select_sma_placeholder(last_price, merged_indicators)
    rsi_placeholder = _select_rsi_placeholder(merged_indicators)

    # Создание snapshot-словаря
    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "ticker_id": ticker_id,
        "price": float(last_price),
        "sma": sma_placeholder,
        "rsi": rsi_placeholder,
        "ts": ts,
        **merged_indicators,
    }

    # Сохраняем снимок в общем контексте и его историю, чтобы потом
    # можно было заменить in‑memory стор на Redis/БД без правки
    # вызывающего кода.
    record_indicators(
        context,
        symbol=symbol,
        snapshot=snapshot,
        logger=logger,
    )

    # Логирование результата
    has_fast = "sma_fast_5" in snapshot
    has_medium = "sma_medium_20" in snapshot
    has_heavy = "sma_heavy_100" in snapshot
    if logger:
        logger.log_info(
            f"📊 [IND] Снимок индикаторов сформирован | ticker_id: {ticker_id} | symbol: {symbol} | "
            f"sma: {snapshot['sma']:.8f} | has_fast: {has_fast} | has_medium: {has_medium} | has_heavy: {has_heavy}"
        )

    return snapshot


def _merge_indicators(
    context: Dict[str, Any],
    symbol: str,
    indicators: Dict[str, Any],
) -> Dict[str, Any]:
    previous = (context.get("indicators") or {}).get(symbol)
    merged: Dict[str, Any] = {}
    if isinstance(previous, dict):
        merged.update({key: value for key, value in previous.items() if key not in _RESERVED_KEYS})
    if indicators:
        merged.update({key: value for key, value in indicators.items() if key not in _RESERVED_KEYS})
    return merged


def _select_sma_placeholder(last_price: float, indicators: Dict[str, Any]) -> float:
    value = indicators.get("sma_7")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return float(last_price)


def _select_rsi_placeholder(indicators: Dict[str, Any]) -> float:
    value = indicators.get("rsi_5")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return 50.0


__all__ = ["create_indicator_snapshot"]
