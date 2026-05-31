"""Тесты для OrderSyncService.apply_exchange_order_to_local / apply_exchange_order."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.domain.entities.order import Order
from src.domain.services.order_sync_service import OrderSyncService


def _make_ccxt_response(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "EX-100",
        "symbol": "BTC/USDT",
        "status": "open",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0,
        "average": None,
        "filled": 0.0,
        "remaining": 1.0,
        "cost": 0.0,
        "timestamp": 5000,
        "datetime": "2025-06-01T00:00:05Z",
        "lastTradeTimestamp": None,
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "triggerPrice": None,
        "fee": None,
        "trades": None,
        "info": {},
    }
    base.update(overrides)
    return base


def _build_service() -> tuple[OrderSyncService, MagicMock, MagicMock]:
    order_repo = MagicMock()
    exchange = MagicMock()
    logger = MagicMock()
    service = OrderSyncService(order_repo=order_repo, exchange=exchange, logger=logger)
    return service, order_repo, logger


class TestApplyExchangeOrderToLocal:
    """Тесты apply_exchange_order_to_local."""

    def test_updates_order_and_persists(self) -> None:
        service, order_repo, _ = _build_service()
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=1.0, price=50000.0)
        resp = _make_ccxt_response()
        context: dict[str, Any] = {}

        service.apply_exchange_order_to_local(order, resp, symbol="BTC/USDT", context=context)

        assert order.exchange_order_id == "EX-100"
        assert order.status == "open"
        assert order.timestamp == 5000
        order_repo.upsert.assert_called_once_with(order)

    def test_rejects_stale_and_does_not_persist(self) -> None:
        service, order_repo, _ = _build_service()
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=1.0, timestamp=9999)
        resp = _make_ccxt_response(timestamp=5000)
        context: dict[str, Any] = {}

        service.apply_exchange_order_to_local(order, resp, symbol="BTC/USDT", context=context)

        assert order.timestamp == 9999  # не изменился
        order_repo.upsert.assert_not_called()

    def test_mutates_same_object(self) -> None:
        """Проверяем мутацию in-place: Deal.buy_order и context ссылаются на один объект."""
        service, _, _ = _build_service()
        order = Order(symbol="BTC/USDT", side="buy", type="limit", amount=1.0, price=50000.0)
        context: dict[str, Any] = {"orders": {"BTC/USDT": [order]}}

        service.apply_exchange_order_to_local(order, _make_ccxt_response(), symbol="BTC/USDT", context=context)

        # Тот же объект в context тоже обновился
        assert context["orders"]["BTC/USDT"][0].exchange_order_id == "EX-100"
        assert context["orders"]["BTC/USDT"][0] is order


class TestApplyExchangeOrder:
    """Тесты apply_exchange_order (из стрима)."""

    def test_finds_and_updates_existing_order(self) -> None:
        service, order_repo, _ = _build_service()
        order = Order(
            symbol="BTC/USDT", side="buy", type="limit", amount=1.0,
            exchange_order_id="EX-100", timestamp=1000,
        )
        context: dict[str, Any] = {"orders": {"BTC/USDT": [order]}}
        resp = _make_ccxt_response(timestamp=5000, status="closed", filled=1.0, remaining=0.0)

        service.apply_exchange_order(resp, symbol="BTC/USDT", context=context)

        assert order.status == "closed"
        assert order.filled == 1.0
        assert order.timestamp == 5000
        order_repo.upsert.assert_called_once_with(order)

    def test_skips_when_order_not_found(self) -> None:
        service, order_repo, _ = _build_service()
        context: dict[str, Any] = {"orders": {"BTC/USDT": []}}
        resp = _make_ccxt_response(id="UNKNOWN-999")

        service.apply_exchange_order(resp, symbol="BTC/USDT", context=context)

        order_repo.upsert.assert_not_called()

    def test_rejects_stale_stream_update(self) -> None:
        service, order_repo, _ = _build_service()
        order = Order(
            symbol="BTC/USDT", side="buy", type="limit", amount=1.0,
            exchange_order_id="EX-100", timestamp=9999,
        )
        context: dict[str, Any] = {"orders": {"BTC/USDT": [order]}}
        resp = _make_ccxt_response(timestamp=5000)

        service.apply_exchange_order(resp, symbol="BTC/USDT", context=context)

        assert order.timestamp == 9999  # не затёрт
        order_repo.upsert.assert_not_called()

    def test_empty_id_ignored(self) -> None:
        service, order_repo, _ = _build_service()
        context: dict[str, Any] = {"orders": {"BTC/USDT": []}}
        resp = _make_ccxt_response(id="")

        service.apply_exchange_order(resp, symbol="BTC/USDT", context=context)

        order_repo.upsert.assert_not_called()
