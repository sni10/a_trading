"""Загрузка и валидация окружения для прототипа.

Минимальный AppConfig на этом этапе:

* environment – логический режим запуска (local/dev/prod).
* symbols – список торгуемых пар.
* indicator_*_interval – частота обновления уровней индикаторов в тиках
  (fast/medium/heavy: 1 / 3 / 5 по умолчанию).
* max_ticks, tick_sleep_sec – параметры демо‑конвейера.

Важно: только этот модуль читает os.getenv; дальше по коду передаём уже
готовый объект AppConfig.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from src.infrastructure.logging.logging_setup import log_stage


@dataclass
class AppConfig:
    """Конфигурация раннего прототипа.

    На этом этапе сюда выносятся только действительно необходимые
    параметры. При развитии прототипа класс можно расширять, но
    стараться не тянуть внутрь бизнес‑логику.
    """

    # Общие параметры окружения
    environment: str = "local"

    # Базовые настройки конвейера
    symbols: List[str] = field(
        default_factory=lambda: ["BTC/USDT", "ETH/USDT"]
    )
    max_ticks: int = 10
    tick_sleep_sec: float = 0.2

    # Частота обновления индикаторов (в тиках)
    indicator_fast_interval: int = 1
    indicator_medium_interval: int = 3
    indicator_heavy_interval: int = 5

    def validate(self) -> None:
        """Проверить базовые инварианты конфига.

        Вызывается один раз при старте. При нарушении инвариантов
        выбрасывает ValueError (fail‑fast), чтобы не запускать конвейер
        с некорректными настройками.
        """

        if self.indicator_fast_interval < 1:
            raise ValueError("indicator_fast_interval must be >= 1")

        if self.indicator_medium_interval < 1:
            raise ValueError("indicator_medium_interval must be >= 1")

        if self.indicator_heavy_interval < 1:
            raise ValueError("indicator_heavy_interval must be >= 1")

        if self.indicator_medium_interval < self.indicator_fast_interval:
            raise ValueError(
                "indicator_medium_interval must be >= indicator_fast_interval"
            )

        if self.indicator_heavy_interval < self.indicator_medium_interval:
            raise ValueError(
                "indicator_heavy_interval must be >= indicator_medium_interval"
            )

        if self.max_ticks <= 0:
            raise ValueError("max_ticks must be > 0")

        if self.tick_sleep_sec < 0:
            raise ValueError("tick_sleep_sec must be >= 0")


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        log_stage("ERROR", "Некорректное целочисленное значение в env", value=value)
        raise ValueError(f"Invalid int value in env: {value!r}") from None


def _parse_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        log_stage("ERROR", "Некорректное вещественное значение в env", value=value)
        raise ValueError(f"Invalid float value in env: {value!r}") from None


_ENV_LOADED = False


def _load_local_env_file() -> None:
    """Загрузить переменные из корневого ``.env`` один раз за процесс.

    Используем только стандартную библиотеку:

    * файл ищется в корне репозитория (рядом с ``main.py``);
    * формат строк: ``KEY=VALUE``;
    * строки, начинающиеся с ``#`` или пустые, игнорируются;
    * переменные, уже присутствующие в ``os.environ``, **не переопределяются**.
    """

    global _ENV_LOADED
    if _ENV_LOADED:
        return

    _ENV_LOADED = True

    # ``src/config/config.py`` -> корень проекта
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


def load_config(
    *,
    # Параметры могут переопределять env (используется из run()).
    symbols: List[str] | None = None,
    max_ticks: int | None = None,
    tick_sleep_sec: float | None = None,
) -> AppConfig:
    """Собрать AppConfig из env + опциональных параметров.

    Порядок приоритета для каждого поля:
    1. Аргументы функции (если переданы явно).
    2. Переменные окружения.
    3. Значения по умолчанию из dataclass AppConfig.
    """

    # Перед чтением os.getenv подгружаем локальный .env (если есть)
    _load_local_env_file()

    base = AppConfig()

    # environment
    env_environment = os.getenv("APP_ENV")
    if env_environment:
        base.environment = env_environment

    # symbols
    # На этом этапе список торговых пар берётся только из значений по
    # умолчанию AppConfig или из явных аргументов функции. Переменная
    # окружения "SYMBOLS" намеренно игнорируется, чтобы точкой
    # агрегации оставалась CurrencyPair через репозиторий, а не сырые
    # строки из env.
    if symbols is not None:
        base.symbols = list(symbols)

    # max_ticks
    env_max_ticks = os.getenv("MAX_TICKS")
    if max_ticks is not None:
        base.max_ticks = max_ticks
    else:
        base.max_ticks = _parse_int(env_max_ticks, base.max_ticks)

    # tick_sleep_sec
    env_tick_sleep = os.getenv("TICK_SLEEP_SEC")
    if tick_sleep_sec is not None:
        base.tick_sleep_sec = tick_sleep_sec
    else:
        base.tick_sleep_sec = _parse_float(env_tick_sleep, base.tick_sleep_sec)

    # indicator intervals
    env_fast = os.getenv("INDICATOR_FAST_INTERVAL")
    env_medium = os.getenv("INDICATOR_MEDIUM_INTERVAL")
    env_heavy = os.getenv("INDICATOR_HEAVY_INTERVAL")

    base.indicator_fast_interval = _parse_int(
        env_fast, base.indicator_fast_interval
    )
    base.indicator_medium_interval = _parse_int(
        env_medium, base.indicator_medium_interval
    )
    base.indicator_heavy_interval = _parse_int(
        env_heavy, base.indicator_heavy_interval
    )

    # Финальная проверка инвариантов
    base.validate()
    return base


__all__ = ["AppConfig", "load_config"]
