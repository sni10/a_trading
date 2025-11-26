"""Тесты для in-memory репозитория валютных пар.

Фокус только на чистой логике:
* инициализация из списка символов;
* поиск по символу;
* фильтрация активных / отключённых пар;
* защита от дубликатов символов.
"""

from src.domain.entities.currency_pair import CurrencyPair
from src.infrastructure.repositories import InMemoryCurrencyPairRepository


def test_from_symbols_creates_pairs_and_all_are_active() -> None:
    repo = InMemoryCurrencyPairRepository.from_symbols(["BTC/USDT", "ETH/USDT"])

    active = repo.list_active()
    symbols = {p.symbol for p in active}

    assert symbols == {"BTC/USDT", "ETH/USDT"}

    btc = repo.get_by_symbol("BTC/USDT")
    eth = repo.get_by_symbol("ETH/USDT")
    assert btc is not None
    assert eth is not None
    assert btc.base_currency == "BTC"
    assert btc.quote_currency == "USDT"


def test_list_all_respects_enabled_flag() -> None:
    enabled_pair = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
        enabled=True,
    )
    disabled_pair = CurrencyPair(
        symbol="ETH/USDT",
        base_currency="ETH",
        quote_currency="USDT",
        enabled=False,
    )

    repo = InMemoryCurrencyPairRepository([enabled_pair, disabled_pair])

    all_pairs = repo.list_all()
    active_only = repo.list_all(include_disabled=False)

    assert {p.symbol for p in all_pairs} == {"BTC/USDT", "ETH/USDT"}
    assert {p.symbol for p in active_only} == {"BTC/USDT"}


def test_duplicate_symbols_raise_value_error() -> None:
    p1 = CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT")
    p2 = CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT")

    try:
        InMemoryCurrencyPairRepository([p1, p2])
    except ValueError as exc:
        assert "Duplicate currency pair symbol" in str(exc)
    else:  # pragma: no cover - защитный блок
        raise AssertionError("Expected ValueError for duplicate symbols")


def test_get_by_symbol_returns_none_for_unknown_symbol() -> None:
    repo = InMemoryCurrencyPairRepository.from_symbols(["BTC/USDT"])

    assert repo.get_by_symbol("UNKNOWN/USDT") is None

