"""
Entity: Deal (Сделка)

Сделка - это логическая пара ордеров:
- Открывающий ордер (buy) - покупка актива
- Закрывающий ордер (sell) - продажа актива

Цель сделки - получить прибыль от разницы между ценой покупки и продажи.
"""
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from src.domain.entities.order import Order


@dataclass
class Deal:
    """
    Сделка - пара связанных ордеров (buy + sell)

    Deal не является биржевой сущностью - это внутренняя логика бота
    для отслеживания полного цикла: открытие позиции -> закрытие позиции -> расчет PnL
    """
    # Идентификация
    id: int | None = None                      # DB autoincrement PK (None до сохранения в БД)
    symbol: str = ""                           # Торговая пара 'BTC/USDT'

    # Статус жизненного цикла
    status: str = ""                           # 'pending', 'open', 'closing', 'closed', 'canceled'

    # Временные метки
    created_at: int = 0                        # Unix timestamp создания (мс)
    opened_at: int | None = None               # Когда buy_order исполнился
    closed_at: int | None = None               # Когда sell_order исполнился

    # Связанные ордера
    buy_order: Order | None = None             # Открывающий ордер (покупка)
    sell_order: Order | None = None            # Закрывающий ордер (продажа)

    # Целевые параметры (планируемые при создании)
    target_amount: float = 0.0                 # Планируемый объем сделки
    target_buy_price: float | None = None      # Целевая цена покупки
    target_sell_price: float | None = None     # Целевая цена продажи
    expected_profit: float | None = None       # Ожидаемая прибыль

    # Риск-менеджмент
    max_loss_amount: float | None = None       # Максимально допустимый убыток

    # Метаданные
    strategy_name: str | None = None           # Название стратегии, создавшей сделку
    metadata: dict[str, Any] = field(default_factory=dict)  # Дополнительные данные

    # Константы статусов
    STATUS_PENDING = "pending"   # Сделка создана, buy_order еще не размещен
    STATUS_OPEN = "open"         # buy_order исполнен, позиция открыта
    STATUS_CLOSING = "closing"   # sell_order размещен, ожидает исполнения
    STATUS_CLOSED = "closed"     # sell_order исполнен, сделка завершена
    STATUS_CANCELED = "canceled" # Сделка отменена

    def __post_init__(self):
        """Синхронизация deal_id в ордерах"""
        self._sync_deal_id()

    def _sync_deal_id(self) -> None:
        """Проставить deal_id в привязанных ордерах (если id уже назначен)."""
        if self.id is not None:
            if self.buy_order:
                self.buy_order.deal_id = self.id
            if self.sell_order:
                self.sell_order.deal_id = self.id

    def assign_db_id(self, db_id: int) -> None:
        """Назначить ID, полученный от БД, и синхронизировать deal_id в ордерах."""
        self.id = db_id
        self._sync_deal_id()

    # === Проверки статуса ===

    def is_pending(self) -> bool:
        """Сделка создана, но еще не открыта"""
        return self.status == self.STATUS_PENDING

    def is_open(self) -> bool:
        """Позиция открыта, ожидает закрытия"""
        return self.status == self.STATUS_OPEN

    def is_closing(self) -> bool:
        """Идет процесс закрытия позиции"""
        return self.status == self.STATUS_CLOSING

    def is_closed(self) -> bool:
        """Сделка полностью завершена"""
        return self.status == self.STATUS_CLOSED

    def is_canceled(self) -> bool:
        """Сделка отменена"""
        return self.status == self.STATUS_CANCELED

    def is_active(self) -> bool:
        """Сделка активна (не завершена и не отменена)"""
        return self.status in [self.STATUS_PENDING, self.STATUS_OPEN, self.STATUS_CLOSING]

    # === Управление жизненным циклом ===

    def attach_buy_order(self, order: Order) -> None:
        """Привязывает открывающий ордер"""
        self.buy_order = order
        if self.id is not None:
            self.buy_order.deal_id = self.id
        if order.is_filled():
            self.mark_as_open()

    def attach_sell_order(self, order: Order) -> None:
        """Привязывает закрывающий ордер"""
        self.sell_order = order
        if self.id is not None:
            self.sell_order.deal_id = self.id
        self.status = self.STATUS_CLOSING
        if order.is_filled():
            self.mark_as_closed()

    def mark_as_open(self) -> None:
        """Помечает сделку как открытую (buy_order исполнен)"""
        self.status = self.STATUS_OPEN
        self.opened_at = int(datetime.now().timestamp() * 1000)

    def mark_as_closing(self) -> None:
        """Помечает сделку как закрывающуюся (sell_order размещен)"""
        self.status = self.STATUS_CLOSING

    def mark_as_closed(self) -> None:
        """Помечает сделку как закрытую (sell_order исполнен)"""
        self.status = self.STATUS_CLOSED
        self.closed_at = int(datetime.now().timestamp() * 1000)

    def mark_as_canceled(self) -> None:
        """Отменяет сделку"""
        self.status = self.STATUS_CANCELED
        self.closed_at = int(datetime.now().timestamp() * 1000)

    # === Расчеты ===

    def calculate_actual_profit(self) -> float | None:
        """
        Рассчитывает фактическую прибыль/убыток сделки

        Returns:
            float: Прибыль в валюте котировки (USDT)
            None: Если сделка еще не закрыта
        """
        if not self.buy_order or not self.sell_order:
            return None

        if not self.buy_order.is_filled() or not self.sell_order.is_filled():
            return None

        # Доход от продажи
        sell_income = self.sell_order.cost

        # Затраты на покупку + комиссии
        buy_cost = self.buy_order.cost
        buy_fee = self.buy_order.fee.cost if self.buy_order.fee else 0.0
        sell_fee = self.sell_order.fee.cost if self.sell_order.fee else 0.0

        # Чистая прибыль
        profit = sell_income - buy_cost - buy_fee - sell_fee

        return profit

    def calculate_profit_percentage(self) -> float | None:
        """
        Рассчитывает процент прибыли относительно вложений

        Returns:
            float: Процент прибыли (например, 2.5 = 2.5%)
            None: Если сделка еще не закрыта
        """
        profit = self.calculate_actual_profit()
        if profit is None or not self.buy_order:
            return None

        investment = self.buy_order.cost
        if investment == 0:
            return None

        return (profit / investment) * 100

    def calculate_roi(self) -> float | None:
        """
        Return on Investment (процент доходности)

        Синоним для calculate_profit_percentage()
        """
        return self.calculate_profit_percentage()

    def get_duration_ms(self) -> int | None:
        """Длительность сделки в миллисекундах"""
        if not self.opened_at or not self.closed_at:
            return None
        return self.closed_at - self.opened_at

    def get_actual_buy_price(self) -> float | None:
        """Фактическая средняя цена покупки"""
        if not self.buy_order:
            return None
        return self.buy_order.average or self.buy_order.price

    def get_actual_sell_price(self) -> float | None:
        """Фактическая средняя цена продажи"""
        if not self.sell_order:
            return None
        return self.sell_order.average or self.sell_order.price

    # === Сериализация ===

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Deal":
        """Десериализовать сделку из dict (например, из БД).

        Формат совместим с :meth:`to_dict` (без расчётных полей).
        """

        buy_data = data.get("buy_order")
        sell_data = data.get("sell_order")
        buy_order = Order.from_dict(buy_data) if isinstance(buy_data, dict) else None
        sell_order = Order.from_dict(sell_data) if isinstance(sell_data, dict) else None

        metadata = data.get("metadata")
        metadata_dict = metadata if isinstance(metadata, dict) else {}

        return cls(
            id=int(data["id"]) if data.get("id") is not None else None,
            symbol=str(data["symbol"]),
            status=str(data["status"]),
            created_at=int(data["created_at"]),
            opened_at=int(data["opened_at"]) if data.get("opened_at") is not None else None,
            closed_at=int(data["closed_at"]) if data.get("closed_at") is not None else None,
            buy_order=buy_order,
            sell_order=sell_order,
            target_amount=float(data.get("target_amount", 0.0)),
            target_buy_price=float(data["target_buy_price"]) if data.get("target_buy_price") is not None else None,
            target_sell_price=float(data["target_sell_price"]) if data.get("target_sell_price") is not None else None,
            expected_profit=float(data["expected_profit"]) if data.get("expected_profit") is not None else None,
            max_loss_amount=float(data["max_loss_amount"]) if data.get("max_loss_amount") is not None else None,
            strategy_name=str(data["strategy_name"]) if data.get("strategy_name") is not None else None,
            metadata=metadata_dict,
        )

    def to_dict(self) -> dict[str, Any]:
        """Преобразует сделку в словарь"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'status': self.status,
            'created_at': self.created_at,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at,
            'buy_order': self.buy_order.to_dict() if self.buy_order else None,
            'sell_order': self.sell_order.to_dict() if self.sell_order else None,
            'target_amount': self.target_amount,
            'target_buy_price': self.target_buy_price,
            'target_sell_price': self.target_sell_price,
            'expected_profit': self.expected_profit,
            'max_loss_amount': self.max_loss_amount,
            'strategy_name': self.strategy_name,
            'metadata': self.metadata,
            # Расчетные поля
            'actual_profit': self.calculate_actual_profit(),
            'profit_percentage': self.calculate_profit_percentage(),
            'duration_ms': self.get_duration_ms()
        }

    def __repr__(self) -> str:
        profit = self.calculate_actual_profit()
        profit_str = f", profit={profit:.2f}" if profit is not None else ""
        return (
            f"Deal(id={self.id}, symbol='{self.symbol}', status='{self.status}', "
            f"buy_order={self.buy_order.id if self.buy_order else None}, "
            f"sell_order={self.sell_order.id if self.sell_order else None}"
            f"{profit_str})"
        )
