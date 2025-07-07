"""Character agent – ensures consistent avatar / character prompts."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CharacterInfo(BaseModel):
    name: str
    description: str | None = ""
    attire: str | None = ""

    class Config:  # noqa: D106
        extra = "ignore"


class CharacterAgentOutput(BaseModel):
    characters: List[CharacterInfo]


class CharacterAgent(BaseAgent):
    async def run(self, script: Dict[str, Any]) -> CharacterAgentOutput:  # type: ignore[override]
        system_prompt = (
            "You are responsible for character design consistency. "
            "Given the animation script, identify every distinct CHARACTER. "
            "For each character return: \n"
            "  • name – string\n  • description – 1 short sentence describing appearance/personality (cannot be empty)\n"
            "  • attire – typical clothes/accessories or 'N/A' if none (cannot be empty).\n"
            "Respond ONLY with valid JSON: {\"characters\": [{...}]}. No markdown fences."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "SCRIPT:\n```json\n" + json.dumps(script, ensure_ascii=False) + "\n```",
            },
        ]

        raw = await self.chat(messages)

        # Robust JSON extraction
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                logger.error("CharacterAgent output missing JSON block")
                raise ValueError("LLM did not return JSON")

            data = json.loads(match.group(0))

        try:
            return CharacterAgentOutput.model_validate(data)
        except Exception as e:
            logger.warning("CharacterAgent validation failed: %s", e)
            char_list = data.get("characters", []) if isinstance(data, dict) else []
            coerced_chars = []
            for c in char_list:
                if isinstance(c, dict):
                    desc = (
                        c.get("description")
                        or c.get("short_appearance")
                        or c.get("appearance")
                        or c.get("summary")
                        or c.get("Description")
                        or ""
                    )
                    coerced_chars.append(CharacterInfo.model_validate({
                        "name": c.get("name", c.get("Name", "Unnamed")),
                        "description": desc,
                        "attire": c.get("attire", c.get("Attire", ""))
                    }))
            return CharacterAgentOutput(characters=coerced_chars) 