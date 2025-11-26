from typing import Dict, Any

from src.domain.interfaces.cache import IIndicatorStore
from src.domain.services.context.state import record_indicators
from src.infrastructure.logging.logging_setup import log_stage


def compute_indicators(
    context: Dict[str, Any], *, tick_id: int, symbol: str, price: float
) -> Dict[str, Any]:
    """Вернуть снимок индикаторов для инструмента и сохранить его в state.

    Сейчас расчёты остаются предельно простыми (демо‑значения), но
    функция моделирует поведение будущего IndicatorEngine:

    * использует ``IIndicatorStore`` из контекста для решения, какие
      слои индикаторов (fast/medium/heavy) нужно обновить на этом тике;
    * записывает значения в in‑memory стор (для прототипа –
      :class:`InMemoryIndicatorStore`);
    * кладёт снимок в ``context["indicators"]`` и историю
      ``context["indicators_history"]`` через ``record_indicators``.

    В дальнейшем вместо этой симуляции можно будет подставить реальный
    провайдер индикаторов, сохранив контракт функции.
    """

    log_stage(
        "IND",
        "Расчёт индикаторов по тику (симуляция)",
        tick_id=tick_id,
        symbol=symbol,
        price=price,
    )

    # --- Обновляем in-memory IndicatorStore, если он есть в контексте ---
    stores = context.get("indicator_stores") or {}
    store = stores.get(symbol)
    if isinstance(store, IIndicatorStore):
        # Для простоты записываем саму цену как «сырое значение» во все
        # истории, согласно их частоте обновления. В реальной системе здесь
        # будут расчёты на основе окон тиков/баров.
        if store.should_update_fast(tick_id):
            store.fast_history.append(float(price))  # type: ignore[attr-defined]
        if store.should_update_medium(tick_id):
            store.medium_history.append(float(price))  # type: ignore[attr-defined]
        if store.should_update_heavy(tick_id):
            store.heavy_history.append(float(price))  # type: ignore[attr-defined]

    # --- Формируем простой снимок индикаторов ---
    sma = float(price)  # placeholder для простой SMA
    rsi = 50.0  # нейтральное значение, пока чистая заглушка
    ts = context.get("market", {}).get(symbol, {}).get("ts")

    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "tick_id": tick_id,
        "sma": sma,
        "rsi": rsi,
        "ts": ts,
    }

    # Сохраняем снимок в общем контексте и его историю, чтобы потом
    # можно было заменить in‑memory стор на Redis/БД без правки
    # вызывающего кода.
    record_indicators(context, symbol=symbol, snapshot=snapshot)

    log_stage(
        "IND",
        "Снимок индикаторов сформирован (симуляция)",
        tick_id=tick_id,
        symbol=symbol,
        sma=sma,
        rsi=rsi,
    )
    return snapshot

