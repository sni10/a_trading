from collections import deque
from typing import Any, Deque, Dict

from src.domain.interfaces.cache import IIndicatorStore
from src.domain.services.context.state import record_indicators
from src.domain.services.tick.tick_source import Ticker
from src.infrastructure.logging.logging_setup import log_stage


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
        tick_id: int,
        symbol: str,
        ticker: Ticker,
    ) -> Dict[str, Any]:
        last_price = float(ticker["last"])

        log_stage(
            "IND",
            "Расчёт индикаторов по тикеру",
            tick_id=tick_id,
            symbol=symbol,
            price=last_price,
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

            # FAST: можно обновлять часто, на небольшом окне
            if store.should_update_fast(tick_id) and len(history) >= fast_window:
                indicators["sma_fast_5"] = _sma(list(history)[-fast_window:])

            # MEDIUM: реже и на большем окне
            if store.should_update_medium(tick_id) and len(history) >= medium_window:
                indicators["sma_medium_20"] = _sma(list(history)[-medium_window:])

            # HEAVY: ещё реже и на самом длинном окне
            if store.should_update_heavy(tick_id) and len(history) >= heavy_window:
                indicators["sma_heavy_100"] = _sma(list(history)[-heavy_window:])

            # Простейший быстрый индикатор на основе стакана: спред и mid.
            if store.should_update_fast(tick_id):
                bid = float(ticker["bid"])
                ask = float(ticker["ask"])
                spread = max(0.0, ask - bid)
                mid = (ask + bid) / 2.0 if ask and bid else last_price
                indicators["spread"] = spread
                indicators["mid_price"] = mid

            # Сохраняем «сырые» значения цены в истории слоёв стора, чтобы
            # при необходимости можно было посчитать индикаторы иначе.
            if store.should_update_fast(tick_id):
                store.fast_history.append(last_price)  # type: ignore[attr-defined]
            if store.should_update_medium(tick_id):
                store.medium_history.append(last_price)  # type: ignore[attr-defined]
            if store.should_update_heavy(tick_id):
                store.heavy_history.append(last_price)  # type: ignore[attr-defined]

        # --- Базовые поля snapshot (обратная совместимость) ---
        ts = context.get("market", {}).get(symbol, {}).get("ts")

        # Поля "sma" и "rsi" пока оставляем как простые заглушки, чтобы
        # не ломать ожидания демо‑конвейера и README.
        sma_placeholder = float(last_price)
        rsi_placeholder = 50.0

        snapshot: Dict[str, Any] = {
            "symbol": symbol,
            "tick_id": tick_id,
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

        log_stage(
            "IND",
            "Снимок индикаторов сформирован",
            tick_id=tick_id,
            symbol=symbol,
            sma=snapshot["sma"],
            has_fast="sma_fast_5" in snapshot,
            has_medium="sma_medium_20" in snapshot,
            has_heavy="sma_heavy_100" in snapshot,
        )
        return snapshot


_ENGINE = IndicatorEngine()


def compute_indicators(
    context: Dict[str, Any], *, tick_id: int, symbol: str, price: float
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
        tick_id=tick_id,
        symbol=symbol,
        ticker=ticker,
    )

