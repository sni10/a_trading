from typing import Dict, Any

from src.domain.interfaces.logger import ILogger


def execute(
    decision: Dict[str, Any],
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    logger: ILogger | None = None,
) -> None:
    """Заглушка исполнения: только логирование, без реальных сайд‑эффектов.

    В боевой системе здесь бы вызывался коннектор биржи и ордерный
    сервис; сейчас мы лишь фиксируем намерение в логах.
    """

    action = decision.get("action")
    reason = decision.get("reason")

    if logger:
        logger.log_info(
            f"⚙️ [EXEC] Исполнение решения стратегии (заглушка) | ticker_id: {ticker_id} | symbol: {symbol} | action: {action} | reason: {reason}"
        )

