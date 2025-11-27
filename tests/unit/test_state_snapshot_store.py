from __future__ import annotations

from typing import Any, Dict

from src.domain.services.context.state import (
    apply_state_snapshot,
    init_context,
    make_state_snapshot,
)
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore
from src.config.config import AppConfig


def test_file_state_snapshot_store_save_and_load(tmp_path) -> None:
    store = FileStateSnapshotStore(base_dir=tmp_path)

    snapshot: Dict[str, Any] = {
        "symbol": "BTC/USDT",
        "ticker_id": 42,
        "market": {"last_price": 123.45, "ts": 111},
        "indicators": {"sma": 123.45},
        "indicators_history": [],
        "intents": [],
        "intents_history": [],
        "decision": {"action": "HOLD"},
        "decisions_history": [],
        "metrics": {"ticks": 42},
    }

    key = "local:BTC/USDT"
    store.save_snapshot(key, snapshot)

    loaded = store.load_snapshot(key)
    assert loaded is not None
    assert loaded["symbol"] == "BTC/USDT"
    assert loaded["ticker_id"] == 42
    assert loaded["market"]["last_price"] == 123.45


def test_make_and_apply_state_snapshot_roundtrip(tmp_path) -> None:
    symbol = "ETH/USDT"
    cfg = AppConfig(symbol=symbol)
    context = init_context(cfg)

    # Инициализируем часть state
    context["market"][symbol] = {"last_price": 10.0, "ts": 1}
    context["metrics"]["ticks"] = 5
    context["intents"][symbol] = [{"action": "BUY"}]

    snapshot = make_state_snapshot(context, symbol=symbol, ticker_id=5)

    # Применяем снапшот к новому контексту и убеждаемся, что данные восстановлены
    new_ctx = init_context(cfg)
    apply_state_snapshot(new_ctx, symbol=symbol, snapshot=snapshot)

    assert new_ctx["market"][symbol]["last_price"] == 10.0
    assert new_ctx["metrics"]["ticks"] == 5
    assert new_ctx["intents"][symbol][0]["action"] == "BUY"
