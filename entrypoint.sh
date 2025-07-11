#!/usr/bin/env bash
set -e

# Wait until Postgres is accepting TCP connections
until nc -z db 5432; do
  echo "[entrypoint] Waiting for Postgres to be available at db:5432..."
  sleep 1
done

# Run migrations from scratch (idempotent): если таблицы уже существуют – Alembic пропустит шаги.
 echo "[entrypoint] Running alembic upgrade head"
 almbk_err=0
 if alembic upgrade head; then
   echo "[entrypoint] Migrations up-to-date"
 else
   almbk_err=$?
   echo "[entrypoint] ERROR: alembic upgrade failed with exit code $almbk_err" >&2
   exit $almbk_err
 fi

# Запускаем FastAPI через Gunicorn
exec gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000 --log-level info 