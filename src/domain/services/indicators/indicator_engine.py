from typing import Any, Dict

from src.domain.interfaces.cache import IIndicatorStore
from src.domain.interfaces.logger import ILogger
from src.domain.services.indicators.fast_indicators import calculate_fast_indicators
from src.domain.services.indicators.heavy_indicators import calculate_heavy_indicators
from src.domain.services.indicators.indicator_snapshot import create_indicator_snapshot
from src.domain.services.indicators.medium_indicators import calculate_medium_indicators
from src.domain.services.indicators.price_history_manager import PriceHistoryManager
from src.domain.services.ticker.ticker_source import Ticker


class IndicatorEngine:
    """Поставщик индикаторов поверх истории тикеров.

    Работает в терминах доменного :class:`Ticker` и трёх слоёв
    триггеров ``fast/medium/heavy`` через :class:`IIndicatorStore`.

    Основная точка входа – метод :meth:`on_ticker`, который:

    * обновляет историю цен ``context["price_history"][symbol]``;
    * по триггерам считает простые SMA и дополнительные fast‑индикаторы;
    * сохраняет снимок через :func:`record_indicators` и возвращает его.
    """

    def __init__(self, logger: ILogger | None = None) -> None:
        self._logger = logger
        self._price_history = PriceHistoryManager(max_history_length=500)

    def on_ticker(
        self,
        context: Dict[str, Any],
        *,
        ticker_id: int,
        symbol: str,
        ticker: Ticker,
    ) -> Dict[str, Any]:
        """Обработать тикер и вернуть snapshot индикаторов.

        Метод оставлен максимально тонким: он лишь обновляет историю,
        извлекает ``IndicatorStore`` для символа, делегирует расчёт
        индикаторов вспомогательному методу и собирает snapshot через
        :func:`create_indicator_snapshot`.
        """

        last_price = float(ticker["last"])

        if self._logger:
            self._logger.log_info(
                f"📊 [IND] Расчёт индикаторов по тикеру | ticker_id: {ticker_id} | symbol: {symbol} | price: {last_price:.8f}"
            )

        # Обновление истории цен и тикеров через менеджер
        self._price_history.update_history(context, symbol=symbol, ticker=ticker)
        history_list = self._price_history.get_price_history(context, symbol)

        store = self._get_indicator_store(context, symbol)
        indicators: Dict[str, Any] = {}
        if store is not None:
            indicators = self._calculate_layer_indicators(
                store=store,
                history_list=history_list,
                ticker_id=ticker_id,
                ticker=ticker,
                last_price=last_price,
            )

        # --- Создание snapshot с backward compatibility ---
        return create_indicator_snapshot(
            context=context,
            symbol=symbol,
            ticker_id=ticker_id,
            last_price=last_price,
            indicators=indicators,
            logger=self._logger,
        )

    def _get_indicator_store(self, context: Dict[str, Any], symbol: str) -> IIndicatorStore | None:
        """Вернуть :class:`IIndicatorStore` для символа, если он настроен.

        Вынесено в отдельный метод для упрощения :meth:`on_ticker` и
        возможного переиспользования в будущих сценариях.
        """

        stores = context.get("indicator_stores") or {}
        store = stores.get(symbol)
        return store if isinstance(store, IIndicatorStore) else None

    def _calculate_layer_indicators(
        self,
        *,
        store: IIndicatorStore,
        history_list: list[float],
        ticker_id: int,
        ticker: Ticker,
        last_price: float,
    ) -> Dict[str, Any]:
        """Рассчитать индикаторы fast/medium/heavy слоёв.

        Внутри используются отдельные модули ``fast_indicators``,
        ``medium_indicators`` и ``heavy_indicators``; метод отвечает только
        за выбор триггеров и обновление per-layer истории в store.
        """

        indicators: Dict[str, Any] = {}

        # Окна для примера fast/medium/heavy. В дальнейшем можно вынести
        # в конфиг/пару, не меняя общий каркас.
        fast_window = 5
        medium_window = 20
        heavy_window = 100

        # --- FAST слой ---
        if store.should_update_fast(ticker_id):
            fast_indicators = calculate_fast_indicators(
                ticker=ticker,
                history_list=history_list,
                fast_window=fast_window,
            )
            indicators.update(fast_indicators)

            # Сохраняем «сырые» значения цены в истории fast‑слоя.
            store.fast_history.append(last_price)  # type: ignore[attr-defined]

        # --- MEDIUM слой ---
        if store.should_update_medium(ticker_id):
            medium_indicators = calculate_medium_indicators(
                history_list=history_list,
                medium_window=medium_window,
                logger=self._logger,
            )
            indicators.update(medium_indicators)

            # История medium‑слоя для возможных альтернативных расчётов в будущем.
            store.medium_history.append(last_price)  # type: ignore[attr-defined]

        # --- HEAVY слой ---
        if store.should_update_heavy(ticker_id):
            heavy_indicators = calculate_heavy_indicators(
                history_list=history_list,
                heavy_window=heavy_window,
                logger=self._logger,
            )
            indicators.update(heavy_indicators)

            # История heavy‑слоя.
            store.heavy_history.append(last_price)  # type: ignore[attr-defined]

        return indicators


def compute_indicators(
    context: Dict[str, Any],
    *,
    ticker_id: int,
    symbol: str,
    price: float,
    logger: ILogger | None = None,
) -> Dict[str, Any]:
    """Фасад для расчёта индикаторов, совместимый с существующим API.

    Внешний контракт (сигнатура и базовый формат snapshot) не меняется,
    но фактическая работа делегирована :class:`IndicatorEngine`, который
    оперирует доменным :class:`Ticker`.

    Для синхронного демо‑конвейера мы строим упрощённый тикер поверх
    текущей цены: все OHLC‑поля приравниваются к ``price``, bid/ask – к
    ``price``, объёмы – к нулю. В async‑конвейере вместо этого будет
    использоваться реальный тикер из :class:`TickSource`.
    """

    ts = context.get("market", {}).get(symbol, {}).get("ts")

    # Упрощённый тикер: один и тот же price во всех ценовых полях,
    # объёмы считаем неизвестными (0.0). Этого достаточно для текущих
    # SMA и демонстрационных индикаторов.
    ticker: Ticker = {
        "symbol": symbol,
        "timestamp": int(ts) if ts is not None else 0,
        "datetime": "",
        "last": float(price),
        "open": float(price),
        "high": float(price),
        "low": float(price),
        "close": float(price),
        "bid": float(price),
        "ask": float(price),
        "baseVolume": 0.0,
        "quoteVolume": 0.0,
    }

    engine = IndicatorEngine(logger=logger)
    return engine.on_ticker(
        context,
        ticker_id=ticker_id,
        symbol=symbol,
        ticker=ticker,
    )

