"""Адаптер логгера, реализующий протокол ILogger.

Делегирует вызовы к существующим функциям из logging_setup.py,
обеспечивая совместимость доменного слоя с инфраструктурой логирования.
"""

from __future__ import annotations

import logging

from src.domain.interfaces.logger import ILogger
from src.infrastructure.logging.logging_setup import (
    log_error,
    log_info,
    log_stage as infra_log_stage,
    log_warning,
)


class LoggerAdapter:
    """Адаптер, реализующий протокол ILogger через функции logging_setup.
    
    Позволяет доменному коду использовать абстракцию ILogger,
    при этом делегируя реальное логирование инфраструктурному слою.
    
    Attributes:
        _logger_name: Опциональное имя логгера для идентификации источника.
    
    Example:
        >>> adapter = LoggerAdapter("my_service")
        >>> adapter.log_info("Service started")
        >>> adapter.log_stage("BOOT", "Initialization complete")
    """
    
    __slots__ = ("_logger_name",)
    
    def __init__(self, logger_name: str | None = None) -> None:
        """Инициализация адаптера.
        
        Args:
            logger_name: Опциональное имя логгера для идентификации
                         источника логов. Если не указано, используется
                         root-логгер.
        """
        self._logger_name = logger_name
    
    def log_stage(self, stage: str, msg: str, *, level: int = logging.INFO) -> None:
        """Залогировать сообщение для указанного этапа конвейера.
        
        Делегирует вызов к infra_log_stage из logging_setup.
        Параметр level в текущей реализации logging_setup не используется
        напрямую (всегда INFO), но сохраняется для совместимости с протоколом.
        
        Args:
            stage: Имя этапа/подсистемы ("TICK", "ORDERBOOK", "EXECUTION" и т.п.).
            msg: Текст сообщения.
            level: Уровень логирования (по умолчанию INFO).
        """
        infra_log_stage(stage, msg, logger_name=self._logger_name)
    
    def log_info(self, msg: str) -> None:
        """Залогировать информационное сообщение (INFO).
        
        Args:
            msg: Текст сообщения.
        """
        log_info(msg, logger_name=self._logger_name)
    
    def log_warning(self, msg: str) -> None:
        """Залогировать предупреждение (WARNING).
        
        Args:
            msg: Текст сообщения.
        """
        log_warning(msg, logger_name=self._logger_name)
    
    def log_error(self, msg: str) -> None:
        """Залогировать сообщение об ошибке (ERROR).
        
        Args:
            msg: Текст сообщения.
        """
        log_error(msg, logger_name=self._logger_name)
    
    def log_debug(self, msg: str) -> None:
        """Залогировать отладочное сообщение (DEBUG).
        
        В logging_setup.py нет отдельной функции log_debug,
        поэтому используем стандартный logging напрямую.
        
        Args:
            msg: Текст сообщения.
        """
        logger = (
            logging.getLogger(self._logger_name)
            if self._logger_name
            else logging.getLogger()
        )
        logger.debug(msg)


# Проверка соответствия протоколу при импорте (runtime_checkable)
assert isinstance(LoggerAdapter(), ILogger), "LoggerAdapter must implement ILogger protocol"


__all__ = ["LoggerAdapter"]
