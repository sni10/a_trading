"""Интерфейс сервиса синхронизации ордеров с биржей."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.order import Order


class IOrderSyncService(Protocol):
    """Сервис синхронизации локальных ордеров с биржевыми.

    Отвечает за:
    - Загрузку открытых ордеров с биржи
    - Сравнение с локальным состоянием (БД + контекст)
    - Обновление статусов ордеров
    - Разрешение конфликтов при рассинхронизации
    """

    def sync_orders_with_exchange(self, symbol: str) -> list[Order]:
        """Синхронизировать ордера с биржей.

        Алгоритм:
        1. Загрузить открытые ордера с биржи (fetch_open_orders)
        2. Загрузить локальные открытые ордера из БД
        3. Сравнить состояния:
           - Если ордер закрылся на бирже -> обновить БД и контекст
           - Если ордер частично исполнен -> обновить filled/remaining
           - Если ордер отменён -> пометить как canceled
        4. Вернуть обновлённые ордера

        Args:
            symbol: Символ валютной пары

        Returns:
            List[Order] - актуальный список открытых ордеров после синхронизации
        """
        ...

    def fetch_and_update_order(self, order_id: str) -> Order | None:
        """Получить актуальное состояние конкретного ордера с биржи.

        Args:
            order_id: ID ордера на бирже

        Returns:
            Order | None - обновлённый ордер или None если не найден
        """
        ...


__all__ = ["IOrderSyncService"]
