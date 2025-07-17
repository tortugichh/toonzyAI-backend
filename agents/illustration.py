"""Illustration agent – generates image prompts and creates illustrations for story scenes.

This agent takes the script and style information to create visual prompts
for each scene, then generates actual images using Vertex AI Imagen.
"""
from __future__ import annotations

import json
import logging
import base64
from typing import Any, Dict, List
from pydantic import BaseModel

from .base_agent import BaseAgent
from utils.model_manager import generate_image
from utils.gcs_client import upload_image_to_gcs

logger = logging.getLogger(__name__)


class SceneIllustration(BaseModel):
    """Single scene illustration data."""
    scene_id: int
    image_prompt: str
    image_url: str | None = None
    

class IllustrationAgentOutput(BaseModel):
    """Output from the Illustration Agent."""
    illustrations: List[SceneIllustration]


class IllustrationAgent(BaseAgent):
    """Generate image prompts and create illustrations for each scene."""

    async def run(self, data: Dict[str, Any]) -> IllustrationAgentOutput:  # type: ignore[override]
        """Generate illustrations for each scene in the script."""
        
        # Извлекаем данные из переданного словаря
        script = data.get("script", {})
        style = data.get("style", {})
        
        logger.info("🎨 IllustrationAgent: Starting run method")
        logger.info("🎨 Script keys: %s", list(script.keys()))
        logger.info("🎨 Style keys: %s", list(style.keys()))
        
        # Получаем языковую инструкцию
        language_instruction = self.get_language_instruction()
        
        # Extract style information
        art_style = style.get("style", style)  # Поддерживаем оба формата
        style_summary = art_style.get("summary", "")
        positive_keywords = art_style.get("positive_keywords", "")
        
        logger.info("🎨 Style summary: %s", style_summary[:100])
        logger.info("🎨 Positive keywords: %s", positive_keywords[:100])
        
        system_prompt = (
            "You are a professional children's book illustrator. "
            "Given a script and art style, create detailed image prompts for each scene. "
            "Each prompt should be vivid, descriptive, and suitable for generating beautiful illustrations. "
            f"Art style guidance: {style_summary}. "
            f"Style keywords: {positive_keywords}. "
            "Return ONLY valid JSON with this schema:\n"
            "{\n"
            "  \"scene_prompts\": [\n"
            "    {\n"
            "      \"scene_id\": int,\n"
            "      \"image_prompt\": \"detailed description for illustration\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            f"{language_instruction}"
        )

        user_prompt = f"""
        Script: {json.dumps(script, ensure_ascii=False)}
        Art Style: {json.dumps(art_style, ensure_ascii=False)}
        
        Create detailed image prompts for each scene.
        """

        logger.info("🎨 IllustrationAgent: Requesting LLM for image prompts")
        try:
            response = await self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            logger.info("🎨 LLM response received: %s", response[:200])
        except Exception as llm_error:
            logger.error("❌ LLM request failed: %s", llm_error, exc_info=True)
            raise

        # Parse JSON response (handle markdown code blocks)
        try:
            logger.info("🎨 Parsing JSON response...")
            
            # Extract JSON from markdown code block if present
            json_content = response.strip()
            if json_content.startswith("```json"):
                # Find the JSON content between ```json and ```
                start_marker = "```json"
                end_marker = "```"
                start_index = json_content.find(start_marker) + len(start_marker)
                end_index = json_content.find(end_marker, start_index)
                if end_index != -1:
                    json_content = json_content[start_index:end_index].strip()
                    logger.info("🎨 Extracted JSON from markdown block")
                else:
                    logger.warning("⚠️ Found ```json but no closing ```, using full response")
            elif json_content.startswith("```") and json_content.endswith("```"):
                # Handle generic code block
                json_content = json_content[3:-3].strip()
                logger.info("🎨 Extracted JSON from generic code block")
            
            response_data = json.loads(json_content)
            scene_prompts = response_data.get("scene_prompts", [])
            logger.info("🎨 Found %d scene prompts", len(scene_prompts))
        except json.JSONDecodeError as parse_error:
            logger.error("❌ Failed to parse JSON response: %s", parse_error)
            logger.error("❌ Raw response: %s", response)
            logger.error("❌ Processed content: %s", json_content if 'json_content' in locals() else 'N/A')
            raise

        # Generate actual images for each scene
        illustrations = []
        for i, scene_prompt in enumerate(scene_prompts):
            try:
                logger.info("🎨 Generating image %d/%d: %s", i+1, len(scene_prompts), scene_prompt["image_prompt"][:50])
                
                # Add delay between requests to avoid rate limits
                if i > 0:
                    import asyncio
                    await asyncio.sleep(2)  # 2 second delay between requests
                
                # Generate image using Vertex AI Imagen
                image_bytes, image_base64 = generate_image(scene_prompt["image_prompt"])
                logger.info("✅ Image generated successfully, size: %d bytes", len(image_bytes))
                
                # Upload to GCS
                logger.info("🎨 Uploading image to GCS...")
                image_filename = f"illustrations/scene_{scene_prompt['scene_id']}_{hash(scene_prompt['image_prompt']) % 10000}.png"
                image_url = upload_image_to_gcs(image_bytes, image_filename)
                logger.info("✅ Image uploaded to GCS: %s", image_url)
                
                illustration = SceneIllustration(
                    scene_id=scene_prompt["scene_id"],
                    image_prompt=scene_prompt["image_prompt"],
                    image_url=image_url
                )
                illustrations.append(illustration)
                logger.info("✅ Illustration %d completed", i+1)
                
            except Exception as generation_error:
                logger.error("❌ Failed to generate illustration for scene %s: %s", 
                           scene_prompt.get("scene_id", "unknown"), generation_error, exc_info=True)
                # Continue with other scenes even if one fails
                continue

        logger.info("🎨 IllustrationAgent completed: %d illustrations generated", len(illustrations))
        return IllustrationAgentOutput(illustrations=illustrations) 