from typing import Dict, Any, List

from src.domain.interfaces.logger import ILogger
from src.domain.services.orchestrator.decision_center import DecisionCenter

_DECISION_CENTER = DecisionCenter()


def decide(
    intents: List[Dict[str, Any]],
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Оркестратор BUY/HOLD решений на основе сигналов и лимитов."""

    if logger:
        logger.log_info(
            f"🧩 [ORCH] Получен список intents для обработки | ticker_id: {ticker_id} | symbol: {symbol} | intents_count: {len(intents)}"
        )

    decision = _DECISION_CENTER.decide(
        intents,
        context,
        ticker_id=ticker_id,
        symbol=symbol,
        logger=logger,
    )

    if logger:
        logger.log_info(
            f"🧩 [ORCH] Решение принято | ticker_id: {ticker_id} | symbol: {symbol} | action: {decision.get('action')} | reason: {decision.get('reason')}"
        )
    return decision

