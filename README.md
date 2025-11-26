# Algorithmic Trading System – Prototype

> WARNING: **Prototype only. Not suitable for real-money trading.**

Этот репозиторий содержит **облегчённый прототип** событийной системы
алгоритмической торговли для криптобирж. Основной фокус кода —
**архитектура и чистый конвейер обработки тиков**, а не Production‑уровень
исполнения.

Прототип реализует упрощённый тиковый конвейер:

```text
BOOT → LOAD → WARMUP → LOOP
    ↓
TICK → FEEDS → IND → CTX → STRAT → ORCH → EXEC → STATE
```

Ключевая идея: каждый тик рыночных данных проходит через чётко выделенные
стадии — от генерации до расчёта индикаторов, оценки стратегий, оркестрации и
"исполнения" — с единообразным логированием на каждом шаге.

**Текущее состояние:** экспериментальный прототип для локальных запусков и
архитектурных экспериментов. Целевая архитектура, к которой движется
прототип, описана в `doc/designing/GIUDELINE.md` и `bad_example/docs/*`.

---

## Stack and Entry Points

- **Language:** Python 3.12 (целевая версия для нового прототипа)
- **Main libraries:**
  - `logging` (standard library) – структурированное логирование
  - Зависимости проекта перечислены в `requirements.txt` (см. ниже). Многие из
    них используются в основном наследуемым проектом `bad_example` или будут
    задействованы на более поздних этапах развития прототипа.
- **Package manager:** `pip` (через `requirements.txt`)

**Entry points:**

- Верхнеуровневый запуск прототипа (текущий репозиторий):
  - `python main.py` →
    импортирует `src.application.use_cases.run_realtime_trading.run` и
    запускает упрощённый тиковый конвейер.
- Наследуемая полная система (только как референс):
  - `cd bad_example`
  - `python main.py` (подробности см. в `bad_example/README.md`).

> Note: В **новом прототипе пока нет реальной интеграции с CCXT / WebSocket**.
> Все тики генерируются локальным симулятором.

---

## High‑Level Architecture (Prototype)

Новый прототип следует упрощённому варианту архитектуры,
описанной в `doc/designing/GIUDELINE.md` и
`bad_example/docs/architecture/FILE_STRUCTURE.md`.

### Tick Pipeline
Система следует последовательной архитектуре конвейера:

```
BOOT → LOAD → WARMUP → LOOP
    ↓
TICK → FEEDS → IND → CTX → STRAT → ORCH → EXEC → STATE
```

#### Stage Overview
1. **BOOT**: Инициализация системы и конфигурации.
2. **LOAD**: Загрузка торговых пар, ордеров и позиций из хранилища.
3. **WARMUP**: Предварительное заполнение индикаторов и стаканов из исторических данных.
4. **TICK**: Получение тика рыночных данных.
5. **FEEDS**: Обновление рыночного кеша новыми данными.
6. **IND**: Вычисление технических индикаторов.
7. **CTX**: Построение комплексного торгового контекста.
8. **STRAT**: Оценка торговых стратегий.
9. **ORCH**: Оркестрация и принятие решений.
10. **EXEC**: Исполнение торговых решений.
11. **STATE**: Обновление метрик системы и состояния.

### Main Components (New Prototype)

#### Data and Context

- `src.domain.services.market_data.tick_source.generate_ticks` – простой
  генератор тиков, имитирующий обновление цен для списка символов.
- `src.domain.services.context.state` – контекст в памяти с текущими
  рыночными данными, позициями и базовыми метриками.
- `src.infrastructure.logging.logging_setup` – общий модуль настройки логов и
  хелпер `log_stage()`, используемый по всему конвейеру.

#### Indicator Engine (placeholder)

- `src.domain.services.indicators.indicator_engine.compute_indicators` –
  фиктивные технические индикаторы (например, `sma = price`, `rsi = 50.0`) с
  корректным интерфейсом и логированием; выступают заглушкой для будущего
  `IndicatorEngine`.

