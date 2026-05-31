"""Симулятор исполнения ордеров для бэктеста.

Логика: на каждом тике проверяет открытые ордера в context и закрывает
те, чья цена достигнута текущей ценой свечи.

Упрощения (MVP):
- Нет частичных исполнений и проскальзывания.
- Нет глубины стакана — ордер исполняется по своей цене.
- BUY исполняется, когда price <= buy_order.price (лимит покупки).
- SELL (тейк) исполняется, когда price >= sell_order.price.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order, OrderFee


class FillSimulator:
    """Симулирует заполнение ордеров по ценовому пересечению.

    Обновляет баланс в context["backtest_balance"] при каждом исполнении.
    """

    def __init__(
        self,
        buy_fee_percent: float = 0.1,
        sell_fee_percent: float = 0.1,
    ) -> None:
        """
        Args:
            buy_fee_percent: Комиссия на покупку, % (0.1 = 0.1%).
            sell_fee_percent: Комиссия на продажу, % (0.1 = 0.1%).
        """
        self._buy_fee = buy_fee_percent / 100.0
        self._sell_fee = sell_fee_percent / 100.0

    def on_tick(
        self,
        context: dict[str, Any],
        symbol: str,
        price: float,
        ts: int,
    ) -> None:
        """Обработать тик: заполнить подходящие ордера, обновить баланс и сделки.

        Args:
            context: In-memory контекст торгового конвейера.
            symbol: Торговая пара.
            price: Цена текущего тика (close свечи).
            ts: Unix timestamp тика в мс.
        """
        deals: list[Deal] = (context.get("deals") or {}).get(symbol) or []

        for deal in deals:
            self._process_deal(context, deal, price, ts)

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _process_deal(
        self,
        context: dict[str, Any],
        deal: Deal,
        price: float,
        ts: int,
    ) -> None:
        """Обработать одну сделку — попробовать закрыть BUY или SELL."""
        if deal.is_closed() or deal.is_canceled():
            return

        buy_order = deal.buy_order
        sell_order = deal.sell_order

        # --- BUY fill ---
        if (
            buy_order is not None
            and buy_order.is_open()
            and buy_order.price is not None
            and price <= buy_order.price
        ):
            self._fill_buy(context, deal, buy_order, price, ts)

        # --- SELL fill (только если BUY уже закрыт) ---
        if (
            deal.is_open()
            and sell_order is not None
            and sell_order.is_open()
            and sell_order.price is not None
            and price >= sell_order.price
        ):
            self._fill_sell(context, deal, sell_order, price, ts)

    def _fill_buy(
        self,
        context: dict[str, Any],
        deal: Deal,
        order: Order,
        price: float,
        ts: int,
    ) -> None:
        """Исполнить BUY-ордер: списать USDT + комиссию с баланса."""
        cost = order.amount * price
        fee_cost = cost * self._buy_fee

        self._update_order_filled(order, price, ts)
        deal.mark_as_open()
        deal.opened_at = ts

        # Списать USDT из баланса
        balance = context.setdefault("backtest_balance", 0.0)
        context["backtest_balance"] = balance - cost - fee_cost

        # Сохранить fee в ордере
        order.fee = OrderFee(currency="USDT", cost=fee_cost, rate=self._buy_fee)

    def _fill_sell(
        self,
        context: dict[str, Any],
        deal: Deal,
        order: Order,
        price: float,
        ts: int,
    ) -> None:
        """Исполнить SELL-ордер: зачислить USDT минус комиссию на баланс."""
        income = order.amount * price
        fee_cost = income * self._sell_fee

        self._update_order_filled(order, price, ts)
        deal.mark_as_closed()
        deal.closed_at = ts

        # Зачислить USDT на баланс
        balance = context.setdefault("backtest_balance", 0.0)
        context["backtest_balance"] = balance + income - fee_cost

        # Сохранить fee в ордере
        order.fee = OrderFee(currency="USDT", cost=fee_cost, rate=self._sell_fee)

    @staticmethod
    def _update_order_filled(order: Order, price: float, ts: int) -> None:
        """Обновить поля ордера при исполнении."""
        order.status = "closed"
        order.filled = order.amount
        order.remaining = 0.0
        order.average = price
        order.cost = round(order.amount * price, 8)
        order.last_trade_timestamp = ts
        iso_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
        order.datetime = iso_time


__all__ = ["FillSimulator"]
