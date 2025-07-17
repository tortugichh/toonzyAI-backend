import os
from pathlib import Path
from PIL import Image
import io
import base64
from typing import Optional, Tuple
import logging
import asyncio
from dotenv import load_dotenv

load_dotenv()

from google.cloud import aiplatform
from google.cloud.aiplatform.gapic import PredictionServiceClient

# Optional: automatic translation for non-English prompts
try:
    from google.cloud import translate_v2 as translate  # Lightweight client
except ImportError:  # translate library may be missing in some envs
    translate = None  # Fallback: no translation

import re
import time

logger = logging.getLogger(__name__)

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")  # Changed from us-east1 to us-central1
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "projects/{project}/locations/{location}/publishers/google/models/imagen-3.0-generate-001")  # Changed to imagen-3.0
GCS_BUCKET = os.getenv("GCS_BUCKET")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

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
    logger.info(f"🎨 Starting image generation with prompt: {prompt[:100]}...")
    
    try:
        # Detect non-English text (simple heuristic: presence of Cyrillic chars)
        original_prompt = prompt
        if translate and re.search(r"[\u0400-\u04FF]", prompt):
            try:
                translator = translate.Client()
                prompt = translator.translate(prompt, target_language="en")["translatedText"]
                logger.info(f"🌐 Prompt translated to English for Imagen: '{original_prompt[:50]}...' -> '{prompt[:50]}...'")
            except Exception as te:
                logger.warning(f"⚠️ Failed to translate prompt '{original_prompt[:50]}...': {te}. Using original text.")

        logger.info(f"🔧 Initializing Vertex AI - Project: {VERTEX_PROJECT}, Location: {VERTEX_LOCATION}")
        aiplatform.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
        endpoint = _get_model_path()
        logger.info(f"🎯 Using endpoint: {endpoint}")
        
        prediction_client = PredictionServiceClient()
        instance = {"prompt": prompt}
        parameters = {"sampleCount": 1}
        
        logger.info("📡 Sending request to Vertex AI Imagen...")
        response = prediction_client.predict(
            endpoint=endpoint,
            instances=[instance],
            parameters=parameters
        )
        
        if not response.predictions:
            logger.error("❌ No predictions returned from Vertex Imagen.")
            raise Exception("No predictions returned from Vertex AI Imagen")
            
        if len(response.predictions) == 0:
            logger.error("❌ Empty predictions array from Vertex Imagen.")
            raise Exception("Empty predictions array from Vertex AI Imagen")
            
        prediction = response.predictions[0]
        logger.info(f"✅ Received prediction with keys: {list(prediction.keys())}")
        
        if "bytesBase64Encoded" not in prediction:
            logger.error(f"❌ No bytesBase64Encoded in prediction. Available keys: {list(prediction.keys())}")
            raise Exception("No bytesBase64Encoded field in Vertex AI response")
            
        image_b64 = prediction["bytesBase64Encoded"]
        logger.info(f"📸 Received base64 image data, length: {len(image_b64)} characters")
        
        # Validate base64 string
        if not image_b64 or len(image_b64) < 100:
            logger.error(f"❌ Invalid base64 image data: length={len(image_b64)}")
            raise Exception("Invalid base64 image data from Vertex AI")
            
        image_bytes = base64.b64decode(image_b64)
        logger.info(f"✅ Successfully decoded image: {len(image_bytes)} bytes")
        
        # Validate image bytes
        if len(image_bytes) < 1000:  # PNG header is at least a few hundred bytes
            logger.error(f"❌ Suspiciously small image: {len(image_bytes)} bytes")
            raise Exception("Generated image is too small - likely corrupted")
            
        logger.info("🎉 Image generation completed successfully!")
        return image_bytes, image_b64
        
    except Exception as e:
        logger.error(f"❌ Vertex Imagen generation failed: {e}", exc_info=True)
        # Re-raise the exception instead of returning placeholder
        raise Exception(f"Image generation failed: {str(e)}")

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