"""Celery tasks that wrap multi-agent pipeline (Director → other agents).

For MVP we run agents sequentially. In future this can be parallelised with
Celery canvases (group / chord).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict

from celery import shared_task

from utils.celery_app import celery_app
from agents.director import Director
from agents.art_director import ArtDirector
from agents.character import CharacterAgent
from agents.environment import EnvironmentAgent
from agents.illustration import IllustrationAgent

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Определяет язык текста на основе присутствия кириллицы."""
    if re.search(r"[\u0400-\u04FF]", text):
        return "russian"
    return "english"


@celery_app.task(name="tasks.agent_tasks.generate_story", bind=True, max_retries=2)
def generate_story(self, story_data: dict) -> Dict[str, Any]:
    """Celery task entrypoint – orchestrates the full MAS up to prompt parts.

    Args:
        story_data: dict with fields from StoryCreateRequest.
    Returns:
        Dict with keys: script, style, characters, environments.
    """
    try:
        # Определяем язык на основе содержимого формы
        all_text = ""
        for field in ["prompt", "genre", "style", "theme", "book_style", "wishes"]:
            if story_data.get(field):
                all_text += " " + str(story_data[field])
        
        # Добавляем текст персонажей
        if story_data.get("characters"):
            for char in story_data["characters"]:
                if char.get("name"):
                    all_text += " " + char["name"]
                if char.get("description"):
                    all_text += " " + char["description"]
                if char.get("role"):
                    all_text += " " + char["role"]
        
        language = detect_language(all_text)
        logger.info(f"🌐 Detected language: {language} from text: {all_text[:100]}...")

        # Собираем строку prompt из структурированных полей
        prompt_parts = []
        if story_data.get("prompt"):
            prompt_parts.append(f"Prompt: {story_data['prompt']}")
        if story_data.get("genre"):
            prompt_parts.append(f"Genre: {story_data['genre']}")
        if story_data.get("style"):
            prompt_parts.append(f"Style: {story_data['style']}")
        if story_data.get("theme"):
            prompt_parts.append(f"Theme: {story_data['theme']}")
        if story_data.get("book_style"):
            prompt_parts.append(f"Book style: {story_data['book_style']}")
        if story_data.get("wishes"):
            prompt_parts.append(f"Wishes: {story_data['wishes']}")
        if story_data.get("characters"):
            chars = story_data["characters"]
            if chars:
                char_str = "; ".join([
                    f"{c.get('name', '')} ({c.get('role', '')}): {c.get('description', '')}" for c in chars
                ])
                prompt_parts.append(f"Characters: {char_str}")
        user_prompt = " | ".join(prompt_parts)

        logger.info("🎬 [MAS] Starting story generation for structured input: %s", user_prompt)

        # Manage event loop similar to other tasks
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_run_agents_async(user_prompt, language))
        logger.info("✅ [MAS] Story generation finished")
        return result

    except Exception as exc:
        logger.exception("❌ [MAS] Error: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _run_agents_async(user_prompt: str, language: str) -> Dict[str, Any]:  # noqa: D401
    """Async helper that runs agents sequentially."""
    director = Director(language=language)
    director_out = await director.run(user_prompt)

    script_dict = director_out.script

    art_dir = ArtDirector(language=language)
    art_out = await art_dir.run(script_dict)

    char_agent = CharacterAgent(language=language)
    char_out = await char_agent.run(script_dict)

    env_agent = EnvironmentAgent(language=language)
    env_out = await env_agent.run(script_dict)

    # Generate illustrations using the script and style information
    try:
        logger.info("🎨 [MAS] Starting illustration generation...")
        illustration_agent = IllustrationAgent(language=language)
        illustration_out = await illustration_agent.run({
            "script": script_dict,
            "style": art_out.style.model_dump(),
            "characters": char_out.characters,
            "environments": env_out.environments
        })
        logger.info("✅ [MAS] Illustration generation completed")
    except Exception as e:
        logger.warning("⚠️ [MAS] Illustration generation failed: %s", e)
        illustration_out = {"illustrations": []}

    return {
        "script": script_dict,
        "style": art_out.style.model_dump(),
        "characters": char_out.model_dump(),
        "environments": env_out.model_dump(),
        "illustrations": illustration_out
    } 