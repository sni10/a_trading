"""Тесты таймаута BUY-ордера."""

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.services.orders.buy_order_timeout_service import cancel_stale_buy_orders


def test_cancel_stale_buy_orders_cancels_deal_and_orders():
    now_ts = 1_700_000_000_000
    buy_order = Order(
        id=1,
        symbol="ETH/USDT",
        timestamp=now_ts - 31_000,
        status="open",
        side="buy",
        type="limit",
        amount=1.0,
        filled=0.0,
        remaining=1.0,
        cost=100.0,
    )
    sell_order = Order(
        id=2,
        symbol="ETH/USDT",
        timestamp=now_ts - 31_000,
        status="open",
        side="sell",
        type="limit",
        amount=1.0,
        filled=0.0,
        remaining=1.0,
        cost=100.0,
    )
    deal = Deal(
        id=10,
        symbol="ETH/USDT",
        status=Deal.STATUS_PENDING,
        created_at=now_ts - 31_000,
        buy_order=buy_order,
        sell_order=sell_order,
    )

    context = {
        "orders": {"ETH/USDT": [buy_order, sell_order]},
        "deals": {"ETH/USDT": [deal]},
    }

    result = cancel_stale_buy_orders(
        context,
        symbol="ETH/USDT",
        now_ts=now_ts,
        timeout_sec=30.0,
    )

    assert result.canceled_orders == 2
    assert result.canceled_deals == 1
    assert buy_order.status == "canceled"
    assert sell_order.status == "canceled"
    assert deal.status == Deal.STATUS_CANCELED
    assert context["orders"]["ETH/USDT"] == [buy_order, sell_order]
