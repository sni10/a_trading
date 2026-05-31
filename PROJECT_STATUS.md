# Статус готовности проекта "Algorithmic Trading System"

**Дата обновления:** 2025-12-25
**Версия:** 0.2.0 (Pre-Alpha)
**Статус:** Активная разработка, фаза интеграции БД и персистентности

---

## 📊 Общий прогресс

| Модуль | Готовность | Статус |
|--------|------------|--------|
| **Domain Entities** | 100% | ✅ Готово |
| **Database Layer** | 90% | 🟡 Частично |
| **Repositories** | 100% | ✅ Готово |
| **Infrastructure** | 80% | 🟡 Частично |
| **Services** | 70% | 🟡 В разработке |
| **Workers** | 50% | 🟡 В разработке |
| **Configuration** | 95% | ✅ Готово |
| **Exchange Integration** | 40% | 🔴 Заглушки |
| **Strategy System** | 40% | 🟡 Базовая логика |
| **Testing** | 35% | 🔴 Минимально |

---

## 🔒 Критично перед реальным биржевым исполнением

1. Реализовать боевой ExecutionService: `create_order/cancel_order/fetch_order`, идемпотентность, retry.
2. Довести OrderSyncService: синхронизация ордеров/трейдов с биржей, восстановление после рестарта.
3. Завершить risk-контуры: лимиты, баланс, min notional, kill-switch, стоп-условия.
4. Гарантировать рыночные данные: актуальный стакан/тикер, warmup индикаторов.
5. Устойчивость: таймауты, rate-limit, алерты, логирование без секретов.
6. Развести ключи и режимы: sandbox/production, проверка окружения перед стартом.

---

## ✅ Готовые компоненты (Production-Ready)

### 1. Domain Entities (100% готово)

#### ✅ CurrencyPair
- **Файл:** `src/domain/entities/currency_pair.py`
- **Статус:** Полностью готов
- **Функционал:**
  - Валидация формата символа (BASE/QUOTE)
  - Торговые настройки (deal_quota, profit_markup, deal_count, order_life_time)
  - Биржевые параметры (min_step, price_step)
  - Сериализация/десериализация (to_dict/from_dict)
  - Timestamps (created_at, updated_at)
- **Используется:** Да, в ApplicationContext и репозиториях

#### ✅ Deal (Сделка)
- **Файл:** `src/domain/entities/deal.py`
- **Статус:** Полностью готов
- **Функционал:**
  - Жизненный цикл: pending → open → closing → closed / canceled
  - Связь с двумя ордерами (buy_order, sell_order)
  - Целевые параметры (target_amount, target_buy_price, target_sell_price)
  - Риск-менеджмент (stop_loss_price, take_profit_price, max_loss_amount)
  - Расчёт прибыли (calculate_actual_profit, calculate_profit_percentage, calculate_roi)
  - Метаданные (strategy_name, metadata dict)
  - Сериализация/десериализация
- **Используется:** В репозиториях, планируется интеграция в стратегии

#### ✅ Order (Ордер)
- **Файл:** `src/domain/entities/order.py`
- **Статус:** Полностью готов
- **Функционал:**
  - Полная совместимость с CCXT Order Structure
  - Статусы: open, closed, canceled, expired, rejected
  - Объёмы и цены (amount, price, average, filled, remaining, cost)
  - Триггерные цены (trigger_price, stop_loss_price, take_profit_price)
  - Комиссии (OrderFee)
  - Список трейдов (trades: list[str])
  - Методы проверки (is_open, is_closed, is_filled, is_partially_filled)
  - Конструктор из CCXT (from_ccxt)
  - Связь с Deal (deal_id)
- **Используется:** В репозиториях, планируется в ExecutionService

#### ✅ Trade (Исполнение)
- **Файл:** `src/domain/entities/trade.py`
- **Статус:** Полностью готов
- **Функционал:**
  - Полная совместимость с CCXT Trade Structure
  - Связь с ордером (order: str)
  - Роль (taker_or_maker: maker/taker)
  - Множественные комиссии (fee + fees: list[TradeFee])
  - Методы проверки (is_maker, is_taker, is_buy, is_sell)
  - Расчёт полной стоимости с комиссиями
  - Конструктор из CCXT (from_ccxt)
- **Используется:** В репозиториях

---

### 2. Database Layer (90% готово)

