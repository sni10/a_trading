"""Фабрика репозиториев (application layer).

Здесь собирается инфраструктура (DB engine/sessions) и выбираются
конкретные реализации репозиториев для доменных интерфейсов.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

from src.config.config_schema import AppConfig
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.interfaces.deal_repository import IDealRepository
from src.domain.interfaces.order_repository import IOrderRepository
from src.domain.interfaces.trade_repository import ITradeRepository
from src.infrastructure.db import SqlAlchemySessionFactory, build_engine, init_db
from src.infrastructure.db.base import set_base_schema
from src.infrastructure.logging import log_stage
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


def _sync_sequences(engine: Engine, schema: str | None) -> None:
    """Синхронизировать PostgreSQL sequences с max(id) в таблицах.

    Предотвращает коллизию autoincrement PK с уже существующими
    строками (например, после ручного INSERT или восстановления дампа).
    Для SQLite не нужно — там autoincrement работает иначе.
    """
    prefix = f"{schema}." if schema else ""
    tables = [
        ("orders", "orders_id_seq"),
        ("deals", "deals_id_seq"),
        ("trades", "trades_id_seq"),
    ]
    with engine.connect() as conn:
        for table, seq in tables:
            try:
                conn.execute(text(
                    f"SELECT setval('{prefix}{seq}', "
                    f"GREATEST((SELECT COALESCE(MAX(id), 0) FROM {prefix}{table}), 1))"
                ))
            except Exception:
                pass  # Таблица/sequence не существует — пропускаем
        conn.commit()


def build_repositories(cfg: AppConfig) -> RepositoryBundle:
    """Собрать репозитории согласно AppConfig.database."""
    # Установить схему ДО создания engine (для корректной работы metadata)
    schema = None
    if cfg.database.database_type == "postgresql" and cfg.database.database_schema:
        schema = cfg.database.database_schema
        set_base_schema(schema)

    engine = build_engine(cfg)
    init_db(engine)

    # Для PostgreSQL: синхронизировать sequences с max(id)
    if cfg.database.database_type == "postgresql":
        _sync_sequences(engine, schema)
        log_stage("BOOT", "DB sequences синхронизированы с max(id)")

    sf = SqlAlchemySessionFactory(engine)

    return RepositoryBundle(
        pair_repository=SqlAlchemyCurrencyPairRepository(sf),
        order_repository=SqlAlchemyOrderRepository(sf),
        trade_repository=SqlAlchemyTradeRepository(sf),
        deal_repository=SqlAlchemyDealRepository(sf),
        session_factory=sf,
    )


__all__ = ["RepositoryBundle", "build_repositories"]
