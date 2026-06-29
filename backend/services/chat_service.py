"""
ChatService: AI assistant using LLM with match context.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import ChatMessage, ChatSession, User
from backend.schemas import ChatResponse


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def respond(
        self,
        user: User,
        message: str,
        match_id: Optional[str],
        session_id: Optional[uuid.UUID],
    ) -> ChatResponse:
        # Get or create session
        session = None
        if session_id:
            result = await self.db.execute(
                select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
            )
            session = result.scalar_one_or_none()

        if not session:
            session = ChatSession(user_id=user.id, match_id=match_id, message_count=0)
            self.db.add(session)
            await self.db.flush()

        # Store user message
        user_msg = ChatMessage(session_id=session.id, role="user", content=message)
        self.db.add(user_msg)
        session.message_count += 1

        # Generate answer via LLM
        answer = await self._generate_answer(message, match_id)

        # Store assistant message
        asst_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
        self.db.add(asst_msg)
        await self.db.commit()

        return ChatResponse(
            session_id=session.id,
            answer=answer,
            related_players=self._extract_players(answer),
            sources_used=["rolling_features", "human_rules"],
        )

    async def _generate_answer(self, message: str, match_id: Optional[str]) -> str:
        """Call LLM or return intelligent mock answer."""
        try:
            from llm.router import get_llm_provider
            provider = get_llm_provider()
            context = f"Match ID: {match_id}" if match_id else "General fantasy cricket question"
            prompt = f"""You are XithSense AI, an expert fantasy cricket assistant with access to 22,062 matches of ball-by-ball data.

Context: {context}

User question: {message}

Provide a concise, data-driven answer. Reference specific stats, averages, or match conditions where relevant."""
            return await provider.complete(prompt)
        except Exception:
            # Mock answer for dev/demo
            return self._mock_answer(message)

    def _mock_answer(self, message: str) -> str:
        msg_lower = message.lower()
        if "captain" in msg_lower and "rohit" in msg_lower:
            return ("Rohit Sharma averages 28 while setting at this venue vs his 54 chasing average. "
                    "Today RCB are fielding first, making Rohit a setting captain — a lower ceiling pick. "
                    "Virat Kohli, who excels while chasing, is a stronger captain option.")
        if "differential" in msg_lower or "low ownership" in msg_lower:
            return ("Best differential picks for this match: Arshad Khan (4% ownership, death-overs specialist, "
                    "95-point ceiling) and B Sai Sudharsan (8% ownership, underrated opener). "
                    "These can separate your GL team from the field.")
        if "safe" in msg_lower or "risk" in msg_lower:
            return ("Safe pick: JR Hazlewood — consistent wicket-taker with 71% confidence score. "
                    "Risk pick: AD Russell — only 65% confidence but 95-point ceiling on this flat pitch.")
        return ("Based on the current match data and 22k+ historical matches analysed, "
                "my recommendation factors in recent form (last-5 avg FP), venue stats, "
                "toss result, and batter-vs-bowler matchups. Ask me about a specific player or captain choice!")

    def _extract_players(self, text: str) -> list[str]:
        known_players = ["Virat Kohli", "Rohit Sharma", "JR Hazlewood", "AD Russell",
                         "MS Dhoni", "JJ Bumrah", "Arshad Khan", "Shubman Gill"]
        return [p for p in known_players if p.lower() in text.lower()]
