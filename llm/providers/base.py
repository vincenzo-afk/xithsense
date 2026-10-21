"""
Provider-neutral chat types.

Messages use one shape for every backend:
    {"role": "user", "content": "..."}
    {"role": "assistant", "content": "..." | None, "tool_calls": [{"id", "name", "arguments": {...}}]}
    {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}

Tools are described with JSON schema:
    {"name": "...", "description": "...", "parameters": {"type": "object", "properties": {...}, "required": [...]}}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatTurn:
    text: Optional[str]
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


def parse_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"value": value}
    except (TypeError, ValueError):
        return {"_raw": str(raw)}


class LLMProvider:
    """Interface every provider implements. `supports_tools` tells the agent whether to use
    native function calling or the JSON fallback protocol."""

    name = "base"
    supports_tools = False

    async def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None,
                       history: Optional[list] = None) -> str:
        turn = await self.chat(list(history or []) + [{"role": "user", "content": prompt}], tools=None,
                               system=system, max_tokens=max_tokens)
        return turn.text or ""

    async def chat(self, messages: List[dict], tools: Optional[List[dict]] = None, system: Optional[str] = None,
                   max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> ChatTurn:
        raise NotImplementedError
