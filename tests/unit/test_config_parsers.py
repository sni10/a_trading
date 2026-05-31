"""Юнит-тесты для парсеров значений конфигурации."""

from __future__ import annotations

import pytest

from src.config.config_parsers import parse_bool, parse_float, parse_int


class TestParseInt:
    """Тесты для parse_int."""

    def test_parse_valid_int(self):
        assert parse_int("42", 0) == 42
        assert parse_int("0", 10) == 0
        assert parse_int("-5", 10) == -5

    def test_parse_none_returns_default(self):
        assert parse_int(None, 100) == 100

    def test_parse_empty_string_returns_default(self):
        assert parse_int("", 50) == 50

    def test_parse_invalid_int_raises_error(self):
        with pytest.raises(ValueError, match="Invalid int value"):
            parse_int("not_a_number", 0)

        with pytest.raises(ValueError, match="Invalid int value"):
            parse_int("3.14", 0)


class TestParseFloat:
    """Тесты для parse_float."""

    def test_parse_valid_float(self):
        assert parse_float("3.14", 0.0) == 3.14
        assert parse_float("0.5", 1.0) == 0.5
        assert parse_float("-2.5", 1.0) == -2.5

    def test_parse_int_as_float(self):
        assert parse_float("42", 0.0) == 42.0

    def test_parse_none_returns_default(self):
        assert parse_float(None, 1.5) == 1.5

    def test_parse_empty_string_returns_default(self):
        assert parse_float("", 2.5) == 2.5

    def test_parse_invalid_float_raises_error(self):
        with pytest.raises(ValueError, match="Invalid float value"):
            parse_float("not_a_number", 0.0)


class TestParseBool:
    """Тесты для parse_bool."""

    def test_parse_true_values(self):
        for value in ["1", "true", "True", "TRUE", "yes", "YES", "y", "Y", "on", "ON"]:
            assert parse_bool(value, False) is True, f"Failed for: {value}"

    def test_parse_false_values(self):
        for value in ["0", "false", "False", "FALSE", "no", "NO", "n", "N", "off", "OFF"]:
            assert parse_bool(value, True) is False, f"Failed for: {value}"

    def test_parse_none_returns_default(self):
        assert parse_bool(None, True) is True
        assert parse_bool(None, False) is False

    def test_parse_empty_string_returns_default(self):
        assert parse_bool("", True) is True
        assert parse_bool("", False) is False

    def test_parse_with_whitespace(self):
        assert parse_bool("  true  ", False) is True
        assert parse_bool("  false  ", True) is False

    def test_parse_invalid_bool_raises_error(self):
        with pytest.raises(ValueError, match="Invalid bool value"):
            parse_bool("maybe", False)

        with pytest.raises(ValueError, match="Invalid bool value"):
            parse_bool("2", False)
