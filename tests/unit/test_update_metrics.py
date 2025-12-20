from __future__ import annotations

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.services.context.state import init_context, update_metrics


def _build_context() -> Dict[str, Any]:
    cfg = AppConfig()  # symbol больше НЕ в AppConfig
    return init_context(cfg)


def test_update_metrics_sets_ticks_counter() -> None:
    ctx = _build_context()

    assert ctx["metrics"]["ticks"] == 0

    update_metrics(ctx, ticker_id=42)

    assert ctx["metrics"]["ticks"] == 42

