from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import log_stage


def decide(intents: List[Dict[str, Any]], context: Dict[str, Any], *, tick_id: int, symbol: str) -> Dict[str, Any]:
    """Простейший оркестратор: первое действие, отличное от HOLD, побеждает."""

    log_stage(
        "ORCH",
        "CLASS:Orchestrator:decide() - получает intents и context, применяет risk/cooldown, возвращает Decision",
        tick_id=tick_id,
        symbol=symbol,
        intents=intents,
    )

    decision: Dict[str, Any] = {
        "action": "HOLD",
        "reason": "no_action",
        "ts": context.get("market", {}).get(symbol, {}).get("ts"),
    }
    for intent in intents:
        if intent.get("action") != "HOLD":
            decision = {
                "action": intent.get("action"),
                "reason": intent.get("reason", "intent"),
                "params": intent.get("params", {}),
            }
            break

    log_stage(
        "ORCH",
        "decision готов",
        tick_id=tick_id,
        symbol=symbol,
        action=decision.get("action"),
        reason=decision.get("reason"),
    )
    return decision

