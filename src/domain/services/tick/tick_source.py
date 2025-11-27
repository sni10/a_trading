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
class Ticker(TypedDict):
    """Доменный тикер в формате CCXT ``fetch_ticker()``.

    Мы используем минимальный поднабор полей из структуры
    ``fetch_ticker()`` (см. ``doc/ccxt_data_structures.md``):

    * ``symbol`` – строковый символ пары, например ``"BTC/USDT"``;
    * ``last`` – последняя цена сделки;
    * ``timestamp`` – Unix‑время в миллисекундах;
    * ``datetime`` – ISO‑строка, соответствующая ``timestamp``.

    Остальные поля CCXT‑тикера (``high``, ``low``, ``bid`` и т.п.)
    на этом этапе не требуются домену и могут быть добавлены позже
    без изменения базового контракта.
    """

    symbol: str
    last: float
    timestamp: int
    datetime: str


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

    async def stream(self) -> AsyncIterator[Ticker]:
        """Асинхронно итерироваться по унифицированным CCXT‑тикерам.

        Ожидается, что коннектор возвращает структуру, совместимую с
        ``fetch_ticker()`` (см. ``doc/ccxt_data_structures.md``), как
        минимум с полями ``symbol``, ``last``, ``timestamp``, ``datetime``.

        Здесь мы лишь жёстко приводим типы и фиксируем контракт через
        :class:`Ticker`.
        """

        async for raw in self._connector.stream_ticks(self._symbol):
            yield Ticker(
                symbol=str(raw["symbol"]),
                last=float(raw["last"]),
                timestamp=int(raw["timestamp"]),
                datetime=str(raw["datetime"]),
            )


__all__ = ["Ticker", "TickSource"]
