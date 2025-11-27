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


def make_state_snapshot(
    context: Dict[str, Any], *, symbol: str, tick_id: int
) -> Dict[str, Any]:
    """Сформировать сериализуемый снапшот state для указанного инструмента.

    В снапшот попадает только чистый dict‑state без несериализуемых
    объектов (репозитории, кэши, config и т.п.), чтобы backend хранения
    мог быть любым (файл, Redis и др.).
    """

    market = (context.get("market") or {}).get(symbol)
    indicators = (context.get("indicators") or {}).get(symbol)
    indicators_history = (context.get("indicators_history") or {}).get(symbol, [])
    intents = (context.get("intents") or {}).get(symbol, [])
    intents_history = (context.get("intents_history") or {}).get(symbol, [])
    decision = (context.get("decisions") or {}).get(symbol)
    decisions_history = (context.get("decisions_history") or {}).get(symbol, [])
    metrics = context.get("metrics") or {}

    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "tick_id": tick_id,
        "market": market,
        "indicators": indicators,
        "indicators_history": indicators_history,
        "intents": intents,
        "intents_history": intents_history,
        "decision": decision,
        "decisions_history": decisions_history,
        "metrics": metrics,
    }

    log_stage(
        "STATE",
        "Формирование снапшота state",
        symbol=symbol,
        tick_id=tick_id,
        has_market=market is not None,
        has_indicators=indicators is not None,
        intents_count=len(intents),
    )

    return snapshot


def apply_state_snapshot(
    context: Dict[str, Any], *, symbol: str, snapshot: Dict[str, Any]
) -> None:
    """Применить ранее сохранённый снапшот к текущему контексту.

    Функция обновляет только высокоуровневые разделы ``market``,
    ``indicators``, ``*_history``, ``intents``, ``decisions`` и
    ``metrics``, не трогая кэши рынка, репозитории и конфигурацию.
    """

    market_section = context.setdefault("market", {})
    if snapshot.get("market") is not None:
        market_section[symbol] = snapshot["market"]

    indicators_section = context.setdefault("indicators", {})
    if snapshot.get("indicators") is not None:
        indicators_section[symbol] = snapshot["indicators"]

    indicators_history_all = context.setdefault("indicators_history", {})
    indicators_history_all[symbol] = list(snapshot.get("indicators_history") or [])

    intents_section = context.setdefault("intents", {})
    intents_section[symbol] = list(snapshot.get("intents") or [])

    intents_history_all = context.setdefault("intents_history", {})
    intents_history_all[symbol] = list(snapshot.get("intents_history") or [])

    decisions_section = context.setdefault("decisions", {})
    if snapshot.get("decision") is not None:
        decisions_section[symbol] = snapshot["decision"]

    decisions_history_all = context.setdefault("decisions_history", {})
    decisions_history_all[symbol] = list(snapshot.get("decisions_history") or [])

    metrics = snapshot.get("metrics") or {}
    if metrics:
        context["metrics"] = dict(metrics)

    log_stage(
        "LOAD",
        "Снапшот state применён к контексту",
        symbol=symbol,
        tick_id=snapshot.get("tick_id"),
    )

