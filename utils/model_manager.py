import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image
import io
import base64
from typing import Optional, Tuple
import logging
from huggingface_hub import login
import requests

login(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))


MODEL_CACHE_DIR = Path("models")
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

logger = logging.getLogger(__name__)

# Функциональный стиль: кэшируем pipeline, warmup, torch.compile.




_pipeline: Optional[StableDiffusionXLPipeline] = None
_initialized: bool = False


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
        # torch.compile (PyTorch 2.0+) — не используем на CPU, вызывает ошибки
        # try:
        #     pipe.unet = torch.compile(pipe.unet)
        #     logger.info("UNet compiled with torch.compile")
        # except Exception as e:
        #     logger.warning(f"torch.compile not available or failed: {e}")
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


def generate_image(prompt: str) -> Tuple[bytes, str]:
    api_key = os.getenv("STABILITY_API_KEY")
    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/png"
    }
    data = {
        "prompt": prompt,
        "output_format": "png"
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            image_bytes = response.content
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return image_bytes, image_base64
        else:
            logging.error(f"Stability API error: {response.status_code} {response.text}")
            return _create_placeholder_image()
    except Exception as e:
        logging.error(f"Image generation failed: {e}")
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