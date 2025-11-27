from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import log_info

# Имя логгера для этого модуля
_LOG = __name__


def evaluate_strategies(context: Dict[str, Any], *, tick_id: int, symbol: str) -> List[Dict[str, Any]]:
    """Вернуть список намерений (intents) для указанного инструмента.

    Сейчас реализована лишь очень простая демонстрационная логика, но
    формат логов уже приближен к боевому.
    """

    log_info(
        f"🎯 [STRAT] Оценка стратегий и формирование intents | tick_id: {tick_id} | symbol: {symbol}",
        _LOG
    )

    # Extremely simple placeholder: alternate HOLD and BUY/SELL for demonstration
    if tick_id % 3 == 0:
        intents = [{"action": "SELL", "confidence": 0.4, "reason": "demo_down", "params": {}}]
    elif tick_id % 2 == 0:
        intents = [{"action": "BUY", "confidence": 0.7, "reason": "demo_up", "params": {"budget": 100}}]
    else:
        intents = [{"action": "HOLD", "confidence": 0.1, "reason": "no_signal", "params": {}}]

    log_info(
        f"🎯 [STRAT] Intents сформированы | tick_id: {tick_id} | symbol: {symbol} | intents: {intents}",
        _LOG
    )
    return intents

