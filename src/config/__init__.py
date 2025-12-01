"""Модуль конфигурации приложения.

Предоставляет:
* :class:`AppConfig` — схема конфигурации (dataclass)
* :func:`load_config` — загрузка конфигурации из env-переменных

Структура модуля:
* config_schema.py — только AppConfig dataclass с валидацией
* config_parsers.py — парсеры значений env-переменных (int, float, bool)
* env_file_loader.py — загрузка .env файла и чтение API-ключей из файлов
* config_loader.py — функция load_config() для сборки конфигурации
"""

from .config_loader import load_config
from .config_schema import AppConfig

__all__ = ["AppConfig", "load_config"]
