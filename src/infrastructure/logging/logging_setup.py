import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any


# Simple, consistent line format for both console and file
LINE_FORMAT = "%(asctime)s | %(levelname)s | stage=%(stage)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class StageFallbackFormatter(logging.Formatter):
    """Форматтер, подставляющий stage="-" при отсутствии поля в записи."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[name-defined]
        if not hasattr(record, "stage"):
            record.stage = "-"  # type: ignore[attr-defined]
        return super().format(record)


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

    Примеры:
      log_stage('BOOT', 'init app')
      log_stage('TICK', 'received', tick_id=1, symbol='BTC/USDT', price=50000)
    """

    kv = " ".join(f"{k}={_stringify(v)}" for k, v in fields.items())
    text = msg if not kv else f"{msg} | {kv}"
    logging.getLogger(__name__).info(text, extra={"stage": stage})


def _stringify(v: Any) -> str:
    try:
        if isinstance(v, float):
            return f"{v:.8f}"  # stable float print
        return str(v)
    except Exception:  # pragma: no cover - защитный код
        return repr(v)

