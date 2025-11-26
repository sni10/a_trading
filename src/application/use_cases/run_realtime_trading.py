import time
from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import setup_logging, log_stage
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.context.state import init_context, update_metrics
from src.domain.services.indicators.indicator_engine import compute_indicators
from src.domain.services.strategies.strategy_hub import evaluate_strategies
from src.domain.services.orchestrator.orchestrator import decide
from src.domain.services.execution.execution_service import execute
from src.config.config import load_config
from src.application.context import build_context


def run(
    max_ticks: int = 10,
    symbols: List[str] | None = None,
    tick_sleep_sec: float = 0.2,
) -> None:
    """Запуск упрощённого тикового конвейера.

    Последовательность стадий:
    TickSource -> Indicators -> Strategies -> Orchestrator -> Execution.
    """

    setup_logging()

    # Инициализируем AppConfig из env + параметров run()
    cfg = load_config(symbols=symbols, max_ticks=max_ticks, tick_sleep_sec=tick_sleep_sec)

    # [BOOT]
    log_stage(
        "BOOT",
        "Запуск демо‑конвейера",
        environment=cfg.environment,
        symbols=",".join(cfg.symbols),
    )

    # Приводим к простому dict, чтобы не ломать существующий init_context
    config: Dict[str, Any] = {
        "environment": cfg.environment,
        "symbols": cfg.symbols,
        "tick_sleep_sec": cfg.tick_sleep_sec,
        "max_ticks": cfg.max_ticks,
        "indicator_fast_interval": cfg.indicator_fast_interval,
        "indicator_medium_interval": cfg.indicator_medium_interval,
        "indicator_heavy_interval": cfg.indicator_heavy_interval,
    }

    # Базовый dict‑контекст (как было ранее)
    context = init_context(config)

    # Обогащаем контекст CurrencyPair и in-memory кэшами под каждый символ
    context = build_context(cfg, context)

    # [LOAD]
    log_stage(
        "LOAD",
        "📦 Загрузка state (пока мок: пары/ордера/позиции из памяти)",
        symbols=",".join(cfg.symbols),
        orders=0,
        positions=0,
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
    log_stage("LOOP", "🔄 Старт основного торгового цикла", max_ticks=cfg.max_ticks, tick_sleep_sec=cfg.tick_sleep_sec)

    start_ts = time.time()
    tick_id = 0

    for tick in generate_ticks(
        cfg.symbols, max_ticks=cfg.max_ticks, sleep_sec=cfg.tick_sleep_sec
    ):
        tick_id += 1
        symbol = tick["symbol"]
        price = tick["price"]

        # [TICK]
        log_stage("TICK", "📈 Тик получен", tick_id=tick_id, symbol=symbol, price=price)

        # [FEEDS]
        log_stage(
            "FEEDS",
            "🌐 Обновление market‑кэша по тикеру",
            tick_id=tick_id,
            symbol=symbol,
        )
        context["market"][symbol] = {"last_price": price, "ts": tick["ts"]}

        # [IND]
        indicators = compute_indicators(context, tick_id=tick_id, symbol=symbol, price=price)
        context["indicators"][symbol] = indicators

        # [CTX]
        log_stage(
            "CTX",
            "🧠 Сбор контекста для стратегий",
            tick_id=tick_id,
            symbol=symbol,
            has_ind=True,
            positions=len(context["positions"]),
        )

        # [STRAT]
        intents = evaluate_strategies(context, tick_id=tick_id, symbol=symbol)

        # [ORCH]
        decision = decide(intents, context, tick_id=tick_id, symbol=symbol)

        # [EXEC]
        if decision.get("action") != "HOLD":
            execute(decision, context, tick_id=tick_id, symbol=symbol)
        else:
            log_stage(
                "EXEC",
                "⚙️ HOLD: заявки в биржу не отправляются",
                tick_id=tick_id,
                symbol=symbol,
                action=decision.get("action"),
            )

        # [STATE]
        update_metrics(context, tick_id=tick_id)

        # [HEARTBEAT]
        if tick_id % 5 == 0:
            elapsed = time.time() - start_ts
            tps = tick_id / elapsed if elapsed > 0 else 0.0
            log_stage("HEARTBEAT", "💓 Конвейер жив", ticks=tick_id, tps=round(tps, 3))

    # [STOP]
    elapsed = time.time() - start_ts
    log_stage("STOP", "🛑 Остановка конвейера", total_ticks=tick_id, elapsed_sec=round(elapsed, 3))

