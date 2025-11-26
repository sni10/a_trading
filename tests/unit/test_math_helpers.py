"""Демонстрационные тесты для показа структуры.

Этот файл показывает, что тесты могут быть на разных уровнях вложенности.
"""

import pytest


@pytest.mark.unit
def test_simple_addition():
    """Простейший тест для демонстрации."""
    assert 2 + 2 == 4


@pytest.mark.unit
def test_simple_multiplication():
    """Ещё один простой тест."""
    assert 3 * 7 == 21
