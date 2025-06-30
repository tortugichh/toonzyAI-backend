from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from db.avatar_repository import AnimationStatus


class AnimationProjectCreate(BaseModel):
    """Схема для создания проекта анимации."""
    source_avatar_id: UUID = Field(..., description="ID исходного аватара для анимации")
    total_segments: int = Field(..., gt=0, le=10, description="Количество видео-сегментов (1-10)")
    animation_prompt: str = Field(..., min_length=10, max_length=500, description="Промпт для анимации")


class AnimationSegmentResponse(BaseModel):
    """Схема ответа для видео-сегмента."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    segment_number: int
    status: AnimationStatus
    start_frame_url: str
    generated_video_url: Optional[str] = None
    # URL для просмотра видео сегмента через API
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AnimationProjectResponse(BaseModel):
    """Схема ответа для проекта анимации."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    source_avatar_id: UUID
    total_segments: int
    animation_prompt: str
    status: AnimationStatus
    final_video_url: Optional[str] = None
    # URL для просмотра финального видео через API
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    segments: List[AnimationSegmentResponse] = []


class AnimationProjectListResponse(BaseModel):
    """Схема для списка проектов анимации пользователя."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    source_avatar_id: UUID
    animation_prompt: str
    status: AnimationStatus
    total_segments: int
    final_video_url: Optional[str] = None
    # URL для просмотра финального видео через API
    video_url: Optional[str] = None
    created_at: datetime


class GenerateSegmentRequest(BaseModel):
    """Схема для запроса генерации конкретного сегмента."""
    segment_number: int = Field(..., gt=0, description="Номер сегмента для генерации")


class AssembleVideoResponse(BaseModel):
    """Схема ответа при запуске сборки финального видео."""
    message: str
    project_id: UUID
    status: str = "assembling" 