#### Strategies (demo)

- `src.domain.services.strategies.strategy_hub.evaluate_strategies` – формирует
  список intents на основе простой демонстрационной логики (например,
  решений, привязанных к `tick_id`).

#### Orchestrator and Execution (demo)

- `src.domain.services.orchestrator.orchestrator.decide` – наивный
  оркестратор, который сейчас выбирает первый intent с `action != "HOLD"`.
- `src.domain.services.execution.execution_service.execute` – заглушка
  Execution‑сервиса, которая только логирует, что было бы отправлено на биржу.

---

## Features and Limitations

### Implemented

- Событийный **тиковый конвейер** с явными стадиями (`TICK`, `IND`, `STRAT`,
  `ORCH`, `EXEC`, `STATE`).
- **Структурированное логирование** с единым хелпером `log_stage()` и
  ротируемыми лог-файлами в `logs/`.
- **Контекст/состояние в памяти**, обновляемое на каждом тике.
- **Демо‑индикаторы и стратегии**, достаточные для наблюдения работы
  конвейера.

### Not Implemented / Prototype‑Only

- Отсутствует реальная **интеграция с биржей** (в новом конвейере пока не
  используется CCXT.pro).
- Нет полноценного **risk management**, учёта портфеля и продвинутых
  стратегий.
- Нет **database** или долговременного хранения — всё состояние находится в
  памяти.
- Нет Production‑grade обработки ошибок, мониторинга и backtesting.

За подробностями о долгосрочном направлении см. `doc/` и `bad_example/docs/`.

---

## Requirements

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

> TODO: явно задокументировать минимальный набор зависимостей, необходимый
> именно для нового конвейера `src/*`, когда он начнёт использовать CCXT,
> TA‑Lib и другие библиотеки в Production‑подобных сценариях.

---

## Setup and Running

Из корня репозитория (`algorithmic_trading`):

1. **Создайте и активируйте виртуальное окружение (рекомендуется)**

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Установите зависимости** (для разработки и тестов)

   ```powershell
   pip install -r requirements.txt
   ```

3. **Запустите тиковый конвейер прототипа**

   ```powershell
   python main.py
   ```

   Эта команда вызывает `src.application.use_cases.run_realtime_trading.run()`
   с параметрами по умолчанию:

   - `max_ticks=10`
   - `symbols=["BTC/USDT", "ETH/USDT"]`
   - `tick_sleep_sec=0.2`

   В консоли и в файле `logs/prototype.log` будут писаться структурированные
   логи.

4. **(опционально) Запустите наследуемую reference‑реализацию**

   ```powershell
   cd bad_example
   python main.py
   ```

   Это запустит более старую, более сложную архитектуру, описанную в
   `bad_example/docs/architecture/PROJECT_OVERVIEW.md`.

---

## Scripts and Utilities

### Local helper scripts (`local_run/`)

Эти скрипты предназначены для экспериментов и локальных утилит; они **не**
являются частью основного API конвейера, но могут быть полезны в процессе
разработки:

- `local_run/update_requirements.py` – обновляет `requirements.txt` (и
  при необходимости `bad_example/requirements.txt`) до последних версий
  пакетов.

  Примеры использования:

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

> TODO: задокументировать каждый скрипт из `local_run/*` кратким описанием,
> когда их ответственность для нового прототипа будет зафиксирована.

---

## Environment Variables and Configuration

**Новый прототип** сейчас использует **встроенную конфигурацию по умолчанию**,
создаваемую в `src.application.use_cases.run_realtime_trading.run()`, и пока
**не имеет централизованной загрузки конфигурации**.

- Пример dict‑конфига в коде:

  ```python
  config = {
      "symbols": ["BTC/USDT", "ETH/USDT"],
      "tick_sleep_sec": 0.2,
      "max_ticks": 10,
  }
  ```

