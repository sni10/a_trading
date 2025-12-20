"""Загрузка и валидация окружения для прототипа.

Важно: только этот модуль читает os.getenv; дальше по коду передаём уже
готовый объект :class:`AppConfig`.
"""

from __future__ import annotations

import os

from src.config.config_parsers import parse_bool, parse_float, parse_int
from src.config.config_schema import AppConfig
from src.config.env_file_loader import load_local_env_file, read_key_file


def load_config(
    *,
    # Параметры могут уточнять конфиг, но не перекрывают env.
    max_ticks: int | None = None,
    ticker_sleep_sec: float | None = None,
) -> AppConfig:
    """Собрать AppConfig из значений по умолчанию + env + параметров.

    Общий приоритет:

    * сначала берутся значения по умолчанию из :class:`AppConfig`;
    * затем они **переопределяются переменными окружения** (включая
      те, что подгружены из ``.env``);
    * явные аргументы функции могут задать значение **только если для
      поля нет значения в env**.

    ВАЖНО: Символы валютных пар (symbol) больше НЕ в AppConfig.
    Они загружаются из CurrencyPair через репозиторий.
    """

    # Перед чтением os.getenv подгружаем локальный .env (если есть)
    load_local_env_file()

    base = AppConfig()

    # --- database settings ---
    env_db_type = os.getenv("DATABASE_TYPE")
    if env_db_type:
        base.database.database_type = env_db_type.strip().lower()  # type: ignore[assignment]

    env_db_path = os.getenv("DATABASE_PATH")
    if env_db_path:
        base.database.database_path = env_db_path.strip()

    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        base.database.database_url = env_db_url.strip()

    # environment
    env_environment = os.getenv("APP_ENV")
    if env_environment:
        base.environment = env_environment

    # max_ticks
    env_max_ticks = os.getenv("MAX_TICKS")
    if env_max_ticks is not None:
        # Env имеет наивысший приоритет
        base.max_ticks = parse_int(env_max_ticks, base.max_ticks)
    elif max_ticks is not None:
        base.max_ticks = max_ticks

    # ticker_sleep_sec
    env_ticker_sleep = os.getenv("TICKER_SLEEP_SEC")
    if env_ticker_sleep is not None:
        base.ticker_sleep_sec = parse_float(env_ticker_sleep, base.ticker_sleep_sec)
    elif ticker_sleep_sec is not None:
        base.ticker_sleep_sec = ticker_sleep_sec

    # indicator intervals
    env_fast = os.getenv("INDICATOR_FAST_INTERVAL")
    env_medium = os.getenv("INDICATOR_MEDIUM_INTERVAL")
    env_heavy = os.getenv("INDICATOR_HEAVY_INTERVAL")

    base.indicator_fast_interval = parse_int(
        env_fast, base.indicator_fast_interval
    )
    base.indicator_medium_interval = parse_int(
        env_medium, base.indicator_medium_interval
    )
    base.indicator_heavy_interval = parse_int(
        env_heavy, base.indicator_heavy_interval
    )

    # exchange / connector settings (env только переопределяет дефолты)
    env_exchange_id = os.getenv("EXCHANGE_ID")
    if env_exchange_id:
        base.exchange_id = env_exchange_id

    env_sandbox = os.getenv("EXCHANGE_SANDBOX_MODE")
    base.sandbox_mode = parse_bool(env_sandbox, base.sandbox_mode)

    env_ob_interval = os.getenv("ORDER_BOOK_REFRESH_INTERVAL_SECONDS")
    base.order_book_refresh_interval_seconds = parse_float(
        env_ob_interval,
        base.order_book_refresh_interval_seconds,
    )

    # --- API‑ключи биржи ---
    # Приоритет: прямые значения в env, затем файлы.
    env_api_key = os.getenv("EXCHANGE_API_KEY")
    env_api_secret = os.getenv("EXCHANGE_API_SECRET")

    if env_api_key is not None:
        base.exchange_api_key = env_api_key
    else:
        file_key = read_key_file("EXCHANGE_API_KEY_FILE")
        if file_key is not None:
            base.exchange_api_key = file_key

    if env_api_secret is not None:
        base.exchange_api_secret = env_api_secret
    else:
        file_secret = read_key_file("EXCHANGE_API_SECRET_FILE")
        if file_secret is not None:
            base.exchange_api_secret = file_secret

    # state snapshot interval (env переопределяет дефолт)
    env_snapshot_interval = os.getenv("STATE_SNAPSHOT_INTERVAL_TICKS")
    base.state_snapshot_interval_ticks = parse_int(
        env_snapshot_interval, base.state_snapshot_interval_ticks
    )

    # Финальная проверка инвариантов
    base.validate()
    return base


__all__ = ["AppConfig", "load_config"]
