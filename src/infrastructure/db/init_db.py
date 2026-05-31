"""Инициализация схемы БД.

В production миграции применяются через Alembic (alembic upgrade head).
create_all() оставлен для тестов, где используется in-memory или
одноразовая БД без необходимости миграционной истории.
"""

from __future__ import annotations

from sqlalchemy import Engine

from src.infrastructure.db.base import Base

# ВАЖНО: чтобы Base.metadata знала о таблицах, модели должны быть импортированы.
# Импортируем модули моделей явно, избегая циклических импортов через db.__init__.
from src.infrastructure.db.models.currency_pair_model import CurrencyPairModel  # noqa: F401
from src.infrastructure.db.models.deal_model import DealModel  # noqa: F401
from src.infrastructure.db.models.order_model import OrderModel  # noqa: F401
from src.infrastructure.db.models.trade_model import TradeModel  # noqa: F401


def init_db(engine: Engine) -> None:
    """Создать таблицы, если они отсутствуют."""

    Base.metadata.create_all(engine)


__all__ = ["init_db"]
