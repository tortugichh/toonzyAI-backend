"""
Клиент для работы с Google Vertex AI Veo 2.0
Обновлено для использования GA версии модели с long-running operations
"""

import os
import base64
import time
import asyncio
import requests
import logging
import tempfile

from google.auth import default
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_PROJECT")
LOCATION = os.getenv("VERTEX_AI_LOCATION") or os.getenv("VERTEX_LOCATION", "us-central1")
GCS_BUCKET = os.getenv("GCS_BUCKET")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

# Popular regions where Vertex AI models are usually available
VERTEX_AI_REGIONS = [
    "us-central1",   # Iowa (required for Veo according to docs)
    "us-east1",      # Virginia 
    "us-west1",      # Oregon
    "europe-west1",  # Belgium
    "europe-west4",  # Netherlands  
    "asia-northeast1" # Tokyo
]

async def generate_video_from_image_v2(
    start_frame_url: str,
    animation_prompt: str,
    duration_seconds: int = 5,
    segment_id: str | None = None
) -> str:
    """
    Генерирует видео используя Veo 2.0 с правильным REST API (согласно официальной документации).
    
    Args:
        start_frame_url: URL изображения или file:// путь
        animation_prompt: Промпт для анимации
        duration_seconds: Длительность видео (5-8 секунд)
        
    Returns:
        URL сгенерированного видео в GCS (gs://)
    """
    
    try:
        logger.info(f"Starting Veo 2.0 video generation with prompt: {animation_prompt}")
        logger.info(f"Using official REST API from documentation")
        
        # 1. Подготавливаем изображение (если есть)
        image_data = None
        if start_frame_url:
            if start_frame_url.startswith('file://'):
                # Локальный файл
                temp_image_path = start_frame_url.replace('file://', '')
                if not os.path.exists(temp_image_path):
                    raise FileNotFoundError(f"Local file not found: {temp_image_path}")
                with open(temp_image_path, 'rb') as f:
                    image_bytes = f.read()
            elif start_frame_url.startswith('gs://'):
                # GCS файл - используем GCS клиент
                from utils.gcs_client import download_file_from_gcs_authenticated
                image_bytes = await download_file_from_gcs_authenticated(start_frame_url)
            else:
                # Скачиваем изображение по HTTP URL
                response = requests.get(start_frame_url)
                response.raise_for_status()
                image_bytes = response.content
            
            # Кодируем в base64
            image_data = {
                "bytesBase64Encoded": base64.b64encode(image_bytes).decode('utf-8'),
                "mimeType": "image/jpeg"
            }
        
        # 2. Получаем токен аутентификации
        credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        credentials.refresh(Request())
        access_token = credentials.token
        
        # 3. Формируем правильный URL (из документации)
        # MODEL_ID может быть: veo-2.0-generate-001 или veo-3.0-generate-preview
        model_id = "veo-2.0-generate-001"  # GA версия
        predict_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{model_id}:predictLongRunning"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # 4. Формируем request body согласно документации
        instances = []
        if image_data:
            # Image-to-video
            instances.append({
                "prompt": animation_prompt,
                "image": image_data
            })
        else:
            # Text-to-video
            instances.append({
                "prompt": animation_prompt
            })
        
        parameters = {
            "sampleCount": 1,
            "durationSeconds": min(max(duration_seconds, 5), 8)  # 5-8 секунд согласно документации
        }
        
        request_body = {
            "instances": instances,
            "parameters": parameters
        }
        
        logger.info(f"Sending predictLongRunning request to: {predict_url}")
        logger.info(f"Duration: {parameters['durationSeconds']} seconds")
        
        # 5. Отправляем запрос на генерацию
        response = requests.post(predict_url, headers=headers, json=request_body)
        response.raise_for_status()
        
        operation_data = response.json()
        operation_name = operation_data.get("name")
        
        if not operation_name:
            raise Exception("No operation name returned from Veo 2.0")
        
        logger.info(f"✅ Veo 2.0 operation started: {operation_name}")
        
        # 6. Polling для получения результата
        video_gcs_uri = await _poll_veo2_operation(operation_name, model_id, segment_id)
        
        logger.info(f"✅ Veo 2.0 video generated successfully: {video_gcs_uri}")
        return video_gcs_uri
            
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Veo 2.0 model not found (404) - project may not have access")
            raise Exception("Veo 2.0 model not available - check project access/waitlist")
        elif e.response.status_code == 429:
            logger.error(f"Quota exceeded for Veo 2.0 (429)")
            raise Exception("Veo 2.0 quota exceeded - try later or increase limits")
        elif e.response.status_code == 403:
            logger.error(f"Permission denied for Veo 2.0 (403)")
            raise Exception("Veo 2.0 access denied - check IAM permissions")
        else:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Veo 2.0 API error: {e.response.status_code}")
        
    except Exception as e:
        logger.error(f"Veo 2.0 generation failed: {str(e)}")
        raise e

