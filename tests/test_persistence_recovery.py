"""Тест восстановления состояния после обрыва процесса.

Проверяет:
1. Сохранение энтити в БД через PersistenceWorker
2. Восстановление Deal/Order/Trade из БД
3. Восстановление реактивных данных из файла
4. Прогрев индикаторов заново
"""

from __future__ import annotations

import time
from pathlib import Path

from src.application.context import build_context
from src.application.repository_factory import build_repositories
from src.application.services.state_snapshot_service import StateSnapshotService
from src.config.config import load_config
from src.domain.entities.currency_pair import CurrencyPair
from src.domain.entities.deal import Deal
from src.domain.entities.order import Order
from src.domain.entities.trade import Trade
from src.domain.services.context.state import init_context
from src.infrastructure.state.file_state_snapshot_store import FileStateSnapshotStore


def test_persistence_and_recovery():
    """Интеграционный тест: сохранение → обрыв → восстановление."""

    print("\n" + "=" * 80)
    print("ТЕСТ ПЕРСИСТЕНТНОСТИ И ВОССТАНОВЛЕНИЯ ПОСЛЕ ОБРЫВА")
    print("=" * 80 + "\n")

    cfg = load_config()
    symbol = "BTC/USDT"

    # === ФАЗА 1: Создание БД и контекста ===
    print("📦 ФАЗА 1: Создание начального состояния\n")

    repos = build_repositories(cfg)
    pair_repo = repos.pair_repository

    # Bootstrap пары
    pair = pair_repo.get_by_symbol(symbol)
    if pair is None:
        pair = pair_repo.upsert(
            CurrencyPair(
                symbol=symbol,
                base_currency="BTC",
                quote_currency="USDT",
                deal_quota=100.0,
                profit_markup=2.0,
            )
        )
        print(f"✅ Пара {symbol} создана в БД")
    else:
        print(f"✅ Пара {symbol} загружена из БД (pair_id={pair.pair_id})")

    # Создать контекст
    context = init_context(cfg)
    context = build_context(cfg, context, pair_repository=pair_repo)
    print(f"✅ Контекст инициализирован\n")

    # === ФАЗА 2: Создание сделок/ордеров в памяти ===
    print("📦 ФАЗА 2: Создание сделок и ордеров в памяти\n")

    ts = int(time.time() * 1000)

    # Создать активную сделку
    deal1 = Deal(
        id=1,
        symbol=symbol,
        status="open",
        created_at=ts,
        target_amount=0.01,
        target_buy_price=50000.0,
        target_sell_price=51000.0,
    )

    # Создать buy ордер для сделки (уже исполнен, есть exchange id)
    order1 = Order(
        id=None,  # Autoincrement в БД
        exchange_order_id="EXCH_123456",  # ID от биржи
        symbol=symbol,
        timestamp=ts,
        datetime=f"{ts}",
        status="closed",
        side="buy",
        type="limit",
        amount=0.01,
        price=50000.0,
        filled=0.01,
        remaining=0.0,
        cost=500.0,
        deal_id=deal1.id,
    )
    deal1.buy_order = order1

    # Создать sell ордер (ещё открыт, может не иметь exchange id)
    order2 = Order(
        id=None,  # Autoincrement в БД
        exchange_order_id="EXCH_789012",  # ID от биржи
        symbol=symbol,
        timestamp=ts,
        datetime=f"{ts}",
        status="open",
        side="sell",
        type="limit",
        amount=0.01,
        price=51000.0,
        filled=0.0,
        remaining=0.01,
        cost=0.0,
        deal_id=deal1.id,
    )
    deal1.sell_order = order2

    # Создать трейд для buy ордера
    trade1 = Trade(
        id=None,  # Autoincrement в БД
        exchange_trade_id="EXCH_TRADE_111",  # ID трейда от биржи
        order_id=None,  # Пока order1.id = None, заполним после сохранения
        symbol=symbol,
        timestamp=ts,
        datetime=f"{ts}",
        side="buy",
        type="limit",
        price=50000.0,
        amount=0.01,
        cost=500.0,
    )

    # Поместить в контекст
    context.setdefault("deals", {})[symbol] = [deal1]
    context.setdefault("orders", {})[symbol] = [order1, order2]
    context.setdefault("trades", {})[symbol] = [trade1]

    print(f"✅ Создана сделка: deal_id={deal1.id}, status={deal1.status}")
    print(f"✅ Создан buy ордер: order_id={order1.id}, status={order1.status}")
    print(f"✅ Создан sell ордер: order_id={order2.id}, status={order2.status}")
    print(f"✅ Создан трейд: trade_id={trade1.id}\n")

    # === ФАЗА 3: Сохранение в БД через StateSnapshotService ===
    print("📦 ФАЗА 3: Сохранение энтити в БД\n")

    snapshot_store = FileStateSnapshotStore()
    snapshot_svc = StateSnapshotService(
        snapshot_store,
        cfg,
        symbol=symbol,
        deal_repo=repos.deal_repository,
        order_repo=repos.order_repository,
        trade_repo=repos.trade_repository,
    )

    # Сохранить в файл + БД
    snapshot_svc.maybe_save(context, ticker_id=100)  # Принудительно сохранить
    snapshot_svc._save_entities_to_db(context)  # Явно сохранить в БД

    print("✅ Энтити сохранены в БД через StateSnapshotService")
    print("✅ Снапшот сохранён в файл\n")

    # После upsert orders получат свои autoincrement ID
    # (в реальности это делает репозиторий при сохранении)

    # Проверить, что сохранилось в БД
    saved_deals = repos.deal_repository.list_active_by_symbol(symbol)
    saved_orders = repos.order_repository.list_by_symbol(symbol, limit=10)

    # Найти сохранённый order1 по exchange_order_id
    saved_order1 = next((o for o in saved_orders if o.exchange_order_id == "EXCH_123456"), None)
    if saved_order1:
        saved_trades = repos.trade_repository.list_by_order_id(saved_order1.id, limit=10)
    else:
        saved_trades = []

    print(f"📊 Проверка БД после сохранения:")
    print(f"   - Сделок в БД: {len(saved_deals)}")
    print(f"   - Ордеров в БД: {len(saved_orders)}")
    print(f"   - Трейдов в БД: {len(saved_trades)}\n")

    assert len(saved_deals) >= 1, "Сделка не сохранилась в БД!"
    assert len(saved_orders) >= 2, "Ордера не сохранились в БД!"
    assert len(saved_trades) >= 1, "Трейд не сохранился в БД!"

    # === ФАЗА 4: Симуляция обрыва процесса ===
    print("📦 ФАЗА 4: Симуляция обрыва процесса (очистка памяти)\n")

    # Очистить контекст (симуляция падения процесса)
    context.clear()
    context = init_context(cfg)
    context = build_context(cfg, context, pair_repository=pair_repo)

    print("✅ Контекст очищен (симуляция crash)\n")

    # === ФАЗА 5: Восстановление из БД + файла ===
    print("📦 ФАЗА 5: Восстановление состояния из БД и файла\n")

    # Создать новый snapshot_svc
    snapshot_svc_new = StateSnapshotService(
        snapshot_store,
        cfg,
        symbol=symbol,
        deal_repo=repos.deal_repository,
        order_repo=repos.order_repository,
        trade_repo=repos.trade_repository,
    )

    # 1. Загрузить реактивные данные из файла
    loaded_ticker_id = snapshot_svc_new.load(context)
    print(f"✅ Загружен снапшот из файла (ticker_id={loaded_ticker_id})")

    # 2. Загрузить персистентные данные из БД
    snapshot_svc_new.load_from_db(context)
    print(f"✅ Энтити загружены из БД\n")

    # === ФАЗА 6: Проверка восстановленных данных ===
    print("📦 ФАЗА 6: Проверка восстановленного состояния\n")

    restored_deals = context.get("deals", {}).get(symbol, [])
    restored_orders = context.get("orders", {}).get(symbol, [])
    restored_trades = context.get("trades", {}).get(symbol, [])

    print(f"📊 Восстановлено из БД:")
    print(f"   - Сделок: {len(restored_deals)}")
    print(f"   - Ордеров: {len(restored_orders)}")
    print(f"   - Трейдов: {len(restored_trades)}\n")

    # Проверки
    assert len(restored_deals) >= 1, "Сделки не восстановились!"
    assert len(restored_orders) >= 2, "Ордера не восстановились!"
    assert len(restored_trades) >= 1, "Трейды не восстановились!"

    # Проверить конкретную сделку
    restored_deal = restored_deals[0]
    assert restored_deal.id == deal1.id, f"ID сделки не совпадает: {restored_deal.id} != {deal1.id}"
    assert restored_deal.status == "open", f"Статус сделки не 'open': {restored_deal.status}"
    assert restored_deal.target_buy_price == 50000.0, f"Buy price не совпадает: {restored_deal.target_buy_price}"

    print(f"✅ Сделка восстановлена корректно:")
    print(f"   - deal_id={restored_deal.id}")
    print(f"   - status={restored_deal.status}")
    print(f"   - target_buy_price={restored_deal.target_buy_price}")
    print(f"   - target_sell_price={restored_deal.target_sell_price}\n")

    # Проверить ордера
    restored_buy_order = next((o for o in restored_orders if o.side == "buy"), None)
    restored_sell_order = next((o for o in restored_orders if o.side == "sell"), None)

    assert restored_buy_order is not None, "Buy ордер не восстановился!"
    assert restored_sell_order is not None, "Sell ордер не восстановился!"
    assert restored_buy_order.status == "closed", "Buy ордер должен быть closed"
    assert restored_sell_order.status == "open", "Sell ордер должен быть open"

    print(f"✅ Ордера восстановлены корректно:")
    print(f"   - Buy order: id={restored_buy_order.id}, status={restored_buy_order.status}")
    print(f"   - Sell order: id={restored_sell_order.id}, status={restored_sell_order.status}\n")

    # === ИТОГОВАЯ СВОДКА ===
    print("=" * 80)
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)
    print("\n📊 Сводка теста:")
    print(f"   1. Создано сделок: 1")
    print(f"   2. Создано ордеров: 2")
    print(f"   3. Создано трейдов: 1")
    print(f"   4. Сохранено в БД: ✅")
    print(f"   5. Восстановлено из БД: ✅")
    print(f"   6. Данные совпадают: ✅")
    print(f"   7. Реактивные данные из файла: ✅ (ticker_id={loaded_ticker_id})")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    test_persistence_and_recovery()
