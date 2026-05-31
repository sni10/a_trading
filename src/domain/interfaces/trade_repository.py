"""Интерфейс репозитория трейдов (исполнений)."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from src.domain.entities.trade import Trade


@runtime_checkable
class ITradeRepository(Protocol):
    """Контракт репозитория трейдов."""

    def upsert(self, trade: Trade) -> None:
        """Создать или обновить трейд по его ID."""

    def get_by_id(self, trade_id: str) -> Trade | None:
        """Получить трейд по ID (биржевой id)."""

    def list_by_order_id(self, order_id: str, *, limit: int = 500) -> List[Trade]:
        """Список трейдов по ордеру (последние N)."""


__all__ = ["ITradeRepository"]
