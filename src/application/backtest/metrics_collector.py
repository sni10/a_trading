"""Сбор метрик прибыльности для бэктеста.

Фиксирует equity-кривую и итоговые метрики по завершённым сделкам:
PnL, winrate, max drawdown, число сделок.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.entities.deal import Deal


@dataclass
class BacktestReport:
    """Итоговый отчёт бэктеста."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    winrate_pct: float = 0.0
    total_pnl: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_drawdown: float = 0.0
    final_balance: float = 0.0
    initial_balance: float = 0.0
    return_pct: float = 0.0
    equity_curve: list[tuple[int, float]] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [
            "=" * 50,
            "        BACKTEST REPORT",
            "=" * 50,
            f"  Сделок всего:      {self.total_trades}",
            f"  Прибыльных:        {self.winning_trades}",
            f"  Убыточных:         {self.losing_trades}",
            f"  Winrate:           {self.winrate_pct:.1f}%",
            f"  Суммарный PnL:     {self.total_pnl:+.4f} USDT",
            f"  Средний PnL:       {self.avg_pnl_per_trade:+.4f} USDT",
            f"  Max Drawdown:      {self.max_drawdown:.4f} USDT",
            f"  Стартовый баланс:  {self.initial_balance:.4f} USDT",
            f"  Итоговый баланс:   {self.final_balance:.4f} USDT",
            f"  Доходность:        {self.return_pct:+.2f}%",
            "=" * 50,
            "",
            "Допущения:",
            "  - bar-vs-tick: close свечи = last тик (упрощение)",
            "  - Упрощённая модель филлов (без проскальзывания)",
            "  - Нейтральный стакан (orderbook-фильтр не режет сигналы)",
            "  - Результат — оценка 'сверху'; реальные результаты ≤ бэктеста",
        ]
        return "\n".join(lines)


class MetricsCollector:
    """Собирает метрики по ходу бэктеста.

    Вызывайте ``record(context, symbol, ts)`` на каждом тике,
    ``finalize(final_balance)`` — после окончания прогона.
    """

    def __init__(self, initial_balance: float) -> None:
        """
        Args:
            initial_balance: Стартовый баланс в USDT.
        """
        self._initial_balance = initial_balance
        self._equity_curve: list[tuple[int, float]] = []
        self._closed_deals: list[Deal] = []
        self._seen_deal_ids: set[int] = set()

    def record(
        self,
        context: dict[str, Any],
        symbol: str,
        ts: int,
    ) -> None:
        """Зафиксировать состояние после обработки тика.

        Записывает equity-точку и собирает новые закрытые сделки.
        """
        balance = context.get("backtest_balance", self._initial_balance)
        self._equity_curve.append((ts, balance))
        self._collect_closed_deals(context, symbol)

    def finalize(self, final_balance: float) -> BacktestReport:
        """Вычислить итоговые метрики и вернуть отчёт.

        Args:
            final_balance: Итоговый баланс после прогона.
        """
        pnl_list = self._compute_pnl_list()
        total_trades = len(pnl_list)
        winning = [p for p in pnl_list if p > 0]
        losing = [p for p in pnl_list if p <= 0]
        total_pnl = sum(pnl_list)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
        winrate = (len(winning) / total_trades * 100) if total_trades > 0 else 0.0
        max_dd = self._compute_max_drawdown()
        return_pct = (
            (final_balance - self._initial_balance) / self._initial_balance * 100
            if self._initial_balance > 0
            else 0.0
        )
        return BacktestReport(
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            winrate_pct=winrate,
            total_pnl=total_pnl,
            avg_pnl_per_trade=avg_pnl,
            max_drawdown=max_dd,
            final_balance=final_balance,
            initial_balance=self._initial_balance,
            return_pct=return_pct,
            equity_curve=list(self._equity_curve),
        )

    # ------------------------------------------------------------------
    # Приватные методы
    # ------------------------------------------------------------------

    def _collect_closed_deals(
        self,
        context: dict[str, Any],
        symbol: str,
    ) -> None:
        """Добавить новые закрытые сделки в список."""
        deals: list[Deal] = (context.get("deals") or {}).get(symbol) or []
        for deal in deals:
            if deal.is_closed():
                # Используем object id как уникальный идентификатор
                oid = id(deal)
                if oid not in self._seen_deal_ids:
                    self._seen_deal_ids.add(oid)
                    self._closed_deals.append(deal)

    def _compute_pnl_list(self) -> list[float]:
        """Вычислить список PnL по каждой закрытой сделке."""
        result: list[float] = []
        for deal in self._closed_deals:
            pnl = deal.calculate_actual_profit()
            if pnl is not None:
                result.append(pnl)
        return result

    def _compute_max_drawdown(self) -> float:
        """Рассчитать максимальную просадку по equity-кривой."""
        if not self._equity_curve:
            return 0.0
        peak = self._equity_curve[0][1]
        max_dd = 0.0
        for _, equity in self._equity_curve:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_dd:
                max_dd = drawdown
        return max_dd


__all__ = ["MetricsCollector", "BacktestReport"]
