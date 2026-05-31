"""Оркестратор прогона бэктеста.

Склеивает: HistoricalTickSource → TickPipelineService → FillSimulator → MetricsCollector.
"""

from __future__ import annotations

from typing import Any

from src.application.backtest.backtest_config import BacktestConfig
from src.application.backtest.fill_simulator import FillSimulator
from src.application.backtest.historical_tick_source import HistoricalTickSource
from src.application.backtest.metrics_collector import BacktestReport, MetricsCollector
from src.application.services.ticker_pipeline_service import TickPipelineService
from src.config.config import AppConfig
from src.domain.services.context.context_initializer import init_context


# Нейтральный стакан: BUY-сигналы не блокируются orderbook-фильтром.
_NEUTRAL_ORDER_BOOK: dict[str, Any] = {
    "bids": [[1.0, 1000.0]],
    "asks": [[1.0, 1000.0]],
    "symbol": "",
    "timestamp": 0,
    "datetime": "",
    "nonce": None,
}


class BacktestRunner:
    """Прогоняет боевой конвейер process_tick на исторических данных.

    Использует тот же TickPipelineService, что и боевой режим — логика
    принятия решений не дублируется.
    """

    def __init__(
        self,
        app_config: AppConfig,
        backtest_config: BacktestConfig,
    ) -> None:
        """
        Args:
            app_config: Конфигурация приложения (берётся из load_config()).
            backtest_config: Параметры прогона бэктеста.
        """
        self._cfg = app_config
        self._bt_cfg = backtest_config
        self._pipeline = TickPipelineService(app_config)
        self._filler = FillSimulator(
            buy_fee_percent=backtest_config.buy_fee_percent,
            sell_fee_percent=backtest_config.sell_fee_percent,
        )
        self._metrics = MetricsCollector(backtest_config.initial_balance)

    def run(self, candles: list[list]) -> BacktestReport:
        """Прогнать бэктест на переданных свечах.

        Args:
            candles: Список OHLCV-свечей [[ts_ms, o, h, l, c, v], ...].

        Returns:
            BacktestReport с итоговыми метриками.
        """
        symbol = self._bt_cfg.symbol
        context = self._build_context(symbol)

        tick_source = HistoricalTickSource(
            candles=candles,
            symbol=symbol,
            until_ms=self._bt_cfg.until_ms,
        )

        for ticker_id, tick in enumerate(tick_source.stream(), start=1):
            price: float = tick["last"]
            ts: int = tick["ts"]

            # Установить нейтральный стакан для orderbook-фильтра
            ob = dict(_NEUTRAL_ORDER_BOOK)
            ob["symbol"] = symbol
            ob["timestamp"] = ts
            context.setdefault("order_book", {})[symbol] = ob

            # Боевой конвейер: IND → STRAT → ORCH → EXEC
            self._pipeline.process_tick(
                context,
                symbol=symbol,
                ticker_id=ticker_id,
                price=price,
                ts=ts,
            )

            # Симулятор исполнения
            self._filler.on_tick(context, symbol=symbol, price=price, ts=ts)

            # Фиксация метрик
            self._metrics.record(context, symbol=symbol, ts=ts)

        final_balance = context.get("backtest_balance", self._bt_cfg.initial_balance)
        return self._metrics.finalize(final_balance)

    def _build_context(self, symbol: str) -> dict[str, Any]:
        """Построить начальный контекст с балансом для бэктеста."""
        context = init_context(self._cfg)
        context["backtest_balance"] = self._bt_cfg.initial_balance
        # Балансы для RiskManager
        quote_currency = symbol.split("/")[1] if "/" in symbol else "USDT"
        context["balances"] = {
            quote_currency: {
                "free": self._bt_cfg.initial_balance,
                "used": 0.0,
                "total": self._bt_cfg.initial_balance,
            }
        }
        return context


__all__ = ["BacktestRunner"]
