"""Обратная совместимость и флаг для загрузки .env.

DEPRECATED: Используйте ``from src.config import AppConfig, load_config``
или ``from src.config.config_loader import load_config``.

Модуль также хранит флаг ``_ENV_LOADED``, который используется
``env_file_loader.load_local_env_file`` для идемпотентной загрузки
``.env`` и может быть переопределён в тестах.
"""

from .config_loader import load_config
from .config_schema import AppConfig

# Флаг, предотвращающий множественную загрузку .env (используется в тестах).
_ENV_LOADED: bool = False

__all__ = ["AppConfig", "load_config"]
