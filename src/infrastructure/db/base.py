"""SQLAlchemy Declarative Base.

Инфраструктурный слой: доменный слой не должен зависеть от SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей."""


__all__ = ["Base"]
