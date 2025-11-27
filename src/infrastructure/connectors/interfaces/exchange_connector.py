from __future__ import annotations

"""Интерфейс биржевого коннектора.

Доменный код видит только этот протокол и **не знает** про ccxt/ccxt.pro.

Контракты методов согласованы с планом в
``doc/implements_plans/2025-11-connector_and_market_pipeline_examples_plan.md``:

* ``stream_ticks`` – асинхронный поток тиков унифицированного формата
  ``{"symbol", "price", "ts"}``;
* ``fetch_order_book`` – единый снепшот стакана с полями ``bids``,
  ``asks``, ``symbol``, ``timestamp``, ``datetime``, ``nonce``.

Реальные реализации (ccxt.pro и т.п.) живут в слое ``infrastructure`` и
обязаны приводить данные к этим структурам.
"""

from collections.abc import AsyncIterator
from typing import Protocol, TypedDict


class UnifiedTicker(TypedDict):
    """Унифицированный тик, возвращаемый биржевым коннектором.

    Используется во всех реализациях :class:`IExchangeConnector`.
    """

    symbol: str
    price: float
    ts: int  # unix‑timestamp в миллисекундах


class IExchangeConnector(Protocol):
    async def stream_ticks(self, symbol: str) -> AsyncIterator[UnifiedTicker]:
        """Асинхронный поток тиков вида ``{"symbol", "price", "ts"}``.

        Контракт одного тика (минимум):

        .. code-block:: python

            tick = {
                "symbol": str,   # "BTC/USDT"
                "price": float,  # last price
                "ts": int,       # unix‑timestamp в миллисекундах
            }
        """

    async def fetch_order_book(self, symbol: str) -> dict:
        """Вернуть снепшот стакана в унифицированном формате.

        Формат результата совместим с примерами ``fetch_order_book`` из
        ``doc/ccxt_data_structures.md``:

        .. code-block:: python

            order_book = {
                "bids": list[list[float, float]],  # [[price, amount], ...]
                "asks": list[list[float, float]],
                "symbol": str,
                "timestamp": int,
                "datetime": str,
                "nonce": int | None,
            }
        """


__all__ = ["IExchangeConnector", "UnifiedTicker"]
