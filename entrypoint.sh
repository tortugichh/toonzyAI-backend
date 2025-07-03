#!/usr/bin/env bash
set -e

# If the alembic_version table is empty, mark the database as already having all baseline migrations applied.
if ! alembic current >/dev/null 2>&1; then
  echo "[entrypoint] alembic_version table is empty – stamping to baseline revision d2d2a701d434"
  alembic stamp d2d2a701d434
fi

# Apply any migrations that came after the baseline (idempotent if already applied)
 echo "[entrypoint] Running alembic upgrade head"
 almbk_err=0
 if alembic upgrade head; then
   echo "[entrypoint] Migrations up-to-date"
 else
   almbk_err=$?
   echo "[entrypoint] ERROR: alembic upgrade failed with exit code $almbk_err" >&2
   exit $almbk_err
 fi

# Launch the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port 8000 