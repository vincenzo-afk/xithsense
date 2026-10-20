"""OpenAI GPT LLM provider."""
from __future__ import annotations

from typing import Optional

from backend.config import settings


class OpenAIProvider:
    async def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None,
                       history: Optional[list] = None) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages = ([{"role": "system", "content": system}] if system else []) + list(history or [])
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL if settings.LLM_MODEL.startswith("gpt") else "gpt-4o",
            messages=messages,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        return response.choices[0].message.content or ""
