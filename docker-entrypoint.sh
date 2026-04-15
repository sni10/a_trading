#!/bin/bash
set -e

# ============================================================================
# docker-entrypoint.sh
# Автоматическое применение SQL-миграций при старте контейнера.
#
# Логика:
#   1. Ждём готовности PostgreSQL (pg_isready)
#   2. Проверяем, существует ли схема "main" и таблицы в ней
#   3. Если схема пуста или отсутствует — применяем все миграции по порядку
#   4. Запускаем основную команду (CMD)
# ============================================================================

MIGRATIONS_DIR="/app/src/infrastructure/db/migrations"

# ---------- переменные подключения ----------
DB_HOST="${POSTGRES_HOST:-postgres-atr}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-atrading}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_SCHEMA="${DB_SCHEMA:-main}"
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

# ---------- проверка наличия схемы и таблиц ----------
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '${DB_SCHEMA}';" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -gt 0 ] 2>/dev/null; then
    echo "✅ Схема '${DB_SCHEMA}' содержит ${TABLE_COUNT} таблиц — миграции не требуются"
else
    echo "📥 Схема '${DB_SCHEMA}' пуста или не существует — применяем миграции..."

    # Применяем миграции в алфавитном порядке (001_, 002_, ...)
    for sql_file in "$MIGRATIONS_DIR"/[0-9]*.sql; do
        if [ -f "$sql_file" ]; then
            filename=$(basename "$sql_file")
            echo "   ▶ Применяю ${filename}..."
            if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                -v ON_ERROR_STOP=1 -f "$sql_file" --quiet --no-psqlrc 2>&1; then
                echo "   ❌ Ошибка при применении ${filename}"
                exit 1
            fi
            echo "   ✅ ${filename} применена"
        fi
    done

    echo "✅ Все миграции применены успешно"
fi

unset PGPASSWORD

# ---------- запуск основной команды ----------
echo "🚀 Запуск: $*"
exec "$@"
