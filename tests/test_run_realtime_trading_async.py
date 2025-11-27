from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import pytest

from src.application.use_cases import run_realtime_trading


class _FakeTickSource:
    def __init__(self, ticks: list[dict[str, Any]]) -> None:
        self._ticks = ticks

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        for t in self._ticks:
            yield t


class _FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def process_tick(
        self,
        context: dict[str, Any],
        *,
        symbol: str,
        ticker_id: int,
        price: float,
        ts: int,
    ) -> None:  # type: ignore[override]
        self.calls.append(
            {
                "context": context,
                "symbol": symbol,
                "ticker_id": ticker_id,
                "price": price,
                "ts": ts,
            }
        )


class _FakeSnapshotService:
    def __init__(self) -> None:
        self.saved_ids: list[int] = []

    def maybe_save(self, context: dict[str, Any], *, ticker_id: int) -> None:  # type: ignore[override]
        self.saved_ids.append(ticker_id)


@pytest.mark.asyncio
async def test_run_realtime_core_processes_all_ticks_and_saves_snapshots() -> None:
    """Проверяет core-логику async-конвейера без реальной сети/CCXT.

    Тестирует функцию ``_run_realtime_core`` напрямую, используя
    фейковые ticker_source/pipeline/snapshot_svc.
    """

    # --- подготовка фейковых тиков ---
    ticks = [
        {
            "symbol": "BTC/USDT",
            "timestamp": 1,
            "datetime": "2020-01-01T00:00:00Z",
            "last": 100.0,
        },
        {
            "symbol": "BTC/USDT",
            "timestamp": 2,
            "datetime": "2020-01-01T00:00:01Z",
            "last": 101.0,
        },
    ]

    fake_source = _FakeTickSource(ticks)
    fake_pipeline = _FakePipeline()
    fake_snapshot = _FakeSnapshotService()

    context: dict[str, Any] = {}

    # Стартуем с ticker_id == 10, чтобы проверить корректный инкремент.
    start_ticker_id = 10

    await run_realtime_trading._run_realtime_core(  # type: ignore[attr-defined]
        ticker_source=fake_source,
        pipeline=fake_pipeline,
        snapshot_svc=fake_snapshot,
        context=context,
        cfg=run_realtime_trading.load_config(symbol="BTC/USDT"),
        symbol="BTC/USDT",
        start_ticker_id=start_ticker_id,
    )

    # --- проверки ---
    # Для двух тиков должны быть ticker_id == 11 и 12.
    assert [c["ticker_id"] for c in fake_pipeline.calls] == [11, 12]
    assert fake_snapshot.saved_ids == [11, 12]
