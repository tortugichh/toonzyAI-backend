from fastapi import APIRouter, HTTPException, status, Response
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import logging
from utils.avatar_agent import generate_avatar
import os
from google.cloud import storage
from utils.model_manager import test_vertex_ai_connection
from db.avatar_repository import test_database_connection, get_avatar_by_id, count_avatars
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from uuid import uuid4
from db.models import Avatar
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/avatars/", response_model=AvatarResponse)
async def create_avatar(request: AvatarCreateRequest, db: AsyncSession = Depends(get_db)) -> AvatarResponse:
    """Создает новый аватар (вся логика прямо в ручке)."""
    logger.info(f"Received avatar creation request: {request}")
    try:
        avatar_id = uuid4()
        user_id = request.user_id if request.user_id else uuid4()
        prompt = request.prompt
        image_data = b''  # Заглушка, если нет генерации
        status = 'completed'
        moderation_flags = None
        avatar = Avatar(
            id=avatar_id,
            user_id=user_id,
            prompt=prompt,
            image_data=image_data,
            status=status,
            moderation_flags=moderation_flags
        )
        db.add(avatar)
        await db.commit()
        await db.refresh(avatar)
        image_url = f"https://storage.googleapis.com/avatars/{avatar_id}.png"
        logger.info(f"Avatar created successfully: {avatar_id}")
        return AvatarResponse(
            avatar_id=avatar_id,
            image_url=image_url,
            prompt=prompt,
            status=status,
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Error creating avatar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create avatar: {str(e)}")

@router.get("/avatars/vertex-ai-test")
async def vertex_ai_test():
    """Тестирует подключение к Vertex AI Imagen."""
    try:
        result = await test_vertex_ai_connection()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Vertex AI test failed: {e}")
        return {"status": "error", "detail": str(e)}

@router.get("/avatars/database-test")
async def database_test():
    """Тестирует подключение к базе данных."""
    try:
        result = await test_database_connection()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return {"status": "error", "detail": str(e)}

@router.get("/avatars/{avatar_id}")
async def get_avatar(avatar_id: str):
    """Получает информацию об аватаре по ID."""
    try:
        avatar_uuid = UUID(avatar_id)
        avatar = await get_avatar_by_id(avatar_uuid)
        if not avatar:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
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
    except Exception as e:
        logger.error(f"Error getting avatar {avatar_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/avatars/count")
async def get_avatars_count():
    """Возвращает количество аватаров в базе данных."""
    try:
        count = await count_avatars()
        return {"count": count, "status": "success"}
    except Exception as e:
        logger.error(f"Error counting avatars: {e}")
        return {"status": "error", "detail": str(e)}

@router.get("/avatars/{avatar_id}/image")
def get_avatar_image(avatar_id: str):
    """Возвращает изображение из GCS по ID."""
    try:
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
    except Exception as e:
        logger.error(f"Error getting avatar image {avatar_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")