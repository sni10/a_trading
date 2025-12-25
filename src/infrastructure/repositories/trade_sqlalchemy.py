"""SQLAlchemy-репозиторий трейдов."""

from __future__ import annotations

from typing import List

from sqlalchemy import select

from src.domain.entities.trade import Trade
from src.domain.interfaces.trade_repository import ITradeRepository
from src.infrastructure.db.models.trade_model import TradeModel
from src.infrastructure.db.session_factory import SqlAlchemySessionFactory


def _entity_to_model(trade: Trade) -> TradeModel:
    data = trade.to_dict()
    return TradeModel(
        id=int(data["id"]) if data.get("id") is not None else None,
        exchange_trade_id=str(data["exchange_trade_id"]) if data.get("exchange_trade_id") is not None else None,
        order_id=int(data["order_id"]) if data.get("order_id") is not None else None,
        timestamp=int(data["timestamp"]),
        datetime=str(data["datetime"]),
        symbol=str(data["symbol"]),
        side=str(data["side"]),
        price=float(data["price"]),
        amount=float(data["amount"]),
        cost=float(data["cost"]),
        taker_or_maker=str(data["taker_or_maker"]) if data.get("taker_or_maker") is not None else None,
        type=str(data["type"]) if data.get("type") is not None else None,
        fee_json=data.get("fee"),
        fees_json=list(data.get("fees") or []),
        info_json=dict(data.get("info") or {}),
    )


def _model_to_entity(model: TradeModel) -> Trade:
    return Trade.from_dict(
        {
            "id": model.id,
            "exchange_trade_id": model.exchange_trade_id,
            "order_id": model.order_id,
            "timestamp": model.timestamp,
            "datetime": model.datetime,
            "symbol": model.symbol,
            "side": model.side,
            "price": model.price,
            "amount": model.amount,
            "cost": model.cost,
            "taker_or_maker": model.taker_or_maker,
            "type": model.type,
            "fee": model.fee_json,
            "fees": model.fees_json,
            "info": model.info_json,
        }
    )


class SqlAlchemyTradeRepository(ITradeRepository):
    """Репозиторий Trade поверх SQLAlchemy."""

    def __init__(self, session_factory: SqlAlchemySessionFactory) -> None:
        self._sf = session_factory

    def upsert(self, trade: Trade) -> None:
        model = _entity_to_model(trade)
        with self._sf.session_scope() as session:
            # Если есть id - update существующего, иначе ищем по exchange_trade_id
            if model.id:
                existing = session.get(TradeModel, model.id)
                if existing:
                    # Update существующего
                    for key, value in model.__dict__.items():
                        if not key.startswith('_'):
                            setattr(existing, key, value)
                    return
            elif model.exchange_trade_id:
                # Ищем по exchange_trade_id
                from sqlalchemy import select
                stmt = select(TradeModel).where(TradeModel.exchange_trade_id == model.exchange_trade_id)
                existing = session.scalars(stmt).first()
                if existing:
                    # Update существующего
                    for key, value in model.__dict__.items():
                        if not key.startswith('_') and key != 'id':
                            setattr(existing, key, value)
                    return

            # Новая запись
            session.add(model)

    def get_by_id(self, trade_id: int) -> Trade | None:
        with self._sf.session_scope() as session:
            model = session.get(TradeModel, trade_id)
            return _model_to_entity(model) if model is not None else None

    def list_by_order_id(self, order_id: int, *, limit: int = 500) -> List[Trade]:
        with self._sf.session_scope() as session:
            stmt = (
                select(TradeModel)
                .where(TradeModel.order_id == order_id)
                .order_by(TradeModel.timestamp.desc())
                .limit(limit)
            )
            models = list(session.scalars(stmt).all())
            return [_model_to_entity(m) for m in models]


__all__ = ["SqlAlchemyTradeRepository"]
