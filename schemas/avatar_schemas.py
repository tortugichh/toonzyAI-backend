from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class AvatarCreateRequest(BaseModel):
    prompt: str
    user_id: Optional[UUID] = None  # Опциональный, если нет аутентификации
 
class AvatarResponse(BaseModel):
    avatar_id: UUID
    image_url: str
    prompt: str
    status: str = "completed"
    user_id: Optional[UUID] = None 