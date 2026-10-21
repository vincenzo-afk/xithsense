"""Unit tests for the cricket-only agent, the JSON tool protocol and the web research helpers."""
import asyncio
import json

import pytest

from llm import agent as A
from llm import tools as T
from llm.providers.base import ChatTurn, LLMProvider, ToolCall, parse_arguments
from llm.providers.openai_compat import OpenAICompatProvider
from integrations.web import cricket_query, extract_text, is_safe_url, parse_ddg_html


class ScriptedProvider(LLMProvider):
    """Replays a list of turns; records what it was asked."""
    name = "scripted"

    def __init__(self, turns, supports_tools=True):
        self.turns = list(turns)
        self.supports_tools = supports_tools
        self.calls = []

    async def chat(self, messages, tools=None, system=None, max_tokens=None, temperature=None):
        self.calls.append({"messages": list(messages), "tools": tools, "system": system})
        return self.turns.pop(0)


@pytest.fixture
def fake_tool(monkeypatch):
    seen = {}

    async def echo(ctx, **kw):
        seen.update(kw)
        ctx.used.append({"name": "echo", "summary": "echoed"})
        ctx.related.append("pid-1")
        return json.dumps({"ok": True, "args": kw})

    tool = T.Tool("echo", "echo tool", {"type": "object", "properties": {"x": {"type": "string"}}}, echo)
    monkeypatch.setattr(T, "TOOLS", [tool])
    monkeypatch.setattr(T, "TOOL_INDEX", {"echo": tool})
    return seen


def test_scope_filter():
    assert A.is_cricket_question("Who should be my captain today?")
    assert A.is_cricket_question("Is Bumrah fit?", ["JJ Bumrah"])
    assert not A.is_cricket_question("Write me a poem about the sea")
    assert not A.is_cricket_question("What's the capital of France?")


def test_native_tool_loop_executes_tools_and_returns_final(fake_tool):
    provider = ScriptedProvider([
        ChatTurn(text=None, tool_calls=[ToolCall(id="c1", name="echo", arguments={"x": "hello"})]),
        ChatTurn(text="**Verdict:** echoed hello."),
    ])
    res = asyncio.run(A.run_agent(None, None, "captain pick?", None, provider=provider))
    assert res.answer.startswith("**Verdict:**")
    assert fake_tool == {"x": "hello"}
    assert res.tools_used[0]["name"] == "echo" and res.related_player_ids == ["pid-1"]
    # second call carried the tool result back to the model
    roles = [m["role"] for m in provider.calls[1]["messages"]]
    assert roles[-2:] == ["assistant", "tool"]
    assert provider.calls[0]["tools"] and provider.calls[0]["tools"][0]["name"] == "echo"
    assert "ONLY discuss cricket" in provider.calls[0]["system"]


def test_json_protocol_for_providers_without_native_tools(fake_tool):
    provider = ScriptedProvider([
        ChatTurn(text='Sure. {"tool": "echo", "arguments": {"x": "via-json"}}'),
        ChatTurn(text='{"final": "Done — projections attached."}'),
    ], supports_tools=False)
    res = asyncio.run(A.run_agent(None, None, "best differentials?", None, provider=provider))
    assert res.answer == "Done — projections attached."
    assert fake_tool == {"x": "via-json"}
    assert provider.calls[0]["tools"] is None and "Tool protocol" in provider.calls[0]["system"]
    assert "[tool echo result]" in provider.calls[1]["messages"][-1]["content"]


def test_step_limit_forces_a_final_answer(fake_tool, monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "AGENT_MAX_STEPS", 2)
    provider = ScriptedProvider([
        ChatTurn(text=None, tool_calls=[ToolCall("c1", "echo", {})]),
        ChatTurn(text=None, tool_calls=[ToolCall("c2", "echo", {})]),
        ChatTurn(text="Final after limit."),
    ])
    res = asyncio.run(A.run_agent(None, None, "team?", None, provider=provider))
    assert res.answer == "Final after limit." and res.steps == 3
    assert provider.calls[-1]["tools"] is None      # last round may not call tools


def test_guardrails_block_betting_language(fake_tool):
    provider = ScriptedProvider([ChatTurn(text="Kohli is a sure thing, place a bet now.")])
    res = asyncio.run(A.run_agent(None, None, "captain?", None, provider=provider))
    assert res.answer == A.REFUSAL


