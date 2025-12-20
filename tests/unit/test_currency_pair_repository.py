"""Тесты для SQLAlchemy-репозитория валютных пар.

InMemory-репозиторий удалён: источник истины для пар — SQLAlchemy (SQLite/PostgreSQL).
Здесь проверяем базовый контракт ICurrencyPairRepository на sqlite :memory:.
"""

from __future__ import annotations

from src.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.infrastructure.db import SqlAlchemySessionFactory, build_engine, init_db
from src.infrastructure.repositories import SqlAlchemyCurrencyPairRepository


def _make_sqlite_memory_repo() -> SqlAlchemyCurrencyPairRepository:
    cfg = AppConfig()
    cfg.database.database_type = "sqlite"
    cfg.database.database_path = ":memory:"
    cfg.validate()

    engine = build_engine(cfg)
    init_db(engine)
    sf = SqlAlchemySessionFactory(engine)
    return SqlAlchemyCurrencyPairRepository(sf)


def test_upsert_and_get_by_symbol_roundtrip() -> None:
    repo = _make_sqlite_memory_repo()

    pair = CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT")
    saved = repo.upsert(pair)
    assert saved.pair_id is not None

    loaded = repo.get_by_symbol("BTC/USDT")
    assert loaded is not None
    assert loaded.symbol == "BTC/USDT"


def test_list_all_and_list_active_respect_enabled_flag() -> None:
    repo = _make_sqlite_memory_repo()

    repo.upsert(
        CurrencyPair(
            symbol="BTC/USDT",
            base_currency="BTC",
            quote_currency="USDT",
            enabled=True,
        )
    )
    repo.upsert(
        CurrencyPair(
            symbol="ETH/USDT",
            base_currency="ETH",
            quote_currency="USDT",
            enabled=False,
        )
    )

    all_pairs = repo.list_all()
    active_only = repo.list_active()

    assert [p.symbol for p in all_pairs] == ["BTC/USDT", "ETH/USDT"]
    assert [p.symbol for p in active_only] == ["BTC/USDT"]


def test_get_by_symbol_returns_none_for_unknown_symbol() -> None:
    repo = _make_sqlite_memory_repo()
    repo.upsert(CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT"))
    assert repo.get_by_symbol("UNKNOWN/USDT") is None