#### ✅ Миграции (SQL)
- **Путь:** `src/infrastructure/db/migrations/`
- **Статус:** Готовы все таблицы
- **Файлы:**
  - `001_create_currency_pairs.sql` - Валютные пары + seed данные (6 пар)
  - `002_create_deals.sql` - Сделки + seed данные (6 сделок разных статусов)
  - `003_create_orders.sql` - Ордера + seed данные (9 ордеров)
  - `004_create_trades.sql` - Трейды + seed данные (9 трейдов)
- **Seed данные:** Готовые тестовые сценарии (закрытые, открытые, отменённые сделки)
- **Используется:** Да, миграции применены к БД

#### ✅ SQLAlchemy Models
- **Путь:** `src/infrastructure/db/models/`
- **Статус:** Готовы все модели
- **Файлы:**
  - `currency_pair_model.py` - ORM-модель валютной пары
  - `deal_model.py` - ORM-модель сделки (с JSON полями для ордеров)
  - `order_model.py` - ORM-модель ордера
  - `trade_model.py` - ORM-модель трейда
- **Особенности:**
  - Универсальность: SQLite + PostgreSQL (через DATABASE_TYPE)
  - JSON поля для сложных структур
  - Индексы по ключевым полям (symbol, status, timestamp)
  - Foreign keys (deal_id в orders, order в trades)

#### ✅ Session Factory
- **Файл:** `src/infrastructure/db/session_factory.py`
- **Статус:** Готов
- **Функционал:**
  - Context manager для сессий (session_scope)
  - Автоматический commit/rollback
  - Поддержка транзакций

#### 🟡 Database Initialization
- **Файл:** `src/infrastructure/db/__init__.py`
- **Статус:** Готов, но требует тестирования
- **Функционал:**
  - `build_engine()` - создание engine (SQLite/PostgreSQL)
  - `init_db()` - создание всех таблиц через metadata
- **TODO:** Интеграция с Alembic для автоматических миграций

---

### 3. Repositories (100% готово)

Все репозитории реализованы через SQLAlchemy и следуют DIP (Dependency Inversion Principle).

#### ✅ SqlAlchemyCurrencyPairRepository
- **Файл:** `src/infrastructure/repositories/currency_pair_sqlalchemy.py`
- **Интерфейс:** `ICurrencyPairRepository`
- **Методы:**
  - `list_all(include_disabled=True)` - все пары
  - `list_active()` - только enabled пары
  - `get_by_symbol(symbol)` - поиск по символу
  - `upsert(pair)` - создание/обновление
- **Статус:** Готов, протестирован

#### ✅ SqlAlchemyDealRepository
- **Файл:** `src/infrastructure/repositories/deal_sqlalchemy.py`
- **Интерфейс:** `IDealRepository`
- **Методы:**
  - `add(deal)` - создать новую сделку
  - `update(deal)` - обновить существующую (upsert-стиль)
  - `get_by_id(deal_id)` - получить по ID
  - `list_active_by_symbol(symbol)` - активные сделки (pending/open/closing)
- **Статус:** Готов, протестирован

#### ✅ SqlAlchemyOrderRepository
- **Файл:** `src/infrastructure/repositories/order_sqlalchemy.py`
- **Интерфейс:** `IOrderRepository`
- **Методы:**
  - `upsert(order)` - создать/обновить ордер (через merge)
  - `get_by_id(order_id)` - получить по ID
  - `list_by_symbol(symbol, limit=100)` - ордера по паре
- **Статус:** Готов, протестирован

#### ✅ SqlAlchemyTradeRepository
- **Файл:** `src/infrastructure/repositories/trade_sqlalchemy.py`
- **Интерфейс:** `ITradeRepository`
- **Методы:**
  - `upsert(trade)` - создать/обновить трейд
  - `get_by_id(trade_id)` - получить по ID
  - `list_by_order_id(order_id, limit=500)` - трейды по ордеру
- **Статус:** Готов, протестирован

---

### 4. Configuration System (95% готово)

#### ✅ AppConfig
- **Файл:** `src/config/config.py`
- **Статус:** Полностью готов
- **Разделы:**
  - `environment` - dev/staging/production
  - `cache` - параметры кэширования (bar_window_size, indicator_layers)
  - `database` - DATABASE_TYPE (sqlite/postgresql), DATABASE_PATH, DATABASE_URL
  - `exchange` - параметры биржи (в разработке)
  - `state_snapshot_interval_ticks` - интервал сохранения state
- **Валидация:** `validate()` метод для проверки корректности
- **Загрузка:** `load_config()` из .env файлов

