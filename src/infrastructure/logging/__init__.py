"""Инфраструктура логирования для прототипа.

Пакет предоставляет единый публичный API для логирования:

* :class:`LoggerAdapter` – реализация :class:`ILogger` для domain-слоя;
* :func:`setup_logging` – базовая настройка корневого логгера;
* функции удобного логирования (:mod:`log_functions`);
* форматтер и легенда emoji (:mod:`log_formatter`).
"""

from src.infrastructure.logging.log_formatter import (
    DATE_FORMAT,
    LINE_FORMAT,
    STAGE_ICONS,
    StageFallbackFormatter,
)
from src.infrastructure.logging.log_functions import (
    log_error,
    log_info,
    log_separator,
    log_stage,
    log_stat_block,
    log_warning,
)
from src.infrastructure.logging.logger_adapter import LoggerAdapter
from src.infrastructure.logging.logging_setup import setup_logging

__all__ = [
    "LoggerAdapter",
    "setup_logging",
    "StageFallbackFormatter",
    "LINE_FORMAT",
    "DATE_FORMAT",
    "STAGE_ICONS",
    "log_info",
    "log_warning",
    "log_error",
    "log_separator",
    "log_stat_block",
    "log_stage",
]
