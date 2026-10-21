"""Anthropic Claude provider with native tool use."""
from __future__ import annotations

from typing import List, Optional

from backend.config import settings
from llm.providers.base import ChatTurn, LLMProvider, ToolCall

DEFAULT_MODEL = "claude-sonnet-5-5"


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    supports_tools = True

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_MODEL

    @staticmethod
    def _to_wire(messages: List[dict]) -> List[dict]:
        """Neutral → Anthropic blocks. Consecutive tool results merge into one user message."""
        out: List[dict] = []
        for m in messages:
            role = m.get("role")
            if role == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls") or []:
                    blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc.get("arguments") or {}})
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            elif role == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": str(m.get("content") or "")}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) \
                        and out[-1]["content"] and out[-1]["content"][0].get("type") == "tool_result":
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            else:
                out.append({"role": "user", "content": m.get("content") or ""})
        return out

    async def chat(self, messages: List[dict], tools: Optional[List[dict]] = None, system: Optional[str] = None,
                   max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> ChatTurn:
        import anthropic
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("anthropic: API key not configured")
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        kwargs = {}
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [{"name": t["name"], "description": t.get("description", ""),
                                "input_schema": t.get("parameters") or {"type": "object", "properties": {}}} for t in tools]
        resp = await client.messages.create(
            model=self.model, max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
            messages=self._to_wire(messages), **kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text") or None
        calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input or {}))
                 for b in resp.content if getattr(b, "type", "") == "tool_use"]
        return ChatTurn(text=text, tool_calls=calls, raw=resp)