#### ✅ Config Loaders
- **Файлы:**
  - `config_loader.py` - основной загрузчик
  - `env_file_loader.py` - парсинг .env файлов
  - `config_parsers.py` - парсеры типов (bool, int, float, list)
  - `config_schema.py` - схемы валидации
- **Статус:** Готовы, используются

#### 🟡 .env.example
- **Статус:** Готов, но требует обновления для новых параметров
- **TODO:** Добавить параметры для PersistenceWorker (PERSISTENCE_INTERVAL_SECONDS)

---

### 5. Infrastructure (80% готово)

#### ✅ Logging System
- **Путь:** `src/infrastructure/logging/`
- **Статус:** Полностью готов
- **Компоненты:**
  - `log_formatter.py` - форматирование логов
  - `log_functions.py` - функции логирования (log_stage, log_tick, etc.)
  - `logger_adapter.py` - адаптер ILogger
- **Особенности:**
  - Структурированные логи с контекстом (symbol, ticker_id, etc.)
  - Цветной вывод (опционально)
  - Разные уровни (INFO, WARNING, ERROR)
- **Используется:** Повсеместно в сервисах

#### ✅ In-Memory Cache
- **Файл:** `src/infrastructure/cache/in_memory.py`
- **Статус:** Готов
- **Классы:**
  - `InMemoryMarketCache` - кэш рыночных данных (тики, order book)
  - `InMemoryIndicatorStore` - хранилище индикаторов
- **Функционал:**
  - FIFO очередь с лимитом размера
  - Быстрый доступ к последним N барам
  - Интеграция с CurrencyPair
- **Используется:** В ApplicationContext

#### ✅ Exchange Connector (CCXT Pro)
- **Файл:** `src/infrastructure/connectors/ccxt_pro_exchange_connector.py`
- **Статус:** Базовый функционал готов
- **Готовые методы:**
  - `watch_ticker()` - стриминг тикеров через WebSocket
  - `watch_order_book()` - стриминг стакана
  - Обёртка над ccxt.pro
- **🔴 НЕ ГОТОВО:**
  - `fetch_open_orders()` - загрузка открытых ордеров ⚠️ ЗАГЛУШКА
  - `fetch_order()` - получение конкретного ордера ⚠️ ЗАГЛУШКА
  - `create_order()` - размещение ордера ⚠️ НЕ РЕАЛИЗОВАНО
  - `cancel_order()` - отмена ордера ⚠️ НЕ РЕАЛИЗОВАНО
- **TODO:** Реализовать ExecutionService методы

#### ✅ File State Snapshot Store
- **Файл:** `src/infrastructure/state/file_state_snapshot_store.py`
- **Статус:** Готов
- **Функционал:**
  - Сохранение state в JSON файлы
  - Загрузка state из файлов
  - Директория: `storage/state/`
- **Используется:** В StateSnapshotService

---

### 6. Domain Services (70% готово)

#### ✅ Context Management
- **Путь:** `src/domain/services/context/`
- **Статус:** Готово
- **Модули:**
  - `context_initializer.py` - инициализация контекста
  - `state_snapshot_manager.py` - сохранение/восстановление state (**РАСШИРЕН для БД-сущностей**)
  - `market_state_updater.py` - обновление рыночного состояния
  - `indicator_recorder.py` - запись индикаторов
  - `decision_recorder.py` - запись решений стратегий
  - `window_utils.py` - утилиты для окон данных
- **Особенности:**
  - Модульная архитектура (SRP)
  - Каждый модуль < 200 строк
  - Чистая зависимость через ILogger

#### ✅ Indicators Engine
- **Путь:** `src/domain/services/indicators/`
- **Статус:** Готово (базовые индикаторы)
- **Модули:**
  - `indicator_snapshot.py` - формирование снапшота индикаторов
  - `fast_indicators.py` - быстрые индикаторы (SMA-5, SMA-7, spread, mid-price)
  - `medium_indicators.py` - средние индикаторы (RSI, SMA-20)
  - `heavy_indicators.py` - тяжёлые индикаторы (MACD, Bollinger Bands)
  - `price_history_manager.py` - управление историей цен
- **Слои расчёта:**
  - FAST (каждый тик)
  - MEDIUM (каждые N тиков)
  - HEAVY (каждые M тиков)
- **TODO:** Добавить больше индикаторов (EMA, VWAP, ATR, etc.)

