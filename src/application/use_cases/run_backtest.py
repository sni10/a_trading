"""Use case: запуск офлайн-бэктеста.

Загружает исторические данные (с кэшем), прогоняет BacktestRunner
и возвращает BacktestReport.
"""

from __future__ import annotations

import asyncio

from src.application.backtest.backtest_config import BacktestConfig
from src.application.backtest.backtest_runner import BacktestRunner
from src.application.backtest.metrics_collector import BacktestReport
from src.application.backtest.ohlcv_cache import OhlcvCache
from src.config.config import AppConfig
from src.domain.interfaces.exchange_connector import IExchangeConnector


async def fetch_candles(
    connector: IExchangeConnector,
    config: BacktestConfig,
) -> list[list]:
    """Загрузить свечи из кэша или с биржи.

    Args:
        connector: Реализация IExchangeConnector с методом fetch_ohlcv.
        config: Параметры бэктеста.

    Returns:
        Список OHLCV-свечей.
    """
    cache = OhlcvCache(config.cache_dir)

    if config.use_cache:
        cached = cache.load(config.symbol, config.timeframe, config.since_ms)
        if cached is not None:
            return cached

    candles = await connector.fetch_ohlcv(
        symbol=config.symbol,
        timeframe=config.timeframe,
        since=config.since_ms,
        limit=1000,
    )

    if config.use_cache:
        cache.save(config.symbol, config.timeframe, config.since_ms, candles)

    return candles


def run_backtest(
    app_config: AppConfig,
    backtest_config: BacktestConfig,
    candles: list[list],
) -> BacktestReport:
    """Запустить бэктест на переданных свечах.

    Args:
        app_config: Конфигурация приложения.
        backtest_config: Параметры бэктеста.
        candles: Исторические OHLCV-свечи.

    Returns:
        BacktestReport с итоговыми метриками.
    """
    backtest_config.validate()
    runner = BacktestRunner(app_config, backtest_config)
    return runner.run(candles)


__all__ = ["run_backtest", "fetch_candles"]
