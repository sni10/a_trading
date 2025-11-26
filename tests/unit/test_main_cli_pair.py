import pytest

from main import _parse_cli_pair


def test_parse_cli_pair_valid_symbol():
    symbol = _parse_cli_pair(["python", "BTC/USDT"])
    assert symbol == "BTC/USDT"


@pytest.mark.parametrize("argv", [[], ["python"], ["python", ""], ["python", "BTC-USDT"], ["python", "BTC/USDT/EXTRA"]])
def test_parse_cli_pair_invalid_argv_exits(argv):
    with pytest.raises(SystemExit):
        _parse_cli_pair(argv)
