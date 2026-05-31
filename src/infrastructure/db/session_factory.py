"""Фабрика сессий SQLAlchemy.

Репозитории получают sessionmaker и открывают/закрывают сессии локально.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


class SqlAlchemySessionFactory:
    """Тонкая обёртка над sessionmaker для удобного DI."""

    def __init__(self, engine: Engine) -> None:
        self._maker = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Контекст-менеджер: session + commit/rollback."""

        session: Session = self._maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def make_session(self) -> Session:
        """Создать сессию без контекст-менеджера (редко нужно)."""

        return self._maker()


__all__ = ["SqlAlchemySessionFactory"]
