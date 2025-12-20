"""ORM-модель ордера."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, index=True)
    datetime: Mapped[str] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8), index=True)
    type: Mapped[str] = mapped_column(String(16), index=True)

    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    average: Mapped[float | None] = mapped_column(Float, nullable=True)
    filled: Mapped[float] = mapped_column(Float, default=0.0)
    remaining: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)

    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    last_trade_timestamp: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    time_in_force: Mapped[str | None] = mapped_column(String(16), nullable=True)
    post_only: Mapped[bool] = mapped_column(Boolean, default=False)
    reduce_only: Mapped[bool] = mapped_column(Boolean, default=False)

    trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    fee_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trades_json: Mapped[list] = mapped_column(JSON, default=list)
    info_json: Mapped[dict] = mapped_column(JSON, default=dict)

    deal_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


__all__ = ["OrderModel"]
