import pytest

from main import _parse_cli_pair


def test_parse_cli_pair_valid_symbol():
    """Явно указанный символ возвращается в верхнем регистре."""
    symbol = _parse_cli_pair(["python", "BTC/USDT"])
    assert symbol == "BTC/USDT"


def test_parse_cli_pair_no_args_returns_none():
    """Если пара не указана, возвращается None (пара берётся из БД)."""
    assert _parse_cli_pair([]) is None
    assert _parse_cli_pair(["python"]) is None


@pytest.mark.parametrize(
    "argv",
    [
        ["python", ""],  # Пустая строка
        ["python", "BTC-USDT"],  # Неправильный разделитель
        ["python", "BTC/USDT/EXTRA"],  # Слишком много разделителей
        ["python", "BTCUSDT"],  # Нет разделителя
    ],
)
def test_parse_cli_pair_invalid_format_exits(argv):
    """Невалидный формат символа вызывает SystemExit."""
    with pytest.raises(SystemExit):
        _parse_cli_pair(argv)
