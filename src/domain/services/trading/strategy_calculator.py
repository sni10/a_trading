from __future__ import annotations

"""Калькулятор BUY/SELL параметров по формулам из старого проекта."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


@dataclass(frozen=True)
class StrategyCalculation:
    """Результат расчёта BUY/SELL."""

    buy_price: float
    buy_price_with_fee: float
    buy_amount: float
    sell_price: float
    sell_amount: float
    total_usdt_needed: float
    final_revenue: float
    net_profit: float


@dataclass(frozen=True)
class StrategyCalculationFailure:
    """Ошибка расчёта стратегии."""

    reason: str


class StrategyCalculator:
    """Повторяет логику calculate_strategy из bad_example."""

    def calculate(
        self,
        *,
        buy_price: float,
        budget: float,
        min_step: float,
        price_step: float,
        buy_fee_percent: float,
        sell_fee_percent: float,
        profit_percent: float,
    ) -> StrategyCalculation | StrategyCalculationFailure:
        # 0) Приведение к Decimal
        buy_price_d = Decimal(str(buy_price))
        budget_d = Decimal(str(budget))
        min_step_d = Decimal(str(min_step))
        price_step_d = Decimal(str(price_step))
        buy_fee_d = Decimal(str(buy_fee_percent))
        sell_fee_d = Decimal(str(sell_fee_percent))
        profit_d = Decimal(str(profit_percent))

        # 1) Проверки входных данных
        if buy_price_d <= 0 or budget_d <= 0 or min_step_d <= 0 or price_step_d <= 0:
            return StrategyCalculationFailure("invalid_inputs")

        # 2) Цена покупки с учётом комиссии
        buy_price_with_fee = buy_price_d * (1 + buy_fee_d / Decimal("100"))
        buy_price_with_fee = round_to_step(buy_price_with_fee, price_step_d)

        # 3) Желаемая цена продажи
        sell_price_raw = buy_price_d * (1 + profit_d / Decimal("100"))
        sell_price = round_to_step(sell_price_raw, price_step_d)

        # 4) Максимальный объём продажи (после комиссии)
        raw_max_x = (budget_d / buy_price_with_fee) * (1 - sell_fee_d / Decimal("100"))
        sell_amount = floor_to_step(raw_max_x, min_step_d)
        if sell_amount <= 0:
            return StrategyCalculationFailure("amount_too_small")

        # 5) Нужно купить чуть больше, чтобы после комиссии осталось sell_amount
        buy_amount = sell_amount / (1 - sell_fee_d / Decimal("100"))
        buy_amount = floor_to_step(buy_amount, min_step_d)

        # 6) Сколько USDT уйдёт на покупку
        total_usdt_needed = buy_amount * buy_price_with_fee
        total_usdt_needed = round_to_step(total_usdt_needed, price_step_d)
        if total_usdt_needed > budget_d:
            return StrategyCalculationFailure("insufficient_budget")

        # 7) Финальная выручка
        final_revenue = sell_amount * sell_price
        final_revenue = round_to_step(final_revenue, price_step_d)

        # 8) Чистая прибыль
        net_profit = final_revenue - total_usdt_needed
        min_required_profit = budget_d * Decimal("0.005")
        if net_profit < min_required_profit:
            return StrategyCalculationFailure("insufficient_profit")

        return StrategyCalculation(
            buy_price=float(buy_price_d),
            buy_price_with_fee=float(buy_price_with_fee),
            buy_amount=float(buy_amount),
            sell_price=float(sell_price),
            sell_amount=float(sell_amount),
            total_usdt_needed=float(total_usdt_needed),
            final_revenue=float(final_revenue),
            net_profit=float(net_profit),
        )


def round_to_step(value: Decimal, step: Decimal) -> Decimal:
    steps = (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return steps * step


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    steps = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return steps * step


__all__ = ["StrategyCalculator", "StrategyCalculation", "StrategyCalculationFailure"]
