from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from src.application.services.state_snapshot_service import StateSnapshotService
from src.config.config import AppConfig


class DummySnapshotStore:
    """Простая in-memory заглушка для IStateSnapshotStore.

    Используется в юнит‑тестах, чтобы не трогать файловую систему.
    """

    def __init__(self) -> None:
        self.saved: List[Tuple[str, Dict[str, Any]]] = []
        self.loaded_snapshot: Dict[str, Any] | None = None
        self.loaded_keys: List[str] = []

    def save_snapshot(self, key: str, snapshot: Dict[str, Any]) -> None:  # type: ignore[override]
        self.saved.append((key, snapshot))

    def load_snapshot(self, key: str) -> Dict[str, Any] | None:  # type: ignore[override]
        self.loaded_keys.append(key)
        return self.loaded_snapshot


def _make_cfg(**overrides: Any) -> AppConfig:
    cfg = AppConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def test_load_returns_zero_and_keeps_context_when_snapshot_missing() -> None:
    cfg = _make_cfg(environment="local", symbol="BTC/USDT")
    store = DummySnapshotStore()
    store.loaded_snapshot = None
    context: Dict[str, Any] = {"foo": "bar"}

    svc = StateSnapshotService(store, cfg)

    start_tick_id = svc.load(context)

    assert start_tick_id == 0
    # Контекст не должен меняться, если снапшота нет
    assert context == {"foo": "bar"}


def test_load_returns_zero_and_keeps_context_when_snapshot_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _make_cfg(environment="local", symbol="BTC/USDT")
    store = DummySnapshotStore()
    store.loaded_snapshot = {}
    context: Dict[str, Any] = {"foo": "bar"}

    called: Dict[str, Any] = {}

    def fake_apply(context_arg: Dict[str, Any], *, symbol: str, snapshot: Dict[str, Any]) -> None:  # pragma: no cover - защитный путь
        called["called"] = True

    monkeypatch.setattr(
        "src.application.services.state_snapshot_service.apply_state_snapshot",
        fake_apply,
    )

    svc = StateSnapshotService(store, cfg)
    start_tick_id = svc.load(context)

    assert start_tick_id == 0
    # apply_state_snapshot не должен вызываться для пустого снапшота
    assert called == {}
    assert context == {"foo": "bar"}


def test_load_applies_snapshot_and_returns_tick_id(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _make_cfg(environment="local", symbol="BTC/USDT")
    store = DummySnapshotStore()
    snapshot = {"tick_id": 42, "metrics": {"trades": 10}}
    store.loaded_snapshot = snapshot
    context: Dict[str, Any] = {}

    applied: Dict[str, Any] = {}

    def fake_apply(context_arg: Dict[str, Any], *, symbol: str, snapshot: Dict[str, Any]) -> None:
        applied["context"] = context_arg
        applied["symbol"] = symbol
        applied["snapshot"] = snapshot
        context_arg["applied"] = True

    monkeypatch.setattr(
        "src.application.services.state_snapshot_service.apply_state_snapshot",
        fake_apply,
    )

    svc = StateSnapshotService(store, cfg)
    start_tick_id = svc.load(context)

    assert start_tick_id == 42
    assert context.get("applied") is True
    assert applied["symbol"] == cfg.symbol
    assert applied["snapshot"] is snapshot


def test_maybe_save_does_nothing_when_interval_non_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    # interval == 0
    cfg = _make_cfg(state_snapshot_interval_ticks=0)
    store = DummySnapshotStore()
    context: Dict[str, Any] = {"foo": "bar"}

    def fake_make(*args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - защитный путь
        raise AssertionError("make_state_snapshot must not be called when interval <= 0")

    monkeypatch.setattr(
        "src.application.services.state_snapshot_service.make_state_snapshot",
        fake_make,
    )

    svc = StateSnapshotService(store, cfg)
    svc.maybe_save(context, tick_id=10)

    assert store.saved == []


def test_maybe_save_calls_save_when_tick_matches_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _make_cfg(environment="prod", symbol="ETH/USDT", state_snapshot_interval_ticks=5)
    store = DummySnapshotStore()
    context: Dict[str, Any] = {"some": "state"}

    produced_snapshot = {"tick_id": 10, "foo": "bar"}

    def fake_make(context_arg: Dict[str, Any], *, symbol: str, tick_id: int) -> Dict[str, Any]:
        assert context_arg is context
        assert symbol == cfg.symbol
        assert tick_id == 10
        return produced_snapshot

    monkeypatch.setattr(
        "src.application.services.state_snapshot_service.make_state_snapshot",
        fake_make,
    )

    svc = StateSnapshotService(store, cfg)

    # tick_id кратен интервалу – должен сохраниться снапшот
    svc.maybe_save(context, tick_id=10)

    assert len(store.saved) == 1
    key, snapshot = store.saved[0]
    assert key == f"{cfg.environment}:{cfg.symbol}"
    assert snapshot is produced_snapshot

    # tick_id не кратен интервалу – не должно быть дополнительных сохранений
    svc.maybe_save(context, tick_id=11)
    assert len(store.saved) == 1

