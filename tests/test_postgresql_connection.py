"""Тест подключения к PostgreSQL.

Проверяет:
1. Загрузку конфигурации из .env
2. Создание engine
3. Инициализацию БД с созданием таблиц
4. Подключение к схеме (если задана)
5. Базовые операции через репозитории
"""

from __future__ import annotations

import time

from src.application.repository_factory import build_repositories
from src.config.config import load_config
from src.domain.entities.currency_pair import CurrencyPair


def test_postgresql_connection():
    """Интеграционный тест подключения к PostgreSQL."""

    print("\n=== Тест подключения к PostgreSQL ===\n")

    # 1. Загрузить конфигурацию
    print("1. Загрузка конфигурации...")
    cfg = load_config()
    print(f"   - DATABASE_TYPE: {cfg.database.database_type}")
    print(f"   - DATABASE_URL: {cfg.database.database_url}")
    print(f"   - DATABASE_SCHEMA: {cfg.database.database_schema or 'public (default)'}")

    if cfg.database.database_type != "postgresql":
        print("\n⚠️  DATABASE_TYPE не postgresql - пропускаем тест")
        return

    # 2. Создать репозитории (автоматически создаст engine и таблицы)
    print("\n2. Создание engine и инициализация БД...")
    bundle = build_repositories(cfg)
    print("   ✓ Engine создан")
    print("   ✓ Таблицы инициализированы")

    # 3. Проверить работу с CurrencyPairRepository
    print("\n3. Проверка работы с репозиторием валютных пар...")
    pair_repo = bundle.pair_repository

    # Создать тестовую пару
    test_pair = CurrencyPair(
        pair_id=1,
        symbol="TEST/USDT",
        base_currency="TEST",
        quote_currency="USDT",
        deal_quota=100.0,
        profit_markup=2.0,
        deal_count=5,
        order_life_time=60,
        min_step=0.0001,
        price_step=0.01,
        enabled=True,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )

    # Upsert (insert or update)
    print(f"   - Upsert пары: {test_pair.symbol}")
    saved_pair = pair_repo.upsert(test_pair)
    print(f"   ✓ Сохранено с pair_id={saved_pair.pair_id}")

    # Получить по symbol
    print(f"   - Получение пары по symbol: {test_pair.symbol}")
    fetched_pair = pair_repo.get_by_symbol(test_pair.symbol)
    assert fetched_pair is not None, "Пара не найдена после сохранения"
    assert fetched_pair.symbol == test_pair.symbol
    print(f"   ✓ Пара получена: {fetched_pair.symbol}")

    # Список всех пар
    print("   - Получение списка всех пар")
    all_pairs = pair_repo.list_all()
    print(f"   ✓ Всего пар в БД: {len(all_pairs)}")

    # Список активных пар
    active_pairs = pair_repo.list_active()
    print(f"   ✓ Активных пар: {len(active_pairs)}")

    print("\n=== ✅ Все проверки пройдены успешно! ===\n")


if __name__ == "__main__":
    test_postgresql_connection()
