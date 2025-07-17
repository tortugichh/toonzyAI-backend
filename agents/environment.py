"""Environment agent – designs backgrounds for each scene."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SceneEnvironment(BaseModel):
    scene_id: int
    environment_description: str

    class Config:  # noqa: D106
        extra = "ignore"


class EnvironmentAgentOutput(BaseModel):
    environments: List[SceneEnvironment]


class EnvironmentAgent(BaseAgent):
    async def run(self, script: Dict[str, Any]) -> EnvironmentAgentOutput:  # type: ignore[override]
        language_instruction = self.get_language_instruction()
        
        system_prompt = (
            "You are a background artist. For each scene in the script produce a concise environment description (lighting, setting, mood). "
            "Return JSON with key 'environments': list of objects {scene_id, environment_description}.\n"
            f"{language_instruction}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "SCRIPT:\n```json\n" + json.dumps(script, ensure_ascii=False) + "\n```",
            },
        ]

        raw = await self.chat(messages)

        # Robust JSON extraction – handle array or object
        raw_clean = raw.strip()
        try:
            data = json.loads(raw_clean)
        except json.JSONDecodeError:
            import re

            # Try to capture {...}
            match_obj = re.search(r"\{.*\}", raw_clean, re.DOTALL)
            if match_obj:
                data = json.loads(match_obj.group(0))
            else:
                # Try to capture [...] and wrap
                match_arr = re.search(r"\[.*\]", raw_clean, re.DOTALL)
                if not match_arr:
                    logger.error("EnvironmentAgent output missing JSON block")
                    raise ValueError("LLM did not return JSON")

                environments = json.loads(match_arr.group(0))
                data = {"environments": environments}

        try:
            return EnvironmentAgentOutput.model_validate(data)
        except Exception as e:
            logger.warning("EnvironmentAgent validation failed: %s", e)
            env_list = data.get("environments", []) if isinstance(data, dict) else []
            coerced_envs = []
            for idx, env in enumerate(env_list, 1):
                if isinstance(env, dict):
                    coerced_envs.append(SceneEnvironment.model_validate({
                        "scene_id": env.get("scene_id", idx),
                        "environment_description": env.get("environment_description", "A generic background")
                    }))
            return EnvironmentAgentOutput(environments=coerced_envs) 