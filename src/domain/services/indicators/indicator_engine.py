from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_stage


def compute_indicators(context: Dict[str, Any], *, tick_id: int, symbol: str, price: float) -> Dict[str, Any]:
    """Вернуть снимок индикаторов для инструмента.

    Сейчас расчёты максимально простые (демо‑значения), но сама форма
    лога и интерфейс соответствуют будущему полноценному IndicatorEngine.
    """

    log_stage(
        "IND",
        "Расчёт индикаторов по тику",
        tick_id=tick_id,
        symbol=symbol,
        price=price,
    )

    # Fake/simple indicators
    sma = price  # placeholder
    rsi = 50.0   # neutral
    snapshot = {"sma": sma, "rsi": rsi, "ts": context.get("market", {}).get(symbol, {}).get("ts")}
    log_stage("IND", "Снимок индикаторов сформирован", tick_id=tick_id, symbol=symbol, sma=sma, rsi=rsi)
    return snapshot

