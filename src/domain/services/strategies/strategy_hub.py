from typing import Dict, Any, List

from src.domain.interfaces.logger import ILogger
from src.domain.services.strategies.indicator_signal_service import (
    IndicatorSignalService,
)

_SIGNAL_SERVICE = IndicatorSignalService()


def evaluate_strategies(
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    logger: ILogger | None = None,
) -> List[Dict[str, Any]]:
    """Вернуть список BUY/HOLD intents для указанного инструмента.

    На текущем этапе стратегия агрегирует индикаторные сигналы и
    формирует единый intent с уровнем confidence.
    """

    if logger:
        logger.log_info(
            f"🎯 [STRAT] Оценка стратегий и формирование intents | ticker_id: {ticker_id} | symbol: {symbol}"
        )

    indicators = (context.get("indicators") or {}).get(symbol)
    if not indicators:
        intents = [
            {
                "action": "HOLD",
                "confidence": 0.0,
                "reason": "no_indicators",
                "params": {},
            }
        ]
    else:
        signal = _SIGNAL_SERVICE.evaluate(indicators)
        action = "BUY" if signal.is_bullish else "HOLD"
        intents = [
            {
                "action": action,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "params": {
                    "signal_score": signal.score,
                    "signal_details": signal.details,
                },
            }
        ]

    if logger:
        logger.log_info(
            f"🎯 [STRAT] Intents сформированы | ticker_id: {ticker_id} | symbol: {symbol} | intents: {intents}"
        )
    return intents

