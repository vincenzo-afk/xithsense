"""
ChatService: fantasy-cricket assistant grounded in the prediction engine.

Pipeline: guardrails → intent classification (CHAT_PROMPTS.md intents) →
grounded answer built from live engine numbers for the selected match →
optional LLM rephrase (with the grounded draft + context as the only facts).
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ChatMessage, ChatSession, Match, MatchupStat, User, VenueStat
from backend.schemas import ChatResponse, RelatedPlayer
from backend.services.engine import MatchScores, PlayerScore, score_match
from llm.explainer import build_factors, confidence_label
from optimizer.captain_engine import recommend
from optimizer.lp_optimizer import solve_team
from optimizer.scoring import score_for_mode

INJECTION = re.compile(r"ignore (previous|all|prior) instructions|you are now|new persona|system prompt|jailbreak", re.I)
OUT_OF_SCOPE_REPLY = ("I can only help with fantasy cricket decisions for matches on XithSense — captains, "
                      "differentials, matchups, venues and team strategy. What would you like to know about today's match?")

INTENTS = [
    ("NEWS_QUERY", r"\b(news|injur|update|announce|playing xi|line-?up|pitch report|weather|rain|latest|confirmed|ruled out)\b"),
    ("CAPTAIN_PICK", r"\b(captain|c/vc|vice[- ]?captain|armband|\bvc\b)"),
    ("DIFFERENTIAL", r"\b(differential|low[- ]owned|ownership|punt|contrarian|grand league|gl\b)"),
    ("TEAM_PICK", r"\b(team|xi|lineup|squad|pick my|best 11|eleven)"),
    ("MATCHUP_QUERY", r"\b(vs|against|matchup|spin|pace|left[- ]arm|bowler type)"),
    ("VENUE_QUERY", r"\b(venue|pitch|ground|stadium|dew|toss|chas)"),
    ("PLAYER_EXPLAIN", r"\b(why|should i|good pick|pick|form|worth|include|drop|bench)"),
]
CRICKET_WORDS = re.compile(r"\b(cricket|fantasy|dream11|match|player|bat|bowl|wicket|run|over|ipl|t20|odi|points?)\b", re.I)

SYSTEM = ("You are XithSense AI, an expert fantasy cricket assistant. Answer in at most 120 words using ONLY the facts "
          "in [GROUNDED ANSWER] and [MATCH CONTEXT]. Never invent numbers, never mention models or algorithms, never "
          "encourage betting. Use **bold** for player names and short bullet points where helpful.")


def classify(message: str) -> str:
    m = message.lower()
    for intent, pat in INTENTS:
        if re.search(pat, m):
            return intent
    if not CRICKET_WORDS.search(m) and len(m.split()) > 3:
        return "OUT_OF_SCOPE"
    return "GENERAL_STRATEGY"


def find_players(message: str, players: List[PlayerScore]) -> List[PlayerScore]:
    m = message.lower()
    hits = []
    for p in players:
        name = p.full_name.lower()
        surname = name.split()[-1]
        if name in m or (len(surname) > 3 and re.search(rf"\b{re.escape(surname)}\b", m)):
            hits.append(p)
    return hits


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _default_match(self) -> Optional[Match]:
        q = select(Match).where(Match.status.in_(("live", "upcoming"))).order_by(Match.match_date, Match.start_time)
        return (await self.db.execute(q.limit(1))).scalar_one_or_none()

    async def respond(self, user: User, message: str, match_id: Optional[str],
                      session_id: Optional[uuid.UUID]) -> ChatResponse:
        session = None
        if session_id:
            session = (await self.db.execute(select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.user_id == user.id))).scalar_one_or_none()
        match = await self.db.get(Match, match_id) if match_id else None
        if match is None:
            match = await self._default_match()
        if not session:
            session = ChatSession(user_id=user.id, match_id=match.id if match else None, message_count=0,
                                  title=message[:80])
            self.db.add(session)
            await self.db.flush()

        history = (await self.db.execute(select(ChatMessage).where(ChatMessage.session_id == session.id)
                                         .order_by(ChatMessage.created_at.desc()).limit(6))).scalars().all()
        self.db.add(ChatMessage(session_id=session.id, role="user", content=message))
        session.message_count += 1

        text = message[:500]
        from llm.agent import REFUSAL, is_cricket_question, run_agent
        scope_terms = [match.team_a, match.team_b] if match else []
        ms: Optional[MatchScores] = None
        if match is not None and match.squad_source != "partial":
            try:
                ms = await score_match(self.db, match.id)
                scope_terms += [p.full_name for p in ms.players]
            except ValueError:
                ms = None
        intent = "OUT_OF_SCOPE" if (INJECTION.search(text) or not is_cricket_question(text, scope_terms)) else classify(text)
        related: List[PlayerScore] = []
        sources: List[str] = []
        tools_used: List[dict] = []
        links: List[dict] = []
        answer, source = None, "engine"
        if intent == "OUT_OF_SCOPE":
            answer = REFUSAL
        else:
            hist = [{"role": h.role, "content": h.content} for h in reversed(history)]
            premium = user.role in ("premium", "admin")
            result = await run_agent(self.db, user, text, match, history=hist, premium=premium)
            if result is not None:
                answer, source = result.answer, f"agent:{result.provider}"
                tools_used, links = result.tools_used, result.sources
                sources = sorted({t["name"] for t in tools_used})
                if result.related_player_ids and ms is not None:
                    related = [ms.by_id[pid] for pid in result.related_player_ids if pid in ms.by_id]
            elif match is None:
                answer = "There are no upcoming fixtures loaded yet — ask an admin to sync fixtures."
            elif ms is None:
                answer = ("Squads aren't complete for this fixture yet (one side has no recent match data), so I can't "
                          "project players. Ask me again once the official squad is announced.")
            else:
                answer, related, sources = await self._grounded(intent, text, ms)
                links = [{"title": s, "url": s} for s in sources if s.startswith("http")]

        self.db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
        await self.db.commit()
        seen, rel = set(), []
        for p in related:
            if p.player_id not in seen:
                seen.add(p.player_id)
                rel.append(RelatedPlayer(player_id=uuid.UUID(p.player_id), full_name=p.full_name))
        return ChatResponse(session_id=session.id, answer=answer, intent=intent, related_players=rel[:8],
                            sources_used=sources, answer_source=source, tools_used=tools_used, sources=links)

    # ── grounded answers ──────────────────────────────────────────────────
    async def _grounded(self, intent: str, text: str, ms: MatchScores) -> Tuple[str, List[PlayerScore], List[str]]:
        m = ms.match
        mentioned = find_players(text, ms.players)
        head = f"**{m.team_a} vs {m.team_b}** · {(m.venue_name or '').split(',')[0]}\n\n"
        if intent == "NEWS_QUERY":
            from integrations import web
            results = await web.search(self.db, f"{m.team_a} vs {m.team_b} {text}", max_results=5)
            if not results:
                return (head + "I couldn't reach the web for news right now. Projections, captaincy and matchups are still "
                        "available from the match data."), [], []
            lines = [head + "**Latest from the web**"]
            for r in results:
                lines.append(f"- [{r['title']}]({r['url']}) — {r.get('snippet', '')[:160]}")
            lines.append("\nI can't verify these myself; check the source before locking a team.")
            return "\n".join(lines), [], [r["url"] for r in results]

        if intent == "CAPTAIN_PICK" or (intent == "PLAYER_EXPLAIN" and "captain" in text.lower()):
            mode = "grand_league" if re.search(r"grand|gl\b|mega", text.lower()) else "safe"
            opts = [p.to_opt() for p in ms.players]
            score_for_mode(opts, mode)
            res = solve_team(opts)
            picks = recommend(res.players, mode) if res else []
            lines = [head + "**Captaincy options**"]
            labels = {"best_captain": "🏆 Best", "safe_captain": "🛡️ Safe", "risk_captain": "🎲 Risk"}
            for c in picks:
                lines.append(f"- {labels[c.type]}: **{c.player.full_name}** — projects {c.player.predicted_fp:.0f} pts "
                             f"(ceiling {c.player.ceiling:.0f}, {c.player.confidence}% confidence, "
                             f"~{c.player.ownership:.0f}% owned)")
            for p in mentioned:
                if p.player_id not in {c.player.player_id for c in picks}:
                    rank = [x.player_id for x in sorted(ms.players, key=lambda s: -s.predicted_fp)].index(p.player_id) + 1
                    lines.append(f"\n**{p.full_name}** ranks #{rank} for projected points ({p.predicted_fp:.0f}); "
                                 f"{self._why(p)}")
            return "\n".join(lines), [ms.by_id[c.player.player_id] for c in picks] + mentioned, ["predictions", "captain_engine"]

        if intent == "DIFFERENTIAL":
            diffs = sorted([p for p in ms.players if p.ownership < 25], key=lambda p: -(p.fp_ceiling - p.ownership * 0.5))[:4]
            lines = [head + "**Differential picks** (low ownership, high ceiling)"]
            for p in diffs:
                lines.append(f"- **{p.full_name}** ({p.role}, {p.credits}cr) — ~{p.ownership:.0f}% owned, ceiling "
                             f"{p.fp_ceiling:.0f}, form {p.fp_avg_5:.1f} avg")
            lines.append("\nPair one or two of these with a popular captain to separate your grand-league team.")
            return "\n".join(lines), diffs, ["predictions", "ownership_estimates"]

        if intent == "TEAM_PICK":
            opts = [p.to_opt() for p in ms.players]
            score_for_mode(opts, "safe")
            res = solve_team(opts)
            if not res:
                return head + "I couldn't build a valid team for this match.", [], []
            picks = recommend(res.players, "safe")
            team = sorted(res.players, key=lambda p: ("WK", "BAT", "AR", "BOWL").index(p.role))
            lines = [head + f"**Safe XI** — {sum(p.credits for p in team):.1f} credits"]
            for role in ("WK", "BAT", "AR", "BOWL"):
                names = [p.full_name for p in team if p.role == role]
                lines.append(f"- **{role}**: {', '.join(names)}")
            lines.append(f"\n(C) **{picks[0].player.full_name}** · (VC) **{picks[1].player.full_name}**")
            return "\n".join(lines), [ms.by_id[p.player_id] for p in team], ["predictions", "optimizer"]

        if intent == "MATCHUP_QUERY" and mentioned:
            p = mentioned[0]
            stats = (await self.db.execute(select(MatchupStat).where(MatchupStat.player_id == uuid.UUID(p.player_id)))).scalars().all()
            lines = [head + f"**{p.full_name} — matchups**"]
            names = {"pace_right": "Right-arm pace", "pace_left": "Left-arm pace", "spin_off": "Off-spin",
                     "spin_left": "Left-arm orthodox", "spin_wrist": "Wrist spin"}
            for s in sorted(stats, key=lambda s: -s.balls_faced):
                lines.append(f"- {names.get(s.bowler_type, s.bowler_type)}: SR {s.strike_rate:.0f}, "
                             f"out every {s.balls_faced / max(s.dismissals, 1):.0f} balls ({s.balls_faced} balls)")
            f = p.features
            lines.append(f"\nToday's opposition bowls ~{f['opp_spin_share'] * 100:.0f}% spin — expected SR "
                         f"{f['expected_matchup_sr']:.0f}.")
            return "\n".join(lines), [p], ["matchup_stats"]

        if intent == "VENUE_QUERY" or (intent == "MATCHUP_QUERY" and not mentioned):
            vs = None
            if m.venue_id:
                vs = (await self.db.execute(select(VenueStat).where(VenueStat.venue_id == m.venue_id))).scalars().first()
            lines = [head + f"**{(m.venue_name or 'Venue').split(',')[0]} profile**"]
            if ms.venue:
                lines.append(f"- Pitch: **{(ms.venue.pitch_type or 'unknown').title()}**"
                             + (" · dew expected in the evening" if ms.venue.dew_factor else ""))
            if vs:
                lines.append(f"- Avg 1st innings: **{vs.avg_first_innings:.0f}** over {vs.total_matches} matches")
                if vs.chasing_win_pct is not None:
                    lines.append(f"- Chasing teams win **{vs.chasing_win_pct * 100:.0f}%**")
                if vs.spin_wicket_pct is not None:
                    lines.append(f"- Wickets: {vs.spin_wicket_pct * 100:.0f}% spin / {vs.pace_wicket_pct * 100:.0f}% pace")
            best = sorted(ms.players, key=lambda p: -p.features.get("venue_fp_avg", 0) if p.features.get("venue_matches", 0) >= 3 else 0)[:3]
            if best:
                lines.append("- Best venue records: " + ", ".join(f"**{p.full_name}** ({p.features['venue_fp_avg']:.0f} avg)" for p in best))
            if m.toss_winner:
                lines.append(f"\nToss: **{m.toss_winner}** chose to {m.toss_decision}.")
            return "\n".join(lines), best, ["venue_stats"]

        if mentioned:
            lines = [head]
            for p in mentioned[:2]:
                lines.append(f"**{p.full_name}** ({p.role}, {p.team}) — projects **{p.predicted_fp:.0f} pts**, "
                             f"ceiling {p.fp_ceiling:.0f}, floor {p.fp_floor:.0f}. Confidence: "
                             f"{confidence_label(p.confidence)} ({p.confidence}%).")
                for f in build_factors(p, m, m.venue_name)[:4]:
                    lines.append(f"- {f['factor']}: {f['value']} — {f['detail']}")
                lines.append(f"\n**Verdict:** {self._verdict(p, ms)}\n")
            return "\n".join(lines), mentioned, ["rolling_features", "venue_stats", "matchup_stats", "human_rules"]

        top = sorted(ms.players, key=lambda p: -p.ensemble_score)[:5]
        lines = [head + "**Top-rated players for this match**"]
        for p in top:
            lines.append(f"- **{p.full_name}** ({p.role}) — {p.predicted_fp:.0f} pts projected, {p.confidence}% confidence")
        lines.append("\nAsk me about captains, differentials, a specific player, matchups or the venue.")
        return "\n".join(lines), top, ["predictions"]

    async def _players_not_in_match(self, text: str, ms: MatchScores) -> list:
        from backend.models import Player
        in_match = {p.player_id for p in ms.players}
        words = {w for w in re.findall(r"[a-z]{4,}", text.lower())}
        if not words:
            return []
        out = []
        for p in (await self.db.execute(select(Player))).scalars():
            if str(p.id) in in_match:
                continue
            surname = p.full_name.lower().split()[-1]
            if surname in words or p.full_name.lower() in text.lower():
                out.append(p)
        return out

    def _why(self, p: PlayerScore) -> str:
        f = p.features
        reasons = []
        if p.fp_avg_5 < 25:
            reasons.append(f"form is flat ({p.fp_avg_5:.1f} avg last 5)")
        if f.get("venue_matches", 0) >= 2 and f["venue_fp_avg"] < p.fp_avg_10 - 4:
            reasons.append(f"he averages only {f['venue_fp_avg']:.0f} here")
        neg = [r for r in p.rules_fired if r["impact"] < 0]
        if neg:
            reasons.append(neg[0]["description"].rstrip("."))
        if p.consistency > 1.0:
            reasons.append("returns are volatile")
        return ("; ".join(reasons) or "others simply project higher today") + "."

    def _verdict(self, p: PlayerScore, ms: MatchScores) -> str:
        rank = [x.player_id for x in ms.players].index(p.player_id) + 1
        if rank <= 8:
            return f"Must-pick — ranked #{rank} of {len(ms.players)} in this match."
        if rank <= 15:
            return f"Good option — #{rank} of {len(ms.players)}; include in most teams."
        if p.is_differential or p.ownership < 15:
            return f"Grand-league punt — #{rank} overall but low ownership gives leverage."
        return f"Avoid in safe teams — ranked #{rank} of {len(ms.players)}; {self._why(p)}"
