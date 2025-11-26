"""Интерфейс репозитория валютных пар.

Ранний прототип использует только in-memory реализацию, но интерфейс
должен быть совместим с будущей реализацией поверх БД (PostgreSQL и т.п.).

Репозиторий отвечает за:

* предоставление списка активных пар для конвейера;
* поиск пары по символу биржи;
* возможность вернуть все пары (включая выключенные), чтобы позже
  синхронизироваться с БД/стейтом.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from src.domain.entities.currency_pair import CurrencyPair


@runtime_checkable
class ICurrencyPairRepository(Protocol):
    """Контракт репозитория валютных пар.

    На этом этапе методы минимальны и покрывают потребности тикового
    конвейера. В дальнейшем интерфейс можно расширять (поиск по ID,
    сохранение новых настроек и т.п.).
    """

    def list_all(self, include_disabled: bool = True) -> List[CurrencyPair]:
        """Вернуть все пары.

        Args:
            include_disabled: если False, вернуть только enabled-пары.
        """

    def list_active(self) -> List[CurrencyPair]:
        """Вернуть только активные (``enabled``) пары."""

    def get_by_symbol(self, symbol: str) -> CurrencyPair | None:
        """Найти пару по символу биржи ("BTC/USDT")."""


__all__ = ["ICurrencyPairRepository"]
