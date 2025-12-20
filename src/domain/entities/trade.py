"""
Entity: Trade (Исполнение ордера)

Представляет факт исполнения ордера на бирже согласно CCXT Trade Structure.
Один ордер может иметь множество трейдов (при частичном исполнении).
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TradeFee:
    """Комиссия за трейд"""
    cost: float
    currency: str
    rate: float | None = None


@dataclass
class Trade:
    """
    Исполнение ордера (CCXT Trade Structure)

    Trade - это факт обмена валют на бирже.
    Один Order может содержать несколько Trade при частичном исполнении.

    Источник: https://docs.ccxt.com/#/?id=trade-structure
    """
    # Обязательные поля
    id: str                                    # ID трейда на бирже
    order: str                                 # ID ордера, к которому относится трейд
    timestamp: int                             # Unix timestamp в миллисекундах
    datetime: str                              # ISO8601 datetime
    symbol: str                                # Торговая пара 'BTC/USDT'
    side: str                                  # 'buy' или 'sell'
    price: float                               # Цена исполнения
    amount: float                              # Объем в базовой валюте

    # Расчетные поля
    cost: float                                # price * amount (общая стоимость)
    taker_or_maker: str | None = None          # 'taker' или 'maker'

    # Дополнительные поля
    type: str | None = None                    # 'market', 'limit' или None
    fee: TradeFee | None = None                # Комиссия за трейд
    fees: list[TradeFee] = field(default_factory=list)  # Массив комиссий (если несколько валют)

    # Оригинальный ответ биржи
    info: dict[str, Any] = field(default_factory=dict)

    def is_maker(self) -> bool:
        """Была ли роль maker в трейде"""
        return self.taker_or_maker == 'maker'

    def is_taker(self) -> bool:
        """Была ли роль taker в трейде"""
        return self.taker_or_maker == 'taker'

    def is_buy(self) -> bool:
        """Трейд на покупку"""
        return self.side == 'buy'

    def is_sell(self) -> bool:
        """Трейд на продажу"""
        return self.side == 'sell'

    def get_total_fee_cost(self) -> float:
        """Общая комиссия по всем валютам"""
        total = 0.0
        if self.fee:
            total += self.fee.cost
        for fee in self.fees:
            total += fee.cost
        return total

    def get_total_cost_with_fees(self) -> float:
        """Общая стоимость с учетом комиссий"""
        return self.cost + self.get_total_fee_cost()

    @classmethod
    def from_ccxt(cls, ccxt_trade: dict[str, Any]) -> "Trade":
        """
        Создает Trade из CCXT ответа биржи

        Args:
            ccxt_trade: Ответ от exchange.fetch_trades() или order['trades']
        """
        # Парсим основную комиссию
        fee = None
        if ccxt_trade.get('fee'):
            fee_data = ccxt_trade['fee']
            fee = TradeFee(
                cost=float(fee_data.get('cost', 0.0)),
                currency=fee_data.get('currency', ''),
                rate=float(fee_data['rate']) if fee_data.get('rate') else None
            )

        # Парсим дополнительные комиссии
        fees_list = []
        if ccxt_trade.get('fees'):
            for fee_data in ccxt_trade['fees']:
                fees_list.append(TradeFee(
                    cost=float(fee_data.get('cost', 0.0)),
                    currency=fee_data.get('currency', ''),
                    rate=float(fee_data['rate']) if fee_data.get('rate') else None
                ))

        return cls(
            id=str(ccxt_trade['id']),
            order=str(ccxt_trade.get('order', '')),
            timestamp=int(ccxt_trade['timestamp']),
            datetime=ccxt_trade['datetime'],
            symbol=ccxt_trade['symbol'],
            side=ccxt_trade['side'],
            price=float(ccxt_trade['price']),
            amount=float(ccxt_trade['amount']),
            cost=float(ccxt_trade['cost']),
            taker_or_maker=ccxt_trade.get('takerOrMaker'),
            type=ccxt_trade.get('type'),
            fee=fee,
            fees=fees_list,
            info=ccxt_trade.get('info', {})
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trade":
        """Десериализовать трейд из dict (например, из БД).

        Формат совместим с :meth:`to_dict`.
        """

        fee_data = data.get("fee")
        fee = None
        if isinstance(fee_data, dict):
            fee = TradeFee(
                cost=float(fee_data.get("cost", 0.0)),
                currency=str(fee_data.get("currency", "")),
                rate=float(fee_data["rate"]) if fee_data.get("rate") is not None else None,
            )

        fees_list: list[TradeFee] = []
        fees_data = data.get("fees")
        if isinstance(fees_data, list):
            for item in fees_data:
                if isinstance(item, dict):
                    fees_list.append(
                        TradeFee(
                            cost=float(item.get("cost", 0.0)),
                            currency=str(item.get("currency", "")),
                            rate=float(item["rate"]) if item.get("rate") is not None else None,
                        )
                    )

        info = data.get("info")
        info_dict = info if isinstance(info, dict) else {}

        return cls(
            id=str(data["id"]),
            order=str(data.get("order", "")),
            timestamp=int(data["timestamp"]),
            datetime=str(data["datetime"]),
            symbol=str(data["symbol"]),
            side=str(data["side"]),
            price=float(data["price"]),
            amount=float(data["amount"]),
            cost=float(data["cost"]),
            taker_or_maker=(
                str(data["taker_or_maker"]) if data.get("taker_or_maker") is not None else None
            ),
            type=str(data["type"]) if data.get("type") is not None else None,
            fee=fee,
            fees=fees_list,
            info=info_dict,
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в словарь"""
        return {
            'id': self.id,
            'order': self.order,
            'timestamp': self.timestamp,
            'datetime': self.datetime,
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'amount': self.amount,
            'cost': self.cost,
            'taker_or_maker': self.taker_or_maker,
            'type': self.type,
            'fee': {
                'cost': self.fee.cost,
                'currency': self.fee.currency,
                'rate': self.fee.rate
            } if self.fee else None,
            'fees': [
                {
                    'cost': f.cost,
                    'currency': f.currency,
                    'rate': f.rate
                } for f in self.fees
            ],
            'info': self.info
        }

    def __repr__(self) -> str:
        role = f" ({self.taker_or_maker})" if self.taker_or_maker else ""
        return (
            f"Trade(id='{self.id}', order='{self.order}', "
            f"symbol='{self.symbol}', side='{self.side}'{role}, "
            f"price={self.price}, amount={self.amount}, cost={self.cost})"
        )
