"""
LLM Router: select the appropriate provider based on LLM_PROVIDER env var.
"""
from __future__ import annotations

from backend.config import settings


def get_llm_provider():
    """Return the configured LLM provider instance."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "anthropic":
        from llm.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    elif provider == "openai":
        from llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "google":
        from llm.providers.google_provider import GoogleProvider
        return GoogleProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'anthropic', 'openai', or 'google'")
