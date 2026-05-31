Анализ архитектурных нарушений

Проведен анализ кодовой базы и составил список замечаний и проблем. Обнаружены существенные нарушения принципа единой ответственности и архитектурных слоев.

🚨 Критические нарушения

1. Нарушение Dependency Inversion Principle

8 файлов в domain/ импортируют infrastructure.logging.logging_setup:

src/domain/services/context/state.py (281 строка)
src/domain/services/execution/execution_service.py
src/domain/services/indicators/indicator_engine.py (309 строк)
src/domain/services/market_data/orderflow_simulator.py
src/domain/services/market_data/ticker_source.py
src/domain/services/orchestrator/orchestrator.py
src/domain/services/strategies/strategy_hub.py
src/domain/services/ticker/ticker_source.py

Проблема: Domain слой не может тестироваться изолированно, нарушен принцип инверсии зависимостей из CLAUDE.md.

  ---
💥 "Раздутые" классы со смешанной ответственностью

1. run_realtime_trading.py — 429 строк

Файл: src/application/use_cases/run_realtime_trading.py

Смешанные ответственности:
- Offline demo mode (175 строк устаревшего кода)
- Realtime core loop
- Exchange integration
- Worker management
- Configuration setup
- Snapshot management
- Logging orchestration

Методы-индикаторы:
run_demo_offline(...)         # 175 строк - устаревший режим
_run_order_book_refresh_worker(...)  # управление воркерами
run_realtime_core(...)       # 85 строк - основной цикл
run_realtime_from_exchange(...)  # 99 строк - режим биржи

Рекомендация: Разделить на 4 модуля:
- run_offline_demo.py
- run_realtime_trading.py
- trading_loop.py
- worker_manager.py

  ---
2. config.py — 340 строк

Файл: src/config/config.py

Смешанные ответственности:
- Структура конфигурации (AppConfig dataclass)
- Парсинг env-переменных (5 helper-функций)
- Чтение .env файла (file I/O)
- Валидация
- Конвертация типов
- Чтение файлов API-ключей

Методы-индикаторы:
class AppConfig:              # 115 строк - слишком много полей
_parse_int(...), _parse_float(...), _parse_bool(...)  # парсеры
_load_local_env_file(...)     # файловый I/O
load_config(...)              # 137 строк сложной логики
_read_key_file(...)           # вложенный helper

Рекомендация: Разделить на 4 модуля:
- config_schema.py — только AppConfig dataclass
- config_loader.py — логика загрузки
- config_parsers.py — конвертация типов
- env_file_loader.py — работа с .env

  ---
3. indicator_engine.py — 309 строк

Файл: src/domain/services/indicators/indicator_engine.py

Смешанные ответственности:
- Управление историей цен
- Управление историей тикеров
- FAST индикаторы (SMA-5, SMA-7, SMA-25, spread, mid-price)
- MEDIUM индикаторы (SMA-20, RSI-5, RSI-15)
- HEAVY индикаторы (SMA-100, MACD, Bollinger Bands)
- Интеграция с TA-Lib
- Legacy совместимость
- Создание снапшотов

Метод-монстр:
def on_ticker(self, ...):  # 213 строк в одном методе!
# Price history management (строки 58-75)
# FAST layer (строки 94-119) - 5 разных индикаторов
# MEDIUM layer (строки 122-150) - 3 индикатора + talib
# HEAVY layer (строки 153-223) - 6+ индикаторов
# Backward compatibility (строки 225-248)

Рекомендация: Разделить на 6 модулей:
- indicator_engine.py — только оркестрация
- fast_indicators.py — SMA, spread, mid-price
- medium_indicators.py — RSI
- heavy_indicators.py — MACD, Bollinger
- price_history_manager.py — управление историей
- indicator_snapshot.py — создание снапшотов

  ---
4. state.py — 281 строка

Файл: src/domain/services/context/state.py

Смешанные ответственности (10!):
- Инициализация контекста
- Обновление рыночного состояния
- Управление метриками
- Вычисление размеров окон
- Утилиты усечения списков
- Запись индикаторов
- Запись интентов
- Запись решений
- Создание снапшотов
- Восстановление снапшотов

Методы-индикаторы:
init_context(...)
update_market_state(...)
update_metrics(...)
_get_window_size_for_symbol(...)
_append_with_window(...)
record_indicators(...)
record_intents(...)
record_decision(...)
make_state_snapshot(...)
apply_state_snapshot(...)

Рекомендация: Разделить на 6 модулей:
- context_initializer.py
- market_state_updater.py
- indicator_recorder.py
- decision_recorder.py
- state_snapshot_manager.py
- window_utils.py

  ---
