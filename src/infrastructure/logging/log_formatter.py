from __future__ import annotations

import logging
import time
from typing import Final


"""Форматирование логов и легенда emoji для стадий конвейера.

Модуль изолирует форматтер и маппинг стадий, чтобы конфигурация
логирования (:mod:`logging_setup`) и вспомогательные функции
(:mod:`log_functions`) зависели только от стабильного API этого модуля.
"""


LINE_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


STAGE_ICONS: dict[str, str] = {
    "BOOT": "🚀",  # запуск/инициализация
    "LOAD": "📦",  # загрузка данных/снапшотов
    "WARMUP": "🔥",  # прогрев индикаторов/кэшей
    "LOOP": "🔄",  # основной цикл
    "TICKER": "📈",  # тики рынка
    "FEEDS": "🌐",  # обновление рыночных фидов/кэшей
    "IND": "📊",  # индикаторы
    "CTX": "🧠",  # сбор контекста
    "STRAT": "🎯",  # стратегии
    "ORCH": "🧩",  # оркестратор
    "EXEC": "⚙️",  # исполнение
    "STATE": "📂",  # состояние/метрики
    "HEARTBEAT": "💓",  # heartbeat/health-check
    "ERROR": "❌",  # критические ошибки/исключения
    "WARN": "⚠️",  # предупреждения
    "STOP": "🛑",  # остановка
}


class StageFallbackFormatter(logging.Formatter):
    """Форматтер, подставляющий ``stage="-"`` и добавляющий миллисекунды.

    * Если в записи нет поля ``stage`` – подставляем ``"-"``.
    * Формат времени приводит ``%(asctime)s`` к виду
      ``YYYY-MM-DD HH:MM:SS,mmm`` (через запятую и 3 знака миллисекунд),
      как в боевых логах из ``bad_example``.
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


__all__ = [
    "LINE_FORMAT",
    "DATE_FORMAT",
    "STAGE_ICONS",
    "StageFallbackFormatter",
]
