"""OpenAI GPT LLM provider."""
from __future__ import annotations
from backend.config import settings


class OpenAIProvider:
    async def complete(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[LLM unavailable: {e}]"
