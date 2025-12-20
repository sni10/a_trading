"""SQLAlchemy-репозиторий валютных пар."""

from __future__ import annotations

from typing import List

from sqlalchemy import select

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.infrastructure.db.models.currency_pair_model import CurrencyPairModel
from src.infrastructure.db.session_factory import SqlAlchemySessionFactory


def _model_to_entity(model: CurrencyPairModel) -> CurrencyPair:
    return CurrencyPair.from_dict(
        {
            "pair_id": model.pair_id,
            "symbol": model.symbol,
            "base_currency": model.base_currency,
            "quote_currency": model.quote_currency,
            "deal_quota": model.deal_quota,
            "profit_markup": model.profit_markup,
            "deal_count": model.deal_count,
            "order_life_time": model.order_life_time,
            "min_step": model.min_step,
            "price_step": model.price_step,
            "enabled": model.enabled,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
    )


class SqlAlchemyCurrencyPairRepository(ICurrencyPairRepository):
    """Репозиторий CurrencyPair поверх SQLAlchemy."""

    def __init__(self, session_factory: SqlAlchemySessionFactory) -> None:
        self._sf = session_factory

    def list_all(self, include_disabled: bool = True) -> List[CurrencyPair]:
        with self._sf.session_scope() as session:
            stmt = select(CurrencyPairModel)
            if not include_disabled:
                stmt = stmt.where(CurrencyPairModel.enabled.is_(True))
            stmt = stmt.order_by(CurrencyPairModel.symbol)
            models = list(session.scalars(stmt).all())
            return [_model_to_entity(m) for m in models]

    def list_active(self) -> List[CurrencyPair]:
        return self.list_all(include_disabled=False)

    def get_by_symbol(self, symbol: str) -> CurrencyPair | None:
        with self._sf.session_scope() as session:
            stmt = select(CurrencyPairModel).where(CurrencyPairModel.symbol == symbol)
            model = session.scalar(stmt)
            return _model_to_entity(model) if model is not None else None

    def upsert(self, pair: CurrencyPair) -> CurrencyPair:
        """Создать/обновить пару по символу.

        Не часть доменного интерфейса, но полезно для инициализации/синхронизации.
        """

        with self._sf.session_scope() as session:
            stmt = select(CurrencyPairModel).where(CurrencyPairModel.symbol == pair.symbol)
            existing = session.scalar(stmt)
            if existing is None:
                existing = CurrencyPairModel(
                    symbol=pair.symbol,
                    base_currency=pair.base_currency,
                    quote_currency=pair.quote_currency,
                    enabled=pair.enabled,
                    deal_quota=pair.deal_quota,
                    profit_markup=pair.profit_markup,
                    deal_count=pair.deal_count,
                    order_life_time=pair.order_life_time,
                    min_step=pair.min_step,
                    price_step=pair.price_step,
                    created_at=pair.created_at,
                    updated_at=pair.updated_at,
                )
                session.add(existing)
            else:
                existing.base_currency = pair.base_currency
                existing.quote_currency = pair.quote_currency
                existing.enabled = pair.enabled
                existing.deal_quota = pair.deal_quota
                existing.profit_markup = pair.profit_markup
                existing.deal_count = pair.deal_count
                existing.order_life_time = pair.order_life_time
                existing.min_step = pair.min_step
                existing.price_step = pair.price_step
                existing.updated_at = pair.updated_at

            session.flush()
            return _model_to_entity(existing)


__all__ = ["SqlAlchemyCurrencyPairRepository"]
