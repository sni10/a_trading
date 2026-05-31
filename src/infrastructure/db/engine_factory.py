"""Фабрика engine/URL для SQLAlchemy.

ВАЖНО:
- Никаких raw SQL.
- ТОЛЬКО PostgreSQL, SQLite удалён.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from src.config.config_schema import AppConfig


def build_database_url(cfg: AppConfig) -> str:
    """Построить SQLAlchemy URL по AppConfig.

    ТОЛЬКО PostgreSQL. SQLite не поддерживается.
    """
    db = cfg.database

    if db.database_type != "postgresql":
        raise ValueError(f"Unsupported database type: {db.database_type}. Only 'postgresql' is supported.")

    if not db.database_url:
        raise ValueError("DATABASE_URL is required for PostgreSQL")

    # По умолчанию SQLAlchemy использует psycopg2 для postgresql://
    return db.database_url


def build_engine(cfg: AppConfig) -> Engine:
    """Создать SQLAlchemy Engine по AppConfig.

    Для PostgreSQL можно задать кастомную схему через DB_SCHEMA.
    Для SQLite схема игнорируется.
    """
    url = build_database_url(cfg)

    # Для PostgreSQL можно задать search_path через connect_args
    connect_args = {}
    if cfg.database.database_type == "postgresql" and cfg.database.database_schema:
        connect_args["options"] = f"-c search_path={cfg.database.database_schema},public"

    # pool_pre_ping полезен для postgres при долгом uptime.
    # Для sqlite лишнего вреда не делает.
    return create_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


__all__ = ["build_database_url", "build_engine"]
