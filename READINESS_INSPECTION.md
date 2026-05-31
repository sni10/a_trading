# Архитектурно-техническое состояние (конкретика)

Осмотр выполнен по коду и документам, без запуска сценариев.

## 1. Runtime-контур (realtime)
- Вход: `main.py:_run_cli` -> `src/application/use_cases/run_realtime_trading.py:run_realtime_from_exchange`.
- Контекст: `src/domain/services/context/state.py:init_context` + `src/application/context.py:build_context`.
- Источник тиков: `src/domain/services/ticker/ticker_source.py:TickSource.stream` ->
  `src/infrastructure/connectors/ccxt_pro_exchange_connector.py:CcxtProExchangeConnector.stream_ticks`.
- Цикл: `src/application/use_cases/trading_loop.py:run_realtime_core`.
- Конвейер: `src/application/services/ticker_pipeline_service.py:process_tick`:
  FEEDS -> IND -> STRAT -> ORCH -> EXEC -> STATE.

## 2. Модель и хранение
- Entities: `src/domain/entities/currency_pair.py`, `deal.py`, `order.py`, `trade.py`.
- Репозитории: `src/infrastructure/repositories/*` через интерфейсы `src/domain/interfaces/*`.
- Инициализация БД: `src/infrastructure/db/__init__.py` + миграции `src/infrastructure/db/migrations/*`.
- Фабрика репозиториев: `src/application/repository_factory.py`.

## 3. Подсистемы: факт реализации
### 3.1 Рынок и биржа (частично)
- Реализовано: `IExchangeConnector` содержит только `stream_ticks` и `fetch_order_book`
  (`src/domain/interfaces/exchange_connector.py`).
- Реализация: `CcxtProExchangeConnector.stream_ticks` (watch_tickers) и `fetch_order_book`
  (fetch_order_book) в `src/infrastructure/connectors/ccxt_pro_exchange_connector.py`.
- Отсутствует: приватные методы биржи (create/cancel/fetch order, balance, trades) в интерфейсе и реализации.

### 3.2 Индикаторы (готово)
- Модули: `fast_indicators.py`, `medium_indicators.py`, `heavy_indicators.py`,
  `price_history_manager.py`, `indicator_snapshot.py`.
- Оркестрация: `IndicatorEngine.on_ticker` + `compute_indicators`
  (`src/domain/services/indicators/indicator_engine.py`).

### 3.3 Стратегии (минимум)
- `IndicatorSignalService` оценивает MACD + SMA и возвращает BUY/HOLD
  (`src/domain/services/strategies/indicator_signal_service.py`).
- `evaluate_strategies` формирует один intent
  (`src/domain/services/strategies/strategy_hub.py`).

### 3.4 Оркестратор (готово для BUY/HOLD)
- `DecisionCenter.decide` включает cooldown, orderbook-анализ, расчет цены/объема,
  риск-проверки (`src/domain/services/orchestrator/decision_center.py`).

### 3.5 Исполнение (симуляция)
- `execute` создает in-memory Deal/Order без биржи
  (`src/domain/services/execution/execution_service.py`).
- Нет обращения к бирже, нет обновления статусов из биржи, нет работы с балансами.

### 3.6 Синхронизация ордеров (заглушки)
- `OrderSyncService` вызывает `_fetch_open_orders_stub` (возвращает `[]`)
  и `_fetch_order_stub` (возвращает `None`) в `src/domain/services/order_sync_service.py`.
- В `IExchangeConnector` отсутствуют методы, которые эти заглушки должны заменить.

### 3.7 Персистентность (частично)
- Снапшоты state: `StateSnapshotService.load/maybe_save`
  (`src/application/services/state_snapshot_service.py`).
- БД-сброс: `_save_entities_to_db` внутри `StateSnapshotService`,
  вызывается из `PersistenceWorker` (`src/application/workers/persistence_worker.py`).

### 3.8 Воркеры (минимум)
- `order_book_refresh_worker` крутится в цикле и пишет в cache,
  без backoff и обработки сетевых ошибок (`src/application/workers/order_book_refresh_worker.py`).

## 4. Несоответствия и долги (с фактом)
- `OrderSyncService` требует `fetch_open_orders/fetch_order`, но в `IExchangeConnector` их нет
  (`src/domain/interfaces/exchange_connector.py`).
- `TickPipelineService` использует `LoggerAdapter`, но не передает `logger` в
  `evaluate_strategies/decide/execute` (`src/application/services/ticker_pipeline_service.py`).
- Балансы: `RiskManager` читает `context["balances"]`, но заполнения балансов нигде нет
  (нет `fetch_balance`) (`src/domain/services/risk/risk_manager.py`).
- `run_offline_demo` помечен как DEPRECATED (`src/application/use_cases/run_offline_demo.py`).
- Совместимость конфигурации: `src/config/config.py` отмечен как DEPRECATED и только re-export.

## 5. Главные блокеры для боевого режима
- Приватные методы биржи и их контракт в `IExchangeConnector`.
- Реальное выставление/отмена ордеров отсутствует; исполнение только in-memory.
- Источник балансов и интеграция с риск-контуром отсутствуют.
- Устойчивость I/O: retry/backoff/таймауты в воркерах и коннекторе отсутствуют.
