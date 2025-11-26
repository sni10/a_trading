"""Infrastructure-level реализации репозиториев.

На этом этапе есть только in-memory реализация репозитория валютных пар,
но структура модуля сразу закладывается под будущие реализации поверх БД.
"""

from .currency_pair_in_memory import InMemoryCurrencyPairRepository

__all__ = ["InMemoryCurrencyPairRepository"]
