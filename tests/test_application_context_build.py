"""Тесты высокоуровневой сборки контекста (build_context).

Проверяем, что:
* пары и кэши создаются на основе репозитория CurrencyPair;
* в контексте появляются ожидаемые ключи;
* можно подменить репозиторий снаружи (для будущих use-case/БД).
"""

from src.application.context import build_context
from src.config.config import AppConfig
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.interfaces.cache import IIndicatorStore, IMarketCache
from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.services.context.state import init_context
from src.infrastructure.repositories import InMemoryCurrencyPairRepository


def test_build_context_uses_repository_and_creates_caches() -> None:
    # В актуальной версии прототипа один процесс обслуживает одну пару.
    # AppConfig больше не поддерживает список symbols, только одиночный
    # ``symbol``. Тест проверяет, что build_context корректно обогащает
    # базовый dict-контекст структурами вокруг этой пары.
    cfg = AppConfig(symbol="BTC/USDT")
    base_ctx = init_context(cfg)

    ctx = build_context(cfg, base_ctx)

    # Базовые разделы
    assert "pairs" in ctx
    assert "market_caches" in ctx
    assert "indicator_stores" in ctx
    assert "pair_repository" in ctx

    pairs = ctx["pairs"]
    market_caches = ctx["market_caches"]
    indicator_stores = ctx["indicator_stores"]
    repo = ctx["pair_repository"]

    assert isinstance(pairs["BTC/USDT"], CurrencyPair)
    assert isinstance(market_caches["BTC/USDT"], IMarketCache)
    assert isinstance(indicator_stores["BTC/USDT"], IIndicatorStore)
    assert isinstance(repo, ICurrencyPairRepository)

    # Репозиторий и pairs в контексте должны ссылаться на одни и те же
    # объекты CurrencyPair (по symbol).
    active_pairs = {p.symbol: p for p in repo.list_active()}
    for symbol, pair in active_pairs.items():
        assert ctx["pairs"][symbol] is pair


def test_build_context_accepts_external_repository() -> None:
    # Собираем репозиторий вручную, с одной парой.
    custom_pair = CurrencyPair(
        symbol="BTC/USDT",
        base_currency="BTC",
        quote_currency="USDT",
    )
    repo = InMemoryCurrencyPairRepository([custom_pair])

    # AppConfig больше не принимает список symbols, но build_context
    # по-прежнему обязан уметь работать с внешним репозиторием, который
    # может содержать несколько пар. На уровне конфига фиксируем одну
    # базовую пару, а список активных берётся из репозитория.
    cfg = AppConfig(symbol="BTC/USDT")
    base_ctx = init_context(cfg)

    ctx = build_context(cfg, base_ctx, pair_repository=repo)

    assert ctx["pair_repository"] is repo
    assert set(ctx["pairs"].keys()) == {"BTC/USDT"}

