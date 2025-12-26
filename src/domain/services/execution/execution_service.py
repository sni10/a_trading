from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from src.domain.interfaces.logger import ILogger
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.entities.deal import Deal
from src.domain.entities.order import Order


def execute(
    decision: Dict[str, Any],
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    logger: ILogger | None = None,
) -> None:
    """Боевой сценарий: создать deal + buy/sell ордера в in-memory контексте.

    Реальных вызовов к бирже тут нет — это безопасная симуляция, которая
    готовит структуры для дальнейшего исполнения через коннектор.
    """

    action = decision.get("action")
    reason = decision.get("reason")

    if action != "BUY":
        if logger:
            logger.log_info(
                f"⚙️ [EXEC] HOLD - заявка не создаётся | ticker_id: {ticker_id} | symbol: {symbol} | reason: {reason}"
            )
        return

    params = decision.get("params") or {}
    price = params.get("price")
    amount = params.get("amount")
    budget = params.get("budget")
    target_sell_price = params.get("target_sell_price")
    sell_amount = params.get("sell_amount")
    ts = decision.get("ts") or context.get("market", {}).get(symbol, {}).get("ts")

    if price is None:
        price = context.get("market", {}).get(symbol, {}).get("last_price")
    if price is None:
        if logger:
            logger.log_info(
                f"⚙️ [EXEC] Пропуск BUY: нет цены | ticker_id: {ticker_id} | symbol: {symbol}"
            )
        return

    price = float(price)
    if amount is None and budget is not None and price > 0:
        amount = float(budget) / price

    if amount is None:
        if logger:
            logger.log_info(
                f"⚙️ [EXEC] Пропуск BUY: нет объёма | ticker_id: {ticker_id} | symbol: {symbol}"
            )
        return

    amount = float(amount)
    sell_amount_value = amount
    if sell_amount is not None:
        try:
            sell_amount_value = float(sell_amount)
        except (TypeError, ValueError):
            sell_amount_value = amount
    deal_id = _next_sequence(context, "deal_seq")
    buy_order_id = _next_sequence(context, "order_seq")
    sell_order_id = _next_sequence(context, "order_seq")

    timestamp = int(ts) if ts is not None else int(datetime.now().timestamp() * 1000)
    iso_time = datetime.utcfromtimestamp(timestamp / 1000).isoformat() + "Z"

    buy_order = Order(
        id=buy_order_id,
        symbol=symbol,
        timestamp=timestamp,
        datetime=iso_time,
        status="open",
        side="buy",
        type="limit",
        amount=amount,
        price=price,
        filled=0.0,
        remaining=amount,
        cost=round(price * amount, 8),
    )

    sell_price = target_sell_price if target_sell_price is not None else price
    sell_order = Order(
        id=sell_order_id,
        symbol=symbol,
        timestamp=timestamp,
        datetime=iso_time,
        status="open",
        side="sell",
        type="limit",
        amount=sell_amount_value,
        price=float(sell_price),
        filled=0.0,
        remaining=sell_amount_value,
        cost=round(float(sell_price) * sell_amount_value, 8),
    )

    pair = (context.get("pairs") or {}).get(symbol)
    max_loss_amount = pair.max_loss_amount if isinstance(pair, CurrencyPair) else None

    deal = Deal(
        id=deal_id,
        symbol=symbol,
        status=Deal.STATUS_PENDING,
        created_at=timestamp,
        target_amount=amount,
        target_buy_price=price,
        target_sell_price=float(sell_price),
        max_loss_amount=max_loss_amount,
        strategy_name=str(params.get("strategy") or "indicator_signal"),
        metadata={
            "reason": reason,
            "confidence": decision.get("confidence"),
        },
    )
    deal.attach_buy_order(buy_order)
    deal.attach_sell_order(sell_order)

    deals_section = context.setdefault("deals", {})
    deals_section.setdefault(symbol, []).append(deal)

    orders_section = context.setdefault("orders", {})
    orders_section.setdefault(symbol, []).extend([buy_order, sell_order])

    risk_section = context.setdefault("risk", {})
    risk_section.setdefault(symbol, {})["last_buy_ts"] = timestamp

    if logger:
        logger.log_info(
            f"⚙️ [EXEC] BUY создан | ticker_id: {ticker_id} | symbol: {symbol} | "
            f"deal_id: {deal_id} | buy_order: {buy_order_id} | sell_order: {sell_order_id}"
        )


def _next_sequence(context: Dict[str, Any], key: str) -> int:
    counters = context.setdefault("metrics", {})
    value = int(counters.get(key, 0)) + 1
    counters[key] = value
    context["metrics"] = counters
    return value

