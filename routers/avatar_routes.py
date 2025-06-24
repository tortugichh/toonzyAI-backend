from fastapi import APIRouter, HTTPException, status
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import logging
from utils.avatar_agent import generate_avatar

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/avatars/", response_model=AvatarResponse)
async def create_avatar(request: AvatarCreateRequest) -> AvatarResponse:
    return await generate_avatar(request)

# Health check endpoint
@router.get("/avatars/health")
async def avatar_health():
    return {"status": "ok", "service": "avatar"}

@router.get("/{avatar_id}", response_model=AvatarResponse)
async def get_avatar(avatar_id: UUID):
    """Get avatar by ID"""
    try:
        logger.info(f"Fetching avatar with ID: {avatar_id}")
        
        avatar = get_avatar_by_id(avatar_id)
        if not avatar:
            logger.warning(f"Avatar not found: {avatar_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Avatar not found"
            )
        
        # Конвертируем binary данные в base64
        image_base64 = ""
        if avatar.image_data:
            image_base64 = base64.b64encode(avatar.image_data).decode('utf-8')
        
        # Парсим moderation_flags
        moderation_flags = []
        if avatar.moderation_flags:
            moderation_flags = avatar.moderation_flags.split(',')
        
        return AvatarResponse(
            id=avatar.id,
            user_id=avatar.user_id,
            prompt=avatar.prompt,
            image_data=image_base64,
            created_at=avatar.created_at,
            status=avatar.status,
            moderation_flags=moderation_flags
        )
    except ImportError as e:
        logger.error(f"Import error in get_avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service unavailable"
        )
    except Exception as e:
        logger.error(f"Error fetching avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch avatar"
        )

@router.post("/{avatar_id}/regenerate", response_model=AvatarResponse)
async def regenerate_avatar(avatar_id: UUID):
    """Regenerate an existing avatar"""
    try:
        from utils.avatar_agent import generate_avatar_with_agent
        
        logger.info(f"Regenerating avatar with ID: {avatar_id}")
        
        avatar = get_avatar_by_id(avatar_id)
        if not avatar:
            logger.warning(f"Avatar not found for regeneration: {avatar_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Avatar not found"
            )
        
        agent_result = generate_avatar_with_agent(avatar.prompt)
        if agent_result.is_blocked:
            logger.warning(f"Avatar regeneration blocked: {agent_result.reason}")
            update_avatar_status(avatar_id, "error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=agent_result.reason
            )
        
        update_avatar_status(avatar_id, "completed", agent_result.image_bytes)
        
        logger.info(f"Avatar regenerated successfully: {avatar_id}")
        
        return AvatarResponse(
            id=avatar_id,
            user_id=avatar.user_id,
            prompt=avatar.prompt,
            image_data=agent_result.image_base64,
            created_at=agent_result.created_at,
            status="completed",
            moderation_flags=agent_result.moderation_flags
        )
    except ImportError as e:
        logger.error(f"Import error in regenerate_avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Avatar generation service unavailable"
        )
    except Exception as e:
        logger.error(f"Error regenerating avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate avatar"
        )

@router.get("/{avatar_id}/image")
def get_avatar_image(avatar_id: UUID):
    avatar = get_avatar_by_id(avatar_id)
    if not avatar or not avatar.image_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Avatar not found or has no image data")
    return StreamingResponse(io.BytesIO(avatar.image_data), media_type="image/png")