#### ✅ Market Data Services
- **Путь:** `src/domain/services/market_data/`
- **Статус:** Частично готово
- **Модули:**
  - `order_book_provider.py` - провайдер order book данных
  - `order_book_analyzer.py` - анализ стакана и сигнал BUY/HOLD
  - `orderflow_simulator.py` - симуляция orderflow
  - `ticker_source.py` / `src/domain/services/ticker/ticker_source.py` - источник тиков
- **Используется:** В тестах и demo-сценариях

#### ✅ Decision Center / Orchestrator
- **Путь:** `src/domain/services/orchestrator/`
- **Статус:** Готов (BUY/HOLD логика)
- **Функционал:**
  - Отбор BUY интентов, игнорирование SELL
  - Блокировки: открытые ордера, незакрытые sell, лимиты сделок
  - Cooldown по последнему BUY
  - Анализ стакана (REJECT/SELL блокируют покупку)
  - Расчёт buy/sell параметров через калькулятор

#### ✅ Indicator Signal Service
- **Путь:** `src/domain/services/strategies/`
- **Статус:** Базовая стратегия готова
- **Функционал:**
  - BUY/HOLD по MACD + SMA (как в bad_example)
  - Генерация intents с confidence/деталями

#### ✅ Cooldown и Strategy Calculator
- **Путь:** `src/domain/services/trading/`
- **Статус:** Готово
- **Функционал:**
  - Cooldown и лимит сделок (SignalCooldownManager)
  - Расчёт buy/sell объёмов и цен по формулам из bad_example

#### ✅ RiskManager
- **Путь:** `src/domain/services/risk/`
- **Статус:** Базовая логика готова
- **Функционал:**
  - Kill-switch, min notional, лимит объёма
  - Проверка доступного баланса (если задан в контексте)
  - Расчёт stop-loss / take-profit уровней

#### 🟡 OrderSyncService
- **Файл:** `src/domain/services/order_sync_service.py`
- **Статус:** Реализован, но с заглушками
- **Функционал:**
  - `sync_orders_with_exchange()` - синхронизация ордеров
  - `fetch_and_update_order()` - обновление конкретного ордера
- **⚠️ ЗАГЛУШКИ:**
  - `_fetch_open_orders_stub()` - возвращает []
  - `_fetch_order_stub()` - возвращает None
- **TODO:** Подключить к реальному IExchangeConnector после реализации методов

#### 🟡 ExecutionService (in-memory)
- **Файл:** `src/domain/services/execution/execution_service.py`
- **Статус:** Частично готов
- **Функционал:**
  - Создание deal + buy/sell ордеров в контексте
  - Проставление `last_buy_ts` для cooldown
- **TODO:**
  - Реальные вызовы биржи (create/cancel/fetch)
  - Идемпотентность по `exchange_order_id`
  - Управление балансом и обработка ошибок

#### 🟡 Strategy System
- **Статус:** Частично реализован
- **Готово:**
  - Индикаторная стратегия BUY/HOLD (MACD + SMA)
  - Генерация intents с confidence
- **TODO:**
  - `IStrategy` интерфейс
  - Scalping/Trend/Grid стратегии
  - Вынести параметры стратегий в конфиг

---

### 7. Application Services (60% готово)

#### ✅ StateSnapshotService (**РАСШИРЕН**)
- **Файл:** `src/application/services/state_snapshot_service.py`
- **Статус:** Готов и расширен
- **Функционал:**
  - Загрузка state из файлов (load)
  - Периодическое сохранение state (maybe_save)
  - **НОВОЕ:** Сохранение БД-сущностей в БД (_save_entities_to_db)
  - **НОВОЕ:** Загрузка БД-сущностей из БД (load_from_db)
- **Зависимости:**
  - IStateSnapshotStore (файлы)
  - IDealRepository, IOrderRepository, ITradeRepository (БД)
- **Используется:** В торговом цикле

#### ✅ TickerPipelineService
- **Файл:** `src/application/services/ticker_pipeline_service.py`
- **Статус:** Готов
- **Функционал:**
  - Обработка тиков (process_tick)
  - Расчёт индикаторов
  - Обновление market state
- **Используется:** В run_realtime_trading

---

### 8. Workers (50% готово)

#### ✅ PersistenceWorker (**НОВЫЙ**)
- **Файл:** `src/application/workers/persistence_worker.py`
- **Статус:** Готов
- **Функционал:**
  - Периодический сброс в БД каждые 180 секунд
  - Сохранение активных сделок, ордеров, трейдов
  - Финальный сброс при остановке
  - Async/await для фонового выполнения
