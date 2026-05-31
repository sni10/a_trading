"""Юнит-тесты для модулей бэктеста.

Покрытие:
- OhlcvCache: сохранение и загрузка свечей.
- HistoricalTickSource: маппинг свечей → тики, фильтр until_ms.
- FillSimulator: сценарии «купил→продал», «не купил», «купил→таймаут».
- MetricsCollector: метрики на синтетических сделках.
- BacktestConfig: валидация.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.application.backtest.backtest_config import BacktestConfig
from src.application.backtest.fill_simulator import FillSimulator
from src.application.backtest.historical_tick_source import HistoricalTickSource
from src.application.backtest.metrics_collector import MetricsCollector
from src.application.backtest.ohlcv_cache import OhlcvCache
from src.domain.entities.deal import Deal
from src.domain.entities.order import Order, OrderFee


# ---------------------------------------------------------------------------
# Вспомогательные фабрики
# ---------------------------------------------------------------------------

def _make_candle(ts_ms: int, close: float) -> list:
    """Создать минимальную OHLCV-свечу."""
    return [ts_ms, close, close, close, close, 1.0]


def _make_open_deal(
    symbol: str = "BTC/USDT",
    buy_price: float = 100.0,
    sell_price: float = 110.0,
    amount: float = 1.0,
    ts: int = 1_000_000,
) -> Deal:
    """Создать сделку в статусе pending с открытыми BUY и SELL ордерами."""
    buy_order = Order(
        symbol=symbol,
        status="open",
        side="buy",
        type="limit",
        amount=amount,
        price=buy_price,
        filled=0.0,
        remaining=amount,
        cost=buy_price * amount,
        timestamp=ts,
    )
    sell_order = Order(
        symbol=symbol,
        status="open",
        side="sell",
        type="limit",
        amount=amount,
        price=sell_price,
        filled=0.0,
        remaining=amount,
        cost=sell_price * amount,
        timestamp=ts,
    )
    deal = Deal(
        symbol=symbol,
        status=Deal.STATUS_PENDING,
        created_at=ts,
        buy_order=buy_order,
        sell_order=sell_order,
    )
    return deal


def _make_context(
    symbol: str,
    initial_balance: float,
    deals: list[Deal] | None = None,
) -> dict:
    """Создать минимальный контекст для тестов."""
    return {
        "deals": {symbol: deals or []},
        "orders": {symbol: []},
        "backtest_balance": initial_balance,
    }


# ---------------------------------------------------------------------------
# OhlcvCache
# ---------------------------------------------------------------------------

class TestOhlcvCache:
    def test_save_and_load(self, tmp_path: Path) -> None:
        cache = OhlcvCache(str(tmp_path))
        candles = [[1_000_000, 1.0, 2.0, 0.5, 1.5, 100.0]]
        cache.save("BTC/USDT", "1h", 1_000_000, candles)
        loaded = cache.load("BTC/USDT", "1h", 1_000_000)
        assert loaded == candles

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        cache = OhlcvCache(str(tmp_path))
        assert cache.load("ETH/USDT", "1h", 999) is None

    def test_save_creates_file(self, tmp_path: Path) -> None:
        cache = OhlcvCache(str(tmp_path))
        cache.save("SOL/USDT", "5m", None, [])
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].suffix == ".json"

    def test_symbol_sanitization(self, tmp_path: Path) -> None:
        """Слеш в символе не должен ломать имя файла."""
        cache = OhlcvCache(str(tmp_path))
        cache.save("BTC/USDT", "1h", 0, [[1, 2, 3, 4, 5, 6]])
        loaded = cache.load("BTC/USDT", "1h", 0)
        assert loaded is not None


# ---------------------------------------------------------------------------
# HistoricalTickSource
# ---------------------------------------------------------------------------

class TestHistoricalTickSource:
    def test_mapping_close_to_last(self) -> None:
        candles = [_make_candle(1_000_000, 95.5)]
        source = HistoricalTickSource(candles, "BTC/USDT")
        ticks = list(source.stream())
        assert len(ticks) == 1
        assert ticks[0]["last"] == 95.5
        assert ticks[0]["symbol"] == "BTC/USDT"
        assert ticks[0]["ts"] == 1_000_000

    def test_timestamps_monotonic(self) -> None:
        candles = [_make_candle(i * 3600_000, 100.0 + i) for i in range(10)]
        source = HistoricalTickSource(candles, "BTC/USDT")
        ticks = list(source.stream())
        timestamps = [t["ts"] for t in ticks]
        assert timestamps == sorted(timestamps)

    def test_until_ms_filter(self) -> None:
        candles = [_make_candle(i * 3600_000, 100.0) for i in range(5)]
        source = HistoricalTickSource(candles, "BTC/USDT", until_ms=2 * 3600_000)
        ticks = list(source.stream())
        assert len(ticks) == 3  # ts=0, 3600000, 7200000

    def test_len_without_filter(self) -> None:
        candles = [_make_candle(i * 3600_000, 100.0) for i in range(7)]
        source = HistoricalTickSource(candles, "BTC/USDT")
        assert len(source) == 7

    def test_empty_candles(self) -> None:
        source = HistoricalTickSource([], "BTC/USDT")
        assert list(source.stream()) == []


# ---------------------------------------------------------------------------
# FillSimulator
# ---------------------------------------------------------------------------

class TestFillSimulator:
    def test_buy_filled_when_price_at_buy_level(self) -> None:
        """BUY исполняется, когда price == buy_price."""
        deal = _make_open_deal(buy_price=100.0, sell_price=110.0, amount=1.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=0.0)

        sim.on_tick(context, "BTC/USDT", price=100.0, ts=2_000_000)

        assert deal.buy_order.status == "closed"
        assert deal.is_open()
        # Баланс уменьшился на cost покупки
        assert context["backtest_balance"] == pytest.approx(900.0)

    def test_sell_filled_when_price_reaches_target(self) -> None:
        """SELL исполняется когда price >= sell_price (после BUY)."""
        deal = _make_open_deal(buy_price=100.0, sell_price=110.0, amount=1.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=0.0)

        # BUY
        sim.on_tick(context, "BTC/USDT", price=100.0, ts=2_000_000)
        assert deal.is_open()

        # SELL
        sim.on_tick(context, "BTC/USDT", price=110.0, ts=3_000_000)

        assert deal.sell_order.status == "closed"
        assert deal.is_closed()
        # Итоговый баланс: 1000 - 100 + 110 = 1010
        assert context["backtest_balance"] == pytest.approx(1010.0)

    def test_buy_not_filled_when_price_above_buy_level(self) -> None:
        """BUY не исполняется, если цена выше уровня покупки."""
        deal = _make_open_deal(buy_price=100.0, sell_price=110.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=0.0)

        sim.on_tick(context, "BTC/USDT", price=101.0, ts=2_000_000)

        assert deal.buy_order.is_open()
        assert context["backtest_balance"] == pytest.approx(1000.0)

    def test_fees_deducted_on_buy(self) -> None:
        """Комиссия списывается при покупке."""
        deal = _make_open_deal(buy_price=100.0, amount=1.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=1.0, sell_fee_percent=0.0)  # 1% fee

        sim.on_tick(context, "BTC/USDT", price=100.0, ts=1)

        # cost=100, fee=1.0 → balance = 1000 - 100 - 1 = 899
        assert context["backtest_balance"] == pytest.approx(899.0)

    def test_fees_deducted_on_sell(self) -> None:
        """Комиссия удерживается при продаже."""
        deal = _make_open_deal(buy_price=100.0, sell_price=110.0, amount=1.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=1.0)  # 1% sell fee

        sim.on_tick(context, "BTC/USDT", price=100.0, ts=1)
        sim.on_tick(context, "BTC/USDT", price=110.0, ts=2)

        # buy: 1000 - 100 = 900; sell: 900 + 110 - 1.1 = 1008.9
        assert context["backtest_balance"] == pytest.approx(1008.9)

    def test_closed_deal_ignored(self) -> None:
        """Уже закрытая сделка не трогается повторно."""
        deal = _make_open_deal(buy_price=100.0, sell_price=110.0)
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=0.0)

        sim.on_tick(context, "BTC/USDT", price=100.0, ts=1)
        sim.on_tick(context, "BTC/USDT", price=110.0, ts=2)
        balance_after_close = context["backtest_balance"]

        # Ещё один тик — не должен менять баланс
        sim.on_tick(context, "BTC/USDT", price=110.0, ts=3)
        assert context["backtest_balance"] == pytest.approx(balance_after_close)

    def test_sell_not_filled_before_buy(self) -> None:
        """SELL не исполняется, пока BUY не заполнен."""
        deal = _make_open_deal(buy_price=100.0, sell_price=95.0)  # sell ниже buy
        context = _make_context("BTC/USDT", 1000.0, [deal])
        sim = FillSimulator(buy_fee_percent=0.0, sell_fee_percent=0.0)

        # price выше buy_price → BUY не исполняется → SELL тоже
        sim.on_tick(context, "BTC/USDT", price=110.0, ts=1)

        assert deal.buy_order.is_open()
        assert deal.sell_order.is_open()


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class TestMetricsCollector:
    def _make_closed_deal_with_profit(
        self,
        symbol: str,
        buy_price: float,
        sell_price: float,
        amount: float = 1.0,
    ) -> Deal:
        """Создать закрытую сделку с известным PnL."""
        deal = _make_open_deal(symbol, buy_price, sell_price, amount)
        # Вручную закрыть
        deal.buy_order.status = "closed"
        deal.buy_order.filled = amount
        deal.buy_order.cost = buy_price * amount
        deal.buy_order.fee = OrderFee(currency="USDT", cost=0.0)
        deal.sell_order.status = "closed"
        deal.sell_order.filled = amount
        deal.sell_order.cost = sell_price * amount
        deal.sell_order.fee = OrderFee(currency="USDT", cost=0.0)
        deal.status = Deal.STATUS_CLOSED
        return deal

    def test_no_trades(self) -> None:
        """Нет сделок — нулевые метрики."""
        collector = MetricsCollector(initial_balance=1000.0)
        context = {"deals": {"BTC/USDT": []}, "backtest_balance": 1000.0}
        collector.record(context, "BTC/USDT", ts=1)
        report = collector.finalize(1000.0)

        assert report.total_trades == 0
        assert report.winrate_pct == 0.0
        assert report.total_pnl == 0.0

    def test_winning_trade_counted(self) -> None:
        """Прибыльная сделка учитывается корректно."""
        deal = self._make_closed_deal_with_profit("BTC/USDT", 100.0, 110.0, 1.0)
        collector = MetricsCollector(initial_balance=1000.0)
        context = {"deals": {"BTC/USDT": [deal]}, "backtest_balance": 1010.0}

        collector.record(context, "BTC/USDT", ts=1)
        report = collector.finalize(1010.0)

        assert report.total_trades == 1
        assert report.winning_trades == 1
        assert report.total_pnl == pytest.approx(10.0)
        assert report.winrate_pct == pytest.approx(100.0)

    def test_mixed_trades_winrate(self) -> None:
        """2 прибыльных + 1 убыточная → winrate 66.7%."""
        d1 = self._make_closed_deal_with_profit("BTC/USDT", 100.0, 110.0)
        d2 = self._make_closed_deal_with_profit("BTC/USDT", 100.0, 108.0)
        d3 = self._make_closed_deal_with_profit("BTC/USDT", 100.0, 95.0)  # убыток

        collector = MetricsCollector(initial_balance=1000.0)
        context = {"deals": {"BTC/USDT": [d1, d2, d3]}, "backtest_balance": 1013.0}
        collector.record(context, "BTC/USDT", ts=1)
        report = collector.finalize(1013.0)

        assert report.total_trades == 3
        assert report.winning_trades == 2
        assert report.losing_trades == 1
        assert report.winrate_pct == pytest.approx(200.0 / 3, abs=0.1)

    def test_max_drawdown_calculated(self) -> None:
        """Max drawdown = пик − минимум после пика."""
        collector = MetricsCollector(initial_balance=1000.0)
        context_base = {"deals": {"BTC/USDT": []}}

        for equity in [1000.0, 1100.0, 900.0, 1050.0]:
            ctx = dict(context_base, backtest_balance=equity)
            collector.record(ctx, "BTC/USDT", ts=1)

        report = collector.finalize(1050.0)
        # Пик=1100, минимум после=900 → DD=200
        assert report.max_drawdown == pytest.approx(200.0)

    def test_return_pct(self) -> None:
        """Доходность = (final - initial) / initial * 100."""
        collector = MetricsCollector(initial_balance=1000.0)
        context = {"deals": {"BTC/USDT": []}, "backtest_balance": 1000.0}
        collector.record(context, "BTC/USDT", ts=1)
        report = collector.finalize(1200.0)

        assert report.return_pct == pytest.approx(20.0)

    def test_equity_curve_length(self) -> None:
        """Equity-кривая содержит точку на каждый record()."""
        collector = MetricsCollector(initial_balance=500.0)
        context = {"deals": {"BTC/USDT": []}, "backtest_balance": 500.0}

        for i in range(5):
            collector.record(context, "BTC/USDT", ts=i * 1000)

        report = collector.finalize(500.0)
        assert len(report.equity_curve) == 5


# ---------------------------------------------------------------------------
# BacktestConfig
# ---------------------------------------------------------------------------

class TestBacktestConfig:
    def test_valid_config_ok(self) -> None:
        cfg = BacktestConfig(
            symbol="BTC/USDT",
            timeframe="1h",
            since_ms=1_700_000_000_000,
            until_ms=1_710_000_000_000,
            initial_balance=500.0,
        )
        cfg.validate()  # не должен падать

    def test_empty_symbol_raises(self) -> None:
        cfg = BacktestConfig(symbol="", timeframe="1h", since_ms=1_000_000)
        with pytest.raises(ValueError, match="symbol"):
            cfg.validate()

    def test_until_before_since_raises(self) -> None:
        cfg = BacktestConfig(
            symbol="BTC/USDT",
            timeframe="1h",
            since_ms=2_000_000,
            until_ms=1_000_000,
        )
        with pytest.raises(ValueError, match="until_ms"):
            cfg.validate()

    def test_negative_balance_raises(self) -> None:
        cfg = BacktestConfig(
            symbol="BTC/USDT", timeframe="1h", since_ms=1_000_000, initial_balance=-1
        )
        with pytest.raises(ValueError, match="initial_balance"):
            cfg.validate()
