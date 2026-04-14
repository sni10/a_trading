from __future__ import annotations

"""Интерфейс биржевого коннектора.

Доменный код видит только этот протокол и **не знает** про ccxt/ccxt.pro.

Контракты методов согласованы с планом в
``doc/implements_plans/2025-11-connector_and_market_pipeline_examples_plan.md``
и с примерами структур из ``doc/ccxt_data_structures.md``:

* ``stream_ticks`` – асинхронный поток тикеров в формате CCXT
  ``fetch_ticker()`` (минимум поля ``symbol``, ``last``, ``timestamp``,
  ``datetime``);
* ``fetch_order_book`` – единый снепшот стакана с полями ``bids``,
  ``asks``, ``symbol``, ``timestamp``, ``datetime``, ``nonce``.

Реальные реализации (ccxt.pro и т.п.) живут в слое ``infrastructure`` и
обязаны приводить данные к этим структурам.
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IExchangeConnector(Protocol):
    async def stream_ticks(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        """Асинхронный поток тикеров, совместимых с CCXT ``fetch_ticker()``.

        Минимальный контракт одного тикера (см.
        ``doc/ccxt_data_structures.md``, раздел ``fetch_ticker()``):

        .. code-block:: python

            ticker = {
                "symbol": str,      # "BTC/USDT"
                "last": float,      # последняя цена сделки
                "timestamp": int,   # unix‑timestamp в миллисекундах
                "datetime": str,    # ISO‑строка, соответствующая timestamp
                # остальные поля CCXT-тикера могут присутствовать, но не
                # обязательны для минимального контракта домена
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

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Разместить ордер на бирже.

        Возвращает сырой CCXT-ответ (unified order structure) в виде dict.
        Парсинг в доменную сущность выполняется на стороне домена.

        Args:
            symbol: Торговая пара, например ``"BTC/USDT"``
            order_type: Тип ордера: ``"limit"`` или ``"market"``
            side: Сторона: ``"buy"`` или ``"sell"``
            amount: Объём в базовой валюте
            price: Цена (обязательна для limit, None для market)
            params: Дополнительные параметры биржи

        Returns:
            dict — сырой CCXT unified order dict
        """
        ...

    async def stream_orders(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        """Асинхронный поток обновлений ордеров (``watch_orders``).

        Каждый элемент — сырой CCXT unified order dict с как минимум
        полями ``id``, ``symbol``, ``status``, ``timestamp``.
        """
        ...

    async def stream_my_trades(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        """Асинхронный поток пользовательских трейдов (``watch_my_trades``).

        Каждый элемент — сырой CCXT unified trade dict с как минимум
        полями ``id``, ``order``, ``symbol``, ``side``, ``amount``,
        ``price``, ``cost``, ``timestamp``.
        """
        ...


__all__ = ["IExchangeConnector"]
