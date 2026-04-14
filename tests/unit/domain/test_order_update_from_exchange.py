"""Тесты для Order.update_from_exchange() и timestamp guard."""

from __future__ import annotations

import warnings
from typing import Any

from src.domain.entities.order import Order, OrderFee


def _make_ccxt_response(**overrides: Any) -> dict[str, Any]:
    """Фабрика минимального CCXT unified order dict."""
    base: dict[str, Any] = {
        "id": "EX-123",
        "symbol": "BTC/USDT",
        "status": "open",
        "side": "buy",
        "type": "limit",
        "amount": 0.5,
        "price": 50000.0,
        "average": None,
        "filled": 0.0,
        "remaining": 0.5,
        "cost": 0.0,
        "timestamp": 1000,
        "datetime": "2025-01-01T00:00:01Z",
        "lastTradeTimestamp": None,
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "triggerPrice": None,
        "fee": None,
        "trades": None,
        "info": {"raw": True},
    }
    base.update(overrides)
    return base


class TestUpdateFromExchange:
    """Тесты метода update_from_exchange."""

    def test_applies_fields_from_ccxt_response(self) -> None:
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5, price=50000.0)
        resp = _make_ccxt_response()

        result = order.update_from_exchange(resp)

        assert result is True
        assert order.exchange_order_id == "EX-123"
        assert order.status == "open"
        assert order.filled == 0.0
        assert order.remaining == 0.5
        assert order.timestamp == 1000
        assert order.datetime == "2025-01-01T00:00:01Z"
        assert order.time_in_force == "GTC"

    def test_rejects_stale_data(self) -> None:
        """Timestamp guard: обновление с более старым timestamp отклоняется."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5, timestamp=2000)
        resp = _make_ccxt_response(timestamp=1000)

        result = order.update_from_exchange(resp)

        assert result is False
        assert order.timestamp == 2000  # не изменился
        assert order.exchange_order_id is None  # не обновился

    def test_rejects_equal_timestamp(self) -> None:
        """Timestamp guard: обновление с тем же timestamp тоже отклоняется."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5, timestamp=1000)
        resp = _make_ccxt_response(timestamp=1000)

        result = order.update_from_exchange(resp)

        assert result is False

    def test_accepts_newer_timestamp(self) -> None:
        """Более новый timestamp принимается."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5, timestamp=1000)
        resp = _make_ccxt_response(timestamp=2000, status="closed", filled=0.5, remaining=0.0, cost=25000.0)

        result = order.update_from_exchange(resp)

        assert result is True
        assert order.timestamp == 2000
        assert order.status == "closed"
        assert order.filled == 0.5
        assert order.cost == 25000.0

    def test_first_update_always_accepted(self) -> None:
        """Первое обновление (timestamp=0) всегда принимается."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5)
        assert order.timestamp == 0

        resp = _make_ccxt_response(timestamp=500)
        result = order.update_from_exchange(resp)

        assert result is True
        assert order.exchange_order_id == "EX-123"

    def test_parses_fee(self) -> None:
        resp = _make_ccxt_response(fee={"currency": "USDT", "cost": 0.5, "rate": 0.001})
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5)
        order.update_from_exchange(resp)

        assert order.fee is not None
        assert order.fee.currency == "USDT"
        assert order.fee.cost == 0.5
        assert order.fee.rate == 0.001

    def test_parses_trades_list(self) -> None:
        resp = _make_ccxt_response(trades=[{"id": "T1"}, {"id": "T2"}])
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5)
        order.update_from_exchange(resp)

        assert order.trades == ["T1", "T2"]

    def test_preserves_deal_id(self) -> None:
        """update_from_exchange не трогает deal_id — он управляется доменом."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5, deal_id=42)
        resp = _make_ccxt_response()
        order.update_from_exchange(resp)

        assert order.deal_id == 42

    def test_preserves_internal_id(self) -> None:
        """update_from_exchange не трогает id (autoincrement из БД)."""
        order = Order(id=7, symbol="BTC/USDT", side="buy", type="limit", amount=0.5)
        resp = _make_ccxt_response()
        order.update_from_exchange(resp)

        assert order.id == 7

    def test_mutates_in_place(self) -> None:
        """Проверяем, что update_from_exchange мутирует тот же объект (не создаёт новый)."""
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=0.5)
        original_id = id(order)
        resp = _make_ccxt_response()
        order.update_from_exchange(resp)

        assert id(order) == original_id


class TestFromCcxtDeprecation:
    """from_ccxt должен работать, но выдавать DeprecationWarning."""

    def test_from_ccxt_emits_deprecation_warning(self) -> None:
        resp = _make_ccxt_response()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            order = Order.from_ccxt(resp)

        assert len(caught) == 1
        assert issubclass(caught[0].category, DeprecationWarning)
        assert "deprecated" in str(caught[0].message).lower()
        assert order.exchange_order_id == "EX-123"
