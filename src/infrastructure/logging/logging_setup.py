import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any

from src.infrastructure.logging.log_formatter import (
    DATE_FORMAT,
    LINE_FORMAT,
    StageFallbackFormatter,
)


"""Единая настройка логов для прототипа.

Модуль отвечает только за конфигурацию корневого логгера. Форматирование
и вспомогательные функции вынесены в :mod:`log_formatter` и
``log_functions`` соответственно (см. ТЗ‑33/34).
"""


def setup_logging(log_file: str = os.path.join("logs", "prototype.log"), level: int = logging.INFO) -> None:
    """Настроить корневой логгер: консоль + ротируемый файл.

    - Console: человеко‑читаемый вывод с единым форматом;
    - File: :class:`RotatingFileHandler` (5 MB x 5 backups).
    """

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers to make function idempotent
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = StageFallbackFormatter(LINE_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


__all__ = ["setup_logging"]

def log_info(msg: str, logger_name: str | None = None) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_info` из ``log_functions``.

    Оставлено только для обратной совместимости старых импортов
    ``from src.infrastructure.logging.logging_setup import log_info``.
    """

    from src.infrastructure.logging.log_functions import log_info as _log_info

    _log_info(msg, logger_name)


def log_warning(msg: str, logger_name: str | None = None) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_warning` из ``log_functions``."""

    from src.infrastructure.logging.log_functions import log_warning as _log_warning

    _log_warning(msg, logger_name)


def log_error(msg: str, logger_name: str | None = None) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_error` из ``log_functions``."""

    from src.infrastructure.logging.log_functions import log_error as _log_error

    _log_error(msg, logger_name)


def log_separator(logger_name: str | None = None) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_separator` из ``log_functions``."""

    from src.infrastructure.logging.log_functions import log_separator as _log_separator

    _log_separator(logger_name)


def log_stat_block(title: str, stats: list[str], logger_name: str | None = None) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_stat_block` из ``log_functions``."""

    from src.infrastructure.logging.log_functions import log_stat_block as _log_stat_block

    _log_stat_block(title, stats, logger_name)


def log_stage(stage: str, msg: str, logger_name: str | None = None, **fields: Any) -> None:  # pragma: no cover - обратная совместимость
    """DEPRECATED: импортируйте :func:`log_stage` из ``log_functions``."""

    from src.infrastructure.logging.log_functions import log_stage as _log_stage

    _log_stage(stage, msg, logger_name, **fields)

