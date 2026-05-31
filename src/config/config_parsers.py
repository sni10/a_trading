"""Парсеры значений переменных окружения.

Предоставляет функции для конвертации строковых значений из env-переменных
в типизированные значения Python (int, float, bool).
"""

from __future__ import annotations

from src.infrastructure.logging import log_stage


def parse_int(value: str | None, default: int) -> int:
    """Преобразовать строковое значение env-переменной в целое число.

    Если значение пустое или None, возвращается дефолтное значение.
    При ошибке парсинга логируется предупреждение и выбрасывается ValueError.

    Args:
        value: Строковое значение из env-переменной.
        default: Значение по умолчанию, если value пустое.

    Returns:
        Целое число.

    Raises:
        ValueError: Если значение не может быть преобразовано в int.
    """
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        log_stage("ERROR", "Некорректное целочисленное значение в env", value=value)
        raise ValueError(f"Invalid int value in env: {value!r}") from None


def parse_float(value: str | None, default: float) -> float:
    """Преобразовать строковое значение env-переменной в вещественное число.

    Если значение пустое или None, возвращается дефолтное значение.
    При ошибке парсинга логируется предупреждение и выбрасывается ValueError.

    Args:
        value: Строковое значение из env-переменной.
        default: Значение по умолчанию, если value пустое.

    Returns:
        Вещественное число.

    Raises:
        ValueError: Если значение не может быть преобразовано в float.
    """
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        log_stage("ERROR", "Некорректное вещественное значение в env", value=value)
        raise ValueError(f"Invalid float value in env: {value!r}") from None


def parse_bool(value: str | None, default: bool) -> bool:
    """Преобразовать строковое значение env-переменной в булево значение.

    Поддерживаемые значения для True: "1", "true", "yes", "y", "on"
    Поддерживаемые значения для False: "0", "false", "no", "n", "off"

    Регистр не учитывается. Если значение пустое или None, возвращается
    дефолтное значение.

    Args:
        value: Строковое значение из env-переменной.
        default: Значение по умолчанию, если value пустое.

    Returns:
        Булево значение.

    Raises:
        ValueError: Если значение не распознано как булево.
    """
    if value is None or value == "":
        return default
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    log_stage("ERROR", "Некорректное булево значение в env", value=value)
    raise ValueError(f"Invalid bool value in env: {value!r}") from None


__all__ = ["parse_int", "parse_float", "parse_bool"]