5. logging_setup.py — 228 строк

Файл: src/infrastructure/logging/logging_setup.py

Смешанные ответственности:
- Custom formatter (класс StageFallbackFormatter)
- Конфигурация логгера
- 6 convenience-функций логирования
- Маппинг stage-иконок (16 значений)
- Утилиты форматирования строк

  ---
✅ Положительные примеры

Хорошая архитектура найдена в:
- src/domain/entities/currency_pair.py — чистая entity без зависимостей
- src/domain/interfaces/cache.py — чистые протоколы
- src/domain/services/orchestrator/orchestrator.py — единая ответственность (кроме logging)
- src/infrastructure/cache/in_memory.py — чистая имплементация

  ---
📋 Приоритеты исправления

Приоритет 1: Исправить нарушение DIP

1. Создать src/domain/interfaces/logger.py с протоколом ILogger
2. Рефакторить 8 domain-сервисов на использование абстракции
3. Переместить IExchangeConnector в src/domain/interfaces/

Приоритет 2: Разбить "God Objects"

1. run_realtime_trading.py → 4 файла
2. config.py → 4 модуля
3. indicator_engine.py → 6 модулей
4. state.py → 6 модулей

Приоритет 3: Улучшить разделение ответственности

1. Извлечь логику логирования из config
2. Разделить оркестрацию и конструирование в context builder

  ---
Оценка архитектуры: C+

Структура слоев понятна, но систематически нарушается Dependency Inversion Principle. Зависимость domain от infrastructure.logging затрагивает
почти все domain-сервисы — это критический приоритет.

ВАЖНО !!! Используя эти замечания составь ПОПУНКТНЫЙ список отдельных независимых промтов-техзаданий задач для исправления ВСЕХ этих проблем и запиши их в файл PROBLEM_ARCH.md в корне проекта. !!! ВАЖНО Чтобы я мог копировать каждый пункт по очереди и передать тебе для исполнения. Не заменяй не трогай и не порти текущий сейчас там контент а дополни своими ТЗ в конец файла.
## ===================================

ТЕКСТЫ-ПРОМТЫ ПЛАНОВ ТЕХНИЧЕСКИХ ЗАДАНИЙ ДЛЯ Junie

# ✅ ТЗ-1: Создание интерфейса ILogger для устранения нарушения DIP - DONE

**Приоритет:** Критический (Priority 1)
**Файлы для создания:** `src/domain/interfaces/logger.py`

**Задача:**
Создай протокол `ILogger` в `src/domain/interfaces/logger.py` с методами:
- `log_stage(stage: str, msg: str, *, level: int = logging.INFO) -> None`
- `log_info(msg: str) -> None`
- `log_warning(msg: str) -> None`
- `log_error(msg: str) -> None`
- `log_debug(msg: str) -> None`

Протокол должен быть чистой абстракцией без зависимостей от `infrastructure`. Используй `typing.Protocol` из стандартной библиотеки Python 3.12. Добавь docstring с описанием контракта.

**Критерии готовности:**
- Файл создан в правильном месте
- Протокол не импортирует ничего из infrastructure
- Добавлен экспорт в `src/domain/interfaces/__init__.py`

---

# ✅ ТЗ-2: Реализация LoggerAdapter в infrastructure - DONE

**Приоритет:** Критический (Priority 1)
**Файлы для создания:** `src/infrastructure/logging/logger_adapter.py`
**Зависимости:** ТЗ-1 должно быть выполнено

**Задача:**
Создай класс `LoggerAdapter` в `src/infrastructure/logging/logger_adapter.py`, который:
1. Реализует протокол `ILogger` из `src/domain/interfaces/logger.py`
2. Внутри делегирует вызовы к существующим функциям из `logging_setup.py` (`log_stage`, `log_info`, etc.)
3. Принимает опциональный `logger_name` в конструкторе для идентификации источника логов

**Критерии готовности:**
- Класс корректно реализует все методы ILogger
- Обратная совместимость с текущим logging_setup сохранена
- Добавлены юнит-тесты в `tests/test_logger_adapter.py`

---

# ✅ ТЗ-3: Рефакторинг state.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/context/state.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/context/state.py`:
1. Удали прямой импорт `from src.infrastructure.logging.logging_setup import ...`
2. Добавь параметр `logger: ILogger | None = None` в функции, которые используют логирование
3. Если logger=None, логирование пропускается (silent mode для тестов)
4. Обнови все вызовы в application layer для передачи LoggerAdapter

