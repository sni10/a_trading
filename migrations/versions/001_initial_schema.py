"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA = "main"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "currency_pairs",
        sa.Column("pair_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(32), unique=True, index=True, nullable=False),
        sa.Column("base_currency", sa.String(16), nullable=False),
        sa.Column("quote_currency", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("deal_quota", sa.Float, server_default=sa.text("25.0"), nullable=False),
        sa.Column("profit_markup", sa.Float, server_default=sa.text("1.5"), nullable=False),
        sa.Column("deal_count", sa.Integer, server_default=sa.text("3"), nullable=False),
        sa.Column("order_life_time", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column("max_loss_amount", sa.Float, nullable=True),
        sa.Column("min_step", sa.Float, server_default=sa.text("0.00001"), nullable=False),
        sa.Column("price_step", sa.Float, server_default=sa.text("0.01"), nullable=False),
        sa.Column("created_at", sa.BigInteger, nullable=False),
        sa.Column("updated_at", sa.BigInteger, nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("exchange_order_id", sa.String(128), unique=True, index=True, nullable=True),
        sa.Column("symbol", sa.String(32), index=True, nullable=False),
        sa.Column("timestamp", sa.BigInteger, index=True, nullable=False),
        sa.Column("datetime", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), index=True, nullable=False),
        sa.Column("side", sa.String(8), index=True, nullable=False),
        sa.Column("type", sa.String(16), index=True, nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("average", sa.Float, nullable=True),
        sa.Column("filled", sa.Float, server_default=sa.text("0.0"), nullable=False),
        sa.Column("remaining", sa.Float, server_default=sa.text("0.0"), nullable=False),
        sa.Column("cost", sa.Float, server_default=sa.text("0.0"), nullable=False),
        sa.Column("last_trade_timestamp", sa.BigInteger, nullable=True),
        sa.Column("time_in_force", sa.String(16), nullable=True),
        sa.Column("post_only", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("reduce_only", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("trigger_price", sa.Float, nullable=True),
        sa.Column("fee_json", sa.JSON, nullable=True),
        sa.Column("trades_json", sa.JSON, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("info_json", sa.JSON, server_default=sa.text("'{}'"), nullable=False),
        sa.Column("deal_id", sa.Integer, index=True, nullable=True),
        schema=SCHEMA,
    )

    op.create_table(
        "deals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(32), index=True, nullable=False),
        sa.Column("status", sa.String(16), index=True, nullable=False),
        sa.Column("created_at", sa.BigInteger, index=True, nullable=False),
        sa.Column("opened_at", sa.BigInteger, nullable=True),
        sa.Column("closed_at", sa.BigInteger, nullable=True),
        sa.Column("buy_order_json", sa.JSON, nullable=True),
        sa.Column("sell_order_json", sa.JSON, nullable=True),
        sa.Column("target_amount", sa.Float, server_default=sa.text("0.0"), nullable=False),
        sa.Column("target_buy_price", sa.Float, nullable=True),
        sa.Column("target_sell_price", sa.Float, nullable=True),
        sa.Column("expected_profit", sa.Float, nullable=True),
        sa.Column("max_loss_amount", sa.Float, nullable=True),
        sa.Column("strategy_name", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.JSON, server_default=sa.text("'{}'"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("exchange_trade_id", sa.String(128), unique=True, index=True, nullable=True),
        sa.Column("order_id", sa.Integer, index=True, nullable=True),
        sa.Column("timestamp", sa.BigInteger, index=True, nullable=False),
        sa.Column("datetime", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), index=True, nullable=False),
        sa.Column("side", sa.String(8), index=True, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("cost", sa.Float, nullable=False),
        sa.Column("taker_or_maker", sa.String(16), nullable=True),
        sa.Column("type", sa.String(16), nullable=True),
        sa.Column("fee_json", sa.JSON, nullable=True),
        sa.Column("fees_json", sa.JSON, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("info_json", sa.JSON, server_default=sa.text("'{}'"), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("trades", schema=SCHEMA)
    op.drop_table("deals", schema=SCHEMA)
    op.drop_table("orders", schema=SCHEMA)
    op.drop_table("currency_pairs", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
