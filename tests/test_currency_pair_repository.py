"""Тесты для in-memory репозитория валютных пар.

Фокус только на чистой логике:
* инициализация из списка символов;
* поиск по символу;
* фильтрация активных / отключённых пар;
* защита от дубликатов символов.
"""

from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.exchange_pair_metadata_provider import PairPrecisions
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


class _DummyPrecisionProvider:
    """Простой мок‑провайдер прецизионов для тестов.

    Имплементирует контракт ``get_precisions(symbol)`` и возвращает
    заранее подготовленные значения шагов цены и количества.
    """

    def __init__(self, data: dict[str, PairPrecisions]):
        self._data = data

    def get_precisions(self, symbol: str) -> PairPrecisions | None:  # pragma: no cover - тривиальная обёртка
        return self._data.get(symbol)


def test_from_symbols_overrides_precisions_from_provider() -> None:
    """При создании из символов прецизионы берутся из провайдера.

    Даже если у CurrencyPair есть значения по умолчанию, они должны
    быть перезаписаны актуальными данными биржи (провайдера).
    """

    provider = _DummyPrecisionProvider(
        {
            "BTC/USDT": {"min_step": 0.001, "price_step": 0.1},
            "ETH/USDT": {"min_step": 0.01, "price_step": 0.5},
        }
    )

    repo = InMemoryCurrencyPairRepository.from_symbols(
        ["BTC/USDT", "ETH/USDT"], precision_provider=provider
    )

    btc = repo.get_by_symbol("BTC/USDT")
    eth = repo.get_by_symbol("ETH/USDT")

    assert btc is not None
    assert eth is not None

    assert btc.min_step == 0.001
    assert btc.price_step == 0.1
    assert eth.min_step == 0.01
    assert eth.price_step == 0.5


def test_init_overrides_existing_precisions_from_provider() -> None:
    """Прецизионы из БД/объекта пары перекрываются данными биржи.

    Это отражает правило: даже если в БД уже записаны шаги цены и
    количества, при инициализации мы обновляем их актуальными
    значениями из объекта биржи/провайдера.
    """

    db_pair = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
        min_step=123.0,
        price_step=456.0,
    )

    provider = _DummyPrecisionProvider(
        {"BTC/USDT": {"min_step": 0.0001, "price_step": 0.01}}
    )

    repo = InMemoryCurrencyPairRepository([db_pair], precision_provider=provider)

    pair = repo.get_by_symbol("BTC/USDT")
    assert pair is not None
    assert pair.min_step == 0.0001
    assert pair.price_step == 0.01