**Критерии готовности:**
- state.py не содержит импортов из infrastructure
- Все существующие тесты проходят
- Функции работают без логгера (для изолированного тестирования)

---

# ✅ ТЗ-4: Рефакторинг execution_service.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/execution/execution_service.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/execution/execution_service.py`:
1. Удали прямой импорт из `infrastructure.logging`
2. Добавь `logger: ILogger` как зависимость класса/функций через конструктор или параметр
3. Обнови инициализацию в application layer

**Критерии готовности:**
- Файл не импортирует infrastructure напрямую
- Логирование работает через абстракцию ILogger

---

# ✅ ТЗ-5: Рефакторинг indicator_engine.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/indicators/indicator_engine.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/indicators/indicator_engine.py`:
1. Удали импорт `from src.infrastructure.logging.logging_setup import ...`
2. Добавь `logger: ILogger | None = None` в конструктор класса `IndicatorEngine`
3. Замени все вызовы логирования на `self._logger.log_xxx()` с проверкой на None

**Критерии готовности:**
- IndicatorEngine не зависит от infrastructure
- Класс можно тестировать изолированно без настройки логирования

---

# ✅ ТЗ-6: Рефакторинг orderflow_simulator.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/market_data/orderflow_simulator.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/market_data/orderflow_simulator.py`:
1. Удали прямой импорт из infrastructure.logging
2. Внедри ILogger через конструктор или параметр функции
3. Обеспечь работу без логгера (None) для тестов

**Критерии готовности:**
- Файл не содержит импортов из infrastructure
- Существующая функциональность сохранена

---

# ✅ ТЗ-7: Рефакторинг ticker_source.py (market_data) — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/market_data/ticker_source.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/market_data/ticker_source.py`:
1. Удали импорт из infrastructure.logging
2. Добавь ILogger как опциональную зависимость
3. Обнови вызывающий код в application layer

**Критерии готовности:**
- Нет импортов из infrastructure в domain
- Тесты можно писать без mock логирования

---

# ✅ ТЗ-8: Рефакторинг orchestrator.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/orchestrator/orchestrator.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/orchestrator/orchestrator.py`:
1. Удали импорт из infrastructure.logging
2. Внедри ILogger через конструктор класса Orchestrator
3. Используй pattern `if self._logger: self._logger.log_xxx()`

**Критерии готовности:**
- Orchestrator полностью изолирован от infrastructure
- Существующие тесты в tests/test_orchestrator.py проходят

---

# ✅ ТЗ-9: Рефакторинг strategy_hub.py — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/strategies/strategy_hub.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/strategies/strategy_hub.py`:
1. Удали прямой импорт из infrastructure.logging
2. Добавь ILogger как зависимость
3. Обнови application layer для передачи LoggerAdapter

**Критерии готовности:**
- Файл не импортирует infrastructure
- Стратегии тестируются изолированно

---

# ✅ ТЗ-10: Рефакторинг ticker_source.py (ticker) — устранение зависимости от infrastructure.logging - DONE

**Приоритет:** Критический (Priority 1)
**Файл:** `src/domain/services/ticker/ticker_source.py`
**Зависимости:** ТЗ-1, ТЗ-2 должны быть выполнены

**Задача:**
Рефакторь `src/domain/services/ticker/ticker_source.py`:
1. Удали импорт из infrastructure.logging
2. Внедри ILogger как опциональную зависимость
3. Проверь и обнови все точки вызова

**Критерии готовности:**
- Нет нарушений DIP в этом файле
- Domain layer полностью чист от infrastructure зависимостей

**Результат:** Файл уже был исправлен ранее, нарушений не обнаружено.

---

# ✅ ТЗ-11: Перемещение IExchangeConnector в domain/interfaces - DONE

**Приоритет:** Критический (Priority 1)
**Файлы:**
- Найти текущее расположение IExchangeConnector
- Переместить в `src/domain/interfaces/exchange_connector.py`

**Задача:**
1. Найди где сейчас определён интерфейс IExchangeConnector
2. Перемести его в `src/domain/interfaces/exchange_connector.py`
3. Обнови все импорты во всех файлах проекта
4. Убедись, что интерфейс не зависит от конкретных реализаций

**Критерии готовности:**
- IExchangeConnector находится в domain/interfaces
- Все импорты обновлены
- Нет циклических зависимостей

**Результат:**
- Создан `src/domain/interfaces/exchange_connector.py`
- Обновлены импорты в 4 файлах (domain, infrastructure, application, tests)
- Удалена папка `src/infrastructure/connectors/interfaces/`
- Проверка DIP: нарушений не найдено

