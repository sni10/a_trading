import time
from typing import List

from src.infrastructure.logging.logging_setup import setup_logging, log_stage
from src.domain.services.market_data.tick_source import generate_ticks
from src.domain.services.context.state import init_context, update_metrics
from src.domain.services.indicators.indicator_engine import compute_indicators
from src.domain.services.strategies.strategy_hub import evaluate_strategies
from src.domain.services.orchestrator.orchestrator import decide
from src.domain.services.execution.execution_service import execute
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.infrastructure.repositories import InMemoryCurrencyPairRepository
from src.config.config import load_config
from src.application.context import build_context

def run(
    max_ticks: int = 10,
    symbols: List[str] | None = None,
    tick_sleep_sec: float = 0.5,
    pair_repository: ICurrencyPairRepository | None = None,
    *,
    symbol: str | None = None,
) -> None:
    """Запуск упрощённого тикового конвейера.

    Последовательность стадий:
    TickSource -> Indicators -> Strategies -> Orchestrator -> Execution.

    На уровне приложения прототип обслуживает **ровно одну** валютную
    пару. Наружу рекомендуется передавать её через параметр
    ``symbol="BTC/USDT"``. Параметр ``symbols`` (список строк) оставлен
    только для обратной совместимости и будет удалён в будущих версиях.
    """

    setup_logging()

    # Нормализуем вход: либо одиночный symbol, либо список symbols.
    if symbol is not None and symbols is not None:
        raise ValueError("Pass either 'symbol' or 'symbols', not both")

    effective_symbols: List[str] | None
    if symbol is not None:
        effective_symbols = [symbol]
    else:
        effective_symbols = symbols

    # Инициализируем AppConfig из env + параметров run()
    cfg = load_config(
        symbols=effective_symbols,
        max_ticks=max_ticks,
        tick_sleep_sec=tick_sleep_sec,
    )

    # Один процесс прототипа обслуживает ровно одну валютную пару. На
    # этом уровне проверяем контракт и работаем только с cfg.symbols[0].
    if len(cfg.symbols) != 1:
        raise ValueError(
            f"This prototype expects exactly one symbol per process, got: {cfg.symbols}"
        )

    active_symbol = cfg.symbols[0]

    # Репозиторий пар: либо передан снаружи (в будущем — обёртка над БД),
    # либо создаём in-memory репозиторий из списка символов конфига.
    if pair_repository is None:
        pair_repository = InMemoryCurrencyPairRepository.from_symbols(cfg.symbols)

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
        symbols=",".join(cfg.symbols),
    )

    # Базовый dict‑контекст на основе типизированного AppConfig
    context = init_context(cfg)

    # Обогащаем контекст CurrencyPair и in-memory кэшами, используя
    # репозиторий пар как единственный источник правды.
    context = build_context(cfg, context, pair_repository=pair_repository)

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

    try:
        for tick in generate_ticks(
            cfg.symbols, max_ticks=cfg.max_ticks, sleep_sec=cfg.tick_sleep_sec
        ):
            tick_id += 1
            symbol = tick["symbol"]
            price = tick["price"]

            # [TICK]
            log_stage("TICK", "📈  Тик получен", tick_id=tick_id, symbol=symbol, price=price)

            # [FEEDS]
            log_stage(
                "FEEDS",
                "🌐  Обновление market‑кэша по тикеру",
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
                "🧠  Сбор контекста для стратегий",
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
                log_stage("HEARTBEAT", "💓  Конвейер жив", ticks=tick_id, tps=round(tps, 3))

    except KeyboardInterrupt:
        log_stage("WARN", "Прерывание по Ctrl+C", tick_id=tick_id)
    except Exception as exc:
        log_stage("ERROR", "Критическая ошибка в торговом цикле", tick_id=tick_id, error=str(exc), error_type=type(exc).__name__)
        raise
    finally:
        # [STOP]
        elapsed = time.time() - start_ts
        log_stage("STOP", "🛑  Остановка конвейера", total_ticks=tick_id, elapsed_sec=round(elapsed, 3))

