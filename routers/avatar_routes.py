from fastapi import APIRouter, HTTPException, status
from schemas.avatar_schemas import AvatarCreateRequest, AvatarResponse
import logging
from utils.avatar_agent import generate_avatar
import os
from fastapi.responses import FileResponse
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

@router.get("/avatars/{avatar_id}/file", response_class=FileResponse)
def get_avatar_file(avatar_id: str):
    """Возвращает файл изображения по ID."""
    file_path = f"static/avatars/{avatar_id}.png"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/png")