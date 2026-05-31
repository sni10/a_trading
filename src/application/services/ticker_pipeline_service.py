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
from src.domain.services.orders.buy_order_timeout_service import cancel_stale_buy_orders
from src.domain.services.strategies.strategy_hub import evaluate_strategies
from src.domain.services.orchestrator.orchestrator import decide
from src.domain.services.execution.execution_service import execute
from src.infrastructure.logging import log_info
from src.infrastructure.logging.logger_adapter import LoggerAdapter

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
        self._logger = LoggerAdapter(_LOG)

    def process_tick(
        self,
        context: Dict[str, Any],
        *,
        symbol: str,
        ticker_id: int,
        price: float,
        ts: int,
    ) -> None:
        """Полностью обработать один тик торгового конвейера.

        Параметры повторяют существующий контракт синхронного демо‑цикла
        и не выполняют внешних операций.
        """

        # FEEDS: обновление market‑state и тикерного кэша.
        log_info(f"🌐 [FEEDS] Обновление market-state | ticker_id: {ticker_id} | symbol: {symbol} | price: {price:.8f} | ts: {ts}", _LOG)
        update_market_state(context, symbol=symbol, price=price, ts=ts)

        # ORDER TIMEOUT: отмена протухших BUY-ордеров.
        timeout_sec = self._cfg.buy_order_timeout_sec
        pending_send_timeout_sec = self._cfg.buy_order_pending_send_timeout_sec
        timeout_result = cancel_stale_buy_orders(
            context,
            symbol=symbol,
            now_ts=ts,
            timeout_sec=timeout_sec,
            pending_send_timeout_sec=pending_send_timeout_sec,
        )
        if timeout_result.canceled_orders:
            log_info(
                f"🕒 [ORDER_TIMEOUT] Отменено BUY/SELL: {timeout_result.canceled_orders} | "
                f"сделок: {timeout_result.canceled_deals}",
                _LOG,
            )
        # Если есть ордера на бирже, которые нужно отменить — складываем
        # их ID в очередь для async-воркера (order_execution_worker).
        if timeout_result.exchange_order_ids_to_cancel:
            cancel_queue = (
                context
                .setdefault("pending_exchange_cancels", {})
                .setdefault(symbol, [])
            )
            cancel_queue.extend(timeout_result.exchange_order_ids_to_cancel)
            log_info(
                f"🕒 [ORDER_TIMEOUT] В очередь на отмену на бирже: "
                f"{timeout_result.exchange_order_ids_to_cancel}",
                _LOG,
            )

        # IND: расчёт индикаторов поверх истории цен.
        log_info(f"📊 [IND] Расчёт индикаторов | ticker_id: {ticker_id} | symbol: {symbol} | price: {price:.8f}", _LOG)
        indicators = compute_indicators(
            context,
            ticker_id=ticker_id,
            symbol=symbol,
            price=price,
            logger=self._logger,
        )
        formatted_indicators = _format_indicators(indicators)
        log_info(
            f"📊 [IND] Индикаторы рассчитаны | ticker_id: {ticker_id}\n{formatted_indicators}",
            _LOG,
        )

        # CTX: подготовка контекста для стратегий
        positions = context.get("positions") or []
        has_indicators = bool(indicators)
        log_info(f"🧠 [CTX] Сбор контекста для стратегий | ticker_id: {ticker_id} | symbol: {symbol} | has_indicators: {has_indicators} | positions: {len(positions)}", _LOG)

        # STRAT: оценка стратегий и формирование intents.
        log_info(f"🎯 [STRAT] Оценка стратегий | ticker_id: {ticker_id} | symbol: {symbol}", _LOG)
        intents = evaluate_strategies(context, ticker_id=ticker_id, symbol=symbol)
        log_info(f"🎯 [STRAT] Intents сформированы | ticker_id: {ticker_id} | intents_count: {len(intents)} | intents: {intents}", _LOG)
        record_intents(context, symbol=symbol, intents=intents)

        # ORCH: оркестратор принимает финальное решение.
        log_info(f"🧩 [ORCH] Принятие решения по intents | ticker_id: {ticker_id} | symbol: {symbol} | intents_count: {len(intents)}", _LOG)
        decision = decide(intents, context, ticker_id=ticker_id, symbol=symbol)
        action = decision.get("action")
        reason = decision.get("reason", "")
        log_info(f"🧩 [ORCH] Решение принято | ticker_id: {ticker_id} | action: {action} | reason: {reason}", _LOG)
        record_decision(context, symbol=symbol, decision=decision)

        # EXEC: выполнение торгового решения.
        if action and action != "HOLD":
            log_info(f"⚙️ [EXEC] Исполнение решения | ticker_id: {ticker_id} | symbol: {symbol} | action: {action} | reason: {reason}", _LOG)
            execute(decision, context, ticker_id=ticker_id, symbol=symbol)
            log_info(f"⚙️ [EXEC] ✅ Решение исполнено | ticker_id: {ticker_id} | action: {action} | price: {price:.8f}", _LOG)
        else:
            log_info(f"⚙️ [EXEC] HOLD - заявки не отправляются | ticker_id: {ticker_id} | reason: {reason}", _LOG)

        # STATE: обновление агрегированных метрик по конвейеру.
        log_info(f"📂 [STATE] Обновление метрик | ticker_id: {ticker_id}", _LOG)
        update_metrics(context, ticker_id=ticker_id)


__all__ = ["TickPipelineService"]


def _format_indicators(indicators: Dict[str, Any]) -> str:
    if not indicators:
        return "indicators: {}"
    lines = ["indicators:"]
    for key in sorted(indicators.keys()):
        value = indicators[key]
        if isinstance(value, float):
            value_str = f"{value:.8f}"
        else:
            value_str = str(value)
        lines.append(f"  {key}: {value_str}")
    return "\n".join(lines)