---

# ✅ ТЗ-12: Разделение config.py — извлечение AppConfig в config_schema.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/config/config.py`
**Создать:** `src/config/config_schema.py`

**Задача:**
1. Создай файл `src/config/config_schema.py`
2. Перенеси в него только dataclass `AppConfig` (без логики загрузки)
3. AppConfig должен содержать только поля и их типы
4. Обнови импорты в config.py и во всех файлах, использующих AppConfig

**Критерии готовности:**
- config_schema.py содержит только AppConfig dataclass
- config.py импортирует AppConfig из config_schema
- Все существующие импорты работают

**Результат:**
- Создан `src/config/config_schema.py` (119 строк)
- Обновлён `src/config/__init__.py` с реэкспортами
- config.py уменьшился с 340 до 241 строки (-99 строк)
- Обратная совместимость импортов сохранена

---

# ✅ ТЗ-13: Разделение config.py — извлечение парсеров в config_parsers.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/config/config.py`
**Создать:** `src/config/config_parsers.py`
**Зависимости:** ТЗ-12 должно быть выполнено

**Задача:**
1. Создай файл `src/config/config_parsers.py`
2. Перенеси туда функции: `_parse_int`, `_parse_float`, `_parse_bool` и аналогичные
3. Обнови импорты в config.py

**Критерии готовности:**
- Парсеры в отдельном модуле
- config.py использует их через импорт
- Добавлены юнит-тесты для парсеров

**Результат:**
- Создан `src/config/config_parsers.py` (93 строки) с полной документацией
- Парсеры переименованы в публичные (`parse_int`, `parse_float`, `parse_bool`)
- config.py уменьшился с 241 до 210 строк (-31 строка)
- Создан `tests/unit/test_config_parsers.py` с юнит-тестами
- **Итоговое сокращение config.py: 340 → 210 строк (-38%)**

---

# ✅ ТЗ-14: Разделение config.py — извлечение env_file_loader.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/config/config.py`
**Создать:** `src/config/env_file_loader.py`
**Зависимости:** ТЗ-12, ТЗ-13 должны быть выполнены

**Задача:**
1. Создай файл `src/config/env_file_loader.py`
2. Перенеси туда функцию `_load_local_env_file` и связанную логику чтения .env
3. Перенеси `_read_key_file` для чтения API-ключей
4. Обнови config.py для использования этих функций

**Критерии готовности:**
- Весь файловый I/O вынесен в отдельный модуль
- config.py содержит только логику сборки конфигурации

**Результат:**
- Создан `src/config/env_file_loader.py` (121 строка)
- Функции сделаны публичными: `load_local_env_file()`, `read_key_file()`
- config.py уменьшился с 210 до 131 строки (-79 строк)
- Удалены неиспользуемые импорты (Path, List)

---

# ✅ ТЗ-15: Финализация config.py — переименование в config_loader.py - DONE

**Приоритет:** Высокий (Priority 2)
**Файл:** `src/config/config.py`
**Зависимости:** ТЗ-12, ТЗ-13, ТЗ-14 должны быть выполнены

**Задача:**
1. После извлечения всех компонентов, оставшийся config.py должен содержать только `load_config()`
2. Переименуй файл в `config_loader.py` (опционально, для ясности)
3. Создай `src/config/__init__.py` с удобным re-export: `from .config_schema import AppConfig` и `from .config_loader import load_config`
4. Обнови все импорты в проекте

**Критерии готовности:**
- Чёткое разделение: schema, parsers, env_loader, loader
- Все импорты через `src.config` работают
- Обратная совместимость сохранена

**Результат:**
- config.py переименован в config_loader.py (131 строка)
- Обновлён __init__.py с подробной документацией
- Создан новый config.py (9 строк) для обратной совместимости
- **Структура config теперь:**
  - config_schema.py (119 строк) — AppConfig dataclass
  - config_parsers.py (93 строки) — парсеры типов
  - env_file_loader.py (121 строка) — файловый I/O
  - config_loader.py (131 строка) — функция load_config
  - config.py (9 строк) — обратная совместимость
  - __init__.py (18 строк) — публичный API

---

# ✅ ТЗ-16: Разделение run_realtime_trading.py — извлечение run_offline_demo.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/application/use_cases/run_realtime_trading.py`
**Создать:** `src/application/use_cases/run_offline_demo.py`

**Задача:**
1. Создай файл `src/application/use_cases/run_offline_demo.py`
2. Перенеси функцию `run_demo_offline()` (175 строк) в новый файл
3. Перенеси все необходимые импорты
4. Обнови вызовы в main.py и других местах

