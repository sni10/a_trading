from __future__ import annotations

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.interfaces.logger import ILogger


def init_context(
    config: AppConfig,
    *,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Создать базовый in-memory контекст приложения.

    Функция инкапсулирует структуру корневого dict-контекста и не
    выполняет никакого внешнего I/O. Конфиг кладётся в раздел
    ``context["config"]`` как объект :class:`AppConfig` без
    преобразования в dict.
    """

    ctx: Dict[str, Any] = {
        "config": config,
        "market": {},
        "indicators": {},  # последний снимок индикаторов по инструментам
        "positions": {},
        "orders": {},
        "risk": {},
        "metrics": {"ticks": 0},
        # История индикаторов по каждому инструменту
        "indicators_history": {},
        # Последние и исторические intents/decisions стратегий и оркестратора
        "intents": {},
        "decisions": {},
        "intents_history": {},
        "decisions_history": {},
    }

    if logger:
        logger.log_info(
            f"🚀 [BOOT] Инициализация базового in‑memory контекста | sections: {sorted(ctx.keys())}"
        )
    return ctx


__all__ = ["init_context"]
