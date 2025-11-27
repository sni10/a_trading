from __future__ import annotations

"""Контракт использования симулятора стакана.

Тесты здесь фиксируют важное архитектурное требование:

* ``update_orderflow_from_tick`` может вызываться **только** в демо‑сценарии
  ``run_demo_offline``;
* боевой async‑сценарий ``run_realtime_from_exchange`` не должен ссылаться
  на симулятор стакана ни напрямую, ни через импорт на уровне модуля.

Это простая статическая проверка: если в будущем кто‑то добавит вызов
симулятора в боевой путь, тест должен упасть уже на этапе импорта.
"""

import inspect

from src.application.use_cases import run_realtime_trading


def test_update_orderflow_not_imported_in_module_scope() -> None:
    """Модульный scope не содержит прямого импорта симулятора стакана.

    Важно, чтобы ``update_orderflow_from_tick`` не был доступен в модуле
    ``run_realtime_trading`` как глобальный символ. Тогда даже случайный
    вызов в ``run_realtime_from_exchange`` станет сразу заметен.
    """

    # Симулятор не должен быть доступен как глобальный атрибут модуля.
    assert not hasattr(run_realtime_trading, "update_orderflow_from_tick")


def test_run_realtime_from_exchange_source_does_not_reference_simulator() -> None:
    """В исходном коде async‑функции нет ссылок на симулятор стакана.

    Мы проверяем текст исходника ``run_realtime_from_exchange`` на
    отсутствие подстроки ``update_orderflow_from_tick``. Этого достаточно,
    чтобы зафиксировать отсутствие прямого вызова или импорта внутри
    функции.
    """

    source = inspect.getsource(run_realtime_trading.run_realtime_from_exchange)
    assert "update_orderflow_from_tick" not in source

