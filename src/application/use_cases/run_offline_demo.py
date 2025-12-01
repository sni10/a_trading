"""
!!! DEPRECATED !!! DEPRECATED !!! DEPRECATED !!!

Синхронный демо‑режим без сети поверх ``generate_ticks``.

Этот сценарий **не обращается к реальной бирже** и полностью
изолирует симуляцию рынка внутри процесса.
"""

from __future__ import annotations

import time

from src.application.context import build_context
from src.application.services.state_snapshot_service import StateSnapshotService
from src.application.services.ticker_pipeline_service import TickPipelineService
from src.config.config import AppConfig, load_config
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.services.context.state import init_context
from src.domain.services.market_data.ticker_source import generate_ticks
from src.infrastructure.logging.logging_setup import (
    log_info,
    log_separator,
    log_warning,
    setup_logging,
)
from src.infrastructure.repositories import InMemoryCurrencyPairRepository
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore

# Версия прототипа
__version__ = "0.1.0"

# Интервал логирования статистики (каждые N тиков)
TICKER_LOG_INTERVAL = 10

# Имя логгера для этого модуля
_LOG = __name__


def run_demo_offline(
    pair_repository: ICurrencyPairRepository | None = None,
    *,
    symbol: str | None = None,
) -> None:
    """
    !!! DEPRECATED !!! DEPRECATED !!! DEPRECATED !!!

    Синхронный демо‑режим без сети поверх ``generate_ticks``.

    Этот сценарий **не обращается к реальной бирже** и полностью
    изолирует симуляцию рынка внутри процесса.

    Используются:

    * ``generate_ticks`` – фейковый генератор тиков;
    * ``update_orderflow_from_tick`` – симуляция стакана/ордерфлоу;
    * ``TickPipelineService`` – чистый конвейер обработки тика;
    * ``StateSnapshotService`` – загрузка/сохранение состояния.

    На уровне приложения прототип обслуживает **ровно одну** валютную
    пару, которая передаётся через параметр ``symbol="BTC/USDT"``.
    """

    setup_logging()

    # Инициализируем AppConfig из env + параметров run()
    cfg = load_config(symbol=symbol)

    # Один процесс прототипа обслуживает ровно одну валютную пару.
    active_symbol = cfg.symbol

    # === СТАРТОВЫЙ БЛОК ===
    log_info(f"🚀 ЗАПУСК AlgoTrade Prototype v{__version__} (OFFLINE DEMO) для {active_symbol}", _LOG)

    # Репозиторий пар: либо передан снаружи (в будущем — обёртка над БД),
    # либо создаём in-memory репозиторий из одного символа конфига.
    if pair_repository is None:
        pair_repository = InMemoryCurrencyPairRepository.from_symbols([cfg.symbol])
    log_info(f"✅ InMemoryCurrencyPairRepository создан для {cfg.symbol}", _LOG)

    pair = pair_repository.get_by_symbol(active_symbol)
    if pair is None:
        raise RuntimeError(f"Currency pair {active_symbol!r} is not configured")
    if not pair.enabled:
        raise RuntimeError(f"Currency pair {active_symbol!r} is disabled for trading")

    log_info(f"✅ Валютная пара {active_symbol} загружена и активна", _LOG)

    # Базовый dict‑контекст на основе типизированного AppConfig
    context = init_context(cfg)
    log_info("✅ Базовый контекст инициализирован (init_context)", _LOG)

    # Обогащаем контекст CurrencyPair и in-memory кэшами, используя
    # репозиторий пар как единственный источник правды.
    context = build_context(cfg, context, pair_repository=pair_repository)
    log_info("✅ Контекст обогащён кэшами и CurrencyPair (build_context)", _LOG)

    # --- Загрузка state из снапшота (если есть) ---
    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(snapshot_store, cfg)
    loaded_ticker_id = snapshot_svc.load(context)

    if loaded_ticker_id > 0:
        log_info(f"📦 Загружен снапшот состояния, ticker_id={loaded_ticker_id}", _LOG)
    else:
        log_info("📦 Снапшот не найден, старт с нуля", _LOG)

    # Прогрев
    log_info("🔥 Прогрев индикаторов и стаканов (исторические данные, OHLCV)", _LOG)
    log_info(f"   - fast_interval: {cfg.indicator_fast_interval}", _LOG)
    log_info(f"   - medium_interval: {cfg.indicator_medium_interval}", _LOG)
    log_info(f"   - heavy_interval: {cfg.indicator_heavy_interval}", _LOG)

    # Единый конвейер обработки одного тика без I/O.
    pipeline = TickPipelineService(cfg)
    log_info("✅ Конвейер обработки тиков создан (TickPipelineService)", _LOG)

    # === СВОДКА ГОТОВНОСТИ СИСТЕМЫ ===
    log_separator(_LOG)
    log_info("🚀 СИСТЕМА ГОТОВА К ЗАПУСКУ (OFFLINE DEMO)", _LOG)
    log_info(f"   - Валютная пара: {active_symbol}", _LOG)
    log_info(f"   - Окружение: {cfg.environment}", _LOG)
    log_info(f"   - Максимум тиков: {cfg.max_ticks}", _LOG)
    log_info(f"   - Задержка между тиками: {cfg.ticker_sleep_sec} сек", _LOG)
    log_info(f"   - Стартовый ticker_id: {loaded_ticker_id}", _LOG)
    log_separator(_LOG)

    # === ЗАПУСК ТОРГОВОГО ЦИКЛА ===
    log_info("🔄 Начинаем основной торговый цикл (offline demo)...", _LOG)

    start_ts = time.time()
    ticker_id = loaded_ticker_id
    last_price = 0.0

    # Статистика для периодических сводок
    ticker_times: list[float] = []

    # Локальный импорт симулятора стакана, чтобы он не «подтягивался»
    # в модульный scope и не был доступен боевому сценарию
    # run_realtime_from_exchange.
    from src.domain.services.market_data.orderflow_simulator import (
        update_orderflow_from_tick,
    )

    try:
        for ticker in generate_ticks(
            cfg.symbol, max_ticks=cfg.max_ticks, sleep_sec=cfg.ticker_sleep_sec
        ):
            ticker_start = time.time()
            ticker_id += 1
            symbol = ticker["symbol"]
            price = ticker["price"]
            last_price = price
            ts = ticker["ts"]

            # Симуляция стакана/ордерфлоу (только для демо)
            update_orderflow_from_tick(
                context,
                symbol=symbol,
                price=price,
                ts=ts,
            )

            # Весь остальной конвейер по тику выполняет TickPipelineService.
            pipeline.process_tick(
                context,
                symbol=symbol,
                ticker_id=ticker_id,
                price=price,
                ts=ts,
            )

            # Периодическое сохранение снапшота во внешнее хранилище
            snapshot_svc.maybe_save(context, ticker_id=ticker_id)

            # Замер времени обработки
            ticker_elapsed = (time.time() - ticker_start) * 1000  # ms
            ticker_times.append(ticker_elapsed)

            # Периодическая сводка каждые TICKER_LOG_INTERVAL тиков
            if ticker_id % TICKER_LOG_INTERVAL == 0:
                elapsed = time.time() - start_ts
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

    except KeyboardInterrupt:
        log_warning(f"⚠️ Прерывание по Ctrl+C на тике {ticker_id}", _LOG)
    except Exception as exc:
        log_warning(f"❌ Критическая ошибка в торговом цикле: {type(exc).__name__}: {exc}", _LOG)
        raise
    finally:
        # Финальная сводка при остановке
        elapsed = time.time() - start_ts
        log_separator(_LOG)
        log_info(f"🛑 Остановка offline-конвейера для {active_symbol}", _LOG)
        log_info(f"   - Всего тиков обработано: {ticker_id}", _LOG)
        log_info(f"   - Последняя цена: {last_price:.8f}", _LOG)
        log_info(f"   - Время работы: {elapsed:.1f} сек", _LOG)
        if elapsed > 0:
            log_info(f"   - Средний TPS: {ticker_id / elapsed:.2f}", _LOG)
        log_separator(_LOG)


__all__ = ["run_demo_offline"]