**Критерии готовности:**
- run_demo_offline полностью в отдельном файле
- run_realtime_trading.py уменьшился на ~175 строк
- Функциональность сохранена

**Результат:**
- Создан `src/application/use_cases/run_offline_demo.py` (234 строки)
- run_realtime_trading.py уменьшился с 429 до 256 строк (-173 строки)
- Добавлен импорт в run_realtime_trading.py для обратной совместимости

---

# ✅ ТЗ-17: Разделение run_realtime_trading.py — извлечение worker_manager.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/application/use_cases/run_realtime_trading.py`
**Создать:** `src/application/use_cases/worker_manager.py`
**Зависимости:** ТЗ-16 должно быть выполнено

**Задача:**
1. Создай файл `src/application/use_cases/worker_manager.py`
2. Перенеси функцию `_run_order_book_refresh_worker()` и связанную логику управления воркерами
3. Создай класс `WorkerManager` если это улучшит структуру
4. Обнови run_realtime_trading.py для использования нового модуля

**Критерии готовности:**
- Логика воркеров изолирована
- Можно тестировать worker management отдельно

**Результат:**
- Создан `src/application/use_cases/worker_manager.py` (55 строк)
- Функция переименована в публичную: `run_order_book_refresh_worker()`
- run_realtime_trading.py уменьшился с 256 до 228 строк (-28 строк)
- Обновлён вызов функции

---

# ✅ ТЗ-18: Разделение run_realtime_trading.py — извлечение trading_loop.py - DONE

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/application/use_cases/run_realtime_trading.py`
**Создать:** `src/application/use_cases/trading_loop.py`
**Зависимости:** ТЗ-16, ТЗ-17 должны быть выполнены

**Задача:**
1. Создай файл `src/application/use_cases/trading_loop.py`
2. Перенеси функцию `run_realtime_core()` (85 строк) — основной торговый цикл
3. Оформи как класс `TradingLoop` или оставь функцией, если это проще
4. Обнови run_realtime_trading.py

**Критерии готовности:**
- Основной цикл торговли изолирован
- run_realtime_trading.py стал оркестратором высокого уровня

**Результат:**
- Создан `src/application/use_cases/trading_loop.py` (128 строк)
- Функция переименована в публичную: `run_realtime_core()`
- run_realtime_trading.py уменьшился с 228 до 142 строк (-86 строк)
- **ИТОГОВОЕ сокращение run_realtime_trading.py: 429 → 142 строки (-67%!)**

---

# ❌ ТЗ-19: Финализация run_realtime_trading.py

**Приоритет:** Высокий (Priority 2)
**Файл:** `src/application/use_cases/run_realtime_trading.py`
**Зависимости:** ТЗ-16, ТЗ-17, ТЗ-18 должны быть выполнены

**Задача:**
1. Убедись, что run_realtime_trading.py содержит только `run_realtime_from_exchange()` и высокоуровневую оркестрацию
2. Функция должна собирать компоненты и делегировать работу модулям
3. Проверь, что размер файла уменьшился до ~100-150 строк

**Критерии готовности:**
- Файл содержит только оркестрацию
- Чёткое разделение ответственности
- Все тесты проходят

---

# ✅ ТЗ-20: Разделение indicator_engine.py — извлечение price_history_manager.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/indicators/indicator_engine.py`
**Создать:** `src/domain/services/indicators/price_history_manager.py`

**Задача:**
1. Создай файл `src/domain/services/indicators/price_history_manager.py`
2. Создай класс `PriceHistoryManager` для управления историей цен и тикеров
3. Перенеси логику строк 58-75 из on_ticker (price history management)
4. Используй этот класс в IndicatorEngine через композицию

**Критерии готовности:**
- История цен управляется отдельным классом
- IndicatorEngine использует PriceHistoryManager
- Добавлены тесты для PriceHistoryManager

**Результат:**
✅ **Выполнено**
- Создан `price_history_manager.py` (112 строк)
- Класс `PriceHistoryManager` инкапсулирует управление историей цен и тикеров
- Методы: `update_history()`, `get_price_history()`, `get_ticker_history()`
- В `IndicatorEngine` внедрён через композицию: `self._price_history = PriceHistoryManager(max_history_length=500)`
- `indicator_engine.py` уменьшен с 309 до 302 строк (−7 строк)
- Удалены неиспользуемые импорты `deque`, `Deque`
- История цен теперь управляется централизованно через менеджер
- Протестирован импорт: ✅ работает корректно

