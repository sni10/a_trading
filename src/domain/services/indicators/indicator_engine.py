from collections import deque
from typing import Any, Deque, Dict

from src.domain.interfaces.cache import IIndicatorStore
from src.domain.services.context.state import record_indicators
from src.domain.services.ticker.ticker_source import Ticker
from src.infrastructure.logging.logging_setup import log_stage, log_info

# Имя логгера для этого модуля
_LOG = __name__

try:  # pragma: no cover - окружения без numpy/talib
    import numpy as _np  # type: ignore[import]
    import talib as _talib  # type: ignore[import]
except Exception:  # pragma: no cover - защитный импорт
    _np = None  # type: ignore[assignment]
    _talib = None  # type: ignore[assignment]


def _sma(values: list[float]) -> float:
    """Простейшая скользящая средняя по списку значений.

    Предполагается, что ``values`` не пустой (контролируется вызывающим
    кодом через длину history).
    """

    return sum(values) / len(values)


class IndicatorEngine:
    """Поставщик индикаторов поверх истории тикеров.

    Работает в терминах доменного :class:`Ticker` и трёх слоёв
    триггеров ``fast/medium/heavy`` через :class:`IIndicatorStore`.

    Основная точка входа – метод :meth:`on_ticker`, который:

    * обновляет историю цен ``context["price_history"][symbol]``;
    * по триггерам считает простые SMA и дополнительные fast‑индикаторы;
    * сохраняет снимок через :func:`record_indicators` и возвращает его.
    """

    def on_ticker(
        self,
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
        ticker: Ticker,
    ) -> Dict[str, Any]:
        last_price = float(ticker["last"])

        log_info(
            f"📊 [IND] Расчёт индикаторов по тикеру | ticker_id: {ticker_id} | symbol: {symbol} | price: {last_price:.8f}",
            _LOG
        )

        # --- История цен по инструменту (общая для всех индикаторов) ---
        price_history_root: Dict[str, Deque[float]] = context.setdefault(
            "price_history", {}
        )
        history: Deque[float] = price_history_root.setdefault(
            symbol, deque(maxlen=500)
        )
        history.append(last_price)

        # Также храним историю тикеров – на будущее для объёмных и
        # спред‑зависимых индикаторов.
        ticker_history_root: Dict[str, Deque[Ticker]] = context.setdefault(
            "ticker_history", {}
        )
        ticker_hist: Deque[Ticker] = ticker_history_root.setdefault(
            symbol, deque(maxlen=500)
        )
        ticker_hist.append(ticker)

        # --- Достаём IndicatorStore для символа (если настроен) ---
        stores = context.get("indicator_stores") or {}
        store = stores.get(symbol)

        indicators: Dict[str, Any] = {}

        if isinstance(store, IIndicatorStore):
            # Окна для примера fast/medium/heavy. В дальнейшем можно
            # вынести в конфиг/пару, не меняя общий каркас.
            fast_window = 5
            medium_window = 20
            heavy_window = 100

            history_list = list(history)
            n = len(history_list)

            # --- FAST слой ---
            if store.should_update_fast(ticker_id):
                # Исторический демо‑индикатор: SMA по 5 последним тикам.
                if n >= fast_window:
                    indicators["sma_fast_5"] = _sma(history_list[-fast_window:])

                # Реальные быстрые индикаторы из старого проекта:
                # SMA‑7 и SMA‑25 по истории цен (см.
                # bad_example/src/domain/services/indicators/indicator_calculator_service.py).
                if n >= 1:
                    sma_7_window = history_list[-7:]
                    indicators["sma_7"] = _sma(sma_7_window)

                if n >= 25:
                    sma_25_window = history_list[-25:]
                    indicators["sma_25"] = _sma(sma_25_window)

                # Простейший быстрый индикатор на основе стакана: спред и mid.
                bid = float(ticker["bid"])
                ask = float(ticker["ask"])
                spread = max(0.0, ask - bid)
                mid = (ask + bid) / 2.0 if ask and bid else last_price
                indicators["spread"] = spread
                indicators["mid_price"] = mid

                # Сохраняем «сырые» значения цены в истории fast‑слоя.
                store.fast_history.append(last_price)  # type: ignore[attr-defined]

            # --- MEDIUM слой ---
            if store.should_update_medium(ticker_id):
                # Демонстрационная SMA по 20 последним тикам.
                if n >= medium_window:
                    indicators["sma_medium_20"] = _sma(
                        history_list[-medium_window:]
                    )

                # Средние индикаторы из старого проекта: RSI‑5 и RSI‑15.
                # Формулы основаны на IndicatorCalculatorService, но
                # используют необязательный talib, если он доступен.
                if _np is not None and _talib is not None and n >= 30:
                    closes = _np.array(history_list[-30:], dtype="float64")  # type: ignore[arg-type]
                    try:
                        rsi_5 = _talib.RSI(closes, timeperiod=5)  # type: ignore[call-arg]
                        rsi_15 = _talib.RSI(closes, timeperiod=15)  # type: ignore[call-arg]

                        if len(rsi_5) > 0 and not _np.isnan(rsi_5[-1]):
                            indicators["rsi_5"] = round(float(rsi_5[-1]), 8)
                        if len(rsi_15) > 0 and not _np.isnan(rsi_15[-1]):
                            indicators["rsi_15"] = round(float(rsi_15[-1]), 8)
                    except Exception as exc:  # pragma: no cover - защитный путь
                        log_info(
                            f"⚠️ [WARN] Ошибка при расчёте RSI через ta-lib | error: {exc}",
                            _LOG
                        )

                # История medium‑слоя для возможных альтернативных
                # расчётов в будущем.
                store.medium_history.append(last_price)  # type: ignore[attr-defined]

            # --- HEAVY слой ---
            if store.should_update_heavy(ticker_id):
                # Демонстрационная SMA по 100 последним тикам.
                if n >= heavy_window:
                    indicators["sma_heavy_100"] = _sma(
                        history_list[-heavy_window:]
                    )

                # Тяжёлые индикаторы из старого проекта: MACD и Bollinger Bands.
                if _np is not None and _talib is not None and n >= 50:
                    closes = _np.array(history_list[-100:], dtype="float64")  # type: ignore[arg-type]
                    try:
                        macd, macdsignal, macdhist = _talib.MACD(  # type: ignore[call-arg]
                            closes,
                            fastperiod=12,
                            slowperiod=26,
                            signalperiod=9,
                        )
                        upperband, middleband, lowerband = _talib.BBANDS(  # type: ignore[call-arg]
                            closes,
                            timeperiod=20,
                            nbdevup=2,
                            nbdevdn=2,
                        )

                        macd_val = float(macd[-1]) if len(macd) > 0 and not _np.isnan(macd[-1]) else 0.0
                        signal_val = (
                            float(macdsignal[-1])
                            if len(macdsignal) > 0 and not _np.isnan(macdsignal[-1])
                            else 0.0
                        )
                        hist_val = (
                            float(macdhist[-1])
                            if len(macdhist) > 0 and not _np.isnan(macdhist[-1])
                            else 0.0
                        )

                        # Signal strength (0-100 scale based on MACD divergence)
                        signal_strength = (
                            min(100.0, abs(macd_val - signal_val) * 10000.0)
                            if signal_val != 0.0
                            else 0.0
                        )

                        # Trend signal (-1 bearish, 0 neutral, 1 bullish)
                        trend_signal = 1 if macd_val > signal_val and hist_val > 0 else (
                            -1 if macd_val < signal_val and hist_val < 0 else 0
                        )

                        indicators["macd"] = round(macd_val, 8)
                        indicators["macdsignal"] = round(signal_val, 8)
                        indicators["macdhist"] = round(hist_val, 8)

                        if len(upperband) > 0 and not _np.isnan(upperband[-1]):
                            indicators["bb_upper"] = round(float(upperband[-1]), 8)
                        if len(middleband) > 0 and not _np.isnan(middleband[-1]):
                            indicators["bb_middle"] = round(
                                float(middleband[-1]), 8
                            )
                        if len(lowerband) > 0 and not _np.isnan(lowerband[-1]):
                            indicators["bb_lower"] = round(float(lowerband[-1]), 8)

                        indicators["signal_strength"] = round(signal_strength, 2)
                        indicators["trend_signal"] = trend_signal
                    except Exception as exc:  # pragma: no cover - защитный путь
                        log_info(
                            f"⚠️ [WARN] Ошибка при расчёте MACD/BBands через ta-lib | error: {exc}",
                            _LOG
                        )

                # История heavy‑слоя.
                store.heavy_history.append(last_price)  # type: ignore[attr-defined]

        # --- Базовые поля snapshot (обратная совместимость) ---
        ts = context.get("market", {}).get(symbol, {}).get("ts")

        # Поля "sma" и "rsi" поддерживаем для обратной совместимости:
        # если доступны реальные индикаторы, используем их, иначе
        # остаёмся на простых заглушках.
        sma_placeholder = float(last_price)
        if "sma_7" in indicators:
            sma_placeholder = float(indicators["sma_7"])

        rsi_placeholder = 50.0
        if "rsi_5" in indicators:
            rsi_placeholder = float(indicators["rsi_5"])

        snapshot: Dict[str, Any] = {
            "symbol": symbol,
            "ticker_id": ticker_id,
            "price": float(last_price),
            "sma": sma_placeholder,
            "rsi": rsi_placeholder,
            "ts": ts,
            **indicators,
        }

        # Сохраняем снимок в общем контексте и его историю, чтобы потом
        # можно было заменить in‑memory стор на Redis/БД без правки
        # вызывающего кода.
        record_indicators(context, symbol=symbol, snapshot=snapshot)

        has_fast = "sma_fast_5" in snapshot
        has_medium = "sma_medium_20" in snapshot
        has_heavy = "sma_heavy_100" in snapshot
        log_info(
            f"📊 [IND] Снимок индикаторов сформирован | ticker_id: {ticker_id} | symbol: {symbol} | "
            f"sma: {snapshot['sma']:.8f} | has_fast: {has_fast} | has_medium: {has_medium} | has_heavy: {has_heavy}",
            _LOG
        )
        return snapshot


