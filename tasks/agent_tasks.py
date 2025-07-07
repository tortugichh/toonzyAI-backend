"""Celery tasks that wrap multi-agent pipeline (Director → other agents).

For MVP we run agents sequentially. In future this can be parallelised with
Celery canvases (group / chord).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from celery import shared_task

from utils.celery_app import celery_app
from agents.director import Director
from agents.art_director import ArtDirector
from agents.character import CharacterAgent
from agents.environment import EnvironmentAgent

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.agent_tasks.generate_story", bind=True, max_retries=2)
def generate_story(self, user_prompt: str) -> Dict[str, Any]:
    """Celery task entrypoint – orchestrates the full MAS up to prompt parts.

    Args:
        user_prompt: High-level idea from user.
    Returns:
        Dict with keys: script, style, characters, environments.
    """
    try:
        logger.info("🎬 [MAS] Starting story generation for prompt: %s", user_prompt)

        # Manage event loop similar to other tasks
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_run_agents_async(user_prompt))
        logger.info("✅ [MAS] Story generation finished")
        return result

    except Exception as exc:
        logger.exception("❌ [MAS] Error: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _run_agents_async(user_prompt: str) -> Dict[str, Any]:  # noqa: D401
    """Async helper that runs agents sequentially."""
    director = Director()
    director_out = await director.run(user_prompt)

    script_dict = director_out.script

    art_dir = ArtDirector()
    art_out = await art_dir.run(script_dict)

    char_agent = CharacterAgent()
    char_out = await char_agent.run(script_dict)

    env_agent = EnvironmentAgent()
    env_out = await env_agent.run(script_dict)

    return {
        "script": script_dict,
        "style": art_out.model_dump(),
        "characters": char_out.model_dump(),
        "environments": env_out.model_dump(),
    } 