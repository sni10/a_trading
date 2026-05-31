from __future__ import annotations

"""Сервис оценки индикаторов и формирования торгового сигнала."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class IndicatorSignal:
    """Результат оценки индикаторов для торгового решения."""

    is_bullish: bool
    confidence: float
    score: float
    reason: str
    details: Dict[str, float]


class IndicatorSignalService:
    """Построение торгового сигнала на основе индикаторного снапшота."""

    def __init__(
        self,
        *,
        min_confidence: float = 0.6,
    ) -> None:
        self._min_confidence = min_confidence

    def evaluate(self, indicators: Dict[str, Any]) -> IndicatorSignal:
        """Оценить индикаторы и вернуть итоговый bullish/hold сигнал."""

        details: Dict[str, float] = {}

        macd = indicators.get("macd")
        macd_signal = indicators.get("macdsignal")
        macd_hist = indicators.get("macdhist")
        sma_7 = indicators.get("sma_7")
        sma_25 = indicators.get("sma_25")

        if macd is None or macd_signal is None or macd_hist is None or sma_7 is None or sma_25 is None:
            return IndicatorSignal(
                is_bullish=False,
                confidence=0.0,
                score=0.0,
                reason="insufficient_indicators",
                details=details,
            )

        macd_val = float(macd)
        signal_val = float(macd_signal)
        hist_val = float(macd_hist)
        sma_fast = float(sma_7)
        sma_slow = float(sma_25)

        details["macd"] = macd_val
        details["macdsignal"] = signal_val
        details["macdhist"] = hist_val
        details["sma_7"] = sma_fast
        details["sma_25"] = sma_slow

        macd_bullish = macd_val > signal_val and hist_val > 0.0
        sma_bullish = sma_fast > sma_slow if sma_slow > 0 else False
        is_bullish = macd_bullish and sma_bullish

        score = (int(macd_bullish) + int(sma_bullish)) / 2.0
        reason = "growth_signal" if is_bullish else "no_growth_signal"
        confidence = 0.0
        if is_bullish:
            strength = indicators.get("signal_strength")
            if strength is not None:
                try:
                    confidence = min(1.0, float(strength) / 100.0)
                except (TypeError, ValueError):
                    confidence = self._min_confidence
            else:
                confidence = self._min_confidence

        return IndicatorSignal(
            is_bullish=is_bullish,
            confidence=round(confidence, 2),
            score=score,
            reason=reason,
            details=details,
        )


__all__ = ["IndicatorSignal", "IndicatorSignalService"]
