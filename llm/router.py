"""
LLM Router: pick the provider from LLM_PROVIDER (groq | anthropic | openai | google).

LLM_MODEL overrides the provider's default model when set.
"""
from __future__ import annotations

from typing import Optional

from backend.config import settings
from llm.providers.base import LLMProvider

PROVIDERS = ("groq", "anthropic", "openai", "google")

_KEY_FOR = {
    "groq": lambda: settings.GROQ_API_KEY,
    "anthropic": lambda: settings.ANTHROPIC_API_KEY,
    "openai": lambda: settings.OPENAI_API_KEY,
    "google": lambda: settings.GOOGLE_API_KEY,
}


def provider_name() -> str:
    return (settings.LLM_PROVIDER or "").lower().strip()


def llm_available(provider: Optional[str] = None) -> bool:
    """True when the configured provider has a usable key (placeholder values like 'sk-...' don't count)."""
    p = provider or provider_name()
    getter = _KEY_FOR.get(p)
    key = getter() if getter else None
    return bool(key) and not str(key).endswith("...") and len(str(key)) > 8


def _model_family(model: str) -> Optional[str]:
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    if m.startswith("gemini"):
        return "google"
    return None            # llama / mixtral / gemma / qwen … → Groq or any OpenAI-compatible host


def model_override(provider: str) -> Optional[str]:
    """LLM_MODEL only applies when it belongs to the selected provider's family, so switching
    LLM_PROVIDER never sends a Claude model name to Groq (or vice versa)."""
    m = (settings.LLM_MODEL or "").strip()
    if not m:
        return None
    fam = _model_family(m)
    if fam is None:
        return m if provider in ("groq", "openai") else None
    return m if fam == provider else None


def get_llm_provider(provider: Optional[str] = None) -> LLMProvider:
    """Return the configured provider instance."""
    p = provider or provider_name()
    model = model_override(p)
    if p == "groq":
        from llm.providers.groq_provider import GroqProvider
        return GroqProvider(model)
    if p == "anthropic":
        from llm.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(model)
    if p == "openai":
        from llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(model)
    if p == "google":
        from llm.providers.google_provider import GoogleProvider
        return GoogleProvider(model)
    raise ValueError(f"Unknown LLM_PROVIDER: {p!r}. Use one of {', '.join(PROVIDERS)}")
