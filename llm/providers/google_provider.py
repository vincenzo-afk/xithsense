"""Google Gemini provider (text only — the agent uses its JSON tool protocol with this backend)."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from backend.config import settings
from llm.providers.base import ChatTurn, LLMProvider

DEFAULT_MODEL = "gemini-2.0-flash"


class GoogleProvider(LLMProvider):
    name = "google"
    supports_tools = False

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_MODEL

    async def chat(self, messages: List[dict], tools: Optional[List[dict]] = None, system: Optional[str] = None,
                   max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> ChatTurn:
        import google.generativeai as genai
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("google: API key not configured")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(self.model, system_instruction=system)
        transcript = []
        for m in messages:
            if m.get("role") == "tool":
                transcript.append(f"tool[{m.get('name')}]: {m.get('content')}")
            else:
                transcript.append(f"{m.get('role')}: {m.get('content') or ''}")
        response = await asyncio.to_thread(
            model.generate_content, "\n".join(transcript),
            generation_config={"max_output_tokens": max_tokens or settings.LLM_MAX_TOKENS,
                               "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature})
        return ChatTurn(text=response.text, raw=response)
