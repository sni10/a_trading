from typing import Dict, Any

from src.infrastructure.logging.logging_setup import log_stage


def init_context(config: Dict[str, Any]) -> Dict[str, Any]:
    """Создать in-memory контекст с обязательными разделами.

    Логика остаётся максимально простой, но лог‑сообщение оформлено в
    боевом стиле: кратко и человеко‑читаемо.
    """

    ctx: Dict[str, Any] = {
        "config": dict(config),
        "market": {},
        "indicators": {},
        "positions": {},
        "orders": {},
        "risk": {},
        "metrics": {"ticks": 0},
    }
    log_stage(
        "BOOT",
        "Инициализация базового in‑memory контекста",
        sections=sorted(ctx.keys()),
    )
    return ctx


def update_metrics(context: Dict[str, Any], tick_id: int) -> None:
    m = context.get("metrics", {})
    m["ticks"] = tick_id
    context["metrics"] = m
    log_stage("STATE", "Обновление метрик состояния", tick_id=tick_id)

