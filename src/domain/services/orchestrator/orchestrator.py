from typing import Dict, Any, List

from src.infrastructure.logging.logging_setup import log_info

# Имя логгера для этого модуля
_LOG = __name__


def decide(intents: List[Dict[str, Any]], context: Dict[str, Any], *, tick_id: int, symbol: str) -> Dict[str, Any]:
    """Простейший оркестратор принятия решения по intents.

    Контракт (на текущем этапе прототипа):

    * На вход подаётся список ``intents`` от стратегий. Каждый intent —
      обычный ``dict`` c ключами:

      - ``"action"``: строка (``"BUY"``, ``"SELL"`` или ``"HOLD"``);
      - ``"reason"``: строка‑объяснение (опционально);
      - ``"params"``: произвольный вложенный ``dict`` с параметрами
        заявки, например ``{"amount": 0.001, "price": 50000}``.

    * ``context`` — общий in‑memory контекст конвейера. Оркестратор
      читает из него **только** готовые данные без внешнего I/O.

      Важные разделы, которые он использует сейчас:

      - ``context["market"][symbol]["ts"]`` — timestamp последнего тика
        (если есть), пробрасывается в решение как ``ts``;
      - ``context["risk"][symbol]["max_amount"]`` — простой риск‑лимит
        по объёму (если задан). Если выбранный intent содержит
        ``params["amount"]`` и он **строго больше** ``max_amount``,
        оркестратор отклоняет действие и возвращает HOLD с причиной
        ``"risk_limit_exceeded"``.

    * Алгоритм выбора решения:

      1. Базовое решение всегда ``HOLD`` с причиной ``"no_action"``.
      2. Из списка intents выбирается **первый** intent, у которого
         ``action != "HOLD"``.
      3. Если такой intent найден, формируется решение на его основе:
         ``{"action", "reason", "params"}``.
      4. Поверх этого решения применяется простой риск‑чек (см. выше).

    Инварианты:

    * Функция не делает сетевых запросов, не обращается к БД, не
      использует рандом и sleep — чистая бизнес‑логика на dict‑ах.
    * Логирование вынесено на уровень выше (TickPipelineService) -
      логируются только важные события (сигналы к действию).
    """

    log_info(
        f"🧩 [ORCH] Получен список intents для обработки | tick_id: {tick_id} | symbol: {symbol} | intents_count: {len(intents)}",
        _LOG
    )

    # Базовое решение: HOLD, если стратегий нет или все бездействуют.
    decision: Dict[str, Any] = {
        "action": "HOLD",
        "reason": "no_action",
        "ts": context.get("market", {}).get(symbol, {}).get("ts"),
    }

    # 1. Выбираем первый не-HOLD intent.
    chosen_intent: Dict[str, Any] | None = None
    for intent in intents:
        if intent.get("action") != "HOLD":
            chosen_intent = intent
            break

    if chosen_intent is not None:
        decision = {
            "action": chosen_intent.get("action"),
            "reason": chosen_intent.get("reason", "intent"),
            "params": chosen_intent.get("params", {}),
        }

        # 2. Применяем простой риск‑чек по объёму, если он настроен.
        risk_cfg = context.get("risk", {}).get(symbol) or {}
        max_amount = risk_cfg.get("max_amount")
        params = decision.get("params") or {}
        amount = params.get("amount")

        try:
            amount_value = float(amount) if amount is not None else None
        except (TypeError, ValueError):  # некорректное значение — игнорируем риск-чек
            amount_value = None

        if max_amount is not None and amount_value is not None:
            try:
                max_amount_value = float(max_amount)
            except (TypeError, ValueError):
                max_amount_value = None

            if max_amount_value is not None and amount_value > max_amount_value:
                # Лимит превышен — решение понижается до HOLD, заявка не
                # будет отправлена в Execution‑слой.
                decision = {
                    "action": "HOLD",
                    "reason": "risk_limit_exceeded",
                    "ts": context.get("market", {}).get(symbol, {}).get("ts"),
                }

    log_info(
        f"🧩 [ORCH] Решение принято | tick_id: {tick_id} | symbol: {symbol} | action: {decision.get('action')} | reason: {decision.get('reason')}",
        _LOG
    )
    return decision