Наследуемый проект (`bad_example`) уже использует `.env` + JSON‑конфиг через
`python-dotenv` и загрузчик конфигурации
(`bad_example/src/config/config_loader.py`).

**Планируемое направление (пока не реализовано для нового прототипа):**

- Вынести конфигурацию нового конвейера в отдельный модуль `config/`.
- Загружать конфигурацию из `.env` + JSON/YAML при старте.
- Рано валидировать конфиг и избегать прямого обращения к `os.getenv` из
  бизнес‑логики.

> TODO: определить и задокументировать конкретные переменные окружения для
> нового прототипа (например, ключи API биржи, список символов, лимиты по
> риску) при добавлении интеграции с биржей и персистентного хранилища.

---

## Tests

Текущий прототип содержит минимальный демонстрационный каркас тестов в каталоге
`tests/`.

- Чтобы запустить тесты для этого прототипа:

  ```powershell
  pytest tests\ -v
  ```

- Чтобы запустить тесты для наследуемого проекта:

  ```powershell
  cd bad_example
  pytest tests\ -v
  ```

На данный момент для нового конвейера нет полноценного набора юнит‑тестов —
есть только демонстрационный файл, использованный при разработке guideline.

> TODO: добавить полноценные юнит‑тесты для чистой бизнес‑логики (например,
> правила принятия решений в оркестраторе, расчёт индикаторов, выбор
> стратегий) по рекомендациям из `.junie/guidelines.md` и
> `bad_example/docs/TESTING_WITH_POSTGRESQL.md` (адаптированным для этого
> облегчённого прототипа).

---

## Project Structure

Упрощённый обзор структуры (новый прототип + наследуемый reference):

```text
algorithmic_trading/
├── main.py                        # Thin entry point: runs new tick pipeline
├── requirements.txt               # Shared dev dependencies (Python 3.12)
├── LICENSE                        # MIT license
├── src/
│   ├── application/
│   │   └── use_cases/
│   │       └── run_realtime_trading.py  # High-level scenario to run pipeline
│   ├── domain/
│   │   └── services/
│   │       ├── context/
│   │       │   └── state.py             # In-memory context and metrics
│   │       ├── execution/
│   │       │   └── execution_service.py # Placeholder execution service
│   │       ├── indicators/
│   │       │   └── indicator_engine.py  # Fake indicators, logging
│   │       ├── market_data/
│   │       │   └── tick_source.py       # Tick generator (simulator)
│   │       ├── orchestrator/
│   │       │   └── orchestrator.py      # Naïve orchestrator
│   │       └── strategies/
│   │           └── strategy_hub.py      # Demo strategies/intents
│   └── infrastructure/
│       └── logging/
│           └── logging_setup.py         # Logging configuration and helpers
├── tests/
│   └── ...                     # Demo tests for prototype (see TODO above)
├── local_run/
│   └── *.py                    # Experimental / helper scripts
├── bad_example/                # Legacy full implementation (reference only)
└── doc/                        # Design docs and technical notes
```

Подробное описание структуры наследуемой системы см. в
`bad_example/docs/architecture/FILE_STRUCTURE.md`.

---

## License

Этот проект распространяется под **MIT License**. Полный текст лицензии см. в
файле [LICENSE](LICENSE).

> Copyright (c) 2025

---

## Disclaimer

Этот репозиторий — **экспериментальный прототип**, предназначенный только для
обучающих и архитектурных целей. Он **не предназначен для реальной торговли с
реальными деньгами**.

- Не даётся никаких гарантий корректности, устойчивости или прибыльности.
- Используйте на свой страх и риск.
- Всегда проводите тщательное тестирование на симулированных данных и/или в
  sandbox‑окружениях бирж.
- Перед вводом любой торговой системы в эксплуатацию консультируйтесь с
  квалифицированными финансовыми специалистами.

Используя это программное обеспечение, вы соглашаетесь с тем, что авторы и
контрибьюторы **не несут ответственности** за любой ущерб или убытки, вызванные
его использованием.