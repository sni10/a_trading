"""Интерфейс репозитория сделок (внутренняя сущность бота)."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from src.domain.entities.deal import Deal


@runtime_checkable
class IDealRepository(Protocol):
    """Контракт репозитория сделок."""

    def add(self, deal: Deal) -> Deal:
        """Создать сделку. Может вернуть deal с присвоенным id."""

    def update(self, deal: Deal) -> None:
        """Обновить существующую сделку."""

    def get_by_id(self, deal_id: int) -> Deal | None:
        """Найти сделку по id."""

    def list_active_by_symbol(self, symbol: str) -> List[Deal]:
        """Вернуть активные сделки по инструменту."""


__all__ = ["IDealRepository"]
