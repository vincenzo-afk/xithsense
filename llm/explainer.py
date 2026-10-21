"""
Explainability engine (EXPLAINABILITY_ENGINE_SPEC).

Builds data-backed factors for a player pick and a plain-English rationale.
The template rationale is always available; when an LLM provider key is
configured, it is rephrased by the LLM under a timeout with output guardrails
(GUARDRAILS.md), falling back to the template on any failure.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import List, Optional, Tuple

from backend.config import settings

logger = logging.getLogger(__name__)

PROHIBITED = ["100% certain", "guaranteed", "definitely will", "place a bet", "i recommend betting",
              "insider information", "sure thing", "money-back guarantee"]
ML_TERMS = re.compile(r"\b(xgboost|lightgbm|catboost|ensemble|rules engine|model weights?)\b", re.I)


def form_label(avg5: float) -> str:
    return "excellent" if avg5 >= 50 else "strong" if avg5 >= 38 else "steady" if avg5 >= 26 else "patchy"


def confidence_label(c: float) -> str:
    return "High" if c >= 80 else "Medium" if c >= 60 else "Low" if c >= 40 else "Very Low"


def build_factors(ps, match, venue_name: Optional[str]) -> List[dict]:
    f = ps.features
    out: List[dict] = []
    trend = ps.fp_avg_3 - ps.fp_avg_10
    out.append({
        "factor": "Recent Form", "value": form_label(ps.fp_avg_5).capitalize(),
        "detail": f"{ps.fp_avg_5:.1f} avg FP over last 5 (last 3: {ps.fp_avg_3:.1f}, "
                  f"{'up' if trend >= 0 else 'down'} {abs(trend):.1f} vs last-10)",
        "sentiment": "positive" if ps.fp_avg_5 >= 35 else "negative" if ps.fp_avg_5 < 22 else "neutral",
    })
    vm = int(f.get("venue_matches", 0))
    if vm >= 2:
        diff = f["venue_fp_avg"] - ps.fp_avg_10
        out.append({
            "factor": "Venue Record", "value": f"{f['venue_fp_avg']:.1f} FP avg",
            "detail": f"{vm} matches at {(venue_name or 'this venue').split(',')[0]} "
                      f"({'+' if diff >= 0 else ''}{diff:.1f} vs his usual)",
            "sentiment": "positive" if diff > 4 else "negative" if diff < -4 else "neutral",
        })
    else:
        out.append({"factor": "Venue Record", "value": "Limited data",
                    "detail": f"Only {vm} previous match{'es' if vm != 1 else ''} at this ground",
                    "sentiment": "neutral"})
    if ps.role in ("BAT", "WK", "AR") and f.get("expected_matchup_sr", 0) > 0:
        spin_share = f["opp_spin_share"]
        sr = f["expected_matchup_sr"]
        attack = "spin-heavy" if spin_share > 0.45 else "pace-heavy" if spin_share < 0.3 else "balanced"
        out.append({
            "factor": "Matchup", "value": f"SR {sr:.0f} vs this attack",
            "detail": f"{attack} opposition attack — SR {f['sr_vs_pace']:.0f} vs pace, {f['sr_vs_spin']:.0f} vs spin",
            "sentiment": "positive" if sr >= 140 else "negative" if sr < 115 else "neutral",
        })
    if ps.role in ("BOWL", "AR") and f.get("avg_wickets_5", 0) > 0:
        out.append({
            "factor": "Bowling", "value": f"{f['avg_wickets_5']:.1f} wkts/match",
            "detail": f"Economy {f['avg_economy_5']:.1f} over the last 5",
            "sentiment": "positive" if f["avg_wickets_5"] >= 1.3 else "neutral",
        })
    ch = f.get("is_chasing", 0.5)
    if ch in (0.0, 1.0):
        cw = f.get("venue_chasing_win_pct", 0.5)
        out.append({
            "factor": "Match Context", "value": "Chasing" if ch == 1.0 else "Setting",
            "detail": f"Teams chasing here win {cw * 100:.0f}% of the time"
                      + (" · home ground" if f.get("is_home") else ""),
            "sentiment": "positive" if (ch == 1.0 and cw > 0.55) or (ch == 0.0 and cw < 0.45) else "neutral",
        })
    elif f.get("is_home"):
        out.append({"factor": "Match Context", "value": "Home ground", "detail": "Playing at his home venue",
                    "sentiment": "positive"})
    for r in ps.rules_fired[:3]:
        out.append({"factor": "Analyst Insight", "value": f"{r['impact']:+.1f} pts",
                    "detail": r.get("description") or r["id"],
                    "sentiment": "positive" if r["impact"] > 0 else "negative"})
    return out


def template_explanation(ps, factors: List[dict]) -> str:
    strength = "Strong pick" if ps.confidence >= 70 else "Solid option" if ps.confidence >= 55 else "Speculative pick"
    parts = [f"{strength}: {ps.full_name} projects {ps.predicted_fp:.0f} points (ceiling {ps.fp_ceiling:.0f})."]
    parts.append(f"Form is {form_label(ps.fp_avg_5)} at {ps.fp_avg_5:.1f} avg FP over the last five.")
    venue = next((x for x in factors if x["factor"] == "Venue Record" and x["value"] != "Limited data"), None)
    if venue:
        parts.append(f"Venue record: {venue['value']} across {venue['detail'].split(' matches')[0]} games.")
    matchup = next((x for x in factors if x["factor"] in ("Matchup", "Bowling")), None)
    if matchup:
        parts.append(f"{matchup['factor']}: {matchup['value']}.")
    rule = next((x for x in factors if x["factor"] == "Analyst Insight"), None)
    if rule:
        parts.append(rule["detail"].rstrip(".") + ".")
    parts.append(f"Confidence: {confidence_label(ps.confidence)}.")
    return " ".join(parts)


def _passes_guardrails(text: str) -> bool:
    low = text.lower()
    words = len(text.split())
    return (20 <= words <= 120 and not any(p in low for p in PROHIBITED)
            and not ML_TERMS.search(text) and bool(re.search(r"\d", text)))


def llm_available() -> bool:
    from llm.router import llm_available as _available
    return _available()


async def llm_complete(prompt: str, system: Optional[str] = None, max_tokens: int = 300) -> Optional[str]:
    if not llm_available():
        return None
    try:
        from llm.router import get_llm_provider
        provider = get_llm_provider()
        text = await asyncio.wait_for(provider.complete(prompt, system=system, max_tokens=max_tokens),
                                      timeout=settings.LLM_TIMEOUT_SECONDS)
        if not text or text.startswith("[LLM unavailable"):
            return None
        return text.strip()
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return None


EXPLAIN_SYSTEM = (
    "You are XithSense, a fantasy cricket analyst. Rewrite the analyst notes into a crisp, confident "
    "explanation of at most 70 words for a fantasy player. Use only the numbers given. Never mention "
    "models, algorithms, or betting. End with the confidence label."
)


async def explain(ps, match, venue_name: Optional[str]) -> Tuple[str, List[dict], str]:
    factors = build_factors(ps, match, venue_name)
    text = template_explanation(ps, factors)
    llm = await llm_complete(
        f"Player: {ps.full_name} ({ps.role}, {ps.team})\nMatch: {match.team_a} vs {match.team_b} at {venue_name}\n"
        f"Analyst notes: {text}\nFactors: " + "; ".join(f"{x['factor']}: {x['value']} — {x['detail']}" for x in factors),
        system=EXPLAIN_SYSTEM, max_tokens=150)
    if llm and _passes_guardrails(llm):
        return llm, factors, "llm"
    return text, factors, "template"
