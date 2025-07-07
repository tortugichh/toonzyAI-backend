"""ArtDirector agent – defines overall visual style.

The agent receives the *entire* script (title + scenes) and returns a style
configuration used later by prompt-composition logic.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from pydantic import BaseModel, Field

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ArtStyle(BaseModel):
    summary: str = Field(..., description="Short description of the art style")
    positive_keywords: str = Field(
        ..., description="Comma-separated keywords to *include* in prompts"
    )
    negative_keywords: str = Field(
        ..., description="Comma-separated keywords to *avoid*"
    )

    class Config:  # noqa: D106
        extra = "ignore"


class ArtDirectorOutput(BaseModel):
    style: ArtStyle


class ArtDirector(BaseAgent):
    """Generate visual style guidance."""

    async def run(self, script: Dict[str, Any]) -> ArtDirectorOutput:  # type: ignore[override]
        system_prompt = (
            "You are an experienced art director for animated films. "
            "Given the JSON script below, define a consistent visual style. "
            "Return ONLY JSON in the following schema:\n"
            "{\n"
            "  'style': {\n"
            "    'summary': str,\n"
            "    'positive_keywords': str,\n"
            "    'negative_keywords': str\n"
            "  }\n"
            "}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"SCRIPT:\n```json\n{json.dumps(script, ensure_ascii=False)}\n```",
            },
        ]

        logger.info("ArtDirector: requesting LLM for style")
        raw = await self.chat(messages)

        # Robust JSON parsing similar to Scriptwriter
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                logger.error("ArtDirector output missing JSON block")
                raise ValueError("LLM did not return JSON")

            data = json.loads(match.group(0))

        try:
            return ArtDirectorOutput.model_validate(data)
        except Exception as e:
            logger.warning("ArtDirector validation failed: %s", e)
            # Attempt to coerce minimal structure
            style_raw = data.get("style", {}) if isinstance(data, dict) else {}
            coerced = {
                "summary": style_raw.get("summary", ""),
                "positive_keywords": style_raw.get("positive_keywords", ""),
                "negative_keywords": style_raw.get("negative_keywords", ""),
            }
            return ArtDirectorOutput(style=ArtStyle.model_validate(coerced)) 