_ENGINE = IndicatorEngine()


def compute_indicators(
    context: Dict[str, Any], *, ticker_id: int, symbol: str, price: float
) -> Dict[str, Any]:
    """Фасад для расчёта индикаторов, совместимый с существующим API.

    Внешний контракт (сигнатура и базовый формат snapshot) не меняется,
    но фактическая работа делегирована :class:`IndicatorEngine`, который
    оперирует доменным :class:`Ticker`.

    Для синхронного демо‑конвейера мы строим упрощённый тикер поверх
    текущей цены: все OHLC‑поля приравниваются к ``price``, bid/ask – к
    ``price``, объёмы – к нулю. В async‑конвейере вместо этого будет
    использоваться реальный тикер из :class:`TickSource`.
    """

    ts = context.get("market", {}).get(symbol, {}).get("ts")

    # Упрощённый тикер: один и тот же price во всех ценовых полях,
    # объёмы считаем неизвестными (0.0). Этого достаточно для текущих
    # SMA и демонстрационных индикаторов.
    ticker: Ticker = {
        "symbol": symbol,
        "timestamp": int(ts) if ts is not None else 0,
        "datetime": "",
        "last": float(price),
        "open": float(price),
        "high": float(price),
        "low": float(price),
        "close": float(price),
        "bid": float(price),
        "ask": float(price),
        "baseVolume": 0.0,
        "quoteVolume": 0.0,
    }

    return _ENGINE.on_ticker(
        context,
        ticker_id=ticker_id,
        symbol=symbol,
        ticker=ticker,
    )

