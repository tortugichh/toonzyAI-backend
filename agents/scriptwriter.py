"""Scriptwriter agent – turns a high-level idea into a structured scenario.

Output schema follows::

    {
        "title": "...",
        "scenes": [
            {"id": 1, "description": "..."},
            {"id": 2, "description": "..."}
        ]
    }

Later we may extend with timing, camera, emotions, etc.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List

from pydantic import BaseModel, Field, validator

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models – relaxed to be tolerant to LLM quirks
# ---------------------------------------------------------------------------

class Scene(BaseModel):
    """Single scene block. Accepts id as int or numeric string."""

    id: int = Field(..., gt=0)
    description: str

    # Allow "1"-style ids
    @validator("id", pre=True)
    def _convert_id(cls, v):  # noqa: D401, ANN001
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    class Config:  # noqa: D106
        extra = "ignore"


class ScriptwriterOutput(BaseModel):
    title: str
    scenes: List[Scene]

    class Config:  # noqa: D106
        extra = "ignore"


class Scriptwriter(BaseAgent):
    """Generate a story script using LLM."""

    async def run(self, user_prompt: str) -> ScriptwriterOutput:  # type: ignore[override]
        system_prompt = (
            "You are a professional animation script writer. "
            "Given a short idea, expand it into a concise JSON script. "
            "Return *only* valid JSON, no markdown, no explanations. "
            "The JSON schema:\n"
            "{\n"
            "  \"title\": str,\n"
            "  \"scenes\": [\n"
            "    { \"id\": int, \"description\": str }\n"
            "  ]\n"
            "}\n"
            "Limit the script to 5 scenes maximum."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("Scriptwriter: requesting LLM for prompt")
        raw = await self.chat(messages)

        logger.debug("Scriptwriter LLM raw output: %s", raw)

        # ------------------------------------------------------------------
        # Robust JSON extraction/parsing
        # ------------------------------------------------------------------
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                logger.error("LLM output did not contain JSON block")
                raise ValueError("LLM did not return valid JSON")

            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON after extraction: %s", e)
                raise ValueError("LLM JSON extraction failed") from e

        # Validate but allow extra fields
        try:
            return ScriptwriterOutput.model_validate(data)
        except Exception as e:
            logger.warning("Validation failed: %s – returning raw data", e)
            # Fallback – coerce scenes list if possible
            title = data.get("title", "Untitled")
            scenes_raw = data.get("scenes", [])
            scenes = []
            for idx, s in enumerate(scenes_raw, 1):
                if isinstance(s, dict):
                    scenes.append(Scene.model_validate({
                        "id": s.get("id", idx),
                        "description": s.get("description", "")
                    }))
            return ScriptwriterOutput(title=title, scenes=scenes) 