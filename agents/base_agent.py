from __future__ import annotations

import abc
import logging
from typing import Any, Dict, Optional

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base class for all agents.

    Each concrete agent must implement :meth:`run` and return a structured
    result (usually a Pydantic model or plain ``dict``) that can be passed to
    downstream tasks.
    """

    def __init__(self, llm: Optional[LLMClient] = None, **kwargs: Any) -> None:
        self.llm: LLMClient = llm or LLMClient()
        self.config: Dict[str, Any] = kwargs

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    async def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Convenience wrapper around :class:`LLMClient.chat`."""
        return self.llm.chat(messages, **kwargs)

    # ------------------------------------------------------------------
    # Required implementation
    # ------------------------------------------------------------------
    @abc.abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        """Run the agent and return its output."""
        raise NotImplementedError 