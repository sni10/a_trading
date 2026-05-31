from __future__ import annotations

"""Базовый риск-менеджер для BUY решений."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RiskDecision:
    """Результат проверки рисков."""

    allowed: bool
    reason: str


class RiskManager:
    """Проверяет лимиты и баланс перед BUY."""

    def evaluate_buy(
        self,
        context: Dict[str, Any],
        *,
        symbol: str,
        buy_price: float,
        buy_amount: float,
        budget: float | None,
    ) -> RiskDecision:
        risk_cfg = context.get("risk", {}).get(symbol) or {}

        if _is_kill_switch_enabled(context, symbol):
            return RiskDecision(False, "kill_switch")

        if buy_price <= 0 or buy_amount <= 0:
            return RiskDecision(False, "invalid_order_params")

        max_amount = _safe_float(risk_cfg.get("max_amount"))
        if max_amount is not None and buy_amount > max_amount:
            return RiskDecision(False, "risk_limit_exceeded")

        min_notional = _safe_float(risk_cfg.get("min_notional"))
        notional = buy_price * buy_amount
        if min_notional is not None and notional < min_notional:
            return RiskDecision(False, "min_notional_not_met")

        available_quote = _get_available_quote(context, symbol, risk_cfg)
        if available_quote is not None and budget is not None and budget > available_quote:
            return RiskDecision(False, "insufficient_balance")

        max_daily_loss = _safe_float(risk_cfg.get("max_daily_loss"))
        daily_loss = _safe_float(risk_cfg.get("daily_loss"))
        if max_daily_loss is not None and daily_loss is not None and daily_loss >= max_daily_loss:
            return RiskDecision(False, "daily_loss_limit")

        return RiskDecision(True, "ok")


def _is_kill_switch_enabled(context: Dict[str, Any], symbol: str) -> bool:
    risk_root = context.get("risk", {}) or {}
    risk_cfg = risk_root.get(symbol) or {}
    return bool(risk_root.get("kill_switch") or risk_cfg.get("kill_switch") or risk_cfg.get("trading_paused"))


def _get_available_quote(
    context: Dict[str, Any],
    symbol: str,
    risk_cfg: Dict[str, Any],
) -> float | None:
    value = _safe_float(risk_cfg.get("available_quote"))
    if value is not None:
        return value

    balances = context.get("balances") or {}
    symbol_bal = balances.get(symbol) or {}
    for key in ("quote_available", "quote_free", "free_quote", "free"):
        value = _safe_float(symbol_bal.get(key))
        if value is not None:
            return value
    return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


__all__ = ["RiskManager", "RiskDecision"]
