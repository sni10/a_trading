from __future__ import annotations

from src.config.environment import Config
from src.domain.entities.currency_pair import CurrencyPair
from src.infrastructure.cache.in_memory import InMemoryIndicatorStore


def test_indicator_store_uses_intervals_from_config() -> None:
    pair = CurrencyPair("ETH/USDT", "ETH", "USDT", indicator_window_size=5)
    cfg = Config(
        indicator_fast_interval=1,
        indicator_medium_interval=3,
        indicator_heavy_interval=5,
    )

    store = InMemoryIndicatorStore(pair, cfg)

    assert store.fast_interval == 1
    assert store.medium_interval == 3
    assert store.heavy_interval == 5

    # Простая проверка политики обновления
    assert store.should_update_fast(1)
    assert store.should_update_fast(2)
    assert not store.should_update_medium(2)
    assert store.should_update_medium(3)
    assert not store.should_update_heavy(4)
    assert store.should_update_heavy(5)


def test_indicator_store_respects_indicator_window_size() -> None:
    pair = CurrencyPair("ETH/USDT", "ETH", "USDT", indicator_window_size=3)
    cfg = Config()
    store = InMemoryIndicatorStore(pair, cfg)

    # Имитируем запись значений индикатора в fast_history
    for i in range(10):
        store.fast_history.append(float(i))

    assert len(store.fast_history) == 3
    assert list(store.fast_history) == [7.0, 8.0, 9.0]
