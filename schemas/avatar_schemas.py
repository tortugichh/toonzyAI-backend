from pydantic import BaseModel

class AvatarCreateRequest(BaseModel):
    prompt: str

class AvatarResponse(BaseModel):
    avatar_id: str
    image_url: str 