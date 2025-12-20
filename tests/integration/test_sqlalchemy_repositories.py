from __future__ import annotations

import time

from src.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.entities.trade import Trade
from src.infrastructure.db import SqlAlchemySessionFactory, build_engine, init_db
from src.infrastructure.repositories import (
    SqlAlchemyCurrencyPairRepository,
    SqlAlchemyDealRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyTradeRepository,
)


def _make_sqlite_memory_cfg() -> AppConfig:
    cfg = AppConfig()
    cfg.database.database_type = "sqlite"
    cfg.database.database_path = ":memory:"
    cfg.validate()
    return cfg


def test_sqlalchemy_currency_pair_repository_crud() -> None:
    cfg = _make_sqlite_memory_cfg()
    engine = build_engine(cfg)
    init_db(engine)
    sf = SqlAlchemySessionFactory(engine)

    repo = SqlAlchemyCurrencyPairRepository(sf)

    pair = CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT")
    saved = repo.upsert(pair)

    assert saved.pair_id is not None
    assert saved.symbol == "BTC/USDT"

    loaded = repo.get_by_symbol("BTC/USDT")
    assert loaded is not None
    assert loaded.symbol == "BTC/USDT"

    active = repo.list_active()
    assert [p.symbol for p in active] == ["BTC/USDT"]


def test_sqlalchemy_order_trade_deal_repositories_roundtrip() -> None:
    cfg = _make_sqlite_memory_cfg()
    engine = build_engine(cfg)
    init_db(engine)
    sf = SqlAlchemySessionFactory(engine)

    order_repo = SqlAlchemyOrderRepository(sf)
    trade_repo = SqlAlchemyTradeRepository(sf)
    deal_repo = SqlAlchemyDealRepository(sf)

    ts = int(time.time() * 1000)

    order = Order(
        id="order_1",
        symbol="BTC/USDT",
        timestamp=ts,
        datetime="2025-01-01T00:00:00.000Z",
        status="open",
        side="buy",
        type="limit",
        amount=0.01,
        price=50000.0,
        filled=0.0,
        remaining=0.01,
        cost=0.0,
        client_order_id="client_1",
    )
    order_repo.upsert(order)

    loaded_order = order_repo.get_by_id("order_1")
    assert loaded_order is not None
    assert loaded_order.id == "order_1"
    assert loaded_order.symbol == "BTC/USDT"

    trade = Trade(
        id="trade_1",
        order="order_1",
        timestamp=ts,
        datetime="2025-01-01T00:00:01.000Z",
        symbol="BTC/USDT",
        side="buy",
        price=50000.0,
        amount=0.01,
        cost=500.0,
    )
    trade_repo.upsert(trade)

    trades = trade_repo.list_by_order_id("order_1")
    assert [t.id for t in trades] == ["trade_1"]

    deal = Deal(
        id=0,
        symbol="BTC/USDT",
        status=Deal.STATUS_PENDING,
        created_at=ts,
        buy_order=order,
        metadata={"source": "test"},
    )
    saved_deal = deal_repo.add(deal)
    assert saved_deal.id > 0
    assert saved_deal.buy_order is not None
    assert saved_deal.buy_order.id == "order_1"

    loaded_deal = deal_repo.get_by_id(saved_deal.id)
    assert loaded_deal is not None
    assert loaded_deal.symbol == "BTC/USDT"
    assert loaded_deal.buy_order is not None
    assert loaded_deal.buy_order.id == "order_1"

    active_deals = deal_repo.list_active_by_symbol("BTC/USDT")
    assert len(active_deals) == 1
    assert active_deals[0].id == saved_deal.id
