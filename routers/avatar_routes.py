from fastapi import APIRouter, HTTPException, status, Response
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import logging
from utils.avatar_agent import generate_avatar
import os
from google.cloud import storage
from utils.model_manager import test_vertex_ai_connection

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/avatars/", response_model=AvatarResponse)
async def create_avatar(request: AvatarCreateRequest) -> AvatarResponse:
    """Создает новый аватар используя Vertex AI Imagen."""
    return await generate_avatar(request)

@router.get("/avatars/vertex-ai-test")
async def vertex_ai_test():
    """Тестирует подключение к Vertex AI Imagen."""
    try:
        result = await test_vertex_ai_connection()
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/avatars/{avatar_id}/file")
def get_avatar_file(avatar_id: str):
    """Возвращает изображение из GCS по ID."""
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