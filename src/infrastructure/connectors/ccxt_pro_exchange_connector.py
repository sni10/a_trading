from __future__ import annotations

"""Минимальный коннектор к бирже на базе ccxt.pro.

Класс :class:`CcxtProExchangeConnector` реализует протокол
``IExchangeConnector`` и инкапсулирует детали работы с ``ccxt.pro``.

Цели:

* домен не импортирует ``ccxt`` напрямую – только этот модуль знает о
  конкретной библиотеке;
* включение sandbox‑режима через ``AppConfig``;
* приведение структур тикеров и стакана к унифицированному формату,
  описанному в планах и ``doc/ccxt_data_structures.md``.

На этом этапе реализация предельно упрощена и ориентирована на будущие
интеграционные тесты. При отсутствии установленного ``ccxt.pro`` класс
поднимает понятное исключение при инициализации.
"""

from collections.abc import AsyncIterator
from typing import Any

from src.config.config import AppConfig
from src.infrastructure.connectors.interfaces.exchange_connector import (
    IExchangeConnector,
)
from src.infrastructure.logging.logging_setup import log_stage


try:  # pragma: no cover - защитный импорт для окружений без ccxt.pro
    import ccxt.pro as ccxt  # type: ignore[import]
except ModuleNotFoundError as exc:  # pragma: no cover - пакет реально не установлен
    # Классический кейс: в окружении нет ``ccxt.pro`` как модуля.
    ccxt = None  # type: ignore[assignment]
    _ccxt_import_error = exc
except Exception as exc:  # pragma: no cover - другие ошибки импорта (лицензия, версия и т.п.)
    # В этом случае модуль физически есть (``import ccxt.pro`` найден),
    # но при инициализации внутри него произошла ошибка (например,
    # просроченная лицензия, несовместимая версия, отсутствующие
    # зависимости). Сохраняем исходное исключение, чтобы показать его
    # в тексте ошибки при создании коннектора.
    ccxt = None  # type: ignore[assignment]
    _ccxt_import_error = exc
else:  # pragma: no cover - ветка с успешно установленным ccxt.pro
    _ccxt_import_error = None


class CcxtProExchangeConnector(IExchangeConnector):
    """Минимальный пример коннектора под ccxt.pro.

    В реальном коде сюда добавятся: детальная обработка ошибок,
    таймауты, backoff и расширенный лог.
    """

    def __init__(self, config: AppConfig) -> None:
        if ccxt is None:
            # Отложенное поднятие ошибки при попытке реального использования.
            #
            # Если ``ccxt`` / ``ccxt.pro`` действительно не установлены в
            # активном окружении, то ``_ccxt_import_error`` будет
            # ``ModuleNotFoundError``. В этом случае даём максимально
            # прикладную подсказку по установке. Во всех остальных
            # случаях (ошибка лицензии, несовместимая версия,
            # проблемы внутри модуля) мы не маскируем исходную причину,
            # а включаем её в текст.

            if isinstance(_ccxt_import_error, ModuleNotFoundError):
                detailed_msg = (
                    "Невозможно создать CcxtProExchangeConnector: пакет 'ccxt' или "
                    "'ccxt.pro' не найден в активном окружении. "
                    "Убедитесь, что вы активировали правильное virtualenv и "
                    "выполнили 'pip install ccxt ccxtpro'. Исходная ошибка: "
                    f"{_ccxt_import_error!r}"
                )
            else:
                base_msg = (
                    "Невозможно создать CcxtProExchangeConnector: ошибка импорта ccxt.pro"
                )
                if _ccxt_import_error is not None:
                    detailed_msg = f"{base_msg}: {_ccxt_import_error!r}"
                else:  # на всякий случай, не должно происходить
                    detailed_msg = base_msg

            raise RuntimeError(detailed_msg) from _ccxt_import_error

        self._config = config

        exchange_id = getattr(config, "exchange_id", "binance")
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"Unknown ccxt.pro exchange_id: {exchange_id!r}")

        exchange_cls = getattr(ccxt, exchange_id)

        # Базовые параметры клиента ccxt.pro. Для получения только
        # публичных данных (тикеры/стакан) достаточно пустого словаря,
        # но если в :class:`AppConfig` заданы API‑ключи, используем их.
        params: dict[str, Any] = {}

        api_key = getattr(config, "exchange_api_key", None)
        api_secret = getattr(config, "exchange_api_secret", None)
        if api_key and api_secret:
            params["apiKey"] = api_key
            params["secret"] = api_secret

        self._exchange = exchange_cls(params)

        if getattr(config, "sandbox_mode", False):
            # см. doc/ccxt_data_structures.md и официальную документацию ccxt
            self._exchange.set_sandbox_mode(True)

        log_stage(
            "BOOT",
            "Создан CcxtProExchangeConnector",
            exchange_id=exchange_id,
            sandbox=getattr(config, "sandbox_mode", False),
            has_api_key=bool(api_key and api_secret),
        )

    async def close(self) -> None:
        await self._exchange.close()

    async def stream_ticks(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        """Асинхронный поток тиков через ``watch_tickers``.

        На выходе всегда выдаётся тикер, совместимый с структурой
        CCXT ``fetch_ticker()`` (см. ``doc/ccxt_data_structures.md``),
        как минимум с полями:

        * ``symbol``, ``timestamp``, ``datetime``;
        * ``last``, ``open``, ``high``, ``low``, ``close``;
        * ``bid``, ``ask``, ``baseVolume``, ``quoteVolume``.

        Остальные поля оригинального CCXT‑тикера при необходимости
        могут быть добавлены без изменения контракта домена.
        """

        symbols = [symbol]

        while True:
            # Вызов ``watch_tickers`` возвращает dict symbol -> ticker.
            tickers: dict[str, Any] = await self._exchange.watch_tickers(symbols)

            raw = tickers[symbol]

            # Приведение к минимальному контракту CCXT‑тикера.
            yield {
                "symbol": str(raw.get("symbol", symbol)),
                "timestamp": int(raw["timestamp"]),
                "datetime": str(raw["datetime"]),
                "last": float(raw["last"]),
                "open": float(raw["open"]),
                "high": float(raw["high"]),
                "low": float(raw["low"]),
                "close": float(raw["close"]),
                "bid": float(raw["bid"]),
                "ask": float(raw["ask"]),
                "baseVolume": float(raw["baseVolume"]),
                "quoteVolume": float(raw["quoteVolume"]),
            }

    async def fetch_order_book(self, symbol: str) -> dict:
        """Вернуть снепшот стакана через HTTP ``fetch_order_book``.

        Формат результата приводится к унифицированному контракту
        ``IExchangeConnector.fetch_order_book``.
        """

        order_book = await self._exchange.fetch_order_book(symbol)

        return {
            "bids": order_book["bids"],
            "asks": order_book["asks"],
            "symbol": order_book["symbol"],
            "timestamp": order_book["timestamp"],
            "datetime": order_book["datetime"],
            "nonce": order_book.get("nonce"),
        }


__all__ = ["CcxtProExchangeConnector"]
