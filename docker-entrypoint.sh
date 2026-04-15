#!/bin/bash
set -e

# ============================================================================
# docker-entrypoint.sh
# Применение миграций Alembic при старте контейнера.
#
# Логика:
#   1. Ждём готовности PostgreSQL (pg_isready)
#   2. alembic upgrade head (идемпотентно — безопасно при каждом старте)
#   3. Запускаем основную команду (CMD)
#
# При удалении Docker volume БД пересоздаётся с нуля:
#   docker compose down -v && docker compose up --build
# ============================================================================

DB_HOST="${POSTGRES_HOST:-postgres-atr}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"

# ---------- ожидание готовности PostgreSQL ----------
echo "⏳ Ожидание готовности PostgreSQL ($DB_HOST:$DB_PORT)..."
for i in $(seq 1 30); do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q 2>/dev/null; then
        echo "✅ PostgreSQL готов"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "❌ PostgreSQL не ответил за 30 секунд, выходим"
        exit 1
    fi
    sleep 1
done

# ---------- применение миграций ----------
echo "📥 Применяю миграции Alembic..."
alembic upgrade head
echo "✅ Миграции применены"

unset PGPASSWORD

# ---------- запуск основной команды ----------
echo "🚀 Запуск: $*"
exec "$@"
