"""
Entity: Order (Ордер)

Представляет ордер/заявку на бирже согласно CCXT Order Structure.
Один ордер может иметь множество исполнений (Trade).
"""
import warnings
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class OrderFee:
    """Комиссия за ордер"""
    currency: str
    cost: float
    rate: float | None = None


@dataclass
class Order:
    """
    Ордер на бирже (CCXT Order Structure)

    Источник: https://docs.ccxt.com/#/?id=order-structure

    ВАЖНО: id - внутренний autoincrement для FK, exchange_order_id - от биржи
    """
    # Внутренний ID (autoincrement в БД)
    id: int | None = None                      # Внутренний PK (autoincrement)

    # Идентификация
    exchange_order_id: str | None = None       # ID ордера на бирже (получаем после создания)
    symbol: str = ""                           # Торговая пара 'BTC/USDT'
    timestamp: int = 0                         # Unix timestamp в миллисекундах
    datetime: str = ""                         # ISO8601 datetime
    status: str = ""                           # 'open', 'closed', 'canceled', 'expired', 'rejected'
    side: str = ""                             # 'buy' или 'sell'
    type: str = ""                             # 'market', 'limit'

    # Объемы и цены
    amount: float = 0.0                        # Запрошенный объем в базовой валюте
    price: float | None = None                 # Цена (может быть None для market ордеров)
    average: float | None = None               # Средняя цена исполнения
    filled: float = 0.0                        # Исполненный объем
    remaining: float = 0.0                     # Оставшийся объем
    cost: float = 0.0                          # filled * price

    # Дополнительные поля
    last_trade_timestamp: int | None = None    # Timestamp последнего трейда
    time_in_force: str | None = None           # 'GTC', 'IOC', 'FOK', 'PO'
    post_only: bool = False                    # Только maker ордер
    reduce_only: bool = False                  # Только для закрытия позиций

    # Триггерные цены (для стоп-ордеров)
    trigger_price: float | None = None         # Цена активации триггера

    # Комиссии и трейды
    fee: OrderFee | None = None                # Комиссия за ордер
    trades: list[str] = field(default_factory=list)  # Список ID трейдов

    # Оригинальный ответ биржи (deprecated — будет удалён в будущих версиях)
    info: dict[str, Any] = field(default_factory=dict)

    # Внутренние поля для связей
    deal_id: int | None = None                 # ID сделки (Deal), к которой относится ордер

    def is_open(self) -> bool:
        """Ордер открыт и ожидает исполнения"""
        return self.status == 'open'

    def is_closed(self) -> bool:
        """Ордер закрыт (полностью исполнен)"""
        return self.status == 'closed'

    def is_canceled(self) -> bool:
        """Ордер отменен"""
        return self.status == 'canceled'

    def is_filled(self) -> bool:
        """Ордер полностью исполнен.

        Учитывает dust-tolerance: биржа может исполнить чуть меньше
        запрошенного объёма из-за округления (например, 0.0107 вместо
        0.01073). Если разница меньше 0.1% — считаем исполненным.
        Также считаем исполненным, если биржа вернула status=closed.
        """
        if self.status == "closed":
            return True
        if self.amount == 0:
            return False
        # Dust tolerance: разница менее 0.1% от amount
        tolerance = self.amount * 0.001
        return self.filled >= (self.amount - tolerance)

    def is_partially_filled(self) -> bool:
        """Ордер частично исполнен"""
        return 0 < self.filled < self.amount

    def get_fill_percentage(self) -> float:
        """Процент исполнения (0.0 - 1.0)"""
        if self.amount == 0:
            return 0.0
        return min(self.filled / self.amount, 1.0)

    def calculate_total_cost(self) -> float:
        """Общая стоимость с учетом комиссий"""
        base_cost = self.cost
        fee_cost = self.fee.cost if self.fee else 0.0
        return base_cost + fee_cost

    def update_from_exchange(self, ccxt_response: dict[str, Any]) -> bool:
        """Обогатить ордер данными от биржи — мутация на месте.

        Применяет monotonic timestamp guard: если входящий timestamp
        не новее текущего, обновление отклоняется (защита от stale data
        при конкурентных WebSocket-апдейтах).

        Args:
            ccxt_response: Сырой CCXT unified order dict

        Returns:
            True если данные применены, False если отклонены как устаревшие
        """
        incoming_ts = int(ccxt_response.get("timestamp") or 0)
        if self.timestamp and incoming_ts < self.timestamp:
            return False  # reject stale data (equal ts is OK — response to our request)

        self.exchange_order_id = str(ccxt_response["id"])
        self.status = ccxt_response["status"]
        self.filled = float(ccxt_response.get("filled", 0.0))
        self.remaining = float(ccxt_response.get("remaining", 0.0))
        self.cost = float(ccxt_response.get("cost", 0.0))
        self.average = (
            float(ccxt_response["average"]) if ccxt_response.get("average") else None
        )
        self.timestamp = incoming_ts
        self.datetime = ccxt_response.get("datetime", "")
        self.last_trade_timestamp = (
            int(ccxt_response["lastTradeTimestamp"])
            if ccxt_response.get("lastTradeTimestamp")
            else None
        )
        self.time_in_force = ccxt_response.get("timeInForce")
        self.post_only = bool(ccxt_response.get("postOnly", False))
        self.reduce_only = bool(ccxt_response.get("reduceOnly", False))
        self.trigger_price = (
            float(ccxt_response["triggerPrice"])
            if ccxt_response.get("triggerPrice")
            else None
        )

        # Комиссия
        if ccxt_response.get("fee"):
            fee_data = ccxt_response["fee"]
            self.fee = OrderFee(
                currency=fee_data.get("currency", ""),
                cost=float(fee_data.get("cost", 0.0)),
                rate=float(fee_data["rate"]) if fee_data.get("rate") else None,
            )

        # Трейды
        if ccxt_response.get("trades"):
            self.trades = [str(t.get("id", "")) for t in ccxt_response["trades"]]

        # info deprecated, но пока сохраняем для обратной совместимости
        self.info = ccxt_response.get("info", {})

        return True

    @classmethod
    def from_ccxt(cls, ccxt_order: dict[str, Any], deal_id: int | None = None) -> "Order":
        """Создает Order из CCXT ответа биржи.

        .. deprecated::
            Используйте конструктор ``Order(...)`` + ``update_from_exchange()``.
            Этот метод будет удалён в будущих версиях.

        Args:
            ccxt_order: Ответ от exchange.create_order() или exchange.fetch_order()
            deal_id: Опционально - ID сделки для связи
        """
        warnings.warn(
            "Order.from_ccxt() is deprecated. "
            "Use Order(...) + order.update_from_exchange(ccxt_dict) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Парсим комиссию
        fee = None
        if ccxt_order.get('fee'):
            fee_data = ccxt_order['fee']
            fee = OrderFee(
                currency=fee_data.get('currency', ''),
                cost=float(fee_data.get('cost', 0.0)),
                rate=float(fee_data['rate']) if fee_data.get('rate') else None
            )

        # Извлекаем ID трейдов если есть
        trade_ids = []
        if ccxt_order.get('trades'):
            trade_ids = [str(t.get('id', '')) for t in ccxt_order['trades']]

        return cls(
            id=None,  # Autoincrement в БД
            exchange_order_id=str(ccxt_order['id']),  # ID от биржи
            symbol=ccxt_order['symbol'],
            timestamp=int(ccxt_order['timestamp']),
            datetime=ccxt_order['datetime'],
            status=ccxt_order['status'],
            side=ccxt_order['side'],
            type=ccxt_order['type'],
            amount=float(ccxt_order['amount']),
            price=float(ccxt_order['price']) if ccxt_order.get('price') else None,
            average=float(ccxt_order['average']) if ccxt_order.get('average') else None,
            filled=float(ccxt_order.get('filled', 0.0)),
            remaining=float(ccxt_order.get('remaining', 0.0)),
            cost=float(ccxt_order.get('cost', 0.0)),
            last_trade_timestamp=int(ccxt_order['lastTradeTimestamp']) if ccxt_order.get('lastTradeTimestamp') else None,
            time_in_force=ccxt_order.get('timeInForce'),
            post_only=bool(ccxt_order.get('postOnly', False)),
            reduce_only=bool(ccxt_order.get('reduceOnly', False)),
            trigger_price=float(ccxt_order['triggerPrice']) if ccxt_order.get('triggerPrice') else None,
            fee=fee,
            trades=trade_ids,
            info=ccxt_order.get('info', {}),
            deal_id=deal_id
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Order":
        """Десериализовать ордер из dict (например, из БД).

        Формат совместим с :meth:`to_dict`.
        """

        fee_data = data.get("fee")
        fee = None
        if isinstance(fee_data, dict):
            fee = OrderFee(
                currency=str(fee_data.get("currency", "")),
                cost=float(fee_data.get("cost", 0.0)),
                rate=float(fee_data["rate"]) if fee_data.get("rate") is not None else None,
            )

        trades = data.get("trades") or []
        trade_ids = [str(x) for x in trades] if isinstance(trades, list) else []

        info = data.get("info")
        info_dict = info if isinstance(info, dict) else {}

        return cls(
            id=int(data["id"]) if data.get("id") is not None else None,
            exchange_order_id=str(data["exchange_order_id"]) if data.get("exchange_order_id") is not None else None,
            symbol=str(data["symbol"]),
            timestamp=int(data["timestamp"]),
            datetime=str(data["datetime"]),
            status=str(data["status"]),
            side=str(data["side"]),
            type=str(data["type"]),
            amount=float(data["amount"]),
            price=float(data["price"]) if data.get("price") is not None else None,
            average=float(data["average"]) if data.get("average") is not None else None,
            filled=float(data.get("filled", 0.0)),
            remaining=float(data.get("remaining", 0.0)),
            cost=float(data.get("cost", 0.0)),
            last_trade_timestamp=(
                int(data["last_trade_timestamp"]) if data.get("last_trade_timestamp") is not None else None
            ),
            time_in_force=(
                str(data["time_in_force"]) if data.get("time_in_force") is not None else None
            ),
            post_only=bool(data.get("post_only", False)),
            reduce_only=bool(data.get("reduce_only", False)),
            trigger_price=float(data["trigger_price"]) if data.get("trigger_price") is not None else None,
            fee=fee,
            trades=trade_ids,
            info=info_dict,
            deal_id=int(data["deal_id"]) if data.get("deal_id") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в словарь"""
        return {
            'id': self.id,
            'exchange_order_id': self.exchange_order_id,
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'datetime': self.datetime,
            'status': self.status,
            'side': self.side,
            'type': self.type,
            'amount': self.amount,
            'price': self.price,
            'average': self.average,
            'filled': self.filled,
            'remaining': self.remaining,
            'cost': self.cost,
            'last_trade_timestamp': self.last_trade_timestamp,
            'time_in_force': self.time_in_force,
            'post_only': self.post_only,
            'reduce_only': self.reduce_only,
            'trigger_price': self.trigger_price,
            'fee': {
                'currency': self.fee.currency,
                'cost': self.fee.cost,
                'rate': self.fee.rate
            } if self.fee else None,
            'trades': self.trades,
            'deal_id': self.deal_id,
            'info': self.info
        }

    def __repr__(self) -> str:
        fill_pct = self.get_fill_percentage() * 100
        return (
            f"Order(id='{self.id}', symbol='{self.symbol}', "
            f"side='{self.side}', type='{self.type}', status='{self.status}', "
            f"amount={self.amount}, filled={self.filled} ({fill_pct:.1f}%), "
            f"price={self.price}, deal_id={self.deal_id})"
        )
