-- Migration: 002_create_deals
-- Description: Создание таблицы сделок (пара ордеров: покупка + продажа)
-- Created: 2024-12-18

SET search_path TO main;

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS deals (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Идентификация
    symbol VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',

    -- Временные метки (миллисекунды)
    created_at BIGINT NOT NULL,
    opened_at BIGINT,
    closed_at BIGINT,

    -- Связанные ордера (хранятся как JSON)
    buy_order_json TEXT,
    sell_order_json TEXT,

    -- Целевые параметры
    target_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    target_buy_price DOUBLE PRECISION,
    target_sell_price DOUBLE PRECISION,
    expected_profit DOUBLE PRECISION,

    -- Риск-менеджмент
    stop_loss_price DOUBLE PRECISION,
    take_profit_price DOUBLE PRECISION,
    max_loss_amount DOUBLE PRECISION,

    -- Метаданные
    strategy_name VARCHAR(64),
    metadata_json TEXT
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_deals_symbol
    ON deals(symbol);

CREATE INDEX IF NOT EXISTS idx_deals_status
    ON deals(status);

CREATE INDEX IF NOT EXISTS idx_deals_created_at
    ON deals(created_at);

CREATE INDEX IF NOT EXISTS idx_deals_symbol_status
    ON deals(symbol, status);

-- ============================================================================
-- SEED DATA (тестовые данные)
-- ============================================================================

-- Сделка 1: Закрытая успешная сделка по BTC/USDT
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'BTC/USDT', 'closed',
    1734499200000, 1734499260000, 1734502800000,
    NULL, NULL,  -- Ордера будут добавлены в следующей миграции
    0.001, 45000.0, 45675.0, 0.675,
    44550.0, 45900.0, 45.0,
    'ScalpingStrategy', '{"note": "First successful deal", "confidence": 0.85}'
);

-- Сделка 2: Открытая сделка по ETH/USDT (ждет закрытия)
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'ETH/USDT', 'open',
    1734502800000, 1734502860000, NULL,
    NULL, NULL,
    0.02, 2500.0, 2530.0, 0.60,
    2475.0, 2550.0, 25.0,
    'TrendFollowingStrategy', '{"entry_signal": "bullish_crossover", "strength": 0.72}'
);

-- Сделка 3: Pending сделка по BNB/USDT (buy_order еще не исполнен)
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'BNB/USDT', 'pending',
    1734506400000, NULL, NULL,
    NULL, NULL,
    0.5, 300.0, 303.0, 1.50,
    297.0, 306.0, 15.0,
    'ScalpingStrategy', '{"waiting_for": "price_dip"}'
);

-- Сделка 4: Closing сделка по SOL/USDT (sell_order размещен)
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'SOL/USDT', 'closing',
    1734503400000, 1734503460000, NULL,
    NULL, NULL,
    1.0, 100.0, 102.0, 2.00,
    98.0, 104.0, 20.0,
    'MomentumStrategy', '{"exit_trigger": "take_profit_target"}'
);

-- Сделка 5: Отмененная сделка по XRP/USDT
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'XRP/USDT', 'canceled',
    1734500000000, NULL, 1734500600000,
    NULL, NULL,
    100.0, 0.60, 0.605, 0.50,
    0.594, 0.612, 6.0,
    'GridStrategy', '{"cancel_reason": "market_conditions_changed"}'
);

-- Сделка 6: Еще одна закрытая успешная сделка по BTC/USDT
INSERT INTO deals (
    symbol, status,
    created_at, opened_at, closed_at,
    buy_order_json, sell_order_json,
    target_amount, target_buy_price, target_sell_price, expected_profit,
    stop_loss_price, take_profit_price, max_loss_amount,
    strategy_name, metadata_json
) VALUES (
    'BTC/USDT', 'closed',
    1734507000000, 1734507060000, 1734510600000,
    NULL, NULL,
    0.0015, 44800.0, 45344.0, 0.816,
    44352.0, 45792.0, 67.2,
    'ScalpingStrategy', '{"note": "Quick scalp on volatility spike", "confidence": 0.91}'
);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Проверка: должно быть 6 сделок
SELECT COUNT(*) as total_deals FROM deals;

-- Статистика по статусам
SELECT
    status,
    COUNT(*) as count
FROM deals
GROUP BY status
ORDER BY count DESC;

-- Вывод всех тестовых сделок
SELECT
    id,
    symbol,
    status,
    target_amount,
    target_buy_price,
    target_sell_price,
    expected_profit,
    strategy_name
FROM deals
ORDER BY id;
