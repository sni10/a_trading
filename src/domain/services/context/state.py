from typing import Dict, Any

from src.config.config import AppConfig
from src.infrastructure.logging.logging_setup import log_stage


def init_context(config: AppConfig) -> Dict[str, Any]:
    """Создать in-memory контекст с обязательными разделами.

    На вход принимает типизированный :class:`AppConfig` и кладёт его
    целиком в раздел ``context["config"]`` без преобразования в dict.

    Логика контекста остаётся простой: только разделы in-memory состояния,
    без доступа к сети/БД.
    """

    ctx: Dict[str, Any] = {
        "config": config,
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