async def _poll_veo2_operation(operation_name: str, model_id: str, segment_id: str | None = None) -> str:
    """
    Polling для получения результата long-running операции Veo 2.0 (согласно официальной документации).
    
    Args:
        operation_name: Полное имя операции (из первоначального ответа)
        model_id: ID модели (veo-2.0-generate-001 или veo-3.0-generate-preview)
        
    Returns:
        GCS URI видео файла (gs://bucket/path/video.mp4)
    """
    
    max_wait_time = 300  # 5 минут максимум
    poll_interval = 10   # Проверяем каждые 10 секунд
    start_time = time.time()
    
    # Формируем URL для fetchPredictOperation (из документации)
    fetch_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/{model_id}:fetchPredictOperation"
    
    while time.time() - start_time < max_wait_time:
        try:
            # Получаем токен аутентификации
            credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            if not credentials.valid:
                credentials.refresh(Request())
            access_token = credentials.token
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Request body согласно документации
            request_body = {
                "operationName": operation_name
            }
            
            logger.info(f"Polling operation status: {operation_name}")
            
            # Отправляем запрос на получение статуса
            response = requests.post(fetch_url, headers=headers, json=request_body)
            response.raise_for_status()
            
            operation_data = response.json()
            
            # Проверяем, завершилась ли операция
            if operation_data.get("done", False):
                logger.info("✅ Veo 2.0 operation completed!")
                
                # Проверяем на ошибки
                if "error" in operation_data:
                    error_msg = operation_data["error"].get("message", "Unknown error")
                    logger.error(f"❌ Operation failed: {error_msg}")
                    raise Exception(f"Video generation failed: {error_msg}")
                
                # Извлекаем GCS URI из ответа (согласно документации)
                response_data = operation_data.get("response", {})
                videos = response_data.get("videos", [])
                
                if videos and len(videos) > 0:
                    video_info = videos[0]  # Берем первое видео
                    
                    logger.info(f"🔍 Video info keys: {list(video_info.keys())}")
                    
                    # Проверяем новый формат (gcsUri) из документации
                    gcs_uri = video_info.get("gcsUri")
                    if gcs_uri:
                        logger.info(f"🎬 Video generated successfully (GCS URI format)!")
                        logger.info(f"📁 GCS URI: {gcs_uri}")
                        return gcs_uri
                    
                    # Проверяем реальный формат (base64) который возвращает Veo
                    base64_video = video_info.get("bytesBase64Encoded")
                    mime_type = video_info.get("mimeType", "video/mp4")
                    
                    if base64_video:
                        logger.info(f"🎬 Video generated successfully (base64 format)!")
                        logger.info(f"📊 Base64 data length: {len(base64_video)} chars")
                        logger.info(f"🎥 MIME type: {mime_type}")
                        
                        # Декодируем base64 данные
                        video_bytes = base64.b64decode(base64_video)
                        logger.info(f"📹 Decoded video size: {len(video_bytes)} bytes")
                        
                        # Сохраняем в GCS
                        gcs_uri = await _save_video_to_gcs(video_bytes, mime_type)
                        logger.info(f"✅ Video saved to GCS: {gcs_uri}")
                        return gcs_uri
                    
                    # Если ни один формат не найден
                    logger.error(f"❌ No video data found. Available fields: {list(video_info.keys())}")
                    raise Exception("No video data in response")
                else:
                    # Check if content was filtered by RAI
                    if "raiMediaFilteredCount" in response_data or "raiMediaFilteredReasons" in response_data:
                        filtered_count = response_data.get("raiMediaFilteredCount", 0)
                        filtered_reasons = response_data.get("raiMediaFilteredReasons", [])
                        
                        logger.error("🚫 Content was filtered by Google's Responsible AI system")
                        logger.error(f"📊 Filtered count: {filtered_count}")
                        if filtered_reasons:
                            logger.error(f"🔍 Filtered reasons: {filtered_reasons}")
                        
                        # Provide helpful error message
                        reason_text = f" (Reasons: {', '.join(filtered_reasons)})" if filtered_reasons else ""
                        raise Exception(f"Content was filtered by Google's AI safety system{reason_text}. Please try a different prompt that doesn't violate content policies.")
                    else:
                        logger.error("❌ No videos array found in response")
                        logger.error(f"Response structure: {list(response_data.keys())}")
                        raise Exception("No videos in response")
                    
            else:
                # Обновляем прогресс, если доступен progressPercent
                progress_meta = operation_data.get("metadata", {})
                percent = progress_meta.get("progressPercent")
                if percent is not None and segment_id:
                    # Обновляем в БД
                    from db.avatar_repository import AsyncSessionLocal, AnimationSegment
                    from sqlalchemy import update
                    async with AsyncSessionLocal() as progress_db:
                        await progress_db.execute(
                            update(AnimationSegment).where(AnimationSegment.id == segment_id).values(progress=int(percent))
                        )
                        await progress_db.commit()

                logger.info(f"⏳ Operation still running ({percent or '?'}%), waiting {poll_interval} seconds...")
                await asyncio.sleep(poll_interval)
        
        except requests.HTTPError as e:
            logger.error(f"HTTP error while polling operation: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
            raise Exception(f"Failed to poll operation: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error polling Veo 2.0 operation: {e}")
            raise
    
    # Таймаут
    logger.error(f"❌ Veo 2.0 operation {operation_name} timed out after {max_wait_time} seconds")
    raise Exception(f"Operation timed out after {max_wait_time} seconds")

async def _save_video_to_gcs(video_bytes: bytes, mime_type: str) -> str:
    """
    Сохраняет видео данные в GCS bucket
    
    Args:
        video_bytes: Видео данные в байтах
        mime_type: MIME тип видео
        
    Returns:
        GCS URI (gs://bucket/path/file.mp4)
    """
    try:
        from google.cloud import storage
        import uuid
        from datetime import datetime, timedelta
        
        # Инициализируем клиент GCS
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        
        # Определяем расширение файла по MIME типу
        extension = ".mp4"  # по умолчанию
        if "webm" in mime_type.lower():
            extension = ".webm"
        elif "avi" in mime_type.lower():
            extension = ".avi"
        elif "mov" in mime_type.lower():
            extension = ".mov"
        
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"animations/veo2/veo2_{timestamp}_{unique_id}{extension}"
        
        # Загружаем видео в GCS
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)
        
        # Делаем видео публичным для прямого доступа
        try:
            blob.make_public()
            logger.info(f"✅ Made video public: {filename}")
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{filename}"
        except Exception as e:
            logger.warning(f"⚠️ Could not make video public (uniform bucket-level access?): {e}")
            # Генерируем signed URL как fallback
            public_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            logger.info("📝 Generated signed URL for video (7 days)")
        
        # Формируем GCS URI
        gcs_uri = f"gs://{GCS_BUCKET}/{filename}"
        logger.info(f"💾 Video saved to GCS: {gcs_uri} ({len(video_bytes)} bytes)")
        logger.info(f"🔗 Accessible URL: {public_url[:120]}...")
        
        return gcs_uri
        
    except Exception as e:
        logger.error(f"❌ Failed to save video to GCS: {e}")
        raise Exception(f"Failed to save video to GCS: {e}")

