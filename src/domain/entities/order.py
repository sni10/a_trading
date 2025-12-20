"""
Entity: Order (Ордер)

Представляет ордер/заявку на бирже согласно CCXT Order Structure.
Один ордер может иметь множество исполнений (Trade).
"""
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
    """
    # Обязательные поля
    id: str                                    # ID ордера на бирже
    symbol: str                                # Торговая пара 'BTC/USDT'
    timestamp: int                             # Unix timestamp в миллисекундах
    datetime: str                              # ISO8601 datetime
    status: str                                # 'open', 'closed', 'canceled', 'expired', 'rejected'
    side: str                                  # 'buy' или 'sell'
    type: str                                  # 'market', 'limit'

    # Объемы и цены
    amount: float                              # Запрошенный объем в базовой валюте
    price: float | None = None                 # Цена (может быть None для market ордеров)
    average: float | None = None               # Средняя цена исполнения
    filled: float = 0.0                        # Исполненный объем
    remaining: float = 0.0                     # Оставшийся объем
    cost: float = 0.0                          # filled * price

    # Дополнительные поля
    client_order_id: str | None = None         # Клиентский ID (для идемпотентности)
    last_trade_timestamp: int | None = None    # Timestamp последнего трейда
    time_in_force: str | None = None           # 'GTC', 'IOC', 'FOK', 'PO'
    post_only: bool = False                    # Только maker ордер
    reduce_only: bool = False                  # Только для закрытия позиций

    # Триггерные цены (для стоп-ордеров)
    trigger_price: float | None = None         # Цена активации триггера
    stop_loss_price: float | None = None       # Цена стоп-лосс
    take_profit_price: float | None = None     # Цена тейк-профит

    # Комиссии и трейды
    fee: OrderFee | None = None                # Комиссия за ордер
    trades: list[str] = field(default_factory=list)  # Список ID трейдов

    # Оригинальный ответ биржи
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
        """Ордер полностью исполнен"""
        return self.filled >= self.amount

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

    @classmethod
    def from_ccxt(cls, ccxt_order: dict[str, Any], deal_id: int | None = None) -> "Order":
        """
        Создает Order из CCXT ответа биржи

        Args:
            ccxt_order: Ответ от exchange.create_order() или exchange.fetch_order()
            deal_id: Опционально - ID сделки для связи
        """
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
            id=str(ccxt_order['id']),
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
            client_order_id=ccxt_order.get('clientOrderId'),
            last_trade_timestamp=int(ccxt_order['lastTradeTimestamp']) if ccxt_order.get('lastTradeTimestamp') else None,
            time_in_force=ccxt_order.get('timeInForce'),
            post_only=bool(ccxt_order.get('postOnly', False)),
            reduce_only=bool(ccxt_order.get('reduceOnly', False)),
            trigger_price=float(ccxt_order['triggerPrice']) if ccxt_order.get('triggerPrice') else None,
            stop_loss_price=float(ccxt_order['stopLossPrice']) if ccxt_order.get('stopLossPrice') else None,
            take_profit_price=float(ccxt_order['takeProfitPrice']) if ccxt_order.get('takeProfitPrice') else None,
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
            id=str(data["id"]),
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
            client_order_id=(
                str(data["client_order_id"]) if data.get("client_order_id") is not None else None
            ),
            last_trade_timestamp=(
                int(data["last_trade_timestamp"]) if data.get("last_trade_timestamp") is not None else None
            ),
            time_in_force=(
                str(data["time_in_force"]) if data.get("time_in_force") is not None else None
            ),
            post_only=bool(data.get("post_only", False)),
            reduce_only=bool(data.get("reduce_only", False)),
            trigger_price=float(data["trigger_price"]) if data.get("trigger_price") is not None else None,
            stop_loss_price=float(data["stop_loss_price"]) if data.get("stop_loss_price") is not None else None,
            take_profit_price=float(data["take_profit_price"]) if data.get("take_profit_price") is not None else None,
            fee=fee,
            trades=trade_ids,
            info=info_dict,
            deal_id=int(data["deal_id"]) if data.get("deal_id") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в словарь"""
        return {
            'id': self.id,
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
            'client_order_id': self.client_order_id,
            'last_trade_timestamp': self.last_trade_timestamp,
            'time_in_force': self.time_in_force,
            'post_only': self.post_only,
            'reduce_only': self.reduce_only,
            'trigger_price': self.trigger_price,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price,
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
