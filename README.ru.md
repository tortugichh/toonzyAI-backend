# ToonzyAI – Бекенд

Бекенд построен на **FastAPI** (Python 3.10), использует:
* **PostgreSQL** + `asyncpg` + `SQLAlchemy 2.x` (Async)  
* **Redis** как брокер и backend для **Celery 5**  
* **Celery** – фоновые задачи (генерация сегментов, сборка видео, multi-agent)  
* **FFmpeg** для видео-обработки  
* Хранение файлов – Google Cloud Storage (с возможностью fallback на локальный режим).

## Быстрый старт (Docker-Compose)

```bash
# 1. Скопируйте пример переменных окружения
cp .env.example .env   # прилагается

# Минимально задайте:
#  DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
#  REDIS_URL=redis://redis:6379/0
#  GCS_BUCKET=<ваш-бакет> (или оставьте пустым для локального режима)

# 2. Запуск
docker compose up -d --build

# 3. Проверка
curl http://localhost:8000/docs    # Swagger UI
```

Запустятся контейнеры: `toonzyai-db` (Postgres), `toonzyai-redis`, `toonzyai-backend` (FastAPI), `toonzyai-celery`.

## Основные директории
```
backend/
  routers/        FastAPI-роуты (auth, avatars, animations, story)
  db/             SQLAlchemy модели + helpers
  tasks/          Celery-задачи (generation, assembly, agent_tasks)
  agents/         LLM-агенты (Director, Art Director, Character, Environment)
  utils/          Утилиты (GCS, ffmpeg, vertex_ai и др.)
  middleware/     Логирование запросов
  alembic/        Миграции базы
```

## Миграции БД
```bash
# создать новую
alembic revision -m "add new table" --autogenerate

# применить
alembic upgrade head
```
`alembic.ini` уже настроен читать `DATABASE_URL`.

## Celery
Запуск воркера вне Docker:
```bash
celery -A utils.celery_app.celery_app worker -l info -Q default -c 4
```

*Задачи разбиты по модулям:*  
`tasks/generation_tasks.py`, `tasks/assembly_tasks.py`, `tasks/agent_tasks.py`.

Мониторинг: `flower` или `watch -n1 docker compose logs celery`.

## Переменные окружения (ключевые)
| Переменная            | Значение по умолчанию | Описание |
|-----------------------|-----------------------|----------|
| `DATABASE_URL`        | —                     | строка подключения PostgreSQL (asyncpg) |
| `REDIS_URL`           | `redis://redis:6379/0`| брокер Celery |
| `GCS_BUCKET`          | —                     | имя GCS-бакета для хранения видео |
| `GOOGLE_CLOUD_PROJECT`| —                     | ID проекта GCP |
| `VEO_API_KEY`         | —                     | ключ/токен к Vertex AI Veo |

Полный список — смотрите файлы `.env.example` и `utils/*_client*.py`.

## Запуск без Docker
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Postgres и Redis должны быть запущены локально
alembic upgrade head
uvicorn main:app --reload
```

## Тестирование API
Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

## Структура Multi-Agent системы
```
User Prompt -> Director Agent -> (ArtDirector, CharacterAgent, EnvironmentAgent) -> script/style/characters/environments
```
Agents описаны в `MULTI_AGENT_ARCHITECTURE.md`.

## Развёртывание в проде
* Рекомендуемый стек: **GKE** или **Render**, либо VPS + Docker Compose.  
* Настройте переменные окружения, HTTPS-проксирование (Nginx / Traefik) и резервное копирование БД. 