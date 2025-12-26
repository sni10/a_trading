"""Загрузка переменных окружения из файлов.

Предоставляет функции для:
* Чтения .env файла из корня проекта
* Чтения API-ключей из файлов

Использует только стандартную библиотеку Python.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

from src.infrastructure.logging.logging_setup import log_stage


def load_local_env_file() -> None:
    """Загрузить переменные из корневого ``.env`` один раз за процесс.

    Используем только стандартную библиотеку:

    * файл ищется в корне репозитория (рядом с ``main.py``);
    * формат строк: ``KEY=VALUE``;
    * строки, начинающиеся с ``#`` или пустые, игнорируются;
    * переменные, уже присутствующие в ``os.environ``, **не переопределяются**.

    Функция идемпотентна — повторные вызовы не перезагружают файл.
    """

    # Флаг идемпотентной загрузки хранится в модуле ``src.config.config``,
    # чтобы его можно было переопределять в тестах, не трогая этот модуль.
    config_module = importlib.import_module("src.config.config")

    if getattr(config_module, "_ENV_LOADED", False):
        return

    setattr(config_module, "_ENV_LOADED", True)

    # Определяем корень проекта (на 2 уровня выше src/config/)
    root_dir = Path(__file__).resolve().parents[2]
    env_path = root_dir / ".env"

    if not env_path.is_file():
        return

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key.startswith("#"):
                continue

            # Удаляем возможные обёртки в кавычки
            value = value.strip().strip("'").strip('"')

            # Не трогаем уже заданные переменные окружения
            if key not in os.environ:
                os.environ[key] = value
    except OSError as exc:
        # На раннем прототипе ошибки чтения .env просто игнорируем, но логируем
        log_stage("WARN", "Не удалось прочитать .env файл", error=str(exc))
        return


def read_key_file(var_name: str) -> str | None:
    """Прочитать API-ключ из файла, путь к которому задан в env-переменной.

    Используется для чтения секретных ключей, хранящихся в файлах
    (например, в ``secure_api_keys/``).

    Args:
        var_name: Имя env-переменной, содержащей путь к файлу с ключом.

    Returns:
        Содержимое файла (без пробелов по краям) или None, если переменная
        не задана или файл не удалось прочитать.

    Example:
        >>> os.environ["EXCHANGE_API_KEY_FILE"] = "secure_api_keys/binance_key.txt"
        >>> key = read_key_file("EXCHANGE_API_KEY_FILE")
    """
    path_value = os.getenv(var_name)
    if not path_value:
        return None

    # Определяем корень проекта
    root_dir = Path(__file__).resolve().parents[2]
    file_path = Path(path_value)
    if not file_path.is_absolute():
        file_path = root_dir / file_path

    try:
        return file_path.read_text(encoding="utf-8").strip()
    except OSError as exc:  # pragma: no cover - защита от средовых ошибок
        log_stage(
            "WARN",
            "Не удалось прочитать файл API‑ключа",
            env_var=var_name,
            path=str(file_path),
            error=str(exc),
        )
        return None


def read_exchange_key(exchange_id: str, filename: str) -> str | None:
    """Прочитать ключ из secure_api_keys/{exchange_id}/{filename}."""
    if not exchange_id:
        return None

    root_dir = Path(__file__).resolve().parents[2]
    file_path = root_dir / "secure_api_keys" / exchange_id / filename
    if not file_path.is_file():
        return None

    try:
        return file_path.read_text(encoding="utf-8").strip()
    except OSError as exc:  # pragma: no cover - защита от средовых ошибок
        log_stage(
            "WARN",
            "Не удалось прочитать файл API‑ключа",
            path=str(file_path),
            error=str(exc),
        )
        return None


__all__ = ["load_local_env_file", "read_key_file", "read_exchange_key"]