def test_unknown_tool_and_premium_gate():
    ctx = T.ToolContext(db=None, user=None, match=None, premium=False)
    assert "Unknown tool" in asyncio.run(T.execute("nope", {}, ctx))
    assert "Premium" in asyncio.run(T.execute("build_team", {}, ctx))
    assert all(s["name"] not in ("build_team", "differentials") for s in T.specs(premium=False))
    assert all(s["name"] not in ("web_search", "fetch_page") for s in T.specs(web_enabled=False))


def test_openai_wire_format():
    msgs = [{"role": "user", "content": "hi"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "name": "echo", "arguments": {"x": 1}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "echo", "content": "{}"}]
    wire = OpenAICompatProvider._to_wire(msgs, "sys")
    assert wire[0] == {"role": "system", "content": "sys"}
    assert wire[2]["tool_calls"][0]["function"] == {"name": "echo", "arguments": '{"x": 1}'}
    assert wire[3] == {"role": "tool", "tool_call_id": "c1", "content": "{}"}
    assert OpenAICompatProvider._tools_wire([{"name": "a", "description": "d", "parameters": {"type": "object"}}])[0]["type"] == "function"
    assert parse_arguments('{"a": 1}') == {"a": 1} and parse_arguments("not json") == {"_raw": "not json"}


def test_anthropic_wire_merges_tool_results():
    from llm.providers.anthropic_provider import AnthropicProvider
    msgs = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "name": "x", "arguments": {}}, {"id": "b", "name": "y", "arguments": {}}]},
            {"role": "tool", "tool_call_id": "a", "name": "x", "content": "1"},
            {"role": "tool", "tool_call_id": "b", "name": "y", "content": "2"}]
    wire = AnthropicProvider._to_wire(msgs)
    assert [m["role"] for m in wire] == ["user", "assistant", "user"]
    assert [b["type"] for b in wire[1]["content"]] == ["tool_use", "tool_use"]
    assert [b["tool_use_id"] for b in wire[2]["content"]] == ["a", "b"]


def test_router_knows_groq(monkeypatch):
    from backend.config import settings
    from llm.router import get_llm_provider, llm_available
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_1234567890")
    p = get_llm_provider()
    assert p.name == "groq" and p.supports_tools and p.model == "llama-3.3-70b-versatile"
    assert p.base_url.startswith("https://api.groq.com/openai/v1")
    assert llm_available()
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-...")
    assert not llm_available()


# ── web helpers ───────────────────────────────────────────────────────────────

DDG_HTML = """
<div class="results">
 <div class="result results_links">
  <h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.espncricinfo.com%2Fstory%2Fbumrah-fit&amp;rut=abc">Bumrah declared fit</a></h2>
  <a class="result__snippet" href="#">Jasprit Bumrah has been declared fit for the series opener.</a>
 </div>
 <div class="result results_links">
  <h2 class="result__title"><a rel="nofollow" class="result__a" href="https://example.com/other">Other</a></h2>
 </div>
</div>"""


def test_parse_ddg_html_decodes_redirects():
    rows = parse_ddg_html(DDG_HTML)
    assert rows[0]["url"] == "https://www.espncricinfo.com/story/bumrah-fit"
    assert rows[0]["title"] == "Bumrah declared fit" and "declared fit" in rows[0]["snippet"]
    assert rows[1]["url"] == "https://example.com/other" and rows[1]["snippet"] == ""


def test_cricket_query_shaping():
    assert cricket_query("Bumrah injury update") == "Bumrah injury update cricket"
    assert cricket_query("IPL playing XI CSK") == "IPL playing XI CSK"


def test_extract_text_strips_chrome():
    title, text = extract_text("<html><head><title>Pitch report</title></head><body><nav>menu</nav>"
                               "<article><p>The surface at Chepauk is expected to turn.</p></article>"
                               "<script>x()</script></body></html>")
    assert "Chepauk" in text and "menu" not in text and "x()" not in text


def test_ssrf_guard():
    assert not asyncio.run(is_safe_url("http://localhost/admin"))
    assert not asyncio.run(is_safe_url("http://127.0.0.1:8000/health"))
    assert not asyncio.run(is_safe_url("file:///etc/passwd"))
    assert not asyncio.run(is_safe_url("http://169.254.169.254/latest/meta-data"))
