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

        Порядок важен: deals → orders → trades, т.к. каждый следующий
        уровень ссылается на PK предыдущего (deal_id, order_id).

        Репозитории при INSERT через ``flush()`` автоматически
        синхронизируют DB autoincrement PK обратно в in-memory entity.
        """
        # 1. Deals — сначала, чтобы deal.id был назначен до сохранения orders
        if self._deal_repo:
            deals = (context.get("deals") or {}).get(self._symbol, [])
            saved_deals = 0
            for deal in deals:
                status = str(getattr(deal, "status", "")).lower()
                if status:
                    self._deal_repo.update(deal)
                    # После update deal.id гарантированно назначен БД
                    saved_deals += 1
            log_stage(
                "DB_SAVE",
                f"💾 Сохранено сделок: {saved_deals}",
                symbol=self._symbol,
            )

        # 2. Orders — deal_id уже проставлен (через deal.assign_db_id → _sync_deal_id)
        if self._order_repo:
            orders = (context.get("orders") or {}).get(self._symbol, [])
            saved_orders = 0
            for order in orders:
                status = str(getattr(order, "status", "")).lower()
                if status in ("open", "closed", "canceled"):
                    self._order_repo.upsert(order)
                    # После upsert order.id гарантированно назначен БД
                    saved_orders += 1
            log_stage(
                "DB_SAVE",
                f"💾 Сохранено ордеров: {saved_orders}",
                symbol=self._symbol,
            )

        # 3. Trades — order_id уже проставлен
        if self._trade_repo:
            trades = (context.get("trades") or {}).get(self._symbol, [])
            orders = (context.get("orders") or {}).get(self._symbol, [])

            for trade in trades:
                # Если order_id не установлен, попробовать найти через связь с order
                if not trade.order_id:
                    matching_order = next(
                        (o for o in orders
                         if o.symbol == trade.symbol and o.side == trade.side
                         and o.id is not None),
                        None
                    )
                    if matching_order:
                        trade.order_id = matching_order.id

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

        # Загрузить все ордера по паре (открытые и закрытые)
        orders = []
        if self._order_repo:
            # Загрузить все ордера по символу
            orders = self._order_repo.list_by_symbol(self._symbol, limit=100)

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

        # КРИТИЧЕСКИ ВАЖНО: Восстановить связи Deal <-> Order
        if deals and orders:
            for deal in deals:
                # Найти BUY ордер для этой сделки
                buy_order = next(
                    (o for o in orders if o.deal_id == deal.id and str(o.side).lower() == "buy"),
                    None
                )
                # Найти SELL ордер для этой сделки
                sell_order = next(
                    (o for o in orders if o.deal_id == deal.id and str(o.side).lower() == "sell"),
                    None
                )

                deal.buy_order = buy_order
                deal.sell_order = sell_order

                log_stage(
                    "DB_LOAD",
                    f"🔗 Восстановлены связи для сделки {deal.id}: buy_order={buy_order.id if buy_order else None}, sell_order={sell_order.id if sell_order else None}",
                    symbol=self._symbol,
                )


__all__ = ["StateSnapshotService"]
