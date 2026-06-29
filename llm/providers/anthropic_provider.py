"""Anthropic Claude LLM provider."""
from __future__ import annotations
from backend.config import settings


class AnthropicProvider:
    async def complete(self, prompt: str) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            message = client.messages.create(
                model=settings.LLM_MODEL or "claude-sonnet-4-6",
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            return f"[LLM unavailable: {e}]"
