from __future__ import annotations

"""Доменный источник тиков поверх биржевого коннектора.

В отличие от синхронного генератора ``market_data.ticker_source.generate_ticks``,
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

    Структура основана на контракте ``fetch_ticker()`` из
    ``doc/ccxt_data_structures.md``. Мы фиксируем подмножество полей,
    достаточное для расчёта индикаторов и фильтров ликвидности.

    Обязательные поля:

    * ``symbol`` – строковый символ пары, например ``"BTC/USDT"``;
    * ``timestamp`` – Unix‑время в миллисекундах;
    * ``datetime`` – ISO‑строка, соответствующая ``timestamp``;
    * ``last`` – последняя цена сделки (используется как текущая цена);
    * ``open`` / ``high`` / ``low`` / ``close`` – цены суточной статистики;
    * ``bid`` / ``ask`` – лучшие цены покупателя/продавца;
    * ``baseVolume`` / ``quoteVolume`` – объёмы базовой и котируемой валют.

    При необходимости дополнительные поля CCXT‑тикера (``vwap``,
    ``percentage``, ``change``, ``average`` и т.п.) могут быть добавлены
    в этот TypedDict без изменения базового контракта домена.
    """

    symbol: str
    timestamp: int
    datetime: str

    last: float
    open: float
    high: float
    low: float
    close: float

    bid: float
    ask: float

    baseVolume: float
    quoteVolume: float


class TickSource:
    """Обёртка над :class:`IExchangeConnector` для одной валютной пары.

    В реальной реализации сюда можно добавить:

    * логирование на каждую стадию получения тика;
    * генерацию внутреннего ``ticker_id``;
    * graceful‑shutdown через внешние сигналы отмены.
    """

    def __init__(self, connector: IExchangeConnector, symbol: str) -> None:
        self._connector = connector
        self._symbol = symbol

    async def stream(self) -> AsyncIterator[Ticker]:
        """Асинхронно итерироваться по унифицированным CCXT‑тикерам.

        Ожидается, что коннектор возвращает структуру, совместимую с
        ``fetch_ticker()`` (см. ``doc/ccxt_data_structures.md``), как
        минимум с полями:

        * ``symbol``, ``timestamp``, ``datetime``;
        * ``last``, ``open``, ``high``, ``low``, ``close``;
        * ``bid``, ``ask``, ``baseVolume``, ``quoteVolume``.

        Здесь мы лишь жёстко приводим типы и фиксируем контракт через
        :class:`Ticker`.
        """

        async for raw in self._connector.stream_ticks(self._symbol):
            yield Ticker(
                symbol=str(raw["symbol"]),
                timestamp=int(raw["timestamp"]),
                datetime=str(raw["datetime"]),
                last=float(raw["last"]),
                open=float(raw["open"]),
                high=float(raw["high"]),
                low=float(raw["low"]),
                close=float(raw["close"]),
                bid=float(raw["bid"]),
                ask=float(raw["ask"]),
                baseVolume=float(raw["baseVolume"]),
                quoteVolume=float(raw["quoteVolume"]),
            )


__all__ = ["Ticker", "TickSource"]
