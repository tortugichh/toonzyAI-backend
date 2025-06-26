from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, Text, func, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import select, update
from uuid import uuid4, UUID
from typing import Optional, List
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import Depends

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

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

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = mapped_column(String(50), unique=True, nullable=False, index=True)
    email = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password = mapped_column(String(255), nullable=False)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    is_verified = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Avatar(Base):
    __tablename__ = "avatars"
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    prompt = mapped_column(Text, nullable=False)
    image_data = mapped_column(LargeBinary, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    status = mapped_column(String, nullable=False)
    moderation_flags = mapped_column(Text, nullable=True)  # comma-separated

async def insert_avatar(avatar_id: UUID, user_id: UUID, prompt: str, image_data: bytes, status: str, moderation_flags: Optional[List[str]] = None, db: AsyncSession = Depends(get_db)) -> UUID:
    """Вставляет новый аватар в базу данных."""
    avatar = Avatar(
        id=avatar_id,
        user_id=user_id,
        prompt=prompt,
        image_data=image_data,
        status=status,
        moderation_flags=','.join(moderation_flags) if moderation_flags else None
    )
    db.add(avatar)
    await db.commit()
    await db.refresh
    # Возвращаем ID напрямую, не используя refresh
    return avatar_id

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
            stmt = update(Avatar).where(Avatar.id == avatar_id).values(status=status)
            if image_data:
                stmt = stmt.values(image_data=image_data)
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        print(f"Error updating avatar status: {e}")
        raise

async def count_avatars() -> int:
    """Возвращает количество аватаров в базе данных."""
    try:
        async with async_session() as session:
            result = await session.execute(select(func.count(Avatar.id)))
            count = result.scalar()
            return count or 0
    except Exception as e:
        print(f"Error counting avatars: {e}")
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