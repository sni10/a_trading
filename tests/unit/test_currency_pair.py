"""Unit tests for CurrencyPair entity."""

from src.domain.entities import CurrencyPair


def test_currency_pair_creation_with_defaults():
    """Тест создания пары с дефолтными настройками."""
    pair = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
    )

    # Core fields
    assert pair.symbol == "BTC/USDT"
    assert pair.base_currency == "BTC"
    assert pair.quote_currency == "USDT"
    assert pair.enabled is True

    # Trading settings (defaults)
    assert pair.deal_quota == 25.0
    assert pair.profit_markup == 1.5
    assert pair.deal_count == 3
    assert pair.order_life_time == 1

    # Cache settings УДАЛЕНЫ - теперь они в AppConfig.cache (глобально)


def test_currency_pair_custom_settings():
    """Тест создания пары с кастомными настройками из config.json."""
    pair = CurrencyPair(
        symbol="ETH/USDT",
        base_currency="ETH",
        quote_currency="USDT",
        # From bad_example config.json
        deal_quota=50.0,
        profit_markup=2.0,
        deal_count=5,
        order_life_time=2,
        min_step=0.0001,
        price_step=0.01,
    )

    assert pair.symbol == "ETH/USDT"
    assert pair.deal_quota == 50.0
    assert pair.profit_markup == 2.0
    assert pair.deal_count == 5
    assert pair.order_life_time == 2
    assert pair.min_step == 0.0001
    assert pair.price_step == 0.01


def test_currency_pair_serialization():
    """Тест сериализации/десериализации для БД."""
    original = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
        deal_quota=50.0,
        profit_markup=2.0,
    )

    # Serialize
    data = original.to_dict()
    assert data["symbol"] == "BTC/USDT"
    assert data["deal_quota"] == 50.0
    assert data["profit_markup"] == 2.0

    # Deserialize
    restored = CurrencyPair.from_dict(data)
    assert restored.symbol == original.symbol
    assert restored.deal_quota == original.deal_quota
    assert restored.profit_markup == original.profit_markup
    # bar_window_size больше не в CurrencyPair


def test_currency_pair_repr():
    """Тест строкового представления."""
    pair = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
    )

    repr_str = repr(pair)
    assert "BTC/USDT" in repr_str
    assert "deal_quota=25.0" in repr_str
    assert "profit_markup=1.5%" in repr_str
    assert "deal_count=3" in repr_str
    # cache≈ больше не в repr (кэш в глобальном конфиге)
