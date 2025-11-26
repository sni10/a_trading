"""Юнит-тесты для оркестратора (Orchestrator.decide).

Проверяем чистую бизнес-логику без внешнего I/O.
"""

import pytest
from src.domain.services.orchestrator.orchestrator import decide


@pytest.mark.unit
def test_decide_returns_hold_when_no_intents():
    """Когда нет интентов, оркестратор возвращает HOLD."""
    intents = []
    context = {"market": {"BTC/USDT": {"ts": 1234567890}}}

    result = decide(intents, context, tick_id=1, symbol="BTC/USDT")

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

    result = decide(intents, context, tick_id=2, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "no_action"


@pytest.mark.unit
def test_decide_selects_first_non_hold_action():
    """Оркестратор выбирает первое действие, отличное от HOLD."""
    intents = [
        {"action": "HOLD", "reason": "no_signal"},
        {"action": "BUY", "reason": "ema_crossover", "params": {"amount": 0.001}},
        {"action": "SELL", "reason": "take_profit", "params": {"amount": 0.002}},
    ]
    context = {"market": {"BTC/USDT": {"ts": 1234567890}}}

    result = decide(intents, context, tick_id=3, symbol="BTC/USDT")

    assert result["action"] == "BUY"
    assert result["reason"] == "ema_crossover"
    assert result["params"] == {"amount": 0.001}


@pytest.mark.unit
def test_decide_includes_params_from_intent():
    """Параметры из интента передаются в решение."""
    intents = [
        {
            "action": "SELL",
            "reason": "stop_loss",
            "params": {"amount": 0.5, "price": 50000},
        }
    ]
    context = {"market": {"ETH/USDT": {"ts": 9876543210}}}

    result = decide(intents, context, tick_id=4, symbol="ETH/USDT")

    assert result["action"] == "SELL"
    assert result["reason"] == "stop_loss"
    assert result["params"]["amount"] == 0.5
    assert result["params"]["price"] == 50000


@pytest.mark.unit
def test_decide_handles_missing_params_in_intent():
    """Если в интенте нет params, в решение передаётся пустой dict."""
    intents = [{"action": "BUY", "reason": "manual"}]
    context = {"market": {"SOL/USDT": {"ts": 1111111111}}}

    result = decide(intents, context, tick_id=5, symbol="SOL/USDT")

    assert result["action"] == "BUY"
    assert result["reason"] == "manual"
    assert result["params"] == {}


@pytest.mark.unit
def test_decide_respects_risk_limit_when_amount_within_limit():
    """Если объём сделки не превышает риск-лимит, действие не понижается.

    Оркестратор должен вернуть действие BUY, так как amount <= max_amount.
    """

    intents = [
        {"action": "BUY", "reason": "signal", "params": {"amount": 0.5}},
    ]
    context = {
        "market": {"BTC/USDT": {"ts": 2222222222}},
        "risk": {"BTC/USDT": {"max_amount": 1.0}},
    }

    result = decide(intents, context, tick_id=6, symbol="BTC/USDT")

    assert result["action"] == "BUY"
    assert result["reason"] == "signal"
    assert result["params"]["amount"] == 0.5


@pytest.mark.unit
def test_decide_downgrades_to_hold_when_risk_limit_exceeded():
    """Если объём сделки превышает риск-лимит, решение понижается до HOLD."""

    intents = [
        {"action": "BUY", "reason": "signal", "params": {"amount": 2.0}},
    ]
    context = {
        "market": {"BTC/USDT": {"ts": 3333333333}},
        "risk": {"BTC/USDT": {"max_amount": 1.0}},
    }

    result = decide(intents, context, tick_id=7, symbol="BTC/USDT")

    assert result["action"] == "HOLD"
    assert result["reason"] == "risk_limit_exceeded"
    # ts для HOLD должен соответствовать последнему тику из контекста
    assert result["ts"] == 3333333333
