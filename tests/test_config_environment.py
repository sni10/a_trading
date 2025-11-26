from __future__ import annotations

import os

from src.config.environment import Config, load_config


def _clear_env(keys: list[str]) -> None:
    for k in keys:
        os.environ.pop(k, None)


def test_load_config_defaults(monkeypatch) -> None:
    """При отсутствии env используются значения по умолчанию."""

    _clear_env([
        "APP_ENV",
        "SYMBOLS",
        "MAX_TICKS",
        "TICK_SLEEP_SEC",
        "INDICATOR_FAST_INTERVAL",
        "INDICATOR_MEDIUM_INTERVAL",
        "INDICATOR_HEAVY_INTERVAL",
    ])

    cfg = load_config()

    assert cfg.environment == "local"
    assert cfg.symbols == ["BTC/USDT", "ETH/USDT"]
    assert cfg.max_ticks == 10
    assert cfg.tick_sleep_sec == 0.2
    assert cfg.indicator_fast_interval == 1
    assert cfg.indicator_medium_interval == 3
    assert cfg.indicator_heavy_interval == 5


def test_load_config_from_env(monkeypatch) -> None:
    """Env‑переменные переопределяют дефолты."""

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("SYMBOLS", "ETH/USDT,BTC/USDT")
    monkeypatch.setenv("MAX_TICKS", "5")
    monkeypatch.setenv("TICK_SLEEP_SEC", "0.1")
    monkeypatch.setenv("INDICATOR_FAST_INTERVAL", "2")
    monkeypatch.setenv("INDICATOR_MEDIUM_INTERVAL", "4")
    monkeypatch.setenv("INDICATOR_HEAVY_INTERVAL", "8")

    cfg = load_config()

    assert cfg.environment == "dev"
    assert cfg.symbols == ["ETH/USDT", "BTC/USDT"]
    assert cfg.max_ticks == 5
    assert cfg.tick_sleep_sec == 0.1
    assert cfg.indicator_fast_interval == 2
    assert cfg.indicator_medium_interval == 4
    assert cfg.indicator_heavy_interval == 8


def test_invalid_indicator_intervals_raise(monkeypatch) -> None:
    """Нарушение порядка fast <= medium <= heavy приводит к ошибке."""

    monkeypatch.setenv("INDICATOR_FAST_INTERVAL", "5")
    monkeypatch.setenv("INDICATOR_MEDIUM_INTERVAL", "3")
    monkeypatch.setenv("INDICATOR_HEAVY_INTERVAL", "1")

    try:
        load_config()
    except ValueError as exc:  # noqa: BLE001
        msg = str(exc)
        assert "indicator_medium_interval" in msg or "indicator_heavy_interval" in msg
    else:  # pragma: no cover - защитный блок
        raise AssertionError("load_config() must fail on invalid intervals")


def test_explicit_arguments_override_env(monkeypatch) -> None:
    """Явные аргументы load_config() важнее env."""

    monkeypatch.setenv("MAX_TICKS", "100")

    cfg = load_config(max_ticks=3)
    assert cfg.max_ticks == 3
