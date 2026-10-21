"""OpenAI GPT provider (shares the OpenAI-compatible client with Groq)."""
from __future__ import annotations

from backend.config import settings
from llm.providers.openai_compat import OpenAICompatProvider

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"

    def __init__(self, model: str | None = None):
        super().__init__(base_url="https://api.openai.com/v1", api_key=settings.OPENAI_API_KEY,
                         model=model or DEFAULT_MODEL)
