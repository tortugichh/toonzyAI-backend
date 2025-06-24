from fastapi import APIRouter, HTTPException, status
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import logging
from utils.avatar_agent import generate_avatar
import os
from fastapi.responses import RedirectResponse
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
    """Редиректит на публичный URL изображения в GCS."""
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET not configured")
    public_url = f"https://storage.googleapis.com/{bucket_name}/avatars/{avatar_id}.png"
    return RedirectResponse(public_url)