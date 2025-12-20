-- Migration: 004_create_trades
-- Description: Создание таблицы трейдов (исполнения ордеров) согласно CCXT Trade Structure
-- Created: 2024-12-18

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS trades (
    -- Primary key (биржевой ID)
    id VARCHAR(128) PRIMARY KEY,

    -- Связь с ордером
    order VARCHAR(128) NOT NULL,

    -- Временные метки
    timestamp BIGINT NOT NULL,
    datetime VARCHAR(64) NOT NULL,

    -- Идентификация
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(8) NOT NULL,

    -- Исполнение
    price REAL NOT NULL,
    amount REAL NOT NULL,
    cost REAL NOT NULL,

    -- Роль и тип
    taker_or_maker VARCHAR(16),
    type VARCHAR(16),

    -- JSON поля
    fee_json TEXT,
    fees_json TEXT,
    info_json TEXT,

    -- Foreign key constraint
    FOREIGN KEY ("order") REFERENCES orders(id) ON DELETE CASCADE
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_trades_order
    ON trades("order");

CREATE INDEX IF NOT EXISTS idx_trades_timestamp
    ON trades(timestamp);

CREATE INDEX IF NOT EXISTS idx_trades_symbol
    ON trades(symbol);

CREATE INDEX IF NOT EXISTS idx_trades_side
    ON trades(side);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp
    ON trades(symbol, timestamp);

-- ============================================================================
-- SEED DATA (тестовые данные)
-- ============================================================================

-- Трейды для btc_buy_001 (deal #1)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'btc_trade_001', 'btc_buy_001',
    1734499260500, '2024-12-18T07:21:00.500Z',
    'BTC/USDT', 'buy',
    45000.0, 0.001, 45.0,
    'maker', 'limit',
    '{"cost": 0.045, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "12345678", "exchange": "binance"}'
);

-- Трейды для btc_sell_001 (deal #1)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'btc_trade_002', 'btc_sell_001',
    1734502800500, '2024-12-18T08:20:00.500Z',
    'BTC/USDT', 'sell',
    45675.0, 0.001, 45.675,
    'maker', 'limit',
    '{"cost": 0.046, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "12345679", "exchange": "binance"}'
);

-- Трейды для eth_buy_001 (deal #2)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'eth_trade_001', 'eth_buy_001',
    1734502860500, '2024-12-18T08:21:00.500Z',
    'ETH/USDT', 'buy',
    2500.0, 0.02, 50.0,
    'maker', 'limit',
    '{"cost": 0.05, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "23456789", "exchange": "binance"}'
);

-- Трейды для sol_buy_001 (deal #4)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'sol_trade_001', 'sol_buy_001',
    1734503460500, '2024-12-18T08:31:00.500Z',
    'SOL/USDT', 'buy',
    100.0, 1.0, 100.0,
    'maker', 'limit',
    '{"cost": 0.1, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "34567890", "exchange": "binance"}'
);

-- Трейды для btc_buy_002 (deal #6)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'btc_trade_003', 'btc_buy_002',
    1734507060500, '2024-12-18T09:31:00.500Z',
    'BTC/USDT', 'buy',
    44800.0, 0.0015, 67.2,
    'maker', 'limit',
    '{"cost": 0.067, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "45678901", "exchange": "binance"}'
);

-- Трейды для btc_sell_002 (deal #6)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'btc_trade_004', 'btc_sell_002',
    1734510600500, '2024-12-18T10:30:00.500Z',
    'BTC/USDT', 'sell',
    45344.0, 0.0015, 68.016,
    'maker', 'limit',
    '{"cost": 0.068, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "56789012", "exchange": "binance"}'
);

-- Дополнительные трейды: частичное исполнение (пример для тестирования)
-- Первое исполнение
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'eth_trade_002', 'eth_buy_001',
    1734502861000, '2024-12-18T08:21:01.000Z',
    'ETH/USDT', 'buy',
    2500.5, 0.01, 25.005,
    'taker', 'limit',
    '{"cost": 0.025, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "23456790", "exchange": "binance", "note": "partial_fill_1"}'
);

-- Второе исполнение
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'eth_trade_003', 'eth_buy_001',
    1734502862000, '2024-12-18T08:21:02.000Z',
    'ETH/USDT', 'buy',
    2499.5, 0.01, 24.995,
    'taker', 'limit',
    '{"cost": 0.025, "currency": "USDT", "rate": 0.001}',
    '[]',
    '{"trade_id": "23456791", "exchange": "binance", "note": "partial_fill_2"}'
);

-- Трейд с множественными комиссиями (пример для тестирования fees_json)
INSERT INTO trades (
    id, "order",
    timestamp, datetime,
    symbol, side,
    price, amount, cost,
    taker_or_maker, type,
    fee_json, fees_json, info_json
) VALUES (
    'btc_trade_005', 'btc_buy_001',
    1734499261000, '2024-12-18T07:21:01.000Z',
    'BTC/USDT', 'buy',
    44995.0, 0.0002, 8.999,
    'taker', 'limit',
    '{"cost": 0.009, "currency": "USDT", "rate": 0.001}',
    '[{"cost": 0.0002, "currency": "BTC", "rate": 0.001}, {"cost": 0.009, "currency": "USDT", "rate": 0.001}]',
    '{"trade_id": "12345677", "exchange": "binance", "note": "multi_currency_fees"}'
);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Проверка: должно быть 9 трейдов
SELECT COUNT(*) as total_trades FROM trades;

-- Статистика по ролям (maker/taker)
SELECT
    taker_or_maker,
    COUNT(*) as count
FROM trades
GROUP BY taker_or_maker;

-- Статистика по сторонам
SELECT
    side,
    COUNT(*) as count
FROM trades
GROUP BY side;

-- Трейды по ордерам
SELECT
    "order" as order_id,
    COUNT(*) as trades_count,
    SUM(amount) as total_amount,
    SUM(cost) as total_cost
FROM trades
GROUP BY "order"
ORDER BY "order";

-- Вывод всех тестовых трейдов
SELECT
    id,
    "order" as order_id,
    symbol,
    side,
    taker_or_maker,
    price,
    amount,
    cost
FROM trades
ORDER BY timestamp;

-- Проверка связей: трейды с их ордерами
SELECT
    t.id as trade_id,
    t."order" as order_id,
    o.symbol,
    o.side,
    o.deal_id,
    t.price,
    t.amount
FROM trades t
JOIN orders o ON t."order" = o.id
ORDER BY t.timestamp;
