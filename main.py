"""Точка входа прототипа.

Вся бизнес-логика конвейера теперь находится в пакете :mod:`src`.
Здесь оставлен только тонкий фасад для совместимости:

    python main.py

см. :mod:`src.application.use_cases.run_realtime_trading`.
"""

from src.application.use_cases.run_realtime_trading import run


if __name__ == "__main__":  # pragma: no cover - сценарий запуска
    run()
