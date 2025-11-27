from __future__ import annotations

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.services.context.state import (
    update_market_state,
    update_metrics,
    record_intents,
    record_decision,
)
from src.domain.services.indicators.indicator_engine import compute_indicators
from src.domain.services.strategies.strategy_hub import evaluate_strategies
from src.domain.services.orchestrator.orchestrator import decide
from src.domain.services.execution.execution_service import execute
from src.infrastructure.logging.logging_setup import log_info


class TickPipelineService:
    """Единый конвейер обработки одного тика.

    Сервис инкапсулирует последовательность стадий:

    ``market state → indicators → strategies → orchestrator → execution → metrics``.

    Важно: внутри нет внешнего I/O, работы с снапшотами, сетью или файлами.
    Всё ограничивается чистой обработкой in-memory контекста.

    Логирование:
    - НЕ логируем каждый тик (это засоряет логи)
    - Логируем только важные события: сигналы к действию (не HOLD)
    """

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def process_tick(
        self,
        context: Dict[str, Any],
        *,
        symbol: str,
        tick_id: int,
        price: float,
        ts: int,
    ) -> None:
        """Полностью обработать один тик торгового конвейера.

        Параметры повторяют существующий контракт синхронного демо‑цикла
        и не выполняют внешних операций.
        """

        # FEEDS: обновление market‑state и тикерного кэша.
        update_market_state(context, symbol=symbol, price=price, ts=ts)

        # IND: расчёт индикаторов поверх истории цен.
        indicators = compute_indicators(
            context, tick_id=tick_id, symbol=symbol, price=price
        )

        # CTX: подготовка контекста для стратегий (без лога на каждый тик).
        # positions = context.get("positions") or []

        # STRAT: оценка стратегий и формирование intents.
        intents = evaluate_strategies(context, tick_id=tick_id, symbol=symbol)
        record_intents(context, symbol=symbol, intents=intents)

        # ORCH: оркестратор принимает финальное решение.
        decision = decide(intents, context, tick_id=tick_id, symbol=symbol)
        record_decision(context, symbol=symbol, decision=decision)

        # EXEC: выполнение торгового решения.
        # Логируем только если есть реальное действие (не HOLD).
        action = decision.get("action")
        if action and action != "HOLD":
            execute(decision, context, tick_id=tick_id, symbol=symbol)
            # Лог важного события - сигнал к действию
            log_info(
                f"🎯 Сигнал {action} | Тик {tick_id} | {symbol} | Цена: {price:.8f}"
            )

        # STATE: обновление агрегированных метрик по конвейеру.
        update_metrics(context, tick_id=tick_id)


__all__ = ["TickPipelineService"]
