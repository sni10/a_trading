"""Интерфейс сервиса синхронизации ордеров с биржей."""

from __future__ import annotations

from typing import Any, Protocol

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

    def apply_exchange_order_to_local(
        self,
        order: Order,
        ccxt_response: dict[str, Any],
        *,
        symbol: str,
        context: dict[str, Any],
    ) -> None:
        """Применить данные от биржи к локальному ордеру после создания.

        Args:
            order: Локальный объект ордера
            ccxt_response: Сырой CCXT unified order dict от биржи
            symbol: Торговая пара
            context: Общий контекст приложения
        """
        ...

    def apply_exchange_order(
        self,
        ccxt_response: dict[str, Any],
        *,
        symbol: str,
        context: dict[str, Any],
    ) -> None:
        """Применить WebSocket-апдейт ордера из стрима к локальному состоянию.

        Args:
            ccxt_response: Сырой CCXT unified order dict из стрима
            symbol: Торговая пара
            context: Общий контекст приложения
        """
        ...


__all__ = ["IOrderSyncService"]
