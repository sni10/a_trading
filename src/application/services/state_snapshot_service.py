from __future__ import annotations

"""Сервис работы со снапшотами состояния.

Выносит логику загрузки/сохранения state из основного сценария
реального времени, чтобы ``run()`` оперировал только in‑memory
контекстом и высокоуровневым сервисом.

РАСШИРЕН для работы с БД-сущностями (Deal, Order, Trade).
"""

from typing import Any, Dict

from src.config.config import AppConfig
from src.domain.services.context.state import apply_state_snapshot, make_state_snapshot
from src.domain.interfaces.state_snapshot_store import IStateSnapshotStore
from src.domain.interfaces import IDealRepository, IOrderRepository, ITradeRepository
from src.infrastructure.logging import log_stage


class StateSnapshotService:
    """Сервис для загрузки и периодического сохранения снапшотов state.

    Работает поверх :class:`FileStateSnapshotStore` и типизированного
    ``AppConfig``. На этом уровне не знает деталей тик‑конвейера,
    оперирует только ``dict``‑контекстом.

    РАСШИРЕН: Теперь сохраняет БД-сущности (Deal, Order, Trade) через репозитории.
    """

    def __init__(
        self,
        store: IStateSnapshotStore,
        cfg: AppConfig,
        *,
        symbol: str,
        deal_repo: IDealRepository | None = None,
        order_repo: IOrderRepository | None = None,
        trade_repo: ITradeRepository | None = None,
    ) -> None:
        self._store = store
        self._cfg = cfg
        self._symbol = symbol
        self._key = f"{cfg.environment}:{symbol}"

        # Репозитории для БД-персистентности
        self._deal_repo = deal_repo
        self._order_repo = order_repo
        self._trade_repo = trade_repo

    def load(self, context: Dict[str, Any]) -> int:
        """Загрузить снапшот и применить его к ``context``.

        Возвращает стартовый ``ticker_id`` из снапшота или ``0``, если
        снапшота нет или он пустой.
        """

        snapshot = self._store.load_snapshot(self._key)
        if not snapshot:
            # Нет снапшота – стартуем с пустого in‑memory state
            log_stage(
                "LOAD",
                "📦 Снапшот state не найден, стартуем с пустого in-memory state",
                symbol=self._symbol,
            )
            return 0

        apply_state_snapshot(context, symbol=self._symbol, snapshot=snapshot)

        loaded_ticker_id = int(snapshot.get("ticker_id") or 0)
        log_stage(
            "LOAD",
            "📦 Снапшот state найден и загружен",
            symbol=self._symbol,
            ticker_id=loaded_ticker_id,
        )
        return loaded_ticker_id

    def maybe_save(self, context: Dict[str, Any], *, ticker_id: int) -> None:
        """По интервалу сохранить снапшот state во внешнее хранилище.

        Интервал берётся из ``cfg.state_snapshot_interval_ticks``. Если
        интервал не задан (<= 0) или ``ticker_id`` не кратен интервалу –
        ничего не делает.

        РАСШИРЕН: Также сохраняет БД-сущности в БД через репозитории.
        """

        interval = getattr(self._cfg, "state_snapshot_interval_ticks", 0)
        if interval <= 0:
            return

        if ticker_id % interval != 0:
            return

        snapshot = make_state_snapshot(
            context,
            symbol=self._symbol,
            ticker_id=ticker_id,
        )
        # Сохранить в файл (как раньше)
        self._store.save_snapshot(self._key, snapshot)

        # РАСШИРЕНИЕ: Сохранить БД-сущности в БД
        self._save_entities_to_db(context)

    def _save_entities_to_db(self, context: Dict[str, Any]) -> None:
        """Сохранить БД-сущности из контекста в БД.

        Сохраняет:
        - Активные сделки (deals)
        - Открытые ордера (orders)
        - Недавние трейды (trades)
        """
        # Deals
        if self._deal_repo:
            deals = (context.get("deals") or {}).get(self._symbol, [])
            for deal in deals:
                if deal.is_active():
                    self._deal_repo.update(deal)
            log_stage(
                "DB_SAVE",
                f"💾 Сохранено активных сделок: {len([d for d in deals if d.is_active()])}",
                symbol=self._symbol,
            )

        # Orders
        if self._order_repo:
            orders = (context.get("orders") or {}).get(self._symbol, [])
            for order in orders:
                if order.status in ["open", "closed"]:
                    self._order_repo.upsert(order)
            log_stage(
                "DB_SAVE",
                f"💾 Сохранено ордеров: {len([o for o in orders if o.status in ['open', 'closed']])}",
                symbol=self._symbol,
            )

        # Trades
        if self._trade_repo:
            trades = (context.get("trades") or {}).get(self._symbol, [])
            for trade in trades:
                self._trade_repo.upsert(trade)
            log_stage(
                "DB_SAVE",
                f"💾 Сохранено трейдов: {len(trades)}",
                symbol=self._symbol,
            )

    def load_from_db(self, context: Dict[str, Any]) -> None:
        """Восстановить состояние БД-сущностей из БД в контекст.

        Загружает из БД:
        - Активные сделки по паре
        - Открытые ордера
        - Трейды по ордерам

        Заполняет секции контекста: deals, orders, trades.
        """
        if not any([self._deal_repo, self._order_repo, self._trade_repo]):
            log_stage(
                "DB_LOAD",
                "⚠️  Репозитории не заданы, пропуск загрузки из БД",
                symbol=self._symbol,
            )
            return

        # Загрузить активные сделки
        deals = []
        if self._deal_repo:
            deals = self._deal_repo.list_active_by_symbol(self._symbol)
            deals_section = context.setdefault("deals", {})
            deals_section[self._symbol] = deals
            log_stage(
                "DB_LOAD",
                f"📥 Загружено активных сделок из БД: {len(deals)}",
                symbol=self._symbol,
            )

        # Загрузить ордера по сделкам + дополнительные открытые ордера
        orders = []
        if self._order_repo:
            # Ордера из сделок
            for deal in deals:
                if deal.buy_order:
                    orders.append(deal.buy_order)
                if deal.sell_order:
                    orders.append(deal.sell_order)

            # Дополнительно загрузить открытые ордера по паре
            all_orders = self._order_repo.list_by_symbol(self._symbol, limit=100)
            open_orders = [o for o in all_orders if o.status == "open"]
            orders.extend(open_orders)

            # Убрать дубликаты
            orders_map = {o.id: o for o in orders}
            orders = list(orders_map.values())

            orders_section = context.setdefault("orders", {})
            orders_section[self._symbol] = orders
            log_stage(
                "DB_LOAD",
                f"📥 Загружено ордеров из БД: {len(orders)}",
                symbol=self._symbol,
            )

        # Загрузить трейды по ордерам
        trades = []
        if self._trade_repo:
            for order in orders:
                order_trades = self._trade_repo.list_by_order_id(order.id, limit=500)
                trades.extend(order_trades)

            trades_section = context.setdefault("trades", {})
            trades_section[self._symbol] = trades
            log_stage(
                "DB_LOAD",
                f"📥 Загружено трейдов из БД: {len(trades)}",
                symbol=self._symbol,
            )


__all__ = ["StateSnapshotService"]
