-- Migration: 003_create_orders
-- Description: Создание таблицы ордеров согласно CCXT Order Structure
-- Created: 2024-12-18

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    -- Primary key (биржевой ID)
    id VARCHAR(128) PRIMARY KEY,

    -- Идентификация
    symbol VARCHAR(32) NOT NULL,
    timestamp BIGINT NOT NULL,
    datetime VARCHAR(64) NOT NULL,

    -- Статус и тип
    status VARCHAR(16) NOT NULL,
    side VARCHAR(8) NOT NULL,
    type VARCHAR(16) NOT NULL,

    -- Объемы и цены
    amount REAL NOT NULL,
    price REAL,
    average REAL,
    filled REAL NOT NULL DEFAULT 0.0,
    remaining REAL NOT NULL DEFAULT 0.0,
    cost REAL NOT NULL DEFAULT 0.0,

    -- Дополнительные поля
    client_order_id VARCHAR(128),
    last_trade_timestamp BIGINT,
    time_in_force VARCHAR(16),
    post_only BOOLEAN DEFAULT 0,
    reduce_only BOOLEAN DEFAULT 0,

    -- Триггерные цены
    trigger_price REAL,
    stop_loss_price REAL,
    take_profit_price REAL,

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

CREATE INDEX IF NOT EXISTS idx_orders_client_order_id
    ON orders(client_order_id);

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
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_buy_001', 'BTC/USDT', 1734499260000, '2024-12-18T07:21:00.000Z',
    'closed', 'buy', 'limit',
    0.001, 45000.0, 45000.0, 0.001, 0.0, 45.0,
    'client_btc_buy_001', 1734499260500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.045, "rate": 0.001}',
    '["btc_trade_001"]',
    '{"exchange": "binance", "order_type": "maker"}',
    1
);

-- Sell order (закрывающий)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_sell_001', 'BTC/USDT', 1734502800000, '2024-12-18T08:20:00.000Z',
    'closed', 'sell', 'limit',
    0.001, 45675.0, 45675.0, 0.001, 0.0, 45.675,
    'client_btc_sell_001', 1734502800500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.046, "rate": 0.001}',
    '["btc_trade_002"]',
    '{"exchange": "binance", "order_type": "maker"}',
    1
);

-- Ордера для сделки #2 (ETH/USDT, open)
-- Buy order (исполнен)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'eth_buy_001', 'ETH/USDT', 1734502860000, '2024-12-18T08:21:00.000Z',
    'closed', 'buy', 'limit',
    0.02, 2500.0, 2500.0, 0.02, 0.0, 50.0,
    'client_eth_buy_001', 1734502860500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.05, "rate": 0.001}',
    '["eth_trade_001"]',
    '{"exchange": "binance", "order_type": "maker"}',
    2
);

-- Ордера для сделки #3 (BNB/USDT, pending - buy order еще не исполнен)
-- Buy order (open, ожидает исполнения)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'bnb_buy_001', 'BNB/USDT', 1734506400000, '2024-12-18T09:20:00.000Z',
    'open', 'buy', 'limit',
    0.5, 300.0, NULL, 0.0, 0.5, 0.0,
    'client_bnb_buy_001', NULL, 'GTC', 1, 0,
    NULL, NULL, NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "order_type": "maker"}',
    3
);

-- Ордера для сделки #4 (SOL/USDT, closing)
-- Buy order (закрыт)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'sol_buy_001', 'SOL/USDT', 1734503460000, '2024-12-18T08:31:00.000Z',
    'closed', 'buy', 'limit',
    1.0, 100.0, 100.0, 1.0, 0.0, 100.0,
    'client_sol_buy_001', 1734503460500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.1, "rate": 0.001}',
    '["sol_trade_001"]',
    '{"exchange": "binance", "order_type": "maker"}',
    4
);

-- Sell order (open, ожидает исполнения)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'sol_sell_001', 'SOL/USDT', 1734506460000, '2024-12-18T09:21:00.000Z',
    'open', 'sell', 'limit',
    1.0, 102.0, NULL, 0.0, 1.0, 0.0,
    'client_sol_sell_001', NULL, 'GTC', 1, 0,
    NULL, NULL, NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "order_type": "maker"}',
    4
);

-- Ордера для сделки #6 (BTC/USDT, closed - вторая успешная сделка)
-- Buy order
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_buy_002', 'BTC/USDT', 1734507060000, '2024-12-18T09:31:00.000Z',
    'closed', 'buy', 'limit',
    0.0015, 44800.0, 44800.0, 0.0015, 0.0, 67.2,
    'client_btc_buy_002', 1734507060500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.067, "rate": 0.001}',
    '["btc_trade_003"]',
    '{"exchange": "binance", "order_type": "maker"}',
    6
);

-- Sell order
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'btc_sell_002', 'BTC/USDT', 1734510600000, '2024-12-18T10:30:00.000Z',
    'closed', 'sell', 'limit',
    0.0015, 45344.0, 45344.0, 0.0015, 0.0, 68.016,
    'client_btc_sell_002', 1734510600500, 'GTC', 1, 0,
    NULL, NULL, NULL,
    '{"currency": "USDT", "cost": 0.068, "rate": 0.001}',
    '["btc_trade_004"]',
    '{"exchange": "binance", "order_type": "maker"}',
    6
);

-- Дополнительный ордер: отмененный ордер (для тестирования)
INSERT INTO orders (
    id, symbol, timestamp, datetime,
    status, side, type,
    amount, price, average, filled, remaining, cost,
    client_order_id, last_trade_timestamp, time_in_force, post_only, reduce_only,
    trigger_price, stop_loss_price, take_profit_price,
    fee_json, trades_json, info_json,
    deal_id
) VALUES (
    'xrp_buy_001', 'XRP/USDT', 1734500000000, '2024-12-18T07:33:20.000Z',
    'canceled', 'buy', 'limit',
    100.0, 0.60, NULL, 0.0, 100.0, 0.0,
    'client_xrp_buy_001', NULL, 'GTC', 1, 0,
    NULL, NULL, NULL,
    NULL,
    '[]',
    '{"exchange": "binance", "cancel_reason": "user_request"}',
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
    GROUP_CONCAT(side) as sides
FROM orders
WHERE deal_id IS NOT NULL
GROUP BY deal_id
ORDER BY deal_id;

-- Вывод всех тестовых ордеров
SELECT
    id,
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
