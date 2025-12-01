from typing import Dict, Any, List

from src.domain.interfaces.logger import ILogger


def evaluate_strategies(
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    logger: ILogger | None = None,
) -> List[Dict[str, Any]]:
    """Вернуть список намерений (intents) для указанного инструмента.

    Сейчас реализована лишь очень простая демонстрационная логика, но
    формат логов уже приближен к боевому.
    """

    if logger:
        logger.log_info(
            f"🎯 [STRAT] Оценка стратегий и формирование intents | ticker_id: {ticker_id} | symbol: {symbol}"
        )

    # Extremely simple placeholder: alternate HOLD and BUY/SELL for demonstration
    if ticker_id % 3 == 0:
        intents = [{"action": "SELL", "confidence": 0.4, "reason": "demo_down", "params": {}}]
    elif ticker_id % 2 == 0:
        intents = [{"action": "BUY", "confidence": 0.7, "reason": "demo_up", "params": {"budget": 100}}]
    else:
        intents = [{"action": "HOLD", "confidence": 0.1, "reason": "no_signal", "params": {}}]

    if logger:
        logger.log_info(
            f"🎯 [STRAT] Intents сформированы | ticker_id: {ticker_id} | symbol: {symbol} | intents: {intents}"
        )
    return intents

