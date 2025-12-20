"""Фабрика engine/URL для SQLAlchemy.

ВАЖНО:
- Никаких raw SQL.
- Выбор backend'а делается по AppConfig.database.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config.config_schema import AppConfig


def _sqlite_url(database_path: str) -> str:
    # SQLAlchemy ожидает URL с forward-slashes.
    if database_path.strip() == ":memory:":
        return "sqlite+pysqlite:///:memory:"

    path = Path(database_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{path.as_posix()}"


def _postgresql_url(database_url: str) -> str:
    # Нормализуем драйвер под psycopg (psycopg3).
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def build_database_url(cfg: AppConfig) -> str:
    """Построить SQLAlchemy URL по AppConfig."""

    db = cfg.database
    if db.database_type == "sqlite":
        return _sqlite_url(db.database_path)
    return _postgresql_url(db.database_url or "")


def build_engine(cfg: AppConfig) -> Engine:
    """Создать SQLAlchemy Engine по AppConfig."""

    url = build_database_url(cfg)

    # pool_pre_ping полезен для postgres при долгом uptime.
    # Для sqlite лишнего вреда не делает.
    return create_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


__all__ = ["build_database_url", "build_engine"]
