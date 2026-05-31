from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.logging.log_formatter import STAGE_ICONS


"""Удобные функции логирования для прикладного кода.

Модуль зависит только от стандартного :mod:`logging` и легенды
``STAGE_ICONS`` из :mod:`log_formatter`. Это позволяет переиспользовать
функции как в application-, так и в infrastructure-слоях.
"""


def log_info(msg: str, logger_name: str | None = None) -> None:
    """Простое INFO‑сообщение без stage‑тегов."""

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info(msg)


def log_warning(msg: str, logger_name: str | None = None) -> None:
    """Простое WARNING‑сообщение."""

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.warning(msg)


def log_error(msg: str, logger_name: str | None = None) -> None:
    """Простое ERROR‑сообщение."""

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.error(msg)


def log_separator(logger_name: str | None = None) -> None:
    """Вывести разделительную линию из знаков ``"="``."""

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info("=" * 80)


def log_stat_block(title: str, stats: list[str], logger_name: str | None = None) -> None:
    """Вывести блок статистики с заголовком и пунктами."""

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)
    for line in stats:
        logger.info(line)
    logger.info("=" * 80)


def log_stage(stage: str, msg: str, logger_name: str | None = None, **fields: Any) -> None:
    """Унифицированное логирование стадий конвейера.

    Формат приближен к боевым логам из ``bad_example`` и ожидается
    тестом :mod:`tests.test_logging_format`.
    """

    icon = STAGE_ICONS.get(stage.upper(), "ℹ️")

    if fields:
        kv_parts = []
        for key, value in fields.items():
            kv_parts.append(f"{key}: {_stringify(value)}")
        kv_str = " | ".join(kv_parts)
        text = f"{icon} {msg} | {kv_str}"
    else:
        text = f"{icon} {msg}"

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info(text, extra={"stage": stage})


def _stringify(v: Any) -> str:
    """Преобразовать значение в строку для логирования."""

    try:
        if isinstance(v, float):
            # Для цен используем 8 знаков, для TPS и времени — меньше
            return f"{v:.8f}".rstrip("0").rstrip(".")
        return str(v)
    except Exception:  # pragma: no cover - максимально защитный fallback
        return repr(v)


__all__ = [
    "log_info",
    "log_warning",
    "log_error",
    "log_separator",
    "log_stat_block",
    "log_stage",
]
