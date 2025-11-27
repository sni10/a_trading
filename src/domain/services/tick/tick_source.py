from __future__ import annotations

"""Доменный источник тиков поверх биржевого коннектора.

В отличие от синхронного генератора ``market_data.tick_source.generate_ticks``,
этот класс работает асинхронно и опирается на абстракцию
``IExchangeConnector``, не зная про ccxt/ccxt.pro.

Он используется как строительный блок для будущего async‑конвейера рынка,
оставаясь при этом полностью изолированным от деталей инфраструктуры.
"""

from collections.abc import AsyncIterator
from typing import TypedDict

from src.infrastructure.connectors.interfaces.exchange_connector import (
    IExchangeConnector,
)


class Tick(TypedDict):
    symbol: str
    price: float
    ts: int  # unix‑timestamp в миллисекундах


class TickSource:
    """Обёртка над :class:`IExchangeConnector` для одной валютной пары.

    В реальной реализации сюда можно добавить:

    * логирование на каждую стадию получения тика;
    * генерацию внутреннего ``tick_id``;
    * graceful‑shutdown через внешние сигналы отмены.
    """

    def __init__(self, connector: IExchangeConnector, symbol: str) -> None:
        self._connector = connector
        self._symbol = symbol

    async def stream(self) -> AsyncIterator[Tick]:
        """Асинхронно итерироваться по унифицированным тикам.

        Коннектор уже возвращает структуру ``{"symbol", "price", "ts"}``,
        но через ``Tick`` мы дополнительно фиксируем контракт на уровне
        типов домена.
        """

        async for raw in self._connector.stream_ticks(self._symbol):
            yield Tick(
                symbol=str(raw["symbol"]),
                price=float(raw["price"]),
                ts=int(raw["ts"]),
            )


__all__ = ["Tick", "TickSource"]
