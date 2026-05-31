"""CLI-фасад для запуска офлайн-бэктеста.

Использование:
    python backtest.py BTC/USDT --from 2025-01-01 --to 2025-03-01 --timeframe 1h --balance 1000

Опции:
    --from       Начало периода (YYYY-MM-DD).  Обязательно.
    --to         Конец периода (YYYY-MM-DD).   По умолчанию — сегодня.
    --timeframe  Таймфрейм свечей (1h).        По умолчанию: 1h.
    --balance    Стартовый баланс USDT.        По умолчанию: 1000.
    --buy-fee    Комиссия на покупку, %.       По умолчанию: 0.1.
    --sell-fee   Комиссия на продажу, %.       По умолчанию: 0.1.
    --no-cache   Не использовать кэш свечей.
    --csv        Сохранить equity-кривую в файл CSV.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone

from src.application.backtest.backtest_config import BacktestConfig
from src.application.use_cases.run_backtest import fetch_candles, run_backtest
from src.config.config_loader import load_config
from src.infrastructure.connectors.ccxt_pro_exchange_connector import (
    CcxtProExchangeConnector,
)


def _parse_date(date_str: str) -> int:
    """Преобразовать строку YYYY-MM-DD в Unix timestamp в мс (UTC)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Построить парсер аргументов CLI."""
    parser = argparse.ArgumentParser(
        prog="backtest.py",
        description="Офлайн-бэктест торговой стратегии на исторических OHLCV-данных.",
    )
    parser.add_argument("symbol", help="Торговая пара (например BTC/USDT)")
    parser.add_argument("--from", dest="date_from", required=True, metavar="DATE",
                        help="Начало периода YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, metavar="DATE",
                        help="Конец периода YYYY-MM-DD (по умолчанию: сегодня)")
    parser.add_argument("--timeframe", default="1h",
                        help="Таймфрейм свечей (по умолчанию: 1h)")
    parser.add_argument("--balance", type=float, default=1000.0,
                        help="Стартовый баланс в USDT (по умолчанию: 1000)")
    parser.add_argument("--buy-fee", type=float, default=0.1, dest="buy_fee",
                        help="Комиссия на покупку, %% (по умолчанию: 0.1)")
    parser.add_argument("--sell-fee", type=float, default=0.1, dest="sell_fee",
                        help="Комиссия на продажу, %% (по умолчанию: 0.1)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Не использовать кэш свечей на диске")
    parser.add_argument("--csv", dest="csv_path", default=None, metavar="FILE",
                        help="Сохранить equity-кривую в CSV-файл")
    return parser


def _save_equity_csv(equity_curve: list[tuple[int, float]], path: str) -> None:
    """Сохранить equity-кривую в CSV-файл."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp_ms", "equity"])
        writer.writerows(equity_curve)
    print(f"Equity-кривая сохранена в: {path}")


async def _main(argv: list[str]) -> None:
    """Точка входа: разбор аргументов, загрузка данных, прогон, вывод отчёта."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv[1:])

    since_ms = _parse_date(args.date_from)
    until_ms = _parse_date(args.date_to) if args.date_to else None

    bt_config = BacktestConfig(
        symbol=args.symbol.upper(),
        timeframe=args.timeframe,
        since_ms=since_ms,
        until_ms=until_ms,
        initial_balance=args.balance,
        buy_fee_percent=args.buy_fee,
        sell_fee_percent=args.sell_fee,
        use_cache=not args.no_cache,
    )
    bt_config.validate()

    app_config = load_config()
    connector = CcxtProExchangeConnector(app_config)

    print(f"Загрузка свечей {bt_config.symbol} [{bt_config.timeframe}] "
          f"с {args.date_from} по {args.date_to or 'сегодня'}...")
    candles = await fetch_candles(connector, bt_config)
    print(f"Загружено {len(candles)} свечей.")

    print("Запуск бэктеста...")
    report = run_backtest(app_config, bt_config, candles)

    print(report)

    if args.csv_path:
        _save_equity_csv(report.equity_curve, args.csv_path)


def main() -> None:
    """Запустить CLI."""
    asyncio.run(_main(sys.argv))


if __name__ == "__main__":
    main()
