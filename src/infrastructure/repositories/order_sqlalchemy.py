"""SQLAlchemy-репозиторий ордеров."""

from __future__ import annotations

from typing import List

from sqlalchemy import select

from src.domain.entities.order import Order
from src.domain.interfaces.order_repository import IOrderRepository
from src.infrastructure.db.models.order_model import OrderModel
from src.infrastructure.db.session_factory import SqlAlchemySessionFactory


def _entity_to_model(order: Order) -> OrderModel:
    data = order.to_dict()
    return OrderModel(
        id=int(data["id"]) if data.get("id") is not None else None,
        exchange_order_id=str(data["exchange_order_id"]) if data.get("exchange_order_id") is not None else None,
        symbol=str(data["symbol"]),
        timestamp=int(data["timestamp"]),
        datetime=str(data["datetime"]),
        status=str(data["status"]),
        side=str(data["side"]),
        type=str(data["type"]),
        amount=float(data["amount"]),
        price=float(data["price"]) if data.get("price") is not None else None,
        average=float(data["average"]) if data.get("average") is not None else None,
        filled=float(data.get("filled", 0.0)),
        remaining=float(data.get("remaining", 0.0)),
        cost=float(data.get("cost", 0.0)),
        last_trade_timestamp=(
            int(data["last_trade_timestamp"]) if data.get("last_trade_timestamp") is not None else None
        ),
        time_in_force=str(data["time_in_force"]) if data.get("time_in_force") is not None else None,
        post_only=bool(data.get("post_only", False)),
        reduce_only=bool(data.get("reduce_only", False)),
        trigger_price=float(data["trigger_price"]) if data.get("trigger_price") is not None else None,
        stop_loss_price=float(data["stop_loss_price"]) if data.get("stop_loss_price") is not None else None,
        take_profit_price=float(data["take_profit_price"]) if data.get("take_profit_price") is not None else None,
        fee_json=data.get("fee"),
        trades_json=list(data.get("trades") or []),
        info_json=dict(data.get("info") or {}),
        deal_id=int(data["deal_id"]) if data.get("deal_id") is not None else None,
    )


def _model_to_entity(model: OrderModel) -> Order:
    return Order.from_dict(
        {
            "id": model.id,
            "exchange_order_id": model.exchange_order_id,
            "symbol": model.symbol,
            "timestamp": model.timestamp,
            "datetime": model.datetime,
            "status": model.status,
            "side": model.side,
            "type": model.type,
            "amount": model.amount,
            "price": model.price,
            "average": model.average,
            "filled": model.filled,
            "remaining": model.remaining,
            "cost": model.cost,
            "last_trade_timestamp": model.last_trade_timestamp,
            "time_in_force": model.time_in_force,
            "post_only": model.post_only,
            "reduce_only": model.reduce_only,
            "trigger_price": model.trigger_price,
            "stop_loss_price": model.stop_loss_price,
            "take_profit_price": model.take_profit_price,
            "fee": model.fee_json,
            "trades": model.trades_json,
            "info": model.info_json,
            "deal_id": model.deal_id,
        }
    )


class SqlAlchemyOrderRepository(IOrderRepository):
    """Репозиторий Order поверх SQLAlchemy."""

    def __init__(self, session_factory: SqlAlchemySessionFactory) -> None:
        self._sf = session_factory

    def upsert(self, order: Order) -> None:
        model = _entity_to_model(order)
        with self._sf.session_scope() as session:
            # Если есть id - update существующего, иначе ищем по exchange_order_id
            if model.id:
                existing = session.get(OrderModel, model.id)
                if existing:
                    # Update существующего
                    for key, value in model.__dict__.items():
                        if not key.startswith('_'):
                            setattr(existing, key, value)
                    return
            elif model.exchange_order_id:
                # Ищем по exchange_order_id
                from sqlalchemy import select
                stmt = select(OrderModel).where(OrderModel.exchange_order_id == model.exchange_order_id)
                existing = session.scalars(stmt).first()
                if existing:
                    # Update существующего
                    for key, value in model.__dict__.items():
                        if not key.startswith('_') and key != 'id':
                            setattr(existing, key, value)
                    return

            # Новая запись
            session.add(model)

    def get_by_id(self, order_id: int) -> Order | None:
        with self._sf.session_scope() as session:
            model = session.get(OrderModel, order_id)
            return _model_to_entity(model) if model is not None else None

    def list_by_symbol(self, symbol: str, *, limit: int = 100) -> List[Order]:
        with self._sf.session_scope() as session:
            stmt = (
                select(OrderModel)
                .where(OrderModel.symbol == symbol)
                .order_by(OrderModel.timestamp.desc())
                .limit(limit)
            )
            models = list(session.scalars(stmt).all())
            return [_model_to_entity(m) for m in models]


__all__ = ["SqlAlchemyOrderRepository"]
