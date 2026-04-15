"""Сервис синхронизации локальных ордеров с биржевыми."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.order import Order
    from src.domain.interfaces import IExchangeConnector, ILogger, IOrderRepository


class OrderSyncService:
    """Сервис синхронизации ордеров с биржей.

    Отвечает за:
    - Загрузку открытых ордеров с биржи
    - Сравнение с локальным состоянием (БД)
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

    async def sync_orders_with_exchange(
        self,
        symbol: str,
        *,
        context: dict[str, Any] | None = None,
        buy_timeout_sec: float = 30.0,
    ) -> list[Order]:
        """Синхронизировать ордера с биржей.

        Алгоритм:
        1. Загрузить открытые ордера с биржи (fetch_open_orders)
        2. Загрузить локальные открытые ордера из контекста
        3. Сравнить состояния:
           - Если ордер закрылся на бирже -> обновить локально и в БД
           - Если ордер частично исполнен -> обновить filled/remaining
           - Если ордер отменён -> пометить canceled
        4. Вернуть актуальный список

        Args:
            symbol: Символ валютной пары
            context: Общий контекст приложения
            buy_timeout_sec: Таймаут BUY-ордера (не используется пока)

        Returns:
            List[Order] - актуальные открытые ордера после синхронизации
        """
        if self._logger:
            self._logger.log_stage("ORDER_SYNC", f"Syncing orders for {symbol}")

        # Загрузить открытые ордера с биржи
        raw_exchange_orders = await self._exchange.fetch_open_orders(symbol)

        # Построить индекс биржевых ордеров по exchange_order_id
        exchange_orders_map: dict[str, dict[str, Any]] = {}
        for raw in raw_exchange_orders:
            eid = str(raw.get("id", ""))
            if eid:
                exchange_orders_map[eid] = raw

        # Локальные ордера из контекста (in-memory — актуальнее БД)
        orders_list: list[Order] = []
        if context is not None:
            orders_list = (context.get("orders") or {}).get(symbol) or []
        else:
            orders_list = self._order_repo.list_by_symbol(symbol, limit=100)

        synced_orders: list[Order] = []
        for local_order in orders_list:
            if local_order.status not in ("open", "closed"):
                continue

            if not local_order.exchange_order_id:
                # Ещё не размещён на бирже — пропускаем
                synced_orders.append(local_order)
                continue

            raw = exchange_orders_map.get(local_order.exchange_order_id)

            if raw is None:
                # Ордер не найден среди открытых — мог закрыться / отмениться
                if local_order.status == "open":
                    if self._logger:
                        self._logger.log_stage(
                            "ORDER_SYNC",
                            f"Order {local_order.exchange_order_id} not in open orders, fetching details",
                        )
                    updated = await self.fetch_and_update_order(
                        local_order.exchange_order_id, symbol, local_order
                    )
                    if updated:
                        synced_orders.append(updated)
            else:
                # Ордер найден — применить обновления
                applied = local_order.update_from_exchange(raw)
                if applied:
                    self._order_repo.upsert(local_order)
                    if self._logger:
                        self._logger.log_stage(
                            "ORDER_SYNC",
                            f"Updated order {local_order.exchange_order_id}: {local_order.status}",
                        )
                synced_orders.append(local_order)

        if self._logger:
            self._logger.log_stage(
                "ORDER_SYNC", f"Synced {len(synced_orders)} orders for {symbol}"
            )

        return synced_orders

    async def fetch_and_update_order(
        self,
        exchange_order_id: str,
        symbol: str,
        local_order: Order | None = None,
    ) -> Order | None:
        """Получить актуальное состояние ордера с биржи и обновить локальный.

        Args:
            exchange_order_id: ID ордера на бирже
            symbol: Торговая пара
            local_order: Локальный объект ордера (если есть)

        Returns:
            Order | None - обновлённый ордер или None если не найден
        """
        try:
            raw = await self._exchange.fetch_order(exchange_order_id, symbol)
        except Exception as exc:
            if self._logger:
                self._logger.log_stage(
                    "ORDER_SYNC",
                    f"Failed to fetch order {exchange_order_id}: {type(exc).__name__}: {exc}",
                )
            return None

        if not raw:
            return None

        if local_order is not None:
            applied = local_order.update_from_exchange(raw)
            if applied:
                self._order_repo.upsert(local_order)
            return local_order

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
        order: Order,
        ccxt_response: dict,
        *,
        symbol: str,
        context: dict,
    ) -> None:
        """Применить данные от биржи к локальному ордеру после создания/обновления.

        Вызывается из ``order_execution_worker`` после успешного
        ``connector.create_order()``. Мутирует существующий объект Order
        на месте через ``update_from_exchange``, затем сохраняет в БД.

        Args:
            order: Локальный объект ордера (тот же, что в Deal)
            ccxt_response: Сырой CCXT unified order dict от биржи
            symbol: Торговая пара
            context: Общий контекст приложения
        """
        applied = order.update_from_exchange(ccxt_response)
        if applied:
            self._order_repo.upsert(order)
            if self._logger:
                self._logger.log_stage(
                    "ORDER_SYNC",
                    f"Applied exchange data to order {order.exchange_order_id}",
                )

    def apply_exchange_order(
        self,
        ccxt_response: dict,
        *,
        symbol: str,
        context: dict,
    ) -> None:
        """Применить WebSocket-апдейт ордера из стрима к локальному состоянию.

        Вызывается из ``order_stream_worker``. Ищет существующий Order
        в контексте по ``exchange_order_id`` и обновляет его через
        ``update_from_exchange`` с timestamp guard.

        Args:
            ccxt_response: Сырой CCXT unified order dict из стрима
            symbol: Торговая пара
            context: Общий контекст приложения
        """
        exchange_order_id = str(ccxt_response.get("id", ""))
        if not exchange_order_id:
            return

        orders_list = (context.get("orders") or {}).get(symbol) or []
        order = None
        for o in orders_list:
            if o.exchange_order_id == exchange_order_id:
                order = o
                break

        if order is None:
            if self._logger:
                self._logger.log_stage(
                    "ORDER_SYNC",
                    f"Stream order {exchange_order_id} not found locally, skipping",
                )
            return

        applied = order.update_from_exchange(ccxt_response)
        if applied:
            self._order_repo.upsert(order)
            if self._logger:
                self._logger.log_stage(
                    "ORDER_SYNC",
                    f"Stream-updated order {exchange_order_id}: {order.status}",
                )


__all__ = ["OrderSyncService"]
