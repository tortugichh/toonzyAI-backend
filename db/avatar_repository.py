from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, Text, func, Boolean, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import select, update
from uuid import uuid4, UUID
from typing import Optional, List
import os
import enum
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import Depends

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Single async engine with tuned pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    future=True
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async_session = AsyncSessionLocal

Base = declarative_base()

class AnimationStatus(enum.Enum):
    """Статусы для анимационных проектов и сегментов."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ASSEMBLING = "assembling"

class StoryStatus(enum.Enum):
    """Статусы для историй."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = mapped_column(String(50), unique=True, nullable=False, index=True)
    email = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password = mapped_column(String(255), nullable=False)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    is_verified = mapped_column(Boolean, default=False, nullable=False)
    is_admin = mapped_column(Boolean, default=False, nullable=False)
    verification_token = mapped_column(String(255), nullable=True)
    verification_token_expires = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token = mapped_column(String(255), nullable=True)
    password_reset_token_expires = mapped_column(DateTime(timezone=True), nullable=True)
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
    progress = mapped_column(Integer, default=0, nullable=False)
    moderation_flags = mapped_column(Text, nullable=True)  # comma-separated

class Story(Base):
    """Модель для хранения созданных историй."""
    __tablename__ = "stories"
    
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Мета-информация истории
    title = mapped_column(String(255), nullable=True)
    prompt = mapped_column(Text, nullable=True)
    genre = mapped_column(String(100), nullable=True)
    style = mapped_column(String(100), nullable=True)
    theme = mapped_column(String(255), nullable=True)
    book_style = mapped_column(String(100), nullable=True)
    wishes = mapped_column(Text, nullable=True)
    
    # ID Celery задачи
    task_id = mapped_column(String(255), nullable=False, unique=True)
    
    # Статус генерации
    status = mapped_column(Enum(StoryStatus), default=StoryStatus.PENDING, nullable=False)
    
    # Результат генерации (JSON)
    story_data = mapped_column(JSON, nullable=True)  # Полный результат от агентов
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")

class AnimationProject(Base):
    """Проект анимации - контейнер для серии видео-сегментов."""
    __tablename__ = "animation_projects"
    
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_avatar_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("avatars.id"), nullable=False)
    
    name = mapped_column(String(255), nullable=False)  # Название проекта
    total_segments = mapped_column(Integer, nullable=False)
    animation_prompt = mapped_column(Text, nullable=True)  # Сделаем опциональным
    status = mapped_column(Enum(AnimationStatus), default=AnimationStatus.PENDING, nullable=False)
    final_video_url = mapped_column(String, nullable=True)
    animation_type = mapped_column(String(32), nullable=False, default="independent")  # Новый тип
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    segments = relationship("AnimationSegment", back_populates="project", cascade="all, delete-orphan")
    avatar = relationship("Avatar")  # Добавим связь с аватаром

class AnimationSegment(Base):
    """Отдельный видео-сегмент в анимационном проекте."""
    __tablename__ = "animation_segments"
    
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    animation_project_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("animation_projects.id"), nullable=False)
    
    segment_number = mapped_column(Integer, nullable=False)
    status = mapped_column(Enum(AnimationStatus), default=AnimationStatus.PENDING, nullable=False)
    progress = mapped_column(Integer, default=0, nullable=False)
    
    # Индивидуальный промпт для каждого сегмента - ПОЛЬЗОВАТЕЛЬ КОНТРОЛИРУЕТ!
    segment_prompt = mapped_column(Text, nullable=True)  # Промпт для этого конкретного сегмента
    
    start_frame_url = mapped_column(String, nullable=False)  # URL картинки-основы для генерации
    generated_video_url = mapped_column(String, nullable=True)  # URL сгенерированного видео-клипа
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("AnimationProject", back_populates="segments")

class PendingRegistration(Base):
    __tablename__ = "pending_registrations"
    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = mapped_column(String(50), unique=True, nullable=False, index=True)
    email = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password = mapped_column(String(255), nullable=False)
    verification_token = mapped_column(String(255), nullable=False, unique=True, index=True)
    verification_token_expires = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

async def insert_avatar(avatar_id: UUID, user_id: UUID, prompt: str, image_data: bytes, status: str, moderation_flags: Optional[List[str]] = None) -> UUID:
    """Вставляет новый аватар в базу данных."""
    try:
        async with async_session() as session:
            avatar = Avatar(
                id=avatar_id,
                user_id=user_id,
                prompt=prompt,
                image_data=image_data,
                status=status,
                moderation_flags=','.join(moderation_flags) if moderation_flags else None
            )
            session.add(avatar)
            await session.commit()
            return avatar_id
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

async def update_avatar_progress(avatar_id: UUID, progress: int):
    """Обновляет поле progress аватара."""
    try:
        async with async_session() as session:
            stmt = update(Avatar).where(Avatar.id == avatar_id).values(progress=progress)
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        print(f"Error updating avatar progress: {e}")
        raise

async def update_segment_progress(segment_id: UUID, progress: int):
    """Обновляет progress у сегмента."""
    try:
        async with async_session() as session:
            stmt = update(AnimationSegment).where(AnimationSegment.id == segment_id).values(progress=progress)
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        print(f"Error updating segment progress: {e}")
        raise

async def get_db() -> AsyncSession:
    """Dependency that provides a reusable async DB session."""
    async with AsyncSessionLocal() as session:
        yield session