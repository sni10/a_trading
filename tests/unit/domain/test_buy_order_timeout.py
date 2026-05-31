"""Тесты таймаута BUY-ордера."""

from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.services.orders.buy_order_timeout_service import cancel_stale_buy_orders


def _make_order(id, side="buy", status="open", exchange_order_id=None, timestamp=0):
    return Order(
        id=id,
        symbol="ETH/USDT",
        timestamp=timestamp,
        status=status,
        side=side,
        type="limit",
        amount=1.0,
        filled=0.0,
        remaining=1.0,
        cost=100.0,
        exchange_order_id=exchange_order_id,
    )


def _make_deal(id, buy_order, sell_order, timestamp=0):
    deal = Deal(
        id=id,
        symbol="ETH/USDT",
        status=Deal.STATUS_PENDING,
        created_at=timestamp,
        buy_order=buy_order,
        sell_order=sell_order,
    )
    return deal


def test_pending_order_not_canceled_by_exchange_timeout():
    """Ордер без exchange_order_id НЕ отменяется основным таймаутом."""
    now_ts = 1_700_000_000_000
    buy_order = _make_order(1, timestamp=now_ts - 31_000)
    sell_order = _make_order(2, side="sell", timestamp=now_ts - 31_000)
    deal = _make_deal(10, buy_order, sell_order, timestamp=now_ts - 31_000)

    context = {
        "orders": {"ETH/USDT": [buy_order, sell_order]},
        "deals": {"ETH/USDT": [deal]},
    }

    result = cancel_stale_buy_orders(
        context,
        symbol="ETH/USDT",
        now_ts=now_ts,
        timeout_sec=30.0,
        pending_send_timeout_sec=0,  # отключён
    )

    assert result.canceled_orders == 0
    assert result.canceled_deals == 0
    assert buy_order.status == "open"
    assert deal.status != Deal.STATUS_CANCELED
    assert result.exchange_order_ids_to_cancel == []


def test_pending_order_canceled_by_pending_send_timeout():
    """Ордер без exchange_order_id отменяется pending_send_timeout."""
    now_ts = 1_700_000_000_000
    buy_order = _make_order(1, timestamp=now_ts - 11_000)
    sell_order = _make_order(2, side="sell", timestamp=now_ts - 11_000)
    deal = _make_deal(10, buy_order, sell_order, timestamp=now_ts - 11_000)

    context = {
        "orders": {"ETH/USDT": [buy_order, sell_order]},
        "deals": {"ETH/USDT": [deal]},
    }

    result = cancel_stale_buy_orders(
        context,
        symbol="ETH/USDT",
        now_ts=now_ts,
        timeout_sec=30.0,
        pending_send_timeout_sec=10.0,
    )

    assert result.canceled_orders == 2
    assert result.canceled_deals == 1
    assert buy_order.status == "canceled"
    assert sell_order.status == "canceled"
    assert deal.status == Deal.STATUS_CANCELED
    # Нет exchange_order_id — нечего отменять на бирже
    assert result.exchange_order_ids_to_cancel == []


def test_exchange_order_canceled_and_collected():
    """Ордер с exchange_order_id отменяется и его ID попадает в список на отмену."""
    now_ts = 1_700_000_000_000
    buy_order = _make_order(
        1, exchange_order_id="EX123", timestamp=now_ts - 31_000
    )
    sell_order = _make_order(2, side="sell", timestamp=now_ts - 31_000)
    deal = _make_deal(10, buy_order, sell_order, timestamp=now_ts - 31_000)

    context = {
        "orders": {"ETH/USDT": [buy_order, sell_order]},
        "deals": {"ETH/USDT": [deal]},
    }

    result = cancel_stale_buy_orders(
        context,
        symbol="ETH/USDT",
        now_ts=now_ts,
        timeout_sec=30.0,
        pending_send_timeout_sec=10.0,
    )

    assert result.canceled_orders == 2
    assert result.canceled_deals == 1
    assert buy_order.status == "canceled"
    assert deal.status == Deal.STATUS_CANCELED
    assert result.exchange_order_ids_to_cancel == ["EX123"]


def test_exchange_order_not_timed_out_yet():
    """Ордер с exchange_order_id, но время ещё не вышло — не отменяется."""
    now_ts = 1_700_000_000_000
    buy_order = _make_order(
        1, exchange_order_id="EX456", timestamp=now_ts - 10_000
    )
    sell_order = _make_order(2, side="sell", timestamp=now_ts - 10_000)
    deal = _make_deal(10, buy_order, sell_order, timestamp=now_ts - 10_000)

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

    assert result.canceled_orders == 0
    assert buy_order.status == "open"
    assert result.exchange_order_ids_to_cancel == []


def test_cancel_stale_buy_orders_cancels_deal_and_orders():
    """Обратная совместимость: без pending_send_timeout ордера без exchange_id не отменяются."""
    now_ts = 1_700_000_000_000
    buy_order = _make_order(1, timestamp=now_ts - 31_000)
    sell_order = _make_order(2, side="sell", timestamp=now_ts - 31_000)
    deal = _make_deal(10, buy_order, sell_order, timestamp=now_ts - 31_000)

    context = {
        "orders": {"ETH/USDT": [buy_order, sell_order]},
        "deals": {"ETH/USDT": [deal]},
    }

    # Без pending_send_timeout_sec (по умолчанию 0) —
    # ордера без exchange_order_id не отменяются exchange timeout
    result = cancel_stale_buy_orders(
        context,
        symbol="ETH/USDT",
        now_ts=now_ts,
        timeout_sec=30.0,
    )

    assert result.canceled_orders == 0
    assert buy_order.status == "open"
