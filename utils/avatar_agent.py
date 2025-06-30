import os
from datetime import datetime
from typing import NamedTuple, Optional, List
from pydantic import BaseModel
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import uuid
import logging
from utils.model_manager import generate_image
from utils.gcs_client import upload_image_to_gcs
from db.avatar_repository import insert_avatar
from uuid import UUID

logger = logging.getLogger(__name__)

class AgentResult(BaseModel):
    is_blocked: bool
    reason: Optional[str] = None
    image_bytes: Optional[bytes] = None
    image_base64: Optional[str] = None
    created_at: Optional[datetime] = None
    moderation_flags: Optional[List[str]] = None

class AvatarGenerationResult(NamedTuple):
    image_bytes: bytes
    image_base64: str
    created_at: datetime
    is_blocked: bool = False
    reason: str = ""
    moderation_flags: List[str] = []

def moderate_prompt(prompt: str) -> tuple[bool, Optional[str], Optional[List[str]]]:
    """Модерирует промпт на недопустимый контент."""
    blocked_words = ["hate", "violence", "nsfw", "explicit"]
    if not prompt or len(prompt.strip()) < 3:
        return True, "Prompt too short", ["too_short"]
    prompt_lower = prompt.lower()
    for word in blocked_words:
        if word in prompt_lower:
            return True, f"Prompt contains inappropriate content", ["blocked_content"]
    return False, None, None

def generate_avatar_with_agent(prompt: str) -> AvatarGenerationResult:
    """Генерирует аватар с использованием агента."""
    try:
        is_blocked, reason, flags = moderate_prompt(prompt)
        if is_blocked:
            return AvatarGenerationResult(
                image_bytes=b"",
                image_base64="",
                created_at=datetime.utcnow(),
                is_blocked=True,
                reason=reason,
                moderation_flags=flags or []
            )
        image_bytes, image_base64 = generate_image(prompt)
        return AvatarGenerationResult(
            image_bytes=image_bytes,
            image_base64=image_base64,
            created_at=datetime.utcnow(),
            is_blocked=False,
            reason="",
            moderation_flags=[]
        )
    except Exception as e:
        return AvatarGenerationResult(
            image_bytes=b"",
            image_base64="",
            created_at=datetime.utcnow(),
            is_blocked=True,
            reason=f"Failed to generate avatar: {str(e)}",
            moderation_flags=["generation_error"]
        )

async def generate_avatar(request: AvatarCreateRequest, user_id: UUID) -> AvatarResponse:
    """Генерирует аватар по запросу для конкретного пользователя."""
    # Генерируем UUID для аватара
    avatar_id = uuid.uuid4()
    
    logger.info(f"Starting avatar generation for user {user_id}, avatar {avatar_id}")
    
    try:
        # Генерируем изображение
        logger.info(f"Generating image with prompt: {request.prompt}")
        image_bytes, _ = generate_image(request.prompt)
        logger.info(f"Image generated successfully, size: {len(image_bytes)} bytes")
        
        # Загружаем изображение в GCS
        logger.info(f"Uploading image to GCS...")
        image_url = upload_image_to_gcs(image_bytes, f"avatars/{avatar_id}.png")
        logger.info(f"Image uploaded to GCS: {image_url}")
        
        # Сохраняем в БД
        logger.info(f"Saving avatar to database...")
        saved_avatar_id = await insert_avatar(
            avatar_id=avatar_id,
            user_id=user_id,
            prompt=request.prompt,
            image_data=image_bytes,
            status="completed",
            moderation_flags=None
        )
        logger.info(f"Avatar saved to database with ID: {saved_avatar_id}")
        
        # Проверяем, что ID совпадают
        if saved_avatar_id != avatar_id:
            logger.warning(f"Generated avatar_id {avatar_id} != saved avatar_id {saved_avatar_id}")
        
        response = AvatarResponse(
            avatar_id=avatar_id,
            image_url=f"/api/v1/avatars/{avatar_id}/image",
            prompt=request.prompt,
            status="completed",
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Avatar generation completed successfully: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Avatar generation failed for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Avatar generation failed: {str(e)}")