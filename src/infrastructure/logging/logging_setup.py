import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Any


"""Единая настройка логов для прототипа.

Формат строк максимально приближен к боевому примеру из bad_example:

    2025-08-14 11:43:29,142 - __main__ - INFO - 🚀 ЗАПУСК AutoTrade v2.3.4 для GTC/USDT
    2025-08-14 11:43:29,224 - infrastructure.connectors.exchange_connector - INFO - ✅ Config loaded for binance (production)
    2025-08-14 11:44:32,781 - application.utils.performance_logger - INFO - 📊 Тик 1 | Цена: 0.45800000 | Сигналов: 13 | TPS: 0.0

Ключевые особенности:
* единый формат времени + имя логгера + уровень + человеко‑читаемое сообщение;
* простой читаемый текст с emoji, без технических тегов в скобках;
* периодические сводки в виде ``📊 Тик N | Цена: X | TPS: Y``.
"""


# Формат для консоли и файла (время, логгер, уровень, текст сообщения)
LINE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class StageFallbackFormatter(logging.Formatter):
    """Форматтер, подставляющий stage="-" и добавляющий миллисекунды.

    * Если в записи нет поля ``stage`` – подставляем ``"-"``.
    * Формат времени приводит ``%(asctime)s`` к виду
      ``YYYY-MM-DD HH:MM:SS,mmm`` (через запятую и 3 знака миллисекунд),
      как в боевых логах из ``bad_example``::

          2025-08-14 11:43:29,142 - __main__ - INFO - ...
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[name-defined]
        if not hasattr(record, "stage"):
            record.stage = "-"  # type: ignore[attr-defined]
        return super().format(record)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # type: ignore[name-defined]
        """Формат ``asctime`` с запятой и миллисекундами.

        Стандартный :mod:`logging` при заданном ``datefmt`` отбрасывает
        миллисекунды. Здесь мы вручную добавляем ``",%03d" % msecs`` к
        строке времени, сохраняя привычный формат даты.
        """

        ct = self.converter(record.created)  # type: ignore[attr-defined]
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(DATE_FORMAT, ct)
        return f"{s},{int(record.msecs):03d}"


# Небольшая «легенда» emoji по стадиям конвейера (для внутреннего использования)
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

def log_info(msg: str, logger_name: str | None = None) -> None:
    """Простое INFO-сообщение без stage-тегов.

    Формат полностью соответствует боевым логам из bad_example:

        2025-08-14 11:43:29,253 - __main__ - INFO - ✅ Коннекторы инициализированы

    Args:
        msg: Текст сообщения (может содержать emoji).
        logger_name: Имя логгера (по умолчанию root).
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info(msg)


def log_warning(msg: str, logger_name: str | None = None) -> None:
    """Простое WARNING-сообщение.

    Args:
        msg: Текст сообщения.
        logger_name: Имя логгера (по умолчанию root).
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.warning(msg)


def log_error(msg: str, logger_name: str | None = None) -> None:
    """Простое ERROR-сообщение.

    Args:
        msg: Текст сообщения.
        logger_name: Имя логгера (по умолчанию root).
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.error(msg)


def log_separator(logger_name: str | None = None) -> None:
    """Вывести разделительную линию из знаков '='.

    Используется для визуального отделения блоков статистики:

        2025-08-14 11:43:33,026 - __main__ - INFO - ================================================================================
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info("=" * 80)


def log_stat_block(title: str, stats: list[str], logger_name: str | None = None) -> None:
    """Вывести блок статистики с заголовком и пунктами.

    Формат как в bad_example:

        ================================================================================
        📊 СТАТИСТИКА ТОРГОВОЙ СИСТЕМЫ
        ================================================================================
        📋 ОРДЕРА:
           • Всего: 0
           • Открытых: 0

    Args:
        title: Заголовок блока (например "📊 СТАТИСТИКА ТОРГОВОЙ СИСТЕМЫ").
        stats: Список строк статистики.
        logger_name: Имя логгера.
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)
    for line in stats:
        logger.info(line)
    logger.info("=" * 80)


def log_stage(stage: str, msg: str, **fields: Any) -> None:
    """Унифицированное логирование стадий конвейера (упрощённый формат).

    В отличие от предыдущей версии, **не выводит** stage-теги в квадратных
    скобках. Формат приближен к боевым логам из bad_example:

        2025-08-14 11:43:29,221 - __main__ - INFO - 🚀 ЗАПУСК AutoTrade v2.3.4 для GTC/USDT

    Args:
        stage: Код этапа (BOOT, TICK, STRAT и т.п.) - используется только
               для выбора emoji.
        msg: Человеко-читаемое сообщение.
        fields: Дополнительные поля для отладки (выводятся через ``|``).
    """
    icon = STAGE_ICONS.get(stage.upper(), "ℹ️")

    # Формируем текст без технических тегов [STAGE]
    if fields:
        # Поля выводим в читаемом формате через |
        kv_parts = []
        for k, v in fields.items():
            kv_parts.append(f"{k}: {_stringify(v)}")
        kv_str = " | ".join(kv_parts)
        text = f"{icon} {msg} | {kv_str}"
    else:
        text = f"{icon} {msg}"

    logging.getLogger().info(text, extra={"stage": stage})


def _stringify(v: Any) -> str:
    """Преобразовать значение в строку для логирования."""
    try:
        if isinstance(v, float):
            # Для цен используем 8 знаков, для TPS и времени — меньше
            if abs(v) < 100:
                return f"{v:.4f}"
            return f"{v:.8f}"
        return str(v)
    except Exception:  # pragma: no cover - защитный код
        return repr(v)

