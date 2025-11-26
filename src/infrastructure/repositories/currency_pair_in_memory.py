"""In-memory репозиторий валютных пар.

Используется ранним прототипом вместо прямой работы со строковыми
символами. Позже может быть заменён на реализацию поверх БД, не меняя
остальной код конвейера.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.interfaces.exchange_pair_metadata_provider import (
    IExchangePairMetadataProvider,
)


class InMemoryCurrencyPairRepository(ICurrencyPairRepository):
    """Простая in-memory реализация репозитория валютных пар.

    Пары передаются готовыми объектами :class:`CurrencyPair` или
    создаются из списка символов через :meth:`from_symbols`.
    """

    def __init__(
        self,
        pairs: Iterable[CurrencyPair],
        precision_provider: IExchangePairMetadataProvider | None = None,
    ):
        """Создать репозиторий из готовых объектов :class:`CurrencyPair`.

        Если передан ``precision_provider``, то для каждой пары будут
        запрошены актуальные прецизионы у провайдера и поля
        :attr:`CurrencyPair.min_step` и :attr:`CurrencyPair.price_step`
        будут **перезаписаны**, даже если у объекта уже были значения
        (например, он пришёл из БД).
        """

        pairs_list: List[CurrencyPair] = list(pairs)
        index: Dict[str, CurrencyPair] = {}

        for pair in pairs_list:
            # Обновляем биржевые прецизионы из внешнего провайдера,
            # если он передан. Это делает биржу источником правды,
            # а БД/дефолты – лишь стартовыми значениями.
            if precision_provider is not None:
                precisions = precision_provider.get_precisions(pair.symbol)
                if precisions is not None:
                    pair.min_step = precisions["min_step"]
                    pair.price_step = precisions["price_step"]

            symbol = pair.symbol
            if symbol in index:
                raise ValueError(f"Duplicate currency pair symbol: {symbol!r}")
            index[symbol] = pair

        self._pairs: List[CurrencyPair] = pairs_list
        self._by_symbol: Dict[str, CurrencyPair] = index

    # --- Фабричный метод ---

    @classmethod
    def from_symbols(
        cls,
        symbols: List[str],
        precision_provider: IExchangePairMetadataProvider | None = None,
    ) -> "InMemoryCurrencyPairRepository":
        """Создать репозиторий из списка символов.

        На этом этапе базовая/котируемая валюта определяются простым
        разбиением строки "BTC/USDT". Логика инкапсулируется в
        репозитории, чтобы не размазывать её по коду конвейера.
        """

        pairs: List[CurrencyPair] = []
        for symbol in symbols:
            if "/" in symbol:
                base, quote = symbol.split("/", 1)
            else:
                # Фолбэк на случай нестандартного символа, совместим с
                # текущим поведением прототипа.
                base, quote = symbol, "USDT"

            pairs.append(
                CurrencyPair(
                    symbol=symbol,
                    base_currency=base,
                    quote_currency=quote,
                )
            )

        return cls(pairs, precision_provider=precision_provider)

    # --- API репозитория ---

    def list_all(self, include_disabled: bool = True) -> List[CurrencyPair]:  # type: ignore[override]
        if include_disabled:
            return list(self._pairs)
        return [p for p in self._pairs if p.enabled]

    def list_active(self) -> List[CurrencyPair]:  # type: ignore[override]
        return [p for p in self._pairs if p.enabled]

    def get_by_symbol(self, symbol: str) -> CurrencyPair | None:  # type: ignore[override]
        return self._by_symbol.get(symbol)


__all__ = ["InMemoryCurrencyPairRepository"]
