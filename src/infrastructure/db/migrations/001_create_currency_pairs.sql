-- Migration: 001_create_currency_pairs
-- Description: Создание таблицы валютных пар с торговыми настройками
-- Created: 2024-12-18

-- Создать схему main
CREATE SCHEMA IF NOT EXISTS main;
SET search_path TO main;

-- ============================================================================
-- CREATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS currency_pairs (
    -- Primary key
    pair_id SERIAL PRIMARY KEY,

    -- Идентификация пары
    symbol VARCHAR(32) NOT NULL UNIQUE,
    base_currency VARCHAR(16) NOT NULL,
    quote_currency VARCHAR(16) NOT NULL,

    -- Статус
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Trading settings (специфичны для каждой пары)
    deal_quota DOUBLE PRECISION NOT NULL DEFAULT 25.0,
    profit_markup DOUBLE PRECISION NOT NULL DEFAULT 1.5,
    deal_count INTEGER NOT NULL DEFAULT 3,
    order_life_time INTEGER NOT NULL DEFAULT 1,

    -- Exchange technical params
    min_step DOUBLE PRECISION NOT NULL DEFAULT 0.00001,
    price_step DOUBLE PRECISION NOT NULL DEFAULT 0.01,

    -- Timestamps (миллисекунды)
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_currency_pairs_symbol
    ON currency_pairs(symbol);

CREATE INDEX IF NOT EXISTS idx_currency_pairs_enabled
    ON currency_pairs(enabled);

-- ============================================================================
-- SEED DATA (тестовые данные)
-- ============================================================================

-- Основные торговые пары для тестирования
INSERT INTO currency_pairs (
    symbol, base_currency, quote_currency,
    enabled,
    deal_quota, profit_markup, deal_count, order_life_time,
    min_step, price_step,
    created_at, updated_at
) VALUES
    -- BTC/USDT - основная пара для тестирования
    (
        'BTC/USDT', 'BTC', 'USDT',
        TRUE,
        100.0, 1.5, 5, 1,
        0.00001, 0.01,
        1734499200000, 1734499200000
    ),

    -- ETH/USDT - вторая по популярности
    (
        'ETH/USDT', 'ETH', 'USDT',
        TRUE,
        50.0, 1.2, 3, 1,
        0.0001, 0.01,
        1734499200000, 1734499200000
    ),

    -- BNB/USDT - для диверсификации
    (
        'BNB/USDT', 'BNB', 'USDT',
        TRUE,
        30.0, 1.0, 2, 1,
        0.0001, 0.01,
        1734499200000, 1734499200000
    ),

    -- SOL/USDT - волатильная пара для агрессивной торговли
    (
        'SOL/USDT', 'SOL', 'USDT',
        TRUE,
        25.0, 2.0, 4, 1,
        0.001, 0.01,
        1734499200000, 1734499200000
    ),

    -- XRP/USDT - низковолатильная пара
    (
        'XRP/USDT', 'XRP', 'USDT',
        TRUE,
        20.0, 0.8, 3, 2,
        0.01, 0.0001,
        1734499200000, 1734499200000
    ),

    -- DOGE/USDT - отключенная пара (для тестирования фильтрации)
    (
        'DOGE/USDT', 'DOGE', 'USDT',
        FALSE,
        15.0, 1.0, 2, 1,
        1.0, 0.000001,
        1734499200000, 1734499200000
    );

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Проверка: должно быть 6 записей
SELECT COUNT(*) as total_pairs FROM currency_pairs;

-- Проверка: должно быть 5 активных пар
SELECT COUNT(*) as active_pairs FROM currency_pairs WHERE enabled = TRUE;

-- Вывод всех тестовых пар
SELECT
    pair_id,
    symbol,
    enabled,
    deal_quota,
    profit_markup,
    deal_count
FROM currency_pairs
ORDER BY pair_id;
