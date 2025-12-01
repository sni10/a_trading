from typing import Any, Dict, List

from src.config.config import AppConfig
from src.domain.interfaces.logger import ILogger
from src.domain.services.context.context_initializer import init_context as _init_context
from src.domain.services.context.decision_recorder import (
    record_decision as _record_decision,
    record_intents as _record_intents,
)
from src.domain.services.context.indicator_recorder import (
    record_indicators as _record_indicators,
)
from src.domain.services.context.market_state_updater import (
    update_market_state as _update_market_state,
    update_metrics as _update_metrics,
)
from src.domain.services.context.window_utils import (
    append_with_window as _append_with_window,
    get_window_size_for_symbol as _get_window_size_for_symbol,
)


def init_context(
    config: AppConfig,
    *,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Фасад для :func:`context_initializer.init_context`.

    Сохранён для обратной совместимости импортов
    ``from src.domain.services.context.state import init_context``.
    """

    return _init_context(config, logger=logger)


def update_market_state(
    context: Dict[str, Any],
    *,
    symbol: str,
    price: float,
    ts: int,
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`market_state_updater.update_market_state`."""

    _update_market_state(context, symbol=symbol, price=price, ts=ts, logger=logger)


def update_metrics(
    context: Dict[str, Any],
    ticker_id: int,
    *,
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`market_state_updater.update_metrics`."""

    _update_metrics(context, ticker_id=ticker_id, logger=logger)


def record_indicators(
    context: Dict[str, Any],
    *,
    symbol: str,
    snapshot: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`indicator_recorder.record_indicators`."""

    _record_indicators(context, symbol=symbol, snapshot=snapshot, logger=logger)


def record_intents(
    context: Dict[str, Any],
    *,
    symbol: str,
    intents: List[Dict[str, Any]],
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`decision_recorder.record_intents`."""

    _record_intents(context, symbol=symbol, intents=intents, logger=logger)


def record_decision(
    context: Dict[str, Any],
    *,
    symbol: str,
    decision: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`decision_recorder.record_decision`."""

    _record_decision(context, symbol=symbol, decision=decision, logger=logger)


def make_state_snapshot(
    context: Dict[str, Any],
    *,
    symbol: str,
    ticker_id: int,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Сформировать сериализуемый снапшот state для указанного инструмента.

    В снапшот попадает только чистый dict‑state без несериализуемых
    объектов (репозитории, кэши, config и т.п.), чтобы backend хранения
    мог быть любым (файл, Redis и др.).
    """

    market = (context.get("market") or {}).get(symbol)
    indicators = (context.get("indicators") or {}).get(symbol)
    indicators_history = (context.get("indicators_history") or {}).get(symbol, [])
    intents = (context.get("intents") or {}).get(symbol, [])
    intents_history = (context.get("intents_history") or {}).get(symbol, [])
    decision = (context.get("decisions") or {}).get(symbol)
    decisions_history = (context.get("decisions_history") or {}).get(symbol, [])
    metrics = context.get("metrics") or {}

    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "ticker_id": ticker_id,
        "market": market,
        "indicators": indicators,
        "indicators_history": indicators_history,
        "intents": intents,
        "intents_history": intents_history,
        "decision": decision,
        "decisions_history": decisions_history,
        "metrics": metrics,
    }

    if logger:
        logger.log_info(
            f"📂 [STATE] Формирование снапшота state | symbol: {symbol} | ticker_id: {ticker_id} | has_market: {market is not None} | has_indicators: {indicators is not None} | intents_count: {len(intents)}"
        )

    return snapshot


def apply_state_snapshot(
    context: Dict[str, Any],
    *,
    symbol: str,
    snapshot: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Применить ранее сохранённый снапшот к текущему контексту.

    Функция обновляет только высокоуровневые разделы ``market``,
    ``indicators``, ``*_history``, ``intents``, ``decisions`` и
    ``metrics``, не трогая кэши рынка, репозитории и конфигурацию.
    """

    market_section = context.setdefault("market", {})
    if snapshot.get("market") is not None:
        market_section[symbol] = snapshot["market"]

    indicators_section = context.setdefault("indicators", {})
    if snapshot.get("indicators") is not None:
        indicators_section[symbol] = snapshot["indicators"]

    indicators_history_all = context.setdefault("indicators_history", {})
    indicators_history_all[symbol] = list(snapshot.get("indicators_history") or [])

    intents_section = context.setdefault("intents", {})
    intents_section[symbol] = list(snapshot.get("intents") or [])

    intents_history_all = context.setdefault("intents_history", {})
    intents_history_all[symbol] = list(snapshot.get("intents_history") or [])

    decisions_section = context.setdefault("decisions", {})
    if snapshot.get("decision") is not None:
        decisions_section[symbol] = snapshot["decision"]

    decisions_history_all = context.setdefault("decisions_history", {})
    decisions_history_all[symbol] = list(snapshot.get("decisions_history") or [])

    metrics = snapshot.get("metrics") or {}
    if metrics:
        context["metrics"] = dict(metrics)

    if logger:
        logger.log_info(
            f"📦 [LOAD] Снапшот state применён к контексту | symbol: {symbol} | ticker_id: {snapshot.get('ticker_id')}"
        )
__all__ = [
    "init_context",
    "update_market_state",
    "update_metrics",
    "record_indicators",
    "record_intents",
    "record_decision",
    "make_state_snapshot",
    "apply_state_snapshot",
]

