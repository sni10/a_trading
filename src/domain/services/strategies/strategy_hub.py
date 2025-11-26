from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import log_stage


def evaluate_strategies(context: Dict[str, Any], *, tick_id: int, symbol: str) -> List[Dict[str, Any]]:
    """Вернуть список намерений (intents) для указанного инструмента.

    Сейчас реализована лишь очень простая демонстрационная логика.
    """

    log_stage(
        "STRAT",
        "CLASS:StrategyHub:evaluate_all() - получает context и возвращает список intents (BUY/SELL/HOLD, confidence, reason)",
        tick_id=tick_id,
        symbol=symbol,
    )

    # Extremely simple placeholder: alternate HOLD and BUY/SELL for demonstration
    if tick_id % 3 == 0:
        intents = [{"action": "SELL", "confidence": 0.4, "reason": "demo_down", "params": {}}]
    elif tick_id % 2 == 0:
        intents = [{"action": "BUY", "confidence": 0.7, "reason": "demo_up", "params": {"budget": 100}}]
    else:
        intents = [{"action": "HOLD", "confidence": 0.1, "reason": "no_signal", "params": {}}]

    log_stage("STRAT", "intents сформированы", tick_id=tick_id, symbol=symbol, intents=intents)
    return intents

