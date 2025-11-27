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

    # Cache settings (defaults)
    assert pair.bar_timeframe == "1m"
    assert pair.bar_window_size == 10000
    assert pair.orderbook_depth == 2000
    assert pair.trades_history_size == 5000
    assert pair.indicator_window_size == 10000

    # Estimate cache size (raw data ~1.8MB + indicators ~7.15MB)
    cache_mb = pair.estimate_cache_size_mb()
    assert 8.0 <= cache_mb <= 10.0, f"Expected cache ~9MB, got {cache_mb:.2f}MB"


def test_currency_pair_custom_settings():
    """Тест создания пары с кастомными настройками из config.json."""
    pair = CurrencyPair(
        symbol="ETH/USDT",
        base_currency="ETH",
        quote_currency="USDT",
        # From bad_example config.json
        deal_quota=25.0,
        profit_markup=1.5,
        deal_count=3,
        order_life_time=1,
        min_step=0.0001,
        price_step=0.01,
        # Custom cache
        bar_timeframe="5m",
        bar_window_size=5000,
        orderbook_depth=1000,
        trades_history_size=2000,
    )

    assert pair.symbol == "ETH/USDT"
    assert pair.bar_timeframe == "5m"
    assert pair.bar_window_size == 5000
    assert pair.orderbook_depth == 1000
    assert pair.trades_history_size == 2000


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
    assert restored.bar_window_size == original.bar_window_size


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
    assert "cache≈" in repr_str
    assert "MB" in repr_str
