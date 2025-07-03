from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from utils.gcs_client import get_public_url

class AvatarCreateRequest(BaseModel):
    prompt: str
 
class AvatarResponse(BaseModel):
    avatar_id: UUID
    image_url: str
    prompt: str
    status: str = "completed"
    user_id: UUID
    created_at: datetime
    
    @field_validator('image_url', mode='before')
    @classmethod
    def convert_gcs_url(cls, v):
        """Конвертирует gs:// URLs в публичные HTTPS URLs для браузера."""
        if v and isinstance(v, str) and v.startswith('gs://'):
            return get_public_url(v)
        return v

class AvatarListResponse(BaseModel):
    avatars: list[AvatarResponse]
    total: int
    page: int
    per_page: int 

class AvatarStatusResponse(BaseModel):
    avatar_id: UUID
    status: str
    progress: int 