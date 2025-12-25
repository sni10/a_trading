from __future__ import annotations

"""Анализ стакана заявок и получение рыночного сигнала."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class OrderBookSignal(str, Enum):
    """Тип сигнала по стакану."""

    STRONG_BUY = "STRONG_BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    STRONG_SELL = "STRONG_SELL"
    REJECT = "REJECT"


@dataclass(frozen=True)
class OrderBookMetrics:
    """Метрики стакана и итоговый сигнал."""

    bid_ask_spread: float
    volume_imbalance: float
    liquidity_depth: float
    slippage_buy: float
    slippage_sell: float
    support_level: float | None
    resistance_level: float | None
    signal: OrderBookSignal
    confidence: float


class OrderBookAnalyzer:
    """Анализирует стакан и формирует сигнал для BUY/HOLD."""

    def __init__(
        self,
        *,
        max_levels: int = 10,
        max_spread_pct: float = 0.35,
        max_slippage_pct: float = 0.6,
        min_liquidity: float = 5.0,
        strong_imbalance: float = 20.0,
        weak_imbalance: float = 5.0,
    ) -> None:
        self._max_levels = max_levels
        self._max_spread_pct = max_spread_pct
        self._max_slippage_pct = max_slippage_pct
        self._min_liquidity = min_liquidity
        self._strong_imbalance = strong_imbalance
        self._weak_imbalance = weak_imbalance

    def analyze(self, order_book: dict[str, Any]) -> OrderBookMetrics | None:
        """Вернуть метрики и сигнал по стакану или None, если данных нет."""

        bids = order_book.get("bids")
        asks = order_book.get("asks")
        if not isinstance(bids, list) or not isinstance(asks, list):
            return None
        if not bids or not asks:
            return None

        bids = bids[: self._max_levels]
        asks = asks[: self._max_levels]

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        if best_bid <= 0 or best_ask <= 0:
            return None

        mid = (best_bid + best_ask) / 2.0
        spread_pct = ((best_ask - best_bid) / mid) * 100.0 if mid else 0.0

        bid_vol = _sum_volume(bids)
        ask_vol = _sum_volume(asks)
        total_vol = bid_vol + ask_vol
        volume_imbalance = ((bid_vol - ask_vol) / total_vol) * 100.0 if total_vol else 0.0

        liquidity_depth = total_vol
        support_level = _max_volume_price(bids)
        resistance_level = _max_volume_price(asks)

        avg_ask = _weighted_avg_price(asks)
        avg_bid = _weighted_avg_price(bids)
        slippage_buy = ((avg_ask - best_ask) / best_ask) * 100.0 if best_ask else 0.0
        slippage_sell = ((best_bid - avg_bid) / best_bid) * 100.0 if best_bid else 0.0

        signal = self._classify_signal(
            spread_pct=spread_pct,
            slippage_buy=slippage_buy,
            slippage_sell=slippage_sell,
            liquidity_depth=liquidity_depth,
            volume_imbalance=volume_imbalance,
        )
        confidence = self._estimate_confidence(volume_imbalance, spread_pct, signal)

        return OrderBookMetrics(
            bid_ask_spread=round(spread_pct, 4),
            volume_imbalance=round(volume_imbalance, 2),
            liquidity_depth=round(liquidity_depth, 2),
            slippage_buy=round(slippage_buy, 3),
            slippage_sell=round(slippage_sell, 3),
            support_level=support_level,
            resistance_level=resistance_level,
            signal=signal,
            confidence=confidence,
        )

    def _classify_signal(
        self,
        *,
        spread_pct: float,
        slippage_buy: float,
        slippage_sell: float,
        liquidity_depth: float,
        volume_imbalance: float,
    ) -> OrderBookSignal:
        if (
            spread_pct > self._max_spread_pct
            or slippage_buy > self._max_slippage_pct
            or slippage_sell > self._max_slippage_pct
            or liquidity_depth < self._min_liquidity
        ):
            return OrderBookSignal.REJECT

        if volume_imbalance >= self._strong_imbalance:
            return OrderBookSignal.STRONG_BUY
        if volume_imbalance >= self._weak_imbalance:
            return OrderBookSignal.WEAK_BUY
        if volume_imbalance <= -self._strong_imbalance:
            return OrderBookSignal.STRONG_SELL
        if volume_imbalance <= -self._weak_imbalance:
            return OrderBookSignal.WEAK_SELL
        return OrderBookSignal.NEUTRAL

    def _estimate_confidence(
        self,
        volume_imbalance: float,
        spread_pct: float,
        signal: OrderBookSignal,
    ) -> float:
        if signal == OrderBookSignal.REJECT:
            return 0.0

        imbalance_strength = min(1.0, abs(volume_imbalance) / self._strong_imbalance)
        spread_penalty = min(1.0, spread_pct / self._max_spread_pct) if self._max_spread_pct else 0.0
        confidence = max(0.0, imbalance_strength * (1.0 - 0.5 * spread_penalty))
        return round(confidence, 2)


def _sum_volume(levels: Iterable[list[float]]) -> float:
    return sum(float(level[1]) for level in levels if len(level) >= 2)


def _weighted_avg_price(levels: Iterable[list[float]]) -> float:
    total = 0.0
    weighted = 0.0
    for level in levels:
        if len(level) < 2:
            continue
        price = float(level[0])
        volume = float(level[1])
        total += volume
        weighted += price * volume
    if total == 0:
        return float(levels[0][0]) if isinstance(levels, list) and levels else 0.0
    return weighted / total


def _max_volume_price(levels: Iterable[list[float]]) -> float | None:
    max_volume = 0.0
    price_at_max = None
    for level in levels:
        if len(level) < 2:
            continue
        price = float(level[0])
        volume = float(level[1])
        if volume > max_volume:
            max_volume = volume
            price_at_max = price
    return price_at_max


__all__ = ["OrderBookAnalyzer", "OrderBookMetrics", "OrderBookSignal"]
