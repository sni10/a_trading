# Database Migrations

Миграции базы данных для системы алготрейдинга с тестовыми данными.

## 📁 Структура миграций

```
migrations/
├── 001_create_currency_pairs.sql  # Валютные пары
├── 002_create_deals.sql           # Сделки (Deal)
├── 003_create_orders.sql          # Ордера (Order)
├── 004_create_trades.sql          # Трейды (Trade)
└── README.md                      # Эта инструкция
```

## 🔄 Порядок применения

**ВАЖНО:** Миграции должны применяться строго по порядку из-за зависимостей между таблицами:

1. **currency_pairs** - независимая таблица
2. **deals** - независимая таблица
3. **orders** - зависит от `deals` (FK: deal_id)
4. **trades** - зависит от `orders` (FK: order)

## 🚀 Применение миграций

### Вариант 1: SQLite CLI

```bash
# Создать пустую БД и применить все миграции
cd src/infrastructure/db/migrations

# Применение по порядку
sqlite3 ../../../../storage/trading.db < 001_create_currency_pairs.sql
sqlite3 ../../../../storage/trading.db < 002_create_deals.sql
sqlite3 ../../../../storage/trading.db < 003_create_orders.sql
sqlite3 ../../../../storage/trading.db < 004_create_trades.sql
```

### Вариант 2: Пакетное применение

```bash
# Из корня проекта
cd src/infrastructure/db/migrations
cat *.sql | sqlite3 ../../../../storage/trading.db
```

### Вариант 3: Python script

```python
import sqlite3
from pathlib import Path

db_path = "storage/trading.db"
migrations_dir = Path("src/infrastructure/db/migrations")

# Порядок миграций
migrations = [
    "001_create_currency_pairs.sql",
    "002_create_deals.sql",
    "003_create_orders.sql",
    "004_create_trades.sql",
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for migration_file in migrations:
    print(f"Applying {migration_file}...")
    sql = (migrations_dir / migration_file).read_text(encoding='utf-8')
    cursor.executescript(sql)
    print(f"✓ {migration_file} applied successfully")

conn.commit()
conn.close()
print("\n✓ All migrations applied successfully!")
```

## 📊 Тестовые данные

Каждая миграция содержит seed data (тестовые данные) для быстрого старта.

### Currency Pairs (6 пар)

| Symbol     | Enabled | Deal Quota | Profit Markup | Deal Count |
|------------|---------|------------|---------------|------------|
| BTC/USDT   | ✓       | 100.0      | 1.5%          | 5          |
| ETH/USDT   | ✓       | 50.0       | 1.2%          | 3          |
| BNB/USDT   | ✓       | 30.0       | 1.0%          | 2          |
| SOL/USDT   | ✓       | 25.0       | 2.0%          | 4          |
| XRP/USDT   | ✓       | 20.0       | 0.8%          | 3          |
| DOGE/USDT  | ✗       | 15.0       | 1.0%          | 2          |

### Deals (6 сделок)

| ID | Symbol    | Status   | Description                          |
|----|-----------|----------|--------------------------------------|
| 1  | BTC/USDT  | closed   | Успешная закрытая сделка             |
| 2  | ETH/USDT  | open     | Открытая сделка (ждет закрытия)      |
| 3  | BNB/USDT  | pending  | Новая сделка (buy_order не исполнен) |
| 4  | SOL/USDT  | closing  | Закрывается (sell_order размещен)    |
| 5  | XRP/USDT  | canceled | Отмененная сделка                    |
| 6  | BTC/USDT  | closed   | Вторая успешная сделка               |

### Orders (9 ордеров)

| ID            | Symbol    | Side | Type  | Status   | Deal ID |
|---------------|-----------|------|-------|----------|---------|
| btc_buy_001   | BTC/USDT  | buy  | limit | closed   | 1       |
| btc_sell_001  | BTC/USDT  | sell | limit | closed   | 1       |
| eth_buy_001   | ETH/USDT  | buy  | limit | closed   | 2       |
| bnb_buy_001   | BNB/USDT  | buy  | limit | open     | 3       |
| sol_buy_001   | SOL/USDT  | buy  | limit | closed   | 4       |
| sol_sell_001  | SOL/USDT  | sell | limit | open     | 4       |
| btc_buy_002   | BTC/USDT  | buy  | limit | closed   | 6       |
| btc_sell_002  | BTC/USDT  | sell | limit | closed   | 6       |
| xrp_buy_001   | XRP/USDT  | buy  | limit | canceled | 5       |

### Trades (9 трейдов)

