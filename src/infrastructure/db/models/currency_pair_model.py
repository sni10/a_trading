"""ORM-модель валютной пары."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class CurrencyPairModel(Base):
    __tablename__ = "currency_pairs"

    pair_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    base_currency: Mapped[str] = mapped_column(String(16))
    quote_currency: Mapped[str] = mapped_column(String(16))

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Trading settings
    deal_quota: Mapped[float] = mapped_column(Float, default=25.0)
    profit_markup: Mapped[float] = mapped_column(Float, default=1.5)
    deal_count: Mapped[int] = mapped_column(Integer, default=3)
    order_life_time: Mapped[int] = mapped_column(Integer, default=1)
    max_loss_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Exchange params
    min_step: Mapped[float] = mapped_column(Float, default=0.00001)
    price_step: Mapped[float] = mapped_column(Float, default=0.01)

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


__all__ = ["CurrencyPairModel"]
