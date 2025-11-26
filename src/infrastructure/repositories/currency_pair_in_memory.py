"""In-memory репозиторий валютных пар.

Используется ранним прототипом вместо прямой работы со строковыми
символами. Позже может быть заменён на реализацию поверх БД, не меняя
остальной код конвейера.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository


class InMemoryCurrencyPairRepository(ICurrencyPairRepository):
    """Простая in-memory реализация репозитория валютных пар.

    Пары передаются готовыми объектами :class:`CurrencyPair` или
    создаются из списка символов через :meth:`from_symbols`.
    """

    def __init__(self, pairs: Iterable[CurrencyPair]):
        pairs_list: List[CurrencyPair] = list(pairs)
        index: Dict[str, CurrencyPair] = {}

        for pair in pairs_list:
            symbol = pair.symbol
            if symbol in index:
                raise ValueError(f"Duplicate currency pair symbol: {symbol!r}")
            index[symbol] = pair

        self._pairs: List[CurrencyPair] = pairs_list
        self._by_symbol: Dict[str, CurrencyPair] = index

    # --- Фабричный метод ---

    @classmethod
    def from_symbols(cls, symbols: List[str]) -> "InMemoryCurrencyPairRepository":
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

        return cls(pairs)

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
