from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pytest

from src.application.use_cases import run_realtime_trading


class _FakeTick:
    def __init__(self, symbol: str, price: float, ts: int) -> None:
        self.data = {"symbol": symbol, "price": price, "ts": ts}


def _make_ticks(symbol: str, prices: Iterable[float]) -> List[Dict[str, Any]]:
    return [
        {"symbol": symbol, "price": float(price), "ts": 1_700_000_000_000 + i}
        for i, price in enumerate(prices, start=1)
    ]


class _FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def process_tick(
        self,
        context: dict[str, Any],
        *,
        symbol: str,
        tick_id: int,
        price: float,
        ts: int,
    ) -> None:  # type: ignore[override]
        self.calls.append(
            {
                "context": context,
                "symbol": symbol,
                "tick_id": tick_id,
                "price": price,
                "ts": ts,
            }
        )


class _DummySnapshotService:
    """Заглушка StateSnapshotService без файловой системы.

    Используется только для run_demo_offline: load() всегда возвращает 0,
    maybe_save() записывает только tick_id в список, не трогая диски.
    """

    def __init__(self) -> None:
        self.loaded: list[dict[str, Any]] = []
        self.saved_ids: list[int] = []

    def load(self, context: dict[str, Any]) -> int:  # type: ignore[override]
        self.loaded.append({"context": context})
        return 0

    def maybe_save(self, context: dict[str, Any], *, tick_id: int) -> None:  # type: ignore[override]
        self.saved_ids.append(tick_id)


def _fake_generate_ticks(symbol: str, max_ticks: int, sleep_sec: float):  # type: ignore[override]
    # sleep_sec игнорируется – в тестах не должно быть задержек
    del sleep_sec

    prices = [100.0 + i for i in range(max_ticks)]
    for i, price in enumerate(prices, start=1):
        yield {"symbol": symbol, "price": price, "ts": 1_700_000_000_000 + i}


@pytest.mark.parametrize("max_ticks", [1, 3, 5])
def test_run_demo_offline_uses_pipeline_for_each_generated_tick(
    monkeypatch: pytest.MonkeyPatch,
    max_ticks: int,
) -> None:
    """run_demo_offline прогоняет все фейковые тики через TickPipelineService.

    В тесте подменяются:

    * generate_ticks – на детерминированный генератор без time.sleep;
    * TickPipelineService – на фейк, который пишет параметры вызова;
    * StateSnapshotService – на in-memory заглушку без файловой системы.
    """

    symbol = "BTC/USDT"

    # --- monkeypatch генератора тиков и сервисов ---
    monkeypatch.setattr(
        run_realtime_trading,
        "generate_ticks",
        lambda symbol_arg, max_ticks=max_ticks, sleep_sec=0.0: _fake_generate_ticks(
            symbol_arg,
            max_ticks=max_ticks,
            sleep_sec=sleep_sec,
        ),
    )

    fake_pipeline = _FakePipeline()
    monkeypatch.setattr(
        run_realtime_trading,
        "TickPipelineService",
        lambda cfg: fake_pipeline,
    )

    dummy_snapshot = _DummySnapshotService()
    monkeypatch.setattr(
        run_realtime_trading,
        "StateSnapshotService",
        lambda store, cfg: dummy_snapshot,
    )

    # --- запуск сценария ---
    # max_ticks контролируется через AppConfig, поэтому подменим load_config,
    # чтобы вернуть конфиг с нужным параметром.
    from src.config.config import AppConfig

    def fake_load_config(symbol: str | None = None) -> AppConfig:  # type: ignore[override]
        cfg = AppConfig()
        if symbol is not None:
            cfg.symbol = symbol
        cfg.max_ticks = max_ticks
        cfg.tick_sleep_sec = 0.0
        return cfg

    monkeypatch.setattr(run_realtime_trading, "load_config", fake_load_config)

    run_realtime_trading.run_demo_offline(symbol=symbol)

    # --- проверки ---
    # Должно быть ровно max_ticks вызовов pipeline.process_tick
    assert [call["tick_id"] for call in fake_pipeline.calls] == list(
        range(1, max_ticks + 1)
    )

    # Все вызовы делаются по одному и тому же символу
    assert {call["symbol"] for call in fake_pipeline.calls} == {symbol}

    # maybe_save должен вызываться хотя бы для каждого тика – детали
    # интервала тестируются отдельно в unit-тестах StateSnapshotService.
    assert dummy_snapshot.saved_ids == list(range(1, max_ticks + 1))
