"""Сервис синхронизации локальных ордеров с биржевыми."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.order import Order
    from src.domain.interfaces import IExchangeConnector, ILogger, IOrderRepository


class OrderSyncService:
    """Сервис синхронизации ордеров с биржей.

    Отвечает за:
    - Загрузку ВСЕХ ордеров с биржи
    - Сравнение с локальным состоянием (БД)
    - ЕСЛИ ордер не имеет сделки в БД - игнорировать.
    - Обновление статусов при расхождениях
    - Разрешение конфликтов (биржа - источник истины)
    """

    def __init__(
        self,
        order_repo: IOrderRepository,
        exchange: IExchangeConnector,
        logger: ILogger | None = None,
    ) -> None:
        """Инициализация сервиса.

        Args:
            order_repo: Репозиторий ордеров
            exchange: Коннектор биржи
            logger: Логгер (опционально)
        """
        self._order_repo = order_repo
        self._exchange = exchange
        self._logger = logger

    def sync_orders_with_exchange(self, symbol: str) -> list[Order]:
        """Синхронизировать ордера с биржей.

        Алгоритм:
        0. Проверить сделки открытые и связанные ордера бай/селл
        1. Загрузить открытые ордера с биржи (fetch_open_orders)
        2. Загрузить локальные открытые ордера из БД
        3. Сравнить состояния:
           - Если ордер закрылся на бирже -> обновить в БД
           - Если ордер частично исполнен -> обновить filled/remaining
           - Если ордер отменён -> пометить canceled
        3,1 Если селл исполнен -> обновить в БД. ЗАкрыть сделку.
        4. Вернуть актуальный список

        Args:
            symbol: Символ валютной пары

        Returns:
            List[Order] - актуальные ордера после синхронизации
        """
        if self._logger:
            self._logger.log_stage("ORDER_SYNC", f"Syncing orders for {symbol}")

        # ЗАГЛУШКА: Загрузить открытые ордера с биржи
        # TODO: Реализовать после готовности IExchangeConnector.fetch_open_orders()
        exchange_orders = self._fetch_open_orders_stub(symbol)

        # Загрузить локальные ордера из БД
        local_orders = self._order_repo.list_by_symbol(symbol, limit=100)

        # Создать индекс биржевых ордеров для быстрого поиска
        exchange_orders_map = {order.id: order for order in exchange_orders}

        # Сравнить и обновить
        synced_orders = []
        for local_order in local_orders:
            if local_order.status not in ["open", "closed"]:
                continue  # Пропускаем canceled/expired

            exchange_order = exchange_orders_map.get(local_order.id)

            if exchange_order is None:
                # Ордер не найден на бирже - возможно закрыт или отменён
                if local_order.status == "open":
                    if self._logger:
                        self._logger.log_stage(
                            "ORDER_SYNC",
                            f"Order {local_order.id} not found on exchange, fetching details",
                        )
                    # Попытаться получить детали
                    updated = self.fetch_and_update_order(local_order.id)
                    if updated:
                        synced_orders.append(updated)
            else:
                # Ордер найден - проверить изменения
                if self._has_order_changed(local_order, exchange_order):
                    if self._logger:
                        self._logger.log_stage(
                            "ORDER_SYNC",
                            f"Updating order {local_order.id}: {local_order.status} -> {exchange_order.status}",
                        )
                    self._order_repo.upsert(exchange_order)
                    synced_orders.append(exchange_order)
                else:
                    synced_orders.append(local_order)

        if self._logger:
            self._logger.log_stage(
                "ORDER_SYNC", f"Synced {len(synced_orders)} orders for {symbol}"
            )

        return synced_orders

    def fetch_and_update_order(self, order_id: str) -> Order | None:
        """Получить актуальное состояние ордера с биржи.

        Args:
            order_id: ID ордера на бирже

        Returns:
            Order | None - обновлённый ордер или None если не найден
        """
        # ЗАГЛУШКА: Получить ордер с биржи
        # TODO: Реализовать после готовности IExchangeConnector.fetch_order()
        exchange_order = self._fetch_order_stub(order_id)

        if exchange_order:
            self._order_repo.upsert(exchange_order)
            return exchange_order

        return None

    def _has_order_changed(self, local: Order, exchange: Order) -> bool:
        """Проверить изменилось ли состояние ордера.

        Args:
            local: Локальный ордер из БД
            exchange: Ордер с биржи

        Returns:
            bool - True если есть изменения
        """
        return (
            local.status != exchange.status
            or local.filled != exchange.filled
            or local.remaining != exchange.remaining
            or local.average != exchange.average
        )

    def apply_exchange_order_to_local(
        self,
        local_order: Order,
        exchange_order_dict: dict,
        symbol: str,
        context: dict | None = None,
    ) -> None:
        """Применить данные с биржи к локальному ордеру.

        Обновляет локальный Order данными из ответа биржи (CCXT Order Structure).

        Args:
            local_order: Локальный ордер (entity)
            exchange_order_dict: Ответ от биржи (CCXT dict)
            symbol: Торговая пара
            context: Контекст приложения (опционально, для обновления in-memory)
        """
        # Обновить поля локального ордера данными с биржи
        local_order.exchange_order_id = str(exchange_order_dict.get("id", ""))
        local_order.status = str(exchange_order_dict.get("status", ""))
        local_order.filled = float(exchange_order_dict.get("filled", 0.0))
        local_order.remaining = float(exchange_order_dict.get("remaining", 0.0))
        local_order.cost = float(exchange_order_dict.get("cost", 0.0))
        local_order.average = (
            float(exchange_order_dict["average"])
            if exchange_order_dict.get("average")
            else None
        )
        local_order.last_trade_timestamp = (
            int(exchange_order_dict["lastTradeTimestamp"])
            if exchange_order_dict.get("lastTradeTimestamp")
            else None
        )

        # Сохранить в БД
        self._order_repo.upsert(local_order)

        if self._logger:
            self._logger.log_stage(
                "ORDER_SYNC",
                f"Ордер обновлён с биржи",
                order_id=local_order.id,
                exchange_order_id=local_order.exchange_order_id,
                status=local_order.status,
                filled=local_order.filled,
            )

    # =========================================================================
    # ЗАГЛУШКИ (TODO: Удалить после реализации IExchangeConnector методов)
    # =========================================================================

    def _fetch_open_orders_stub(self, symbol: str) -> list[Order]:
        """ЗАГЛУШКА: Получить все ордера с биржи.

        TODO: Заменить на self._exchange.fetch_open_orders(symbol)
        """
        if self._logger:
            self._logger.log_stage("ORDER_SYNC", f"[STUB] Fetching open orders for {symbol}")
        # Возвращаем пустой список (заглушка)
        return []

    def _fetch_order_stub(self, order_id: str) -> Order | None:
        """ЗАГЛУШКА: Получить конкретный ордер с биржи.

        TODO: Заменить на self._exchange.fetch_order(order_id)
        """
        if self._logger:
            self._logger.log_stage("ORDER_SYNC", f"[STUB] Fetching order {order_id}")
        # Возвращаем None (заглушка)
        return None


__all__ = ["OrderSyncService"]