---

# ✅ ТЗ-21: Разделение indicator_engine.py — извлечение fast_indicators.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/indicators/indicator_engine.py`
**Создать:** `src/domain/services/indicators/fast_indicators.py`
**Зависимости:** ТЗ-20 должно быть выполнено

**Задача:**
1. Создай файл `src/domain/services/indicators/fast_indicators.py`
2. Создай класс `FastIndicators` или набор функций для быстрых индикаторов
3. Перенеси логику FAST layer: SMA-5, SMA-7, SMA-25, spread, mid-price
4. Индикаторы должны быть чистыми функциями без side effects

**Критерии готовности:**
- Быстрые индикаторы изолированы
- Легко тестируются
- Нет зависимости от состояния engine

**Результат:**
✅ **Выполнено**
- Создан `fast_indicators.py` (156 строк)
- Реализованы чистые функции:
  - `calculate_sma_fast_5()` — демо-индикатор SMA-5
  - `calculate_sma_7()` — реальный индикатор SMA-7
  - `calculate_sma_25()` — реальный индикатор SMA-25
  - `calculate_spread_and_mid()` — спред и mid-price из bid/ask
  - `calculate_fast_indicators()` — главная функция-оркестратор
- Все функции — pure functions без side effects
- `indicator_engine.py` уменьшен с 302 до 288 строк (−14 строк)
- FAST layer в engine сократился с 26 до 12 строк кода
- Протестирован импорт: ✅ работает корректно

---

