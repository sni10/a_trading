"""Точка входа прототипа.

Вся бизнес-логика конвейера теперь находится в пакете :mod:`src`.
Здесь оставлен только тонкий фасад для совместимости:

    python main.py

см. :mod:`src.application.use_cases.run_realtime_trading`.
"""

from __future__ import annotations

import sys
from src.application.use_cases.run_realtime_trading import run


def _parse_cli_pair(argv: list[str]) -> str:
    """Извлечь символ валютной пары из аргументов командной строки.

    Ожидается формат вызова::

        python main.py BTC/USDT

    Если пара не указана или формат некорректен, процесс завершается
    с понятным сообщением.
    """

    if len(argv) < 2:
        raise SystemExit("Usage: python main.py BTC/USDT")

    symbol = argv[1].strip()
    if "/" not in symbol or symbol.count("/") != 1:
        raise SystemExit(
            f"Invalid pair symbol: {symbol!r}. Expected format BASE/QUOTE, e.g. BTC/USDT"
        )

    return symbol


if __name__ == "__main__":  # pragma: no cover - сценарий запуска
    from src.infrastructure.logging.logging_setup import log_stage

    try:
        cli_symbol = _parse_cli_pair(sys.argv)
        # В прототипе один процесс обслуживает одну пару, поэтому
        # передаём одиночный symbol в use-case.
        run(symbol=cli_symbol)
    except KeyboardInterrupt:
        log_stage("WARN", "Прерывание работы по Ctrl+C")
        sys.exit(0)
    except Exception as exc:
        log_stage("ERROR", "Критическая ошибка в main()", error=str(exc), error_type=type(exc).__name__)
        sys.exit(1)
