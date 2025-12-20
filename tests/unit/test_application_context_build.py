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


class _FakeCurrencyPairRepository:
    def __init__(self, pairs: list[CurrencyPair]):
        self._pairs = list(pairs)
        self._by_symbol = {p.symbol: p for p in self._pairs}

    def list_all(self, include_disabled: bool = True) -> list[CurrencyPair]:
        if include_disabled:
            return list(self._pairs)
        return [p for p in self._pairs if p.enabled]

    def list_active(self) -> list[CurrencyPair]:
        return [p for p in self._pairs if p.enabled]

    def get_by_symbol(self, symbol: str) -> CurrencyPair | None:
        return self._by_symbol.get(symbol)

    def upsert(self, pair: CurrencyPair) -> CurrencyPair:
        existing = self._by_symbol.get(pair.symbol)
        if existing is None:
            self._pairs.append(pair)
            self._by_symbol[pair.symbol] = pair
            return pair

        existing.base_currency = pair.base_currency
        existing.quote_currency = pair.quote_currency
        existing.deal_quota = pair.deal_quota
        existing.profit_markup = pair.profit_markup
        existing.deal_count = pair.deal_count
        existing.order_life_time = pair.order_life_time
        existing.min_step = pair.min_step
        existing.price_step = pair.price_step
        existing.enabled = pair.enabled
        existing.updated_at = pair.updated_at
        return existing


def test_build_context_uses_repository_and_creates_caches() -> None:
    # Тест проверяет, что build_context корректно обогащает
    # базовый dict-контекст структурами вокруг переданной пары.
    # ВАЖНО: символ теперь НЕ в AppConfig, а в CurrencyPair из репозитория.
    cfg = AppConfig()
    base_ctx = init_context(cfg)

    # Создаем репозиторий с одной парой
    pair_repo = _FakeCurrencyPairRepository(
        [CurrencyPair(symbol="BTC/USDT", base_currency="BTC", quote_currency="USDT")]
    )

    ctx = build_context(cfg, base_ctx, pair_repository=pair_repo)

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
    repo = _FakeCurrencyPairRepository([custom_pair])

    # build_context работает с внешним репозиторием, который
    # может содержать несколько пар. Список активных берётся из репозитория.
    # AppConfig содержит только ГЛОБАЛЬНЫЕ настройки (не содержит symbol).
    cfg = AppConfig()
    base_ctx = init_context(cfg)

    ctx = build_context(cfg, base_ctx, pair_repository=repo)

    assert ctx["pair_repository"] is repo
    assert set(ctx["pairs"].keys()) == {"BTC/USDT"}

