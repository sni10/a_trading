from __future__ import annotations

"""Боевой центр принятия решений (BUY/HOLD)."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.logger import ILogger
from src.domain.services.market_data.order_book_analyzer import (
    OrderBookAnalyzer,
    OrderBookSignal,
)
from src.domain.services.market_data.order_book_provider import (
    get_order_book_from_context,
)
from src.domain.services.risk.risk_manager import RiskManager
from src.domain.services.trading.signal_cooldown_manager import SignalCooldownManager
from src.domain.services.trading.strategy_calculator import (
    StrategyCalculator,
    StrategyCalculationFailure,
)


@dataclass(frozen=True)
class DecisionPayload:
    """Собранные данные для решения BUY."""

    buy_price: float
    buy_amount: float
    sell_price: float
    sell_amount: float
    budget: float | None
    net_profit: float | None


class DecisionCenter:
    """Принимает BUY/HOLD решение с учётом сигналов и лимитов."""

    def __init__(
        self,
        *,
        orderbook_analyzer: OrderBookAnalyzer | None = None,
        cooldown_manager: SignalCooldownManager | None = None,
        calculator: StrategyCalculator | None = None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self._orderbook_analyzer = orderbook_analyzer or OrderBookAnalyzer()
        self._cooldown_manager = cooldown_manager or SignalCooldownManager()
        self._calculator = calculator or StrategyCalculator()
        self._risk_manager = risk_manager or RiskManager()

    def decide(
        self,
        intents: Iterable[Dict[str, Any]],
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
        logger: ILogger | None = None,
    ) -> Dict[str, Any]:
        """Принять решение BUY/HOLD на основе intents и контекста."""

        ts = context.get("market", {}).get(symbol, {}).get("ts")
        base_hold = {"action": "HOLD", "reason": "no_action", "ts": ts}
        buy_intent = self._select_buy_intent(intents)
        if buy_intent is None:
            return base_hold
        order_block_reason = self._check_order_blocks(context, symbol)
        if order_block_reason:
            return {"action": "HOLD", "reason": order_block_reason, "ts": ts}
        limit_reason = self._check_limits_and_cooldown(context, symbol, ts)
        if limit_reason:
            return {"action": "HOLD", "reason": limit_reason, "ts": ts}
        orderbook_signal = self._check_orderbook(context, symbol)
        if orderbook_signal in {OrderBookSignal.REJECT, OrderBookSignal.WEAK_SELL, OrderBookSignal.STRONG_SELL}:
            return {"action": "HOLD", "reason": "orderbook_reject", "ts": ts}
        price = self._get_last_price(context, symbol)
        if price is None:
            return {"action": "HOLD", "reason": "no_price", "ts": ts}
        payload = self._build_payload(context, symbol, price)
        if isinstance(payload, StrategyCalculationFailure):
            return {"action": "HOLD", "reason": payload.reason, "ts": ts}
        risk_decision = self._risk_manager.evaluate_buy(
            context,
            symbol=symbol,
            buy_price=payload.buy_price,
            buy_amount=payload.buy_amount,
            budget=payload.budget,
        )
        if not risk_decision.allowed:
            return {"action": "HOLD", "reason": risk_decision.reason, "ts": ts}
        decision = self._build_decision(
            buy_intent=buy_intent,
            payload=payload,
            orderbook_signal=orderbook_signal,
            ts=ts,
        )
        if logger:
            logger.log_info(
                f"🧩 [ORCH] BUY подтверждён | ticker_id: {ticker_id} | symbol: {symbol} | "
                f"price: {payload.buy_price:.8f} | confidence: {decision.get('confidence')}"
            )
        return decision

    def _select_buy_intent(self, intents: Iterable[Dict[str, Any]]) -> Dict[str, Any] | None:
        buy_intents = [
            intent for intent in intents if str(intent.get("action")).upper() == "BUY"
        ]
        if not buy_intents:
            return None
        return max(buy_intents, key=lambda item: _safe_float(item.get("confidence", 0.0)))

    def _check_limits_and_cooldown(
        self,
        context: Dict[str, Any],
        symbol: str,
        ts: int | None,
    ) -> str | None:
        pair = self._get_pair(context, symbol)
        max_deals = pair.deal_count if pair else None
        active_deals = self._get_active_deals(context, symbol)

        risk_cfg = context.get("risk", {}).get(symbol) or {}
        cooldown_sec = risk_cfg.get("buy_cooldown_sec")
        last_buy_ts = risk_cfg.get("last_buy_ts")

        decision = self._cooldown_manager.can_buy(
            active_deals_count=active_deals,
            max_deals=max_deals,
            last_buy_ts=last_buy_ts,
            now_ts=ts,
            cooldown_sec=cooldown_sec,
        )
        return None if decision.allowed else decision.reason

    def _check_orderbook(self, context: Dict[str, Any], symbol: str) -> OrderBookSignal | None:
        order_book = get_order_book_from_context(context, symbol=symbol)
        if not order_book:
            return OrderBookSignal.REJECT
        metrics = self._orderbook_analyzer.analyze(order_book)
        return metrics.signal if metrics else OrderBookSignal.REJECT

    def _get_last_price(self, context: Dict[str, Any], symbol: str) -> float | None:
        indicators = (context.get("indicators") or {}).get(symbol) or {}
        price = indicators.get("price")
        if price is not None:
            return float(price)
        market = (context.get("market") or {}).get(symbol) or {}
        last_price = market.get("last_price")
        return float(last_price) if last_price is not None else None

    def _build_payload(
        self, context: Dict[str, Any], symbol: str, price: float
    ) -> DecisionPayload | StrategyCalculationFailure:
        pair = self._get_pair(context, symbol)
        if pair is None:
            return StrategyCalculationFailure("pair_not_loaded")

        budget = pair.deal_quota
        profit_markup = pair.profit_markup
        min_step = pair.min_step
        price_step = pair.price_step

        risk_cfg = context.get("risk", {}).get(symbol) or {}
        buy_fee_percent = _safe_float(risk_cfg.get("buy_fee_percent", 0.1))
        sell_fee_percent = _safe_float(risk_cfg.get("sell_fee_percent", 0.1))

        result = self._calculator.calculate(
            buy_price=price,
            budget=budget,
            min_step=min_step,
            price_step=price_step,
            buy_fee_percent=buy_fee_percent,
            sell_fee_percent=sell_fee_percent,
            profit_percent=profit_markup,
        )
        if isinstance(result, StrategyCalculationFailure):
            return result

        return DecisionPayload(
            buy_price=result.buy_price,
            buy_amount=result.buy_amount,
            sell_price=result.sell_price,
            sell_amount=result.sell_amount,
            budget=budget,
            net_profit=result.net_profit,
        )

    def _build_decision(
        self,
        *,
        buy_intent: Dict[str, Any],
        payload: DecisionPayload,
        orderbook_signal: OrderBookSignal | None,
        ts: int | None,
    ) -> Dict[str, Any]:
        reasons = []
        intent_reason = buy_intent.get("reason")
        if intent_reason:
            reasons.append(str(intent_reason))
        if orderbook_signal is not None:
            reasons.append(f"orderbook_{orderbook_signal.value.lower()}")

        confidence = _safe_float(buy_intent.get("confidence", 0.0))
        if orderbook_signal in {OrderBookSignal.STRONG_BUY, OrderBookSignal.WEAK_BUY}:
            confidence = min(1.0, confidence + 0.1)

        params = dict(buy_intent.get("params") or {})
        params.setdefault("price", payload.buy_price)
        if payload.budget is not None:
            params.setdefault("budget", payload.budget)
        params.setdefault("amount", payload.buy_amount)
        params.setdefault("sell_amount", payload.sell_amount)
        params.setdefault("target_sell_price", payload.sell_price)
        if payload.net_profit is not None:
            params.setdefault("net_profit", payload.net_profit)
        if orderbook_signal is not None:
            params.setdefault("orderbook_signal", orderbook_signal.value)

        return {
            "action": "BUY",
            "reason": "; ".join(reasons) if reasons else "signal_confirmed",
            "confidence": round(confidence, 2),
            "params": params,
            "ts": ts,
        }

    def _get_pair(self, context: Dict[str, Any], symbol: str) -> CurrencyPair | None:
        pairs = context.get("pairs") or {}
        pair = pairs.get(symbol)
        return pair if isinstance(pair, CurrencyPair) else None

    def _get_active_deals(self, context: Dict[str, Any], symbol: str) -> int:
        deals = (context.get("deals") or {}).get(symbol) or []
        active_deals = [
            deal
            for deal in deals
            if getattr(deal, "is_active", None) and deal.is_active()
        ]
        return len(active_deals)

    def _check_order_blocks(self, context: Dict[str, Any], symbol: str) -> str | None:
        orders = (context.get("orders") or {}).get(symbol) or []
        has_unclosed_sell = any(
            str(getattr(order, "side", "")).lower() == "sell"
            and str(getattr(order, "status", "")).lower() not in {"closed", "canceled"}
            for order in orders
        )
        if has_unclosed_sell:
            return "sell_not_closed"
        has_open_orders = any(
            str(getattr(order, "status", "")).lower() == "open"
            for order in orders
        )
        if has_open_orders:
            return "open_orders_blocked"
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = ["DecisionCenter"]
