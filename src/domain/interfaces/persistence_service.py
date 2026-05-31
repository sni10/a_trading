"""Интерфейс сервиса персистентности для сохранения/восстановления состояния."""

from __future__ import annotations

from typing import Protocol


class IPersistenceService(Protocol):
    """Сервис для сохранения и восстановления состояния контекста в БД.

    Отвечает за:
    - Периодическое сохранение активных сделок, ордеров в БД
    - Восстановление состояния из БД при перезапуске процесса
    - Синхронизацию состояния БД с in-memory контекстом
    """

    def save_snapshot(self, symbol: str) -> None:
        """Сохранить текущий snapshot состояния в БД.

        Сохраняет из ApplicationContext:
        - Активные сделки (deals)
        - Открытые ордера (orders)
        - Недавние трейды

        Args:
            symbol: Символ валютной пары для сохранения
        """
        ...

    def restore_snapshot(self, symbol: str) -> dict:
        """Восстановить состояние из БД в контекст.

        Загружает из БД:
        - Активные сделки по паре
        - Открытые ордера
        - Связанные трейды

        Args:
            symbol: Символ валютной пары для восстановления

        Returns:
            dict с ключами:
                - 'deals': List[Deal] - активные сделки
                - 'orders': List[Order] - открытые ордера
                - 'trades': List[Trade] - трейды по ордерам
        """
        ...


__all__ = ["IPersistenceService"]