- **Используется:** Планируется в trading_loop

#### ✅ OrderBookRefreshWorker
- **Файл:** `src/application/workers/order_book_refresh_worker.py`
- **Статус:** Готов
- **Функционал:**
  - Периодическое обновление order book
  - Async worker
- **Используется:** В trading_loop (опционально)

---

### 9. Use Cases (40% готово)

#### 🟡 run_realtime_trading
- **Файл:** `src/application/use_cases/run_realtime_trading.py`
- **Статус:** Базовый функционал готов
- **Функционал:**
  - Подключение к бирже через CCXT Pro
  - Стриминг тиков
  - Обработка тиков через TickerPipelineService
  - Периодическое сохранение state
- **TODO:**
  - Интеграция PersistenceWorker
  - Интеграция OrderSyncService
  - Восстановление state из БД при старте

#### ✅ run_offline_demo
- **Файл:** `src/application/use_cases/run_offline_demo.py`
- **Статус:** Готов (для тестирования)
- **Функционал:**
  - Симуляция тиков без биржи
  - Тестирование конвейера обработки
- **Используется:** В тестах

#### 🟡 trading_loop
- **Файл:** `src/application/use_cases/trading_loop.py`
- **Статус:** В разработке
- **TODO:**
  - Интеграция стратегий
  - Принятие торговых решений
  - Вызов ExecutionService

---

## 🟡 Требует завершения перед реальной торговлей

### 1. Exchange Integration (Критично)

#### ⚠️ IExchangeConnector методы
- `fetch_open_orders(symbol)` - **ЗАГЛУШКА**
- `fetch_order(order_id)` - **ЗАГЛУШКА**
- `create_order()` - **НЕ РЕАЛИЗОВАНО**
- `cancel_order()` - **НЕ РЕАЛИЗОВАНО**
- `fetch_balance()` - **НЕ РЕАЛИЗОВАНО**
- `fetch_trades()` - **НЕ РЕАЛИЗОВАНО**

**Блокирует:** ExecutionService, OrderSyncService, торговые стратегии

---

### 2. Execution System (Критично)

#### 🟡 ExecutionService (боевой)
- Реальные вызовы `create_order/cancel_order/fetch_order`
- Идемпотентность по `exchange_order_id`
- Управление балансом и обработка ошибок

**Блокирует:** Реальное исполнение на бирже

---

### 3. Strategy System (Высокий приоритет)

#### 🟡 IStrategy интерфейс
- Генерация intents (buy/hold)
- Анализ индикаторов и market state
- Конфигурация параметров

#### 🟡 Конкретные стратегии
- Индикаторная стратегия есть (MACD + SMA)
- Нет продвинутых стратегий (Scalping/Trend/Grid)

**Блокирует:** Масштабирование стратегий

---

### 4. Risk Management (Высокий приоритет)

#### 🟡 RiskManager
- Базовые лимиты, cooldown, min notional и kill-switch есть
- Есть расчёт stop-loss / take-profit уровней (через риск-конфиг)
- Нет фактического исполнения стоп-ордеров и контроля просадки

---

### 5. Orchestrator (Средний приоритет)

#### ✅ Orchestrator / DecisionEngine
- Приём intents от стратегий
- Лимиты, cooldown, блокировки по ордерам
- Генерация финальных BUY/HOLD решений

---

### 6. Testing (Низкая покрытость)

#### 🔴 Unit Tests
- Domain entities: частично
- Repositories: есть интеграционные тесты
- Services: минимально
- Workers: нет

#### 🔴 Integration Tests
- БД репозитории: 1 тест
- Exchange integration: нет
- End-to-end: нет

#### 🔴 Fixtures & Mocks
- Mock Exchange: нет
- Mock Strategies: нет
- Test data generators: минимально

---

## 🎯 Текущий этап проекта

### **Фаза 2: Интеграция БД и Персистентность** ✅ (Завершается)

**Цели:**
- ✅ Создать все Entity классы (Deal, Order, Trade)
- ✅ Реализовать SQLAlchemy репозитории
- ✅ Подготовить миграции БД с seed-данными
- ✅ Расширить StateSnapshotService для БД
- ✅ Создать PersistenceWorker для периодического сброса
- 🟡 Интегрировать в торговый цикл (в процессе)

**Что дальше:** Переход к **Фазе 3: Exchange Integration & Execution**

---

## 🚀 Следующие шаги (Roadmap)

