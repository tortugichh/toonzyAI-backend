from fastapi import APIRouter, HTTPException, status, Response, Depends, Query
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse, AvatarListResponse, AvatarStatusResponse
import logging
from utils.avatar_agent import generate_avatar
from utils.content_moderator import check_prompt_safety
import os
from google.cloud import storage
from db.avatar_repository import get_avatar_by_id, get_db, User, Avatar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from utils.auth import get_current_active_user
from sqlalchemy import select, func, delete
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# ===== Maintenance flag (shared with animation_routes) =====
from routers.animation_routes import MAINTENANCE_MODE  # reuse flag

@router.post("/avatars/", response_model=AvatarResponse)
async def create_avatar(
    request: AvatarCreateRequest, 
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AvatarResponse:
    """Creates a new avatar for the authenticated user."""
    if MAINTENANCE_MODE:
        raise HTTPException(status_code=503, detail="Image generation is temporarily disabled for maintenance. Please try later.")
    logger.info(f"Received avatar creation request from user {current_user.username}: {request.prompt}")

    # Лимит: только 1 аватар на пользователя
    count_query = select(func.count(Avatar.id)).where(Avatar.user_id == current_user.id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    if total >= 1:
        raise HTTPException(status_code=403, detail="Доступна только одна генерация аватара для нового пользователя.")

    # Проверяем промпт на безопасность
    moderation_result = check_prompt_safety(request.prompt)
    if not moderation_result.is_safe:
        logger.warning(f"Unsafe prompt detected from user {current_user.username}: {moderation_result.reasons}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "content_policy_violation",
                "message": "Ваш промпт нарушает политику контента",
                "reasons": moderation_result.reasons,
                "suggested_fix": moderation_result.suggested_fix
            }
        )
    try:
        result = await generate_avatar(request, current_user.id)
        logger.info(f"Avatar created successfully for user {current_user.username}: {result.avatar_id}")
        return result
    except Exception as e:
        logger.error(f"Error creating avatar for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create avatar: {str(e)}")

@router.get("/avatars/", response_model=AvatarListResponse)
async def get_user_avatars(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page")
) -> AvatarListResponse:
    """Get all avatars for the authenticated user with pagination."""
    try:
        offset = (page - 1) * per_page
        
        # Get total count for user
        count_query = select(func.count(Avatar.id)).where(Avatar.user_id == current_user.id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get avatars for user with pagination
        avatars_query = select(Avatar).where(
            Avatar.user_id == current_user.id
        ).order_by(Avatar.created_at.desc()).offset(offset).limit(per_page)
        
        result = await db.execute(avatars_query)
        avatars = result.scalars().all()
        
        bucket_name = os.getenv("GCS_BUCKET")
        if not bucket_name:
            raise HTTPException(status_code=500, detail="GCS_BUCKET not configured")
            
        avatar_responses = []
        for avatar in avatars:
            # Используем наш API эндпоинт вместо прямых GCS ссылок
            avatar_responses.append(AvatarResponse(
                avatar_id=avatar.id,
                image_url=f"/api/v1/avatars/{avatar.id}/image",
                prompt=avatar.prompt,
                status=avatar.status,
                user_id=avatar.user_id,
                created_at=avatar.created_at
            ))
        
        return AvatarListResponse(
            avatars=avatar_responses,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error getting avatars for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/avatars/{avatar_id}")
async def get_avatar(
    avatar_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Gets avatar information by ID (only user's own avatars)."""
    try:
        avatar_uuid = UUID(avatar_id)
        avatar = await get_avatar_by_id(avatar_uuid)
        
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        # Check if avatar belongs to current user
        if avatar.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "avatar_id": str(avatar.id),
            "user_id": str(avatar.user_id),
            "prompt": avatar.prompt,
            "status": avatar.status,
            "image_url": f"/api/v1/avatars/{avatar.id}/image",
            "created_at": avatar.created_at.isoformat() if avatar.created_at else None,
            "moderation_flags": avatar.moderation_flags.split(',') if avatar.moderation_flags else None
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid avatar ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting avatar {avatar_id} for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/avatars/{avatar_id}/image")
async def get_avatar_image(
    avatar_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the avatar image file."""
    try:
        avatar_uuid = UUID(avatar_id)
        avatar = await get_avatar_by_id(avatar_uuid)
        
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        # Check if avatar belongs to current user
        if avatar.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Return image from database binary data
        if avatar.image_data:
            return Response(
                content=avatar.image_data,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"inline; filename=avatar_{avatar_id}.png",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        else:
            raise HTTPException(status_code=404, detail="Avatar image not found")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid avatar ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting avatar image {avatar_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/avatars/{avatar_id}")
async def delete_avatar(
    avatar_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes an avatar (only user's own avatars)."""
    try:
        avatar_uuid = UUID(avatar_id)
        
        # Find avatar and check ownership
        avatar_query = select(Avatar).where(
            Avatar.id == avatar_uuid,
            Avatar.user_id == current_user.id
        )
        avatar_result = await db.execute(avatar_query)
        avatar = avatar_result.scalar_one_or_none()
        
        if not avatar:
            raise HTTPException(
                status_code=404, 
                detail="Avatar not found or you don't have permission to delete it"
            )
        
        # Delete avatar from database
        await db.delete(avatar)
        await db.commit()
        
        logger.info(f"Avatar {avatar_id} deleted by user {current_user.username}")
        
        return {"message": "Avatar deleted successfully", "avatar_id": avatar_id}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid avatar ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting avatar {avatar_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/avatars/{avatar_id}/status", response_model=AvatarStatusResponse)
async def get_avatar_status(avatar_id: UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)) -> AvatarStatusResponse:
    """Возвращает статус и прогресс генерации аватара."""
    avatar = await get_avatar_by_id(avatar_id)
    if not avatar or avatar.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return AvatarStatusResponse(
        avatar_id=avatar.id,
        status=avatar.status,
        progress=avatar.progress
    )