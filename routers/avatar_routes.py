from fastapi import APIRouter, HTTPException, status, Response, Depends, Query
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse, AvatarListResponse
import logging
from utils.avatar_agent import generate_avatar
import os
from google.cloud import storage
from utils.model_manager import test_vertex_ai_connection
from db.avatar_repository import test_database_connection, get_avatar_by_id, count_avatars, get_db, User, Avatar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from utils.auth import get_current_active_user
from sqlalchemy import select, func, delete
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/avatars/", response_model=AvatarResponse)
async def create_avatar(
    request: AvatarCreateRequest, 
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AvatarResponse:
    """Creates a new avatar for the authenticated user."""
    logger.info(f"Received avatar creation request from user {current_user.username}: {request.prompt}")
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
        
        avatar_responses = []
        for avatar in avatars:
            avatar_responses.append(AvatarResponse(
                avatar_id=avatar.id,
                image_url=f"https://storage.googleapis.com/avatars/{avatar.id}.png",
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

@router.get("/avatars/vertex-ai-test")
async def vertex_ai_test(current_user: User = Depends(get_current_active_user)):
    """Tests Vertex AI Imagen connection (admin only)."""
    try:
        result = await test_vertex_ai_connection()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Vertex AI test failed: {e}")
        return {"status": "error", "detail": str(e)}

@router.get("/avatars/database-test")
async def database_test(current_user: User = Depends(get_current_active_user)):
    """Tests database connection (admin only)."""
    try:
        result = await test_database_connection()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return {"status": "error", "detail": str(e)}

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

@router.get("/avatars/count")
async def get_avatars_count(current_user: User = Depends(get_current_active_user)):
    """Gets total count of user's avatars."""
    try:
        count = await count_avatars()
        return {"count": count}
    except Exception as e:
        logger.error(f"Error counting avatars: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/avatars/{avatar_id}/image")
async def get_avatar_image(
    avatar_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns avatar image from GCS (only user's own avatars)."""
    try:
        avatar_uuid = UUID(avatar_id)
        avatar = await get_avatar_by_id(avatar_uuid)
        
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        # Check if avatar belongs to current user
        if avatar.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        bucket_name = os.getenv("GCS_BUCKET")
        if not bucket_name:
            raise HTTPException(status_code=500, detail="GCS_BUCKET not configured")
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"avatars/{avatar_id}.png")
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_bytes = blob.download_as_bytes()
        return Response(content=image_bytes, media_type="image/png")
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid avatar ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting avatar image {avatar_id} for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/avatars/{avatar_id}")
async def delete_avatar(
    avatar_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete avatar (only user's own avatars)."""
    try:
        avatar_uuid = UUID(avatar_id)
        avatar = await get_avatar_by_id(avatar_uuid)
        
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        # Check if avatar belongs to current user
        if avatar.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete from database
        delete_stmt = delete(Avatar).where(Avatar.id == avatar_uuid)
        await db.execute(delete_stmt)
        await db.commit()
        
        # Optionally delete from GCS
        try:
            bucket_name = os.getenv("GCS_BUCKET")
            if bucket_name:
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(f"avatars/{avatar_id}.png")
                if blob.exists():
                    blob.delete()
        except Exception as gcs_error:
            logger.warning(f"Failed to delete image from GCS: {gcs_error}")
        
        logger.info(f"Avatar {avatar_id} deleted by user {current_user.username}")
        return {"message": "Avatar deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid avatar ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting avatar {avatar_id} for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")