import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
from pathlib import Path
import torch
from PIL import Image
import io
import base64
from typing import Optional, Tuple
import logging
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from google.protobuf import json_format
import asyncio

logger = logging.getLogger(__name__)

# Функциональный стиль: кэшируем pipeline, warmup, torch.compile.




_pipeline: Optional[StableDiffusionXLPipeline] = None
_initialized: bool = False

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "projects/{project}/locations/{location}/publishers/google/models/imagen-4.0-generate-preview-06-06")


def ensure_model_downloaded() -> None:
    MODEL_CACHE_DIR.mkdir(exist_ok=True)




def get_pipeline() -> StableDiffusionXLPipeline:
    global _pipeline, _initialized
    if _pipeline is not None and _initialized:
        return _pipeline
    try:
        logger.info("Initializing SDXL 1.0 pipeline (CPU-only)...")
        ensure_model_downloaded()
        device = "cpu"
        torch_dtype = torch.float32
        pipe = StableDiffusionXLPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch_dtype
        )
        _pipeline = pipe
        _initialized = True
        logger.info(f"SDXL 1.0 pipeline initialized successfully on {device}")
        return _pipeline
    except Exception as e:
        logger.error(f"Failed to initialize SDXL 1.0 pipeline: {e}")
        raise


def warmup_pipeline() -> None:
    """Генерирует 1 изображение для прогрева пайплайна."""
    pipe = get_pipeline()
    prompt = "warmup"
    try:
        logger.info("Warming up Stable Diffusion pipeline...")
        pipe(prompt, num_inference_steps=2, guidance_scale=5.0, height=256, width=256)
        logger.info("Warmup complete.")
    except Exception as e:
        logger.warning(f"Warmup failed: {e}")


def _get_model_path() -> str:
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
        prediction_client = aiplatform.gapic.PredictionServiceClient()
        instance = {"prompt": prompt}
        instances = [instance]
        parameters = {"sampleCount": 1}
        response = prediction_client.predict(
            endpoint=endpoint,
            instances=[json_format.ParseDict(instance, predict.instance.ImageGenerationPredictionInstance())],
            parameters=json_format.ParseDict(parameters, predict.params.ImageGenerationPredictionParams())
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


def _image_to_bytes(image: Image.Image) -> bytes:
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='PNG')
    return img_byte_array.getvalue()


def _create_placeholder_image() -> Tuple[bytes, str]:
    img = Image.new('RGB', (512, 512), color='lightgray')
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_bytes = img_byte_array.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_bytes, img_base64

MODEL_CACHE_DIR = Path("models")
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

async def test_vertex_ai_connection() -> str:
    """Тестирует подключение к Vertex AI Imagen."""
    try:
        loop = asyncio.get_event_loop()
        # Используем run_in_executor для вызова sync функции generate_image
        image_bytes, image_b64 = await loop.run_in_executor(None, generate_image, "test connection")
        if image_bytes and image_b64:
            return "Vertex AI Imagen connection successful. Image generated."
        return "Vertex AI Imagen connection failed: no image returned."
    except Exception as e:
        return f"Vertex AI Imagen connection error: {str(e)}"