from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func, select, update
from uuid import uuid4, UUID
from typing import Optional, List
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
# Используем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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

async def insert_avatar(user_id: UUID, prompt: str, image_data: bytes, status: str, moderation_flags: Optional[List[str]] = None) -> UUID:
    async with async_session() as session:
        avatar = Avatar(
            user_id=user_id,
            prompt=prompt,
            image_data=image_data,
            status=status,
            moderation_flags=','.join(moderation_flags) if moderation_flags else None
        )
        session.add(avatar)
        await session.commit()
        return avatar.id

async def get_avatar_by_id(avatar_id: UUID) -> Optional[Avatar]:
    async with async_session() as session:
        result = await session.execute(select(Avatar).where(Avatar.id == avatar_id))
        avatar = result.scalar_one_or_none()
        return avatar

async def update_avatar_status(avatar_id: UUID, status: str, image_data: Optional[bytes] = None):
    async with async_session() as session:
        stmt = update(Avatar).where(Avatar.id == avatar_id).values(status=status)
        if image_data:
            stmt = stmt.values(image_data=image_data)
        await session.execute(stmt)
        await session.commit()