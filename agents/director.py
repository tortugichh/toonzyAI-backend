"""Director agent – orchestrates the full animation workflow.

For the first milestone the Director will:
1. Receive a *high-level* user prompt.
2. Invoke the Scriptwriter agent to obtain a structured script.
3. Return the script so that downstream Celery tasks can continue.

Later we will extend this class to spawn parallel tasks for Character / Environment / Art-Director and then Generation & Assembly.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from .base_agent import BaseAgent

# Import inside try/except for now – Scriptwriter may not yet exist.
try:
    from .scriptwriter import Scriptwriter  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    Scriptwriter = None  # type: ignore

logger = logging.getLogger(__name__)


class DirectorOutput(BaseModel):
    """Minimal output of Director for MVP."""

    script: dict[str, Any]


class Director(BaseAgent):
    """Top-level orchestrator agent."""

    async def run(self, user_prompt: str) -> DirectorOutput:  # type: ignore[override]
        logger.info("Director: received prompt: %s", user_prompt)

        if Scriptwriter is None:
            raise ImportError(
                "Scriptwriter agent is not yet implemented."
            )

        # 1. Generate script with language support
        scriptwriter = Scriptwriter(llm=self.llm, language=self.language)
        script_data = await scriptwriter.run(user_prompt)

        # 2. Return structured result (will be enriched later)
        return DirectorOutput(script=script_data.model_dump()) 