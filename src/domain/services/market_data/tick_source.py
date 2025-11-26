import time
import itertools
import random
from typing import Dict, Iterable

from src.infrastructure.logging.logging_setup import log_stage


def generate_ticks(symbol: str, max_ticks: int = 10, sleep_sec: float = 0.2) -> Iterable[Dict]:
    """Синхронный фейковый генератор тиков для **одной** пары.

    Возвращает ``dict`` с ключами ``symbol``, ``price``, ``ts``.
    В логах фиксируется только старт генерации; сами тики подробно
    логируются на стадии TICK основного конвейера.
    """

    log_stage(
        "TICK",
        "Старт генерации тестовых тиков",
        symbol=symbol,
        max_ticks=max_ticks,
        sleep_sec=sleep_sec,
    )

    base_price = 100.0 + random.random() * 10
    clock = itertools.count(1)

    for _ in range(1, max_ticks + 1):
        # small random walk
        base_price *= 1.0 + random.uniform(-0.001, 0.001)
        yield {"symbol": symbol, "price": round(base_price, 2), "ts": int(time.time())}
        time.sleep(sleep_sec)