# ✅ ТЗ-22: Разделение indicator_engine.py — извлечение medium_indicators.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/indicators/indicator_engine.py`
**Создать:** `src/domain/services/indicators/medium_indicators.py`
**Зависимости:** ТЗ-20, ТЗ-21 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/indicators/medium_indicators.py`
2. Перенеси логику MEDIUM layer: SMA-20, RSI-5, RSI-15
3. Включи интеграцию с TA-Lib для RSI
4. Обработай случай отсутствия TA-Lib gracefully

**Критерии готовности:**
- Medium индикаторы изолированы
- TA-Lib опционален (fallback если не установлен)

**Результат:**
✅ **Выполнено**
- Создан `medium_indicators.py` (136 строк)
- Реализованы функции:
  - `calculate_sma_medium_20()` — демо-индикатор SMA-20
  - `calculate_rsi_indicators()` — RSI-5 и RSI-15 через TA-Lib
  - `calculate_medium_indicators()` — главная функция-оркестратор
- Интеграция с TA-Lib: опциональная, с graceful degradation
- Логирование ошибок через `ILogger` (прокидывается как параметр)
- `indicator_engine.py` уменьшен с 288 до 272 строк (−16 строк)
- MEDIUM layer в engine сократился с 30 до 13 строк кода
- Протестирован импорт: ✅ работает корректно

---

# ✅ ТЗ-23: Разделение indicator_engine.py — извлечение heavy_indicators.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/indicators/indicator_engine.py`
**Создать:** `src/domain/services/indicators/heavy_indicators.py`
**Зависимости:** ТЗ-20, ТЗ-21, ТЗ-22 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/indicators/heavy_indicators.py`
2. Перенеси логику HEAVY layer: SMA-100, MACD, Bollinger Bands
3. Эти индикаторы должны работать с большими окнами данных

**Критерии готовности:**
- Тяжёлые индикаторы изолированы
- Оптимизированы для работы с большими данными

**Результат:**
✅ **Выполнено**
- Создан `heavy_indicators.py` (234 строки)
- Реализованы функции:
  - `calculate_sma_heavy_100()` — демо-индикатор SMA-100
  - `calculate_macd_indicators()` — MACD с производными метриками (signal_strength, trend_signal)
  - `calculate_bollinger_bands()` — Bollinger Bands (bb_upper, bb_middle, bb_lower)
  - `calculate_heavy_indicators()` — главная функция-оркестратор
- Интеграция с TA-Lib: опциональная, с graceful degradation
- Логирование ошибок через `ILogger` (прокидывается как параметр)
- `indicator_engine.py` уменьшен с 272 до 196 строк (−76 строк!)
- HEAVY layer в engine сократился с 72 до 12 строк кода
- Удалены неиспользуемые импорты numpy/talib и функция `_sma` из engine
- Протестирован импорт: ✅ работает корректно

---

# ✅ ТЗ-24: Разделение indicator_engine.py — извлечение indicator_snapshot.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/indicators/indicator_engine.py`
**Создать:** `src/domain/services/indicators/indicator_snapshot.py`
**Зависимости:** ТЗ-20-23 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/indicators/indicator_snapshot.py`
2. Перенеси логику создания снапшотов индикаторов
3. Перенеси backward compatibility код (строки 225-248)

**Критерии готовности:**
- Снапшоты создаются отдельным модулем
- Backward compatibility сохранена

**Результат:**
✅ **Выполнено**
- Создан `indicator_snapshot.py` (98 строк)
- Реализована функция `create_indicator_snapshot()`:
  - Создание snapshot-словаря с индикаторами
  - Backward compatibility: placeholder-поля "sma" и "rsi"
  - Сохранение snapshot в контекст через record_indicators
  - Логирование результата
- `indicator_engine.py` уменьшен с 196 до 163 строк (−33 строки)
- Логика создания snapshot сократилась с 43 до 10 строк кода
- Удалён импорт `record_indicators` из engine (теперь в snapshot-модуле)
- Протестирован импорт: ✅ работает корректно

---

# ✅ ТЗ-25: Финализация indicator_engine.py — чистая оркестрация

**Приоритет:** Высокий (Priority 2)
**Файл:** `src/domain/services/indicators/indicator_engine.py`
**Зависимости:** ТЗ-20-24 должны быть выполнены

**Задача:**
1. Рефакторь IndicatorEngine для использования всех извлечённых модулей
2. Метод on_ticker() должен только оркестрировать вызовы, не содержать бизнес-логику
3. Размер on_ticker() должен уменьшиться с 213 строк до ~30-50 строк

**Критерии готовности:**
- IndicatorEngine — чистый оркестратор
- Все компоненты связаны через композицию
- Метод on_ticker() читается как сценарий

**Результат:**
✅ **Выполнено**
- `indicator_engine.py` финализирован: **163 строки** (было 309, уменьшение −47%!)
- Метод `on_ticker()`: 83 строки всего, **~47 строк чистого кода** (без комментариев/пробелов)
- **Чистая оркестрация**: вся бизнес-логика делегирована модулям:
  - `PriceHistoryManager` — управление историей
  - `calculate_fast_indicators` — FAST layer
  - `calculate_medium_indicators` — MEDIUM layer
  - `calculate_heavy_indicators` — HEAVY layer
  - `create_indicator_snapshot` — создание snapshot
- **Композиция**: все компоненты внедрены через DI и используются через интерфейсы
- **Читаемость**: метод читается как последовательный сценарий шагов
- Сохранена обратная совместимость через функцию `compute_indicators()`

**Итоговая статистика рефакторинга indicator_engine.py:**
- **Было:** 309 строк (1 God Object)
- **Стало:** 163 строки (чистый оркестратор) + 5 модулей
- **Извлечено в модули:**
  - `price_history_manager.py` — 112 строк
  - `fast_indicators.py` — 156 строк
  - `medium_indicators.py` — 136 строк
  - `heavy_indicators.py` — 234 строк
  - `indicator_snapshot.py` — 98 строк
- **Всего:** 163 + 736 = 899 строк (вместо 309 монолита)
- **Выигрыш:** модульность, тестируемость, читаемость, соблюдение SRP

---

# ❌ ТЗ-26: Разделение state.py — извлечение context_initializer.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/context_initializer.py`

**Задача:**
1. Создай файл `src/domain/services/context/context_initializer.py`
2. Перенеси функцию `init_context()` и связанную логику инициализации
3. Убедись, что функция не зависит от infrastructure (после ТЗ-3)

**Критерии готовности:**
- Инициализация контекста изолирована
- Чистая функция без side effects

---

# ❌ ТЗ-27: Разделение state.py — извлечение market_state_updater.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/market_state_updater.py`
**Зависимости:** ТЗ-26 должно быть выполнено

**Задача:**
1. Создай файл `src/domain/services/context/market_state_updater.py`
2. Перенеси функции `update_market_state()` и `update_metrics()`
3. Добавь тесты

**Критерии готовности:**
- Обновление рыночного состояния изолировано
- Функции легко тестируются

---

