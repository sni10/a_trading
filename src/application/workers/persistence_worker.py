"""Worker для периодического сохранения состояния в БД."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from src.application.services.state_snapshot_service import StateSnapshotService
from src.infrastructure.logging import log_stage


class PersistenceWorker:
    """Фоновый worker для периодического сброса состояния в БД.

    Каждые {interval} секунд сохраняет:
    - Активные сделки (deals)
    - Открытые ордера (orders)
    - Трейды

    Это защищает от потери данных при аварийном прерывании процесса.
    Максимальная рассинхронизация БД с контекстом = {interval} секунд.
    """

    def __init__(
        self,
        snapshot_service: StateSnapshotService,
        context: Dict[str, Any],
        *,
        symbol: str,
        interval_seconds: int = 180,
    ) -> None:
        """Инициализация worker.

        Args:
            snapshot_service: Сервис снапшотов с репозиториями
            context: ApplicationContext (dict)
            symbol: Символ валютной пары
            interval_seconds: Интервал сброса в БД (по умолчанию 180 сек)
        """
        self._snapshot_service = snapshot_service
        self._context = context
        self._symbol = symbol
        self._interval = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Запустить периодический сброс в БД."""
        if self._running:
            log_stage(
                "PERSISTENCE_WORKER",
                "⚠️  Worker уже запущен",
                symbol=self._symbol,
            )
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log_stage(
            "PERSISTENCE_WORKER",
            f"▶️  Запущен периодический сброс в БД (интервал: {self._interval} сек)",
            symbol=self._symbol,
        )

    async def stop(self) -> None:
        """Остановить периодический сброс."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Финальный сброс перед остановкой
        self._snapshot_service._save_entities_to_db(self._context)
        log_stage(
            "PERSISTENCE_WORKER",
            "⏹️  Остановлен, выполнен финальный сброс в БД",
            symbol=self._symbol,
        )

    async def _run_loop(self) -> None:
        """Основной цикл периодического сброса."""
        try:
            while self._running:
                await asyncio.sleep(self._interval)

                if not self._running:
                    break

                # Сохранить БД-сущности в БД
                try:
                    self._snapshot_service._save_entities_to_db(self._context)
                    log_stage(
                        "PERSISTENCE_WORKER",
                        f"✅ Периодический сброс в БД выполнен",
                        symbol=self._symbol,
                    )
                except Exception as e:
                    log_stage(
                        "PERSISTENCE_WORKER",
                        f"❌ Ошибка при сбросе в БД: {e}",
                        symbol=self._symbol,
                    )
        except asyncio.CancelledError:
            log_stage(
                "PERSISTENCE_WORKER",
                "Цикл сброса отменён",
                symbol=self._symbol,
            )
            raise


__all__ = ["PersistenceWorker"]
