"""SQLAlchemy Declarative Base.

Инфраструктурный слой: доменный слой не должен зависеть от SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей.

    Схема задаётся через metadata.schema и может быть переопределена
    при создании engine через функцию set_base_schema().
    """

    metadata = MetaData()


def set_base_schema(schema: str | None) -> None:
    """Установить схему для всех таблиц в Base.metadata.

    Должна вызываться ДО создания engine/инициализации БД.
    Для PostgreSQL позволяет использовать кастомные схемы.
    Для SQLite игнорируется.
    """
    if schema:
        Base.metadata.schema = schema


__all__ = ["Base", "set_base_schema"]
