import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any


"""Единая настройка логов для прототипа.

Формат строк максимально приближен к боевому примеру из bad_example:

    2025-08-28 18:36:03,399 - __main__ - INFO - 🚀 ЗАПУСК AutoTrade...

Ключевые особенности:
* единый формат времени + имя логгера + уровень + человеко‑читаемое сообщение;
* все сообщения из конвейера пишутся через :func:`log_stage` и получают
  понятный emoji‑префикс по стадии (BOOT, TICK, STRAT, ORCH, EXEC и т.д.).
"""


# Формат для консоли и файла (время, логгер, уровень, текст сообщения)
LINE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class StageFallbackFormatter(logging.Formatter):
    """Форматтер, подставляющий stage="-" при отсутствии поля в записи.

    Сейчас поле ``stage`` не выводится напрямую в формате, но остаётся в
    записи логгера на будущее (фильтры, сторонние обработчики и т.п.).
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[name-defined]
        if not hasattr(record, "stage"):
            record.stage = "-"  # type: ignore[attr-defined]
        return super().format(record)


# Небольшая «легенда» emoji по стадиям конвейера
STAGE_ICONS: dict[str, str] = {
    "BOOT": "🚀",        # запуск/инициализация
    "LOAD": "📦",        # загрузка данных/снапшотов
    "WARMUP": "🔥",      # прогрев индикаторов/кэшей
    "LOOP": "🔄",        # основной цикл
    "TICK": "📈",        # тики рынка
    "FEEDS": "🌐",       # обновление рыночных фидов/кэшей
    "IND": "📊",         # индикаторы
    "CTX": "🧠",         # сбор контекста
    "STRAT": "🎯",       # стратегии
    "ORCH": "🧩",        # оркестратор
    "EXEC": "⚙️",        # исполнение
    "STATE": "📂",       # состояние/метрики
    "HEARTBEAT": "💓",   # heartbeat/health‑check
    "ERROR": "❌",       # критические ошибки/исключения
    "WARN": "⚠️",        # предупреждения
    "STOP": "🛑",        # остановка
}


def setup_logging(log_file: str = os.path.join("logs", "prototype.log"), level: int = logging.INFO) -> None:
    """Настроить корневой логгер: консоль + ротируемый файл.

    - Console: человеко‑читаемый вывод с единым форматом
    - File: RotatingFileHandler (5 MB x 5 backups)
    """

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers to make function idempotent
    for h in list(logger.handlers):
        logger.removeHandler(h)

    formatter = StageFallbackFormatter(LINE_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def log_stage(stage: str, msg: str, **fields: Any) -> None:
    """Унифицированное логирование стадий конвейера.

    * ``stage`` – короткий код этапа (BOOT, TICK, STRAT, ORCH, EXEC и т.п.);
    * ``msg`` – человеко‑читаемое описание события;
    * ``fields`` – дополнительные поля, логируются в виде ``key=value``.

    Примеры использования:

        log_stage("BOOT", "Запуск демо‑конвейера")
        log_stage("TICK", "Получен тик", tick_id=1, symbol="BTC/USDT", price=50000)
    """

    icon = STAGE_ICONS.get(stage.upper(), "ℹ️")
    kv = " ".join(f"{k}={_stringify(v)}" for k, v in fields.items())

    base = f"{icon} [{stage}] {msg}"
    text = base if not kv else f"{base} | {kv}"

    # Пишем в корневой логгер, чтобы формат соответствовал примерам вида
    # "2025-08-28 18:36:03,399 - root - INFO - ..."
    logging.getLogger().info(text, extra={"stage": stage})


def _stringify(v: Any) -> str:
    try:
        if isinstance(v, float):
            return f"{v:.8f}"  # stable float print
        return str(v)
    except Exception:  # pragma: no cover - защитный код
        return repr(v)

