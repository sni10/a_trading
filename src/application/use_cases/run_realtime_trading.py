import asyncio
import time
from typing import List

from src.infrastructure.logging.logging_setup import setup_logging, log_stage
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.market_data.orderflow_simulator import (
    update_orderflow_from_tick,
)
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
    cfg = load_config(
        symbol=symbol,
    )

    # Один процесс прототипа обслуживает ровно одну валютную пару.
    active_symbol = cfg.symbol

    # Репозиторий пар: либо передан снаружи (в будущем — обёртка над БД),
    # либо создаём in-memory репозиторий из одного символа конфига.
    if pair_repository is None:
        pair_repository = InMemoryCurrencyPairRepository.from_symbols([cfg.symbol])

    pair = pair_repository.get_by_symbol(active_symbol)
    if pair is None:
        raise RuntimeError(f"Currency pair {active_symbol!r} is not configured")
    if not pair.enabled:
        raise RuntimeError(f"Currency pair {active_symbol!r} is disabled for trading")

    # [BOOT]
    log_stage(
        "BOOT",
        "Запуск демо‑конвейера",
        environment=cfg.environment,
        symbol=cfg.symbol,
    )

    # Базовый dict‑контекст на основе типизированного AppConfig
    context = init_context(cfg)

    # Обогащаем контекст CurrencyPair и in-memory кэшами, используя
    # репозиторий пар как единственный источник правды.
    context = build_context(cfg, context, pair_repository=pair_repository)

    # --- Загрузка state из снапшота (если есть) ---
    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(snapshot_store, cfg)
    loaded_tick_id = snapshot_svc.load(context)

    # [WARMUP]
    log_stage(
        "WARMUP",
        "🔥 Прогрев индикаторов и стаканов (исторические данные, OHLCV)",
        indicator_fast_interval=cfg.indicator_fast_interval,
        indicator_medium_interval=cfg.indicator_medium_interval,
        indicator_heavy_interval=cfg.indicator_heavy_interval,
    )

    # Main loop
    log_stage(
        "LOOP",
        "🔄 Старт основного торгового цикла (offline demo)",
        max_ticks=cfg.max_ticks,
        tick_sleep_sec=cfg.tick_sleep_sec,
    )

    start_ts = time.time()
    tick_id = loaded_tick_id

    # Единый конвейер обработки одного тика без I/O.
    pipeline = TickPipelineService(cfg)

    try:
        for tick in generate_ticks(
            cfg.symbol, max_ticks=cfg.max_ticks, sleep_sec=cfg.tick_sleep_sec
        ):
            tick_id += 1
            symbol = tick["symbol"]
            price = tick["price"]
            ts = tick["ts"]

            # [TICK]
            log_stage(
                "TICK",
                "📈  Тик получен",
                tick_id=tick_id,
                symbol=symbol,
                price=price,
            )

            # [FEEDS] + симуляция стакана/ордерфлоу остаются в демо‑режиме.
            log_stage(
                "FEEDS",
                "🌐  Обновление market‑состояния и кэша по тику",
                tick_id=tick_id,
                symbol=symbol,
            )

            # Дополнительно симулируем стакан/трейды/бары поверх тика.
            # В боевом async‑сценарии эту роль выполняет реальный коннектор
            # и воркер стакана; здесь остаётся только demo‑симуляция.
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

            # [HEARTBEAT]
            if tick_id % 5 == 0:
                elapsed = time.time() - start_ts
                tps = tick_id / elapsed if elapsed > 0 else 0.0
                log_stage(
                    "HEARTBEAT",
                    "💓  Конвейер жив",
                    ticks=tick_id,
                    tps=round(tps, 3),
                )

    except KeyboardInterrupt:
        log_stage("WARN", "Прерывание по Ctrl+C", tick_id=tick_id)
    except Exception as exc:
        log_stage("ERROR", "Критическая ошибка в торговом цикле", tick_id=tick_id, error=str(exc), error_type=type(exc).__name__)
        raise
    finally:
        # [STOP]
        elapsed = time.time() - start_ts
        log_stage(
            "STOP",
            "🛑  Остановка offline‑конвейера",
            total_ticks=tick_id,
            elapsed_sec=round(elapsed, 3),
        )


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
    """

    loop = asyncio.get_event_loop()
    start_ts = loop.time()
    tick_id = start_tick_id

    async for ticker in tick_source.stream():
        tick_id += 1

        price = float(ticker["last"])
        ts = ticker["timestamp"] or int(loop.time() * 1000)

        pipeline.process_tick(
            context,
            symbol=symbol,
            tick_id=tick_id,
            price=price,
            ts=ts,
        )

        snapshot_svc.maybe_save(context, tick_id=tick_id)

        if tick_id % 5 == 0:
            elapsed = loop.time() - start_ts
            tps = tick_id / elapsed if elapsed > 0 else 0.0
            log_stage(
                "HEARTBEAT",
                "Конвейер жив",
                ticks=tick_id,
                tps=round(tps, 3),
            )


async def run_realtime_from_exchange(symbol: str | None = None) -> None:
    """Боевой async‑сценарий real‑time торговли от реальной биржи.

    Использует ``CcxtProExchangeConnector`` + ``TickSource`` и
    асинхронный воркер стакана. Внутри **нет** ``generate_ticks`` и
    симулятора стакана; все данные приходят с биржи.
    """

    setup_logging()

    cfg = load_config(symbol=symbol)
    active_symbol = cfg.symbol

    # Репозиторий пар и валидация активной пары
    pair_repo = InMemoryCurrencyPairRepository.from_symbols([active_symbol])
    pair = pair_repo.get_by_symbol(active_symbol)
    if pair is None:
        raise RuntimeError(f"Currency pair {active_symbol!r} is not configured")
    if not pair.enabled:
        raise RuntimeError(f"Currency pair {active_symbol!r} is disabled for trading")

    log_stage(
        "BOOT",
        "Запуск боевого async‑конвейера",
        environment=cfg.environment,
        symbol=active_symbol,
    )

    # Контекст и снапшоты
    context = init_context(cfg)
    context = build_context(cfg, context, pair_repository=pair_repo)

    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(snapshot_store, cfg)
    tick_id = snapshot_svc.load(context)

    # Сетевой коннектор и источник тиков
    connector = CcxtProExchangeConnector(cfg)
    tick_source = TickSource(connector, symbol=active_symbol)

    # Воркер стакана
    orderbook_task = asyncio.create_task(
        _run_order_book_refresh_worker(connector, context, cfg, symbol=active_symbol)
    )

    pipeline = TickPipelineService(cfg)

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

