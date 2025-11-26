import time
from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import setup_logging, log_stage
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.context.state import init_context, update_metrics
from src.domain.services.indicators.indicator_engine import compute_indicators
from src.domain.services.strategies.strategy_hub import evaluate_strategies
from src.domain.services.orchestrator.orchestrator import decide
from src.domain.services.execution.execution_service import execute


def run(max_ticks: int = 10, symbols: List[str] | None = None, tick_sleep_sec: float = 0.2) -> None:
    """Запуск упрощённого тикового конвейера.

    Последовательность стадий:
    TickSource -> Indicators -> Strategies -> Orchestrator -> Execution.
    """

    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT"]

    setup_logging()

    # [BOOT]
    log_stage("BOOT", "init app")

    # Initialize config and context
    config: Dict[str, Any] = {
        "symbols": symbols,
        "tick_sleep_sec": tick_sleep_sec,
        "max_ticks": max_ticks,
    }

    context = init_context(config)

    # [LOAD]
    log_stage(
        "LOAD",
        "would load pairs/orders/positions from storage",
        symbols=",".join(symbols),
        orders=0,
        positions=0,
    )

    # [WARMUP]
    log_stage("WARMUP", "would warm-up indicators and order books from history")

    # Main loop
    log_stage("LOOP", "start main loop", limit=max_ticks)

    start_ts = time.time()
    tick_id = 0

    for tick in generate_ticks(symbols, max_ticks=max_ticks, sleep_sec=tick_sleep_sec):
        tick_id += 1
        symbol = tick["symbol"]
        price = tick["price"]

        # [TICK]
        log_stage("TICK", "received tick", tick_id=tick_id, symbol=symbol, price=price)

        # [FEEDS]
        log_stage(
            "FEEDS",
            "CLASS:MarketCache:update() - получает Ticker, обновляет market cache, ничего не возвращает",
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
            "CLASS:ContextBuilder:compose() - получает market/indicators/positions/risk, возвращает dict контекст",
            tick_id=tick_id,
            symbol=symbol,
            has_ind=True,
            has_pos=len(context["positions"]),
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
                "CLASS:ExecutionService:execute() - HOLD: ничего не отправляем",
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
            log_stage("HEARTBEAT", "alive", ticks=tick_id, tps=round(tps, 3))

    # [STOP]
    elapsed = time.time() - start_ts
    log_stage("STOP", "graceful stop", total_ticks=tick_id, elapsed_sec=round(elapsed, 3))

