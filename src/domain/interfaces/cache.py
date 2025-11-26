"""Интерфейсы (протоколы) для кэшей рыночных данных и индикаторов.

На этом этапе нужны только самые базовые методы, чтобы:

* зафиксировать форму API под будущие реализации (Redis и т.п.);
* иметь in-memory реализацию, завязанную на CurrencyPair и AppConfig;
* не тянуть детали ccxt внутрь домена – только простые dict‑структуры,
  совместимые с примерами в doc/ccxt_data_structures.md и
  doc/EXCHANGE_INTEGRATION.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class IMarketCache(Protocol):
    """Кэш hot‑данных рынка для одной пары.

    Оперирует унифицированными dict‑структурами уровня ccxt:

    * ticker – см. `fetch_ticker()` в doc/ccxt_data_structures.md;
    * orderbook – см. `fetch_order_book()`;
    * trades – список сделок в формате ccxt.
    """

    symbol: str

    # --- Ticker ---
    def update_ticker(self, ticker: Dict[str, Any]) -> None:
        """Обновить последний тикер пары."""

    def get_ticker(self) -> Dict[str, Any] | None:
        """Вернуть последний тикер или None, если его ещё нет."""

    # --- Order book ---
    def update_orderbook(self, orderbook: Dict[str, Any]) -> None:
        """Обновить срез стакана (asks/bids ограничиваются depth пары)."""

    def get_orderbook(self) -> Dict[str, Any] | None:
        """Вернуть последний стакан или None."""

    # --- Trades ---
    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Добавить сделку в историю (ограничено окном пары)."""

    def get_trades(self, limit: int | None = None) -> List[Dict[str, Any]]:
        """Вернуть последние сделки, не более limit (с конца)."""

    # --- Bars / OHLCV ---
    def add_bar(self, bar: Dict[str, Any]) -> None:
        """Добавить бар OHLCV в окно (ограничено bar_window_size)."""

    def get_bars(self, limit: int | None = None) -> List[Dict[str, Any]]:
        """Вернуть последние бары, не более limit (с конца)."""


@runtime_checkable
class IIndicatorStore(Protocol):
    """Кэш значений индикаторов для одной пары.

    Хранит три логических слоя индикаторов (fast/medium/heavy) и знает
    частоту их обновления в тиках. На данном этапе интерфейс сводится к
    решению "нужно ли обновлять" на этом тике – этого достаточно, чтобы
    позже подвязать реальный IndicatorEngine.
    """

    fast_interval: int
    medium_interval: int
    heavy_interval: int

    def should_update_fast(self, tick_id: int) -> bool:
        """Нужно ли обновить быстрые индикаторы на этом тике."""

    def should_update_medium(self, tick_id: int) -> bool:
        """Нужно ли обновить средние индикаторы на этом тике."""

    def should_update_heavy(self, tick_id: int) -> bool:
        """Нужно ли обновить тяжёлые индикаторы на этом тике."""
