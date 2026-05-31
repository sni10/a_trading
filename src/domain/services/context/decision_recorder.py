from __future__ import annotations

from typing import Any, Dict, List

from src.domain.interfaces.logger import ILogger
from src.domain.services.context.window_utils import (
    append_with_window,
    get_window_size_for_symbol,
)


def record_intents(
    context: Dict[str, Any],
    *,
    symbol: str,
    intents: List[Dict[str, Any]],
    logger: ILogger | None = None,
) -> None:
    """Сохранить intents стратегий в последний срез и историю.

    Формат intents не фиксируется жёстко: это список произвольных dict,
    но на уровне оркестратора ожидаются как минимум поля ``action``,
    ``reason`` и ``params``.
    """

    current = context.setdefault("intents", {})
    current[symbol] = intents

    history_all = context.setdefault("intents_history", {})
    history_for_symbol: List[List[Dict[str, Any]]] = history_all.setdefault(
        symbol, []
    )

    window = get_window_size_for_symbol(context, symbol)
    truncated = append_with_window(history_for_symbol, intents, maxlen=window)

    if logger:
        logger.log_info(
            f"📂 [STATE] Intents сохранены в истории | symbol: {symbol} | intents_count: {len(intents)} | history_len: {len(history_for_symbol)} | window: {window} | truncated: {truncated}"
        )


def record_decision(
    context: Dict[str, Any],
    *,
    symbol: str,
    decision: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Сохранить финальное решение оркестратора в срез и историю."""

    current = context.setdefault("decisions", {})
    current[symbol] = decision

    history_all = context.setdefault("decisions_history", {})
    history_for_symbol: List[Dict[str, Any]] = history_all.setdefault(symbol, [])

    window = get_window_size_for_symbol(context, symbol)
    truncated = append_with_window(history_for_symbol, decision, maxlen=window)

    if logger:
        action = decision.get("action")
        logger.log_info(
            f"📂 [STATE] Решение оркестратора сохранено в истории | symbol: {symbol} | action: {action} | history_len: {len(history_for_symbol)} | window: {window} | truncated: {truncated}"
        )


__all__ = ["record_intents", "record_decision"]
