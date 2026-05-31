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
from src.domain.services.context.state_snapshot_manager import (
    apply_state_snapshot as _apply_state_snapshot,
    make_state_snapshot as _make_state_snapshot,
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
    """Фасад для :func:`state_snapshot_manager.make_state_snapshot`."""

    return _make_state_snapshot(context, symbol=symbol, ticker_id=ticker_id, logger=logger)


def apply_state_snapshot(
    context: Dict[str, Any],
    *,
    symbol: str,
    snapshot: Dict[str, Any],
    logger: ILogger | None = None,
) -> None:
    """Фасад для :func:`state_snapshot_manager.apply_state_snapshot`."""

    _apply_state_snapshot(context, symbol=symbol, snapshot=snapshot, logger=logger)


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

