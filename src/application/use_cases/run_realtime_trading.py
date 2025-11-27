import time
from typing import List

from src.infrastructure.logging.logging_setup import setup_logging, log_stage
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.market_data.orderflow_simulator import (
    update_orderflow_from_tick,
)
from src.domain.services.context.state import (
    init_context,
    apply_state_snapshot,
    make_state_snapshot,
)
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.infrastructure.repositories import InMemoryCurrencyPairRepository
from src.config.config import load_config
from src.application.context import build_context
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore
from src.application.services.tick_pipeline_service import TickPipelineService

def run(
    pair_repository: ICurrencyPairRepository | None = None,
    *,
    symbol: str | None = None,
) -> None:
    """Запуск упрощённого тикового конвейера.

    Последовательность стадий:
    TickSource -> Indicators -> Strategies -> Orchestrator -> Execution.

    На уровне приложения прототип обслуживает **ровно одну** валютную
    пару. Наружу она всегда передаётся через параметр
    ``symbol="BTC/USDT"``. Поддержка списков ``symbols`` на этом уровне
    полностью убрана.
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
    snapshot_key = f"{cfg.environment}:{cfg.symbol}"
    loaded_snapshot = snapshot_store.load_snapshot(snapshot_key)
    loaded_tick_id = 0

    if loaded_snapshot is not None:
        apply_state_snapshot(context, symbol=cfg.symbol, snapshot=loaded_snapshot)
        loaded_tick_id = int(loaded_snapshot.get("tick_id") or 0)
        log_stage(
            "LOAD",
            "📦 Снапшот state найден и загружен",
            symbol=cfg.symbol,
            tick_id=loaded_tick_id,
        )
    else:
        log_stage(
            "LOAD",
            "📦 Снапшот state не найден, стартуем с пустого in-memory state",
            symbol=cfg.symbol,
        )

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
        "🔄 Старт основного торгового цикла",
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
            interval = getattr(cfg, "state_snapshot_interval_ticks", 0)
            if interval > 0 and tick_id % interval == 0:
                snapshot = make_state_snapshot(
                    context, symbol=symbol, tick_id=tick_id
                )
                snapshot_store.save_snapshot(snapshot_key, snapshot)

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
        log_stage("STOP", "🛑  Остановка конвейера", total_ticks=tick_id, elapsed_sec=round(elapsed, 3))

