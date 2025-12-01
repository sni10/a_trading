from __future__ import annotations

from typing import Any, Dict, List


def get_window_size_for_symbol(
    context: Dict[str, Any],
    symbol: str,
    *,
    default: int = 1000,
) -> int:
    """Вернуть размер окна истории для указанной пары.

    Сейчас используется ``CurrencyPair.indicator_window_size`` как
    единый лимит для историй индикаторов, intents и decisions. Это
    позволяет контролировать объём in‑memory state и в будущем заменить
    хранение на Redis/БД без изменения вызывающего кода.
    """

    pairs = context.get("pairs") or {}
    pair = pairs.get(symbol)
    return getattr(pair, "indicator_window_size", default) if pair is not None else default


def append_with_window(
    sequence: List[Any],
    item: Any,
    *,
    maxlen: int,
) -> bool:
    """Добавить элемент в список с усечением головы по ``maxlen``.

    Возвращает ``True``, если при добавлении пришлось обрезать старые
    элементы с начала списка.
    """

    sequence.append(item)
    truncated = False
    if len(sequence) > maxlen:
        del sequence[0 : len(sequence) - maxlen]
        truncated = True
    return truncated


__all__ = ["get_window_size_for_symbol", "append_with_window"]
