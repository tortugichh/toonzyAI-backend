from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AvatarCreateRequest(BaseModel):
    prompt: str
 
class AvatarResponse(BaseModel):
    avatar_id: UUID
    image_url: str
    prompt: str
    status: str = "completed"
    user_id: UUID
    created_at: datetime

class AvatarListResponse(BaseModel):
    avatars: list[AvatarResponse]
    total: int
    page: int
    per_page: int 