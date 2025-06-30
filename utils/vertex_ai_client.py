import os
import tempfile
from typing import Optional
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip
import base64
import requests
from utils.gcs_client import upload_file_to_gcs
import logging

logger = logging.getLogger(__name__)

# Инициализация Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

aiplatform.init(project=PROJECT_ID, location=LOCATION)


async def generate_video_from_image(
    start_frame_url: str,
    animation_prompt: str,
    duration_seconds: int = 5
) -> str:
    """
    Генерирует видео из изображения используя Vertex AI Imagen.
    
    Args:
        start_frame_url: URL изображения-основы
        animation_prompt: Промпт для анимации
        duration_seconds: Длительность видео в секундах
        
    Returns:
        URL сгенерированного видео в GCS
    """
    try:
        # Обрабатываем URL или локальный файл
        if start_frame_url.startswith('file://'):
            # Локальный файл
            temp_image_path = start_frame_url.replace('file://', '')
            if not os.path.exists(temp_image_path):
                raise FileNotFoundError(f"Local file not found: {temp_image_path}")
        else:
            # Скачиваем изображение по URL
            response = requests.get(start_frame_url)
            response.raise_for_status()
            
            # Создаем временный файл для изображения
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_image:
                temp_image.write(response.content)
                temp_image_path = temp_image.name
        
        # Кодируем изображение в base64
        with open(temp_image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Используем новейшую модель Veo 3 для генерации видео
        endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/veo-3-generate-001-preview:predict"
        
        request_data = {
            "instances": [{
                "prompt": animation_prompt,
                "image": {
                    "bytesBase64Encoded": image_data
                },
                # Veo 3 поддерживает улучшенные параметры
                "generationConfig": {
                    "duration": f"{duration_seconds}s",
                    "aspectRatio": "16:9",
                    "motionLevel": "medium",  # low, medium, high
                    "quality": "standard"     # standard, high
                }
            }],
            "parameters": {
                "sampleCount": 1
            }
        }
        
        # Вызываем модель через Vertex AI API
        try:
            client = aip.PredictionServiceClient()
            
            response = client.predict(
                endpoint=endpoint,
                instances=request_data["instances"],
                parameters=request_data["parameters"]
            )
        except Exception as api_error:
            # Если модель недоступна, выбрасываем ошибку
            if "Invalid Endpoint name" in str(api_error) or "not found" in str(api_error).lower():
                logger.error(f"Veo model not available in project {PROJECT_ID}")
                raise api_error
            else:
                raise api_error
        
        # Извлекаем сгенерированное видео
        if response.predictions:
            video_data = response.predictions[0].get("videoData")
            if video_data:
                # Декодируем видео из base64
                video_bytes = base64.b64decode(video_data)
                
                # Создаем временный файл для видео
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                    temp_video.write(video_bytes)
                    temp_video_path = temp_video.name
                
                # Загружаем видео в GCS
                video_url = await upload_file_to_gcs(
                    temp_video_path,
                    f"animations/segments/{os.path.basename(temp_video_path)}"
                )
                
                # Удаляем временные файлы (кроме исходных локальных файлов)
                if not start_frame_url.startswith('file://'):
                    os.unlink(temp_image_path)
                os.unlink(temp_video_path)
                
                logger.info(f"Successfully generated video: {video_url}")
                return video_url
        
        raise RuntimeError("No video data received from Vertex AI")
        
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        # Удаляем временные файлы в случае ошибки (кроме исходных локальных файлов)
        try:
            if not start_frame_url.startswith('file://'):
                os.unlink(temp_image_path)
        except:
            pass
        raise


 