### Фаза 3: Exchange Integration & Execution (Критично)
**Приоритет:** 🔴 ВЫСОКИЙ
**Блокирует:** Всю торговую логику

**Задачи:**
1. Реализовать методы IExchangeConnector:
   - `fetch_open_orders()`
   - `fetch_order()`
   - `create_order()` (limit/market)
   - `cancel_order()`
   - `fetch_balance()`
2. Довести ExecutionService до боевого уровня:
   - Реальные вызовы биржи (create/cancel/fetch)
   - Идемпотентность ордеров (`exchange_order_id`)
   - Retry логика и error handling
3. Интегрировать OrderSyncService (убрать заглушки)
4. Написать тесты с mock биржей

---

### Фаза 4: Strategy System (Высокий приоритет)
**Приоритет:** 🟡 ВЫСОКИЙ
**Зависит от:** Фазы 3

**Задачи:**
1. Создать IStrategy интерфейс
2. Реализовать базовые стратегии:
   - ScalpingStrategy (простая)
   - TrendFollowingStrategy
3. Расширить Orchestrator под несколько стратегий
4. Интегрировать в trading_loop
5. Написать тесты стратегий

---

### Фаза 5: Risk Management (Высокий приоритет)
**Приоритет:** 🟡 ВЫСОКИЙ
**Зависит от:** Фазы 3, 4

**Задачи:**
1. Создать RiskManager
2. Реализовать лимиты:
   - Максимум открытых сделок
   - Размер позиции (deal_quota)
   - Stop-loss / take-profit
3. Интегрировать в Orchestrator
4. Логирование и мониторинг рисков

---

### Фаза 6: Testing & Quality (Средний приоритет)
**Приоритет:** 🟢 СРЕДНИЙ
**Параллельно с:** Фазами 3-5

**Задачи:**
1. Увеличить покрытие unit-тестами до 70%
2. Добавить интеграционные тесты:
   - Mock Exchange для тестирования торговли
   - End-to-end тесты с симуляцией
3. Создать test fixtures для сделок/ордеров
4. CI/CD pipeline (GitHub Actions)

---

### Фаза 7: Production Readiness (Низкий приоритет)
**Приоритет:** 🔵 НИЗКИЙ
**Когда:** После успешного тестирования на dev/staging

**Задачи:**
1. Мониторинг и алертинг (Prometheus + Grafana)
2. Production logging (structured logs, ELK)
3. Database migrations через Alembic
4. Graceful shutdown и recovery
5. Performance optimization
6. Security audit
7. Documentation (API, архитектура, deployment)

---

## 📝 Технический долг

### Архитектурные проблемы (из PROBLEM_ARCH.md)
- ✅ **ТЗ-1 до ТЗ-11:** Устранены импорты infrastructure из domain
- 🟡 **ТЗ-12 до ТЗ-32:** Частично разбиты God Objects (indicators engine)
- 🔴 **Остальное:** См. PROBLEM_ARCH.md

### Code Quality
- Некоторые файлы > 200 строк (требуют разбивки)
- Недостаточно docstrings в новых модулях
- Type hints не везде полные

### Performance
- Не оптимизирована работа с БД (N+1 queries возможны)
- In-memory кэш не имеет eviction policy
- Индикаторы не кэшируются между тиками

---

## 🔧 Как использовать этот документ

### Для разработки Roadmap:
1. Используй секцию "Следующие шаги" как основу для планирования
2. Фазы 3-4 - критичны для MVP
3. Фаза 5 - обязательна для production
4. Фазы 6-7 - по мере готовности

### Для создания Issues:
1. Каждая фаза → отдельный Epic/Milestone
2. Каждая задача в фазе → отдельный Issue
3. Используй метки: `critical`, `high-priority`, `medium`, `low`
4. Связывай Issues с блокирующими зависимостями

### Для оценки прогресса:
- Обновляй таблицу "Общий прогресс" по мере готовности модулей
- Отмечай завершённые фазы
- Добавляй новые секции при появлении новых компонентов

---

## 📚 Дополнительные документы

- **PROBLEM_ARCH.md** - Архитектурные проблемы и план рефакторинга
- **.claude/CLAUDE.md** - Гайдлайны разработки (DIP, SOLID, лимиты)
- **README.md** - Общее описание проекта
- **doc/** - Документация по CCXT, биржам, архитектуре

---

**Обновлено:** 2025-12-25
**Автор:** Development Team
**Версия документа:** 1.0
