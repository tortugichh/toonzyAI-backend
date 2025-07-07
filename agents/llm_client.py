"""Unified LLM access layer for ToonzyAI agents.

If the app runs inside a GCP project (detected by presence of
``GOOGLE_CLOUD_PROJECT``), we default to Vertex AI Chat models.
Otherwise we fall back to the free Gemini API-key flow via Google AI Studio.

Usage:
    llm = LLMClient(model_name="gemini-pro")
    response = llm.chat([
        {"role": "user", "content": "Hello!"}
    ])
"""
from __future__ import annotations

import os
from functools import cached_property
from typing import List, Sequence


class LLMClient:  # noqa: D101
    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> None:
        # Use supported default model; override via GEMINI_MODEL_NAME env.
        self.model_name = model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        # Decide backend
        self._use_vertex = bool(os.getenv("GOOGLE_CLOUD_PROJECT"))

    # ------------------------------------------------------------------
    # Lazy-initialised backends
    # ------------------------------------------------------------------
    @cached_property
    def _vertex_llm(self):
        """Vertex AI chat backend (requires service-account credentials)."""
        from langchain_google_vertexai import ChatVertexAI  # local import

        return ChatVertexAI(
            model_name=self.model_name,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )

    @cached_property
    def _studio_llm(self):
        """Gemini via AI Studio API-key backend."""
        import google.generativeai as genai  # type: ignore
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(self, messages: Sequence[dict], **kwargs):  # noqa: D401, ANN001
        """Send a chat completion request and return the assistant message."""
        prompt = "\n".join(m["content"] for m in messages)
        if self._use_vertex:
            return self._vertex_llm.invoke(prompt, **kwargs).content
        return self._studio_llm.invoke(prompt, **kwargs).content 