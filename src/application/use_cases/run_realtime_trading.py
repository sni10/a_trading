import asyncio
import time
from typing import List

from src.infrastructure.logging.logging_setup import (
    setup_logging,
    log_stage,
    log_info,
    log_warning,
    log_separator,
    log_stat_block,
)

# Имя логгера для этого модуля (используется во всех вызовах log_*)
_LOG = __name__
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.context.state import init_context
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.infrastructure.repositories import InMemoryCurrencyPairRepository
from src.config.config import load_config, AppConfig
from src.application.context import build_context
from src.application.services.tick_pipeline_service import TickPipelineService
from src.application.services.state_snapshot_service import StateSnapshotService
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore
from src.domain.services.tick.tick_source import TickSource
from src.infrastructure.connectors.ccxt_pro_exchange_connector import (
    CcxtProExchangeConnector,
)
from src.application.workers.order_book_refresh_worker import (
    order_book_refresh_worker,
)

# Версия прототипа
__version__ = "0.1.0"

# Интервал логирования статистики (каждые N тиков)
TICK_LOG_INTERVAL = 10


def run_demo_offline(
    pair_repository: ICurrencyPairRepository | None = None,
    *,
    symbol: str | None = None,
) -> None:
    """Синхронный демо‑режим без сети поверх ``generate_ticks``.

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
    loaded_tick_id = snapshot_svc.load(context)

    if loaded_tick_id > 0:
        log_info(f"📦 Загружен снапшот состояния, tick_id={loaded_tick_id}", _LOG)
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
    log_info(f"   - Задержка между тиками: {cfg.tick_sleep_sec} сек", _LOG)
    log_info(f"   - Стартовый tick_id: {loaded_tick_id}", _LOG)
    log_separator(_LOG)

    # === ЗАПУСК ТОРГОВОГО ЦИКЛА ===
    log_info("🔄 Начинаем основной торговый цикл (offline demo)...", _LOG)

    start_ts = time.time()
    tick_id = loaded_tick_id
    last_price = 0.0

    # Статистика для периодических сводок
    tick_times: list[float] = []

    # Локальный импорт симулятора стакана, чтобы он не «подтягивался»
    # в модульный scope и не был доступен боевому сценарию
    # run_realtime_from_exchange.
    from src.domain.services.market_data.orderflow_simulator import (
        update_orderflow_from_tick,
    )

    try:
        for tick in generate_ticks(
            cfg.symbol, max_ticks=cfg.max_ticks, sleep_sec=cfg.tick_sleep_sec
        ):
            tick_start = time.time()
            tick_id += 1
            symbol = tick["symbol"]
            price = tick["price"]
            last_price = price
            ts = tick["ts"]

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
                tick_id=tick_id,
                price=price,
                ts=ts,
            )

            # Периодическое сохранение снапшота во внешнее хранилище
            snapshot_svc.maybe_save(context, tick_id=tick_id)

            # Замер времени обработки
            tick_elapsed = (time.time() - tick_start) * 1000  # ms
            tick_times.append(tick_elapsed)

            # Периодическая сводка каждые TICK_LOG_INTERVAL тиков
            if tick_id % TICK_LOG_INTERVAL == 0:
                elapsed = time.time() - start_ts
                tps = tick_id / elapsed if elapsed > 0 else 0.0
                avg_time = sum(tick_times) / len(tick_times) if tick_times else 0.0
                min_time = min(tick_times) if tick_times else 0.0
                max_time = max(tick_times) if tick_times else 0.0

                log_info(
                    f"📊 Тик {tick_id} | Цена: {price:.8f} | "
                    f"TPS: {tps:.1f} | Среднее время: {avg_time:.1f}ms | "
                    f"Мин/Макс: {min_time:.1f}/{max_time:.1f}ms",
                    _LOG
                )

                # Сбрасываем статистику для следующего интервала
                tick_times.clear()

    except KeyboardInterrupt:
        log_warning(f"⚠️ Прерывание по Ctrl+C на тике {tick_id}", _LOG)
    except Exception as exc:
        log_warning(f"❌ Критическая ошибка в торговом цикле: {type(exc).__name__}: {exc}", _LOG)
        raise
    finally:
        # Финальная сводка при остановке
        elapsed = time.time() - start_ts
        log_separator(_LOG)
        log_info(f"🛑 Остановка offline-конвейера для {active_symbol}", _LOG)
        log_info(f"   - Всего тиков обработано: {tick_id}", _LOG)
        log_info(f"   - Последняя цена: {last_price:.8f}", _LOG)
        log_info(f"   - Время работы: {elapsed:.1f} сек", _LOG)
        if elapsed > 0:
            log_info(f"   - Средний TPS: {tick_id / elapsed:.2f}", _LOG)
        log_separator(_LOG)


async def _run_order_book_refresh_worker(
    connector: CcxtProExchangeConnector,
    context: dict,
    cfg: AppConfig,
    *,
    symbol: str,
) -> None:
    """Вспомогательная обёртка для запуска воркера стакана.

    Выделена в отдельную функцию, чтобы её было проще подменять в
    юнит‑тестах через monkeypatch.
    """

    market_caches = context.get("market_caches") or {}
    market_cache = market_caches.get(symbol)
    if market_cache is None:
        raise RuntimeError(f"Market cache for symbol {symbol!r} not found in context")

    await order_book_refresh_worker(
        connector,
        market_cache,
        symbol,
        cfg,
    )


async def _run_realtime_core(
    *,
    tick_source: TickSource,
    pipeline: TickPipelineService,
    snapshot_svc: StateSnapshotService,
    context: dict,
    cfg: AppConfig,
    symbol: str,
    start_tick_id: int,
) -> None:
    """Core‑цикл async‑конвейера поверх абстрактного источника тиков.

    Вынесен в отдельную функцию, чтобы его можно было
    тестировать через фейковые ``tick_source`` / ``snapshot_svc`` /
    ``pipeline`` **без** реальных сетевых подключений и CCXT.

    Логирование:
    - НЕ логируем каждый тик (это засоряет логи)
    - Логируем сводку каждые TICK_LOG_INTERVAL тиков в формате bad_example:
      ``📊 Тик 100 | Цена: 0.45800000 | TPS: 0.9 | Среднее время: 0.0ms``
    """

    loop = asyncio.get_event_loop()
    start_ts = loop.time()
    tick_id = start_tick_id
    last_price = 0.0

    # Статистика для периодических сводок
    tick_times: list[float] = []

    try:
        async for ticker in tick_source.stream():
            tick_start = loop.time()
            tick_id += 1

            price = float(ticker["last"])
            last_price = price
            ts = ticker["timestamp"] or int(loop.time() * 1000)

            # Обработка тика через конвейер (без отдельного лога на каждый тик)
            pipeline.process_tick(
                context,
                symbol=symbol,
                tick_id=tick_id,
                price=price,
                ts=ts,
            )

            snapshot_svc.maybe_save(context, tick_id=tick_id)

            # Замер времени обработки
            tick_elapsed = (loop.time() - tick_start) * 1000  # ms
            tick_times.append(tick_elapsed)

            # Периодическая сводка каждые TICK_LOG_INTERVAL тиков
            # Формат как в bad_example:
            # 📊 Тик 100 | Цена: 0.45800000 | TPS: 0.9 | Среднее время: 0.0ms | Мин/Макс: 0.0/1.6ms
            if tick_id % TICK_LOG_INTERVAL == 0:
                elapsed = loop.time() - start_ts
                tps = tick_id / elapsed if elapsed > 0 else 0.0
                avg_time = sum(tick_times) / len(tick_times) if tick_times else 0.0
                min_time = min(tick_times) if tick_times else 0.0
                max_time = max(tick_times) if tick_times else 0.0

                log_info(
                    f"📊 Тик {tick_id} | Цена: {price:.8f} | "
                    f"TPS: {tps:.1f} | Среднее время: {avg_time:.1f}ms | "
                    f"Мин/Макс: {min_time:.1f}/{max_time:.1f}ms",
                    _LOG
                )

                # Сбрасываем статистику для следующего интервала
                tick_times.clear()

    finally:
        # Финальная сводка при остановке
        elapsed = loop.time() - start_ts
        log_separator(_LOG)
        log_info(f"🛑 Остановка realtime-конвейера для {symbol}", _LOG)
        log_info(f"   - Всего тиков обработано: {tick_id}", _LOG)
        log_info(f"   - Последняя цена: {last_price:.8f}", _LOG)
        log_info(f"   - Время работы: {elapsed:.1f} сек", _LOG)
        if elapsed > 0:
            log_info(f"   - Средний TPS: {tick_id / elapsed:.2f}", _LOG)
        log_separator(_LOG)


async def run_realtime_from_exchange(symbol: str | None = None) -> None:
    """Боевой async‑сценарий real‑time торговли от реальной биржи.

    Использует ``CcxtProExchangeConnector`` + ``TickSource`` и
    асинхронный воркер стакана. Внутри **нет** ``generate_ticks`` и
    симулятора стакана; все данные приходят с биржи.
    """

    setup_logging()

    cfg = load_config(symbol=symbol)
    active_symbol = cfg.symbol

    # === СТАРТОВЫЙ БЛОК (как в bad_example) ===
    log_info(f"🚀 ЗАПУСК AlgoTrade Prototype v{__version__} для {active_symbol}", _LOG)

    # Репозиторий пар и валидация активной пары
    pair_repo = InMemoryCurrencyPairRepository.from_symbols([active_symbol])
    log_info(f"✅ InMemoryCurrencyPairRepository создан для {active_symbol}", _LOG)
    
    pair = pair_repo.get_by_symbol(active_symbol)
    if pair is None:
        raise RuntimeError(f"Currency pair {active_symbol!r} is not configured")
    if not pair.enabled:
        raise RuntimeError(f"Currency pair {active_symbol!r} is disabled for trading")

    log_info(f"✅ Валютная пара {active_symbol} загружена и активна", _LOG)

    # Контекст и снапшоты
    context = init_context(cfg)
    log_info("✅ Базовый контекст инициализирован (init_context)", _LOG)
    
    context = build_context(cfg, context, pair_repository=pair_repo)
    log_info("✅ Контекст обогащён кэшами и CurrencyPair (build_context)", _LOG)

    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(snapshot_store, cfg)
    tick_id = snapshot_svc.load(context)

    if tick_id > 0:
        log_info(f"📦 Загружен снапшот состояния, tick_id={tick_id}", _LOG)
    else:
        log_info("📦 Снапшот не найден, старт с нуля", _LOG)

    # Сетевой коннектор и источник тиков
    connector = CcxtProExchangeConnector(cfg)
    tick_source = TickSource(connector, symbol=active_symbol)

    mode_str = "Sandbox" if cfg.sandbox_mode else "Production"
    log_info(f"✅ Коннектор инициализирован ({cfg.exchange_id}, {mode_str})", _LOG)

    # Воркер стакана
    orderbook_task = asyncio.create_task(
        _run_order_book_refresh_worker(connector, context, cfg, symbol=active_symbol)
    )
    log_info("✅ Воркер стакана запущен", _LOG)

    pipeline = TickPipelineService(cfg)
    log_info("✅ Конвейер обработки тиков создан (TickPipelineService)", _LOG)

    # === СВОДКА ГОТОВНОСТИ СИСТЕМЫ ===
    log_separator(_LOG)
    log_info("🚀 СИСТЕМА ГОТОВА К ЗАПУСКУ ТОРГОВЛИ", _LOG)
    log_info(f"   - Валютная пара: {active_symbol}", _LOG)
    log_info(f"   - Биржа: {cfg.exchange_id}", _LOG)
    log_info(f"   - Режим: {mode_str}", _LOG)
    log_info(f"   - Окружение: {cfg.environment}", _LOG)
    log_info(f"   - Стартовый tick_id: {tick_id}", _LOG)
    log_separator(_LOG)

    # === ЗАПУСК ТОРГОВОГО ЦИКЛА ===
    log_info("🔄 Начинаем основной торговый цикл...", _LOG)
    log_info(f"🎯 Подключаемся к тикеру для символа: {active_symbol}", _LOG)

    try:
        await _run_realtime_core(
            tick_source=tick_source,
            pipeline=pipeline,
            snapshot_svc=snapshot_svc,
            context=context,
            cfg=cfg,
            symbol=active_symbol,
            start_tick_id=tick_id,
        )
    finally:
        orderbook_task.cancel()
        try:
            await orderbook_task
        except asyncio.CancelledError:
            pass

        await connector.close()
        log_info("🛑 Коннектор закрыт, система остановлена", _LOG)

