from pydantic import BaseModel
from typing import Optional

class AvatarCreateRequest(BaseModel):
    prompt: str
 
class AvatarResponse(BaseModel):
    avatar_id: str
    image_url: str
    prompt: Optional[str] = None
    status: str = "completed" 