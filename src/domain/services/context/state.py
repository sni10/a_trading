from typing import Dict, Any, List

from src.config.config import AppConfig
from src.domain.interfaces.cache import IMarketCache
from src.infrastructure.logging.logging_setup import log_stage


def init_context(config: AppConfig) -> Dict[str, Any]:
    """Создать in-memory контекст с обязательными разделами.

    На вход принимает типизированный :class:`AppConfig` и кладёт его
    целиком в раздел ``context["config"]`` без преобразования в dict.

    Логика контекста остаётся простой: только разделы in-memory состояния,
    без доступа к сети/БД.
    """

    ctx: Dict[str, Any] = {
        "config": config,
        "market": {},
        "indicators": {},  # снимки индикаторов по инструментам (последний)
        "positions": {},
        "orders": {},
        "risk": {},
        "metrics": {"ticks": 0},
        # История индикаторов по каждому инструменту
        "indicators_history": {},
        # Решения/намерения стратегий и оркестратора.
        # Храним как последний срез по инструменту и простую историю,
        # чтобы в будущем можно было прозрачно заменить backend на Redis
        # или БД, не меняя бизнес‑код конвейера.
        "intents": {},
        "decisions": {},
        "intents_history": {},
        "decisions_history": {},
    }
    log_stage(
        "BOOT",
        "Инициализация базового in‑memory контекста",
        sections=sorted(ctx.keys()),
    )
    return ctx


def update_market_state(
    context: Dict[str, Any], *, symbol: str, price: float, ts: int
) -> None:
    """Обновить разделы ``market`` и ``market_caches`` по простому тику.

    Используется синхронным демо‑конвейером: тик описывается минимальным
    набором полей (``symbol``, ``price``, ``ts``). Функция не делает
    внешнего I/O и работает только с in‑memory структурами контекста.
    """

    # Высокоуровневый срез рынка для стратегий/оркестратора.
    market = context.setdefault("market", {})
    market[symbol] = {"last_price": price, "ts": ts}

    # Если в контексте есть кэш рынка для этой пары, обновляем и его.
    caches = context.get("market_caches") or {}
    cache = caches.get(symbol)
    if isinstance(cache, IMarketCache):
        ticker = {
            "symbol": symbol,
            "last": price,
            "timestamp": ts,
        }
        cache.update_ticker(ticker)

    log_stage(
        "FEEDS",
        "Обновление market‑state по тику",
        symbol=symbol,
        price=price,
        ts=ts,
        has_cache=isinstance(cache, IMarketCache),
    )


def update_metrics(context: Dict[str, Any], tick_id: int) -> None:
    m = context.get("metrics", {})
    m["ticks"] = tick_id
    context["metrics"] = m
    log_stage("STATE", "Обновление метрик состояния", tick_id=tick_id)


def _get_window_size_for_symbol(context: Dict[str, Any], symbol: str, *, default: int = 1000) -> int:
    """Вспомогательно: взять размер окна по паре, если она есть в контексте.

    Сейчас используем ``CurrencyPair.indicator_window_size`` как единый
    лимит для историй индикаторов, intents и decisions. Это позволяет
    контролировать объём in‑memory state и в будущем заменить хранение
    на Redis/БД без изменения вызывающего кода.
    """

    pairs = context.get("pairs") or {}
    pair = pairs.get(symbol)
    return getattr(pair, "indicator_window_size", default) if pair is not None else default


def _append_with_window(sequence: List[Any], item: Any, *, maxlen: int) -> bool:
    """Добавить элемент в список с обрезкой по ``maxlen`` с начала.

    Возвращает ``True``, если при добавлении пришлось обрезать голову
    списка (старые элементы вытеснены).
    """

    sequence.append(item)
    truncated = False
    if len(sequence) > maxlen:
        # откусываем только из начала, чтобы сохранить порядок последних
        del sequence[0 : len(sequence) - maxlen]
        truncated = True
    return truncated


def record_indicators(
    context: Dict[str, Any], *, symbol: str, snapshot: Dict[str, Any]
) -> None:
    """Сохранить снимок индикаторов в контекст и его историю.

    * ``context["indicators"][symbol]`` – последний снимок;
    * ``context["indicators_history"][symbol]`` – окно последних N
      снимков, где ``N == CurrencyPair.indicator_window_size``.

    История живёт в простом dict/list, чтобы в будущем можно было
    прозрачно заменить backend (например, на Redis), оставив контракт
    этой функции прежним.
    """

    indicators = context.setdefault("indicators", {})
    indicators[symbol] = snapshot

    history_all = context.setdefault("indicators_history", {})
    history_for_symbol: List[Dict[str, Any]] = history_all.setdefault(symbol, [])

    window = _get_window_size_for_symbol(context, symbol)
    truncated = _append_with_window(history_for_symbol, snapshot, maxlen=window)

    log_stage(
        "IND",
        "Снимок индикаторов записан в историю",
        symbol=symbol,
        history_len=len(history_for_symbol),
        window=window,
        truncated=truncated,
    )


def record_intents(
    context: Dict[str, Any], *, symbol: str, intents: List[Dict[str, Any]]
) -> None:
    """Сохранить intents стратегий в последний срез и историю.

    Формат intents не фиксируется жёстко: это список произвольных dict,
    но на уровне оркестратора ожидаются как минимум поля ``action``,
    ``reason`` и ``params``. В контексте держим:

    * ``context["intents"][symbol]`` – последний список intents;
    * ``context["intents_history"][symbol]`` – окно последних наборов
      intents по тикам, размер окна берётся из настроек пары.
    """

    current = context.setdefault("intents", {})
    current[symbol] = intents

    history_all = context.setdefault("intents_history", {})
    history_for_symbol: List[List[Dict[str, Any]]] = history_all.setdefault(symbol, [])

    window = _get_window_size_for_symbol(context, symbol)
    truncated = _append_with_window(history_for_symbol, intents, maxlen=window)

    log_stage(
        "STATE",
        "Intents сохранены в истории",
        symbol=symbol,
        intents_count=len(intents),
        history_len=len(history_for_symbol),
        window=window,
        truncated=truncated,
    )


def record_decision(
    context: Dict[str, Any], *, symbol: str, decision: Dict[str, Any]
) -> None:
    """Сохранить финальное решение оркестратора в срез и историю.

    * ``context["decisions"][symbol]`` – последнее решение;
    * ``context["decisions_history"][symbol]`` – окно последних N
      решений, N определяется настройками пары.
    """

    current = context.setdefault("decisions", {})
    current[symbol] = decision

    history_all = context.setdefault("decisions_history", {})
    history_for_symbol: List[Dict[str, Any]] = history_all.setdefault(symbol, [])

    window = _get_window_size_for_symbol(context, symbol)
    truncated = _append_with_window(history_for_symbol, decision, maxlen=window)

    log_stage(
        "STATE",
        "Решение оркестратора сохранено в истории",
        symbol=symbol,
        action=decision.get("action"),
        history_len=len(history_for_symbol),
        window=window,
        truncated=truncated,
    )

