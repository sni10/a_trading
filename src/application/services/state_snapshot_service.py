from __future__ import annotations

"""Сервис работы со снапшотами состояния.

Выносит логику загрузки/сохранения state из основного сценария
реального времени, чтобы ``run()`` оперировал только in‑memory
контекстом и высокоуровневым сервисом.
"""

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.services.context.state import apply_state_snapshot, make_state_snapshot
from src.domain.interfaces.state_snapshot_store import IStateSnapshotStore
from src.infrastructure.logging import log_stage


class StateSnapshotService:
    """Сервис для загрузки и периодического сохранения снапшотов state.

    Работает поверх :class:`FileStateSnapshotStore` и типизированного
    ``AppConfig``. На этом уровне не знает деталей тик‑конвейера,
    оперирует только ``dict``‑контекстом.
    """

    def __init__(self, store: IStateSnapshotStore, cfg: AppConfig, *, symbol: str) -> None:
        self._store = store
        self._cfg = cfg
        self._symbol = symbol
        self._key = f"{cfg.environment}:{symbol}"

    def load(self, context: Dict[str, Any]) -> int:
        """Загрузить снапшот и применить его к ``context``.

        Возвращает стартовый ``ticker_id`` из снапшота или ``0``, если
        снапшота нет или он пустой.
        """

        snapshot = self._store.load_snapshot(self._key)
        if not snapshot:
            # Нет снапшота – стартуем с пустого in‑memory state
            log_stage(
                "LOAD",
                "📦 Снапшот state не найден, стартуем с пустого in-memory state",
                symbol=self._symbol,
            )
            return 0

        apply_state_snapshot(context, symbol=self._symbol, snapshot=snapshot)

        loaded_ticker_id = int(snapshot.get("ticker_id") or 0)
        log_stage(
            "LOAD",
            "📦 Снапшот state найден и загружен",
            symbol=self._symbol,
            ticker_id=loaded_ticker_id,
        )
        return loaded_ticker_id

    def maybe_save(self, context: Dict[str, Any], *, ticker_id: int) -> None:
        """По интервалу сохранить снапшот state во внешнее хранилище.

        Интервал берётся из ``cfg.state_snapshot_interval_ticks``. Если
        интервал не задан (<= 0) или ``ticker_id`` не кратен интервалу –
        ничего не делает.
        """

        interval = getattr(self._cfg, "state_snapshot_interval_ticks", 0)
        if interval <= 0:
            return

        if ticker_id % interval != 0:
            return

        snapshot = make_state_snapshot(
            context,
            symbol=self._symbol,
            ticker_id=ticker_id,
        )
        self._store.save_snapshot(self._key, snapshot)


__all__ = ["StateSnapshotService"]
