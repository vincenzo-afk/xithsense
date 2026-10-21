"""Groq (OpenAI-compatible endpoint, Llama / Mixtral / Gemma models, native tool calling)."""
from __future__ import annotations

from backend.config import settings
from llm.providers.openai_compat import OpenAICompatProvider

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(OpenAICompatProvider):
    name = "groq"

    def __init__(self, model: str | None = None):
        super().__init__(base_url=settings.GROQ_BASE_URL, api_key=settings.GROQ_API_KEY,
                         model=model or DEFAULT_MODEL)
