from pydantic import BaseModel
from typing import List

class StoryboardCreateRequest(BaseModel):
    avatar_id: str
    prompt: str
    num_frames: int = 3

class StoryboardFrame(BaseModel):
    frame_id: str
    image_url: str

class StoryboardResponse(BaseModel):
    frames: List[StoryboardFrame] 