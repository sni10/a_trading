"""SQLAlchemy-репозиторий сделок."""

from __future__ import annotations

from typing import List

from sqlalchemy import select

from src.domain.entities.deal import Deal
from src.domain.interfaces.deal_repository import IDealRepository
from src.infrastructure.db.models.deal_model import DealModel
from src.infrastructure.db.session_factory import SqlAlchemySessionFactory


def _model_to_entity(model: DealModel) -> Deal:
    return Deal.from_dict(
        {
            "id": model.id,
            "symbol": model.symbol,
            "status": model.status,
            "created_at": model.created_at,
            "opened_at": model.opened_at,
            "closed_at": model.closed_at,
            "buy_order": model.buy_order_json,
            "sell_order": model.sell_order_json,
            "target_amount": model.target_amount,
            "target_buy_price": model.target_buy_price,
            "target_sell_price": model.target_sell_price,
            "expected_profit": model.expected_profit,
            "stop_loss_price": model.stop_loss_price,
            "take_profit_price": model.take_profit_price,
            "max_loss_amount": model.max_loss_amount,
            "strategy_name": model.strategy_name,
            "metadata": model.metadata_json,
        }
    )


class SqlAlchemyDealRepository(IDealRepository):
    """Репозиторий Deal поверх SQLAlchemy."""

    def __init__(self, session_factory: SqlAlchemySessionFactory) -> None:
        self._sf = session_factory

    def add(self, deal: Deal) -> Deal:
        with self._sf.session_scope() as session:
            model = DealModel(
                symbol=deal.symbol,
                status=deal.status,
                created_at=deal.created_at,
                opened_at=deal.opened_at,
                closed_at=deal.closed_at,
                buy_order_json=deal.buy_order.to_dict() if deal.buy_order else None,
                sell_order_json=deal.sell_order.to_dict() if deal.sell_order else None,
                target_amount=deal.target_amount,
                target_buy_price=deal.target_buy_price,
                target_sell_price=deal.target_sell_price,
                expected_profit=deal.expected_profit,
                stop_loss_price=deal.stop_loss_price,
                take_profit_price=deal.take_profit_price,
                max_loss_amount=deal.max_loss_amount,
                strategy_name=deal.strategy_name,
                metadata_json=dict(deal.metadata or {}),
            )
            session.add(model)
            session.flush()
            return _model_to_entity(model)

    def update(self, deal: Deal) -> None:
        with self._sf.session_scope() as session:
            model = session.get(DealModel, deal.id)
            if model is None:
                # Если записи нет, создаём.
                session.add(
                    DealModel(
                        id=deal.id,
                        symbol=deal.symbol,
                        status=deal.status,
                        created_at=deal.created_at,
                        opened_at=deal.opened_at,
                        closed_at=deal.closed_at,
                        buy_order_json=deal.buy_order.to_dict() if deal.buy_order else None,
                        sell_order_json=deal.sell_order.to_dict() if deal.sell_order else None,
                        target_amount=deal.target_amount,
                        target_buy_price=deal.target_buy_price,
                        target_sell_price=deal.target_sell_price,
                        expected_profit=deal.expected_profit,
                        stop_loss_price=deal.stop_loss_price,
                        take_profit_price=deal.take_profit_price,
                        max_loss_amount=deal.max_loss_amount,
                        strategy_name=deal.strategy_name,
                        metadata_json=dict(deal.metadata or {}),
                    )
                )
                return

            model.symbol = deal.symbol
            model.status = deal.status
            model.created_at = deal.created_at
            model.opened_at = deal.opened_at
            model.closed_at = deal.closed_at
            model.buy_order_json = deal.buy_order.to_dict() if deal.buy_order else None
            model.sell_order_json = deal.sell_order.to_dict() if deal.sell_order else None
            model.target_amount = deal.target_amount
            model.target_buy_price = deal.target_buy_price
            model.target_sell_price = deal.target_sell_price
            model.expected_profit = deal.expected_profit
            model.stop_loss_price = deal.stop_loss_price
            model.take_profit_price = deal.take_profit_price
            model.max_loss_amount = deal.max_loss_amount
            model.strategy_name = deal.strategy_name
            model.metadata_json = dict(deal.metadata or {})

    def get_by_id(self, deal_id: int) -> Deal | None:
        with self._sf.session_scope() as session:
            model = session.get(DealModel, deal_id)
            return _model_to_entity(model) if model is not None else None

    def list_active_by_symbol(self, symbol: str) -> List[Deal]:
        with self._sf.session_scope() as session:
            stmt = select(DealModel).where(
                DealModel.symbol == symbol,
                DealModel.status.in_([Deal.STATUS_PENDING, Deal.STATUS_OPEN, Deal.STATUS_CLOSING]),
            )
            stmt = stmt.order_by(DealModel.created_at.desc())
            models = list(session.scalars(stmt).all())
            return [_model_to_entity(m) for m in models]


__all__ = ["SqlAlchemyDealRepository"]
