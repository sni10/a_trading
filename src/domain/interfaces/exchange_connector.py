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

    async def fetch_balance(self) -> dict:
        """Запросить балансы всех валют на аккаунте.

        Формат результата совместим с CCXT ``fetch_balance()``:

        .. code-block:: python

            balance = {
                "BTC": {"free": 1.5, "used": 0.0, "total": 1.5},
                "USDT": {"free": 10000.0, "used": 500.0, "total": 10500.0},
                ...
            }
        """

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict | None = None,
    ) -> dict:
        """Создать ордер на бирже.

        Args:
            symbol: Торговая пара (например 'BTC/USDT')
            order_type: Тип ордера ('limit', 'market')
            side: Сторона ('buy', 'sell')
            amount: Количество базовой валюты
            price: Цена (для limit ордеров)
            params: Дополнительные параметры (clientOrderId и т.д.)

        Returns:
            CCXT Order Structure (см. Order.from_ccxt())
        """

    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        """Отменить ордер на бирже.

        Args:
            order_id: ID ордера на бирже
            symbol: Торговая пара

        Returns:
            CCXT Order Structure отменённого ордера
        """

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        """Запросить текущий статус ордера с биржи.

        Args:
            order_id: ID ордера на бирже
            symbol: Торговая пара

        Returns:
            CCXT Order Structure
        """


__all__ = ["IExchangeConnector"]
