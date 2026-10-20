"""Google Gemini LLM provider."""
from __future__ import annotations

import asyncio
from typing import Optional

from backend.config import settings


class GoogleProvider:
    async def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None,
                       history: Optional[list] = None) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            settings.LLM_MODEL if settings.LLM_MODEL.startswith("gemini") else "gemini-2.0-flash",
            system_instruction=system)
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in (history or []))
        response = await asyncio.to_thread(
            model.generate_content, f"{convo}\nuser: {prompt}" if convo else prompt,
            generation_config={"max_output_tokens": max_tokens or settings.LLM_MAX_TOKENS})
        return response.text
