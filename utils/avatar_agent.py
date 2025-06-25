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
    blocked_words = ["hate", "violence", "nsfw", "explicit"]
    if not prompt or len(prompt.strip()) < 3:
        return True, "Prompt too short", ["too_short"]
    prompt_lower = prompt.lower()
    for word in blocked_words:
        if word in prompt_lower:
            return True, f"Prompt contains inappropriate content", ["blocked_content"]
    return False, None, None

def generate_avatar_with_agent(prompt: str) -> AvatarGenerationResult:
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

async def generate_avatar(request: AvatarCreateRequest) -> AvatarResponse:
    # Генерируем UUID для аватара
    avatar_id = uuid.uuid4()
    try:
        # Генерируем изображение
        image_bytes, _ = generate_image(request.prompt)
        
        # Загружаем изображение в GCS
        image_url = upload_image_to_gcs(image_bytes, f"avatars/{avatar_id}.png")
        
        # Используем user_id из запроса или генерируем новый
        user_id = request.user_id or uuid.uuid4()
        
        # Сохраняем в БД
        await insert_avatar(
            avatar_id=avatar_id,
            user_id=user_id,
            prompt=request.prompt,
            image_data=image_bytes,
            status="completed",
            moderation_flags=None
        )
        
        logger.info(f"Avatar generated and saved: {image_url}")
        return AvatarResponse(
            avatar_id=avatar_id,
            image_url=image_url,
            prompt=request.prompt,
            status="completed",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Failed to generate avatar: {e}")
        raise