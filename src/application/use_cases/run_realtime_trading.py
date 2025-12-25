"""Сценарий запуска realtime-торговли через биржевой коннектор."""

from __future__ import annotations

import asyncio

from src.application.context import build_context
from src.application.services.state_snapshot_service import StateSnapshotService
from src.application.services.ticker_pipeline_service import TickPipelineService
from src.application.repository_factory import build_repositories
from src.application.use_cases.run_offline_demo import run_demo_offline
from src.application.use_cases.trading_loop import run_realtime_core
from src.application.use_cases.worker_manager import run_order_book_refresh_worker
from src.application.workers.persistence_worker import PersistenceWorker
from src.config.config import AppConfig, load_config
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.services.context.state import init_context
from src.domain.services.ticker.ticker_source import TickSource
from src.infrastructure.connectors.ccxt_pro_exchange_connector import (
    CcxtProExchangeConnector,
)
from src.infrastructure.logging import (
    log_info,
    log_separator,
    log_stage,
    log_stat_block,
    log_warning,
    setup_logging,
)
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore

# Версия прототипа
__version__ = "0.1.0"

# Интервал логирования статистики (каждые N тиков)
TICKER_LOG_INTERVAL = 10

# Имя логгера для этого модуля
_LOG = __name__


async def run_realtime_from_exchange(symbol: str | None = None) -> None:
    """Боевой async‑сценарий real‑time торговли от реальной биржи.

    Использует ``CcxtProExchangeConnector`` + ``TickSource`` и
    асинхронный воркер стакана. Внутри **нет** ``generate_ticks`` и
    симулятора стакана; все данные приходят с биржи.
    """

    setup_logging()

    if not symbol:
        raise RuntimeError("Symbol is required (expected like 'BTC/USDT')")

    active_symbol = symbol
    cfg = load_config()

    # === СТАРТОВЫЙ БЛОК (как в bad_example) ===
    log_info(f"🚀 ЗАПУСК AlgoTrade Prototype v{__version__} для {active_symbol}", _LOG)

    # Репозитории (DB через SQLAlchemy)
    repos = build_repositories(cfg)
    pair_repo = repos.pair_repository

    # Bootstrap: если пары нет в БД — создаём с дефолтами.
    pair = pair_repo.get_by_symbol(active_symbol)
    if pair is None:
        base, quote = active_symbol.split("/", 1)
        pair = pair_repo.upsert(
            CurrencyPair(
                symbol=active_symbol,
                base_currency=base,
                quote_currency=quote,
            )
        )
        log_info(f"✅ Валютная пара {active_symbol} добавлена в БД (bootstrap)", _LOG)
    if not pair.enabled:
        raise RuntimeError(f"Currency pair {active_symbol!r} is disabled for trading")

    log_info(f"✅ Валютная пара {active_symbol} загружена и активна", _LOG)

    # Контекст и снапшоты
    context = init_context(cfg)
    log_info("✅ Базовый контекст инициализирован (init_context)", _LOG)
    
    context = build_context(cfg, context, pair_repository=pair_repo)
    log_info("✅ Контекст обогащён кэшами и CurrencyPair (build_context)", _LOG)

    # Снапшоты: файл-стораж + БД-репозитории
    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(
        snapshot_store,
        cfg,
        symbol=active_symbol,
        deal_repo=repos.deal_repository,
        order_repo=repos.order_repository,
        trade_repo=repos.trade_repository,
    )

    # 1. Загрузить реактивные данные из файл-стораж (индикаторы, метрики и т.д.)
    loaded_ticker_id = snapshot_svc.load(context)

    # 2. Загрузить персистентные данные из БД (сделки, ордера, трейды)
    snapshot_svc.load_from_db(context)

    # Важно: реактивные данные (тикеры, стакан, история цен) при запуске
    # всегда прогреваются заново, поэтому логический счётчик tick(ticker)_id
    # для НОВОЙ сессии всегда стартует с 0, даже если в снапшоте был
    # сохранён больший tick_id.
    if loaded_ticker_id > 0:
        log_info(
            f"📦 Загружен снапшот из файла (tick_id={loaded_ticker_id}), стартовый ticker_id новой сессии = 0",
            _LOG,
        )
    else:
        log_info("📦 Файловый снапшот не найден", _LOG)

    log_info("📦 Персистентные данные (сделки, ордера, трейды) загружены из БД", _LOG)

    # Сетевой коннектор и источник тиков
    connector = CcxtProExchangeConnector(cfg)
    ticker_source = TickSource(connector, symbol=active_symbol)

    mode_str = "Sandbox" if cfg.sandbox_mode else "Production"
    log_info(f"✅ Коннектор инициализирован ({cfg.exchange_id}, {mode_str})", _LOG)

    # Воркер стакана
    orderbook_task = asyncio.create_task(
        run_order_book_refresh_worker(connector, context, cfg, symbol=active_symbol)
    )
    log_info("✅ Воркер стакана запущен", _LOG)

    # Воркер периодического сброса в БД (каждые 3 минуты)
    persistence_worker = PersistenceWorker(
        snapshot_svc, context, symbol=active_symbol, interval_seconds=180
    )
    await persistence_worker.start()
    log_info("✅ Воркер персистентности запущен (интервал: 180 сек)", _LOG)

    pipeline = TickPipelineService(cfg)
    log_info("✅ Конвейер обработки тиков создан (TickPipelineService)", _LOG)

    # === СВОДКА ГОТОВНОСТИ СИСТЕМЫ ===
    log_separator(_LOG)
    log_info("🚀 СИСТЕМА ГОТОВА К ЗАПУСКУ ТОРГОВЛИ", _LOG)
    log_info(f"   - Валютная пара: {active_symbol}", _LOG)
    log_info(f"   - Биржа: {cfg.exchange_id}", _LOG)
    log_info(f"   - Режим: {mode_str}", _LOG)
    log_info(f"   - Окружение: {cfg.environment}", _LOG)
    log_info("   - Стартовый ticker_id: 0 (новая сессия)", _LOG)
    log_separator(_LOG)

    # === ЗАПУСК ТОРГОВОГО ЦИКЛА ===
    log_info("🔄 Начинаем основной торговый цикл...", _LOG)
    log_info(f"🎯 Подключаемся к тикеру для символа: {active_symbol}", _LOG)

    try:
        await run_realtime_core(
            ticker_source=ticker_source,
            pipeline=pipeline,
            snapshot_svc=snapshot_svc,
            context=context,
            cfg=cfg,
            symbol=active_symbol,
            start_ticker_id=0,
        )
    finally:
        # Остановка воркеров и финальное сохранение
        log_info("🛑 Остановка воркеров и сохранение состояния...", _LOG)

        # Остановить воркер персистентности (внутри сделает финальный сброс в БД)
        await persistence_worker.stop()
        log_info("✅ Воркер персистентности остановлен, финальный сброс в БД выполнен", _LOG)

        # Остановить воркер стакана
        orderbook_task.cancel()
        try:
            await orderbook_task
        except asyncio.CancelledError:
            pass
        log_info("✅ Воркер стакана остановлен", _LOG)

        await connector.close()
        log_info("🛑 Коннектор закрыт, система остановлена", _LOG)

