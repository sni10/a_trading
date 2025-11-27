from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_info

# Имя логгера для этого модуля
_LOG = __name__


def execute(decision: Dict[str, Any], context: Dict[str, Any], *, tick_id: int, symbol: str) -> None:
    """Заглушка исполнения: только логирование, без реальных сайд‑эффектов.

    В боевой системе здесь бы вызывался коннектор биржи и ордерный
    сервис; сейчас мы лишь фиксируем намерение в логах.
    """

    action = decision.get("action")
    reason = decision.get("reason")
    log_info(
        f"⚙️ [EXEC] Исполнение решения стратегии (заглушка) | tick_id: {tick_id} | symbol: {symbol} | action: {action} | reason: {reason}",
        _LOG
    )

