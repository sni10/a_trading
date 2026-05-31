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

    РАСШИРЕН для включения БД-сущностей (Deal, Order, Trade).
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

    # === РАСШИРЕНИЕ: Сериализация БД-сущностей ===
    # Deals (активные сделки по паре)
    deals_section = (context.get("deals") or {}).get(symbol, [])
    deals_serialized = [deal.to_dict() for deal in deals_section] if deals_section else []

    # Orders (открытые ордера по паре)
    orders_section = (context.get("orders") or {}).get(symbol, [])
    orders_serialized = [order.to_dict() for order in orders_section] if orders_section else []

    # Trades (недавние трейды)
    trades_section = (context.get("trades") or {}).get(symbol, [])
    trades_serialized = [trade.to_dict() for trade in trades_section] if trades_section else []

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
        # БД-сущности
        "deals": deals_serialized,
        "orders": orders_serialized,
        "trades": trades_serialized,
    }

    if logger:
        logger.log_info(
            "📂 [STATE] Формирование снапшота state | "
            f"symbol: {symbol} | ticker_id: {ticker_id} | "
            f"has_market: {market is not None} | "
            f"has_indicators: {indicators is not None} | "
            f"intents_count: {len(intents)} | "
            f"deals_count: {len(deals_serialized)} | "
            f"orders_count: {len(orders_serialized)} | "
            f"trades_count: {len(trades_serialized)}"
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

    РАСШИРЕН для восстановления БД-сущностей (Deal, Order, Trade).
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

    # === РАСШИРЕНИЕ: Десериализация БД-сущностей ===
    from src.domain.entities.deal import Deal
    from src.domain.entities.order import Order
    from src.domain.entities.trade import Trade

    # Восстановить Deals
    deals_data = snapshot.get("deals") or []
    deals_section = context.setdefault("deals", {})
    deals_section[symbol] = [Deal.from_dict(d) for d in deals_data]

    # Восстановить Orders
    orders_data = snapshot.get("orders") or []
    orders_section = context.setdefault("orders", {})
    orders_section[symbol] = [Order.from_dict(o) for o in orders_data]

    # Восстановить Trades
    trades_data = snapshot.get("trades") or []
    trades_section = context.setdefault("trades", {})
    trades_section[symbol] = [Trade.from_dict(t) for t in trades_data]

    if logger:
        logger.log_info(
            "📦 [LOAD] Снапшот state применён к контексту | "
            f"symbol: {symbol} | ticker_id: {snapshot.get('ticker_id')} | "
            f"deals_restored: {len(deals_data)} | "
            f"orders_restored: {len(orders_data)} | "
            f"trades_restored: {len(trades_data)}"
        )


__all__ = ["make_state_snapshot", "apply_state_snapshot"]
