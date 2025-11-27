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

# Имя логгера для этого модуля
_LOG = __name__


class TickPipelineService:
    """Единый конвейер обработки одного тика.

    Сервис инкапсулирует последовательность стадий:

    ``market state → indicators → strategies → orchestrator → execution → metrics``.

    Важно: внутри нет внешнего I/O, работы с снапшотами, сетью или файлами.
    Всё ограничивается чистой обработкой in-memory контекста.

    Логирование:
    - Логируем КАЖДЫЙ этап конвейера для полной отладки на этапе разработки.
    - В будущем можно отключить подробное логирование одной опцией.
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
        log_info(f"🌐 [FEEDS] Обновление market-state | tick_id: {tick_id} | symbol: {symbol} | price: {price:.8f} | ts: {ts}", _LOG)
        update_market_state(context, symbol=symbol, price=price, ts=ts)

        # IND: расчёт индикаторов поверх истории цен.
        log_info(f"📊 [IND] Расчёт индикаторов | tick_id: {tick_id} | symbol: {symbol} | price: {price:.8f}", _LOG)
        indicators = compute_indicators(
            context, tick_id=tick_id, symbol=symbol, price=price
        )
        log_info(f"📊 [IND] Индикаторы рассчитаны | tick_id: {tick_id} | sma: {indicators.get('sma', 'N/A')} | rsi: {indicators.get('rsi', 'N/A')}", _LOG)

        # CTX: подготовка контекста для стратегий
        positions = context.get("positions") or []
        has_indicators = bool(indicators)
        log_info(f"🧠 [CTX] Сбор контекста для стратегий | tick_id: {tick_id} | symbol: {symbol} | has_indicators: {has_indicators} | positions: {len(positions)}", _LOG)

        # STRAT: оценка стратегий и формирование intents.
        log_info(f"🎯 [STRAT] Оценка стратегий | tick_id: {tick_id} | symbol: {symbol}", _LOG)
        intents = evaluate_strategies(context, tick_id=tick_id, symbol=symbol)
        log_info(f"🎯 [STRAT] Intents сформированы | tick_id: {tick_id} | intents_count: {len(intents)} | intents: {intents}", _LOG)
        record_intents(context, symbol=symbol, intents=intents)

        # ORCH: оркестратор принимает финальное решение.
        log_info(f"🧩 [ORCH] Принятие решения по intents | tick_id: {tick_id} | symbol: {symbol} | intents_count: {len(intents)}", _LOG)
        decision = decide(intents, context, tick_id=tick_id, symbol=symbol)
        action = decision.get("action")
        reason = decision.get("reason", "")
        log_info(f"🧩 [ORCH] Решение принято | tick_id: {tick_id} | action: {action} | reason: {reason}", _LOG)
        record_decision(context, symbol=symbol, decision=decision)

        # EXEC: выполнение торгового решения.
        if action and action != "HOLD":
            log_info(f"⚙️ [EXEC] Исполнение решения | tick_id: {tick_id} | symbol: {symbol} | action: {action} | reason: {reason}", _LOG)
            execute(decision, context, tick_id=tick_id, symbol=symbol)
            log_info(f"⚙️ [EXEC] ✅ Решение исполнено | tick_id: {tick_id} | action: {action} | price: {price:.8f}", _LOG)
        else:
            log_info(f"⚙️ [EXEC] HOLD - заявки не отправляются | tick_id: {tick_id} | reason: {reason}", _LOG)

        # STATE: обновление агрегированных метрик по конвейеру.
        log_info(f"📂 [STATE] Обновление метрик | tick_id: {tick_id}", _LOG)
        update_metrics(context, tick_id=tick_id)


__all__ = ["TickPipelineService"]
