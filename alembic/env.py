from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys
import asyncio
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Добавляем корень проекта в путь импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Получаем объект конфигурации Alembic
config = context.config

# Подставляем переменную DATABASE_URL из .env в конфиг Alembic
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Настройка логгирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Импорт базы моделей
try:
    from db.avatar_repository import Base
except ImportError as e:
    print(f"Warning: Could not import Base from db.avatar_repository: {e}")
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()

# Метаданные для генерации миграций
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

# Определяем, в каком режиме запущен alembic
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
