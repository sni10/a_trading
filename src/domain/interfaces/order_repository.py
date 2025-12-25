"""Интерфейс репозитория ордеров.

Доменный слой не знает о SQLAlchemy/БД, только о контракте.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from src.domain.entities.order import Order


@runtime_checkable
class IOrderRepository(Protocol):
    """Контракт репозитория ордеров."""

    def upsert(self, order: Order) -> None:
        """Создать или обновить ордер по его ID."""

    def get_by_id(self, order_id: str) -> Order | None:
        """Получить ордер по ID."""

    def list_by_symbol(self, symbol: str, *, limit: int = 100) -> List[Order]:
        """Список ордеров по инструменту (последние N)."""


__all__ = ["IOrderRepository"]
