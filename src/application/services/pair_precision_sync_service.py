from __future__ import annotations

"""Синхронизация биржевых прецизионов с CurrencyPair в БД."""

from typing import Optional

from src.domain.interfaces.currency_pair_repository import ICurrencyPairRepository
from src.domain.interfaces.exchange_connector import IExchangeConnector
from src.infrastructure.logging import log_stage


_DEFAULT_MIN_STEP = 0.00001
_DEFAULT_PRICE_STEP = 0.01
_EPS = 1e-12


async def sync_pair_precisions(
    pair_repo: ICurrencyPairRepository,
    connector: IExchangeConnector,
    *,
    symbol: str,
) -> bool:
    """Обновить min_step/price_step пары в БД на основе данных биржи."""
    pair = pair_repo.get_by_symbol(symbol)
    if pair is None:
        return False

    if not _needs_update(pair.min_step, pair.price_step):
        return False

    precisions = await connector.fetch_pair_precisions(symbol)
    if not precisions:
        return False

    min_step = precisions.get("min_step")
    price_step = precisions.get("price_step")

    updated = False
    if _should_replace(pair.min_step, _DEFAULT_MIN_STEP, min_step):
        pair.min_step = float(min_step)
        updated = True
    if _should_replace(pair.price_step, _DEFAULT_PRICE_STEP, price_step):
        pair.price_step = float(price_step)
        updated = True

    if updated:
        pair_repo.upsert(pair)
        log_stage(
            "BOOT",
            "Обновлены биржевые прецизионы пары",
            symbol=symbol,
            min_step=pair.min_step,
            price_step=pair.price_step,
        )

    return updated


def _needs_update(min_step: float, price_step: float) -> bool:
    return _is_default(min_step, _DEFAULT_MIN_STEP) or _is_default(
        price_step, _DEFAULT_PRICE_STEP
    )


def _is_default(value: float | None, default: float) -> bool:
    if value is None:
        return True
    if value <= 0:
        return True
    return abs(float(value) - default) <= _EPS


def _should_replace(current: float, default: float, incoming: Optional[float]) -> bool:
    if incoming is None:
        return False
    if incoming <= 0:
        return False
    return _is_default(current, default)


__all__ = ["sync_pair_precisions"]
