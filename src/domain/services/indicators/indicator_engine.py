from collections import deque
from typing import Any, Deque, Dict

from src.domain.interfaces.cache import IIndicatorStore
from src.domain.services.context.state import record_indicators
from src.infrastructure.logging.logging_setup import log_stage


def _sma(values: list[float]) -> float:
    """Простейшая скользящая средняя по списку значений.

    Предполагается, that ``values`` не пустой (контролируется вызывающим
    кодом через длину history).
    """

    return sum(values) / len(values)


def compute_indicators(
    context: Dict[str, Any], *, tick_id: int, symbol: str, price: float
) -> Dict[str, Any]:
    """Вернуть снимок индикаторов для инструмента и сохранить его в state.

    Функция остаётся совместимой по контракту (сигнатура и базовый
    формат snapshot), но внутренняя логика ближе к целевому
    ``IndicatorEngine`` из плана 2025‑11:

    * использует ``IIndicatorStore`` из контекста для триггеров
      fast/medium/heavy;
    * ведёт in‑memory буфер цен ``context["price_history"][symbol]``;
    * по триггерам считает простые SMA на разных окнах и добавляет их в
      snapshot.
    """

    log_stage(
        "IND",
        "Расчёт индикаторов по тику",
        tick_id=tick_id,
        symbol=symbol,
        price=price,
    )

    # --- История цен по инструменту (общая для всех индикаторов) ---
    price_history_root: Dict[str, Deque[float]] = context.setdefault(
        "price_history", {}
    )
    history: Deque[float] = price_history_root.setdefault(
        symbol, deque(maxlen=500)
    )
    history.append(float(price))

    # --- Достаём IndicatorStore для символа (если настроен) ---
    stores = context.get("indicator_stores") or {}
    store = stores.get(symbol)

    indicators: Dict[str, Any] = {}

    if isinstance(store, IIndicatorStore):
        # Окна для примера fast/medium/heavy. В дальнейшем можно вынести
        # в конфиг/пару, не меняя общий каркас функции.
        fast_window = 5
        medium_window = 20
        heavy_window = 100

        # FAST: можно обновлять часто, на небольшом окне
        if store.should_update_fast(tick_id) and len(history) >= fast_window:
            indicators["sma_fast_5"] = _sma(list(history)[-fast_window:])

        # MEDIUM: реже и на большем окне
        if store.should_update_medium(tick_id) and len(history) >= medium_window:
            indicators["sma_medium_20"] = _sma(list(history)[-medium_window:])

        # HEAVY: ещё реже и на самом длинном окне
        if store.should_update_heavy(tick_id) and len(history) >= heavy_window:
            indicators["sma_heavy_100"] = _sma(list(history)[-heavy_window:])

        # Сохраняем «сырые» значения цены в истории слоёв стора, чтобы при
        # необходимости можно было посчитать индикаторы иначе.
        if store.should_update_fast(tick_id):
            store.fast_history.append(float(price))  # type: ignore[attr-defined]
        if store.should_update_medium(tick_id):
            store.medium_history.append(float(price))  # type: ignore[attr-defined]
        if store.should_update_heavy(tick_id):
            store.heavy_history.append(float(price))  # type: ignore[attr-defined]

    # --- Базовые поля snapshot (обратная совместимость) ---
    ts = context.get("market", {}).get(symbol, {}).get("ts")

    # Поля "sma" и "rsi" пока оставляем как простые заглушки, чтобы не
    # ломать ожидания демо‑конвейера и README.
    sma_placeholder = float(price)
    rsi_placeholder = 50.0

    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "tick_id": tick_id,
        "price": float(price),
        "sma": sma_placeholder,
        "rsi": rsi_placeholder,
        "ts": ts,
        **indicators,
    }

    # Сохраняем снимок в общем контексте и его историю, чтобы потом
    # можно было заменить in‑memory стор на Redis/БД без правки
    # вызывающего кода.
    record_indicators(context, symbol=symbol, snapshot=snapshot)

    log_stage(
        "IND",
        "Снимок индикаторов сформирован",
        tick_id=tick_id,
        symbol=symbol,
        sma=snapshot["sma"],
        has_fast="sma_fast_5" in snapshot,
        has_medium="sma_medium_20" in snapshot,
        has_heavy="sma_heavy_100" in snapshot,
    )
    return snapshot

