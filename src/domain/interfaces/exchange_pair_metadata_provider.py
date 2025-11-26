"""Интерфейс провайдера биржевых прецизионов для валютной пары.

На этом этапе нам нужен минимальный контракт, который:

* даёт шаг количества (``min_step``) и цены (``price_step``) для символа;
* легко мокается в тестах простым классом/объектом;
* в будущем может быть реализован поверх реального объекта биржи
  (ccxt/ccxt.pro), который читает данные из ``exchange.markets[symbol]``.

Важно: бизнес‑код не знает о конкретной бирже или ccxt, он зависит только
от этого интерфейса. Тем самым CurrencyPair может всегда получать актуальные
прецизионы из внешнего провайдера, в том числе перекрывая значения из БД.
"""

from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


class PairPrecisions(TypedDict):
    """Структура с прецизионами для валютной пары.

    * ``min_step`` – минимальный шаг количества (lot size step);
    * ``price_step`` – минимальный шаг цены (tick size).
    """

    min_step: float
    price_step: float


@runtime_checkable
class IExchangePairMetadataProvider(Protocol):
    """Провайдер биржевых прецизионов для пары.

    Реализация может брать данные откуда угодно:

    * из замоканного объекта биржи в юнит‑тестах;
    * из ccxt ``exchange.markets[symbol]``;
    * из кэша/БД, синхронизированного с биржей.
    """

    def get_precisions(self, symbol: str) -> PairPrecisions | None:
        """Вернуть прецизионы для заданного символа.

        Если символ биржа не поддерживает или данные недоступны,
        можно вернуть ``None`` – в этом случае будут использоваться
        значения по умолчанию/из БД.
        """


__all__ = ["PairPrecisions", "IExchangePairMetadataProvider"]
