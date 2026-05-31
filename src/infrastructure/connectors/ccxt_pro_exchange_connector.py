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

import base64
import hashlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from src.config.config import AppConfig
from src.domain.interfaces.exchange_connector import IExchangeConnector
from src.infrastructure.logging.logging_setup import log_stage


try:  # pragma: no cover - защитный импорт для окружений без ccxt.pro
    import ccxt.pro as ccxt  # type: ignore[import]
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
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

        # Ed25519 авторизация для Binance (если есть приватный ключ)
        self._ed25519_private_key = None
        self._api_key = api_key
        self._original_sign = self._exchange.sign  # Сохраняем оригинальный метод
        if exchange_id == "binance" and api_key:
            ed25519_key_path = Path("secure_api_keys/binance/id_ed25519.pem")
            if ed25519_key_path.exists():
                try:
                    with open(ed25519_key_path, "rb") as f:
                        self._ed25519_private_key = load_pem_private_key(
                            data=f.read(), password=None
                        )

                    # Переопределяем метод sign для использования Ed25519
                    self._exchange.sign = self._ed25519_sign_wrapper

                    log_stage(
                        "BOOT",
                        "✅ Ed25519 авторизация активирована",
                        key_path=str(ed25519_key_path),
                    )
                except Exception as e:
                    log_stage(
                        "BOOT",
                        f"⚠️ Не удалось загрузить Ed25519 ключ: {e}",
                        key_path=str(ed25519_key_path),
                    )

        log_stage(
            "BOOT",
            "Создан CcxtProExchangeConnector",
            exchange_id=exchange_id,
            sandbox=getattr(config, "sandbox_mode", False),
            has_api_key=bool(api_key and api_secret),
            ed25519=self._ed25519_private_key is not None,
        )

    def _ed25519_sign_wrapper(self, path, api="public", method="GET", params=None, headers=None, body=None):
        """Wrapper для подписи запросов с Ed25519 (Binance testnet)."""
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        # Для приватных запросов используем Ed25519
        if api == "private" and self._ed25519_private_key:
            import urllib.parse
            import time

            params = dict(params)
            params["timestamp"] = int(time.time() * 1000)

            # Создаём payload для подписи
            payload = urllib.parse.urlencode(params, encoding="UTF-8")
            signature = base64.b64encode(
                self._ed25519_private_key.sign(payload.encode("ASCII"))
            ).decode("utf-8")

            params["signature"] = signature
            headers["X-MBX-APIKEY"] = self._api_key

            # Формируем URL с параметрами
            url = self._exchange.urls["api"][api] + "/" + path
            if method == "GET" or method == "DELETE":
                url += "?" + urllib.parse.urlencode(params)
                body = None
            else:
                body = urllib.parse.urlencode(params)

            return {"url": url, "method": method, "body": body, "headers": headers}

        # Для публичных запросов используем стандартную подпись
        return self._original_sign(path, api, method, params, headers, body)

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

    async def fetch_balance(self) -> dict:
        """Запросить балансы всех валют на аккаунте через ``fetch_balance``.

        Возвращает упрощённый формат: валюта -> {free, used, total}.
        """

        balance_raw = await self._exchange.fetch_balance()

        # CCXT возвращает сложную структуру, извлекаем только нужное
        result = {}
        for currency, info in balance_raw.items():
            if currency in ("free", "used", "total", "info", "timestamp", "datetime"):
                # Пропускаем служебные поля CCXT
                continue
            if isinstance(info, dict):
                result[currency] = {
                    "free": float(info.get("free", 0.0)),
                    "used": float(info.get("used", 0.0)),
                    "total": float(info.get("total", 0.0)),
                }
        return result

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict | None = None,
    ) -> dict:
        """Создать ордер на бирже через ccxt ``create_order()``.

        Args:
            symbol: Торговая пара (например 'BTC/USDT')
            order_type: Тип ордера ('limit', 'market')
            side: Сторона ('buy', 'sell')
            amount: Количество базовой валюты
            price: Цена (для limit ордеров)
            params: Дополнительные параметры (clientOrderId и т.д.)

        Returns:
            CCXT Order Structure
        """
        params = params or {}

        log_stage(
            "EXEC",
            f"Создание ордера на бирже",
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price,
        )

        # CCXT API: create_order(symbol, type, side, amount, price=None, params={})
        order = await self._exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params,
        )

        log_stage(
            "EXEC",
            f"✅ Ордер создан",
            exchange_order_id=order.get("id"),
            status=order.get("status"),
        )

        return order

    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        """Отменить ордер на бирже через ccxt ``cancel_order()``.

        Args:
            order_id: ID ордера на бирже
            symbol: Торговая пара

        Returns:
            CCXT Order Structure отменённого ордера
        """
        log_stage(
            "EXEC",
            f"Отмена ордера",
            exchange_order_id=order_id,
            symbol=symbol,
        )

        order = await self._exchange.cancel_order(order_id, symbol)

        log_stage(
            "EXEC",
            f"✅ Ордер отменён",
            exchange_order_id=order_id,
            status=order.get("status"),
        )

        return order

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        """Запросить статус ордера через ccxt ``fetch_order()``.

        Args:
            order_id: ID ордера на бирже
            symbol: Торговая пара

        Returns:
            CCXT Order Structure
        """
        order = await self._exchange.fetch_order(order_id, symbol)
        return order

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: int | None = None,
        limit: int = 500,
    ) -> list[list]:
        """Загрузить исторические OHLCV-свечи через ccxt ``fetch_ohlcv()``.

        Выполняет постраничную докачку: если свечей меньше чем запрошено
        и биржа вернула полную страницу, делает дополнительные запросы.

        Args:
            symbol: Торговая пара (например 'BTC/USDT')
            timeframe: Таймфрейм ('1m', '5m', '1h', '4h', '1d' и т.д.)
            since: Unix timestamp в мс — начало периода (None = последние limit свечей)
            limit: Максимальное число свечей за один запрос

        Returns:
            Список свечей: [[timestamp_ms, open, high, low, close, volume], ...]
        """
        all_candles: list[list] = []
        current_since = since
        page_limit = min(limit, 1000)  # биржи часто ограничивают до 1000

        while True:
            candles = await self._exchange.fetch_ohlcv(
                symbol, timeframe, since=current_since, limit=page_limit
            )
            if not candles:
                break
            all_candles.extend(candles)
            # Если запрос без since — возвращаем как есть
            if since is None:
                break
            # Если страница неполная — данных больше нет
            if len(candles) < page_limit:
                break
            # Следующая страница: after last timestamp
            current_since = candles[-1][0] + 1

        return all_candles


__all__ = ["CcxtProExchangeConnector"]
