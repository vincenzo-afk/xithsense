"""
OpenAI-compatible chat-completions client (used for Groq and OpenAI).

Talks to `/chat/completions` directly over httpx with native function calling, so no SDK
is required and both providers share one code path.
"""
from __future__ import annotations

import json
from typing import List, Optional

import httpx

from backend.config import settings
from llm.providers.base import ChatTurn, LLMProvider, ToolCall, parse_arguments


class OpenAICompatProvider(LLMProvider):
    supports_tools = True
    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: Optional[str], model: str, timeout: float = 40.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    # ── message conversion ────────────────────────────────────────────────
    @staticmethod
    def _to_wire(messages: List[dict], system: Optional[str]) -> List[dict]:
        out: List[dict] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            role = m.get("role")
            if role == "assistant" and m.get("tool_calls"):
                out.append({
                    "role": "assistant",
                    "content": m.get("content") or None,
                    "tool_calls": [{
                        "id": tc["id"], "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc.get("arguments") or {})},
                    } for tc in m["tool_calls"]],
                })
            elif role == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": str(m.get("content") or "")})
            else:
                out.append({"role": role, "content": m.get("content") or ""})
        return out

    @staticmethod
    def _tools_wire(tools: Optional[List[dict]]) -> Optional[List[dict]]:
        if not tools:
            return None
        return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                                  "parameters": t.get("parameters") or {"type": "object", "properties": {}}}}
                for t in tools]

    async def chat(self, messages: List[dict], tools: Optional[List[dict]] = None, system: Optional[str] = None,
                   max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> ChatTurn:
        if not self.api_key:
            raise RuntimeError(f"{self.name}: API key not configured")
        body = {
            "model": self.model,
            "messages": self._to_wire(messages, system),
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        }
        wire_tools = self._tools_wire(tools)
        if wire_tools:
            body["tools"] = wire_tools
            body["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=body,
                                  headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        if r.status_code >= 400:
            detail = r.text[:300]
            raise RuntimeError(f"{self.name} {r.status_code}: {detail}")
        data = r.json()
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        calls = [ToolCall(id=tc.get("id") or f"call_{i}", name=tc["function"]["name"],
                          arguments=parse_arguments(tc["function"].get("arguments")))
                 for i, tc in enumerate(msg.get("tool_calls") or []) if tc.get("function")]
        return ChatTurn(text=msg.get("content"), tool_calls=calls, raw=data)
