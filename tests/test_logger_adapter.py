"""Юнит-тесты для LoggerAdapter.

Проверяют корректность реализации протокола ILogger
и делегирование вызовов к функциям logging_setup.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.domain.interfaces.logger import ILogger
from src.infrastructure.logging.logger_adapter import LoggerAdapter


class TestLoggerAdapterProtocolCompliance:
    """Тесты соответствия LoggerAdapter протоколу ILogger."""
    
    def test_implements_ilogger_protocol(self) -> None:
        """LoggerAdapter должен реализовывать протокол ILogger."""
        adapter = LoggerAdapter()
        assert isinstance(adapter, ILogger)
    
    def test_implements_ilogger_with_logger_name(self) -> None:
        """LoggerAdapter с logger_name также реализует ILogger."""
        adapter = LoggerAdapter("test_logger")
        assert isinstance(adapter, ILogger)
    
    def test_has_all_required_methods(self) -> None:
        """LoggerAdapter должен иметь все методы из ILogger."""
        adapter = LoggerAdapter()
        
        assert hasattr(adapter, "log_stage")
        assert hasattr(adapter, "log_info")
        assert hasattr(adapter, "log_warning")
        assert hasattr(adapter, "log_error")
        assert hasattr(adapter, "log_debug")
        
        assert callable(adapter.log_stage)
        assert callable(adapter.log_info)
        assert callable(adapter.log_warning)
        assert callable(adapter.log_error)
        assert callable(adapter.log_debug)


class TestLoggerAdapterInitialization:
    """Тесты инициализации LoggerAdapter."""
    
    def test_default_initialization(self) -> None:
        """Адаптер должен создаваться без аргументов."""
        adapter = LoggerAdapter()
        assert adapter._logger_name is None
    
    def test_initialization_with_logger_name(self) -> None:
        """Адаптер должен принимать logger_name."""
        adapter = LoggerAdapter("my_service")
        assert adapter._logger_name == "my_service"
    
    def test_initialization_with_none_logger_name(self) -> None:
        """Адаптер должен принимать явный None."""
        adapter = LoggerAdapter(None)
        assert adapter._logger_name is None


class TestLoggerAdapterDelegation:
    """Тесты делегирования вызовов к logging_setup."""
    
    @patch("src.infrastructure.logging.logger_adapter.log_info")
    def test_log_info_delegates_to_logging_setup(self, mock_log_info: MagicMock) -> None:
        """log_info должен делегировать вызов к logging_setup.log_info."""
        adapter = LoggerAdapter()
        adapter.log_info("Test message")
        
        mock_log_info.assert_called_once_with("Test message", logger_name=None)
    
    @patch("src.infrastructure.logging.logger_adapter.log_info")
    def test_log_info_passes_logger_name(self, mock_log_info: MagicMock) -> None:
        """log_info должен передавать logger_name."""
        adapter = LoggerAdapter("my_service")
        adapter.log_info("Test message")
        
        mock_log_info.assert_called_once_with("Test message", logger_name="my_service")
    
    @patch("src.infrastructure.logging.logger_adapter.log_warning")
    def test_log_warning_delegates_to_logging_setup(self, mock_log_warning: MagicMock) -> None:
        """log_warning должен делегировать вызов к logging_setup.log_warning."""
        adapter = LoggerAdapter()
        adapter.log_warning("Warning message")
        
        mock_log_warning.assert_called_once_with("Warning message", logger_name=None)
    
    @patch("src.infrastructure.logging.logger_adapter.log_warning")
    def test_log_warning_passes_logger_name(self, mock_log_warning: MagicMock) -> None:
        """log_warning должен передавать logger_name."""
        adapter = LoggerAdapter("warning_service")
        adapter.log_warning("Warning message")
        
        mock_log_warning.assert_called_once_with("Warning message", logger_name="warning_service")
    
    @patch("src.infrastructure.logging.logger_adapter.log_error")
    def test_log_error_delegates_to_logging_setup(self, mock_log_error: MagicMock) -> None:
        """log_error должен делегировать вызов к logging_setup.log_error."""
        adapter = LoggerAdapter()
        adapter.log_error("Error message")
        
        mock_log_error.assert_called_once_with("Error message", logger_name=None)
    
    @patch("src.infrastructure.logging.logger_adapter.log_error")
    def test_log_error_passes_logger_name(self, mock_log_error: MagicMock) -> None:
        """log_error должен передавать logger_name."""
        adapter = LoggerAdapter("error_service")
        adapter.log_error("Error message")
        
        mock_log_error.assert_called_once_with("Error message", logger_name="error_service")
    
    @patch("src.infrastructure.logging.logger_adapter.infra_log_stage")
    def test_log_stage_delegates_to_logging_setup(self, mock_log_stage: MagicMock) -> None:
        """log_stage должен делегировать вызов к logging_setup.log_stage."""
        adapter = LoggerAdapter()
        adapter.log_stage("BOOT", "Starting up")
        
        mock_log_stage.assert_called_once_with("BOOT", "Starting up", logger_name=None)
    
    @patch("src.infrastructure.logging.logger_adapter.infra_log_stage")
    def test_log_stage_passes_logger_name(self, mock_log_stage: MagicMock) -> None:
        """log_stage должен передавать logger_name."""
        adapter = LoggerAdapter("stage_service")
        adapter.log_stage("TICK", "Processing tick")
        
        mock_log_stage.assert_called_once_with("TICK", "Processing tick", logger_name="stage_service")
    
    @patch("src.infrastructure.logging.logger_adapter.infra_log_stage")
    def test_log_stage_accepts_level_parameter(self, mock_log_stage: MagicMock) -> None:
        """log_stage должен принимать параметр level (для совместимости с ILogger)."""
        adapter = LoggerAdapter()
        adapter.log_stage("ERROR_STAGE", "Critical error", level=logging.ERROR)
        
        # level не передаётся в infra_log_stage, но метод должен принимать его
        mock_log_stage.assert_called_once_with("ERROR_STAGE", "Critical error", logger_name=None)


class TestLoggerAdapterLogDebug:
    """Тесты для метода log_debug (реализован напрямую через logging)."""
    
    @patch("logging.getLogger")
    def test_log_debug_uses_root_logger_by_default(self, mock_get_logger: MagicMock) -> None:
        """log_debug без logger_name должен использовать root-логгер."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        adapter = LoggerAdapter()
        adapter.log_debug("Debug message")
        
        mock_get_logger.assert_called_once_with()
        mock_logger.debug.assert_called_once_with("Debug message")
    
    @patch("logging.getLogger")
    def test_log_debug_uses_named_logger(self, mock_get_logger: MagicMock) -> None:
        """log_debug с logger_name должен использовать именованный логгер."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        adapter = LoggerAdapter("debug_service")
        adapter.log_debug("Debug message")
        
        mock_get_logger.assert_called_once_with("debug_service")
        mock_logger.debug.assert_called_once_with("Debug message")


class TestLoggerAdapterIntegration:
    """Интеграционные тесты LoggerAdapter с реальным logging."""
    
    def test_log_info_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_info не должен вызывать исключений."""
        adapter = LoggerAdapter()
        with caplog.at_level(logging.INFO):
            adapter.log_info("Integration test info")
    
    def test_log_warning_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_warning не должен вызывать исключений."""
        adapter = LoggerAdapter()
        with caplog.at_level(logging.WARNING):
            adapter.log_warning("Integration test warning")
    
    def test_log_error_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_error не должен вызывать исключений."""
        adapter = LoggerAdapter()
        with caplog.at_level(logging.ERROR):
            adapter.log_error("Integration test error")
    
    def test_log_debug_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_debug не должен вызывать исключений."""
        adapter = LoggerAdapter()
        with caplog.at_level(logging.DEBUG):
            adapter.log_debug("Integration test debug")
    
    def test_log_stage_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_stage не должен вызывать исключений."""
        adapter = LoggerAdapter()
        with caplog.at_level(logging.INFO):
            adapter.log_stage("TEST", "Integration test stage")