async def test_veo_availability_in_regions() -> dict:
    """Test Veo model availability across different regions"""
    results = {}
    
    for region in VERTEX_AI_REGIONS:
        try:
            logger.info(f"Testing Veo availability in region: {region}")
            
            # Get authentication token
            credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            credentials.refresh(Request())
            access_token = credentials.token
            
            # Test endpoint for this region
            test_url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{region}/publishers/google/models/veo-3.0-generate-preview"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Simple GET request to check if model exists
            response = requests.get(test_url, headers=headers)
            
            if response.status_code == 200:
                results[region] = {"status": "✅ Available", "model": "veo-3.0-generate-preview"}
                logger.info(f"✅ Veo 3.0 available in {region}")
            elif response.status_code == 404:
                # Try Veo 2.0 
                test_url_v2 = f"https://{region}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{region}/publishers/google/models/veo-2.0-generate-001"
                response_v2 = requests.get(test_url_v2, headers=headers)
                
                if response_v2.status_code == 200:
                    results[region] = {"status": "✅ Available", "model": "veo-2.0-generate-001"}
                    logger.info(f"✅ Veo 2.0 available in {region}")
                else:
                    results[region] = {"status": "❌ Not Available", "error": f"HTTP {response.status_code}"}
                    logger.warning(f"❌ Veo not available in {region}")
            else:
                results[region] = {"status": "⚠️ Other Error", "error": f"HTTP {response.status_code}"}
                logger.warning(f"⚠️ Unexpected response in {region}: {response.status_code}")
                
        except Exception as e:
            results[region] = {"status": "❌ Error", "error": str(e)}
            logger.error(f"❌ Error testing {region}: {str(e)}")
    
    return results

if __name__ == "__main__":
    # Простой тест новой реализации
    async def main():
        try:
            print("🧪 Testing new Veo 2.0 implementation...")
            
            video_url = await generate_video_from_image_v2(
                start_frame_url=None,
                animation_prompt="A beautiful sunset over mountains",
                duration_seconds=5
            )
            
            print(f"✅ Success! Video: {video_url}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    import asyncio
    asyncio.run(main()) 