"""Юнит-тесты для оркестратора (DecisionCenter через decide).

Проверяем чистую бизнес-логику без внешнего I/O.
"""

import pytest

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.entities.deal import Deal
from src.domain.services.orchestrator.orchestrator import decide


class _FakeMarketCache:
    def __init__(self, orderbook, symbol: str):
        self._orderbook = orderbook
        self.symbol = symbol

    def update_ticker(self, ticker):
        del ticker

    def get_ticker(self):
        return None

    def update_orderbook(self, orderbook):
        self._orderbook = orderbook

    def get_orderbook(self):
        return self._orderbook

    def add_trade(self, trade):
        del trade

    def get_trades(self, limit=None):
        del limit
        return []

    def add_bar(self, bar):
        del bar

    def get_bars(self, limit=None):
        del limit
        return []


def _neutral_orderbook(symbol: str, price: float = 100.0):
    return {
        "bids": [[price, 5.0], [price - 0.1, 5.0]],
        "asks": [[price + 0.1, 5.0], [price + 0.2, 5.0]],
        "timestamp": 111,
        "symbol": symbol,
    }


@pytest.mark.unit
def test_decide_returns_hold_when_no_intents():
    """Когда нет интентов, оркестратор возвращает HOLD."""
    intents = []
    context = {"market": {"BTC/USDT": {"ts": 1234567890}}}

    result = decide(intents, context, ticker_id=1, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "no_action"


@pytest.mark.unit
def test_decide_returns_hold_when_all_intents_are_hold():
    """Когда все интенты HOLD, оркестратор возвращает HOLD."""
    intents = [
        {"action": "HOLD", "reason": "no_signal"},
        {"action": "HOLD", "reason": "cooldown"},
    ]
    context = {"market": {"BTC/USDT": {"ts": 1234567890}}}

    result = decide(intents, context, ticker_id=2, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "no_action"


@pytest.mark.unit
def test_decide_ignores_sell_intents():
    """SELL-интенты не приводят к BUY-решениям."""
    intents = [{"action": "SELL", "reason": "take_profit"}]
    context = {"market": {"BTC/USDT": {"ts": 1234567890, "last_price": 100.0}}}

    result = decide(intents, context, ticker_id=3, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "no_action"


@pytest.mark.unit
def test_decide_builds_buy_decision_with_budget_and_target():
    """BUY-решение включает расчёт суммы и целевой цены продажи."""
    intents = [{"action": "BUY", "reason": "growth_signal", "confidence": 0.7}]
    context = {
        "market": {"ETH/USDT": {"ts": 9876543210, "last_price": 100.0}},
        "pairs": {
            "ETH/USDT": CurrencyPair(
                symbol="ETH/USDT",
                base_currency="ETH",
                quote_currency="USDT",
                deal_quota=50.0,
                profit_markup=1.5,
                min_step=0.001,
                price_step=0.01,
            )
        },
        "market_caches": {
            "ETH/USDT": _FakeMarketCache(_neutral_orderbook("ETH/USDT"), "ETH/USDT")
        },
    }

    result = decide(intents, context, ticker_id=4, symbol="ETH/USDT")

    assert result["action"] == "BUY"
    assert result["params"]["budget"] == 50.0
    assert result["params"]["amount"] == pytest.approx(0.499, rel=1e-3)
    assert result["params"]["sell_amount"] == pytest.approx(0.499, rel=1e-3)
    assert result["params"]["target_sell_price"] == 101.5


@pytest.mark.unit
def test_decide_respects_risk_limit_when_amount_within_limit():
    """Если объём сделки не превышает риск-лимит, решение остаётся BUY."""
    intents = [
        {"action": "BUY", "reason": "signal"},
    ]
    context = {
        "market": {"BTC/USDT": {"ts": 2222222222, "last_price": 100.0}},
        "risk": {"BTC/USDT": {"max_amount": 1.0}},
        "pairs": {
            "BTC/USDT": CurrencyPair(
                symbol="BTC/USDT",
                base_currency="BTC",
                quote_currency="USDT",
                deal_quota=50.0,
                profit_markup=1.5,
                min_step=0.001,
                price_step=0.01,
            )
        },
        "market_caches": {
            "BTC/USDT": _FakeMarketCache(_neutral_orderbook("BTC/USDT"), "BTC/USDT")
        },
    }

    result = decide(intents, context, ticker_id=6, symbol="BTC/USDT")

    assert result["action"] == "BUY"
    assert result["reason"].startswith("signal")


@pytest.mark.unit
def test_decide_downgrades_to_hold_when_risk_limit_exceeded():
    """Если объём сделки превышает риск-лимит, решение понижается до HOLD."""
    intents = [
        {"action": "BUY", "reason": "signal"},
    ]
    context = {
        "market": {"BTC/USDT": {"ts": 3333333333, "last_price": 100.0}},
        "risk": {"BTC/USDT": {"max_amount": 0.3}},
        "pairs": {
            "BTC/USDT": CurrencyPair(
                symbol="BTC/USDT",
                base_currency="BTC",
                quote_currency="USDT",
                deal_quota=50.0,
                profit_markup=1.5,
                min_step=0.001,
                price_step=0.01,
            )
        },
        "market_caches": {
            "BTC/USDT": _FakeMarketCache(_neutral_orderbook("BTC/USDT"), "BTC/USDT")
        },
    }

    result = decide(intents, context, ticker_id=7, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "risk_limit_exceeded"
    assert result["ts"] == 3333333333


@pytest.mark.unit
def test_decide_blocks_when_deal_limit_reached():
    """Если достигнут лимит активных сделок, BUY не разрешается."""
    intents = [{"action": "BUY", "reason": "signal"}]
    context = {
        "market": {"BTC/USDT": {"ts": 4444444444, "last_price": 100.0}},
        "pairs": {
            "BTC/USDT": CurrencyPair(
                symbol="BTC/USDT",
                base_currency="BTC",
                quote_currency="USDT",
                deal_count=1,
            )
        },
        "deals": {
            "BTC/USDT": [
                Deal(
                    id=1,
                    symbol="BTC/USDT",
                    status=Deal.STATUS_OPEN,
                    created_at=0,
                )
            ]
        },
    }

    result = decide(intents, context, ticker_id=8, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "deal_limit_reached"


@pytest.mark.unit
def test_decide_blocks_on_orderbook_reject():
    """Негативный сигнал стакана блокирует BUY."""

    intents = [{"action": "BUY", "reason": "signal"}]
    orderbook = {
        "bids": [[100.0, 1.0]],
        "asks": [[120.0, 1.0]],
        "timestamp": 111,
        "symbol": "BTC/USDT",
    }
    context = {
        "market": {"BTC/USDT": {"ts": 5555555555, "last_price": 100.0}},
        "market_caches": {"BTC/USDT": _FakeMarketCache(orderbook, "BTC/USDT")},
    }

    result = decide(intents, context, ticker_id=9, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "orderbook_reject"


@pytest.mark.unit
def test_decide_blocks_on_open_orders():
    """Открытый ордер блокирует BUY."""
    intents = [{"action": "BUY", "reason": "signal"}]
    context = {
        "market": {"BTC/USDT": {"ts": 6666666666, "last_price": 100.0}},
        "orders": {"BTC/USDT": []},
    }

    class _Order:
        def __init__(self):
            self.status = "open"
            self.side = "buy"

    context["orders"]["BTC/USDT"] = [_Order()]

    result = decide(intents, context, ticker_id=10, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "open_orders_blocked"


@pytest.mark.unit
def test_decide_blocks_on_unclosed_sell():
    """Незакрытый sell блокирует BUY."""
    intents = [{"action": "BUY", "reason": "signal"}]
    context = {
        "market": {"BTC/USDT": {"ts": 7777777777, "last_price": 100.0}},
        "orders": {"BTC/USDT": []},
    }

    class _Order:
        def __init__(self):
            self.status = "open"
            self.side = "sell"

    context["orders"]["BTC/USDT"] = [_Order()]

    result = decide(intents, context, ticker_id=11, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "sell_not_closed"


@pytest.mark.unit
def test_decide_blocks_on_cooldown():
    """BUY блокируется, если не истёк cooldown."""
    intents = [{"action": "BUY", "reason": "signal"}]
    now_ts = 8_000_000_000_000
    context = {
        "market": {"BTC/USDT": {"ts": now_ts, "last_price": 100.0}},
        "risk": {
            "BTC/USDT": {
                "buy_cooldown_sec": 120,
                "last_buy_ts": now_ts - 1_000,
            }
        },
        "market_caches": {
            "BTC/USDT": _FakeMarketCache(_neutral_orderbook("BTC/USDT"), "BTC/USDT")
        },
    }

    result = decide(intents, context, ticker_id=12, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "buy_cooldown_active"


@pytest.mark.unit
def test_decide_blocks_on_kill_switch():
    """Kill-switch блокирует BUY."""
    intents = [{"action": "BUY", "reason": "signal"}]
    context = {
        "market": {"BTC/USDT": {"ts": 9_000_000_000_000, "last_price": 100.0}},
        "pairs": {
            "BTC/USDT": CurrencyPair(
                symbol="BTC/USDT",
                base_currency="BTC",
                quote_currency="USDT",
                deal_quota=50.0,
                profit_markup=1.5,
                min_step=0.001,
                price_step=0.01,
            )
        },
        "risk": {
            "BTC/USDT": {
                "kill_switch": True,
            }
        },
        "market_caches": {
            "BTC/USDT": _FakeMarketCache(_neutral_orderbook("BTC/USDT"), "BTC/USDT")
        },
    }

    result = decide(intents, context, ticker_id=13, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "kill_switch"
