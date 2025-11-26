from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_stage


def init_context(config: Dict[str, Any]) -> Dict[str, Any]:
    """Создать in-memory контекст с обязательными разделами."""

    ctx: Dict[str, Any] = {
        "config": dict(config),
        "market": {},
        "indicators": {},
        "positions": {},
        "orders": {},
        "risk": {},
        "metrics": {"ticks": 0},
    }
    log_stage("BOOT", "CLASS:Context:init() - создает базовый контекст в памяти, возвращает dict", keys=list(ctx.keys()))
    return ctx


def update_metrics(context: Dict[str, Any], tick_id: int) -> None:
    m = context.get("metrics", {})
    m["ticks"] = tick_id
    context["metrics"] = m
    log_stage(
        "STATE",
        "CLASS:Metrics:update() - получает tick_id, обновляет счетчики, ничего не возвращает",
        tick_id=tick_id,
    )

