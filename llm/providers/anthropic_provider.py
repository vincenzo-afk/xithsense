"""Anthropic Claude LLM provider."""
from __future__ import annotations

from typing import Optional

from backend.config import settings


class AnthropicProvider:
    async def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None,
                       history: Optional[list] = None) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        messages = list(history or []) + [{"role": "user", "content": prompt}]
        kwargs = {"system": system} if system else {}
        message = await client.messages.create(
            model=settings.LLM_MODEL or "claude-sonnet-5-5",
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            messages=messages,
            **kwargs,
        )
        return "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
