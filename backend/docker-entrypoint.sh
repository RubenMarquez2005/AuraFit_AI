#!/bin/sh
set -eu

DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"

echo "Esperando base de datos en ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 2
done

echo "Base de datos disponible. Iniciando backend..."
exec python -m uvicorn main:app --host 0.0.0.0 --port 8001
