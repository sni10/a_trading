"""Скрипт для пересоздания БД с новыми миграциями."""

from pathlib import Path
import sys

# Добавить src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config
from src.infrastructure.db.engine_factory import build_engine
from sqlalchemy import text

def main():
    """Пересоздать все таблицы и применить миграции."""

    cfg = load_config()
    engine = build_engine(cfg)

    migrations_dir = Path(__file__).parent.parent / "src" / "infrastructure" / "db" / "migrations"

    print("🗑️  Удаление схемы и таблиц...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS main CASCADE"))

    print("✅ Схема main удалена\n")

    # Применить миграции по порядку
    migrations = [
        "001_create_currency_pairs.sql",
        "002_create_deals.sql",
        "003_create_orders.sql",
        "004_create_trades.sql",
    ]

    for migration_file in migrations:
        print(f"📥 Применение {migration_file}...")
        sql_path = migrations_dir / migration_file
        sql = sql_path.read_text(encoding='utf-8')

        with engine.begin() as conn:
            conn.execute(text(sql))

        print(f"✅ {migration_file} применена\n")

    print("=" * 80)
    print("✅ ВСЕ МИГРАЦИИ ПРИМЕНЕНЫ УСПЕШНО!")
    print("=" * 80)

    # Проверка
    print("\n📊 Проверка данных:\n")
    with engine.begin() as conn:
        conn.execute(text("SET search_path TO main"))
        for table in ["currency_pairs", "deals", "orders", "trades"]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM main.{table}"))
            count = result.scalar()
            print(f"   {table:20} : {count:3} записей")

    print("\n✅ Готово! Запускай тесты: python -m pytest tests/test_persistence_recovery.py -v\n")

if __name__ == "__main__":
    main()