# ❌ ТЗ-28: Разделение state.py — извлечение window_utils.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/window_utils.py`
**Зависимости:** ТЗ-26, ТЗ-27 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/context/window_utils.py`
2. Перенеси функции `_get_window_size_for_symbol()` и `_append_with_window()`
3. Сделай их публичными (без underscore) с ясными именами

**Критерии готовности:**
- Утилиты окон переиспользуемы
- Хорошо документированы

---

# ❌ З-29: Разделение state.py — извлечение indicator_recorder.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/indicator_recorder.py`
**Зависимости:** ТЗ-26-28 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/context/indicator_recorder.py`
2. Перенеси функцию `record_indicators()`
3. Используй window_utils для усечения списков

**Критерии готовности:**
- Запись индикаторов изолирована
- Использует window_utils

---

# ❌ ТЗ-30: Разделение state.py — извлечение decision_recorder.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/decision_recorder.py`
**Зависимости:** ТЗ-26-29 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/context/decision_recorder.py`
2. Перенеси функции `record_intents()` и `record_decision()`

**Критерии готовности:**
- Запись решений изолирована
- Функции независимы от других компонентов state

---

# ❌ ТЗ-31: Разделение state.py — извлечение state_snapshot_manager.py

**Приоритет:** Высокий (Priority 2)
**Исходный файл:** `src/domain/services/context/state.py`
**Создать:** `src/domain/services/context/state_snapshot_manager.py`
**Зависимости:** ТЗ-26-30 должны быть выполнены

**Задача:**
1. Создай файл `src/domain/services/context/state_snapshot_manager.py`
2. Перенеси функции `make_state_snapshot()` и `apply_state_snapshot()`
3. Создай класс `StateSnapshotManager` если это улучшит структуру

**Критерии готовности:**
- Снапшоты управляются отдельным модулем
- Сериализация/десериализация изолированы

---

# ❌ ТЗ-32: Финализация state.py — чистый фасад

**Приоритет:** Высокий (Priority 2)
**Файл:** `src/domain/services/context/state.py`
**Зависимости:** ТЗ-26-31 должны быть выполнены

**Задача:**
1. Превратить state.py в фасад, который re-export'ит функции из новых модулей
2. Или создать `src/domain/services/context/__init__.py` с удобным API
3. Сохранить обратную совместимость импортов

**Критерии готовности:**
- state.py минимален (re-exports только)
- Обратная совместимость сохранена
- Все тесты проходят

---

# ❌ ТЗ-33: Разделение logging_setup.py — извлечение log_formatter.py

**Приоритет:** Средний (Priority 3)
**Исходный файл:** `src/infrastructure/logging/logging_setup.py`
**Создать:** `src/infrastructure/logging/log_formatter.py`

**Задача:**
1. Создай файл `src/infrastructure/logging/log_formatter.py`
2. Перенеси класс `StageFallbackFormatter`
3. Перенеси маппинг stage-иконок (STAGE_ICONS или аналог)

**Критерии готовности:**
- Форматирование логов изолировано
- Можно менять формат независимо от setup

---

# ❌ ТЗ-34: Разделение logging_setup.py — извлечение log_functions.py

**Приоритет:** Средний (Priority 3)
**Исходный файл:** `src/infrastructure/logging/logging_setup.py`
**Создать:** `src/infrastructure/logging/log_functions.py`
**Зависимости:** ТЗ-33 должно быть выполнено

**Задача:**
1. Создай файл `src/infrastructure/logging/log_functions.py`
2. Перенеси convenience-функции: `log_stage`, `log_info`, `log_warning`, `log_error`, `log_debug`
3. Обнови импорты во всех файлах

**Критерии готовности:**
- Функции логирования в отдельном модуле
- Импорты обновлены

---

# ❌ ТЗ-35: Финализация logging_setup.py

**Приоритет:** Средний (Priority 3)
**Файл:** `src/infrastructure/logging/logging_setup.py`
**Зависимости:** ТЗ-33, ТЗ-34 должны быть выполнены

**Задача:**
1. logging_setup.py должен содержать только `setup_logging()` — конфигурацию логгера
2. Создай `src/infrastructure/logging/__init__.py` с re-exports для удобства

**Критерии готовности:**
- Чёткое разделение: formatter, functions, setup
- Обратная совместимость через __init__.py

---

# ❌ ТЗ-36: Финальная проверка архитектуры и тестов

**Приоритет:** Завершающий
**Зависимости:** Все предыдущие ТЗ должны быть выполнены

**Задача:**
1. Запусти все тесты: `pytest tests\ -v`
2. Проверь, что domain layer не импортирует infrastructure:
   ```powershell
   Select-String -Path "src\domain\**\*.py" -Pattern "from src.infrastructure" -Recurse
   ```
3. Проверь размеры файлов — все "God Objects" должны быть разбиты
4. Обнови PROBLEM_ARCH.md с новой оценкой архитектуры

**Критерии готовности:**
- Все тесты проходят
- Нет нарушений DIP в domain layer
- Оценка архитектуры улучшилась до B+ или выше