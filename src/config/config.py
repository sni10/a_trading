"""Загрузка и валидация окружения для прототипа.

Минимальный AppConfig на этом этапе:

* environment – логический режим запуска (local/dev/prod).
* symbol – **одна** торгуемая пара на процесс ("BTC/USDT" и т.п.).
* indicator_*_interval – частота обновления уровней индикаторов в тиках
  (fast/medium/heavy: 1 / 3 / 5 по умолчанию).
* max_ticks, tick_sleep_sec – параметры демо‑конвейера.

Важно: только этот модуль читает os.getenv; дальше по коду передаём уже
готовый объект :class:`AppConfig`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
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
    # В раннем прототипе один процесс всегда обслуживает **одну**
    # валютную пару. Поэтому здесь фиксируем одиночный ``symbol``.
    # Поддержка нескольких пар (и связанных списков) будет добавляться
    # отдельно, когда появится полноценный MarketBus.
    symbol: str = "BTC/USDT"
    max_ticks: int = 10
    tick_sleep_sec: float = 0.2

    # Частота обновления индикаторов (в тиках)
    indicator_fast_interval: int = 1
    indicator_medium_interval: int = 3
    indicator_heavy_interval: int = 5

    # Параметры интеграции с биржевым коннектором
    # (используются только в async‑конвейере и воркерах рынка).
    exchange_id: str = "binance"
    sandbox_mode: bool = False
    order_book_refresh_interval_seconds: float = 5.0

    # API‑ключи биржи. На раннем этапе они опциональны: если заданы,
    # коннектор будет аутентифицироваться и сможет работать с приватными
    # методами. Для получения только публичных данных (тикер/стакан)
    # поля могут оставаться пустыми.
    #
    # Источники значений:
    # * прямые переменные окружения ``EXCHANGE_API_KEY`` /
    #   ``EXCHANGE_API_SECRET``;
    # * либо пути к файлам с ключами через
    #   ``EXCHANGE_API_KEY_FILE`` / ``EXCHANGE_API_SECRET_FILE`` –
    #   содержимое файла читается целиком и используется как значение
    #   ключа. Это позволяет хранить секреты в ``secure_api_keys``.
    exchange_api_key: str | None = None
    exchange_api_secret: str | None = None

    # Интервал между файловыми снапшотами state в тиках. Значение 0
    # отключает периодическое сохранение снапшотов.
    state_snapshot_interval_ticks: int = 100

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

        if self.order_book_refresh_interval_seconds <= 0:
            raise ValueError("order_book_refresh_interval_seconds must be > 0")

        if self.state_snapshot_interval_ticks < 0:
            raise ValueError("state_snapshot_interval_ticks must be >= 0")


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


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    log_stage("ERROR", "Некорректное булево значение в env", value=value)
    raise ValueError(f"Invalid bool value in env: {value!r}") from None


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
    # Параметры могут уточнять конфиг, но не перекрывают env.
    symbol: str | None = None,
    max_ticks: int | None = None,
    tick_sleep_sec: float | None = None,
) -> AppConfig:
    """Собрать AppConfig из значений по умолчанию + env + параметров.

    Общий приоритет:

    * сначала берутся значения по умолчанию из :class:`AppConfig`;
    * затем они **переопределяются переменными окружения** (включая
      те, что подгружены из ``.env``);
    * явные аргументы функции могут задать значение **только если для
      поля нет значения в env**.

    Исключение: торговый ``symbol`` намеренно не управляется через env
    (переменная ``SYMBOLS`` игнорируется), поэтому для него порядок
    такой: аргумент функции → значение по умолчанию.
    """

    # Перед чтением os.getenv подгружаем локальный .env (если есть)
    _load_local_env_file()

    base = AppConfig()

    # environment
    env_environment = os.getenv("APP_ENV")
    if env_environment:
        base.environment = env_environment

    # symbol
    # На этом этапе **одна** торговая пара берётся либо из значений по
    # умолчанию :class:`AppConfig`, либо из явного аргумента функции.
    # Переменная окружения "SYMBOLS" намеренно игнорируется, чтобы
    # точкой агрегации оставалась CurrencyPair через репозиторий, а не
    # сырые строки из env.
    if symbol is not None:
        base.symbol = symbol

    # max_ticks
    env_max_ticks = os.getenv("MAX_TICKS")
    if env_max_ticks is not None:
        # Env имеет наивысший приоритет
        base.max_ticks = _parse_int(env_max_ticks, base.max_ticks)
    elif max_ticks is not None:
        base.max_ticks = max_ticks

    # tick_sleep_sec
    env_tick_sleep = os.getenv("TICK_SLEEP_SEC")
    if env_tick_sleep is not None:
        base.tick_sleep_sec = _parse_float(env_tick_sleep, base.tick_sleep_sec)
    elif tick_sleep_sec is not None:
        base.tick_sleep_sec = tick_sleep_sec

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

    # exchange / connector settings (env только переопределяет дефолты)
    env_exchange_id = os.getenv("EXCHANGE_ID")
    if env_exchange_id:
        base.exchange_id = env_exchange_id

    env_sandbox = os.getenv("EXCHANGE_SANDBOX_MODE")
    base.sandbox_mode = _parse_bool(env_sandbox, base.sandbox_mode)

    env_ob_interval = os.getenv("ORDER_BOOK_REFRESH_INTERVAL_SECONDS")
    base.order_book_refresh_interval_seconds = _parse_float(
        env_ob_interval,
        base.order_book_refresh_interval_seconds,
    )

    # --- API‑ключи биржи ---
    # Приоритет: прямые значения в env, затем файлы.
    env_api_key = os.getenv("EXCHANGE_API_KEY")
    env_api_secret = os.getenv("EXCHANGE_API_SECRET")

    # Вспомогательная функция для чтения ключей из файла. Путь может быть
    # как абсолютным, так и относительным к корню репозитория.
    def _read_key_file(var_name: str) -> str | None:
        path_value = os.getenv(var_name)
        if not path_value:
            return None

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

    if env_api_key is not None:
        base.exchange_api_key = env_api_key
    else:
        file_key = _read_key_file("EXCHANGE_API_KEY_FILE")
        if file_key is not None:
            base.exchange_api_key = file_key

    if env_api_secret is not None:
        base.exchange_api_secret = env_api_secret
    else:
        file_secret = _read_key_file("EXCHANGE_API_SECRET_FILE")
        if file_secret is not None:
            base.exchange_api_secret = file_secret

    # state snapshot interval (env переопределяет дефолт)
    env_snapshot_interval = os.getenv("STATE_SNAPSHOT_INTERVAL_TICKS")
    base.state_snapshot_interval_ticks = _parse_int(
        env_snapshot_interval, base.state_snapshot_interval_ticks
    )

    # Финальная проверка инвариантов
    base.validate()
    return base


__all__ = ["AppConfig", "load_config"]
