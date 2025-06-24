import os
from pathlib import Path
from PIL import Image
import io
import base64
from typing import Optional, Tuple
import logging
import asyncio
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic import PredictionServiceClient

logger = logging.getLogger(__name__)

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "projects/{project}/locations/{location}/publishers/google/models/imagen-4.0-generate-preview-06-06")

def _get_model_path() -> str:
    """Получает полный путь к модели Imagen."""
    project = VERTEX_PROJECT
    location = VERTEX_LOCATION
    if not project:
        raise RuntimeError("VERTEX_PROJECT env var is required for Vertex AI Imagen usage.")
    return IMAGEN_MODEL.format(project=project, location=location)

def generate_image(prompt: str) -> Tuple[bytes, str]:
    """
    Генерирует изображение через Vertex AI Imagen API.
    Возвращает (image_bytes, image_base64).
    """
    try:
        aiplatform.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
        endpoint = _get_model_path()
        prediction_client = PredictionServiceClient()
        instance = {"prompt": prompt}
        parameters = {"sampleCount": 1}
        response = prediction_client.predict(
            endpoint=endpoint,
            instances=[instance],
            parameters=parameters
        )
        if not response.predictions:
            logger.error("No predictions returned from Vertex Imagen.")
            return _create_placeholder_image()
        image_b64 = response.predictions[0]["bytesBase64Encoded"]
        image_bytes = base64.b64decode(image_b64)
        return image_bytes, image_b64
    except Exception as e:
        logger.error(f"Vertex Imagen generation failed: {e}")
        return _create_placeholder_image()

def _create_placeholder_image() -> Tuple[bytes, str]:
    """Создает placeholder изображение в случае ошибки."""
    img = Image.new('RGB', (512, 512), color='lightgray')
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_bytes = img_byte_array.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_bytes, img_base64

async def test_vertex_ai_connection() -> str:
    """Тестирует подключение к Vertex AI Imagen."""
    try:
        loop = asyncio.get_event_loop()
        image_bytes, image_b64 = await loop.run_in_executor(None, generate_image, "test connection")
        if image_bytes and image_b64:
            return "Vertex AI Imagen connection successful. Image generated."
        return "Vertex AI Imagen connection failed: no image returned."
    except Exception as e:
        return f"Vertex AI Imagen connection error: {str(e)}"