Трейды показывают:
- Полное исполнение ордеров (1 ордер = 1 трейд)
- Частичное исполнение (eth_buy_001 = 3 трейда)
- Роли maker/taker
- Множественные комиссии

## 🔍 Проверка данных

После применения миграций можно проверить данные:

```bash
sqlite3 storage/trading.db
```

```sql
-- Проверка всех таблиц
SELECT 'currency_pairs' as table_name, COUNT(*) as count FROM currency_pairs
UNION ALL
SELECT 'deals', COUNT(*) FROM deals
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'trades', COUNT(*) FROM trades;

-- Проверка связей Deal → Orders → Trades
SELECT
    d.id as deal_id,
    d.symbol,
    d.status as deal_status,
    o.id as order_id,
    o.side,
    o.status as order_status,
    COUNT(t.id) as trades_count
FROM deals d
LEFT JOIN orders o ON o.deal_id = d.id
LEFT JOIN trades t ON t."order" = o.id
GROUP BY d.id, o.id
ORDER BY d.id, o.id;

-- Анализ прибыльности закрытых сделок
SELECT
    d.id,
    d.symbol,
    d.target_buy_price,
    d.target_sell_price,
    d.expected_profit,
    d.strategy_name
FROM deals d
WHERE d.status = 'closed'
ORDER BY d.expected_profit DESC;
```

## 🗑️ Откат миграций

Для очистки БД и повторного применения:

```bash
# Удалить БД
rm storage/trading.db

# Применить миграции заново (см. "Применение миграций")
```

Или удалить таблицы по порядку:

```sql
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS deals;
DROP TABLE IF EXISTS currency_pairs;
```

## 📝 Структура таблиц

### currency_pairs
- **PK**: pair_id (autoincrement)
- **Unique**: symbol
- **Indexes**: symbol, enabled
- **Назначение**: Торговые пары с настройками (deal_quota, profit_markup и т.д.)

### deals
- **PK**: id (autoincrement)
- **Indexes**: symbol, status, created_at, (symbol, status)
- **Назначение**: Логические сделки (buy + sell)
- **JSON поля**: buy_order_json, sell_order_json, metadata_json

### orders
- **PK**: id (autoincrement INT)
- **Unique**: exchange_order_id (биржевой ID для синхронизации)
- **FK**: deal_id → deals.id
- **Indexes**: exchange_order_id, symbol, timestamp, status, side, type, deal_id
- **Назначение**: Ордера на бирже (CCXT Order Structure)
- **JSON поля**: fee_json, trades_json, info_json

### trades
- **PK**: id (autoincrement INT)
- **Unique**: exchange_trade_id (биржевой ID для синхронизации)
- **FK**: order_id → orders.id (CASCADE)
- **Indexes**: exchange_trade_id, order_id, timestamp, symbol, side, (symbol, timestamp)
- **Назначение**: Исполнения ордеров (CCXT Trade Structure)
- **JSON поля**: fee_json, fees_json, info_json

## 🔗 Foreign Keys

```
trades.order → orders.id (ON DELETE CASCADE)
orders.deal_id → deals.id (ON DELETE SET NULL)
```

## 💡 Примеры использования

### Найти все активные сделки

```sql
SELECT * FROM deals
WHERE status IN ('pending', 'open', 'closing');
```

### Найти ордера без трейдов (не исполнены)

```sql
SELECT o.id, o.symbol, o.side, o.status
FROM orders o
LEFT JOIN trades t ON t."order" = o.id
WHERE t.id IS NULL;
```

### Рассчитать общую комиссию по сделке

```sql
SELECT
    d.id as deal_id,
    d.symbol,
    SUM(
        CAST(json_extract(t.fee_json, '$.cost') AS REAL)
    ) as total_fees
FROM deals d
JOIN orders o ON o.deal_id = d.id
JOIN trades t ON t."order" = o.id
WHERE d.status = 'closed'
GROUP BY d.id;
```

## 🎯 Следующие шаги

1. Применить миграции
2. Проверить данные
3. Запустить интеграционные тесты с тестовыми данными
4. При необходимости добавить свои тестовые данные
5. Использовать репозитории для работы с entities

## ⚠️ Важные замечания

- Миграции содержат проверочные запросы в конце - они выводят статистику
- JSON поля хранятся как TEXT в SQLite
- Timestamps в миллисекундах (BIGINT)
- Boolean поля: 0 = False, 1 = True
- Foreign keys должны быть включены в SQLite: `PRAGMA foreign_keys = ON;`

## 📚 Связанные файлы

- **Entities**: `src/domain/entities/`
- **Models**: `src/infrastructure/db/models/`
- **Repositories**: `src/infrastructure/repositories/`
