import os
from datetime import datetime
from typing import NamedTuple, Optional, List
from pydantic import BaseModel
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import uuid
import logging
from utils.model_manager import generate_image

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
    avatar_id = str(uuid.uuid4())
    try:
        image_bytes, _ = generate_image(request.prompt)
        image_path = f"static/avatars/{avatar_id}.png"
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        image_url = f"/static/avatars/{avatar_id}.png"
        logger.info(f"Avatar generated and saved: {image_url}")
        return AvatarResponse(avatar_id=avatar_id, image_url=image_url)
    except Exception as e:
        logger.error(f"Failed to generate avatar: {e}")
        raise