from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import pytest

from src.application.use_cases import run_realtime_trading


class _FakeConnector:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:  # pragma: no cover - простая заглушка
        self.closed = True


class _FakeTickSource:
    def __init__(self, ticks: list[dict[str, Any]]) -> None:
        self._ticks = ticks

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        for t in self._ticks:
            yield t


class _FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def process_tick(self, context: dict[str, Any], *, symbol: str, tick_id: int, price: float, ts: int) -> None:  # type: ignore[override]
        self.calls.append({
            "symbol": symbol,
            "tick_id": tick_id,
            "price": price,
            "ts": ts,
        })


class _FakeSnapshotService:
    def __init__(self) -> None:
        self.saved_ids: list[int] = []

    def load(self, context: dict[str, Any]) -> int:  # type: ignore[override]
        return 0

    def maybe_save(self, context: dict[str, Any], *, tick_id: int) -> None:  # type: ignore[override]
        self.saved_ids.append(tick_id)


async def _fake_worker(*_: Any, **__: Any) -> None:  # pragma: no cover - имитация бесконечного воркера
    try:
        while True:
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        # корректное завершение по отмене задачи
        raise


@pytest.mark.asyncio
async def test_run_realtime_from_exchange_pipeline_and_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет, что async-сценарий прогоняет все тики через pipeline и снапшоты.

    Тест не использует реальный ccxt/сеть: все внешние зависимости
    подменяются фейками через ``monkeypatch``.
    """

    # --- подготовка фейковых тиков ---
    ticks = [
        {
            "symbol": "BTC/USDT",
            "timestamp": 1,
            "datetime": "2020-01-01T00:00:00Z",
            "last": 100.0,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "bid": 99.5,
            "ask": 100.5,
            "baseVolume": 1.0,
            "quoteVolume": 100.0,
        },
        {
            "symbol": "BTC/USDT",
            "timestamp": 2,
            "datetime": "2020-01-01T00:00:01Z",
            "last": 101.0,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "bid": 100.5,
            "ask": 101.5,
            "baseVolume": 2.0,
            "quoteVolume": 200.0,
        },
    ]

    fake_pipeline = _FakePipeline()
    fake_snapshot = _FakeSnapshotService()

    # --- monkeypatch инфраструктурных компонентов внутри use-case ---

    monkeypatch.setattr(
        run_realtime_trading,
        "CcxtProExchangeConnector",
        lambda cfg: _FakeConnector(),
    )

    monkeypatch.setattr(
        run_realtime_trading,
        "TickSource",
        lambda connector, symbol: _FakeTickSource(ticks),
    )

    monkeypatch.setattr(
        run_realtime_trading,
        "TickPipelineService",
        lambda cfg: fake_pipeline,
    )

    monkeypatch.setattr(
        run_realtime_trading,
        "StateSnapshotService",
        lambda store, cfg: fake_snapshot,
    )

    monkeypatch.setattr(
        run_realtime_trading,
        "_run_order_book_refresh_worker",
        _fake_worker,
    )

    # Чтобы выйти из бесконечного цикла async-стрима, подменяем TickSource
    # фейком, который отдаёт конечный список тиков и завершается.

    await run_realtime_trading.run_realtime_from_exchange(symbol="BTC/USDT")

    # --- проверки ---
    assert [c["tick_id"] for c in fake_pipeline.calls] == [1, 2]
    assert fake_snapshot.saved_ids == [1, 2]
