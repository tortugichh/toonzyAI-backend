from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from db.avatar_repository import AnimationStatus
from utils.gcs_client import get_public_url


class AnimationProjectCreate(BaseModel):
    """Схема для создания проекта анимации. Общий промпт теперь опционален."""
    name: str = Field(..., min_length=1, max_length=255, description="Название проекта")
    source_avatar_id: UUID = Field(..., description="ID исходного аватара для анимации")
    total_segments: int = Field(..., gt=0, le=5, description="Количество видео-сегментов (1-5)")
    animation_prompt: Optional[str] = Field(None, max_length=500, description="(Необязательно) Общий промпт для анимации")
    animation_type: str = Field("independent", description="Тип анимации: 'sequential' или 'independent'")





class SegmentGenerateRequest(BaseModel):
    """Схема для запуска генерации конкретного сегмента (промпт обязателен)."""
    segment_prompt: str = Field(..., min_length=10, max_length=500, description="Индивидуальный промпт для генерации этого сегмента")


class AnimationSegmentResponse(BaseModel):
    """Схема ответа для видео-сегмента."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    segment_number: int
    status: AnimationStatus
    segment_prompt: Optional[str] = None  # Индивидуальный промпт сегмента
    start_frame_url: str
    generated_video_url: Optional[str] = None
    # URL для просмотра видео сегмента через API
    video_url: Optional[str] = None
    progress: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    @field_validator('start_frame_url', 'generated_video_url', 'video_url', mode='before')
    @classmethod
    def convert_gcs_urls(cls, v):
        """Конвертирует gs:// URLs в публичные HTTPS URLs для браузера."""
        if v and isinstance(v, str) and v.startswith('gs://'):
            return get_public_url(v)
        return v


class AnimationProjectResponse(BaseModel):
    """Схема ответа для проекта анимации."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    source_avatar_id: UUID
    name: str  # Название проекта
    total_segments: int
    animation_prompt: Optional[str] = None  # Общий промпт проекта - теперь опциональный
    status: AnimationStatus
    final_video_url: Optional[str] = None
    # URL для просмотра финального видео через API
    video_url: Optional[str] = None
    # URL аватара для отображения на карточке проекта  
    source_avatar_url: Optional[str] = None
    animation_type: str  # Тип анимации: 'sequential' или 'independent'
    created_at: datetime
    updated_at: datetime
    segments: List[AnimationSegmentResponse] = []
    
    @field_validator('final_video_url', 'video_url', 'source_avatar_url', mode='before')
    @classmethod
    def convert_gcs_urls(cls, v):
        """Конвертирует gs:// URLs в публичные HTTPS URLs для браузера."""
        if v and isinstance(v, str) and v.startswith('gs://'):
            return get_public_url(v)
        return v


class AnimationProjectListResponse(BaseModel):
    """Схема для списка проектов анимации пользователя."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    source_avatar_id: UUID
    name: str  # Название проекта
    animation_prompt: Optional[str] = None  # Общий промпт - теперь опциональный
    status: AnimationStatus
    total_segments: int
    final_video_url: Optional[str] = None
    # URL для просмотра финального видео через API
    video_url: Optional[str] = None
    # URL аватара для отображения на карточке проекта
    source_avatar_url: Optional[str] = None
    animation_type: str  # Тип анимации: 'sequential' или 'independent'
    created_at: datetime
    
    @field_validator('final_video_url', 'video_url', 'source_avatar_url', mode='before')
    @classmethod
    def convert_gcs_urls(cls, v):
        """Конвертирует gs:// URLs в публичные HTTPS URLs для браузера."""
        if v and isinstance(v, str) and v.startswith('gs://'):
            return get_public_url(v)
        return v








class AssembleVideoResponse(BaseModel):
    """Схема ответа при запуске сборки финального видео."""
    message: str
    project_id: UUID
    status: str = "assembling" 





class SegmentPromptBatch(BaseModel):
    """Схема для массового обновления промптов сегментов."""
    segment_number: int = Field(..., gt=0, description="Номер сегмента")
    segment_prompt: str = Field(..., min_length=10, max_length=500, description="Промпт для этого сегмента")


class BatchSegmentPromptsUpdate(BaseModel):
    """Схема для обновления промптов всех сегментов сразу."""
    prompts: List[SegmentPromptBatch] = Field(..., min_items=1, description="Список промптов для сегментов")


class GenerateAllSegmentsRequest(BaseModel):
    """Схема для запуска параллельной генерации всех сегментов."""
    force_regenerate: Optional[bool] = Field(False, description="Перегенерировать уже готовые сегменты")


class BatchGenerationResponse(BaseModel):
    """Схема ответа при запуске массовой генерации сегментов."""
    message: str
    project_id: UUID
    total_segments: int
    segments_started: int
    task_ids: List[str] = Field(description="ID задач Celery для каждого сегмента")
    estimated_completion_time: str
    status: str = "generating" 