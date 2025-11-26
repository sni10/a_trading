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
