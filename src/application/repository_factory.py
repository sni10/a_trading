"""Фабрика репозиториев (application layer).

Здесь собирается инфраструктура (DB engine/sessions) и выбираются
конкретные реализации репозиториев для доменных интерфейсов.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config.config_schema import AppConfig
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.interfaces.deal_repository import IDealRepository
from src.domain.interfaces.order_repository import IOrderRepository
from src.domain.interfaces.trade_repository import ITradeRepository
from src.infrastructure.db import SqlAlchemySessionFactory, build_engine, init_db
from src.infrastructure.db.base import set_base_schema
from src.infrastructure.repositories import (
    SqlAlchemyCurrencyPairRepository,
    SqlAlchemyDealRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyTradeRepository,
)


@dataclass(frozen=True)
class RepositoryBundle:
    """Набор репозиториев, собранных для текущего запуска."""

    pair_repository: ICurrencyPairRepository
    order_repository: IOrderRepository
    trade_repository: ITradeRepository
    deal_repository: IDealRepository

    # Иногда полезно для low-level задач (инициализация, транзакции),
    # но доменный слой этого не видит.
    session_factory: SqlAlchemySessionFactory


def build_repositories(cfg: AppConfig) -> RepositoryBundle:
    """Собрать репозитории согласно AppConfig.database.

    Сейчас обе опции (sqlite/postgresql) используют один стек SQLAlchemy.

    Для PostgreSQL можно задать схему через DB_SCHEMA. Схема должна
    существовать в БД (создаётся администратором или миграциями).
    """
    # Установить схему ДО создания engine (для корректной работы metadata)
    if cfg.database.database_type == "postgresql" and cfg.database.database_schema:
        set_base_schema(cfg.database.database_schema)

    engine = build_engine(cfg)
    init_db(engine)
    sf = SqlAlchemySessionFactory(engine)

    return RepositoryBundle(
        pair_repository=SqlAlchemyCurrencyPairRepository(sf),
        order_repository=SqlAlchemyOrderRepository(sf),
        trade_repository=SqlAlchemyTradeRepository(sf),
        deal_repository=SqlAlchemyDealRepository(sf),
        session_factory=sf,
    )


__all__ = ["RepositoryBundle", "build_repositories"]
