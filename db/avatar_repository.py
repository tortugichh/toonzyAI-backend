from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func, select, update
from uuid import uuid4, UUID
from typing import Optional, List
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Проверяем наличие DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Используем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# ИСПРАВЛЕНИЕ: Используем async_sessionmaker вместо обычного sessionmaker
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

class Avatar(Base):
    __tablename__ = "avatars"
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    prompt = mapped_column(Text, nullable=False)
    image_data = mapped_column(LargeBinary, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    status = mapped_column(String, nullable=False)
    moderation_flags = mapped_column(Text, nullable=True)  # comma-separated

async def insert_avatar(avatar_id: UUID, user_id: UUID, prompt: str, image_data: bytes, status: str, moderation_flags: Optional[List[str]] = None) -> UUID:
    """Вставляет новый аватар в базу данных."""
    try:
        async with async_session() as session:
            # ИСПРАВЛЕНИЕ: Добавляем начало транзакции
            async with session.begin():
                avatar = Avatar(
                    id=avatar_id,
                    user_id=user_id,
                    prompt=prompt,
                    image_data=image_data,
                    status=status,
                    moderation_flags=','.join(moderation_flags) if moderation_flags else None
                )
                session.add(avatar)
                # ИСПРАВЛЕНИЕ: commit() теперь происходит автоматически при выходе из begin()
                # await session.commit() - убираем, так как используем session.begin()
                
                # Добавляем refresh для получения сгенерированных значений
                await session.refresh(avatar)
                return avatar.id
    except Exception as e:
        print(f"Error inserting avatar: {e}")
        raise

async def get_avatar_by_id(avatar_id: UUID) -> Optional[Avatar]:
    """Получает аватар по ID."""
    try:
        async with async_session() as session:
            result = await session.execute(select(Avatar).where(Avatar.id == avatar_id))
            avatar = result.scalar_one_or_none()
            return avatar
    except Exception as e:
        print(f"Error getting avatar by id: {e}")
        raise

async def update_avatar_status(avatar_id: UUID, status: str, image_data: Optional[bytes] = None):
    """Обновляет статус аватара."""
    try:
        async with async_session() as session:
            async with session.begin():
                stmt = update(Avatar).where(Avatar.id == avatar_id).values(status=status)
                if image_data:
                    stmt = stmt.values(image_data=image_data)
                await session.execute(stmt)
                # commit() происходит автоматически при выходе из begin()
    except Exception as e:
        print(f"Error updating avatar status: {e}")
        raise

# Дополнительная функция для проверки подключения к БД
async def test_database_connection():
    """Тестирует подключение к базе данных."""
    try:
        async with async_session() as session:
            result = await session.execute(select(func.now()))
            current_time = result.scalar()
            return f"Database connection successful. Current time: {current_time}"
    except Exception as e:
        return f"Database connection failed: {e}"