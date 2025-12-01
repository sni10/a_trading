"""Модуль конфигурации приложения.

Предоставляет:
* :class:`AppConfig` — схема конфигурации (dataclass)
* :func:`load_config` — загрузка конфигурации из env-переменных
"""

from .config import load_config
from .config_schema import AppConfig

__all__ = ["AppConfig", "load_config"]
