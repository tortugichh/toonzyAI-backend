from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func, select, update
from uuid import uuid4, UUID
from typing import Optional, List
import os
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True, future=True)
session_local = sessionmaker(bind=engine, expire_on_commit=False)
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

def insert_avatar(user_id: UUID, prompt: str, image_data: bytes, status: str, moderation_flags: Optional[List[str]] = None) -> UUID:
    with session_local() as session:
        avatar = Avatar(
            user_id=user_id,
            prompt=prompt,
            image_data=image_data,
            status=status,
            moderation_flags=','.join(moderation_flags) if moderation_flags else None
        )
        session.add(avatar)
        session.commit()
        return avatar.id

def get_avatar_by_id(avatar_id: UUID) -> Optional[Avatar]:
    with session_local() as session:
        result = session.execute(select(Avatar).where(Avatar.id == avatar_id))
        avatar = result.scalar_one_or_none()
        return avatar

def update_avatar_status(avatar_id: UUID, status: str, image_data: Optional[bytes] = None):
    with session_local() as session:
        stmt = update(Avatar).where(Avatar.id == avatar_id).values(status=status)
        if image_data:
            stmt = stmt.values(image_data=image_data)
        session.execute(stmt)
        session.commit()