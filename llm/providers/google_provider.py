"""Google Gemini LLM provider."""
from __future__ import annotations
from backend.config import settings


class GoogleProvider:
    async def complete(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(settings.LLM_MODEL or "gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"[LLM unavailable: {e}]"
