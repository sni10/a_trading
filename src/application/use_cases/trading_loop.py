"""Основной цикл realtime-торговли.

Содержит core-логику обработки потока тиков от биржи,
изолированную от деталей подключения и инфраструктуры.
"""

from __future__ import annotations

import asyncio

from src.application.services.state_snapshot_service import StateSnapshotService
from src.application.services.ticker_pipeline_service import TickPipelineService
from src.config.config import AppConfig
from src.domain.services.ticker.ticker_source import TickSource
from src.infrastructure.logging.logging_setup import log_info, log_separator

# Интервал логирования статистики (каждые N тиков)
TICKER_LOG_INTERVAL = 10

# Имя логгера для этого модуля
_LOG = __name__


async def run_realtime_core(
    *,
    ticker_source: TickSource,
    pipeline: TickPipelineService,
    snapshot_svc: StateSnapshotService,
    context: dict,
    cfg: AppConfig,
    symbol: str,
    start_ticker_id: int,
) -> None:
    """Core‑цикл async‑конвейера поверх абстрактного источника тиков.

    Вынесен в отдельную функцию, чтобы его можно было
    тестировать через фейковые ``ticker_source`` / ``snapshot_svc`` /
    ``pipeline`` **без** реальных сетевых подключений и CCXT.

    Логирование:
    - НЕ логируем каждый тик (это засоряет логи)
    - Логируем сводку каждые TICKER_LOG_INTERVAL тиков в формате bad_example:
      ``📊 Тик 100 | Цена: 0.45800000 | TPS: 0.9 | Среднее время: 0.0ms``

    Args:
        ticker_source: Асинхронный источник тиков от биржи.
        pipeline: Конвейер обработки одного тика.
        snapshot_svc: Сервис сохранения состояния.
        context: Глобальный контекст приложения.
        cfg: Конфигурация приложения.
        symbol: Торговая пара.
        start_ticker_id: Стартовый ID тика (из загруженного снапшота).
    """

    loop = asyncio.get_event_loop()
    start_ts = loop.time()
    ticker_id = start_ticker_id
    last_price = 0.0

    # Статистика для периодических сводок
    ticker_times: list[float] = []

    try:
        async for ticker in ticker_source.stream():
            ticker_start = loop.time()
            ticker_id += 1

            price = float(ticker["last"])
            last_price = price
            ts = ticker["timestamp"] or int(loop.time() * 1000)

            # Обработка тика через конвейер (без отдельного лога на каждый тик)
            pipeline.process_tick(
                context,
                symbol=symbol,
                ticker_id=ticker_id,
                price=price,
                ts=ts,
            )

            snapshot_svc.maybe_save(context, ticker_id=ticker_id)

            # Замер времени обработки
            ticker_elapsed = (loop.time() - ticker_start) * 1000  # ms
            ticker_times.append(ticker_elapsed)

            # Периодическая сводка каждые TICKER_LOG_INTERVAL тиков
            # Формат как в bad_example:
            # 📊 Тик 100 | Цена: 0.45800000 | TPS: 0.9 | Среднее время: 0.0ms | Мин/Макс: 0.0/1.6ms
            if ticker_id % TICKER_LOG_INTERVAL == 0:
                elapsed = loop.time() - start_ts
                tps = ticker_id / elapsed if elapsed > 0 else 0.0
                avg_time = sum(ticker_times) / len(ticker_times) if ticker_times else 0.0
                min_time = min(ticker_times) if ticker_times else 0.0
                max_time = max(ticker_times) if ticker_times else 0.0

                log_info(
                    f"📊 Тик {ticker_id} | Цена: {price:.8f} | "
                    f"TPS: {tps:.1f} | Среднее время: {avg_time:.1f}ms | "
                    f"Мин/Макс: {min_time:.1f}/{max_time:.1f}ms",
                    _LOG
                )

                # Сбрасываем статистику для следующего интервала
                ticker_times.clear()

    finally:
        # Финальная сводка при остановке
        elapsed = loop.time() - start_ts
        log_separator(_LOG)
        log_info(f"🛑 Остановка realtime-конвейера для {symbol}", _LOG)
        log_info(f"   - Всего тиков обработано: {ticker_id}", _LOG)
        log_info(f"   - Последняя цена: {last_price:.8f}", _LOG)
        log_info(f"   - Время работы: {elapsed:.1f} сек", _LOG)
        if elapsed > 0:
            log_info(f"   - Средний TPS: {ticker_id / elapsed:.2f}", _LOG)
        log_separator(_LOG)


__all__ = ["run_realtime_core"]
