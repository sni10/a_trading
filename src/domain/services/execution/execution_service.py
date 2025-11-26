from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_stage


def execute(decision: Dict[str, Any], context: Dict[str, Any], *, tick_id: int, symbol: str) -> None:
    """Заглушка исполнения: только логирование, без реальных сайд-эффектов."""

    log_stage(
        "EXEC",
        "CLASS:ExecutionService:execute() - получает Decision, проверяет риск/баланс и отправляет в биржу; в прототипе только лог",
        tick_id=tick_id,
        symbol=symbol,
        action=decision.get("action"),
        reason=decision.get("reason"),
    )

