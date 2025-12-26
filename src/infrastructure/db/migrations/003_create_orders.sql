-- Migration: 003_create_orders
-- Description: Создание таблицы ордеров согласно CCXT Order Structure
-- Created: 2024-12-18
-- Updated: 2024-12-25 - Refactored to use autoincrement INT id + exchange_order_id

SET search_path TO main;

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    -- Primary key (внутренний autoincrement для FK)
    id SERIAL PRIMARY KEY,

    -- ID ордера на бирже (для синхронизации после восстановления)
    exchange_order_id VARCHAR(128) UNIQUE,

    -- Идентификация
    symbol VARCHAR(32) NOT NULL,
    timestamp BIGINT NOT NULL,
    datetime VARCHAR(64) NOT NULL,

    -- Статус и тип
    status VARCHAR(16) NOT NULL,
    side VARCHAR(8) NOT NULL,
    type VARCHAR(16) NOT NULL,

    -- Объемы и цены
    amount DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION,
    average DOUBLE PRECISION,
    filled DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    remaining DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    -- Дополнительные поля
    last_trade_timestamp BIGINT,
    time_in_force VARCHAR(16),
    post_only BOOLEAN DEFAULT FALSE,
    reduce_only BOOLEAN DEFAULT FALSE,

    -- Триггерные цены
    trigger_price DOUBLE PRECISION,

    -- JSON поля
    fee_json TEXT,
    trades_json TEXT,
    info_json TEXT,

    -- Связь с Deal
    deal_id INTEGER,

    -- Foreign key constraint
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_orders_exchange_order_id
    ON orders(exchange_order_id);

CREATE INDEX IF NOT EXISTS idx_orders_symbol
    ON orders(symbol);

CREATE INDEX IF NOT EXISTS idx_orders_timestamp
    ON orders(timestamp);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_side
    ON orders(side);

CREATE INDEX IF NOT EXISTS idx_orders_type
    ON orders(type);

CREATE INDEX IF NOT EXISTS idx_orders_deal_id
    ON orders(deal_id);

CREATE INDEX IF NOT EXISTS idx_orders_symbol_status
    ON orders(symbol, status);

-- ============================================================================
-- SEED DATA (тестовые данные)
-- ============================================================================

-- Ордера для сделки #1 (BTC/USDT, closed)
-- Buy order (открывающий)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_buy_001', 'BTC/USDT', 1734499260000, '2024-12-18T07:21:00.000Z',
    'closed', 'buy', 'limit',
    0.001, 45000.0, 45000.0, 0.001, 0.0, 45.0,
    1734499260500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.045, "rate": 0.001}'::json,
    '["1", "9"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    1
);

-- Sell order (закрывающий)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_sell_001', 'BTC/USDT', 1734502800000, '2024-12-18T08:20:00.000Z',
    'closed', 'sell', 'limit',
    0.001, 45675.0, 45675.0, 0.001, 0.0, 45.675,
    1734502800500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.046, "rate": 0.001}'::json,
    '["2"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    1
);

-- Ордера для сделки #2 (ETH/USDT, open)
-- Buy order (исполнен)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'eth_buy_001', 'ETH/USDT', 1734502860000, '2024-12-18T08:21:00.000Z',
    'closed', 'buy', 'limit',
    0.02, 2500.0, 2500.0, 0.02, 0.0, 50.0,
    1734502860500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.05, "rate": 0.001}'::json,
    '["3", "7", "8"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    2
);

-- Ордера для сделки #3 (BNB/USDT, pending - buy order еще не исполнен)
-- Buy order (open, ожидает исполнения)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'bnb_buy_001', 'BNB/USDT', 1734506400000, '2024-12-18T09:20:00.000Z',
    'open', 'buy', 'limit',
    0.5, 300.0, NULL, 0.0, 0.5, 0.0,
    NULL, 'GTC', TRUE, FALSE,
    NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "order_type": "maker"}'::json,
    3
);

-- Ордера для сделки #4 (SOL/USDT, closing)
-- Buy order (закрыт)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'sol_buy_001', 'SOL/USDT', 1734503460000, '2024-12-18T08:31:00.000Z',
    'closed', 'buy', 'limit',
    1.0, 100.0, 100.0, 1.0, 0.0, 100.0,
    1734503460500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.1, "rate": 0.001}'::json,
    '["4"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    4
);

-- Sell order (open, ожидает исполнения)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'sol_sell_001', 'SOL/USDT', 1734506460000, '2024-12-18T09:21:00.000Z',
    'open', 'sell', 'limit',
    1.0, 102.0, NULL, 0.0, 1.0, 0.0,
    NULL, 'GTC', TRUE, FALSE,
    NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "order_type": "maker"}'::json,
    4
);

-- Ордера для сделки #6 (BTC/USDT, closed - вторая успешная сделка)
-- Buy order
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_buy_002', 'BTC/USDT', 1734507060000, '2024-12-18T09:31:00.000Z',
    'closed', 'buy', 'limit',
    0.0015, 44800.0, 44800.0, 0.0015, 0.0, 67.2,
    1734507060500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.067, "rate": 0.001}'::json,
    '["5"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    6
);

-- Sell order
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_sell_002', 'BTC/USDT', 1734510600000, '2024-12-18T10:30:00.000Z',
    'closed', 'sell', 'limit',
    0.0015, 45344.0, 45344.0, 0.0015, 0.0, 68.016,
    1734510600500, 'GTC', TRUE, FALSE,
    NULL,
    '{"currency": "USDT", "cost": 0.068, "rate": 0.001}'::json,
    '["6"]'::json,
    '{"exchange": "binance", "order_type": "maker"}'::json,
    6
);

-- Дополнительный ордер: отмененный ордер (для тестирования)
INSERT INTO orders (
    exchange_order_id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'xrp_buy_001', 'XRP/USDT', 1734500000000, '2024-12-18T07:33:20.000Z',
    'canceled', 'buy', 'limit',
    100.0, 0.60, NULL, 0.0, 100.0, 0.0,
    NULL, 'GTC', TRUE, FALSE,
    NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "cancel_reason": "user_request"}'::json,
    5
);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Проверка: должно быть 9 ордеров
SELECT COUNT(*) as total_orders FROM orders;

-- Статистика по статусам
SELECT
    status,
    COUNT(*) as count
FROM orders
GROUP BY status;

-- Статистика по сторонам
SELECT
    side,
    COUNT(*) as count
FROM orders
GROUP BY side;

-- Ордера по сделкам
SELECT
    deal_id,
    COUNT(*) as orders_count,
    STRING_AGG(side, ', ') as sides
FROM orders
WHERE deal_id IS NOT NULL
GROUP BY deal_id
ORDER BY deal_id;

-- Вывод всех тестовых ордеров
SELECT
    id,
    exchange_order_id,
    symbol,
    side,
    type,
    status,
    amount,
    price,
    filled,
    deal_id
FROM orders
ORDER BY timestamp;
