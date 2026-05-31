from __future__ import annotations

from typing import Any, Dict, List

from src.domain.interfaces.logger import ILogger
from src.domain.services.context.window_utils import (
    append_with_window,
    get_window_size_for_symbol,
)


def record_indicators(
    context: Dict[str, Any],
    *,
    symbol: str,
    snapshot: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Сохранить снимок индикаторов в контекст и его историю.

    * ``context["indicators"][symbol]`` – последний снимок;
    * ``context["indicators_history"][symbol]`` – окно последних N
      снимков, где ``N == CurrencyPair.indicator_window_size``.

    История живёт в простом dict/list, чтобы в будущем можно было
    прозрачно заменить backend (например, на Redis), оставив контракт
    этой функции прежним.
    """

    indicators = context.setdefault("indicators", {})
    indicators[symbol] = snapshot

    history_all = context.setdefault("indicators_history", {})
    history_for_symbol: List[Dict[str, Any]] = history_all.setdefault(symbol, [])

    window = get_window_size_for_symbol(context, symbol)
    truncated = append_with_window(history_for_symbol, snapshot, maxlen=window)

    if logger:
        logger.log_info(
            f"📊 [IND] Снимок индикаторов записан в историю | symbol: {symbol} | history_len: {len(history_for_symbol)} | window: {window} | truncated: {truncated}"
        )


__all__ = ["record_indicators"]
