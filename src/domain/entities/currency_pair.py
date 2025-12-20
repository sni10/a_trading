"""CurrencyPair entity с торговыми настройками."""

import time


class CurrencyPair:
    """Валютная пара с торговыми настройками и техническими параметрами биржи.

    Entity загружается из БД и содержит:
    - Идентификацию пары (symbol, base/quote валюты)
    - Торговые настройки для этой конкретной пары
    - Технические параметры биржи (шаги цены и количества)

    ВАЖНО: Параметры кэша (bar_window_size и т.д.) теперь глобальные
    и находятся в AppConfig.cache
    """

    def __init__(
        self,
        symbol: str,  # ОБЯЗАТЕЛЬНО! Без дефолта
        base_currency: str,
        quote_currency: str,
        # Trading settings (специфичны для каждой пары)
        deal_quota: float = 25.0,
        profit_markup: float = 1.5,
        deal_count: int = 3,
        order_life_time: int = 1,
        # Exchange technical params (получаются с биржи)
        min_step: float = 0.00001,
        price_step: float = 0.01,
        # Meta
        enabled: bool = True,
        pair_id: int | None = None,
        created_at: int | None = None,
        updated_at: int | None = None,
    ):
        """Создать валютную пару.

        Args:
            symbol: Символ пары на бирже (например "BTC/USDT") - ОБЯЗАТЕЛЬНО!
            base_currency: Базовая валюта (например "BTC")
            quote_currency: Котируемая валюта (например "USDT")

            # Trading settings (для этой конкретной пары):
            deal_quota: Размер сделки в quote валюте (например 25.0 USDT)
            profit_markup: Желаемый профит в % (например 1.5 = 1.5%)
            deal_count: Макс. количество одновременно открытых сделок
            order_life_time: Время жизни ордера в минутах до отмены

            # Exchange params (технические ограничения биржи):
            min_step: Минимальный шаг количества (lot size step)
            price_step: Минимальный шаг цены (ticker size)

            # Meta:
            enabled: Активна ли пара для торговли
            pair_id: ID в БД (если загружено из БД)
            created_at: Timestamp создания (ms)
            updated_at: Timestamp последнего обновления (ms)
        """
        # --- Core ---

        # Символ всегда в формате BASE/QUOTE. Это базовый инвариант,
        # вокруг которого строится вся конфигурация процесса
        # (один процесс = одна пара). На раннем этапе фиксируем только
        # наличие разделителя, без агрессивного парсинга.
        if "/" not in symbol:
            raise ValueError("CurrencyPair.symbol must be in 'BASE/QUOTE' format")

        self.pair_id = pair_id
        self.symbol = symbol
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.enabled = enabled

        # Trading settings
        self.deal_quota = deal_quota
        self.profit_markup = profit_markup
        self.deal_count = deal_count
        self.order_life_time = order_life_time

        # --- Exchange params ---

        # Биржевые шаги количества и цены должны быть строго > 0.
        # Это отражает контракт с провайдером прецизионов и защищает
        # от конфигураций, при которых расчёт объёма/цены теряет смысл.
        if min_step <= 0:
            raise ValueError("CurrencyPair.min_step must be > 0")
        if price_step <= 0:
            raise ValueError("CurrencyPair.price_step must be > 0")

        self.min_step = min_step
        self.price_step = price_step

        # Timestamps
        self.created_at = created_at or int(time.time() * 1000)
        self.updated_at = updated_at or int(time.time() * 1000)

    def __repr__(self) -> str:
        return (
            f"<CurrencyPair(symbol={self.symbol}, "
            f"deal_quota={self.deal_quota}, "
            f"profit_markup={self.profit_markup}%, "
            f"deal_count={self.deal_count})>"
        )

    def to_dict(self) -> dict:
        """Сериализовать в dict для БД."""
        return {
            "pair_id": self.pair_id,
            "symbol": self.symbol,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "enabled": self.enabled,
            # Trading
            "deal_quota": self.deal_quota,
            "profit_markup": self.profit_markup,
            "deal_count": self.deal_count,
            "order_life_time": self.order_life_time,
            # Exchange
            "min_step": self.min_step,
            "price_step": self.price_step,
            # Meta
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CurrencyPair":
        """Десериализовать из dict (из БД)."""
        return cls(**data)
