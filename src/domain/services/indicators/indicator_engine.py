from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_stage


def compute_indicators(context: Dict[str, Any], *, tick_id: int, symbol: str, price: float) -> Dict[str, Any]:
    """Вернуть снимок индикаторов для инструмента.

    Пока реализованы лишь фиктивные значения, но логика и интерфейс
    соответствуют будущему IndicatorEngine.
    """

    log_stage(
        "IND",
        "CLASS:IndicatorEngine:on_tick() - получает Ticker(symbol, price), обновляет внутреннее состояние и возвращает IndicatorSnapshot",
        tick_id=tick_id,
        symbol=symbol,
        price=price,
    )

    # Fake/simple indicators
    sma = price  # placeholder
    rsi = 50.0   # neutral
    snapshot = {"sma": sma, "rsi": rsi, "ts": context.get("market", {}).get(symbol, {}).get("ts")}
    log_stage("IND", "snapshot готов", tick_id=tick_id, symbol=symbol, sma=sma, rsi=rsi)
    return snapshot

