from __future__ import annotations

"""Simple in-memory order book provider for strategies and orchestrator.

This module does **not** talk to the exchange directly. It only reads the
latest order book snapshot from :class:`IMarketCache` stored inside the
shared ``context`` dict.

Intended usage in the future decision center:

* indicators give a positive trading signal;
* the decision center asks this provider for the latest order book of the
  target symbol;
* a separate "order book analysis" service consumes this snapshot and
  produces liquidity/impact metrics.

By keeping this provider in the domain layer and working only with
``IMarketCache`` we avoid leaking ccxt/exchange details into strategies
and orchestrator.
"""

from typing import Any, Dict

from src.domain.interfaces.cache import IMarketCache


def get_order_book_from_context(
    context: Dict[str, Any], *, symbol: str
) -> Dict[str, Any] | None:
    """Return the latest order book snapshot for ``symbol`` from context.

    Contract:

    * reads ``context["market_caches"][symbol]`` and, if it is an
      :class:`IMarketCache`, returns ``cache.get_orderbook()``;
    * never touches the exchange connector directly;
    * returns ``None`` if there is no cache for the given symbol or if
      the cache does not yet contain an order book.

    The snapshot format is the unified ccxt-like dict used across the
    project (see ``doc/ccxt_data_structures.md``, ``fetch_order_book()``):

    .. code-block:: python

        order_book = {
            "bids": list[list[float, float]],
            "asks": list[list[float, float]],
            "symbol": str,
            "timestamp": int,
            "datetime": str | None,
            "nonce": int | None,
        }
    """

    caches = context.get("market_caches") or {}
    cache = caches.get(symbol)
    if not isinstance(cache, IMarketCache):
        return None

    return cache.get_orderbook()


__all__ = ["get_order_book_from_context"]
