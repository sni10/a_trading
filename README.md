# 🚀 Algorithmic Trading System – Prototype

> ⚠️ **WARNING: Prototype only. Not suitable for real-money trading.**

Этот репозиторий содержит **облегчённый прототип** событийной системы
алгоритмической торговли для криптобирж. Основной фокус кода —
**архитектура и чистый конвейер обработки тиков**, а не Production‑уровень
исполнения.

---

## 📋 Table of Contents
- [🎯 Overview](#-overview)
- [⚙️ Stack and Entry Points](#%EF%B8%8F-stack-and-entry-points)
- [🏗️ High‑Level Architecture](#%EF%B8%8F-highlevel-architecture)
- [✨ Features and Limitations](#-features-and-limitations)
- [📦 Requirements](#-requirements)
- [🚀 Setup and Running](#-setup-and-running)
- [📊 Backtest](#-backtest)
- [🛠️ Scripts and Utilities](#%EF%B8%8F-scripts-and-utilities)
- [🔧 Environment Variables and Configuration](#-environment-variables-and-configuration)
- [🧪 Tests](#-tests)
- [📂 Project Structure](#-project-structure)
- [📄 License](#-license)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)

---

## 🎯 Overview

Прототип реализует упрощённый тиковый конвейер:

```
🚀 BOOT → 📥 LOAD → 🔥 WARMUP → 🔄 LOOP
    ↓
📊 TICK → 🌐 FEEDS → 📈 IND → 🧠 CTX → 🎯 STRAT → 🎭 ORCH → ⚡ EXEC → 💾 STATE
```

Ключевая идея: каждый тик рыночных данных проходит через чётко выделенные
стадии — от генерации до расчёта индикаторов, оценки стратегий, оркестрации и
"исполнения" — с единообразным логированием на каждом шаге.

**Текущее состояние:** экспериментальный прототип для локальных запусков и
архитектурных экспериментов. Целевая архитектура, к которой движется
прототип, описана в `doc/designing/GIUDELINE.md` и `bad_example/docs/*`.

---

## ⚙️ Stack and Entry Points

### 💻 Technology Stack
- **Language:** Python 3.12 (целевая версия для нового прототипа)
- **Main libraries:**
  - `logging` (standard library) – структурированное логирование
  - Зависимости проекта перечислены в `requirements.txt` (см. ниже). Многие из
    них используются в основном наследуемым проектом `bad_example` или будут
    задействованы на более поздних этапах развития прототипа.
- **Package manager:** `pip` (через `requirements.txt`)

### 🎯 Entry Points

**Верхнеуровневый запуск прототипа (текущий репозиторий):**
- `python main.py BTC/USDT` →
  запускает упрощённый тиковый конвейер для **одной** валютной пары.

  Пара передаётся как ключ процесса ("один процесс → одна пара"). Внутри
  используется централизованный конфиг `AppConfig` из
  `src/config/config.py` и репозиторий `CurrencyPair`.

**Наследуемая полная система (только как референс):**
- `cd bad_example`
- `python main.py` (подробности см. в `bad_example/README.md`).

> 📝 **Note:** В **новом прототипе пока нет реальной интеграции с CCXT / WebSocket**.
> Все тики генерируются локальным симулятором.

---

## 🏗️ High‑Level Architecture

Новый прототип следует упрощённому варианту архитектуры,
описанной в `doc/designing/GIUDELINE.md` и
`bad_example/docs/architecture/FILE_STRUCTURE.md`.

### 🔄 Ticker Pipeline

Система следует последовательной архитектуре конвейера:

```
🚀 BOOT → 📥 LOAD → 🔥 WARMUP → 🔄 LOOP
    ↓
📊 TICK → 🌐 FEEDS → 📈 IND → 🧠 CTX → 🎯 STRAT → 🎭 ORCH → ⚡ EXEC → 💾 STATE
```

### 📊 Stage Overview

| Stage | Description |
|-------|-------------|
| 🚀 **BOOT** | Инициализация системы и конфигурации |
| 📥 **LOAD** | Загрузка торговых пар, ордеров и позиций из хранилища |
| 🔥 **WARMUP** | Предварительное заполнение индикаторов и стаканов из исторических данных |
| 📊 **TICK** | Получение тика рыночных данных |
| 🌐 **FEEDS** | Обновление рыночного кеша новыми данными |
| 📈 **IND** | Вычисление технических индикаторов |
| 🧠 **CTX** | Построение комплексного торгового контекста |
| 🎯 **STRAT** | Оценка торговых стратегий |
| 🎭 **ORCH** | Оркестрация и принятие решений |
| ⚡ **EXEC** | Исполнение торговых решений |
| 💾 **STATE** | Обновление метрик системы и состояния |

### 🧩 Main Components (New Prototype)

#### 📈 Data and Context

- `src.domain.services.market_data.tick_source.generate_ticks` – простой
  генератор тиков, имитирующий обновление цен для списка символов.
- `src.domain.services.context.state` – контекст в памяти с текущими
  рыночными данными, позициями и базовыми метриками.
- `src.infrastructure.logging.logging_setup` – общий модуль настройки логов и
  хелпер `log_stage()`, используемый по всему конвейеру.

#### 📊 Indicator Engine (placeholder)

- `src.domain.services.indicators.indicator_engine.compute_indicators` –
  фиктивные технические индикаторы (например, `sma = price`, `rsi = 50.0`) с
  корректным интерфейсом и логированием; выступают заглушкой для будущего
  `IndicatorEngine`.

#### 🎯 Strategies (demo)

- `src.domain.services.strategies.strategy_hub.evaluate_strategies` – формирует
  список intents на основе простой демонстрационной логики (например,
  решений, привязанных к `tick_id`).

#### 🎭 Orchestrator and Execution (demo)

- `src.domain.services.orchestrator.orchestrator.decide` – наивный
  оркестратор, который сейчас выбирает первый intent с `action != "HOLD"`.
- `src.domain.services.execution.execution_service.execute` – заглушка
  Execution‑сервиса, которая только логирует, что было бы отправлено на биржу.

---

## ✨ Features and Limitations

### ✅ Implemented

- Событийный **тиковый конвейер** с явными стадиями (`TICK`, `IND`, `STRAT`,
  `ORCH`, `EXEC`, `STATE`).
- **Структурированное логирование** с единым хелпером `log_stage()` и
  ротируемыми лог-файлами в `logs/`.
- **Контекст/состояние в памяти**, обновляемое на каждом тике.
- **Технические индикаторы**: MACD, RSI, SMA‑5/7/20/25, Bollinger Bands, спред.
- **Стратегии**: `IndicatorSignalService` (MACD + SMA‑7/25 → BUY/HOLD) + стакан-фильтр.
- **Оркестратор**: risk-лимиты, таймаут протухших ордеров, принятие решений.
- **Исполнение**: идемпотентные лимитные ордера (`clientOrderId`), Deal-lifecycle.
- **Биржевой коннектор** (`CcxtProExchangeConnector`): `stream_ticks`, `fetch_order_book`,
  `fetch_balance`, `create_order`, `cancel_order`, `fetch_order`, `fetch_ohlcv`.
- **SQLAlchemy 2.0+** репозитории (Order, Trade, Deal, CurrencyPair) — работают
  с SQLite и PostgreSQL.
- **Офлайн-бэктест** (`backtest.py`) — полный прогон стратегии на исторических
  OHLCV-данных с метриками PnL / winrate / drawdown (см. раздел [📊 Backtest](#-backtest)).

### ⚠️ Prototype‑Only / Ограничения

- Нет Production‑grade обработки ошибок, мониторинга, алертов.
- Нет автоматического forward-test на testnet.
- Нет полноценного risk management (позиционирование, портфель).
- Бэктест использует bar-vs-tick упрощение (close свечи = last тик).

За подробностями о долгосрочном направлении см. `doc/` и `BACKTEST_PLAN.md`.

---

## 📦 Requirements

Для **нового прототипа** в этом репозитории:

- **Python:** 3.12.x
- **OS:** основная разработка и тестирование ведутся под Windows; прототип
  должен работать и на других платформах при наличии Python 3.12 и нужных
  зависимостей (обратите внимание, что `pywin32` в `requirements.txt`
  предназначен только для Windows и помечен платформенным условием).
- **Dependencies:**
  - Для минимального запуска прототипа (без реальной биржи / БД)
    используются только стандартная библиотека и внутренние модули.
  - Для разработки и запуска тестов установите пакеты из `requirements.txt`:

    ```powershell
    pip install -r requirements.txt
    ```

Для **наследуемой полной системы** в каталоге `bad_example/` см.
`bad_example/requirements.txt` и `bad_example/README.md`.

> 📝 **TODO:** явно задокументировать минимальный набор зависимостей, необходимый
> именно для нового конвейера `src/*`, когда он начнёт использовать CCXT,
> TA‑Lib и другие библиотеки в Production‑подобных сценариях.

---

## 🚀 Setup and Running

Из корня репозитория (`algorithmic_trading`):

### 1️⃣ Создайте и активируйте виртуальное окружение (рекомендуется)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2️⃣ Установите зависимости (для разработки и тестов)

```powershell
pip install -r requirements.txt
```

### 3️⃣ Запустите тиковый конвейер прототипа

```powershell
python main.py BTC/USDT
```

Эта команда запускает конвейер для **одной** валютной пары, переданной в
CLI. Внутри вызывается `src.application.use_cases.run_realtime_trading.run()`
с конфигом `AppConfig`, собранным через `load_config()`.

Если переменные окружения не заданы, по умолчанию используются значения из
`AppConfig` (см. `src/config/config.py`), в том числе:

- `max_ticks=10`
- `tick_sleep_sec=2.0`

В консоли и в файле `logs/prototype.log` будут писаться структурированные
логи.

### 4️⃣ (опционально) Запустите наследуемую reference‑реализацию

```powershell
cd bad_example
python main.py
```

Это запустит более старую, более сложную архитектуру, описанную в
`bad_example/docs/architecture/PROJECT_OVERVIEW.md`.

---

## 📊 Backtest

Офлайн-бэктест прогоняет боевой торговый конвейер на исторических OHLCV-данных
(без реального подключения к бирже во время прогона) и выдаёт метрики прибыльности.

### ⚡ Быстрый старт

```powershell
# Бэктест BTC/USDT за Q1 2025, таймфрейм 1h, стартовый баланс 1000 USDT
python backtest.py BTC/USDT --from 2025-01-01 --to 2025-03-31

# Тот же прогон + сохранить equity-кривую в CSV
python backtest.py BTC/USDT --from 2025-01-01 --to 2025-03-31 --csv equity.csv

# Другой таймфрейм и баланс, без кэша (свежая загрузка с биржи)
python backtest.py ETH/USDT --from 2025-01-01 --to 2025-06-01 --timeframe 4h --balance 5000 --no-cache
```

> ⚠️ Первый запуск скачивает свечи с биржи через CCXT — нужны `EXCHANGE_API_KEY` /
> `EXCHANGE_API_SECRET` в `.env` (или testnet-ключи при `EXCHANGE_TESTNET=true`).
> Повторные прогоны берут данные из локального кэша `data/ohlcv_cache/` — биржа
> не вызывается.

### 🔧 Все параметры CLI

| Параметр | Обязательный | По умолчанию | Описание |
|----------|:---:|:---:|----------|
| `symbol` | ✅ | — | Торговая пара: `BTC/USDT`, `ETH/USDT`, … |
| `--from DATE` | ✅ | — | Начало периода `YYYY-MM-DD` |
| `--to DATE` | — | сегодня | Конец периода `YYYY-MM-DD` |
| `--timeframe TF` | — | `1h` | Таймфрейм свечей: `1m`, `5m`, `15m`, `1h`, `4h`, `1d` |
| `--balance N` | — | `1000.0` | Стартовый баланс в USDT |
| `--buy-fee N` | — | `0.1` | Комиссия на покупку, % (0.1 = 0.1%) |
| `--sell-fee N` | — | `0.1` | Комиссия на продажу, % |
| `--no-cache` | — | off | Принудительно скачать свечи с биржи (не читать кэш) |
| `--csv FILE` | — | — | Сохранить equity-кривую в CSV-файл |

### 📋 Формат отчёта

```
==================================================
        BACKTEST REPORT
==================================================
  Сделок всего:      42
  Прибыльных:        24
  Убыточных:         18
  Winrate:           57.1%
  Суммарный PnL:     +123.4567 USDT
  Средний PnL:       +2.9394 USDT
  Max Drawdown:      45.2300 USDT
  Стартовый баланс:  1000.0000 USDT
  Итоговый баланс:   1123.4567 USDT
  Доходность:        +12.34%
==================================================

Допущения:
  - bar-vs-tick: close свечи = last тик (упрощение)
  - Упрощённая модель филлов (без проскальзывания)
  - Нейтральный стакан (orderbook-фильтр не режет сигналы)
  - Результат — оценка 'сверху'; реальные результаты ≤ бэктеста
```

### 🗄️ Кэш OHLCV-данных

Свечи кэшируются в `data/ohlcv_cache/` (папка в `.gitignore`).
Имя файла кодирует символ + таймфрейм + начало периода:

```
data/ohlcv_cache/
└── BTC_USDT_1h_1735689600000.json   # BTC/USDT, 1h, since=2025-01-01
```

- При повторном `python backtest.py BTC/USDT --from 2025-01-01 ...` данные
  берутся из кэша мгновенно — биржа не вызывается.
- Чтобы обновить данные — добавьте флаг `--no-cache`.
- Чтобы очистить весь кэш: `Remove-Item data\ohlcv_cache\* -Force`.

### 🏗️ Архитектура бэктеста

```
fetch_ohlcv (с кэшем)
   → HistoricalTickSource: свеча → Ticker (close = last)
      → BacktestRunner (цикл по тикам):
           process_tick(context)       # боевой конвейер: IND → STRAT → ORCH → EXEC
           FillSimulator.on_tick()     # пометить filled, закрыть deal, обновить баланс
           MetricsCollector.record()   # снять equity / зафиксировать сделку
      → MetricsCollector.finalize()   # итоговый отчёт
```

| Модуль | Путь | Назначение |
|--------|------|------------|
| `BacktestConfig` | `src/application/backtest/backtest_config.py` | Параметры прогона (dataclass) |
| `OhlcvCache` | `src/application/backtest/ohlcv_cache.py` | Дисковый кэш свечей |
| `HistoricalTickSource` | `src/application/backtest/historical_tick_source.py` | OHLCV → поток тиков |
| `FillSimulator` | `src/application/backtest/fill_simulator.py` | Симулятор исполнения ордеров |
| `MetricsCollector` | `src/application/backtest/metrics_collector.py` | PnL / winrate / drawdown |
| `BacktestRunner` | `src/application/backtest/backtest_runner.py` | Оркестрация прогона |
| `run_backtest` | `src/application/use_cases/run_backtest.py` | Use case: загрузка + запуск |

### ⚠️ Важные допущения

1. **Bar-vs-tick** — стратегия считает индикаторы по `close` свечи, а не по
   реальному тик-потоку. Результаты могут незначительно отличаться от боевого
   прогона.
2. **Упрощённая модель филлов** — ордер заполняется при пересечении ценой
   уровня. Проскальзывание, частичные исполнения и глубина стакана не
   моделируются. Реальные результаты **≤ бэктеста**.
3. **Нейтральный стакан** — orderbook-фильтр в `DecisionCenter` не активен
   (исторического стакана нет). Бэктест пропускает больше BUY-сигналов, чем
   в реальном режиме.
4. **Комиссии обязательно учтены** — задаются через `--buy-fee` / `--sell-fee`.

---

## 🛠️ Scripts and Utilities

### 🔧 Local helper scripts (`local_run/`)

Эти скрипты предназначены для экспериментов и локальных утилит; они **не**
являются частью основного API конвейера, но могут быть полезны в процессе
разработки:

- `local_run/update_requirements.py` – обновляет `requirements.txt` (и
  при необходимости `bad_example/requirements.txt`) до последних версий
  пакетов.

  **Примеры использования:**

  ```powershell
  # Update main requirements.txt in place
  python local_run\update_requirements.py

  # Dry‑run: show what would change, do not modify files
  python local_run\update_requirements.py --dry-run

  # Update both top‑level and bad_example requirements
  python local_run\update_requirements.py --all
  ```

- Другие скрипты в `local_run/` (`sandbox*.py`, `quick_swap.py` и т.д.)
  ориентированы на наследуемый торговый код и эксперименты.

> 📝 **TODO:** задокументировать каждый скрипт из `local_run/*` кратким описанием,
> когда их ответственность для нового прототипа будет зафиксирована.

---

## 🔧 Environment Variables and Configuration

Новый прототип использует **централизованный конфиг** `AppConfig` в
`src/config/config.py` и функцию `load_config()`.

- `main.py` получает символ пары из CLI (`python main.py BTC/USDT`) и
  передаёт его в `run_realtime_trading.run()`.
- `load_config()` заполняет `AppConfig` значениями по умолчанию и
  переопределяет их из переменных окружения.
- Список торговых пар **не управляется через env**: он задаётся через
  `AppConfig` и репозиторий `CurrencyPair`, а в долгосрочной перспективе —
  из БД.

### Поддерживаемые переменные окружения

Сейчас учитываются только базовые настройки конвейера (см. `.env.example`):

- `APP_ENV` — окружение (`local`, `dev`, `prod` и т.п.).
- `MAX_TICKS` — максимальное число тиков за запуск.
- `TICK_SLEEP_SEC` — пауза между тиками.
- `INDICATOR_FAST_INTERVAL` — период пересчёта fast‑индикаторов.
- `INDICATOR_MEDIUM_INTERVAL` — период пересчёта medium‑индикаторов.
- `INDICATOR_HEAVY_INTERVAL` — период пересчёта heavy‑индикаторов.

Env‑переменная `SYMBOLS` **намеренно не используется**.

Наследуемый проект (`bad_example`) уже использует `.env` + JSON‑конфиг через
`python-dotenv` и загрузчик конфигурации
(`bad_example/src/config/config_loader.py`).

> 📝 **TODO:** по мере добавления реальной интеграции с биржей и персистентным
> хранилищем задокументировать дополнительные переменные окружения (ключи API,
> лимиты по риску и т.п.). Список торговых пар при этом по‑прежнему остаётся
> частью доменной модели (`CurrencyPair` + репозиторий), а не env.

---

## 🧪 Tests

Текущий прототип содержит минимальный демонстрационный каркас тестов в каталоге
`tests/`.

### ▶️ Запуск тестов

```powershell
# Все юнит-тесты
pytest tests\ -v

# Только тесты бэктеста (26 тестов: OhlcvCache, HistoricalTickSource, FillSimulator, MetricsCollector, BacktestConfig)
pytest tests\test_backtest.py -v

# Конкретный модуль
pytest tests\test_orchestrator.py -q
```

> ℹ️ Интеграционные тесты в `tests/integration/` требуют запущенного PostgreSQL.
> Запустить только юнит-тесты без БД:
> ```powershell
> pytest tests\ -v --ignore=tests\integration --ignore=tests\test_postgresql_connection.py
> ```

---

## 📂 Project Structure

Упрощённый обзор структуры (новый прототип + наследуемый reference):

```text
algorithmic_trading/
├── main.py                        # Точка входа: реалтайм-торговля (одна пара)
├── backtest.py                    # Точка входа: офлайн-бэктест на OHLCV
├── requirements.txt               # Зависимости (Python 3.12)
├── LICENSE
├── src/
│   ├── config/                    # AppConfig, load_config()
│   ├── domain/
│   │   ├── entities/              # Order, Trade, Deal, CurrencyPair (dataclass)
│   │   ├── interfaces/            # IExchangeConnector, IRepository, ILogger, …
│   │   └── services/
│   │       ├── indicators/        # IndicatorEngine (MACD, RSI, SMA, Bollinger)
│   │       ├── strategies/        # IndicatorSignalService (BUY/HOLD)
│   │       ├── orchestrator/      # DecisionCenter, RiskManager
│   │       └── execution/         # ExecutionService (идемпотентные ордера)
│   ├── infrastructure/
│   │   ├── connectors/            # CcxtProExchangeConnector (CCXT.pro)
│   │   ├── db/                    # SQLAlchemy models, engine/session factory
│   │   ├── repositories/          # Order/Trade/Deal/CurrencyPair репозитории
│   │   ├── cache/                 # In-memory кэш
│   │   └── logging/               # LoggerAdapter, logging_setup
│   └── application/
│       ├── backtest/              # Бэктест: config, tick_source, fill_sim, metrics
│       ├── use_cases/             # run_realtime_trading, run_backtest
│       ├── workers/               # Фоновые воркеры (order_sync, persistence)
│       └── services/              # TickPipelineService, state_snapshot
├── tests/
│   ├── test_backtest.py           # 26 юнит-тестов бэктеста
│   ├── test_orchestrator.py
│   ├── test_indicators.py
│   └── integration/               # Требуют PostgreSQL
├── data/
│   └── ohlcv_cache/               # Кэш OHLCV-свечей (.gitignore)
├── local_run/                     # Вспомогательные скрипты
├── bad_example_old_proj/          # Референсная реализация (только справка)
└── doc/                           # Технические заметки и планы
```

Подробное описание структуры наследуемой системы см. в
`bad_example/docs/architecture/FILE_STRUCTURE.md`.

---

## 📄 License

Этот проект распространяется под **MIT License**. Полный текст лицензии см. в
файле [LICENSE](LICENSE).

> Copyright (c) 2025

---

## ⚠️ Disclaimer

Этот репозиторий — **экспериментальный прототип**, предназначенный только для
обучающих и архитектурных целей. Он **не предназначен для реальной торговли с
реальными деньгами**.

- ❌ Не даётся никаких гарантий корректности, устойчивости или прибыльности.
- ⚠️ Используйте на свой страх и риск.
- 🧪 Всегда проводите тщательное тестирование на симулированных данных и/или в
  sandbox‑окружениях бирж.
- 💼 Перед вводом любой торговой системы в эксплуатацию консультируйтесь с
  квалифицированными финансовыми специалистами.

Используя это программное обеспечение, вы соглашаетесь с тем, что авторы и
контрибьюторы **не несут ответственности** за любой ущерб или убытки, вызванные
его использованием.
