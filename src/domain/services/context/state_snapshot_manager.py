from __future__ import annotations

from typing import Any, Dict, List

from src.domain.interfaces.logger import ILogger


def make_state_snapshot(
    context: Dict[str, Any],
    *,
    symbol: str,
    ticker_id: int,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Сформировать сериализуемый снапшот ``state`` для инструмента.

    В снапшот попадает только чистый ``dict``‑state без несериализуемых
    объектов (репозитории, кэши, config и т.п.), чтобы backend хранения
    мог быть любым (файл, Redis и др.).
    """

    market = (context.get("market") or {}).get(symbol)
    indicators = (context.get("indicators") or {}).get(symbol)
    indicators_history: List[Dict[str, Any]] = (
        (context.get("indicators_history") or {}).get(symbol, [])
    )
    intents: List[Dict[str, Any]] = (context.get("intents") or {}).get(symbol, [])
    intents_history: List[Dict[str, Any]] = (
        (context.get("intents_history") or {}).get(symbol, [])
    )
    decision = (context.get("decisions") or {}).get(symbol)
    decisions_history: List[Dict[str, Any]] = (
        (context.get("decisions_history") or {}).get(symbol, [])
    )
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
            "📂 [STATE] Формирование снапшота state | "
            f"symbol: {symbol} | ticker_id: {ticker_id} | "
            f"has_market: {market is not None} | "
            f"has_indicators: {indicators is not None} | "
            f"intents_count: {len(intents)}"
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

    Обновляет только высокоуровневые разделы ``market``, ``indicators``,
    ``*_history``, ``intents``, ``decisions`` и ``metrics``, не трогая
    кэши рынка, репозитории и конфигурацию.
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
            "📦 [LOAD] Снапшот state применён к контексту | "
            f"symbol: {symbol} | ticker_id: {snapshot.get('ticker_id')}"
        )


__all__ = ["make_state_snapshot", "apply_state_snapshot"]
