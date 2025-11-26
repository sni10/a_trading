import time
import itertools
import random
from typing import Dict, Iterable, List

from src.infrastructure.logging.logging_setup import log_stage


def generate_ticks(symbols: List[str], max_ticks: int = 10, sleep_sec: float = 0.2) -> Iterable[Dict]:
    """Синхронный фейковый генератор тиков.

    Возвращает dict-объекты с ключами symbol, price, ts.
    Логирует старт работы; детальное логирование происходит на уровне
    TICK-стадии в конвейере.
    """

    log_stage(
        "TICK",
        "CLASS:TickSource:__iter__() - генерирует фиктивные тики, возвращает dict {symbol, price, ts}",
        symbols=",".join(symbols),
        limit=max_ticks,
    )

    base_prices = {s: 100.0 + random.random() * 10 for s in symbols}
    clock = itertools.count(1)

    for _ in range(1, max_ticks + 1):
        for s in symbols:
            # small random walk
            base = base_prices[s]
            base *= 1.0 + random.uniform(-0.001, 0.001)
            base_prices[s] = base
            yield {"symbol": s, "price": round(base, 2), "ts": int(time.time())}
            time.sleep(sleep_sec)

