from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.application.services.ticker_pipeline_service import TickPipelineService
from src.config.config import AppConfig
from src.domain.services.context.state import init_context


@pytest.fixture()
def base_context() -> Dict[str, Any]:
    """Базовый in-memory контекст для тестов конвейера по тику."""

    cfg = AppConfig()
    return init_context(cfg)


def test_process_ticker_does_not_execute_on_hold(monkeypatch, base_context) -> None:
    """При действии HOLD execute не должен вызываться."""

    import src.application.services.ticker_pipeline_service as tps

    executed: List[Dict[str, Any]] = []

    def fake_evaluate_strategies(context: Dict[str, Any], *, ticker_id: int, symbol: str):
        return [
            {
                "action": "HOLD",
                "confidence": 0.5,
                "reason": "test_hold",
                "params": {},
            }
        ]

    def fake_decide(
        intents: List[Dict[str, Any]],
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
    ) -> Dict[str, Any]:
        # Решение явно сигнализирует HOLD.
        return {"action": "HOLD", "reason": "no_trade"}

    def fake_execute(
        decision: Dict[str, Any],
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
    ) -> None:  # pragma: no cover - не должен вызываться в этом тесте
        executed.append(
            {
                "decision": decision,
                "ticker_id": ticker_id,
                "symbol": symbol,
            }
        )

    monkeypatch.setattr(tps, "evaluate_strategies", fake_evaluate_strategies)
    monkeypatch.setattr(tps, "decide", fake_decide)
    monkeypatch.setattr(tps, "execute", fake_execute)

    cfg = AppConfig()
    service = TickPipelineService(cfg)

    ticker_id = 1
    symbol = cfg.symbol
    price = 100.0
    ts = 1_700_000_000_000

    service.process_tick(
        base_context,
        symbol=symbol,
        ticker_id=ticker_id,
        price=price,
        ts=ts,
    )

    # execute не вызывался
    assert executed == []

    # Intents и решение сохранены в контекст и историю.
    intents = base_context["intents"][symbol]
    assert len(intents) == 1
    assert intents[0]["action"] == "HOLD"

    decision = base_context["decisions"][symbol]
    assert decision["action"] == "HOLD"

    intents_history = base_context["intents_history"][symbol]
    decisions_history = base_context["decisions_history"][symbol]
    assert len(intents_history) == 1
    assert len(decisions_history) == 1

    # Метрики обновлены на текущий ticker_id.
    assert base_context["metrics"]["ticks"] == ticker_id


def test_process_ticker_executes_on_non_hold(monkeypatch, base_context) -> None:
    """При действии BUY/SELL execute вызывается ровно один раз с корректными параметрами."""

    import src.application.services.ticker_pipeline_service as tps

    calls: List[Dict[str, Any]] = []

    def fake_evaluate_strategies(context: Dict[str, Any], *, ticker_id: int, symbol: str):
        return [
            {
                "action": "BUY",
                "confidence": 0.9,
                "reason": "test_buy",
                "params": {"budget": 123},
            }
        ]

    def fake_decide(
        intents: List[Dict[str, Any]],
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
    ) -> Dict[str, Any]:
        assert intents and intents[0]["action"] == "BUY"
        return {"action": "BUY", "reason": "ok", "volume": 1.0}

    def fake_execute(
        decision: Dict[str, Any],
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
    ) -> None:
        calls.append(
            {
                "decision": decision,
                "context": context,
                "ticker_id": ticker_id,
                "symbol": symbol,
            }
        )

    monkeypatch.setattr(tps, "evaluate_strategies", fake_evaluate_strategies)
    monkeypatch.setattr(tps, "decide", fake_decide)
    monkeypatch.setattr(tps, "execute", fake_execute)

    cfg = AppConfig()
    service = TickPipelineService(cfg)

    ticker_id = 5
    symbol = cfg.symbol
    price = 250.5
    ts = 1_700_000_100_000

    service.process_tick(
        base_context,
        symbol=symbol,
        ticker_id=ticker_id,
        price=price,
        ts=ts,
    )

    # execute вызван ровно один раз
    assert len(calls) == 1
    call = calls[0]

    assert call["ticker_id"] == ticker_id
    assert call["symbol"] == symbol
    assert call["decision"]["action"] == "BUY"
    assert call["decision"]["reason"] == "ok"

    # В контексте сохранены intents и решение.
    intents = base_context["intents"][symbol]
    assert len(intents) == 1
    assert intents[0]["action"] == "BUY"

    decision = base_context["decisions"][symbol]
    assert decision["action"] == "BUY"

    # Метрики обновлены.
    assert base_context["metrics"]["ticks"] == ticker_id
