from __future__ import annotations

"""Cooldown-правила для сигналов BUY."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CooldownDecision:
    """Результат проверки cooldown и лимитов."""

    allowed: bool
    reason: str


class SignalCooldownManager:
    """Контроль частоты BUY-сигналов и лимитов сделок."""

    def __init__(self, *, default_cooldown_sec: float = 60.0) -> None:
        self._default_cooldown_sec = default_cooldown_sec

    def can_buy(
        self,
        *,
        active_deals_count: int,
        max_deals: int | None,
        last_buy_ts: int | None,
        now_ts: int | None,
        cooldown_sec: float | None = None,
    ) -> CooldownDecision:
        if max_deals is not None and max_deals > 0 and active_deals_count >= max_deals:
            return CooldownDecision(False, "deal_limit_reached")

        effective_cooldown = self._default_cooldown_sec if cooldown_sec is None else cooldown_sec
        if effective_cooldown and last_buy_ts and now_ts:
            elapsed_ms = now_ts - last_buy_ts
            if elapsed_ms < effective_cooldown * 1000:
                return CooldownDecision(False, "buy_cooldown_active")

        return CooldownDecision(True, "ok")


__all__ = ["SignalCooldownManager", "CooldownDecision"]
