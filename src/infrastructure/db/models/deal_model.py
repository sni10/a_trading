"""ORM-модель сделки."""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class DealModel(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)

    created_at: Mapped[int] = mapped_column(BigInteger, index=True)
    opened_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    closed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    buy_order_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sell_order_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    target_amount: Mapped[float] = mapped_column(Float, default=0.0)
    target_buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_sell_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_profit: Mapped[float | None] = mapped_column(Float, nullable=True)

    max_loss_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    strategy_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


__all__ = ["DealModel"]
