"""ORM-модель трейда (частичное/полное исполнение ордера)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class TradeModel(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    order: Mapped[str] = mapped_column(String(128), index=True)

    timestamp: Mapped[int] = mapped_column(BigInteger, index=True)
    datetime: Mapped[str] = mapped_column(String(64))

    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8), index=True)

    price: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)

    taker_or_maker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    type: Mapped[str | None] = mapped_column(String(16), nullable=True)

    fee_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fees_json: Mapped[list] = mapped_column(JSON, default=list)
    info_json: Mapped[dict] = mapped_column(JSON, default=dict)


__all__ = ["TradeModel"]
