from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class AvatarCreate(BaseModel):
    prompt: str
    user_id: UUID

class AvatarResponse(BaseModel):
    id: UUID
    user_id: UUID
    prompt: str
    image_data: str  # base64 string
    created_at: datetime
    status: str
    moderation_flags: Optional[List[str]] = None 