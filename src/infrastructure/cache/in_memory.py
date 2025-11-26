"""In-memory реализации кэшей под CurrencyPair + AppConfig.

Для раннего прототипа всё хранится в памяти, но интерфейсы совместимы
с IMarketCache / IIndicatorStore, чтобы позже заменить их на Redis или
другой бекенд без изменения бизнес‑логики.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List

from src.config.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.cache import IIndicatorStore, IMarketCache
from src.infrastructure.logging.logging_setup import log_stage


class InMemoryMarketCache(IMarketCache):
    """Кэш рыночных данных для одной пары.

    Использует размеры окон из CurrencyPair:

    * bar_window_size – длина истории баров;
    * trades_history_size – длина истории трейдов;
    * orderbook_depth – максимальное число уровней стакана на сторону.
    """

    def __init__(self, pair: CurrencyPair):
        self.pair = pair
        self.symbol: str = pair.symbol

        self._ticker: Dict[str, Any] | None = None
        self._orderbook: Dict[str, Any] | None = None
        self._bars: Deque[Dict[str, Any]] = deque(maxlen=pair.bar_window_size)
        self._trades: Deque[Dict[str, Any]] = deque(
            maxlen=pair.trades_history_size
        )

        log_stage(
            "BOOT",
            "Инициализация InMemoryMarketCache",
            symbol=self.symbol,
            bar_window_size=pair.bar_window_size,
            trades_history_size=pair.trades_history_size,
            orderbook_depth=pair.orderbook_depth,
        )

    # --- Ticker ---

    def update_ticker(self, ticker: Dict[str, Any]) -> None:  # type: ignore[override]
        if "symbol" not in ticker:
            ticker = {**ticker, "symbol": self.symbol}
        self._ticker = ticker
        log_stage(
            "FEEDS",
            "Обновлён тикер в InMemoryMarketCache",
            symbol=self.symbol,
            last=ticker.get("last"),
            timestamp=ticker.get("timestamp"),
        )

    def get_ticker(self) -> Dict[str, Any] | None:  # type: ignore[override]
        return self._ticker

    # --- Order book ---

    def update_orderbook(self, orderbook: Dict[str, Any]) -> None:  # type: ignore[override]
        """Сохранить стакан, обрезав списки bids/asks по depth пары."""

        depth = self.pair.orderbook_depth
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        trimmed = {
            **orderbook,
            "symbol": orderbook.get("symbol") or self.symbol,
            "bids": list(bids)[:depth],
            "asks": list(asks)[:depth],
        }
        self._orderbook = trimmed

        log_stage(
            "FEEDS",
            "Стакан обновлён в InMemoryMarketCache",
            symbol=self.symbol,
            bids=len(trimmed["bids"]),
            asks=len(trimmed["asks"]),
            depth=depth,
        )

    def get_orderbook(self) -> Dict[str, Any] | None:  # type: ignore[override]
        return self._orderbook

    # --- Trades ---

    def add_trade(self, trade: Dict[str, Any]) -> None:  # type: ignore[override]
        self._trades.append(trade)
        log_stage(
            "FEEDS",
            "Добавлен трейд в историю InMemoryMarketCache",
            symbol=self.symbol,
            price=trade.get("price"),
            trades_len=len(self._trades),
            window=self.pair.trades_history_size,
        )

    def get_trades(self, limit: int | None = None) -> List[Dict[str, Any]]:  # type: ignore[override]
        items = list(self._trades)
        if limit is None or limit >= len(items):
            return items
        return items[-limit:]

    # --- Bars / OHLCV ---

    def add_bar(self, bar: Dict[str, Any]) -> None:  # type: ignore[override]
        self._bars.append(bar)
        log_stage(
            "FEEDS",
            "Добавлен бар в историю InMemoryMarketCache",
            symbol=self.symbol,
            close=bar.get("close"),
            bars_len=len(self._bars),
            window=self.pair.bar_window_size,
        )

    def get_bars(self, limit: int | None = None) -> List[Dict[str, Any]]:  # type: ignore[override]
        items = list(self._bars)
        if limit is None or limit >= len(items):
            return items
        return items[-limit:]


class InMemoryIndicatorStore(IIndicatorStore):
    """Кэш индикаторов для одной пары.

    Пока хранит только историю "сырых" значений для трёх уровней
    (fast/medium/heavy) и умеет отвечать, нужно ли обновлять индикаторы
    на данном тике, исходя из интервалов в AppConfig.
    """

    def __init__(self, pair: CurrencyPair, config: AppConfig):
        self.pair = pair
        self.config = config

        self.fast_interval: int = config.indicator_fast_interval
        self.medium_interval: int = config.indicator_medium_interval
        self.heavy_interval: int = config.indicator_heavy_interval

        # Храним последние значения индикаторов в отдельных окнах.
        maxlen = pair.indicator_window_size
        self.fast_history: Deque[float] = deque(maxlen=maxlen)
        self.medium_history: Deque[float] = deque(maxlen=maxlen)
        self.heavy_history: Deque[float] = deque(maxlen=maxlen)

        log_stage(
            "BOOT",
            "Инициализация InMemoryIndicatorStore",
            symbol=pair.symbol,
            indicator_window_size=maxlen,
            fast_interval=self.fast_interval,
            medium_interval=self.medium_interval,
            heavy_interval=self.heavy_interval,
        )

    # --- Политика обновления ---

    def _should_update(self, interval: int, tick_id: int) -> bool:
        return interval > 0 and tick_id % interval == 0

    def should_update_fast(self, tick_id: int) -> bool:  # type: ignore[override]
        return self._should_update(self.fast_interval, tick_id)

    def should_update_medium(self, tick_id: int) -> bool:  # type: ignore[override]
        return self._should_update(self.medium_interval, tick_id)

    def should_update_heavy(self, tick_id: int) -> bool:  # type: ignore[override]
        return self._should_update(self.heavy_interval, tick_id)


__all__ = [
    "InMemoryMarketCache",
    "InMemoryIndicatorStore",
]
