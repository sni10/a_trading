"""Alembic environment — автогенерация миграций по ORM-моделям."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from src.infrastructure.db.base import Base

# Импорт всех моделей, чтобы Base.metadata знала о таблицах
from src.infrastructure.db.models.currency_pair_model import CurrencyPairModel  # noqa: F401
from src.infrastructure.db.models.deal_model import DealModel  # noqa: F401
from src.infrastructure.db.models.order_model import OrderModel  # noqa: F401
from src.infrastructure.db.models.trade_model import TradeModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Схема PostgreSQL для всех таблиц
DB_SCHEMA = os.environ.get("DB_SCHEMA", "main")

# Переопределяем URL из переменной окружения если задана
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Генерация SQL без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=DB_SCHEMA,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Применение миграций с подключением к БД."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Создаём схему если не существует и ставим search_path
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        connection.execute(text(f"SET search_path TO {DB_SCHEMA}, public"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=DB_SCHEMA,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
